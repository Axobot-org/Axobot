import copy
import time
import typing
from math import ceil

import discord
import emoji
from cachingutils import LRUCache
from discord import app_commands
from discord.ext import commands

from libs.bot_classes import MyContext, Zbot
from libs.serverconfig import options_list as opt_list
from libs.serverconfig.autocomplete import autocomplete_main
from libs.serverconfig.config_paginator import ServerConfigPaginator
from libs.views import ConfirmView

from . import checks


class Servers(commands.Cog):
    """"Cog in charge of all the bot configuration management for your server. As soon as an option
    is searched, modified or deleted, this cog will handle the operations."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.default_language = 'en'
        self.embed_color = discord.Colour(0x3fb9ef)
        self.log_color = 1793969
        self.file = "servers"
        self.cache: LRUCache = LRUCache(max_size=10000, timeout=3600)
        self.raids_levels = ["None", "Smooth", "Careful", "High", "(╯°□°）╯︵ ┻━┻"]
        self.options_list = [
            "prefix", "language", "description", "clear_allowed_roles", "slowmode_allowed_roles", "mute_allowed_roles",
            "kick_allowed_roles", "ban_allowed_roles", "warn_allowed_roles", "say_allowed_roles", "welcome_channel",
            "welcome", "leave", "welcome_roles", "anti_scam", "poll_channels", "partner_channel", "partner_color",
            "partner_role", "modlogs_channel", "nicknames_history", "enable_xp", "levelup_msg", "levelup_channel",
            "noxp_channels", "xp_rate", "xp_type", "anti_caps_lock", "enable_fun", "membercounter", "anti_raid",
            "vote_emojis", "morpion_emojis", "help_in_dm", "compress_help", "muted_role", "voice_roles", "voice_channel",
            "voice_category", "voice_channel_format", "ttt_display", "bot_news", "update_mentions", "streaming_channel",
            "stream_mention", "streaming_role",
        ]
        self.membercounter_pending: dict[int, int] = {}
        self.max_members_for_nicknames = 3000

    async def clear_cache(self):
        self.cache._items.clear()

    async def get_bot_infos(self, bot_id: int):
        """Return every options of the bot"""
        if not self.bot.database_online:
            return list()
        query = ("SELECT * FROM `bot_infos` WHERE `ID`={}".format(bot_id))
        async with self.bot.db_query(query) as query_results:
            liste = list(query_results)
        return liste

    async def edit_bot_infos(self, bot_id: int, values=[()]):
        if not isinstance(values, list):
            raise ValueError
        set_query = ', '.join('{}=%s'.format(val[0]) for val in values)
        query = f"UPDATE `bot_infos` SET {set_query} WHERE `ID`='{bot_id}'"
        async with self.bot.db_query(query, (val[1] for val in values)):
            pass
        return True

    async def get_languages(self, ignored_guilds: typing.List[int], return_dict: bool = False):
        """Return stats on used languages"""
        if not self.bot.database_online or not 'Languages' in self.bot.cogs:
            return []
        query = "SELECT `language`,`ID` FROM `servers` WHERE `beta` = %s"
        liste = []
        guilds = {x.id for x in self.bot.guilds if x.id not in ignored_guilds}
        async with self.bot.db_query(query, (self.bot.beta,)) as query_results:
            for row in query_results:
                if row['ID'] in guilds:
                    liste.append(row['language'])
        for _ in range(len(guilds)-len(liste)):
            liste.append(self.bot.get_cog('Languages').languages.index(self.default_language))
        if return_dict:
            langs = {}
            for e, lang in enumerate(self.bot.get_cog('Languages').languages):
                langs[lang] = liste.count(e)
        else:
            langs = []
            for e, lang in enumerate(self.bot.get_cog('Languages').languages):
                langs.append((lang, liste.count(e)))
        return langs

    async def get_xp_types(self, ignored_guilds: typing.List[int], return_dict: bool = False):
        "Return stats on used xp types"
        if not self.bot.database_online:
            return []
        query = "SELECT `xp_type`,`ID` FROM `servers` WHERE `beta` = %s"
        liste = []
        guilds = {x.id for x in self.bot.guilds if x.id not in ignored_guilds}
        async with self.bot.db_query(query, (self.bot.beta,)) as query_results:
            for row in query_results:
                if row['ID'] in guilds:
                    liste.append(row['xp_type'])
        for _ in range(len(guilds)-len(liste)):
            liste.append(opt_list.default_values['xp_type'])
        if return_dict:
            types = {}
            for e, name in enumerate(self.bot.get_cog('Xp').types):
                types[name] = liste.count(e)
        else:
            types = []
            for e, name in enumerate(self.bot.get_cog('Xp').types):
                types.append((name, liste.count(e)))
        return types

    async def staff_finder(self, user: discord.Member, option: str):
        """Check is user is part of a staff"""
        if option not in opt_list.roles_options:
            raise TypeError
        if await self.bot.get_cog('Admin').check_if_god(user):
            return True
        if not self.bot.database_online or not isinstance(user, discord.Member):
            return False
        staff = str(await self.get_option(user.guild.id,option)).split(";")
        staff = [x for x in staff if len(x) > 10 and x.isnumeric()]
        if len(staff) == 0:
            return False
        for r in user.roles:
            if str(r.id) in staff:
                return True
        raise commands.CommandError("User doesn't have required roles")

    async def get_option(self, guild_id: typing.Union[discord.Guild, int], option_name: str) -> typing.Optional[str]:
        """return the value of an option
        Return None if this option doesn't exist or if no value has been set (like if the guild isn't in the database)"""
        if isinstance(guild_id, discord.Guild):
            guild_id = guild_id.id
        elif guild_id is None or not self.bot.database_online:
            return None
        if (cached := self.cache.get((guild_id, option_name))) is not None:
            return cached
        sql_result = await self.get_server([option_name],criters=["ID="+str(guild_id)],return_type=list)
        if len(sql_result) == 0:
            value = None
        elif sql_result[0][0] == '':
            if option_name == "nicknames_history":
                value = None
            else:
                value = opt_list.default_values[option_name]
        else:
            value = sql_result[0][0]
        if value is None and option_name == "nicknames_history" and (guild := self.bot.get_guild(guild_id)):
            value = len(guild.members) < self.max_members_for_nicknames
        self.cache[(guild_id, option_name)] = value
        return value

    async def get_server(self, columns=[], criters=["ID > 1"], relation="AND", return_type=dict):
        """return every options of a server"""
        await self.bot.wait_until_ready()
        if not isinstance(columns, list) or not isinstance(criters, list):
            raise ValueError
        if len(columns) == 0:
            cl = "*"
        else:
            cl = "`"+"`,`".join(columns)+"`"
        relation = " "+relation+" "
        query = ("SELECT {} FROM `servers` WHERE `beta` = %s AND {}".format(cl, relation.join(criters)))
        liste = list()
        async with self.bot.db_query(query, (self.bot.beta,), astuple=(return_type!=dict)) as query_results:
            for row in query_results:
                if isinstance(row, dict):
                    for k, v in row.items():
                        if v == '':
                            row[k] = opt_list.default_values.get(k, None)
                liste.append(row)
        return liste

    async def modify_server(self, guild_id: int, values=None):
        """Update a server config in the database"""
        if values is not None and not isinstance(values, list):
            raise ValueError
        if values is None:
            values = [()]
        set_query = ', '.join(f'`{val[0]}`=%s' for val in values)
        query = f"UPDATE `servers` SET {set_query} WHERE `ID`=%s AND `beta` = %s"
        async with self.bot.db_query(query, tuple(val[1] for val in values) + (guild_id, self.bot.beta)):
            pass
        for value in values:
            self.cache[(guild_id, value[0])] = value[1]
        return True

    async def delete_option(self, guild_id: int, opt):
        """Reset an option"""
        if opt not in opt_list.default_values:
            raise ValueError
        value = opt_list.default_values[opt]
        if opt == 'language':
            await self.bot.get_cog('Languages').change_cache(guild_id,value)
        elif opt == 'prefix':
            await self.bot.prefix_manager.update_prefix(guild_id,value)
        return await self.modify_server(guild_id,values=[(opt,value)])

    async def add_server(self, guild_id: int):
        """add a new server to the db"""
        if isinstance(guild_id, str):
            if not guild_id.isnumeric():
                raise ValueError
        query = "INSERT INTO `servers` (`ID`, `beta`) VALUES (%s, %s)"
        async with self.bot.db_query(query, (guild_id, self.bot.beta)):
            pass
        return True

    async def create_row_if_needed(self, guild_id: int):
        """Check if a server is already in the db"""
        i = await self.get_option(guild_id, "ID")
        if i is None:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                raise Exception("Guild not found")
            emb_desc = f"New server in the database :tada: `{guild.name}` ({guild.id})"
            emb = discord.Embed(description=emb_desc, color=self.log_color, timestamp=self.bot.utcnow())
            await self.bot.send_embed(emb)
            return await self.add_server(guild_id)
        return True

    async def delete_server(self, guild_id: int):
        """remove a server from the db"""
        if not isinstance(guild_id, int):
            raise ValueError
        query = f"DELETE FROM `servers` WHERE `ID` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta)):
            pass
        return True


    async def option_name_autocomplete(self, current: str):
        "Autocompletion for an option name"
        blacklisted_autocomplete = {'bot_news', 'update_mentions'}
        filtered = sorted(
            (not option.startswith(current), option) for option in self.options_list
            if option not in blacklisted_autocomplete and current in option
        )
        return [
            app_commands.Choice(name=value[1], value=value[1])
            for value in filtered
        ][:25]

    @commands.hybrid_group(name='config')
    @discord.app_commands.default_permissions(manage_guild=True)
    @commands.guild_only()
    async def sconfig_main(self, ctx: MyContext):
        """Function for setting the bot on a server

