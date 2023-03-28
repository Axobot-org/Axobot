import json
import time
from typing import Any, Optional

import discord
from cachingutils import LRUCache
from discord import app_commands
from discord.ext import commands

from fcts import checks
from libs.bot_classes import Axobot, MyContext
from libs.serverconfig.autocomplete import autocomplete_main
from libs.serverconfig.config_paginator import ServerConfigPaginator
from libs.serverconfig.converters import AllRepresentation, from_input, from_raw, to_display, to_raw
from libs.serverconfig.options_list import options as options_list
from libs.views import ConfirmView


class ServerConfig(commands.Cog):
    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "serverconfig"
        self.cache: LRUCache = LRUCache(max_size=1_000, timeout=3_600 * 2)
        self.membercounter_pending: dict[int, int] = {}
        self.embed_color = 0x3fb9ef
        self.log_color = 0x1b5fb1
        self.max_members_for_nicknames = 3_000

    async def clear_cache(self):
        self.cache._items.clear()

    # ---- PUBLIC QUERIES ----

    async def get_raw_option(self, guild_id: int, option_name: str):
        "Return the value of a server config option without any transformation"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            return to_raw(option_name, options_list[option_name]["default"])
        if (value := await self.db_get_value(guild_id, option_name)) is None:
            value = to_raw(option_name, options_list[option_name]["default"])
        return value

    async def get_option(self, guild_id: int, option_name: str):
        "Return the formated value of a server config option"
        if (cached := self.cache.get((guild_id, option_name))) is not None:
            return cached
        if (guild := self.bot.get_guild(guild_id)) is None:
            value = options_list[option_name]["default"]
        else:
            raw_value = await self.get_raw_option(guild_id, option_name)
            value = from_raw(option_name, raw_value, guild)
        if option_name == "nicknames_history" and value is None:
            value = len(guild.members) < self.max_members_for_nicknames
        self.cache[(guild_id, option_name)] = value
        return value

    async def set_option(self, guild_id: int, option_name: str, value: Any):
        "Set the value of a server config option"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            return False
        if await self.db_set_value(guild_id, option_name, to_raw(option_name, value)):
            self.cache[(guild_id, option_name)] = value
            if option_name == "prefix":
                await self.bot.prefix_manager.update_prefix(guild_id, value)
            return True
        return False

    async def reset_option(self, guild_id: int, option_name: str):
        "Reset the value of a server config option"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            return False
        if await self.db_delete_option(guild_id, option_name):
            if (guild_id, option_name) in self.cache:
                del self.cache._items[(guild_id, option_name)]
            if option_name == "prefix":
                await self.bot.prefix_manager.reset_prefix(guild_id)
            return True
        return False

    async def reset_guild_config(self, guild_id: int):
        "Reset the config of a guild"
        if not self.bot.database_online:
            return False
        if await self.db_delete_guild(guild_id):
            for option_name in options_list:
                if (guild_id, option_name) in self.cache:
                    del self.cache._items[(guild_id, option_name)]
                    await self.bot.prefix_manager.reset_prefix(guild_id)
            return True
        return False

    async def get_guild_config(self, guild_id: int, with_defaults: bool) -> dict[str, Any]:
        "Return the config of a guild"
        if not self.bot.database_online or (guild := self.bot.get_guild(guild_id)) is None:
            if with_defaults:
                return {option_name: option["default"] for option_name, option in options_list.items()}
            return {}
        config = await self.db_get_guild(guild_id)
        if config is None:
            if with_defaults:
                return {option_name: option["default"] for option_name, option in options_list.items()}
            return {}
        if with_defaults:
            for option_name, option in options_list.items():
                if option_name not in config:
                    config[option_name] = option["default"]
                else:
                    config[option_name] = from_raw(option_name, config[option_name], guild)
        return config

    async def get_languages(self, ignored_guilds: list[int]):
        "Return stats on used languages"
        if not self.bot.database_online or not 'Languages' in self.bot.cogs:
            return {}
        query = "SELECT `guild_id`, `value` FROM `serverconfig` WHERE `option_name` = 'language' AND `beta` = %s"
        values_list: list[str] = []
        guilds = {x.id for x in self.bot.guilds if x.id not in ignored_guilds}
        async with self.bot.db_query(query, (self.bot.beta,)) as query_results:
            for row in query_results:
                if row['guild_id'] in guilds:
                    values_list.append(row['value'])
        for _ in range(len(guilds)-len(values_list)):
            values_list.append(options_list['language']['default'])
        langs: dict[str, int] = {}
        for lang in options_list['language']['values']:
            langs[lang] = values_list.count(lang)
        return langs

    async def get_xp_types(self, ignored_guilds: list[int]):
        "Return stats on used xp types"
        if not self.bot.database_online:
            return {}
        query = "SELECT `guild_id`, `value` FROM `serverconfig` WHERE `option_name` = 'xp_type' AND `beta` = %s"
        values_list: list[str] = []
        guilds = {x.id for x in self.bot.guilds if x.id not in ignored_guilds}
        async with self.bot.db_query(query, (self.bot.beta,)) as query_results:
            for row in query_results:
                if row['guild_id'] in guilds:
                    values_list.append(row['value'])
        for _ in range(len(guilds)-len(values_list)):
            values_list.append(options_list['xp_type']['default'])
        types: dict[str, int] = {}
        for name in options_list['xp_type']['values']:
            types[name] = values_list.count(name)
        return types

    async def check_member_config_permission(self, member: discord.Member, option_name: str):
        "Check if a user has the required roles from a specific config"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if options_list[option_name]["type"] != "roles_list":
            raise ValueError(f"Option {option_name} is not a roles list")
        if await self.bot.get_cog("Admin").check_if_god(member):
            return True
        if not self.bot.database_online or not isinstance(member, discord.Member):
            return False
        raw_roles = await self.get_raw_option(member.guild.id, option_name)
        if raw_roles is None:
            return False
        roles_ids: list[int] = json.loads(raw_roles)
        member_role_ids = {role.id for role in member.roles}
        return any(role in member_role_ids for role in roles_ids)

    async def update_everyMembercounter(self):
        "Update all pending membercounter channels"
        if not self.bot.database_online:
            return
        i = 0
        now = time.time()
        for guild in self.bot.guilds:
            if guild.id in self.membercounter_pending.keys() and self.membercounter_pending[guild.id] < now:
                del self.membercounter_pending[guild.id]
                await self.update_memberChannel(guild)
                i += 1
        if i > 0:
            emb = discord.Embed(description=f"[MEMBERCOUNTER] {i} channels refreshed", color=5011628, timestamp=self.bot.utcnow())
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb, url="loop")

    async def update_memberChannel(self, guild: discord.Guild):
        "Update a membercounter channel for a specific guild"
        # If we already did an update recently: abort
        if guild.id in self.membercounter_pending.keys():
            if self.membercounter_pending[guild.id] > time.time():
                return False
        channel = await self.get_option(guild.id, "membercounter")
        if channel is None:
            return False
        lang = await self.bot._(guild.id, '_used_locale')
        tr = (await self.bot._(guild.id, "misc.membres")).capitalize()
        text = "{}{}: {}".format(tr, " " if lang=='fr' else "" , guild.member_count)
        if channel.name == text:
            return
        try:
            await channel.edit(name=text, reason=await self.bot._(guild.id,"logs.reason.memberchan"))
            self.membercounter_pending[guild.id] = round(time.time()) + 5*60 # cooldown 5min
            return True
        except discord.HTTPException as err:
            self.bot.log.warning("[UpdateMemberChannel] %s", err)
        except Exception as err:
            self.bot.dispatch("error", err)
        return False

    # ---- DATABASE ACCESS ----

    async def db_get_value(self, guild_id: int, option_name: str) -> Optional[str]:
        "Get a value from the database"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "SELECT `value` FROM `serverconfig` WHERE `guild_id` = %s AND `option_name` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, option_name, self.bot.beta), fetchone=True) as query_results:
            if len(query_results) == 0:
                return None
            return query_results['value']

    async def db_get_guild(self, guild_id: int) -> Optional[dict[str, str]]:
        "Get a guild from the database"
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "SELECT * FROM `serverconfig` WHERE `guild_id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta)) as query_results:
            if len(query_results) == 0:
                return None
            return {row['option_name']: row['value'] for row in query_results}

    async def db_set_value(self, guild_id: int, option_name: str, new_value: str) -> bool:
        "Edit a value in the database"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "INSERT INTO `serverconfig` (`guild_id`, `option_name`, `value`, `beta`) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE `value` = %s"
        async with self.bot.db_query(query, (guild_id, option_name, new_value, self.bot.beta, new_value), returnrowcount=True) as query_results:
            return query_results > 0

    async def db_delete_option(self, guild_id: int, option_name: str) -> bool:
        "Delete a value from the database"
        if option_name not in options_list:
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "DELETE FROM `serverconfig` WHERE `guild_id` = %s AND `option_name` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, option_name, self.bot.beta), returnrowcount=True) as query_results:
            return query_results > 0

    async def db_delete_guild(self, guild_id: int) -> bool:
        "Delete a guild from the database"
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "DELETE FROM `serverconfig` WHERE `guild_id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta), returnrowcount=True) as query_results:
            return query_results > 0

    # ---- COMMANDS ----

    async def option_name_autocomplete(self, current: str):
        "Autocompletion for an option name"
        filtered = sorted(
            (not name.startswith(current), name) for name, data in options_list.items()
            if data["is_listed"] and current in name
        )
        return [
            app_commands.Choice(name=name, value=name)
            for _, name in filtered
        ][:25]

    @commands.hybrid_group(name='config')
    @discord.app_commands.default_permissions(manage_guild=True)
    @commands.guild_only()
    async def config_main(self, ctx: MyContext):
        "Configure the bot for your server"
        if ctx.invoked_subcommand is None:
            subcommand_passed = ctx.message.content.replace(ctx.prefix+"config", "").strip()
            if subcommand_passed in options_list:
                await self.config_see(ctx, subcommand_passed)
            else:
                await ctx.send_help("config")
                return

    @config_main.command(name="set")
    @app_commands.describe(
        option="The option to modify",
        value="The new option value"
        )
    @commands.cooldown(3, 8, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def config_set(self, ctx: MyContext, option: str, *, value: str):
        "Set a server configuration option"
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id, "cases.no_database"))
        if (opt_data := options_list.get(option)) is None:
            return await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        if not opt_data["is_listed"]:
            return await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        await self.config_set_cmd(ctx, option, value)

    @config_set.autocomplete("option")
    async def sconfig_change_autocomplete_opt(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    @config_set.autocomplete("value")
    async def sconfig_change_autocomplete_val(self, interaction: discord.Interaction, value: str):
        "Autocomplete the value of a config option"
        if option_name := interaction.namespace.option:
            try:
                return await autocomplete_main(self.bot, interaction, option_name, value)
            except Exception as err:
                self.bot.dispatch("error", err, interaction)
        return []


    @config_main.command(name="reset")
    @app_commands.describe(option="The option to reset")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def config_reset(self, ctx: MyContext, option: str):
        "Reset an option to its initial value"
        if not ctx.bot.database_online:
            await ctx.send(await self.bot._(ctx.guild.id, "cases.no_database"))
            return
        if (opt_data := options_list.get(option)) is None:
            return await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        if not opt_data["is_listed"]:
            return await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        await self.reset_option(ctx.guild.id, option)
        await ctx.send(await self.bot._(ctx.guild.id, "server.value-deleted", option=option))
        # send internal log
        msg = f"Reset option in server {ctx.guild.id}: {option}"
        emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
        emb.set_footer(text=ctx.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)
        self.bot.log.debug(msg)

    @config_reset.autocomplete("option")
    async def sconfig_del_autocomplete(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    @config_main.command(name="reset-all")
    @commands.cooldown(1, 60, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_admin)
    async def config_reset_all(self, ctx: MyContext):
        """Reset the whole config of your server
        VERY DANGEROUS, NO ROLLBACK POSSIBLE"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id, "cases.no_database"))
        text = await self.bot._(ctx.guild.id, "server.reset-all.confirmation")
        confirm_view = ConfirmView(
            self.bot, ctx.channel,
            validation=lambda inter: inter.user == ctx.author,
            ephemeral=False,
            send_confirmation=False
            )
        await confirm_view.init()
        confirm_msg = await ctx.send(text, view=confirm_view)
        await confirm_view.wait()
        await confirm_view.disable(confirm_msg)
        if not confirm_view.value:
            return
        if await self.reset_guild_config(ctx.guild.id):
            await ctx.send(await self.bot._(ctx.guild.id, "server.reset-all.success"))
            # Send internal log
            msg = f"Reset all options in server {ctx.guild.id}"
            emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
            emb.set_footer(text=ctx.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)
            self.bot.log.info(msg)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "server.reset-all.error"))

    @config_main.command(name='list')
    @commands.cooldown(1, 20, commands.BucketType.guild)
    async def config_list(self, ctx: MyContext):
        """Get the list of every usable option"""
        options = sorted(options_list.keys())
        txt = "\n```\n-{}\n```\n".format('\n-'.join(options))
        link = "<https://zbot.readthedocs.io/en/latest/server.html#list-of-every-option>"
        await ctx.send(await self.bot._(ctx.guild.id, "server.config-list",
                                        text=txt, link=link))

    @config_main.command(name="see")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    @commands.guild_only()
    async def config_see(self, ctx: MyContext, option: Optional[str]=None):
        """Displays the value of an option, or all options if none is specified"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id, "cases.no_database"))
        if option is None:
            await self.send_all_config(ctx.guild, ctx)
        else:
            await self.send_specific_config(ctx.guild, ctx, option)

    @config_see.autocomplete("option")
    async def sconfig_see_autocomplete(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    async def send_all_config(self, guild: discord.Guild, ctx: MyContext):
        "Send the config lookup of a guild into a channel"
        if self.bot.zombie_mode:
            return
        _quit = await self.bot._(ctx.guild, "misc.quit")
        view = ServerConfigPaginator(self.bot, ctx.author, stop_label=_quit.capitalize(), guild=guild, cog=self)
        msg = await view.send_init(ctx)
        if msg:
            if await view.wait():
                # only manually disable if it was a timeout (ie. not a user stop)
                await view.disable(msg)

    async def send_specific_config(self, guild: discord.Guild, ctx: MyContext, option: str):
        "Send the specific config value for guild into a channel"
        if self.bot.zombie_mode:
            return
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.cant-embed"))
            return
        if (opt_data := options_list.get(option)) is None:
            return await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        if not opt_data["is_listed"]:
            return await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        value = await self.get_option(guild.id, option)
        if (display := await to_display(option, value, guild, self.bot)) is None:
            display = "Ø"
        elif len(display) > 1024:
            display = display[:1023] + "…"
        title = await self.bot._(ctx.channel, "server.opt_title", opt=option, guild=guild.name)
        description = await self.bot._(ctx.channel, f"server.server_desc.{option}", value=display)
        embed = discord.Embed(title=title, color=self.embed_color, description=description)
        if isinstance(ctx, commands.Context):
            embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        await ctx.send(embed=embed)

    async def _get_set_success_message(self, ctx: MyContext, option_name: str, value: Any):
        "Generate a proper success message when a setting is modified"
        option_type = options_list[option_name]["type"]
        if option_type == "boolean":
            if value:
                return await self.bot._(ctx.guild.id, f"server.set_success.boolean.true", opt=option_name)
            else:
                return await self.bot._(ctx.guild.id, f"server.set_success.boolean.false", opt=option_name)
        if option_type == "levelup_channel":
            if value in {"none", "any"}:
                return await self.bot._(ctx.guild.id, f"server.set_success.levelup_channel.{value}", opt=option_name)
            else:
                return await self.bot._(ctx.guild.id, f"server.set_success.levelup_channel.channel", opt=option_name, val=value.mention)
        str_value = await to_display(option_name, value, ctx.guild, self.bot)
        return await self.bot._(ctx.guild.id, f"server.set_success.{option_type}", opt=option_name, val=str_value)

    async def _get_set_error_message(self, ctx: MyContext, option_name: str, error: ValueError, value: Any):
        "Generate a proper error message for an invalid value"
        repr: AllRepresentation = error.args[2]
        if repr["type"] in {"int", "float"}:
            return await self.bot._(ctx.guild.id, f"server.set_error.{repr['type']}_err", min=repr["min"], max=repr["max"])
        if repr["type"] == "enum":
            return await self.bot._(ctx.guild.id, f"server.set_error.ENUM_INVALID", list=', '.join(repr["values"]))
        if repr["type"] == "text":
            return await self.bot._(ctx.guild.id, f"server.set_error.text_err", min=repr["min_length"], max=repr["max_length"])
        error_name: str = error.args[1]
        if error_name in {"ROLES_TOO_FEW", "ROLES_TOO_MANY"}:
            return await self.bot._(ctx.guild.id, "server.set_error.roles_list", min=repr["min_count"], max=repr["max_count"])
        if error_name in {"CHANNELS_TOO_FEW", "CHANNELS_TOO_MANY"}:
            return await self.bot._(ctx.guild.id, "server.set_error.channels_list", min=repr["min_count"], max=repr["max_count"])
        if error_name in {"EMOJIS_TOO_FEW", "EMOJIS_TOO_MANY"}:
            if repr["min_count"] == repr["max_count"]:
                return await self.bot._(ctx.guild.id, "server.set_error.emojis_list_exact", count=repr["min_count"])
            return await self.bot._(ctx.guild.id, "server.set_error.emojis_list", min=repr["min_count"], max=repr["max_count"])
        user_input = error.args[3] if len(error.args) > 3 else None
        return await self.bot._(ctx.guild.id, "server.set_error." + error_name, input=user_input)

    async def config_set_cmd(self, ctx: MyContext, option_name: str, raw_input: str):
        "Process the config_set command"
        if option_name not in options_list:
            await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
            return
        await ctx.defer()
        try:
            value = await from_input(option_name, raw_input, ctx.guild, ctx)
        except ValueError as err:
            if len(err.args) > 2:
                mentions = discord.AllowedMentions.none()
                await ctx.send(await self._get_set_error_message(ctx, option_name, err, raw_input), allowed_mentions=mentions)
            else:
                await ctx.send(await self.bot._(ctx.guild.id, "server.internal-error"))
            return
        await self.set_option(ctx.guild.id, option_name, value)
        await ctx.send(await self._get_set_success_message(ctx, option_name, value))
        # Send internal log
        msg = f"Changed option in server {ctx.guild.id}: {option_name} = `{to_raw(option_name, value)}`"
        emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
        emb.set_footer(text=ctx.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)
        self.bot.log.debug(msg)


async def setup(bot: Axobot):
    await bot.add_cog(ServerConfig(bot))
