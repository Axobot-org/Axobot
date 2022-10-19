import asyncio
import copy
import datetime
import importlib
import random
import re
from math import ceil
from typing import Dict, List, Literal, Optional, Tuple, Union

import discord
from discord.ext import commands
from libs.bot_classes import MyContext, Zbot
from libs.formatutils import FormatUtils
from libs.paginator import Paginator

from . import args, checks
from fcts.cases import Case

importlib.reload(checks)
importlib.reload(args)

class Moderation(commands.Cog):
    """Here you will find everything you need to moderate your server.
    Please note that most of the commands are reserved for certain members only."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "moderation"
        # maximum of roles granted/revoked by query
        self.max_roles_modifications = 300

    @commands.command(name="slowmode")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.check(checks.can_slowmode)
    async def slowmode(self, ctx: MyContext, time=None):
        """Keep your chat cool
Slowmode works up to one message every 6h (21600s)

..Example slowmode 10

..Example slowmode off

..Doc moderator.html#slowmode"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.no-perm"))
            return
        if time is None:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.slowmode.info", s=ctx.channel.slowmode_delay))
        if time.isnumeric():
            time = int(time)
        if time == 'off' or time == 0:
            await ctx.channel.edit(slowmode_delay=0)
            message = await self.bot._(ctx.guild.id, "moderation.slowmode.disabled")
            log = await self.bot._(ctx.guild.id,"logs.slowmode-disabled", channel=ctx.channel.mention)
            await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"slowmode",log,ctx.author)
        elif isinstance(time, int):
            if time > 21600:
                message = await self.bot._(ctx.guild.id, "moderation.slowmode.too-long")
            else:
                await ctx.channel.edit(slowmode_delay=time)
                message = await self.bot._(ctx.guild.id, "moderation.slowmode.enabled", channel=ctx.channel.mention, s=time)
                log = await self.bot._(ctx.guild.id,"logs.slowmode-enabled", channel=ctx.channel.mention, seconds=time)
                await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"slowmode",log,ctx.author)
        else:
            message = await self.bot._(ctx.guild.id, "moderation.slowmode.invalid")
        await ctx.send(message)


    @commands.command(name="clear")
    @commands.cooldown(4, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_clear)
    async def clear(self, ctx: MyContext, number:int, *, params=''):
        """Keep your chat clean
        <number> : number of messages to check
        Available parameters :
            <@user> : list of users to check (just mention them)
            ('-f' or) '+f' : delete if the message  (does not) contain any file
            ('-l' or) '+l' : delete if the message (does not) contain any link
            ('-p' or) '+p' : delete if the message is (not) pinned
            ('-i' or) '+i' : delete if the message (does not) contain a Discord invite
        By default, the bot will not delete pinned messages

..Example clear 120

..Example clear 10 @someone

..Example clear 50 +f +l -p

..Doc moderator.html#clear"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-manage-messages"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-read-history"))
            return
        if number<1:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.clear.too-few")+" "+self.bot.emojis_manager.customs["owo"])
            return
        if len(params) == 0:
            return await self.clear_simple(ctx,number)
        #file
        if "-f" in params:
            files = 0
        elif "+f" in params:
            files = 2
        else:
            files = 1
        #link
        if "-l" in params:
            links = 0
        elif "+l" in params:
            links = 2
        else:
            links = 1
        #pinned
        if '-p' in params:
            pinned = 0
        elif "+p" in params:
            pinned = 2
        else:
            pinned = 1
        #invite
        if '-i' in params:
            invites = 0
        elif "+i" in params:
            invites = 2
        else:
            invites = 1
        # 0: does  -  2: does not  -  1: why do we care?
        def check(m):
            i = self.bot.get_cog("Utilities").sync_check_discord_invite(m.content)
            r = self.bot.get_cog("Utilities").sync_check_any_link(m.content)
            c1 = c2 = c3 = c4 = True
            if pinned != 1:
                if (m.pinned and pinned == 0) or (not m.pinned and pinned==2):
                    c1 = False
            else:
                c1 = not m.pinned
            if files != 1:
                if (m.attachments != [] and files == 0) or (m.attachments==[] and files==2):
                    c2 = False
            if links != 1:
                if (r is None and links==2) or (r is not None and links == 0):
                    c3 = False
            if invites != 1:
                if (i is None and invites==2) or (i is not None and invites == 0):
                    c4 = False
            #return ((m.pinned == pinned) or ((m.attachments != []) == files) or ((r is not None) == links)) and m.author in users
            mentions = list(map(int, re.findall(r'<@!?(\d{167,19})>', ctx.message.content)))
            if str(ctx.bot.user.id) in ctx.prefix:
                mentions.remove(ctx.bot.user.id)
            if mentions and m.author is not None:
                return c1 and c2 and c3 and c4 and m.author.id in mentions
            else:
                return c1 and c2 and c3 and c4
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=number, check=check)
            await ctx.send(await self.bot._(ctx.guild, "moderation.clear.done", count=len(deleted)), delete_after=2.0)
            if len(deleted) > 0:
                log = await self.bot._(ctx.guild.id, "logs.clear", channel=ctx.channel.mention, number=len(deleted))
                await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        except Exception as e:
            await self.bot.get_cog('Errors').on_command_error(ctx,e)

    async def clear_simple(self, ctx: MyContext, number: int):
        def check(m):
            return not m.pinned
        try:
            await ctx.message.delete()
            deleted = await ctx.channel.purge(limit=number, check=check)
            await ctx.send(await self.bot._(ctx.guild, "moderation.clear.done", count=len(deleted)), delete_after=2.0)
            log = await self.bot._(ctx.guild.id, "logs.clear", channel=ctx.channel.mention, number=len(deleted))
            await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        except discord.errors.NotFound:
            await ctx.send(await self.bot._(ctx.guild, "moderation.clear.not-found"))
        except Exception as e:
            await self.bot.get_cog('Errors').on_command_error(ctx,e)


    @commands.command(name="kick")
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
            async def user_can_kick(user):
                try:
                    return await self.bot.get_cog("Servers").staff_finder(user, "kick_allowed_roles")
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
            await ctx.guild.kick(user,reason=reason[:512])
            caseID = "'Unsaved'"
            if self.bot.database_online:
                Cases = self.bot.get_cog('Cases')
                case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="kick",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow())
                try:
                    await Cases.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e, ctx)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
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
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            await self.bot.get_cog('Errors').on_error(e,ctx)
        await self.bot.get_cog('Events').add_event('kick')


    @commands.command(name="warn")
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
                    return await self.bot.get_cog("Servers").staff_finder(user, "warn_allowed_roles")
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
                    case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="warn",ModID=ctx.author.id,Reason=message,date=ctx.bot.utcnow())
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
            except discord.Forbidden:
                pass
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            self.bot.dispatch("command_error", ctx, err)

    async def get_muted_role(self, guild: discord.Guild):
        "Find the muted role from the guild config option"
        opt = await self.bot.get_config(guild.id,'muted_role')
        if opt is None or (isinstance(opt, str) and not opt.isdigit()):
            return None
            # return discord.utils.find(lambda x: x.name.lower() == "muted", guild.roles)
        return guild.get_role(int(opt))

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

    @commands.command(name="mute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def mute(self, ctx: MyContext, user: discord.Member, time: commands.Greedy[args.tempdelta], *, reason="Unspecified"):
        """Mute someone.
