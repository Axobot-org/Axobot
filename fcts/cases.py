import importlib
from datetime import datetime
from math import ceil
from typing import Optional

import discord
from discord.ext import commands

from fcts.checks import is_support_staff
from libs.bot_classes import MyContext, Axobot
from libs.formatutils import FormatUtils
from libs.paginator import Paginator

from . import args

importlib.reload(args)


async def can_edit_case(ctx: MyContext):
    if await ctx.bot.get_cog('Admin').check_if_admin(ctx.author):
        return True
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "warn_allowed_roles")
    return False

class Case:
    def __init__(self, bot: Axobot, guild_id: int, member_id: int, case_type: str, mod_id: int, reason: str, date: datetime, duration: Optional[int]=None, case_id: Optional[int]=None):
        self.bot = bot
        self.guild = guild_id
        self.id = case_id
        self.user = member_id
        self.type = case_type
        self.mod = mod_id
        self.reason = reason
        self.duration = duration
        if date is None:
            self.date = "Unknown"
        else:
            self.date = date

    async def display(self, display_guild: bool=False) -> str:
        u = self.bot.get_user(self.user)
        if u is None:
            u = self.user
        else:
            u = u.mention
        g: discord.Guild = self.bot.get_guild(self.guild)
        if g is None:
            g = self.guild
        else:
            g = g.name
        text = await self.bot._(self.guild, "cases.title-search", ID=self.id)
        # add guild name if needed
        if display_guild:
            text += await self.bot._(self.guild, "cases.display.guild", data=g)
        # add fields
        for key, value in (
            ("type", self.type),
            ("user", u),
            ("moderator", self.mod),
            ("date", self.date or self.bot._(self.guild, "misc.unknown")),
            ("reason", self.reason)):
            text += await self.bot._(self.guild, "cases.display."+key, data=value)
        # add duration if exists
        if self.duration is not None and self.duration > 0:
            lang = await self.bot._(self.guild, "_used_locale")
            duration_ = await FormatUtils.time_delta(self.duration,lang=lang,form="short")
            text += await self.bot._(self.guild, "cases.display.duration", data=duration_)
        return text


