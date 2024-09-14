import json
import time
from typing import Any, Literal

import discord
from cachetools import TTLCache
from discord import app_commands
from discord.ext import commands, tasks

from core.bot_classes import Axobot
from core.tips import UserTip
from core.views import ConfirmView

from .src.autocomplete import autocomplete_main
from .src.checks import check_config
from .src.config_paginator import ServerConfigPaginator
from .src.converters import (AllRepresentation, from_input, from_raw,
                             to_display, to_raw)


class ServerConfig(commands.Cog):
    "Commands and events related to the bot configuration on a server"
    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "serverconfig"
        self.cache = TTLCache[tuple[int, str], Any](maxsize=10_000, ttl=60) # 1min cache
        self.enable_caching = True
        self.membercounter_pending: dict[int, int] = {}
        self.embed_color = 0x3fb9ef
        self.log_color = 0x1b5fb1
        self.max_members_for_nicknames = 3_000

    async def cog_load(self):
        self.update_every_membercounter.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.update_every_membercounter.cancel() # pylint: disable=no-member

    async def clear_cache(self):
        self.cache.clear()

    async def get_options_list(self):
        return await self.bot.get_options_list()

    # ---- PUBLIC QUERIES ----

    async def get_raw_option(self, guild_id: int, option_name: str):
        "Return the value of a server config option without any transformation"
        if option_name not in await self.get_options_list():
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            return await to_raw(option_name, (await self.get_options_list())[option_name]["default"], self.bot)
        if (value := await self.db_get_value(guild_id, option_name)) is None:
            value = await to_raw(option_name, (await self.get_options_list())[option_name]["default"], self.bot)
        return value

    async def get_option(self, guild_id: discord.Guild | int, option_name: str):
        "Return the formated value of a server config option"
        if self.enable_caching:
            try:
                return self.cache[(guild_id, option_name)]
            except KeyError:
                pass
        guild = guild_id if isinstance(guild_id, discord.Guild) else self.bot.get_guild(guild_id)
        if guild is None:
            value = (await self.get_options_list())[option_name]["default"]
        else:
            guild_id = guild.id
            raw_value = await self.get_raw_option(guild_id, option_name)
            value = await from_raw(option_name, raw_value, guild, self.bot)
        if self.enable_caching:
            self.cache[(guild_id, option_name)] = value
        return value

    async def set_option(self, guild_id: int, option_name: str, value: Any):
        "Set the value of a server config option"
        if not isinstance(guild_id, int):
            raise ValueError(f"Guild ID must be an integer, not {type(guild_id)}")
        if option_name not in (await self.get_options_list()):
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            return False
        if await self.db_set_value(guild_id, option_name, await to_raw(option_name, value, self.bot)):
            if self.enable_caching:
                self.cache[(guild_id, option_name)] = value
            return True
        return False

    async def reset_option(self, guild_id: int, option_name: str):
        "Reset the value of a server config option"
        if not isinstance(guild_id, int):
            raise ValueError(f"Guild ID must be an integer, not {type(guild_id)}")
        if option_name not in (await self.get_options_list()):
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            return False
        if await self.db_delete_option(guild_id, option_name):
            if self.enable_caching and (guild_id, option_name) in self.cache:
                self.cache.pop((guild_id, option_name))
            return True
        return False

    async def reset_guild_config(self, guild_id: int):
        "Reset the config of a guild"
        if not self.bot.database_online:
            return False
        await self.db_delete_guild(guild_id)
        for option_name in (await self.get_options_list()):
            if self.enable_caching and (guild_id, option_name) in self.cache:
                self.cache.pop((guild_id, option_name))
        return True

    async def get_guild_config(self, guild_id: int, with_defaults: bool) -> dict[str, Any]:
        "Return the config of a guild"
        if not self.bot.database_online or (guild := self.bot.get_guild(guild_id)) is None:
            if with_defaults:
                return {option_name: option["default"] for option_name, option in (await self.get_options_list()).items()}
            return {}
        config = await self.db_get_guild(guild_id)
        if config is None:
            if with_defaults:
                return {option_name: option["default"] for option_name, option in (await self.get_options_list()).items()}
            return {}
        if with_defaults:
            for option_name, option in (await self.get_options_list()).items():
                if option_name not in config:
                    config[option_name] = option["default"]
                else:
                    config[option_name] = await from_raw(option_name, config[option_name], guild, self.bot)
        return config

    async def get_enum_usage_stats(self, option_id: str, ignored_guilds: list[int]):
        "Return stats on used languages"
        if not self.bot.database_online or "Languages" not in self.bot.cogs:
            return {}
        query = "SELECT `guild_id`, `value` FROM `serverconfig` WHERE `option_name` = 'language' AND `beta` = %s"
        values_list: list[str] = []
        guilds = {x.id for x in self.bot.guilds if x.id not in ignored_guilds}
        async with self.bot.db_main.read(query, (self.bot.beta,)) as query_results:
            for row in query_results:
                if row["guild_id"] in guilds:
                    values_list.append(row["value"])
        options_list = await self.get_options_list()
        for _ in range(len(guilds) - len(values_list)):
            values_list.append(options_list[option_id]["default"])
        langs: dict[str, int] = {}
        for lang in options_list[option_id]["values"]:
            langs[lang] = values_list.count(lang)
        return langs

    async def check_member_config_permission(self, member: discord.Member, option_name: str):
        "Check if a user has the required roles from a specific config"
        if option_name not in await self.get_options_list():
            raise ValueError(f"Option {option_name} does not exist")
        if (await self.get_options_list())[option_name]["type"] != "roles_list":
            raise ValueError(f"Option {option_name} is not a roles list")
        if not self.bot.database_online or not isinstance(member, discord.Member):
            return False
        raw_roles = await self.get_raw_option(member.guild.id, option_name)
        if raw_roles is None:
            return False
        roles_ids: list[int] = json.loads(raw_roles)
        member_role_ids = {role.id for role in member.roles}
        return any(role in member_role_ids for role in roles_ids)

    # ---- MEMBERCOUNTER CHANNELS ----

    @tasks.loop(minutes=1)
    async def update_every_membercounter(self):
        "Update all pending membercounter channels"
        if not self.bot.database_online:
            return
        i = 0
        now = time.time()
        for guild_id in await self.db_get_guilds_with_membercounter():
            if (guild := self.bot.get_guild(guild_id)) is None:
                continue
            if guild_id in self.membercounter_pending and self.membercounter_pending[guild_id] < now:
                del self.membercounter_pending[guild.id]
            if await self.update_memberchannel(guild):
                i += 1
        if i > 0:
            log_text = f"[MEMBERCOUNTER] {i} channels refreshed"
            emb = discord.Embed(description=log_text, color=5011628, timestamp=self.bot.utcnow())
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            self.bot.log.info(log_text)
            await self.bot.send_embed(emb, url="loop")

    @update_every_membercounter.error
    async def update_every_membercounter_error(self, error: Exception):
        "Error handler for the update_every_membercounter loop"
        self.bot.dispatch("error", error, "Membercounter update loop")

    async def update_memberchannel(self, guild: discord.Guild):
        "Update a membercounter channel for a specific guild"
        # If we already did an update recently: abort
        if guild.id in self.membercounter_pending:
            if self.membercounter_pending[guild.id] > time.time():
                return False
        channel = await self.get_option(guild.id, "membercounter")
        if channel is None:
            return False
        lang = await self.bot._(guild.id, "_used_locale")
        text = (await self.bot._(guild.id, "misc.membres")).capitalize()
        if lang == "fr":
            text += ' '
        text += ": "
        text += str(guild.member_count)
        if channel.name == text:
            return False
        try:
            await channel.edit(name=text, reason=await self.bot._(guild.id, "logs.reason.memberchan"))
            self.membercounter_pending[guild.id] = round(time.time()) + 5*60 # cooldown 5min
            return True
        except (discord.Forbidden, discord.NotFound):
            pass
        except Exception as err:
            self.bot.dispatch("error", err, f"Updating membercount channel {channel.id} in guild {guild.id}")
        return False

    # ---- DATABASE ACCESS ----

    async def db_get_value(self, guild_id: int, option_name: str) -> str | None:
        "Get a value from the database"
        if option_name not in (await self.get_options_list()):
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "SELECT `value` FROM `serverconfig` WHERE `guild_id` = %s AND `option_name` = %s AND `beta` = %s"
        async with self.bot.db_main.read(query, (guild_id, option_name, self.bot.beta), fetchone=True) as query_results:
            if len(query_results) == 0:
                return None
            return query_results["value"]

    async def db_get_guild(self, guild_id: int) -> dict[str, str] | None:
        "Get a guild from the database"
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "SELECT * FROM `serverconfig` WHERE `guild_id` = %s AND `beta` = %s"
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta)) as query_results:
            if len(query_results) == 0:
                return None
            return {row["option_name"]: row["value"] for row in query_results}

    async def db_set_value(self, guild_id: int, option_name: str, new_value: str) -> bool:
        "Edit a value in the database"
        if option_name not in (await self.get_options_list()):
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "INSERT INTO `serverconfig` (`guild_id`, `option_name`, `value`, `beta`) VALUES (%s, %s, %s, %s) "\
            "ON DUPLICATE KEY UPDATE `value` = %s"
        async with self.bot.db_main.write(query, (guild_id, option_name, new_value, self.bot.beta, new_value), returnrowcount=True
                                     ) as query_results:
            return query_results > 0

    async def db_delete_option(self, guild_id: int, option_name: str) -> bool:
        "Delete a value from the database"
        if option_name not in (await self.get_options_list()):
            raise ValueError(f"Option {option_name} does not exist")
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "DELETE FROM `serverconfig` WHERE `guild_id` = %s AND `option_name` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (guild_id, option_name, self.bot.beta), returnrowcount=True) as query_results:
            return query_results > 0

    async def db_delete_guild(self, guild_id: int) -> bool:
        "Delete a guild from the database"
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "DELETE FROM `serverconfig` WHERE `guild_id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (guild_id, self.bot.beta), returnrowcount=True) as query_results:
            return query_results > 0

    async def db_get_guilds_with_membercounter(self) -> list[int]:
        "Get a list of guilds with a membercounter"
        if not self.bot.database_online:
            raise RuntimeError("Database is offline")
        query = "SELECT `guild_id` FROM `serverconfig` WHERE `option_name` = 'membercounter' AND `beta` = %s"
        async with self.bot.db_main.read(query, (self.bot.beta,)) as query_results:
            return [row["guild_id"] for row in query_results]

    # ---- EDITION LOGS ----

    @commands.Cog.listener()
    async def on_config_edit(self, guild_id: int, user_id: int,
                             event_type: Literal["sconfig_option_set", "sconfig_option_reset", "sconfig_reset_all"],
                             data: dict[str, Any] | None):
        "Record a config edit event in the database"
        if len(event_type) > 64:
            raise ValueError("Event type cannot exceed 64 characters")
        query = "INSERT INTO `edition_logs` (`guild_id`, `user_id`, `type`, `data`, `origin`, `beta`) "\
            "VALUES (%s, %s, %s, %s, 'bot', %s)"
        async with self.bot.db_main.write(query, (guild_id, user_id, event_type, json.dumps(data), self.bot.beta)):
            pass


    # ---- COMMANDS ----

    async def option_name_autocomplete(self, current: str):
        "Autocompletion for an option name"
        filtered = sorted(
            (not name.startswith(current), name) for name, data in (await self.get_options_list()).items()
            if data["is_listed"] and current in name
        )
        return [
            app_commands.Choice(name=name, value=name)
            for _, name in filtered
        ][:25]

    config_main = app_commands.Group(
        name="config",
        description="Configure the bot on your server",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @config_main.command(name="set")
    @app_commands.describe(
        option="The option to modify",
        value="The new option value"
        )
    @app_commands.checks.cooldown(3, 8)
    async def config_set(self, interaction: discord.Interaction, option: str, *, value: str):
        "Set a server configuration option"
        if not self.bot.database_online:
            await interaction.response.send_message(
                await self.bot._(interaction, "cases.no_database"), ephemeral=True
            )
            return
        if (opt_data := (await self.get_options_list()).get(option)) is None:
            await interaction.response.send_message(
                await self.bot._(interaction, "server.option-notfound"), ephemeral=True
            )
            return
        if not opt_data["is_listed"]:
            await interaction.response.send_message(
                await self.bot._(interaction, "server.option-notfound"), ephemeral=True
            )
            return
        await interaction.response.defer()
        await self.config_set_cmd(interaction, option, value)

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
    @app_commands.checks.cooldown(3, 20)
    async def config_reset(self, interaction: discord.Interaction, option: str):
        "Reset an option to its initial value"
        if not self.bot.database_online:
            await interaction.response.send_message(
                await self.bot._(interaction, "cases.no_database"), ephemeral=True
            )
            return
        if (opt_data := (await self.get_options_list()).get(option)) is None:
            await interaction.response.send_message(
                await self.bot._(interaction, "server.option-notfound"), ephemeral=True
            )
            return
        if not opt_data["is_listed"]:
            await interaction.response.send_message(
                await self.bot._(interaction, "server.option-notfound"), ephemeral=True
            )
            return
        await interaction.response.defer()
        await self.reset_option(interaction.guild_id, option)
        await self.on_config_edit(interaction.guild_id, interaction.user.id, "sconfig_option_reset", {"option": option})
        await interaction.followup.send(await self.bot._(interaction, "server.value-deleted", option=option))
        # send internal log
        msg = f"Reset option in server {interaction.guild_id}: {option}"
        emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
        emb.set_footer(text=interaction.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)
        self.bot.log.debug(msg)

    @config_reset.autocomplete("option")
    async def sconfig_del_autocomplete(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    @config_main.command(name="reset-all")
    @app_commands.checks.cooldown(1, 60)
    async def config_reset_all(self, interaction: discord.Interaction):
        """Reset the whole config of your server.
        VERY DANGEROUS, NO ROLLBACK POSSIBLE"""
        if not self.bot.database_online:
            await interaction.response.send_message(
                await self.bot._(interaction, "cases.no_database"), ephemeral=True
            )
            return
        text = await self.bot._(interaction, "server.reset-all.confirmation")
        confirm_view = ConfirmView(
            self.bot, interaction,
            validation=lambda inter: inter.user == interaction.user,
            ephemeral=False,
            send_confirmation=False
            )
        await confirm_view.init()
        await interaction.response.send_message(text, view=confirm_view)
        await confirm_view.wait()
        if confirm_view.response_interaction:
            interaction = confirm_view.response_interaction
            await interaction.response.defer()
        await confirm_view.disable(interaction)
        if not confirm_view.value:
            return
        if await self.reset_guild_config(interaction.guild_id):
            await interaction.followup.send(await self.bot._(interaction, "server.reset-all.success"))
            # Send internal log
            await self.on_config_edit(interaction.guild_id, interaction.user.id, "sconfig_reset_all", None)
            msg = f"Reset all options in server {interaction.guild_id}"
            emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
            emb.set_footer(text=interaction.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)
            self.bot.log.info(msg)
        else:
            await interaction.followup.send(await self.bot._(interaction, "server.reset-all.error"))

    @config_main.command(name="list")
    @app_commands.checks.cooldown(1, 15)
    async def config_list(self, interaction: discord.Interaction):
        """Get the list of every usable option"""
        options = sorted((await self.get_options_list()).keys())
        txt = "\n```\n- {}\n```\n".format("\n- ".join(options))
        link = f"<https://{self.bot.doc_url}server.html#list-of-every-option>"
        await interaction.response.send_message(
            await self.bot._(interaction, "server.config-list", text=txt, link=link),
            ephemeral=True
        )

    @config_main.command(name="see")
    @app_commands.checks.cooldown(2, 10)
    async def config_see(self, interaction: discord.Interaction, option: str | None = None):
        """Displays the value of an option, or all options if none is specified"""
        if not self.bot.database_online:
            await interaction.response.send_message(
                await self.bot._(interaction, "cases.no_database"), ephemeral=True
            )
            return
        await interaction.response.defer()
        await self.send_online_user_tip(interaction)
        if option is None:
            await self.send_all_config(interaction.guild, interaction)
        else:
            await self.send_specific_config(interaction.guild, interaction, option)

    @config_see.autocomplete("option")
    async def sconfig_see_autocomplete(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    async def send_online_user_tip(self, interaction: discord.Interaction):
        "Send a tip about viewing the dashboard online"
        if not await self.bot.get_cog("Users").db_get_user_config(interaction.user.id, "show_tips"):
            # tips are disabled
            return
        if await self.bot.tips_manager.should_show_user_tip(interaction.user.id, UserTip.ONLINE_DASHBOARD_ACCESS):
            # user has not seen this tip yet
            domain = "axobeta.zrunner.me" if self.bot.beta else "axobot.xyz"
            await self.bot.tips_manager.send_user_tip(
                interaction,
                UserTip.ONLINE_DASHBOARD_ACCESS,
                url=f"https://{domain}/dashboard"
            )

    async def send_all_config(self, guild: discord.Guild, interaction: discord.Interaction):
        "Send the config lookup of a guild into a channel"
        if self.bot.zombie_mode:
            return
        _quit = await self.bot._(interaction.guild, "misc.quit")
        view = ServerConfigPaginator(self.bot, interaction.user, stop_label=_quit.capitalize(), guild=guild, cog=self)
        await view.send_init(interaction)
        if await view.wait():
            # only manually disable if it was a timeout (ie. not a user stop)
            await view.disable(interaction)

    async def send_specific_config(self, guild: discord.Guild, interaction: discord.Interaction, option: str):
        "Send the specific config value for guild into a channel"
        if self.bot.zombie_mode:
            return
        if (opt_data := (await self.get_options_list()).get(option)) is None:
            await interaction.followup.send(await self.bot._(interaction, "server.option-notfound"))
            return
        if not opt_data["is_listed"]:
            await interaction.followup.send(await self.bot._(interaction, "server.option-notfound"))
            return
        value = await self.get_option(guild.id, option)
        if (display := await to_display(option, value, guild, self.bot)) is None:
            display = "Ø"
        elif len(display) > 1024:
            display = display[:1023] + "…"
        title = await self.bot._(interaction, "server.opt_title", opt=option, guild=guild.name)
        description = await self.bot._(interaction, f"server.server_desc.{option}", value=display)
        embed = discord.Embed(title=title, color=self.embed_color, description=description)
        await interaction.followup.send(embed=embed)

    async def _get_set_success_message(self, interaction: discord.Interaction, option_name: str, value: Any):
        "Generate a proper success message when a setting is modified"
        option_type = (await self.get_options_list())[option_name]["type"]
        if option_type == "boolean":
            if value:
                return await self.bot._(interaction, "server.set_success.boolean.true", opt=option_name)
            else:
                return await self.bot._(interaction, "server.set_success.boolean.false", opt=option_name)
        if option_type == "levelup_channel":
            if value in {"none", "any", "dm"}:
                return await self.bot._(interaction, f"server.set_success.levelup_channel.{value}", opt=option_name)
            else:
                return await self.bot._(interaction,
                                        "server.set_success.levelup_channel.channel",
                                        opt=option_name, val=value.mention)
        str_value = await to_display(option_name, value, interaction.guild, self.bot)
        return await self.bot._(interaction, f"server.set_success.{option_type}", opt=option_name, val=str_value)

    async def _get_set_error_message(self, interaction: discord.Interaction, option_name: str, error: ValueError, _value: Any):
        "Generate a proper error message for an invalid value"
        option_data: AllRepresentation = error.args[2]
        if option_data["type"] in {"int", "float"}:
            return await self.bot._(interaction,
                                    f"server.set_error.{option_data['type']}_err",
                                    min=option_data["min"], max=option_data["max"])
        if option_data["type"] == "enum":
            translated_values = [
                await self.bot._(interaction, f"server.enum.{option_name}.{value}")
                for value in option_data["values"]
            ]
            return await self.bot._(interaction, "server.set_error.ENUM_INVALID", list=", ".join(translated_values))
        if option_data["type"] == "text":
            return await self.bot._(interaction,
                                    "server.set_error.text_err",
                                    min=option_data["min_length"], max=option_data["max_length"])
        error_name: str = error.args[1]
        if error_name in {"ROLES_TOO_FEW", "ROLES_TOO_MANY"}:
            return await self.bot._(interaction,
                                    "server.set_error.roles_list",
                                    min=option_data["min_count"], max=option_data["max_count"])
        if error_name in {"CHANNELS_TOO_FEW", "CHANNELS_TOO_MANY"}:
            return await self.bot._(interaction,
                                    "server.set_error.channels_list",
                                    min=option_data["min_count"], max=option_data["max_count"])
        if error_name in {"EMOJIS_TOO_FEW", "EMOJIS_TOO_MANY"}:
            if option_data["min_count"] == option_data["max_count"]:
                return await self.bot._(interaction, "server.set_error.emojis_list_exact", count=option_data["min_count"])
            return await self.bot._(interaction,
                                    "server.set_error.emojis_list",
                                    min=option_data["min_count"], max=option_data["max_count"])
        user_input = error.args[3] if len(error.args) > 3 else None
        return await self.bot._(interaction, "server.set_error." + error_name, input=user_input)

    async def config_set_cmd(self, interaction: discord.Interaction, option_name: str, raw_input: str):
        "Process the config_set command"
        if option_name not in (await self.get_options_list()):
            await interaction.followup.send(await self.bot._(interaction, "server.option-notfound"), ephemeral=True)
            return
        try:
            value = await from_input(option_name, raw_input, interaction.guild, interaction)
        except ValueError as err:
            if len(err.args) > 2:
                mentions = discord.AllowedMentions.none()
                await interaction.followup.send(
                    await self._get_set_error_message(interaction, option_name, err, raw_input),
                    allowed_mentions=mentions,
                    ephemeral=True
                )
            else:
                await interaction.followup.send(await self.bot._(interaction, "server.internal-error"), ephemeral=True)
            return
        await self.set_option(interaction.guild_id, option_name, value)
        await self.on_config_edit(interaction.guild_id, interaction.user.id, "sconfig_option_set",
                                  {"option": option_name, "value": await to_raw(option_name, value, self.bot)})
        check_embed = await check_config(self.bot, interaction.guild, option_name, value)
        await interaction.followup.send(
            await self._get_set_success_message(interaction, option_name, value),
            embed=check_embed
        )
        # send bot_warning tip
        if option_name in {"welcome_channel", "welcome_roles", "welcome"} and (serverlogs_cog := self.bot.get_cog("ServerLogs")):
            await serverlogs_cog.send_botwarning_tip(interaction)
        # Send internal log
        msg = f"Changed option in server {interaction.guild_id}: {option_name} = `{await to_raw(option_name, value, self.bot)}`"
        emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
        emb.set_footer(text=interaction.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)
        self.bot.log.debug(msg.replace('`', ''))


async def setup(bot: Axobot):
    await bot.add_cog(ServerConfig(bot))
