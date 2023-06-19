import importlib
from datetime import datetime
from math import ceil
from typing import Any, Optional

import discord
from discord.ext import commands

from fcts import args
from libs.checks.checks import database_connected, is_support_staff
from libs.bot_classes import Axobot, MyContext
from libs.formatutils import FormatUtils
from libs.paginator import Paginator

importlib.reload(args)


async def can_edit_case(ctx: MyContext):
    "Check if the context user can edit or delete a moderation case"
    if await ctx.bot.get_cog('Admin').check_if_admin(ctx.author):
        return True
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "warn_allowed_roles")
    return False

class Case:
    "Represents a moderation case"

    def __init__(self, bot: Axobot, guild_id: int, user_id: int, case_type: str, mod_id: int, reason: str, date: datetime,
                 duration: Optional[int]=None, case_id: Optional[int]=None):
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.type = case_type
        self.mod_id = mod_id
        self.reason = reason
        self.duration = duration
        self.id = case_id
        if date is None:
            self.date = "Unknown"
        else:
            self.date = date

    async def display(self, display_guild: bool=False):
        "Format a case to be human readable"
        if user := self.bot.get_user(self.user_id):
            f_user = user.mention
        else:
            f_user = self.user_id
        if guild := self.bot.get_guild(self.guild_id):
            f_guild = guild.name
        else:
            f_guild = self.guild_id
        text = await self.bot._(self.guild_id, "cases.title-search", ID=self.id)
        # add guild name if needed
        if display_guild:
            text += await self.bot._(self.guild_id, "cases.display.guild", data=f_guild)
        # add fields
        for key, value in (
            ("type", self.type),
            ("user", f_user),
            ("moderator", self.mod_id),
            ("date", self.date or self.bot._(self.guild_id, "misc.unknown")),
            ("reason", self.reason)):
            text += await self.bot._(self.guild_id, "cases.display."+key, data=value)
        # add duration if exists
        if self.duration is not None and self.duration > 0:
            lang = await self.bot._(self.guild_id, "_used_locale")
            duration_ = await FormatUtils.time_delta(self.duration,lang=lang,form="short")
            text += await self.bot._(self.guild_id, "cases.display.duration", data=duration_)
        return text

    def copy(self):
        return Case(self.bot, self.guild_id, self.user_id, self.type, self.mod_id, self.reason, self.date, self.duration, self.id)


