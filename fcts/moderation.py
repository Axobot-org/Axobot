import datetime
import importlib
import random
from math import ceil
from typing import Dict, List, Literal, Optional, Union

import discord
from discord import app_commands
from discord.ext import commands
from libs.bot_classes import MyContext, Axobot
from libs.formatutils import FormatUtils
from libs.paginator import Paginator
from libs.views import ConfirmView

from fcts import args, checks
from fcts.cases import Case

importlib.reload(checks)
importlib.reload(args)

class Moderation(commands.Cog):
    """Here you will find everything you need to moderate your server.
    Please note that most of the commands are reserved for certain members only."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "moderation"
        # maximum of roles granted/revoked by query
        self.max_roles_modifications = 300

    @commands.hybrid_command(name="slowmode")
    @app_commands.default_permissions(manage_channels=True)
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.check(checks.can_slowmode)
    async def slowmode(self, ctx: MyContext, seconds: int = 0):
        """Keep your chat cool
Slowmode works up to one message every 6h (21600s)

..Example slowmode 10

..Example slowmode 0

..Doc moderator.html#slowmode"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.no-perm"))
            return
        if seconds == 0:
            await ctx.channel.edit(slowmode_delay=0)
            message = await self.bot._(ctx.guild.id, "moderation.slowmode.disabled")
            log = await self.bot._(ctx.guild.id, "logs.slowmode-disabled", channel=ctx.channel.mention)
            await self.bot.get_cog("Events").send_logs_per_server(ctx.guild, "slowmode", log, ctx.author)
        elif seconds > 21600:
            message = await self.bot._(ctx.guild.id, "moderation.slowmode.too-long")
        else:
            await ctx.channel.edit(slowmode_delay=seconds)
            duration = await FormatUtils.time_delta(seconds, lang=await self.bot._(ctx, "_used_locale"))
            message = await self.bot._(ctx.guild.id, "moderation.slowmode.enabled", channel=ctx.channel.mention, s=duration)
            log = await self.bot._(ctx.guild.id, "logs.slowmode-enabled", channel=ctx.channel.mention, seconds=duration)
            await self.bot.get_cog("Events").send_logs_per_server(ctx.guild, "slowmode", log, ctx.author)
        await ctx.send(message)


    @commands.hybrid_command(name="clear")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(number="The max amount of messages to delete")
    @app_commands.describe(users="list of user IDs or mentions to delete messages from, separated by spaces")
    @app_commands.describe(contains_file="Clear only messages that contains (or does not) files")
    @app_commands.describe(contains_url="Clear only messages that contains (or does not) links")
    @app_commands.describe(contains_invite="Clear only messages that contains (or does not) Discord invites")
    @app_commands.describe(is_pinned="Clear only messages that are (or are not) pinned")
    @commands.cooldown(4, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_clear)
    async def clear(self, ctx: MyContext, number:int, users: commands.Greedy[discord.User]=None, *, contains_file: Optional[bool]=None, contains_url: Optional[bool]=None, contains_invite: Optional[bool]=None, is_pinned: Optional[bool]=None):
        """Keep your chat clean
        <number>: number of messages to check
        [users]: list of user IDs or mentions to delete messages from
        [contains_file]: delete if the message does (or does not) contain any file
        [contains_url]: delete if the message does (or does not) contain any link
        [contains_invite] : delete if the message does (or does not) contain a Discord invite
        [is_pinned]: delete if the message is (or is not) pinned
        By default, the bot will NOT delete pinned messages

..Example clear 120

..Example clear 10 @someone

..Example clear 50 False False True

..Doc moderator.html#clear"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-manage-messages"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-read-history"))
            return
        if number < 1:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.clear.too-few")+" "+self.bot.emojis_manager.customs["owo"])
            return
        await ctx.defer()
        if users is None and contains_file is None and contains_url is None and contains_invite is None and is_pinned is None:
            return await self.clear_simple(ctx, number)
        user_ids = None if users is None else {u.id for u in users}

        def check(msg: discord.Message):
            # do not delete invocation message
            if ctx.interaction is not None and msg.interaction is not None and ctx.interaction.id == msg.interaction.id:
                return False
            if is_pinned is not None and msg.pinned != is_pinned:
                return False
            elif is_pinned is None and msg.pinned:
                return False
            if contains_file is not None and bool(msg.attachments) != contains_file:
                return False
            url_match = self.bot.get_cog("Utilities").sync_check_any_link(msg.content)
            if contains_url is not None and (url_match is not None) != contains_url:
                return False
            invite_match = self.bot.get_cog("Utilities").sync_check_discord_invite(msg.content)
            if contains_invite is not None and (invite_match is not None) != contains_invite:
                return False
            if users and msg.author is not None:
                return msg.author.id in user_ids
            return True

        if ctx.interaction:
            # we'll have to check past the command answer
            number += 1
        else:
            # start by deleting the invocation message
            await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=number, check=check)
        await ctx.send(await self.bot._(ctx.guild, "moderation.clear.done", count=len(deleted)), delete_after=2.0)
        if len(deleted) > 0:
            log = await self.bot._(ctx.guild.id, "logs.clear", channel=ctx.channel.mention, number=len(deleted))
            await self.bot.get_cog("Events").send_logs_per_server(ctx.guild, "clear", log, ctx.author)

    async def clear_simple(self, ctx: MyContext, number: int):
        def check(msg: discord.Message):
            if msg.pinned or msg.id == ctx.message.id:
                return False
            if ctx.interaction is None or msg.interaction is None:
                return True
            return ctx.interaction.id != msg.interaction.id
        if ctx.interaction:
            # we'll have to check past the command answer
            number += 1
        else:
            # start by deleting the invocation message
            await ctx.message.delete()
        try:
            deleted = await ctx.channel.purge(limit=number, check=check)
            await ctx.send(await self.bot._(ctx.guild, "moderation.clear.done", count=len(deleted)), delete_after=2.0)
            log = await self.bot._(ctx.guild.id, "logs.clear", channel=ctx.channel.mention, number=len(deleted))
            await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        except discord.errors.NotFound:
            await ctx.send(await self.bot._(ctx.guild, "moderation.clear.not-found"))
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)


    @commands.hybrid_command(name="kick")
    @app_commands.default_permissions(kick_members=True)
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_kick)
    async def kick(self, ctx: MyContext, user:discord.Member, *, reason="Unspecified"):
        """Kick a member from this server

