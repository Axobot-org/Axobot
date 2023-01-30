import importlib
import json
import time
import typing

import discord
from discord.ext import commands
from libs.bot_classes import MyContext, Axobot
from libs.enums import RankCardsFlag, UserFlag

from . import args, checks

importlib.reload(args)
importlib.reload(checks)


class Users(commands.Cog):

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'users'

    async def get_userflags(self, user: discord.User) -> list[str]:
        """Check what user flags has a user"""
        if not self.bot.database_online:
            return []
        parameters = None
        try:
            if cog := self.bot.get_cog("Utilities"):
                get_data = cog.get_db_userinfo
            else:
                return False
            parameters = await get_data(criters=["userID="+str(user.id)], columns=['user_flags'])
        except Exception as err:
            self.bot.dispatch("error", err)
        if parameters is None:
            return []
        return UserFlag().int_to_flags(parameters['user_flags'])

    async def has_userflag(self, user: discord.User, flag: str) -> bool:
        """Check if a user has a specific user flag"""
        if flag not in UserFlag.FLAGS.values():
            return False
        return flag in await self.get_userflags(user)

    async def get_rankcards(self, user: discord.User) -> list[str]:
        """Check what rank cards got unlocked by a user"""
        if not self.bot.database_online:
            return []
        parameters = None
        try:
            if cog := self.bot.get_cog("Utilities"):
                get_data = cog.get_db_userinfo
            else:
                return []
            parameters = await get_data(criters=["userID="+str(user.id)], columns=['rankcards_unlocked'])
        except Exception as err:
            self.bot.dispatch("error", err)
        if parameters is None:
            return []
        return RankCardsFlag().int_to_flags(parameters['rankcards_unlocked'])

    async def has_rankcard(self, user: discord.User, rankcard: str) -> bool:
        """Check if a user has unlocked a specific rank card"""
        if rankcard not in RankCardsFlag.FLAGS.values():
            return False
        return rankcard in await self.get_rankcards(user)

    async def set_rankcard(self, user: discord.User, style: str, add: bool=True):
        """Add or remove a rank card style for a user"""
        if style not in RankCardsFlag.FLAGS.values():
            raise ValueError(f"Unknown card style: {style}")
        rankcards: list = await self.get_rankcards(user)
        if style in rankcards and add:
            return
        if style not in rankcards and not add:
            return
        if add:
            rankcards.append(style)
        else:
            rankcards.remove(style)
        await self.bot.get_cog('Utilities').change_db_userinfo(
            user.id,
            'rankcards_unlocked',
            RankCardsFlag().flags_to_int(rankcards)
        )

    async def get_rankcards_stats(self) -> dict:
        """Get how many users use any rank card"""
        if not self.bot.database_online:
            return {}
        try:
            query = "SELECT xp_style, Count(*) as count FROM `users` WHERE used_rank=1 GROUP BY xp_style"
            async with self.bot.db_query(query, astuple=True) as query_results:
                result = {x[0]: x[1] for x in query_results}
        except Exception as err:
            self.bot.dispatch("error", err)
            return {}
        if '' in result:
            result['default'] = result.pop('')
        return result

    async def used_rank(self, user_id: int):
        """Write in the database that a user used its rank card"""
        if not self.bot.database_online:
            return
        if cog := self.bot.get_cog("Utilities"):
            await cog.change_db_userinfo(user_id, "used_rank", True)

    async def reload_event_rankcard(self, user: typing.Union[discord.User, int], cards: list = None, points: int = None):
        """Grant the current event rank card to the provided user, if they have enough points
        'cards' and 'points' arguments can be provided to avoid re-fetching the database"""
        if (events_cog := self.bot.get_cog("BotEvents")) is None:
            return
        if events_cog.current_event is None or len(rewards := await events_cog.get_specific_objectives("rankcard")) == 0:
            return
        if isinstance(user, int):
            user = self.bot.get_user(user)
            if user is None:
                return
        if cards is None:
            cards = await self.get_rankcards(user)
        if points is None:
            points = await self.bot.get_cog("Utilities").get_eventsPoints_rank(user.id)
            points = 0 if (points is None) else points["events_points"]
        for reward in rewards:
            if reward["rank_card"] not in cards and points >= reward["points"]:
                await self.set_rankcard(user, reward["rank_card"], True)

    @commands.group(name='profile')
    async def profile_main(self, ctx: MyContext):
        """Get and change info about yourself"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @profile_main.command(name='card-preview')
    @commands.check(checks.database_connected)
    @commands.cooldown(3,45,commands.BucketType.user)
    @commands.cooldown(5,60,commands.BucketType.guild)
    async def profile_cardpreview(self, ctx: MyContext, style: args.cardStyle):
        """Get a preview of a card style

        ..Example profile card-preview red

        ..Doc user.html#change-your-xp-card"""
        if ctx.bot_permissions.attach_files:
            txts = [await self.bot._(ctx.channel, 'xp.card-level'), await self.bot._(ctx.channel, 'xp.card-rank')]
            desc = await self.bot._(ctx.channel, 'users.card-desc')
            await ctx.send(desc,file=await self.bot.get_cog('Xp').create_card(ctx.author,style,25,0,[1,0],txts,force_static=True))
        else:
            await ctx.send(await self.bot._(ctx.channel, 'users.missing-attach-files'))

    @profile_main.command(name='card')
    @commands.check(checks.database_connected)
    async def profile_card(self, ctx: MyContext, style: typing.Optional[args.cardStyle]=None):
        """Change your xp card style.
        If no style is specified, the bot will send a preview of the current selected style (dark by default)

        ..Example profile card

        ..Example profile card christmas20

        ..Doc user.html#change-your-xp-card"""
        if style is None and len(ctx.view.buffer.split(' '))>2:
            available_cards = ', '.join(await ctx.bot.get_cog('Utilities').allowed_card_styles(ctx.author))
            if ctx.view.buffer.split(' ')[2] == 'list':
                try:
                    await self.reload_event_rankcard(ctx.author.id)
                except Exception as err:
                    self.bot.dispatch("error", err)
                await ctx.send(await self.bot._(ctx.channel, 'users.list-cards', cards=available_cards))
            else:
                await ctx.send(await self.bot._(ctx.channel, 'users.invalid-card', cards=available_cards))
            return
        elif style is None:
            if ctx.channel.permissions_for(ctx.me).attach_files:
                style = await self.bot.get_cog('Utilities').get_xp_style(ctx.author)
                txts = [await self.bot._(ctx.channel, 'xp.card-level'), await self.bot._(ctx.channel, 'xp.card-rank')]
                desc = await self.bot._(ctx.channel, 'users.card-desc')
                await ctx.send(desc,file=await self.bot.get_cog('Xp').create_card(ctx.author,style,25,0,[1,0],txts,force_static=True))
            else:
                await ctx.send(await self.bot._(ctx.channel, 'users.missing-attach-files'))
        else:
            if await ctx.bot.get_cog('Utilities').change_db_userinfo(ctx.author.id,'xp_style',style):
                await ctx.send(await self.bot._(ctx.channel, 'users.changed-card', style=style))
                last_update = self.get_last_rankcard_update(ctx.author.id)
                if last_update is None:
                    await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id,15)
                elif last_update < time.time()-86400:
                    await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id,2)
                self.set_last_rankcard_update(ctx.author.id)
            else:
                await ctx.send(await self.bot._(ctx.channel, 'users.changed-error'))

    @profile_main.command(name="config")
    @commands.check(checks.database_connected)
    async def user_config(self, ctx: MyContext, option: str, allow: bool=None):
        """Modify any config option
        Here you can (dis)allow one of the users option that Zbot have, which are:
        - animated_card: Display an animated rank card if your pfp is a gif (way slower rendering)
        - auto_unafk: Automatically remove your AFK mode
        - usernames_log: Record when you change your username/nickname

        Value can only be a boolean (true/false)
        Providing empty value will show you the current value and more details"""
        options = {"animated_card":"animated_card", "auto_unafk":"auto_unafk", "usernames_log":"allow_usernames_logs"}
        if option not in options:
            await ctx.send(await self.bot._(ctx.channel, "users.config_list", options=" - ".join(options.keys())))
            return
        if allow is None:
            value = await self.bot.get_cog('Utilities').get_db_userinfo([options[option]],[f'`userID`={ctx.author.id}'])
            if value is None:
                value = False
            else:
                value = value[options[option]]
            if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).external_emojis:
                emojis = self.bot.emojis_manager.customs['green_check'], self.bot.emojis_manager.customs['red_cross']
            else:
                emojis = ('✅','❎')
            if value:
                await ctx.send(emojis[0]+" "+await self.bot._(ctx.channel, f'users.set_config.{option}.true'))
            else:
                await ctx.send(emojis[1]+" "+await self.bot._(ctx.channel, f'users.set_config.{option}.false'))
        else:
            if await self.bot.get_cog('Utilities').change_db_userinfo(ctx.author.id,options[option],allow):
                await ctx.send(await self.bot._(ctx.channel, 'users.config_success', opt=option))
            else:
                await ctx.send(await self.bot._(ctx.channel, 'users.changed-error'))

    def get_last_rankcard_update(self, user_id: int):
        "Get the timestamp of the last rank card change for a user"
        try:
            with open("rankcards_update.json", 'r', encoding="ascii") as file:
                records: dict[str, int] = json.load(file)
        except FileNotFoundError:
            return None
        return records.get(str(user_id))

    def set_last_rankcard_update(self, user_id: int):
        "Set the timestamp of the last rank card change for a user as now"
        try:
            with open("rankcards_update.json", 'r', encoding="ascii") as file:
                old: dict[str, int] = json.load(file)
        except FileNotFoundError:
            old: dict[str, int] = {}
        old[str(user_id)] = round(time.time())
        with open("rankcards_update.json", 'w', encoding="ascii") as file:
            json.dump(old, file)

async def setup(bot):
    await bot.add_cog(Users(bot))