class Cases(commands.Cog):
    """This part of the bot allows you to manage all your members' cases, to delete or edit them"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "cases"

    @property
    def table(self):
        return 'cases_beta' if self.bot.beta else 'cases'

    async def _convert_db_row_to_case(self, row: dict[str, Any]):
        return Case(
            bot=self.bot,
            guild_id=row['guild'],
            case_id=row['ID'],
            user_id=row['user'],
            case_type=row['type'],
            mod_id=row['mod'],
            date=row['created_at'],
            reason=row['reason'],
            duration=row['duration']
        )

    async def db_get_user_cases_in_guild(self, guild_id: int, user_id: int) -> list[Case]:
        "Get all cases of a user in a guild"
        if not self.bot.database_online:
            return []
        query = f"SELECT * FROM `{self.table}` WHERE `guild` = %s AND `user` = %s"
        async with self.bot.db_query(query, (guild_id, user_id)) as query_results:
            return [await self._convert_db_row_to_case(row) for row in query_results]

    async def db_get_all_user_cases(self, user_id: int) -> list[Case]:
        "Get all cases of a user"
        if not self.bot.database_online:
            return []
        query = f"SELECT * FROM `{self.table}` WHERE `user` = %s"
        async with self.bot.db_query(query, (user_id,)) as query_results:
            return [await self._convert_db_row_to_case(row) for row in query_results]

    async def db_get_case_from_id(self, guild_id: int, case_id: int):
        "Get a case from its id"
        if not self.bot.database_online:
            return None
        query = f"SELECT * FROM `{self.table}` WHERE `guild` = %s AND `ID` = %s"
        async with self.bot.db_query(query, (guild_id, case_id)) as query_results:
            if len(query_results) == 1:
                return await self._convert_db_row_to_case(query_results[0])
        return None

    async def db_get_user_cases_count_from_guild(self, user_id: int, guild_id: int) -> int:
        """Get the number of users infractions"""
        if not self.bot.database_online:
            return 0
        try:
            query = f"SELECT COUNT(*) as count FROM `{self.table}` WHERE `user` = %s AND `guild` = %s AND `type` <> 'unban'"
            async with self.bot.db_query(query, (user_id, guild_id), fetchone=True) as query_results:
                if len(query_results) == 1:
                    return query_results['count']
        except Exception as err:
            self.bot.dispatch("error", err)
        return 0

    async def db_delete_case(self, case_id: int):
        """delete a case from the db"""
        if not self.bot.database_online:
            return False
        if not isinstance(case_id, int):
            raise ValueError
        query = f"DELETE FROM `{self.table}` WHERE `ID` = %s"
        async with self.bot.db_query(query, (case_id,)):
            pass
        return True

    async def db_add_case(self, case: Case):
        """add a new case to the db"""
        if not self.bot.database_online:
            return False
        if not isinstance(case, Case):
            raise ValueError
        query = f"INSERT INTO `{self.table}` (`guild`, `user`, `type`, `mod`, `reason`,`duration`) VALUES (%(g)s, %(u)s, %(t)s, %(m)s, %(r)s, %(d)s)"
        query_args = { 'g': case.guild_id, 'u': case.user_id, 't': case.type, 'm': case.mod_id, 'r': case.reason, 'd': case.duration }
        async with self.bot.db_query(query, query_args) as last_row_id:
            case.id = last_row_id
        return True

    async def db_update_reason(self, case_id: int, new_reason: str):
        """update infos of a case"""
        if not self.bot.database_online:
            return False
        query = f"UPDATE `{self.table}` SET `reason` = %s WHERE `ID` = %s"
        async with self.bot.db_query(query, (new_reason, case_id)):
            pass
        return True


    @commands.group(name="cases", aliases=['case', 'infractions'])
    @commands.guild_only()
    @commands.cooldown(5, 15, commands.BucketType.user)
    @commands.check(can_edit_case)
    @commands.check(database_connected)
    async def case_main(self, ctx: MyContext):
        """Do anything with any user cases

        ..Doc moderator.html#handling-cases"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @case_main.command(name="list")
    @commands.guild_only()
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def see_case(self, ctx: MyContext, *, user:args.AnyUser):
        """Get every case of a user
        This user can have left the server

        ..Example cases list @someone

        ..Doc moderator.html#view-list"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        await self.see_case_main(ctx, ctx.guild.id, user)

    @case_main.command(name="glist")
    @commands.guild_only()
    @commands.check(is_support_staff)
    async def see_case_2(self, ctx: MyContext, guild: Optional[args.Guild], *, user: discord.User):
        """Get every case of a user on a specific guild or on every guilds
        This user can have left the server

        ..Example cases glist "Axobot Staff" someone

        ..Example cases glist someone"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        await self.see_case_main(ctx, guild.id if guild else None, user)

    async def see_case_main(self, ctx: MyContext, guild_id: Optional[int], user: discord.User):
        "Main method to show cases from a given user"
        if guild_id is None:
            syntax: str = await self.bot._(ctx.guild, 'cases.list-1')
            cases = await self.db_get_all_user_cases(user.id)
        else:
            syntax: str = await self.bot._(ctx.guild, 'cases.list-0')
            cases = await self.db_get_user_cases_in_guild(guild_id, user.id)
        cases.reverse()
        if not cases:
            await ctx.send(await self.bot._(ctx.guild.id, "cases.no-case"))
            return
        if ctx.can_send_embed:
            author_text = await self.bot._(ctx.guild.id, "cases.display.title", user=user.display_name, user_id=user.id)
            title = await self.bot._(ctx.guild.id,"cases.records_number", nbr=len(cases))
            lang = await self.bot._(ctx.guild.id,'_used_locale')

            class RecordsPaginator(Paginator):
                "Paginator used to display a user record"
                users: dict[int, Optional[discord.User]]

                async def get_page_count(self) -> int:
                    length = len(cases)
                    if length == 0:
                        return 1
                    return ceil(length/21)

                async def get_page_content(self, interaction, page):
                    "Create one page"
                    embed_color = self.client.get_cog("ServerConfig").embed_color
                    embed = discord.Embed(title=title, colour=embed_color, timestamp=ctx.message.created_at)
                    embed.set_author(name=author_text, icon_url=user.display_avatar.with_format("png").url)
                    page_start, page_end = (page-1)*21, page*21
                    for case in cases[page_start:page_end]:
                        guild = self.client.get_guild(case.guild_id)
                        if guild is None:
                            guild = case.guild_id
                        else:
                            guild = guild.name
                        mod = self.client.get_user(case.mod_id)
                        if mod is None:
                            mod = case.mod_id
                        else:
                            mod = mod.mention
                        date_ = f"<t:{case.date.timestamp():.0f}>"
                        text = syntax.format(G=guild, T=case.type, M=mod, R=case.reason, D=date_)
                        if case.duration is not None and case.duration > 0:
                            formated_duration = await FormatUtils.time_delta(case.duration, lang=lang, year=False, form="short")
                            text += "\n" + await self.client._(interaction, 'cases.display.duration', data=formated_duration)
                        embed.add_field(
                            name=await self.client._(interaction, "cases.title-search", ID=case.id),
                            value=text,
                            inline=True
                        )
                    footer = f"{ctx.author}  |  {page}/{await self.get_page_count()}"
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
                    case_text = (await case.display(True)).replace('*','')
                    text += f"```{case_text}\n```"
                    if len(text) > 1800:
                        await ctx.send(text)
                        text = ""
                if len(text) > 0:
                    await ctx.send(text)


    @case_main.command(name="edit-reason", aliases=["edit"])
    @commands.guild_only()
    async def reason(self, ctx: MyContext, case_id: int, *, new_reason: str):
        """Edit the reason of a case

        ..Example cases reason 95 Was too dumb

        ..Doc moderator.html#edit-reason"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        old_case = await self.db_get_case_from_id(ctx.guild.id, case_id)
        if old_case is None:
            await ctx.send(await self.bot._(ctx.guild.id,"cases.not-found"))
            return
        new_case = old_case.copy()
        new_case.reason = new_reason
        await self.db_update_reason(case_id, new_reason)
        await ctx.send(await self.bot._(ctx.guild.id,"cases.reason-edited", ID=case_id))
        self.bot.dispatch("case_edit", ctx.guild, old_case, new_case)

    @case_main.command(name="search")
    @commands.guild_only()
    async def search_case(self, ctx: MyContext, case_id: int):
        """Search for a specific case in your guild

        ..Example cases search 69

        ..Doc moderator.html#search-for-a-case"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id, 'cases.no_database'))
        case = await self.db_get_case_from_id(ctx.guild.id, case_id)
        if case is None:
            await ctx.send(await self.bot._(ctx.guild.id, "cases.not-found"))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.guild.id, "minecraft.cant-embed"))
            return
        if user := await self.bot.fetch_user(case.user_id):
            f_user = f"{user} ({user.id})"
        else:
            f_user = case.user_id
        if mod := await self.bot.fetch_user(case.mod_id):
            f_mod = f"{mod} ({mod.id})"
        else:
            f_mod = case.mod_id
        title = await self.bot._(ctx.guild.id, "cases.title-search", ID=case.id)
        lang = await self.bot._(ctx.guild.id, '_used_locale')
        # main structure
        if not await is_support_staff(ctx):
            f_guild = ctx.guild.name
            _msg = await self.bot._(ctx.guild.id, 'cases.search-0')
        else: # if support: add guild
            if guild := self.bot.get_guild(case.guild_id):
                f_guild = f"{guild.name} ({guild.id})"
            else:
                f_guild = case.guild_id
            _msg = await self.bot._(ctx.guild.id, 'cases.search-1')
        # add duration
        if case.duration is not None and case.duration > 0:
            f_duration = await FormatUtils.time_delta(case.duration, lang=lang, year=False, form="short")
            _msg += "\n" + await self.bot._(ctx.guild.id, 'cases.display.duration', data=f_duration)
        # format date
        f_date = f"<t:{case.date.timestamp():.0f}>"
        # finish message
        _msg = _msg.format(
            G=f_guild,
            U=f_user,
            T=case.type,
            M=f_mod,
            R=case.reason,
            D=f_date
        )
        # send embed
        embed_color = self.bot.get_cog('ServerConfig').embed_color
        emb = discord.Embed(title=title, description=_msg, color=embed_color, timestamp=ctx.message.created_at)
        emb.set_author(name=user, icon_url=user.display_avatar)
        await ctx.send(embed=emb)


    @case_main.command(name="remove", aliases=["delete"])
    @commands.guild_only()
    async def remove(self, ctx: MyContext, case_id: int):
        """Delete a case forever
        Warning: "Forever", it's very long. And no backups are done

        ..Example cases remove 42

        ..Doc moderator.html#remove-case"""
        if not self.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,'cases.no_database'))
        case = await self.db_get_case_from_id(ctx.guild.id, case_id)
        if case is None:
            await ctx.send(await self.bot._(ctx.guild.id,"cases.not-found"))
            return
        await self.db_delete_case(case.id)
        await ctx.send(await self.bot._(ctx.guild.id,"cases.deleted", ID=case.id))
        self.bot.dispatch("case_delete", ctx.guild, case)


async def setup(bot):
    await bot.add_cog(Cases(bot))