..Example kick @someone Not nice enough to stay here

..Doc moderator.html#kick"""
        try:
            if not ctx.channel.permissions_for(ctx.guild.me).kick_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.no-perm"))
                return
            await ctx.defer()

            async def user_can_kick(user):
                try:
                    return await self.bot.get_cog("ServerConfig").check_member_config_permission(user, "kick_allowed_roles")
                except commands.errors.CommandError:
                    pass
                return False

            if user == ctx.guild.me or (self.bot.database_online and await user_can_kick(user)):
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.cant-staff"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).kick_members:
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.cant-staff"))
            if user.roles[-1].position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.too-high"))
                return
            # send DM
            await self.dm_user(user, "kick", ctx, reason = None if reason=="Unspecified" else reason)
            reason = await self.bot.get_cog("Utilities").clear_msg(reason, everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.kick(user,reason=reason[:512])
            caseID = "'Unsaved'"
            if self.bot.database_online:
                Cases = self.bot.get_cog('Cases')
                case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="kick",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow())
                try:
                    await Cases.add_case(case)
                    caseID = case.id
                except Exception as err:
                    self.bot.dispatch("error", err, ctx)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            # optional values
            opt_case = None if caseID=="'Unsaved'" else caseID
            opt_reason = None if reason=="Unspecified" else reason
            # send in chat
            await self.send_chat_answer("kick", user, ctx, opt_case)
            # send in modlogs
            await self.send_modlogs("kick", user, ctx.author, ctx.guild, opt_case, opt_reason)
        except discord.errors.Forbidden:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.too-high"))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("error", err, ctx)
        await self.bot.get_cog('Events').add_event('kick')


    @commands.hybrid_command(name="warn")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(message="The reason of the warn")
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_warn)
    async def warn(self, ctx: MyContext, user:discord.Member, *, message):
        """Send a warning to a member

..Example warn @someone Please just stop, next one is a mute duh

..Doc moderator.html#warn"""
        try:
            async def user_can_warn(user):
                try:
                    return await self.bot.get_cog("ServerConfig").check_member_config_permission(user, "warn_allowed_roles")
                except commands.errors.CommandError:
                    pass
                return False
            if user==ctx.guild.me or (self.bot.database_online and await user_can_warn(user)):
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.warn.cant-staff"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.warn.cant-staff"))
            if user.bot and not user.id==423928230840500254:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.warn.cant-bot"))
                return
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        try:
            # send DM
            await self.dm_user(user, "warn", ctx, reason=message)
            message = await self.bot.get_cog("Utilities").clear_msg(message,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            caseID = "'Unsaved'"
            if self.bot.database_online:
                if cases_cog := self.bot.get_cog('Cases'):
                    case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="warn",mod_id=ctx.author.id,reason=message,date=ctx.bot.utcnow())
                    await cases_cog.add_case(case)
                    caseID = case.id
            else:
                await ctx.send(await self.bot._(ctx.guild.id,"moderation.warn.warn-but-db"))
            # optional values
            opt_case = None if caseID=="'Unsaved'" else caseID
            # send in chat
            await self.send_chat_answer("warn", user, ctx, opt_case)
            # send in modlogs
            await self.send_modlogs("warn", user, ctx.author, ctx.guild, opt_case, message)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("command_error", ctx, err)

    async def get_muted_role(self, guild: discord.Guild) -> Optional[discord.Role]:
        "Find the muted role from the guild config option"
        return await self.bot.get_config(guild.id, "muted_role")
        # return discord.utils.find(lambda x: x.name.lower() == "muted", guild.roles)

    async def mute_event(self, member:discord.Member, author:discord.Member, reason:str, case_id:int, f_duration:str=None, duration: datetime.timedelta=None):
        """Call when someone should be muted in a guild"""
        # add the muted role
        role = await self.get_muted_role(member.guild)
        if role is None:
            duration = duration or datetime.timedelta(days=28)
            await member.timeout(duration, reason=reason[:512])
        else:
            await member.add_roles(role, reason=reason[:512])
        # send in modlogs
        opt_case = None if case_id == "'Unsaved'" else case_id
        opt_reason = None if reason == "Unspecified" else reason
        await self.send_modlogs("mute", member, author, member.guild, opt_case, opt_reason, f_duration)
        # save in database that the user is muted
        if not self.bot.database_online:
            return
        query = "INSERT IGNORE INTO `mutes` VALUES (%s, %s, CURRENT_TIMESTAMP)"
        async with self.bot.db_query(query, (member.id, member.guild.id)):
            pass

    async def check_mute_context(self, ctx: MyContext, role: discord.Role, user: discord.Member):
        "Return True if the user can be muted in the given context"
        if await self.is_muted(ctx.guild, user, role):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.already-mute"))
            return False
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
            return False
        if role is None:
            if not ctx.guild.me.guild_permissions.moderate_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-timeout"))
                return False
            if user.top_role.position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.too-high"))
                return False
            return True
        if role.position > ctx.guild.me.roles[-1].position:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.mute-high"))
            return False
        return True

    @commands.hybrid_command(name="mute")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(time="The duration of the mute, example 3d 7h 12min")
    @app_commands.describe(reason="The reason of the mute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def mute(self, ctx: MyContext, user: discord.Member, time: commands.Greedy[args.Duration], *, reason="Unspecified"):
        """Timeout someone.
You can also mute this member for a defined duration, then use the following format:
`XXm` : XX minutes
`XXh` : XX hours
`XXd` : XX days
`XXw` : XX weeks

..Example mute @someone 1d 3h Reason is becuz he's a bad guy

..Example mute @someone Plz respect me

..Doc moderator.html#mute-unmute"""
        duration = sum(time)
        if duration > 0:
            if duration > 60*60*24*365*3: # max 3 years
                await ctx.send(await self.bot._(ctx.channel, "timers.rmd.too-long"))
                return
            f_duration = await FormatUtils.time_delta(duration, lang=await self.bot._(ctx.guild,'_used_locale'), form="short")
        else:
            f_duration = None
        await ctx.defer()

        async def user_can_mute(user):
            try:
                return await self.bot.get_cog("ServerConfig").check_member_config_permission(user, "mute_allowed_roles")
            except commands.errors.CommandError:
                pass
            return False

        try:
            if user==ctx.guild.me or (self.bot.database_online and await user_can_mute(user)):
                emoji = random.choice([':confused:',':upside_down:',self.bot.emojis_manager.customs['wat'],':no_mouth:',self.bot.emojis_manager.customs['owo'],':thinking:',])
                await ctx.send((await self.bot._(ctx.guild.id, "moderation.mute.staff-mute")) + " " + emoji)
                return
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.warn.cant-staff"))
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        role = await self.get_muted_role(ctx.guild)
        if not await self.check_mute_context(ctx, role, user):
            return
        caseID = "'Unsaved'"
        try:
            reason = await self.bot.get_cog("Utilities").clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            if self.bot.database_online:
                Cases = self.bot.get_cog('Cases')
                if f_duration is None:
                    case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="mute",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow())
                else:
                    case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="tempmute",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow(),duration=duration)
                    await self.bot.task_handler.add_task('mute',duration,user.id,ctx.guild.id)
                try:
                    await Cases.add_case(case)
                    caseID = case.id
                except Exception as err:
                    self.bot.dispatch("command_error", ctx, err)
            # actually mute
            await self.mute_event(user, ctx.author, reason, caseID, f_duration, datetime.timedelta(seconds=duration) if duration else None)
            # optional values
            opt_case = None if caseID=="'Unsaved'" else caseID
            opt_reason = None if reason=="Unspecified" else reason
            # send DM
            await self.dm_user(user, "mute", ctx, reason=opt_reason, duration=f_duration)
            # send in chat
            await self.send_chat_answer("mute", user, ctx, opt_case)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("command_error", ctx, err)


    async def unmute_event(self, guild: discord.Guild, user: discord.Member, author: discord.Member):
        """Call this to unmute someone"""
        # remove the role
        role = await self.get_muted_role(guild)
        if author == guild.me:
            reason = await self.bot._(guild.id,"logs.reason.autounmute")
        else:
            reason = await self.bot._(guild.id,"logs.reason.unmute", user=author)
        if role is None:
            await user.timeout(None, reason=reason)
        elif role in user.roles:
            await user.remove_roles(role, reason=reason)
        # send in modlogs
        await self.send_modlogs("unmute", user, author, guild)
        # remove the muted record in the database
        if not self.bot.database_online:
            return
        query = "DELETE IGNORE FROM mutes WHERE userid=%s AND guildid=%s"
        async with self.bot.db_query(query, (user.id, guild.id)):
            pass

    async def is_muted(self, guild: discord.Guild, user: discord.User, role: Optional[discord.Role]) -> bool:
        """Check if a user is currently muted"""
        if not self.bot.database_online:
            if role is None:
                return False
            if not isinstance(user, discord.Member):
                return False
            return role in user.roles
        query = "SELECT COUNT(*) AS count FROM `mutes` WHERE guildid=%s AND userid=%s"
        async with self.bot.db_query(query, (guild.id, user.id)) as query_results:
            result: int = query_results[0]['count']
        return bool(result)

    async def db_get_muted_list(self, guild_id: int, reasons: bool = False) -> Union[Dict[int, str], List[int]]:
        """List muted users for a specific guild
        Set 'reasons' to True if you want the attached reason"""
        if reasons:
            cases_table = "cases_beta" if self.bot.beta else "cases"
            query = f'SELECT userid, (SELECT reason FROM {cases_table} WHERE {cases_table}.user=userid AND {cases_table}.guild=guildid AND {cases_table}.type LIKE "%mute" ORDER BY `{cases_table}`.`created_at` DESC LIMIT 1) as reason FROM `mutes` WHERE guildid=%s'
            async with self.bot.db_query(query, (guild_id,)) as query_results:
                result = {row['userid']: row['reason'] for row in query_results}
        else:
            query = 'SELECT userid FROM `mutes` WHERE guildid=%s'
            async with self.bot.db_query(query, (guild_id,)) as query_results:
                result = [row['userid'] for row in query_results]
        return result

    @commands.hybrid_command(name="unmute")
    @app_commands.default_permissions(moderate_members=True)
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def unmute(self, ctx:MyContext, *, user:discord.Member):
        """Unmute someone
This will remove the role 'muted' for the targeted member

..Example unmute @someone

..Doc moderator.html#mute-unmute"""
        role = await self.get_muted_role(ctx.guild)
        # if role not in user.roles:
        if not await self.is_muted(ctx.guild, user, role):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.already-unmute"))
            return
        if role is not None:
            if not ctx.channel.permissions_for(ctx.guild.me).manage_roles:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
                return
            if role.position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.mute-high"))
                return
        elif user.is_timed_out():
            if not ctx.guild.me.guild_permissions.moderate_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-timeout"))
                return
            if user.top_role.position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.too-high"))
                return
        await ctx.defer()
        try:
            await self.unmute_event(ctx.guild, user, ctx.author)
            # send in chat
            await self.send_chat_answer("unmute", user, ctx)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            # remove planned automatic unmutes
            await self.bot.task_handler.cancel_unmute(user.id, ctx.guild.id)
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("command_error", ctx, err)

    @commands.hybrid_command(name="mute-config")
    @app_commands.default_permissions(manage_roles=True)
    @commands.cooldown(1, 15, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def mute_config(self, ctx: MyContext):
        """Auto configure the muted role for you, if you do not want to use the official timeout
        Useful if you want to have a base for a properly working muted role
        Warning: the process may break some things in your server, depending on how you configured your channel permissions.

        ..Doc moderator.html#mute-unmute
        """
        await ctx.defer()
        confirm_view = ConfirmView(
            self.bot, ctx.channel,
            validation=lambda inter: inter.user == ctx.author,
            ephemeral=False)
        await confirm_view.init()
        confirm_txt = await self.bot._(ctx.guild.id, "moderation.mute-config.confirm")
        confirm_txt += "\n\n" + await self.bot._(ctx.guild.id, "moderation.mute-config.tip", mute=await self.bot.get_command_mention("mute"))
        confirm_msg = await ctx.send(confirm_txt, view=confirm_view)

        await confirm_view.wait()
        await confirm_view.disable(confirm_msg)
        if not confirm_view.value:
            return

        role = await self.get_muted_role(ctx.guild)
        create = role is None
        role, count = await self.configure_muted_role(ctx.guild, role)
        if role is None or count >= len(ctx.guild.voice_channels+ctx.guild.text_channels):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute-config.err"))
        elif create:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute-config.success", count=count))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute-config.success2", count=count))


    @commands.hybrid_command(name="ban")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(time="The duration of the ban, example 3d 7h 12min")
    @app_commands.describe(days_to_delete="How many days of messages to delete, max 7")
    @app_commands.describe(reason="The reason of the ban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_ban)
    async def ban(self, ctx:MyContext, user:args.AnyUser, time:commands.Greedy[args.Duration]=None, days_to_delete:Optional[int]=0, *, reason="Unspecified"):
        """Ban someone
The 'days_to_delete' option represents the number of days worth of messages to delete from the user in the guild, bewteen 0 and 7

..Example ban @someone 3d You're bad

..Example ban someone#1234 7 Spam isn't tolerated here

..Example ban someone_else DM advertising is against Discord ToS!!!

..Doc moderator.html#ban-unban
        """
        try:
            duration = sum(time) if time else 0
            if duration > 0:
                if duration > 60*60*24*365*20: # max 20 years
                    await ctx.send(await self.bot._(ctx.channel, "timers.rmd.too-long"))
                    return
                f_duration = await FormatUtils.time_delta(duration,lang=await self.bot._(ctx.guild,'_used_locale'),form="short")
            else:
                f_duration = None
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.cant-ban"))
                return
            if user in ctx.guild.members:
                member = ctx.guild.get_member(user.id)
                async def user_can_ban(user):
                    try:
                        return await self.bot.get_cog("ServerConfig").check_member_config_permission(user, "ban_allowed_roles")
                    except commands.errors.CommandError:
                        pass
                    return False
                if user==ctx.guild.me or (self.bot.database_online and await user_can_ban(member)):
                    await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.staff-ban"))
                    return
                elif not self.bot.database_online and (ctx.channel.permissions_for(member).ban_members or user==ctx.guild.me):
                    await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.staff-ban"))
                    return
                if member.roles[-1].position >= ctx.guild.me.roles[-1].position:
                    await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.too-high"))
                    return
                # send DM only if the user is still in the server
                await self.dm_user(user, "ban", ctx, reason = None if reason=="Unspecified" else reason)
            if days_to_delete not in range(8):
                days_to_delete = 0
            reason = await self.bot.get_cog("Utilities").clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.ban(user, reason=reason[:512], delete_message_seconds=days_to_delete * 86400)
            await self.bot.get_cog('Events').add_event('ban')
            case_id = "'Unsaved'"
            if self.bot.database_online:
                cases_cog = self.bot.get_cog('Cases')
                if f_duration is None:
                    case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="ban",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow())
                else:
                    case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="tempban",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow(),duration=duration)
                    await self.bot.task_handler.add_task('ban',duration,user.id,ctx.guild.id)
                try:
                    await cases_cog.add_case(case)
                    case_id = case.id
                except Exception as err:
                    self.bot.dispatch("error", err, ctx)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            # optional values
            opt_case = None if case_id=="'Unsaved'" else case_id
            opt_reason = None if reason=="Unspecified" else reason
            # send message in chat
            await self.send_chat_answer("ban", user, ctx, opt_case)
            # send in modlogs
            await self.send_modlogs("ban", user, ctx.author, ctx.guild, opt_case, opt_reason, f_duration)
        except discord.errors.Forbidden:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.too-high"))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("error", err, ctx)

    async def unban_event(self, guild: discord.Guild, user: discord.User, author: discord.User):
        if not guild.me.guild_permissions.ban_members:
            return
        reason = await self.bot._(guild.id,"logs.reason.unban", user=author)
        await guild.unban(user, reason=reason[:512])
        # send in modlogs
        await self.send_modlogs("unban", user, author, guild, reason="Automod")

    @commands.hybrid_command(name="unban")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(reason="The reason of the unban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_ban)
    async def unban(self, ctx: MyContext, user: str, *, reason="Unspecified"):
        """Unban someone

..Example unban 486896267788812288 Nice enough

..Doc moderator.html#ban-unban"""
        try:
            backup = user
            try:
                user: discord.User = await commands.UserConverter().convert(ctx,user)
            except commands.BadArgument:
                if user.isnumeric():
                    try:
                        user: discord.User = await self.bot.fetch_user(int(user))
                    except discord.NotFound:
                        await ctx.send(await self.bot._(ctx.guild.id, "moderation.cant-find-user", user=backup))
                        return
                    del backup
                else:
                    await ctx.send(await self.bot._(ctx.guild.id, "errors.usernotfound", u=user))
                    return
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.cant-ban"))
                return
            await ctx.defer()
            try:
                await ctx.guild.fetch_ban(user)
            except discord.NotFound:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.user-not-banned"))
                return
            reason = await self.bot.get_cog("Utilities").clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.unban(user,reason=reason[:512])
            case_id = "'Unsaved'"
            if self.bot.database_online:
                cases_cog = self.bot.get_cog('Cases')
                case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="unban",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow())
                try:
                    await cases_cog.add_case(case)
                    case_id = case.id
                except Exception as err:
                    self.bot.dispatch("error", err, ctx)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            # optional values
            opt_case = None if case_id=="'Unsaved'" else case_id
            opt_reason = None if reason=="Unspecified" else reason
            # send in chat
            await self.send_chat_answer("unban", user, ctx, opt_case)
            # send in modlogs
            await self.send_modlogs("unban", user, ctx.author, ctx.guild, opt_case, opt_reason)
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("error", err, ctx)

    @commands.hybrid_command(name="softban")
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(reason="The reason of the kick")
    @commands.guild_only()
    @commands.check(checks.can_kick)
    async def softban(self, ctx: MyContext, user: discord.Member, *, reason="Unspecified"):
        """Kick a member and lets Discord delete all his messages up to 7 days old.
Permissions for using this command are the same as for the kick

..Example softban @someone No spam pls

..Doc moderator.html#softban"""
        try:
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.cant-ban"))
                return
            async def user_can_kick(user):
                try:
                    return await self.bot.get_cog("ServerConfig").check_member_config_permission(user, "kick_allowed_roles")
                except commands.errors.CommandError:
                    pass
                return False
            if user == ctx.guild.me or (self.bot.database_online and await user_can_kick(user)):
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.cant-staff"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).kick_members:
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.cant-staff"))
            if user.roles[-1].position >= ctx.guild.me.roles[-1].position:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.too-high"))
                return
            # send DM
            await self.dm_user(user, "kick", ctx, reason = None if reason=="Unspecified" else reason)

            reason = await self.bot.get_cog("Utilities").clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.ban(user,reason=reason[:512],delete_message_days=7)
            await user.unban()
            caseID = "'Unsaved'"
            if self.bot.database_online:
                Cases = self.bot.get_cog('Cases')
                case = Case(bot=self.bot,guild_id=ctx.guild.id,member_id=user.id,case_type="softban",mod_id=ctx.author.id,reason=reason,date=ctx.bot.utcnow())
                try:
                    await Cases.add_case(case)
                    caseID = case.id
                except Exception as err:
                    self.bot.dispatch("error", err, ctx)
            try:
                await ctx.message.delete()
            except (discord.Forbidden, discord.NotFound):
                pass
            # optional values
            opt_case = None if caseID=="'Unsaved'" else caseID
            opt_reason = None if reason=="Unspecified" else reason
            # send in chat
            await self.send_chat_answer("kick", user, ctx, opt_case)
            # send in modlogs
            await self.send_modlogs("softban", user, ctx.author, ctx.guild, opt_case, opt_reason)
        except discord.errors.Forbidden:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.kick.too-high"))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("error", err, ctx)

    async def dm_user(self, user: discord.User, action: str, ctx: MyContext, reason: str = None, duration: str = None):
        if user.id in self.bot.get_cog('Welcomer').no_message:
            return
        if action in ('warn', 'mute', 'kick', 'ban'):
            message = await self.bot._(user, "moderation."+action+"-dm", guild=ctx.guild.name)
        else:
            return
        color: int = None
        if helpCog := self.bot.get_cog("Help"):
            color = helpCog.help_color
        emb = discord.Embed(description=message, colour=color)
        if duration:
            if len(duration) > 1020:
                duration = duration[:1020] + "..."
            _duration = await self.bot._(user, "misc.duration")
            emb.add_field(name=_duration.capitalize(), value=duration)
        if reason:
            if len(reason) > 1020:
                reason = reason[:1020] + "..."
            _reason = await self.bot._(user, "misc.reason")
            emb.add_field(name=_reason.capitalize(),
                          value=reason, inline=False)
        try:
            await user.send(embed=emb)
        except (discord.Forbidden, discord.NotFound):
            pass
        except discord.HTTPException as err:
            if err.code == 50007:
                # "Cannot send message to this user"
                return
            self.bot.dispatch("error", err, ctx)
        except Exception as err:
            self.bot.dispatch("error", err, ctx)

    async def send_chat_answer(self, action: str, user: discord.User, ctx: MyContext, case: int = None):
        if action in ('warn', 'mute', 'unmute', 'kick', 'ban', 'unban'):
            message = await self.bot._(ctx.guild.id, "moderation."+action+"-chat", user=user.mention, userid=user.id)
        else:
            return
        _case = await self.bot._(ctx.guild.id, "misc.case")
        if ctx.can_send_embed:
            color = discord.Color.red()
            if action in ("unmute", "unban"):
                if helpCog := self.bot.get_cog("Help"):
                    color = helpCog.help_color
            emb = discord.Embed(description=message, colour=color)
            if case:
                emb.add_field(name=_case.capitalize(), value=f"#{case}")
            await ctx.send(embed=emb)
        else:
            await ctx.send(f"{message}\n{_case.capitalize()} #{case}")

    async def send_modlogs(self, action: str, user: discord.User, author: discord.User, guild: discord.Guild, case: int = None, reason: str = None, duration: str = None):
        if action not in ('warn', 'mute', 'unmute', 'kick', 'ban', 'unban', 'softban'):
            return
        message = await self.bot._(guild.id, "logs."+action, user=str(user), userid=user.id)
        fields = list()
        if case:
            _case = await self.bot._(guild.id, "misc.case")
            fields.append({'name': _case.capitalize(),
                          'value': f"#{case}", 'inline': True})
        if duration:
            _duration = await self.bot._(guild.id, "misc.duration")
            if len(duration) > 1020:
                duration = duration[:1020] + "..."
            fields.append({'name': _duration.capitalize(),
                          'value': duration, 'inline': True})
        if reason:
            if len(reason) > 1020:
                reason = reason[:1020] + "..."
            _reason = await self.bot._(guild.id, "misc.reason")
            fields.append({'name': _reason.capitalize(), 'value': reason})
        await self.bot.get_cog("Events").send_logs_per_server(guild, action, message, author, fields)

    @commands.hybrid_command(name="banlist")
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(show_reasons="Show or not the bans reasons")
    @commands.guild_only()
    @commands.check(checks.has_admin)
    @commands.check(checks.bot_can_embed)
    async def banlist(self, ctx: MyContext, show_reasons: bool=True):
        """Check the list of currently banned members.
The 'show_reasons' parameter is used to display the ban reasons.

You must be an administrator of this server to use this command.

..Doc moderator.html#banlist-mutelist"""
        if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.cant-ban"))
            return

        class BansPaginator(Paginator):
            "Paginator used to display banned users"
            saved_bans: list[discord.guild.BanEntry] = []
            users: set[int] = set()

            async def get_page_count(self) -> int:
                length = len(self.saved_bans)
                if length == 0:
                    return 1
                if length%1000 == 0:
                    return self.page+1
                return ceil(length/30)

            async def get_page_content(self, interaction, page):
                "Create one page"
                if last_user := (None if len(self.saved_bans) == 0 else self.saved_bans[-1].user):
                    self.saved_bans += [
                        entry async for entry in ctx.guild.bans(limit=1000, after=last_user) if entry.user.id not in self.users
                    ]
                else:
                    self.saved_bans += [
                        entry async for entry in ctx.guild.bans(limit=1000) if entry.user.id not in self.users
                    ]
                self.users = {entry.user.id for entry in self.saved_bans}

                _title = await self.client._(ctx.guild.id, "moderation.ban.list-title-0")
                emb = discord.Embed(title=_title.format(ctx.guild.name), color=7506394)
                if len(self.saved_bans) == 0:
                    emb.description = await self.client._(ctx.guild.id, "moderation.ban.no-bans")
                else:
                    page_start, page_end = (page-1)*30, min(page*30, len(self.saved_bans))
                    for i in range(page_start, page_end, 10):
                        column_start, column_end = i+1, min(i+10, len(self.saved_bans))
                        if show_reasons:
                            values = [f"{entry.user}  *({entry.reason})*" for entry in self.saved_bans[i:i+10]]
                        else:
                            values = [str(entry.user) for entry in self.saved_bans[i:i+10]]
                        emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(values))
                footer = f"{ctx.author}  |  {page}/{await self.get_page_count()}"
                emb.set_footer(text=footer, icon_url=ctx.author.display_avatar)
                return {
                    "embed": emb
                }

        _quit = await self.bot._(ctx.guild, "misc.quit")
        view = BansPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
        await view.send_init(ctx)


    @commands.hybrid_command(name="mutelist")
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(show_reasons="Show or not the mute reasons")
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def mutelist(self, ctx: MyContext, show_reasons:bool=True):
        """Check the list of members currently **muted by using this bot**.
The 'show_reasons' parameter is used to display the mute reasons.

..Doc moderator.html#banlist-mutelist"""
        try:
            muted_list = await self.db_get_muted_list(ctx.guild.id, reasons=show_reasons)
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("error", err, ctx)
            return

        class MutesPaginator(Paginator):
            "Paginator used to display muted users"
            users_map: dict[int, Optional[discord.User]] = {}

            async def get_page_count(self) -> int:
                length = len(muted_list)
                if length == 0:
                    return 1
                return ceil(length/30)

            async def _resolve_user(self, user_id: int):
                if user := self.users_map.get(user_id):
                    return user
                if user := self.client.get_user(user_id):
                    self.users_map[user_id] = user
                    return user
                if user := await self.client.fetch_user(user_id):
                    self.users_map[user_id] = user
                    return user
                return user_id

            async def get_page_content(self, interaction, page):
                "Create one page"
                title = await self.client._(ctx.guild.id, "moderation.mute.list-title-0", guild=ctx.guild.name)
                emb = discord.Embed(title=title, color=self.client.get_cog("ServerConfig").embed_color)
                if len(muted_list) == 0:
                    emb.description = await self.client._(ctx.guild.id, "moderation.mute.no-mutes")
                else:
                    page_start, page_end = (page-1)*30, min(page*30, len(muted_list))
                    for i in range(page_start, page_end, 10):
                        column_start, column_end = i+1, min(i+10, len(muted_list))
                        values: list[str] = []
                        if show_reasons:
                            for user_id, reason in list(muted_list.items())[i:i+10]:
                                user = await self._resolve_user(user_id)
                                values.append(f"{user}  *({reason})*")
                        else:
                            for user_id in muted_list[i:i+10]:
                                user = await self._resolve_user(user_id)
                                values.append(str(user))
                        emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(values))
                footer = f"{ctx.author}  |  {page}/{await self.get_page_count()}"
                emb.set_footer(text=footer, icon_url=ctx.author.display_avatar)
                return {
                    "embed": emb
                }

        _quit = await self.bot._(ctx.guild, "misc.quit")
        view = MutesPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
        await view.send_init(ctx)


    @commands.hybrid_group(name="emoji",aliases=['emojis', 'emote'])
    @app_commands.default_permissions(manage_emojis=True)
    @commands.guild_only()
    @commands.cooldown(5,20, commands.BucketType.guild)
    async def emoji_group(self, ctx: MyContext):
        """Manage your emoji
        Administrator permission is required

        ..Doc moderator.html#emoji-manager"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @emoji_group.command(name="rename")
    @app_commands.describe(emoji="The emoji to rename", name="The new name")
    @commands.guild_only()
    @commands.check(checks.has_manage_emojis)
    async def emoji_rename(self, ctx: MyContext, emoji: discord.Emoji, name: str):
        """Rename an emoji

        ..Example emoji rename :cool\: supercool

        ..Doc moderator.html#emoji-manager"""
        if emoji.guild != ctx.guild:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.emoji.wrong-guild"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_emojis:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.emoji.cant-emoji"))
            return
        await emoji.edit(name=name)
        await ctx.send(await self.bot._(ctx.guild.id, "moderation.emoji.renamed", emoji=emoji))

    @emoji_group.command(name="restrict")
    @app_commands.describe(emoji="The emoji to restrict", roles="The roles allowed to use this emoji (separated by spaces), or 'everyone'")
    @commands.guild_only()
    @commands.check(checks.has_manage_emojis)
    async def emoji_restrict(self, ctx: MyContext, emoji: discord.Emoji, roles: commands.Greedy[Union[discord.Role, Literal['everyone']]]):
        """Restrict the use of an emoji to certain roles

        ..Example emoji restrict :vip: @VIP @Admins

        ..Example emoji restrict :vip: everyone

        ..Doc moderator.html#emoji-manager"""
        if emoji.guild != ctx.guild:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.emoji.wrong-guild"))
            return
        if not ctx.guild.me.guild_permissions.manage_emojis:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.emoji.cant-emoji"))
            return
        for e, role in enumerate(roles):
            if role == "everyone":
                roles[e] = ctx.guild.default_role
        # remove duplicates
        roles = list(set(roles))
        await emoji.edit(name=emoji.name, roles=roles)
        await ctx.send(await self.bot._(ctx.guild.id, "moderation.emoji.emoji-valid", name=emoji, roles=", ".join([x.name for x in roles])))

    @emoji_group.command(name="clear")
    @commands.guild_only()
    @commands.check(checks.has_manage_msg)
    async def emoji_clear(self, ctx: MyContext, message: discord.Message, emoji: discord.Emoji = None):
        """Remove all reactions under a message
        If you specify an emoji, only reactions with that emoji will be deleted

        ..Example emoji clear

        ..Example emoji clear :axoblob:

        ..Doc moderator.html#emoji-manager"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-manage-messages"))
        if emoji:
            await message.clear_reaction(emoji)
        else:
            await message.clear_reactions()
        try:
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

    @emoji_group.command(name="list")
    @commands.guild_only()
    @commands.check(checks.bot_can_embed)
    async def emoji_list(self, ctx: MyContext):
        """List every emoji of your server

        ..Example emojis list

        ..Example emojis list 2

        ..Doc moderator.html#emoji-manager"""
        structure = await self.bot._(ctx.guild.id, "moderation.emoji.list")
        priv = "**"+await self.bot._(ctx.guild.id, "moderation.emoji.private")+"**"
        title = await self.bot._(ctx.guild.id, "moderation.emoji.list-title", guild=ctx.guild.name)
        # static emojis
        emotes = [
            structure.format(x, x.name, f"<t:{x.created_at.timestamp():.0f}>", priv if len(x.roles) > 0 else '')
            for x in ctx.guild.emojis
            if not x.animated
        ]
        # animated emojis
        emotes += [
            structure.format(x, x.name, f"<t:{x.created_at.timestamp():.0f}>", priv if len(x.roles) > 0 else '')
            for x in ctx.guild.emojis
            if x.animated
        ]

        class EmojisPaginator(Paginator):
            async def get_page_count(self) -> int:
                length = len(emotes)
                if length == 0:
                    return 1
                return ceil(length / 50)

            async def get_page_content(self, _: discord.Interaction, page: int):
                "Create one page"
                first_index = (page - 1) * 50
                last_index = min(first_index + 50, len(emotes))
                embed = discord.Embed(title=title, color=ctx.bot.get_cog('ServerConfig').embed_color)
                for i in range(first_index, last_index, 10):
                    emotes_list = list()
                    for emote in emotes[i:i+10]:
                        emotes_list.append(emote)
                    field_name = "{}-{}".format(i + 1, i + len(emotes_list))
                    embed.add_field(name=field_name, value="\n".join(emotes_list), inline=False)
                return {
                    "embed": embed
                }

        _quit = await self.bot._(ctx.guild, "misc.quit")
        view = EmojisPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
        await view.send_init(ctx)


    @commands.hybrid_group(name="role", aliases=["roles"])
    @app_commands.default_permissions(manage_roles=True)
    @commands.guild_only()
    async def main_role(self, ctx: MyContext):
        """A few commands to manage roles

        ..Doc moderator.html#emoji-manager"""
        if ctx.subcommand_passed is None and ctx.interaction is None:
            await ctx.send_help(ctx.command)

    @main_role.command(name="set-color", aliases=['set-colour'])
    @app_commands.describe(color="The new color role, preferably in hex format (#ff6699)")
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def role_color(self, ctx: MyContext, role: discord.Role, color: discord.Color):
        """Change a color of a role

        ..Example role set-color "Admin team" red

        ..Doc moderator.html#role-manager"""
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
            return
        if role.position >= ctx.guild.me.roles[-1].position:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.too-high",r=role.name))
            return
        await role.edit(colour=color,reason="Asked by {}".format(ctx.author))
        await ctx.send(await self.bot._(ctx.guild.id,"moderation.role.color-success", role=role.name))

    @main_role.command(name="members-list")
    @commands.cooldown(5, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def role_list(self, ctx: MyContext, *, role: discord.Role):
        """Send the list of members in a role

        ..Example role members-list "Technical team"

        ..Doc moderator.html#role-manager"""
        if not (await checks.has_manage_roles(ctx) or await checks.has_manage_guild(ctx) or await checks.has_manage_msg(ctx)):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.missing-user-perms"))
            return
        if not ctx.can_send_embed:
            return await ctx.send(await self.bot._(ctx.guild.id,"fun.no-embed-perm"))
        tr_nbr = await self.bot._(ctx.guild.id,'info.info.role-3')
        tr_mbr = await self.bot._(ctx.guild.id,"misc.membres")
        txt = str()
        emb = discord.Embed(title=role.name, color=role.color, timestamp=ctx.message.created_at)
        emb.add_field(name=tr_nbr.capitalize(), value=len(role.members), inline=False)
        nbr = len(role.members)
        if nbr <= 200:
            for i in range(nbr):
                txt += role.members[i].mention+" "
                if i<nbr-1 and len(txt+role.members[i+1].mention) > 1000:
                    emb.add_field(name=tr_mbr.capitalize(), value=txt)
                    txt = str()
            if len(txt) > 0:
                emb.add_field(name=tr_mbr.capitalize(), value=txt)
        emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        await ctx.send(embed=emb)

    @main_role.command(name="temporary-grant")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def roles_temp_grant(self, ctx: MyContext, role: discord.Role, user: discord.Member, time: commands.Greedy[args.Duration]):
        """Temporary give a role to a member

        ..Example role temporary-grant Slime Theo 1h

        ..Doc moderator.html#role-manager"""
        duration = sum(time)
        if duration == 0:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['time'])
        if duration > 60*60*24*31: # max 31 days
            await ctx.send(await self.bot._(ctx.guild.id, "timers.rmd.too-long"))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-too-high", r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-roles-higher"))
        await user.add_roles(role, reason=f"Asked by {ctx.author}")
        await self.bot.task_handler.add_task('role-grant', duration, user.id, ctx.guild.id, data={'role': role.id})
        f_duration = await FormatUtils.time_delta(duration, lang=await self.bot._(ctx.guild,'_used_locale'), form="short")
        await ctx.send(
            await self.bot._(ctx.guild.id, "moderation.role.temp-grant-success", role=role.name, user=user.mention, time=f_duration),
            allowed_mentions=discord.AllowedMentions.none()
        )


    @main_role.command(name="grant", aliases=["add", "give"])
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def roles_give(self, ctx: MyContext, role: discord.Role, users: commands.Greedy[Union[discord.Role, discord.Member, Literal['everyone']]]):
        """Give a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role grant Elders everyone

        ..Example role grant Slime Theo AsiliS

        ..Doc moderator.html#role-manager"""
        if len(users) == 0:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['users'])
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-too-high", r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-roles-higher"))
        n_users: set[discord.Member] = set()
        for item in users:
            if item == "everyone":
                item = ctx.guild.default_role
            if isinstance(item, discord.Member):
                if role not in item.roles:
                    n_users.add(item)
            else:
                for m in item.members:
                    if role not in m.roles:
                        n_users.add(m)
        if len(n_users) > 15:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-pending", n=len(n_users)))
        count = 0
        for user in n_users:
            if count >= self.max_roles_modifications:
                break
            await user.add_roles(role, reason="Asked by {}".format(ctx.author))
            count += 1
        answer = await self.bot._(ctx.guild.id, "moderation.role.give-success", count=count, m=len(n_users))
        if count == self.max_roles_modifications and len(n_users) > count:
            answer += f'\n⚠️ *{await self.bot._(ctx.guild.id, "moderation.role.limit-hit", limit=self.max_roles_modifications)}*'
        if len(n_users) > 50:
            await ctx.reply(answer)
        else:
            await ctx.send(answer)

    @main_role.command(name="revoke", aliases=["remove"])
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def roles_remove(self, ctx:MyContext, role:discord.Role, users:commands.Greedy[Union[discord.Role,discord.Member,Literal['everyone']]]):
        """Remove a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role revoke VIP @muted

        ..Doc moderator.html#role-manager"""
        if len(users) == 0:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['users'])
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-too-high",r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-roles-higher"))
        n_users: set[discord.Member] = set()
        for item in users:
            if item == "everyone":
                item = ctx.guild.default_role
            if isinstance(item, discord.Member):
                if role in item.roles:
                    n_users.add(item)
            else:
                for m in item.members:
                    if role in m.roles:
                        n_users.add(m)
        if len(n_users) > 15:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.remove-pending", n=len(n_users)))
        count = 0
        for user in n_users:
            if count >= self.max_roles_modifications:
                break
            await user.remove_roles(role,reason="Asked by {}".format(ctx.author))
            count += 1
        answer = await self.bot._(ctx.guild.id, "moderation.role.remove-success",count=count,m=len(n_users))
        if count == self.max_roles_modifications and len(n_users) > count:
            answer += f'\n⚠️ *{await self.bot._(ctx.guild.id, "moderation.role.limit-hit", limit=self.max_roles_modifications)}*'
        if len(n_users) > 50:
            await ctx.reply(answer)
        else:
            await ctx.send(answer)

    @commands.hybrid_command(name='unhoist')
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.describe(chars="The list of characters that should be considered as hoisting")
    @commands.guild_only()
    @commands.check(checks.has_manage_nicknames)
    async def unhoist(self, ctx: MyContext, chars: str=None):
        """Remove the special characters from the beginning of usernames

        ..Example unhoist

        ..Example unhoist 0AZ^_

        ..Doc moderator.html#unhoist-members"""
        count = 0
        if not ctx.channel.permissions_for(ctx.guild.me).manage_nicknames:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.missing-manage-nick"))
        if len(ctx.guild.members) > 5000:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.unhoist-too-many-members"))
        if chars is None:
            def check(username: str):
                while username < '0' and len(username):
                    username = username[1:]
                if len(username) == 0:
                    username = "z unhoisted"
                return username
        else:
            chars = chars.lower()
            def check(username: str):
                while len(username) and username[0].lower() in chars+' ':
                    username = username[1:]
                if len(username) == 0:
                    username = "z unhoisted"
                return username
        for member in ctx.guild.members:
            try:
                new = check(member.display_name)
                if new != member.display_name:
                    if not self.bot.beta:
                        await member.edit(nick=new)
                    count += 1
            except discord.Forbidden:
                pass
        await ctx.send(await self.bot._(ctx.guild.id,"moderation.unhoisted",count=count))

    @commands.hybrid_command(name="destop")
    @app_commands.default_permissions(manage_messages=True)
    @commands.guild_only()
    @commands.check(checks.can_clear)
    @commands.cooldown(2, 30, commands.BucketType.channel)
    async def destop(self, ctx:MyContext, start_message:discord.Message):
        """Clear every message between now and an older message
        Message can be either ID or url
        Limited to 1,000 messages

        ..Example destop https://discordapp.com/channels/356067272730607628/488769306524385301/740249890201796688

        ..Doc moderator.html#clear"""
        if start_message.guild != ctx.guild:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.destop.no-guild"))
            return
        if not start_message.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-manage-messages"))
            return
        if not start_message.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-read-history"))
            return
        if start_message.created_at < ctx.bot.utcnow() - datetime.timedelta(days=21):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.destop.too-old", days=21))
            return
        await ctx.defer()
        messages = await start_message.channel.purge(after=start_message, before=ctx.message, limit=1000, oldest_first=False)
        await start_message.delete()
        messages.append(start_message)
        txt = await self.bot._(ctx.guild.id, "moderation.clear.done", count=len(messages))
        await ctx.send(txt, delete_after=2.0)
        log = await self.bot._(ctx.guild.id,"logs.clear", channel=start_message.channel.mention, number=len(messages))
        await self.bot.get_cog("Events").send_logs_per_server(ctx.guild, "clear", log, ctx.author)


    async def configure_muted_role(self, guild: discord.Guild, role: discord.Role = None):
        """Ajoute le rôle muted au serveur, avec les permissions nécessaires"""
        if not guild.me.guild_permissions.manage_roles:
            return None, 0
        if role is None:
            role = await guild.create_role(name="muted")
        count = 0 # nbr of errors
        try:
            for x in guild.by_category():
                category, channelslist = x[0], x[1]
                for channel in channelslist:
                    if channel is None:
                        continue
                    if len(channel.changed_roles) != 0 and not channel.permissions_synced:
                        try:
                            await channel.set_permissions(role, send_messages=False)
                            for r in channel.changed_roles:
                                if r.managed and len(r.members) == 1 and r.members[0].bot:
                                    # if it's an integrated bot role
                                    continue
                                obj = channel.overwrites_for(r)
                                if obj.send_messages:
                                    obj.send_messages = None
                                    await channel.set_permissions(r, overwrite=obj)
                        except discord.errors.Forbidden:
                            count += 1
                if category is not None and category.permissions_for(guild.me).manage_roles:
                    await category.set_permissions(role, send_messages=False)
        except Exception as err:
            self.bot.dispatch("error", err)
            count = len(guild.channels)
        await self.bot.get_cog("ServerConfig").set_option(guild.id, "muted_role", role)
        return role, count



async def setup(bot):
    await bot.add_cog(Moderation(bot))