When someone is muted, the bot adds the role "muted" to them
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
            f_duration = await FormatUtils.time_delta(duration,lang=await self.bot._(ctx.guild,'_used_locale'),form="short")
        else:
            f_duration = None
        try:
            async def user_can_mute(user):
                try:
                    return await self.bot.get_cog("Servers").staff_finder(user, "mute_allowed_roles")
                except commands.errors.CommandError:
                    pass
                return False
            if user==ctx.guild.me or (self.bot.database_online and await user_can_mute(user)):
                emoji = random.choice([':confused:',':upside_down:',self.bot.emojis_manager.customs['wat'],':no_mouth:',self.bot.emojis_manager.customs['owo'],':thinking:',])
                await ctx.send((await self.bot._(ctx.guild.id, "moderation.mute.staff-mute"))+emoji)
                return
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.bot._(ctx.guild.id, "moderation.warn.cant-staff"))
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,ctx)
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
                    case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="mute",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow())
                else:
                    case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="tempmute",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow(),duration=duration)
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
            except discord.Forbidden:
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

    async def bdd_muted_list(self, guild_id: int, reasons: bool = False) -> Union[List[Dict[int, str]], List[int]]:
        """List muted users for a specific guild
        Set 'reasons' to True if you want the attached reason"""
        if reasons:
            cases_table = "cases_beta" if self.bot.beta else "cases"
            query = f'SELECT userid, (SELECT reason FROM {cases_table} WHERE {cases_table}.user=userid AND {cases_table}.guild=guildid AND {cases_table}.type="mute" ORDER BY `{cases_table}`.`created_at` DESC LIMIT 1) as reason FROM `mutes` WHERE guildid=%s'
            async with self.bot.db_query(query, (guild_id,)) as query_results:
                result = {row['userid']: row['reason'] for row in query_results}
        else:
            query = 'SELECT userid FROM `mutes` WHERE guildid=%s'
            async with self.bot.db_query(query, (guild_id,)) as query_results:
                result = [row['userid'] for row in query_results]
        return result

    @commands.command(name="unmute")
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
        try:
            await self.unmute_event(ctx.guild, user, ctx.author)
            # send in chat
            await self.send_chat_answer("unmute", user, ctx)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
            # remove planned automatic unmutes
            await self.bot.task_handler.cancel_unmute(user.id, ctx.guild.id)
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            await self.bot.get_cog('Errors').on_error(err,ctx)

    @commands.command(name="mute-config")
    @commands.cooldown(1,15, commands.BucketType.guild)
    @commands.guild_only()
    @commands.has_guild_permissions(manage_roles=True)
    async def mute_config(self, ctx: MyContext):
        """Auto configure the muted role for you
        Useful if you want to have a base for a properly working muted role
        Warning: the process may break some things in your server, depending on how you configured your channel permissions.

        ..Doc moderator.html#mute-unmute
        """
        role = await self.get_muted_role(ctx.guild)
        create = role is None
        role, count = await self.configure_muted_role(ctx.guild, role)
        if role is None or count >= len(ctx.guild.voice_channels+ctx.guild.text_channels):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.mute-config-err"))
        elif create:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.mute-config-success", count=count))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.mute-config-success2", count=count))


    @commands.command(name="ban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_ban)
    async def ban(self,ctx:MyContext,user:args.user,time:commands.Greedy[args.tempdelta],days_to_delete:Optional[int]=0,*,reason="Unspecified"):
        """Ban someone
The 'days_to_delete' option represents the number of days worth of messages to delete from the user in the guild, bewteen 0 and 7

..Example ban @someone 3d You're bad

..Example ban someone#1234 7 Spam isn't tolerated here

..Example ban someone_else DM advertising is against Discord ToS!!!

..Doc moderator.html#ban-unban
        """
        try:
            duration = sum(time)
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
                        return await self.bot.get_cog("Servers").staff_finder(user, "ban_allowed_roles")
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
            await ctx.guild.ban(user,reason=reason[:512],delete_message_days=days_to_delete)
            await self.bot.get_cog('Events').add_event('ban')
            case_id = "'Unsaved'"
            if self.bot.database_online:
                Cases = self.bot.get_cog('Cases')
                if f_duration is None:
                    case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="ban",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow())
                else:
                    case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="tempban",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow(),duration=duration)
                    await self.bot.task_handler.add_task('ban',duration,user.id,ctx.guild.id)
                try:
                    await Cases.add_case(case)
                    case_id = case.id
                except Exception as err:
                    await self.bot.get_cog('Errors').on_error(err,ctx)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
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
            await self.bot.get_cog('Errors').on_error(err,ctx)

    async def unban_event(self, guild: discord.Guild, user: discord.User, author: discord.User):
        if not guild.me.guild_permissions.ban_members:
            return
        reason = await self.bot._(guild.id,"logs.reason.unban", user=author)
        await guild.unban(user, reason=reason[:512])
        # send in modlogs
        await self.send_modlogs("unban", user, author, guild, reason="Automod")

    @commands.command(name="unban")
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
                    await ctx.send(ctx.guild.id, "errors.usernotfound", u=user)
                    return
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.cant-ban"))
                return
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
                case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="unban",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow())
                try:
                    await cases_cog.add_case(case)
                    case_id = case.id
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e,ctx)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
            # optional values
            opt_case = None if case_id=="'Unsaved'" else case_id
            opt_reason = None if reason=="Unspecified" else reason
            # send in chat
            await self.send_chat_answer("unban", user, ctx, opt_case)
            # send in modlogs
            await self.send_modlogs("unban", user, ctx.author, ctx.guild, opt_case, opt_reason)
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            await self.bot.get_cog('Errors').on_error(e,ctx)

    @commands.command(name="softban")
    @commands.guild_only()
    @commands.check(checks.can_kick)
    async def softban(self, ctx: MyContext, user:discord.Member, *, reason="Unspecified"):
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
                    return await self.bot.get_cog("Servers").staff_finder(user, "kick_allowed_roles")
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
                case = Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="softban",ModID=ctx.author.id,Reason=reason,date=ctx.bot.utcnow())
                try:
                    await Cases.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e,ctx)
            try:
                await ctx.message.delete()
            except discord.Forbidden:
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
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            await self.bot.get_cog('Errors').on_error(e,ctx)

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
        except discord.Forbidden:
            pass
        except discord.HTTPException as e:
            if e.code == 50007:
                # "Cannot send message to this user"
                return
            await self.bot.get_cog('Errors').on_error(e, ctx)
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e, ctx)

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

    @commands.command(name="banlist")
    @commands.guild_only()
    @commands.check(checks.has_admin)
    @commands.check(checks.bot_can_embed)
    async def banlist(self, ctx: MyContext, reasons:bool=True):
        """Check the list of currently banned members.
The 'reasons' parameter is used to display the ban reasons.

You must be an administrator of this server to use this command.

..Doc moderator.html#banlist-mutelist"""
        if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.cant-ban"))
            return

        class BansPaginator(Paginator):
            "Paginator used to display banned users"
            saved_bans: list[discord.guild.BanEntry] = []
            users: set[int] = set()
            async def send_init(self, ctx: MyContext):
                "Create and send 1st page"
                contents = await self.get_page_content(None, 1)
                await self._update_buttons(None)
                await ctx.send(**contents, view=self)
            async def get_page_count(self, _: discord.Interaction) -> int:
                length = len(self.saved_bans)
                if length == 0:
                    return 1
                if length%1000 == 0:
                    return self.page+1
                return ceil(length/30)
            async def get_page_content(self, interaction: discord.Interaction, page: int):
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
                        if reasons:
                            values = [f"{entry.user}  *({entry.reason})*" for entry in self.saved_bans[i:i+10]]
                        else:
                            values = [str(entry.user) for entry in self.saved_bans[i:i+10]]
                        emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(values))
                footer = f"{ctx.author}  |  {page}/{await self.get_page_count(interaction)}"
                emb.set_footer(text=footer, icon_url=ctx.author.display_avatar)
                return {
                    "embed": emb
                }

        _quit = await self.bot._(ctx.guild, "misc.quit")
        view = BansPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
        await view.send_init(ctx)


    @commands.command(name="mutelist")
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def mutelist(self, ctx: MyContext, reasons:bool=True):
        """Check the list of currently muted members.
The 'reasons' parameter is used to display the mute reasons.

..Doc moderator.html#banlist-mutelist"""
        try:
            liste = await self.bdd_muted_list(ctx.guild.id, reasons=reasons)
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.error"))
            await self.bot.get_cog("Errors").on_command_error(ctx, e)
            return
        desc = list()
        title = await self.bot._(ctx.guild.id, "moderation.mute.list-title-0", guild=ctx.guild.name)
        if len(liste) == 0:
            desc.append(await self.bot._(ctx.guild.id, "moderation.mute.no-mutes"))
        elif reasons:
            _unknown = (await self.bot._(ctx.guild, "misc.unknown")).capitalize()
            for userid, reason in liste.items():
                user: Optional[discord.User] = self.bot.get_user(userid)
                if user is None:
                    continue
                if len(desc) >= 45:
                    break
                _reason = reason if (
                    reason is not None and reason != "Unspecified") else _unknown
                desc.append("{}  *({})*".format(user, _reason))
            if len(liste) > 45: # overwrite title with limit
                title = await self.bot._(ctx.guild.id, "moderation.mute.list-title-1", guild=ctx.guild.name)
        else:
            for userid in liste[:45]:
                user: Optional[discord.User] = self.bot.get_user(userid)
                if user is None:
                    continue
                if len(desc) >= 60:
                    break
                desc.append(str(user))
            if len(liste) > 60: # overwrite title with limit
                title = await self.bot._(ctx.guild.id, "moderation.mute.list-title-2", guild=ctx.guild.name)
        embed = discord.Embed(title=title, color=self.bot.get_cog("Servers").embed_color,
                              description="\n".join(desc), timestamp=ctx.message.created_at)
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        try:
            await ctx.send(embed=embed, delete_after=20)
        except discord.errors.HTTPException as e:
            if e.code == 400:
                await ctx.send(await self.bot._(ctx.guild.id, "moderation.ban.list-error"))


    @commands.group(name="emoji",aliases=['emojis', 'emote'])
    @commands.guild_only()
    @commands.cooldown(5,20, commands.BucketType.guild)
    async def emoji_group(self, ctx: MyContext):
        """Manage your emoji
        Administrator permission is required

        ..Doc moderator.html#emoji-manager"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx,['emoji'])

    @emoji_group.command(name="rename")
    @commands.check(checks.has_manage_emojis)
    async def emoji_rename(self, ctx: MyContext, emoji: discord.Emoji, name: str):
        """Rename an emoji

        ..Example emoji rename :cool: supercool

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
        except discord.Forbidden:
            pass

    @emoji_group.command(name="info")
    @commands.check(checks.has_manage_emojis)
    async def emoji_info(self, ctx: MyContext, emoji: discord.Emoji):
        """Get info about an emoji
        This is only an alias or `info emoji`

        ..Example info :owo:"""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + "info emoji " + str(emoji.id)
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @emoji_group.command(name="list")
    @commands.check(checks.bot_can_embed)
    async def emoji_list(self, ctx: MyContext, page: int = 1):
        """List every emoji of your server

        ..Example emojis list

        ..Example emojis list 2

        ..Doc moderator.html#emoji-manager"""
        if page < 1:
            await ctx.send(await self.bot._(ctx.guild.id, "xp.low-page"))
            return
        structure = await self.bot._(ctx.guild.id, "moderation.emoji.list")
        date = FormatUtils.date
        lang = await self.bot._(ctx.guild.id,'_used_locale')
        priv = "**"+await self.bot._(ctx.guild.id, "moderation.emoji.private")+"**"
        title = await self.bot._(ctx.guild.id, "moderation.emoji.list-title", guild=ctx.guild.name)
        try:
            emotes = [structure.format(x,x.name,await date(x.created_at,lang,year=True,hour=False,digital=True),priv if len(x.roles) > 0 else '') for x in ctx.guild.emojis if not x.animated]
            emotes += [structure.format(x,x.name,await date(x.created_at,lang,year=True,hour=False,digital=True),priv if len(x.roles) > 0 else '') for x in ctx.guild.emojis if x.animated]
            if (page-1)*50 >= len(emotes):
                await ctx.send(await self.bot._(ctx.guild.id, "xp.high-page"))
                return
            emotes = emotes[(page-1)*50:page*50]
            nbr = len(emotes)
            embed = discord.Embed(title=title, color=self.bot.get_cog('Servers').embed_color)
            for i in range(0, min(50, nbr), 10):
                emotes_list = list()
                for emote in emotes[i:i+10]:
                    emotes_list.append(emote)
                field_name = "{}-{}".format(i+1, i+10 if i+10 < nbr else nbr)
                embed.add_field(name=field_name, value="\n".join(emotes_list), inline=False)
            embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.bot.get_cog('Errors').on_command_error(ctx,e)


    @commands.group(name="role", aliases=["roles"])
    @commands.guild_only()
    async def main_role(self, ctx: MyContext):
        """A few commands to manage roles

        ..Doc moderator.html#emoji-manager"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx,['role'])

    @main_role.command(name="color",aliases=['colour'])
    @commands.check(checks.has_manage_roles)
    async def role_color(self, ctx: MyContext, role: discord.Role, color: discord.Color):
        """Change a color of a role

        ..Example role color "Admin team" red

        ..Doc moderator.html#role-manager"""
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
            return
        if role.position >= ctx.guild.me.roles[-1].position:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.too-high",r=role.name))
            return
        await role.edit(colour=color,reason="Asked by {}".format(ctx.author))
        await ctx.send(await self.bot._(ctx.guild.id,"moderation.role.color-success", role=role.name))

    @main_role.command(name="list")
    @commands.cooldown(5,30,commands.BucketType.guild)
    async def role_list(self, ctx: MyContext, *, role: discord.Role):
        """Send the list of members in a role

        ..Example role list "Technical team"

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

    @main_role.command(name="server-list",aliases=["glist"])
    @commands.check(checks.bot_can_embed)
    @commands.cooldown(5,30,commands.BucketType.guild)
    async def role_glist(self, ctx:MyContext):
        """Check the list of every role

        ..Example role glist

        ..Doc moderator.html#role-manager"""
        if not (await checks.has_manage_roles(ctx) or await checks.has_manage_guild(ctx) or await checks.has_manage_msg(ctx)):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.missing-user-perms"))
            return
        tr_mbr = await self.bot._(ctx.guild.id,"misc.membres")
        title = await self.bot._(ctx.guild.id, "moderation.role.list")
        desc = list()
        count = 0
        for role in ctx.guild.roles[1:]:
            txt = "{} - {} {}".format(role.mention, len(role.members), tr_mbr)
            if count+len(txt) > 2040:
                emb = discord.Embed(title=title, description="\n".join(desc), color=ctx.guild.me.color, timestamp=ctx.message.created_at)
                emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
                await ctx.send(embed=emb)
                desc.clear()
                count = 0
            desc.append(txt)
            count += len(txt)+2
        if count > 0:
            emb = discord.Embed(title=title, description="\n".join(desc), color=ctx.guild.me.color, timestamp=ctx.message.created_at)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)


    @main_role.command(name="info")
    @commands.check(checks.has_manage_msg)
    async def role_info(self, ctx: MyContext, role:discord.Role):
        """Get info about a role
        This is only an alias or `info role`

        ..Example role info VIP+

        ..Doc moderator.html#role-manager"""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + "info role " + str(role.id)
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @main_role.command(name="give", aliases=["add", "grant"])
    @commands.check(checks.has_manage_roles)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def roles_give(self, ctx:MyContext, role:discord.Role, users:commands.Greedy[Union[discord.Role,discord.Member,Literal['everyone']]]):
        """Give a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role give Elders everyone

        ..Example role give Slime Theo AsiliS

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

    @main_role.command(name="remove", aliases=["revoke"])
    @commands.check(checks.has_manage_roles)
    @commands.cooldown(1, 30, commands.BucketType.guild)
    async def roles_remove(self, ctx:MyContext, role:discord.Role, users:commands.Greedy[Union[discord.Role,discord.Member,Literal['everyone']]]):
        """Remove a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role remove VIP @muted

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
            if isinstance(item,discord.Member):
                if role not in item.roles:
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


    @commands.command(name="pin")
    @commands.check(checks.has_manage_msg)
    async def pin_msg(self, ctx: MyContext, msg: int):
        """Pin a message
ID corresponds to the Identifier of the message

..Example pin https://discord.com/channels/159962941502783488/201215818724409355/505373568184483851"""
        if ctx.guild is not None and not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.bot._(ctx.channel, "moderation.cant-pin"))
            return
        try:
            message = await ctx.channel.fetch_message(msg)
        except Exception as e:
            await ctx.send(await self.bot._(ctx.channel, "moderation.pin.error-notfound", err=e))
            return
        try:
            await message.pin()
        except Exception as e:
            await ctx.send(await self.bot._(ctx.channel, "moderation.pin.error-toomuch", err=e))
            return

    @commands.command(name='unhoist')
    @commands.guild_only()
    @commands.check(checks.has_manage_nicknames)
    async def unhoist(self, ctx: MyContext, chars: str=None):
        """Remove the special characters from usernames

        ..Example unhoist

        ..Example unhoist 0AZ^_

        ..Doc moderator.html#unhoist-members"""
        count = 0
        if not ctx.channel.permissions_for(ctx.guild.me).manage_nicknames:
            return await ctx.send(await self.bot._(ctx.guild.id,"moderation.missing-manage-nick"))
        if chars is None:
            def check(username: str):
                while username < '0':
                    username = username[1:]
                    if len(username) == 0:
                        username = "z unhoisted"
                return username
        else:
            chars = chars.lower()
            def check(username):
                while username[0].lower() in chars+' ':
                    username = username[1:]
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

    @commands.command(name="destop")
    @commands.guild_only()
    @commands.check(checks.can_clear)
    @commands.cooldown(2, 30, commands.BucketType.channel)
    async def destop(self, ctx:MyContext, message:discord.Message):
        """Clear every message between now and another message
        Message can be either ID or url
        Limited to 1,000 messages

        ..Example destop https://discordapp.com/channels/356067272730607628/488769306524385301/740249890201796688

        ..Doc moderator.html#clear"""
        if message.guild != ctx.guild:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.destop.no-guild"))
            return
        if not message.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-manage-messages"))
            return
        if not message.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.need-read-history"))
            return
        if message.created_at < ctx.bot.utcnow() - datetime.timedelta(days=21):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.destop.too-old", days=21))
            return
        messages = await message.channel.purge(after=message, limit=1000, oldest_first=False)
        await message.delete()
        messages.append(message)
        txt = await self.bot._(ctx.guild.id, "moderation.clear.done", count=len(messages))
        await ctx.send(txt, delete_after=2.0)
        log = await self.bot._(ctx.guild.id,"logs.clear", channel=message.channel.mention, number=len(messages))
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
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e, None)
            count = len(guild.channels)
        await self.bot.get_cog('Servers').modify_server(guild.id, values=[('muted_role',role.id)])
        return role, count



async def setup(bot):
    await bot.add_cog(Moderation(bot))