..Doc server.html#config-options"""
        if ctx.invoked_subcommand is None:
            subcommand_passed = ctx.message.content.replace(ctx.prefix+"config", "").strip()
            if subcommand_passed == "":
                await ctx.send_help("config")
                return
            msg = copy.copy(ctx.message)
            if subcommand_passed.isnumeric():
                msg.content = ctx.prefix + "config see " + subcommand_passed
            elif subcommand_passed.split(" ")[0] in self.options_list:
                if len(subcommand_passed.split(" "))==1:
                    msg.content = ctx.prefix + "config see " + subcommand_passed
                else:
                    msg.content = ctx.prefix + "config change " + subcommand_passed
            else:
                msg.content = ctx.prefix + "config help"
            new_ctx = await self.bot.get_context(msg)
            await self.bot.invoke(new_ctx)

    @sconfig_main.command(name="reset")
    @app_commands.describe(option="The option to reset")
    @commands.cooldown(1, 2, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def sconfig_del(self, ctx: MyContext, option: str):
        """Reset an option to its initial value"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,"cases.no_database"))
        await self.sconfig_del2(ctx, option)

    @sconfig_del.autocomplete("option")
    async def sconfig_del_autocomplete(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    @sconfig_main.command(name="change")
    @app_commands.describe(
        option="The option to modify",
        value="The new option value"
        )
    @commands.cooldown(1, 2, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def sconfig_change(self, ctx: MyContext, option:str, *, value: str):
        """Allows you to modify an option"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,"cases.no_database"))
        await self.create_row_if_needed(ctx.guild.id)
        if option in opt_list.roles_options:
            await self.conf_roles(ctx, option, value)
        elif option in opt_list.bool_options:
            await self.conf_bool(ctx, option, value)
        elif option in opt_list.textchannels_options:
            await self.conf_textchan(ctx, option, value)
        elif option in opt_list.category_options:
            await self.conf_category(ctx, option, value)
        elif option in opt_list.text_options:
            await self.conf_text(ctx, option, value)
        elif option in opt_list.numb_options:
            await self.conf_numb(ctx, option, value)
        elif option in opt_list.voicechannels_options:
            await self.conf_vocal(ctx, option, value)
        elif option == "language":
            await self.conf_lang(ctx, option, value)
        elif option in opt_list.prefix_options:
            await self.conf_prefix(ctx, option, value)
        elif option in opt_list.raid_options:
            await self.conf_raid(ctx, option, value)
        elif option in opt_list.emoji_option:
            await self.conf_emoji(ctx, option, value)
        elif option in opt_list.xp_type_options:
            await self.conf_xp_type(ctx, option, value)
        elif option in opt_list.color_options:
            await self.conf_color(ctx, option, value)
        elif option in opt_list.xp_rate_option:
            await self.conf_xp_rate(ctx, option, value)
        elif option in opt_list.levelup_channel_option:
            await self.conf_levelup_chan(ctx, option, value)
        elif option in opt_list.ttt_display_option:
            await self.conf_tttdisplay(ctx, option, value)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
            return

    @sconfig_change.autocomplete("option")
    async def sconfig_change_autocomplete_opt(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    @sconfig_change.autocomplete("value")
    async def sconfig_change_autocomplete_value(self, interaction: discord.Interaction, value: str):
        return await autocomplete_main(self.bot, interaction, interaction.namespace.option, value)

    @sconfig_main.command(name="reset-all")
    @commands.guild_only()
    @commands.check(checks.has_admin)
    async def admin_delete(self, ctx: MyContext):
        """Reset the whole config of your server
        VERY DANGEROUS, NO ROLLBACK POSSIBLE"""
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
        if await self.delete_server(ctx.guild.id):
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

    async def sconfig_del2(self, ctx: MyContext, option: str):
        "Reset an option for a given guild"
        try:
            if await self.delete_option(ctx.guild.id,option):
                msg = await self.bot._(ctx.guild.id, "server.value-deleted", option=option)
            else:
                await ctx.send(await self.bot._(ctx.guild.id, "server.internal-error"))
                return
            await ctx.send(msg)
            msg = f"Reset option in server {ctx.guild.id}: {option}"
            emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
            emb.set_footer(text=ctx.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)
            self.bot.log.debug(msg)
        except ValueError:
            await ctx.send(await self.bot._(ctx.guild.id, "server.option-notfound"))
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)

    async def send_embed(self, guild: discord.Guild, option: str, value: str):
        "Send a log embed into the private logs channel when an option is edited"
        msg = f"Changed option in server {guild.id}: {option} = `{value}`"
        emb = discord.Embed(description=msg, color=self.log_color, timestamp=self.bot.utcnow())
        emb.set_footer(text=guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)
        self.bot.log.debug(msg)


    async def get_guild(self, item) -> discord.Guild:
        """Try to find a guild from anything (int, guild, ctx, str)"""
        guild = None
        if isinstance(item, commands.Context):
            guild = item.guild
        elif isinstance(item, discord.Guild):
            guild = item
        elif isinstance(item, str):
            if item.isnumeric():
                guild = self.bot.get_guild(int(item))
        elif isinstance(item, int):
            guild = self.bot.get_guild(item)
        return guild

    async def conf_roles(self, ctx: MyContext, option: str, value: str):
        guild = await self.get_guild(ctx)
        ext = not isinstance(ctx, commands.Context)
        if value == "scret-desc":
            roles = await self.get_option(guild.id,option)
            return await self.form_roles(guild, roles, ext)
        else:
            roles = value.split(",")
            liste = list()
            liste2 = list()
            for role in roles:
                role = role.strip()
                try:
                    if role == "everyone":
                        r = guild.default_role
                    else:
                        r = await commands.RoleConverter().convert(ctx,role)
                except commands.errors.BadArgument:
                    msg = await self.bot._(guild.id, "server.edit-error.role", name=role)
                    await ctx.send(msg)
                    return
                if str(r.id) in liste:
                    continue
                liste.append(str(r.id))
                liste2.append(r.mention)
            await self.modify_server(guild.id,values=[(option,";".join(liste))])
            msg = await self.bot._(guild.id, "server.edit-success.role", opt=option, val=", ".join(liste2))
            await ctx.send(msg)
            await self.send_embed(guild, option, value)

    async def form_roles(self, guild: discord.Guild, roles: str, ext: bool=False):
        if not isinstance(roles,int):
            if (roles is None or len(roles) == 0):
                return "Ø"
            roles = roles.split(";")
        else:
            roles = [roles]
        g_roles = list()
        for r in roles:
            g_role = guild.get_role(int(r))
            if g_role is None:
                g_roles.append('<' + await self.bot._(guild, "server.deleted-role") + '>')
            elif ext:
                g_roles.append("@"+g_role.name)
            else:
                g_roles.append(g_role.mention)
        return g_roles

    async def conf_bool(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            v = await self.get_option(guild.id, option)
            if option == "nicknames_history" and v is None:
                v = len(ctx.guild.members) < self.max_members_for_nicknames
            return await self.form_bool(v)
        else:
            if value.lower() in {"true","vrai","1","oui","yes","activé"}:
                value = True
                v = 1
            elif value.lower() in {"false","faux","non","no","désactivé","wrong",'0'}:
                value = False
                v = 0
            else:
                msg = await self.bot._(ctx.guild.id, "server.edit-error.boolean", name=option)
                await ctx.send(msg)
                return
            await self.modify_server(ctx.guild.id,values=[(option,v)])
            msg = await self.bot._(ctx.guild.id, "server.edit-success.boolean", opt=option, val=value)
            await ctx.send(msg)
            await self.send_embed(ctx.guild, option, value)

    async def form_bool(self, boolean):
        if boolean == 1:
            v = True
        else:
            v = False
        return v

    async def conf_textchan(self, ctx: MyContext, option: str, value: str):
        guild = await self.get_guild(ctx)
        ext = not isinstance(ctx, commands.Context)
        if value == "scret-desc":
            chans = await self.get_option(guild.id,option)
            return await self.form_textchan(guild, chans, ext)
        else:
            chans = value.split(",")
            liste = list()
            liste2 = list()
            for chan in chans:
                chan = chan.strip()
                if len(chan) == 0:
                    continue
                try:
                    c = await commands.TextChannelConverter().convert(ctx,chan)
                except commands.errors.BadArgument:
                    msg = await self.bot._(guild.id, "server.edit-error.channel", channel=chan)
                    await ctx.send(msg)
                    return
                if str(c.id) in liste:
                    continue
                liste.append(str(c.id))
                liste2.append(c.mention)
            await self.modify_server(guild.id,values=[(option,";".join(liste))])
            if option=='noxp_channels':
                self.bot.get_cog('Xp').xp_channels_cache[guild.id] = [int(x) for x in liste]
            msg = await self.bot._(guild.id, "server.edit-success.channel", opt=option, val=", ".join(liste2))
            await ctx.send(msg)
            await self.send_embed(guild, option, value)

    async def form_textchan(self, guild: discord.Guild, chans: str, ext=False):
        if len(chans) == 0:
            return "Ø"
        chans = chans.split(";")
        g_chans = list()
        for r in chans:
            g_chan = guild.get_channel_or_thread(int(r))
            if g_chan is None:
                g_chans.append('<' + await self.bot._(guild, "server.deleted-channel") + '>')
            elif ext:
                g_chans.append("#"+g_chan.name)
            else:
                g_chans.append(g_chan.mention)
        return g_chans
    
    async def conf_category(self, ctx: MyContext, option: str, value: str):
        guild = await self.get_guild(ctx)
        ext = not isinstance(ctx, commands.Context)
        if value == "scret-desc":
            chans = await self.get_option(guild.id,option)
            return await self.form_category(guild, chans, ext)
        else:
            chans = value.split(",")
            liste = list()
            liste2 = list()
            for chan in chans:
                chan = chan.strip()
                if len(chan) == 0:
                    continue
                try:
                    c = await commands.CategoryChannelConverter().convert(ctx, chan)
                except commands.errors.BadArgument:
                    msg = await self.bot._(guild.id, "server.edit-error.category", name=chan)
                    await ctx.send(msg)
                    return
                if str(c.id) in liste:
                    continue
                liste.append(str(c.id))
                liste2.append(c.name)
            await self.modify_server(guild.id, values=[(option, ";".join(liste))])
            msg = await self.bot._(guild.id, "server.edit-success.category", opt=option, val=", ".join(liste2))
            await ctx.send(msg)
            await self.send_embed(guild, option, value)

    async def form_category(self, guild: discord.Guild, chans: str, _=False):
        if len(chans) == 0:
            return "Ø"
        chans = chans.split(";")
        g_chans = list()
        for r in chans:
            g_chan = guild.get_channel(int(r))
            if g_chan is None:
                g_chans.append('<' + await self.bot._(guild, "server.deleted-channel") + '>')
            else:
                g_chans.append(g_chan.name)
        return g_chans

    async def conf_emoji(self, ctx: MyContext, option: str, value: str):
        guild = await self.get_guild(ctx)
        if value == "scret-desc":
            emojis = await self.get_option(guild.id,option)
            return ' '.join(await self.form_emoji(emojis, option))
        else:
            emojis = value.split(',') if ',' in value else value.split(' ')
            liste = []
            liste2 = []
            for e in emojis:
                e = e.strip()
                if len(e) == 0:
                    continue
                try:
                    e = await commands.EmojiConverter().convert(ctx,e)
                except commands.errors.BadArgument:
                    if e not in self.bot.emojis_manager.unicode_set:
                        msg = await self.bot._(ctx.guild.id, "server.edit-error.emoji", emoji=e)
                        await ctx.send(msg)
                        return
                    if emoji.demojize(e) not in liste:
                        liste.append(emoji.demojize(e))
                        liste2.append(e)
                else:
                    if str(e.id) not in liste:
                        liste.append(str(e.id))
                        liste2.append("<:{}:{}>".format(e.name,e.id))
            await self.modify_server(ctx.guild.id,values=[(option,";".join(liste))])
            msg = await self.bot._(ctx.guild.id, "server.edit-success.emojis", opt=option, val=", ".join(liste2))
            await ctx.send(msg)
            await self.send_embed(ctx.guild, option, value)

    async def form_emoji(self, emojis: str, option: str):
        if len(emojis) == 0:
            emojis = opt_list.default_values[option]
        emojis = emojis.split(";")
        l_em = list()
        for r in emojis:
            if len(r) == 0:
                continue
            if r.isnumeric():
                d_em = discord.utils.get(self.bot.emojis, id=int(r))
                if d_em is None:
                    l_em.append("?")
                else:
                    a = 'a' if d_em.animated else ''
                    l_em.append("<{}:{}:{}>".format(a, d_em.name, d_em.id))
            else:
                l_em.append(emoji.emojize(r, language="alias"))
        return l_em

    async def conf_vocal(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            chans = await self.get_option(guild.id,option)
            return await self.form_vocal(guild,chans)
        else:
            chans = value.split(",")
            liste = list()
            liste2 = list()
            for chan in chans:
                chan = chan.strip()
                try:
                    c = await commands.VoiceChannelConverter().convert(ctx,chan)
                except commands.errors.BadArgument:
                    msg = await self.bot._(ctx.guild.id, "server.edit-error.channel", channel=chan)
                    await ctx.send(msg)
                    return
                if str(c.id) in liste:
                    continue
                liste.append(str(c.id))
                liste2.append(c.mention)
            await self.modify_server(ctx.guild.id,values=[(option,";".join(liste))])
            msg = await self.bot._(ctx.guild.id, "server.edit-success.channel", opt=option, val=", ".join(liste2))
            await ctx.send(msg)
            await self.send_embed(ctx.guild, option, value)

    async def form_vocal(self, guild: discord.Guild, chans: str):
        if len(chans) == 0:
            return "Ø"
        chans = chans.split(";")
        g_chans = list()
        for r in chans:
            g_chan = discord.utils.get(guild.voice_channels, id=int(r))
            if g_chan is None:
                g_chans.append('<' + await self.bot._(guild, "server.deleted-channel") + '>')
            else:
                g_chans.append(g_chan.mention)
        return g_chans

    async def conf_text(self, ctx: MyContext, option: str, value: str):
        guild = await self.get_guild(ctx)
        if value == "scret-desc":
            text = await self.get_option(guild.id,option)
            return await self.form_text(text)
        else:
            await self.modify_server(guild.id,values=[(option, value)])
            msg = await self.bot._(guild.id, "server.edit-success.text", opt=option, val=value)
            await ctx.send(msg)
            await self.send_embed(guild, option, value)

    async def form_text(self, text: str):
        if len(text) == 0:
            text = "Ø"
        elif len(text) > 1000:
            text = "```\n" + text[:1000] + "...```"
        else:
            text = "```\n" + text + "```"
        return text

    async def conf_prefix(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            text = await self.get_option(guild.id,'prefix')
            return await self.form_prefix(text)
        else:
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            if len(value) > 10:
                await ctx.send(await self.bot._(ctx.guild.id, "server.edit-error.prefix.long"))
                return
            try:
                await self.modify_server(ctx.guild.id,values=[('prefix',value)])
            except Exception:
                self.bot.log.warning("Error while editing prefix", exc_info=True)
                await ctx.send(await self.bot._(ctx.guild.id,"server.edit-error.prefix.invalid"))
                return
            await self.bot.prefix_manager.update_prefix(ctx.guild.id,value)
            msg = await self.bot._(ctx.guild.id, "server.edit-success.prefix", val=value)
            await ctx.send(msg)
            await self.send_embed(ctx.guild, option, value)

    async def form_prefix(self, text: str):
        if len(text) == 0:
            text = "!"
        return '`'+text+'`'

    async def conf_numb(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            return await self.get_option(guild.id,option)
        else:
            if value.isnumeric():
                value = int(value)
                await self.send_embed(ctx.guild, option, value)
            else:
                msg = await self.bot._(ctx.guild.id, "server.edit-error.numeric", name=option)
                await ctx.send(msg.format(option))

    async def conf_lang(self, ctx: MyContext, option: str,value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            if guild is None:
                return self.default_language
            v = await self.get_option(guild,option)
            return await self.form_lang(v)
        else:
            languages = self.bot.get_cog("Languages").languages
            if value in languages:
                v = languages.index(value)
                await self.modify_server(ctx.guild.id,values=[(option,v)])
                await self.bot.get_cog('Languages').change_cache(ctx.guild.id,value)
                msg = await self.bot._(ctx.guild.id, "server.edit-success.lang", val=value)
                await ctx.send(msg)
                await self.send_embed(ctx.guild, option, value)
            else:
                msg = await self.bot._(ctx.guild.id,"server.edit-error.lang", list=", ".join(languages))
                await ctx.send(msg)

    async def form_lang(self, value: str):
        if value is None:
            return self.default_language
        else:
            return self.bot.get_cog("Languages").languages[value]

    async def conf_raid(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            if guild is None:
                return opt_list.default_values['anti_raid']
            v = await self.get_option(guild,option)
            return await self.form_raid(v)
        else:
            raids = self.raids_levels
            value = value.capitalize()
            if value.isnumeric():
                value = int(value)
                if value in range(0,len(raids)):
                    value = raids[value]
            if value in raids:
                v = raids.index(value)
                await self.modify_server(ctx.guild.id,values=[(option,v)])
                msg = await self.bot._(ctx.guild.id, "server.edit-success.raid", name=value, index=raids.index(value))
                await ctx.send(msg)
                await self.send_embed(ctx.guild, option, value)
            else:
                msg = await self.bot._(ctx.guild.id,"server.edit-error.anti_raid", list=", ".join(raids))
                await ctx.send(msg)

    async def form_raid(self, value: str):
        if value is None:
            return opt_list.default_values['anti_raid']
        else:
            return self.raids_levels[value]

    async def conf_xp_type(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            if guild is None:
                return self.bot.get_cog('Xp').types[0]
            v = await self.get_option(guild,option)
            return await self.form_xp_type(v)
        else:
            available_types = self.bot.get_cog("Xp").types
            if value in available_types:
                v = available_types.index(value)
                await self.modify_server(ctx.guild.id,values=[(option,v)])
                msg = await self.bot._(ctx.guild.id, "server.edit-success.xp", val=value)
                await ctx.send(msg)
                await self.send_embed(ctx.guild, option, value)
            else:
                msg = await self.bot._(ctx.guild.id, "server.edit-error.xp", list=", ".join(available_types))
                await ctx.send(msg)

    async def form_xp_type(self, value: str):
        if value is None:
            return self.bot.get_cog('Xp').types[0]
        else:
            return self.bot.get_cog("Xp").types[value]

    async def conf_color(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            if guild is None:
                return str(discord.Colour(opt_list.default_values[option]))
            v = await self.get_option(guild,option)
            return await self.form_color(option,v)
        else:
            try:
                if value=="default":
                    color = discord.Color(opt_list.default_values[option])
                else:
                    color = await commands.ColourConverter().convert(ctx,value)
            except commands.errors.BadArgument:
                msg = await self.bot._(ctx.guild.id, "server.edit-error.color")
                await ctx.send(msg)
                return
            await self.modify_server(ctx.guild.id,values=[(option,color.value)])
            msg = await self.bot._(ctx.guild.id, "server.edit-success.color", opt=option, val=color)
            if ctx.can_send_embed:
                await ctx.send(embed=discord.Embed(description=msg, colour=color))
            else:
                await ctx.send(msg)
            await self.send_embed(ctx.guild,option,color)

    async def form_color(self, option: str, value: str):
        if value is None:
            return str(discord.Colour(opt_list.default_values[option]))
        else:
            return str(discord.Colour(value))
    
    async def conf_xp_rate(self, ctx: MyContext, option: str, value: str):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            return await self.get_option(guild.id,option)
        else:
            try:
                value = round(float(value),2)
            except ValueError:
                msg = await self.bot._(ctx.guild.id, "server.edit-error.numeric", name=option)
                await ctx.send(msg)
                return
            if value < 0.1 or value > 3:
                await ctx.send(await self.bot._(ctx.guild.id, "server.edit-error.xp_rate", min=0.1, max=3))
                return
            await self.modify_server(ctx.guild.id,values=[(option,value)])
            await ctx.send(await self.bot._(ctx.guild.id, "server.edit-success.xp_rate",val=value))
            await self.send_embed(ctx.guild, option, value)
    
    async def form_xp_rate(self, option: str, value: str):
        if value is None:
            return opt_list.default_values[option]
        else:
            return value

    async def conf_levelup_chan(self, ctx: MyContext, option: str, value: str):
        guild = await self.get_guild(ctx)
        ext = not isinstance(ctx, commands.Context)
        if value == "scret-desc":
            chan = await self.get_option(guild.id,option)
            if chan is None:
                chan = opt_list.default_values[option]
            return await self.form_levelup_chan(guild, chan, ext)
        else:
            if value.lower() in {"any", "tout", "tous", "current", "all", "any channel"}:
                c_id = "any"
                msg = await self.bot._(guild.id,"server.edit-success.levelup_channel.any")
            elif value.lower() in {"none", "aucun", "disabled", "nowhere"}:
                c_id = "none"
                msg = await self.bot._(guild.id,"server.edit-success.levelup_channel.none")
            else:
                chan = value.strip()
                try:
                    c = await commands.TextChannelConverter().convert(ctx,chan)
                except commands.errors.BadArgument:
                    msg = await self.bot._(guild.id, "server.edit-error.channel", channel=chan)
                    await ctx.send(msg)
                    return
                msg = await self.bot._(guild.id, "server.edit-success.levelup_channel.chan", val=c.mention)
                c_id = c.id
            await self.modify_server(guild.id,values=[(option,c_id)])
            await ctx.send(msg)
            await self.send_embed(guild, option, value)

    async def form_levelup_chan(self, guild: discord.Guild, value: str, ext: bool=False):
        if value == "any":
            return "Any channel"
        if value == "none":
            return "Nowhere"
        if value.isnumeric():
            g_chan = guild.get_channel_or_thread(int(value))
            if g_chan is None:
                return '<' + await self.bot._(guild, "server.deleted-channel") + '>'
            elif ext:
                return "#"+g_chan.name
            else:
                return g_chan.mention
        return ""

    async def conf_tttdisplay(self, ctx: MyContext, option: str, value: int):
        if value == "scret-desc":
            guild = await self.get_guild(ctx)
            if guild is None:
                return self.bot.get_cog('Morpions').types[0]
            v = await self.get_option(guild, option)
            return await self.form_tttdisplay(v)
        else:
            available_types: list[str] = self.bot.get_cog("Morpions").types
            value = value.lower()
            if value in available_types:
                v = available_types.index(value)
                await self.modify_server(ctx.guild.id,values=[(option,v)])
                msg = await self.bot._(ctx.guild.id, "server.edit-success.tttdisplay", val=value)
                await ctx.send(msg)
                await self.send_embed(ctx.guild, option, value)
            else:
                msg = await self.bot._(ctx.guild.id, "server.edit-error.tttdisplay", list=", ".join(available_types))
                await ctx.send(msg)

    async def form_tttdisplay(self, value: int):
        if value is None:
            return self.bot.get_cog('Morpions').types[0].capitalize()
        else:
            return self.bot.get_cog("Morpions").types[value].capitalize()

    @sconfig_main.command(name='list')
    async def sconfig_list(self, ctx: MyContext):
        """Get the list of every usable option"""
        options = sorted(self.options_list)
        txt = "\n```\n-{}\n```\n".format('\n-'.join(options))
        link = "<https://zbot.readthedocs.io/en/latest/server.html#list-of-every-option>"
        await ctx.send(await self.bot._(ctx.guild.id, "server.config-list",
                                        text=txt, link=link))

    @sconfig_main.command(name="see")
    @commands.cooldown(1,10,commands.BucketType.guild)
    @commands.guild_only()
    async def sconfig_see(self, ctx: MyContext, option: typing.Optional[str]=None):
        """Displays the value of an option, or all options if none is specified"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,"cases.no_database"))
        await self.send_see(ctx.guild, ctx, option, ctx.message)

    @sconfig_see.autocomplete("option")
    async def sconfig_see_autocomplete(self, _: discord.Interaction, option: str):
        return await self.option_name_autocomplete(option)

    async def send_see(self, guild: discord.Guild, ctx: MyContext, option: str, msg: discord.Message):
        """Envoie l'embed dans un salon"""
        if self.bot.zombie_mode:
            return
        if option is None:
            option = "1"
        if option.isnumeric():
            page = int(option)
            if page < 1:
                return await ctx.send(await self.bot._(ctx.channel, "xp.low-page"))
            _quit = await self.bot._(ctx.guild, "misc.quit")
            view = ServerConfigPaginator(self.bot, ctx.author, stop_label=_quit.capitalize(), guild=guild, cog=self)
            await view.send_init(ctx)
            return
        elif ctx is not None:
            if option in opt_list.roles_options:
                r = await self.conf_roles(ctx, option, 'scret-desc')
                r = ", ".join(r)
            elif option in opt_list.bool_options:
                r = str(await self.conf_bool(ctx, option, 'scret-desc'))
            elif option in opt_list.textchannels_options:
                r = await self.conf_textchan(ctx, option, 'scret-desc')
                r = ", ".join(r)
            elif option in opt_list.category_options:
                r = await self.conf_category(ctx, option, 'scret-desc')
                r = ', '.join(r)
            elif option in opt_list.text_options:
                r = await self.conf_text(ctx, option, 'scret-desc')
            elif option in opt_list.numb_options:
                r = await self.conf_numb(ctx, option, 'scret-desc')
            elif option in opt_list.voicechannels_options:
                r = await self.conf_vocal(ctx, option, 'scret-desc')
                r = ", ".join(r)
            elif option == "language":
                r = await self.conf_lang(ctx, option, 'scret-desc')
            elif option in opt_list.prefix_options:
                r = await self.conf_prefix(ctx, option, 'scret-desc')
            elif option in opt_list.raid_options:
                r = await self.conf_raid(ctx, option, 'scret-desc')
            elif option in opt_list.emoji_option:
                r = await self.conf_emoji(ctx, option, 'scret-desc')
            elif option in opt_list.xp_type_options:
                r = await self.conf_xp_type(ctx, option, 'scret-desc')
            elif option in opt_list.color_options:
                r = await self.conf_color(ctx, option, 'scret-desc')
            elif option in opt_list.xp_rate_option:
                r = await self.conf_xp_rate(ctx, option, 'scret-desc')
            elif option in opt_list.levelup_channel_option:
                r = await self.conf_levelup_chan(ctx, option, 'scret-desc')
            elif option in opt_list.ttt_display_option:
                r = await self.conf_tttdisplay(ctx, option, 'scret-desc')
            else:
                r = None
            guild = ctx if isinstance(ctx, discord.Guild) else ctx.guild
            if r is None:
                r = await self.bot._(ctx.channel, "server.option-notfound")
            else:
                try:
                    r = await self.bot._(ctx.channel, f"server.server_desc.{option}", value=r)
                except Exception as err:
                    pass
            try:
                if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
                    await ctx.send(await self.bot._(ctx.channel, "minecraft.cant-embed"))
                    return
                title = await self.bot._(ctx.channel, "server.opt_title", opt=option, guild=guild.name)
                embed = discord.Embed(title=title, color=self.embed_color, description=r)
                if isinstance(ctx, commands.Context):
                    embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
                await ctx.send(embed=embed)
            except Exception as err:
                self.bot.dispatch("error", err, ctx if isinstance(ctx, commands.Context) else None)

    async def update_memberChannel(self, guild: discord.Guild):
        # If we already did an update recently: abort
        if guild.id in self.membercounter_pending.keys():
            if self.membercounter_pending[guild.id] > time.time():
                return False
        ch = await self.get_option(guild.id,"membercounter")
        if ch not in ['', None]:
            ch = guild.get_channel(int(ch))
            if ch is None:
                return
            lang = await self.bot._(guild.id,'_used_locale')
            tr = str(await self.bot._(guild.id, "misc.membres")).capitalize()
            text = "{}{}: {}".format(tr, " " if lang=='fr' else "" , guild.member_count)
            if ch.name == text:
                return
            try:
                await ch.edit(name=text, reason=await self.bot._(guild.id,"logs.reason.memberchan"))
                self.membercounter_pending[guild.id] = round(time.time()) + 5*60 # cooldown 5min
                return True
            except Exception as e:
                self.bot.log.debug("[UpdateMemberChannel] "+str(e))
        return False

    async def update_everyMembercounter(self):
        if not self.bot.database_online:
            return
        i = 0
        now = time.time()
        for x in self.bot.guilds:
            if x.id in self.membercounter_pending.keys() and self.membercounter_pending[x.id] < now:
                del self.membercounter_pending[x.id]
                await self.update_memberChannel(x)
                i += 1
        if i > 0:
            emb = discord.Embed(description=f"[MEMBERCOUNTER] {i} channels refreshed", color=5011628, timestamp=self.bot.utcnow())
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb, url="loop")


async def setup(bot):
    await bot.add_cog(Servers(bot))
