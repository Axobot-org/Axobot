import importlib
import json
import time
import typing

import discord
from discord.ext import commands
from libs.classes import MyContext, RankCardsFlag, UserFlag, Zbot

from fcts import args, checks

importlib.reload(args)
importlib.reload(checks)


class Users(commands.Cog):

    def __init__(self, bot: Zbot):
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
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e, None)
        if parameters is None:
            return []
        return UserFlag().intToFlags(parameters['user_flags'])

    async def has_userflag(self, user: discord.User, flag: str) -> bool:
        """Check if a user has a specific user flag"""
        if flag not in UserFlag.FLAGS.values():
            return False
        return flag in await self.get_userflags(user)
    
    async def get_rankcards(self, user: discord.User) -> list[str]:
        """Check what rank cards got unlocked by a user"""
        if not self.bot.database_online:
            return list()
        parameters = None
        try:
            if cog := self.bot.get_cog("Utilities"):
                get_data = cog.get_db_userinfo
            else:
                return list()
            parameters = await get_data(criters=["userID="+str(user.id)], columns=['rankcards_unlocked'])
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e, None)
        if parameters is None:
            return list()
        return RankCardsFlag().intToFlags(parameters['rankcards_unlocked'])

    async def has_rankcard(self, user: discord.User, rankcard: str) -> bool:
        """Check if a user has unlocked a specific rank card"""
        if rankcard not in RankCardsFlag.FLAGS.values():
            return False
        return rankcard in await self.get_rankcards(user)

    async def set_rankcard(self, user: discord.User, style: str, add: bool=True):
        """Add or remove a rank card style for a user"""
        if style not in RankCardsFlag.FLAGS.values():
            raise ValueError("Unknown card style")
        rankcards: list = await self.get_rankcards(user)
        if style in rankcards and add:
            return
        if style not in rankcards and not add:
            return
        if add:
            rankcards.append(style)
        else:
            rankcards.remove(style)
        await self.bot.get_cog('Utilities').change_db_userinfo(user.id, 'rankcards_unlocked', RankCardsFlag().flagsToInt(rankcards))

    async def get_rankcards_stats(self) -> dict:
        """Get how many users use any rank card"""
        if not self.bot.database_online:
            return dict()
        try:
            query = "SELECT xp_style, Count(*) as count FROM `users` WHERE used_rank=1 GROUP BY xp_style"
            async with self.bot.db_query(query, astuple=True) as query_results:
                result = {x[0]: x[1] for x in query_results}
        except Exception as err:
            await self.bot.get_cog("Errors").on_error(err, None)
            return dict()
        if '' in result:
            result['default'] = result.pop('')
        return result

    async def used_rank(self, userID: int):
        """Write in the database that a user used its rank card"""
        if not self.bot.database_online:
            return
        if cog := self.bot.get_cog("Utilities"):
            await cog.change_db_userinfo(userID, "used_rank", True)

    async def reload_event_rankcard(self, user: typing.Union[discord.User, int], cards: list = None, points: int = None):
        eventsCog = self.bot.get_cog("BotEvents")
        if eventsCog is None:
            return
        if eventsCog.current_event_id != "april-2022":
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
        if "april_22" not in cards and points >= self.bot.current_event_data["objectives"][0]:
            await self.set_rankcard(user, "april_22", True)

    @commands.group(name='profile')
    async def profile_main(self, ctx: MyContext):
        """Get and change info about yourself"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx,['profile'])
    
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
                except Exception as e:
                    await self.bot.get_cog("Errors").on_error(e, None)
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
        if option not in options.keys():
            await ctx.send(await self.bot._(ctx.channel, "users.config_list", options=" - ".join(options.keys())))
            return
        if allow is None:
            value = await self.bot.get_cog('Utilities').get_db_userinfo([options[option]],[f'`userID`={ctx.author.id}'])
            if value is None:
                value = False
            else:
                value = value[options[option]]
            if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).external_emojis:
                emojis = self.bot.get_cog('Emojis').customs['green_check'], self.bot.get_cog('Emojis').customs['red_cross']
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

    def get_last_rankcard_update(self, userID: int):
        try:
            with open("rankcards_update.json",'r') as f:
                r = json.load(f)
        except FileNotFoundError:
            return None
        if str(userID) in r.keys():
            return r[str(userID)]
        return None
    
    def set_last_rankcard_update(self, userID: int):
        try:
            with open("rankcards_update.json",'r') as f:
                old = json.load(f)
        except FileNotFoundError:
            old = dict()
        old[str(userID)] = round(time.time())
        with open("rankcards_update.json",'w') as f:
            json.dump(old,f)

async def setup(bot):
    await bot.add_cog(Users(bot))