class Cases(commands.Cog):
    """This part of the bot allows you to manage all your members' cases, to delete or edit them"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "cases"
        if bot.user is not None:
            self.table = 'cases_beta' if bot.beta else 'cases'

    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'cases_beta' if self.bot.beta else 'cases'

    async def get_case(self, columns=None, criters=None, relation="AND") -> Optional[list[Case]]:
        """return every cases"""
        if not self.bot.database_online:
            return None
        if columns is None:
            columns = []
        if criters is None:
            criters = ["1"]
        if not isinstance(columns, list) or not isinstance(criters, list):
            raise ValueError
        if len(columns) == 0:
            cl = "*"
        else:
            cl = "`"+"`,`".join(columns)+"`"
        relation = " "+relation+" "
        query = ("SELECT {} FROM `{}` WHERE {}".format(cl,self.table,relation.join(criters)))
        liste = list()
        async with self.bot.db_query(query) as query_results:
            if len(columns) == 0:
                for elem in query_results:
                    case = Case(
                        bot=self.bot,
                        guild_id=elem['guild'],
                        case_id=elem['ID'],
                        member_id=elem['user'],
                        case_type=elem['type'],
                        mod_id=elem['mod'],
                        date=elem['created_at'],
                        reason=elem['reason'], 
                        duration=elem['duration']
                    )
                    liste.append(case)
            else:
                for elem in query_results:
                    liste.append(elem)
        return liste

    async def get_nber(self, user_id:int, guild_id:int):
        """Get the number of users infractions"""
        try:
            query = ("SELECT COUNT(*) as count FROM `{}` WHERE `user`={} AND `guild`={} AND `type`!='unban'".format(self.table, user_id, guild_id))
            async with self.bot.db_query(query, fetchone=True) as query_results:
                if len(query_results) == 1:
                    return query_results['count']
            return 0
        except Exception as err:
            self.bot.dispatch("error", err)

    async def delete_case(self, case_id: int):
        """delete a case from the db"""
        if not self.bot.database_online:
            return False
        if not isinstance(case_id, int):
            raise ValueError
        query = ("DELETE FROM `{}` WHERE `ID`='{}'".format(self.table, case_id))
        async with self.bot.db_query(query):
            pass
        return True

    async def add_case(self, case):
        """add a new case to the db"""
        if not self.bot.database_online:
            return False
        if not isinstance(case, Case):
            raise ValueError
        query = "INSERT INTO `{}` (`guild`, `user`, `type`, `mod`, `reason`,`duration`) VALUES (%(g)s, %(u)s, %(t)s, %(m)s, %(r)s, %(d)s)".format(self.table)
        query_args = { 'g': case.guild, 'u': case.user, 't': case.type, 'm': case.mod, 'r': case.reason, 'd': case.duration }
        async with self.bot.db_query(query, query_args) as last_row_id:
            case.id = last_row_id
        return True

    async def update_reason(self, case):
        """update infos of a case"""
        if not self.bot.database_online:
            return False
        if not isinstance(case, Case):
            raise ValueError
        query = ("UPDATE `{}` SET `reason` = %s WHERE `ID` = %s".format(self.table))
        async with self.bot.db_query(query, (case.reason, case.id)):
            pass
        return True


    @commands.group(name="cases",aliases=['case', 'infractions'])
    @commands.guild_only()
    @commands.cooldown(5, 15, commands.BucketType.user)
    @commands.check(can_edit_case)
    async def case_main(self, ctx: MyContext):
        """Do anything with any user cases

        ..Doc moderator.html#handling-cases"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @case_main.command(name="list")
    @commands.guild_only()
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def see_case(self, ctx: MyContext, *, user:args.user):
        """Get every case of a user
        This user can have left the server

        ..Example cases list someone#7515

        ..Doc moderator.html#view-list"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        await self.see_case_main(ctx, ctx.guild.id, user)

    @case_main.command(name="glist")
    @commands.guild_only()
    @commands.check(is_support_staff)
    async def see_case_2(self, ctx: MyContext, guild: Optional[args.Guild], *, user:args.user):
        """Get every case of a user on a specific guild or on every guilds
        This user can have left the server

        ..Example cases glist "ZBot Staff" someone

        ..Example cases glist someone"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        await self.see_case_main(ctx, guild.id if guild else None, user)

    async def see_case_main(self, ctx: MyContext, guild: discord.Guild, user: discord.User):
        if guild is not None:
            criters = ["`user`='{}'".format(user.id),"guild='{}'".format(guild)]
            syntax: str = await self.bot._(ctx.guild,'cases.list-0')  
        else:
            syntax: str = await self.bot._(ctx.guild,'cases.list-1')
            criters = ["`user`='{}'".format(user.id)]
        try:
            MAX_CASES = 60
            cases = await self.get_case(criters=criters)
            cases.reverse()
            if cases is None or len(cases) == 0:
                await ctx.send(await self.bot._(ctx.guild.id, "cases.no-case"))
                return
            cases: list[Case]
            if ctx.can_send_embed:
                author_text = await self.bot._(ctx.guild.id, "cases.display.title", user=str(user), user_id=user.id)
                title = await self.bot._(ctx.guild.id,"cases.records_number", nbr=len(cases))
                lang = await self.bot._(ctx.guild.id,'_used_locale')

                class RecordsPaginator(Paginator):
                    "Paginator used to display a user record"
                    users: dict[int, Optional[discord.User]]

                    async def get_page_count(self, interaction) -> int:
                        length = len(cases)
                        if length == 0:
                            return 1
                        return ceil(length/21)

                    async def get_page_content(self, interaction, page):
                        "Create one page"
                        embed = discord.Embed(title=title, colour=self.client.get_cog('Servers').embed_color, timestamp=ctx.message.created_at)
                        embed.set_author(name=author_text, icon_url=str(user.display_avatar.with_format("png")))
                        page_start, page_end = (page-1)*21, page*21
                        for case in cases[page_start:page_end]:
                            guild = self.client.get_guild(case.guild)
                            if guild is None:
                                guild = case.guild
                            else:
                                guild = guild.name
                            mod = self.client.get_user(case.mod)
                            if mod is None:
                                mod = case.mod
                            else:
                                mod = mod.mention
                            date_ = f"<t:{case.date.timestamp():.0f}>"
                            text = syntax.format(G=guild, T=case.type, M=mod, R=case.reason, D=date_)
                            if case.duration is not None and case.duration > 0:
                                formated_duration = await FormatUtils.time_delta(case.duration,lang=lang,year=False,form="short")
                                text += "\n" + await self.client._(interaction,'cases.display.duration', data=formated_duration)
                            embed.add_field(name=await self.client._(interaction, "cases.title-search", ID=case.id), value=text, inline=True)
                        footer = f"{ctx.author}  |  {page}/{await self.get_page_count(interaction)}"
                        embed.set_footer(text=footer, icon_url=ctx.author.display_avatar)
                        return {
                            "embed": embed
                        }
                
                _quit = await self.bot._(ctx.guild, "misc.quit")
                view = RecordsPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
                await view.send_init(ctx)
            else:
                if len(cases) > 0:
                    text = await self.bot._(ctx.guild.id,"cases.records_number", nbr=len(cases)) + "\n"
                    for case in cases:
                        text += "```{}\n```".format((await case.display(True)).replace('*',''))
                        if len(text) > 1800:
                            await ctx.send(text)
                            text = ""
                    if len(text) > 0:
                        await ctx.send(text)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)


    @case_main.command(name="reason",aliases=['edit'])
    @commands.guild_only()
    async def reason(self, ctx: MyContext, case:int, *, reason):
        """Edit the reason of a case

        ..Example cases reason 95 Was too dumb

        ..Doc moderator.html#edit-reason"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        try:
            c = ["ID="+str(case)]
            if not await self.bot.get_cog('Admin').check_if_admin(ctx.author):
                c.append("guild="+str(ctx.guild.id))
            cases = await self.get_case(criters=c)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        if len(cases)!=1:
            await ctx.send(await self.bot._(ctx.guild.id,"cases.not-found"))
            return
        case = cases[0]
        old_reason = case.reason
        case.reason = reason
        await self.update_reason(case)
        await ctx.send(await self.bot._(ctx.guild.id,"cases.reason-edited", ID=case.id))
        log = await self.bot._(ctx.guild.id,"logs.case-reason",old=old_reason,new=case.reason,id=case.id)
        await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"case-edit",log,ctx.author)

    @case_main.command(name="search")
    @commands.guild_only()
    async def search_case(self, ctx: MyContext, case:int):
        """Search for a specific case in your guild

        ..Example cases search 69

        ..Doc moderator.html#search-for-a-case"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        try:
            isSupport = await is_support_staff(ctx)
            c = ["ID="+str(case)]
            if not isSupport:
                c.append("guild="+str(ctx.guild.id))
            cases = await self.get_case(criters=c)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        if len(cases)!=1:
            await ctx.send(await self.bot._(ctx.guild.id,"cases.not-found"))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.guild.id,"minecraft.cant-embed"))
            return
        try:
            case: Case = cases[0]
            user = await self.bot.fetch_user(case.user)
            mod = await self.bot.fetch_user(case.mod)
            u = "{} ({})".format(user,user.id)
            title = await self.bot._(ctx.guild.id,"cases.title-search", ID=case.id)
            l = await self.bot._(ctx.guild.id, '_used_locale')
            # main structure
            if not isSupport:
                guild = ctx.guild.name
                _msg = await self.bot._(ctx.guild.id,'cases.search-0')
            else: # if support: add guild
                guild = "{0.name} ({0.id})".format(self.bot.get_guild(case.guild))
                _msg = await self.bot._(ctx.guild.id,'cases.search-1')
            # add duration
            if case.duration is not None and case.duration > 0:
                _msg += "\n" + await self.bot._(ctx.guild.id,'cases.display.duration', data=await FormatUtils.time_delta(case.duration,lang=l,year=False,form="short"))
            # format date
            _date = f"<t:{case.date.timestamp():.0f}>"
            # finish message
            _msg = _msg.format(G=guild,U=u,T=case.type,M=str(mod),R=case.reason,D=_date)

            emb = discord.Embed(title=title, description=_msg, color=self.bot.get_cog('Servers').embed_color, timestamp=ctx.message.created_at)
            emb.set_author(name=user, icon_url=user.display_avatar)
            await ctx.send(embed=emb)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)


    @case_main.command(name="remove", aliases=["clear", "delete"])
    @commands.guild_only()
    async def remove(self, ctx: MyContext, case:int):
        """Delete a case forever
        Warning: "Forever", it's very long. And no backups are done

        ..Example cases remove 42

        ..Doc moderator.html#remove-case"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        try:
            c = ["ID="+str(case)]
            if not await self.bot.get_cog('Admin').check_if_admin(ctx.author):
                c.append("guild="+str(ctx.guild.id))
            cases = await self.get_case(columns=['ID','user'],criters=c)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        if len(cases) != 1:
            await ctx.send(await self.bot._(ctx.guild.id,"cases.not-found"))
            return
        case = cases[0]
        await self.delete_case(case['ID'])
        await ctx.send(await self.bot._(ctx.guild.id,"cases.deleted", ID=case['ID']))
        user = ctx.bot.get_user(case['user'])
        if user is None:
            user = case['user']
        log = await self.bot._(ctx.guild.id,"logs.case-del",id=case['ID'],user=str(user))
        await self.bot.get_cog("Events").send_logs_per_server(ctx.guild,"case-edit",log,ctx.author)


async def setup(bot):
    await bot.add_cog(Cases(bot))
