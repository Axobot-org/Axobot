import asyncio
import importlib
import operator
import re
from typing import Any, List

import aiohttp
from cachingutils import acached
import discord
from discord.ext import commands
from libs.bot_classes import MyContext, Axobot
from libs.serverconfig.options_list import options

from . import args

importlib.reload(args)


class Utilities(commands.Cog):
    """This cog has various useful functions for the rest of the bot."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "utilities"
        self.config = {}
        self.table = 'users'
        self.new_pp = False
        bot.add_check(self.global_check)

    async def cog_unload(self):
        self.bot.remove_check(self.global_check)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.get_bot_infos()

    async def get_bot_infos(self):
        if not self.bot.database_online:
            return list()
        query = ("SELECT * FROM `bot_infos` WHERE `ID` = %s")
        async with self.bot.db_query(query, (self.bot.user.id,)) as query_results:
            config_list = list(query_results)
        if len(config_list) > 0:
            self.config: dict = config_list[0]
            self.config.pop('token', None)
            return self.config
        return None

    async def edit_bot_infos(self, bot_id: int, values: list[tuple[str, Any]]):
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError
        set_query = ', '.join('{}=%s'.format(val[0]) for val in values)
        query = f"UPDATE `bot_infos` SET {set_query} WHERE `ID`='{bot_id}'"
        async with self.bot.db_query(query, (val[1] for val in values)):
            pass
        return True

    async def find_img(self, name: str):
        return discord.File(f"assets/images/{name}")

    async def find_url_redirection(self, url: str) -> str:
        """Find where an url is redirected to"""
        timeout = aiohttp.ClientTimeout(total=10, connect=7)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, allow_redirects=True) as response:
                    answer = str(response.url)
        except aiohttp.ClientConnectorError as err:
            return "https://" + err.args[0].host
        except aiohttp.ClientResponseError as err:
            return str(err.args[0].real_url)
        except (asyncio.exceptions.TimeoutError, aiohttp.ServerTimeoutError):
            return url
        except ValueError as err:
            if err.args[0] != "URL should be absolute":
                self.bot.dispatch("error", err)
            return url
        return answer

    async def global_check(self, ctx: MyContext):
        """Do a lot of checks before executing a command (banned guilds, system message etc)"""
        if self.bot.zombie_mode:
            if isinstance(ctx, commands.Context) and ctx.command.name in self.bot.allowed_commands:
                return True
            return False
        if await self.bot.check_axobot_presence(ctx=ctx):
            if ctx.prefix and ctx.prefix.strip() == self.bot.user.mention:
                invite = 'http://discord.gg/N55zY88'
                await ctx.send(await self.bot._(ctx.guild.id, "errors.zbot-migration", invite=invite))
            return False
        if self.config is None:
            await self.get_bot_infos()
        if not isinstance(ctx, commands.Context) or self.config is None:
            return True
        if ctx.message.type not in {discord.MessageType.default, discord.MessageType.reply, discord.MessageType.chat_input_command}:
            if not ctx.message.type.value == discord.MessageType.chat_input_command:
                return False
        if await self.bot.get_cog('Admin').check_if_admin(ctx):
            return True
        elif not self.config:
            await self.get_bot_infos()
        if len(self.config) == 0 or self.config is None:
            return True
        if ctx.guild is not None:
            if str(ctx.guild.id) in self.config['banned_guilds'].split(";"):
                return False
        if str(ctx.author.id) in self.config['banned_users'].split(";"):
            return False
        return True

    async def get_members_repartition(self, members: List[discord.Member]):
        """Get number of total/online/bots members in a selection"""
        bots = online = total = unverified = 0
        for u in members:
            if u.bot:
                bots += 1
            if u.status != discord.Status.offline:
                online += 1
            if u.pending:
                unverified += 1
            total += 1
        return total, bots, online, unverified

    def sync_check_any_link(self, text: str):
        "Check if a text contains a http url"
        pattern = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(pattern, text)

    def sync_check_discord_invite(self, text: str):
        "Check if a text contains a discord invite url"
        pattern = r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)"
        return re.search(pattern, text)

    async def clear_msg(self, text: str, everyone: bool=False, ctx: MyContext=None, emojis: bool=True):
        """Remove every mass mention from a text, and add custom emojis"""
        if emojis:
            for x in re.finditer(r'(?<!<|a):([^:<]+):', text):
                try:
                    if ctx is not None:
                        em = await commands.EmojiConverter().convert(ctx, x.group(1))
                    else:
                        emoji_id = x.group(1)
                        if emoji_id.isnumeric():
                            em = self.bot.get_emoji(int(emoji_id))
                        else:
                            em = discord.utils.find(
                                lambda e, id=emoji_id: e.name == id, self.bot.emojis)
                except (commands.BadArgument, commands.EmojiNotFound):
                    continue
                if em is not None:
                    text = text.replace(x.group(0), "<{}:{}:{}>".format(
                        'a' if em.animated else '', em.name, em.id))
        return text

    async def get_xp_style(self, user: discord.User) -> str:
        if config := await self.bot.get_cog("Users").db_get_userinfo(user.id):
            if config["xp_style"]:
                return config['xp_style']
        return 'dark'

    @acached(timeout=60)
    async def allowed_card_styles(self, user: discord.User):
        """Retourne la liste des styles autorisées pour la carte d'xp de cet utilisateur"""
        liste = ['blue', 'dark', 'green', 'grey', 'orange',
                 'purple', 'red', 'turquoise', 'yellow']
        if not self.bot.database_online:
            return sorted(liste)
        liste2 = []
        if await self.bot.get_cog('Admin').check_if_admin(user):
            liste2.append('admin')
        if not self.bot.database_online:
            return sorted(liste2)+sorted(liste)
        userflags = await self.bot.get_cog('Users').get_userflags(user)
        for flag in ("support", "contributor", "partner", "premium"):
            if flag in userflags:
                liste2.append(flag)
        for card in await self.bot.get_cog('Users').get_rankcards(user):
            liste.append(card)
        return sorted(liste2)+sorted(liste)

    async def get_languages(self, user: discord.User, limit: int=0):
        """Get the most used languages of an user
        If limit=0, return every languages"""
        if not self.bot.database_online:
            return [("en", 1.0)]
        languages = []
        disp_lang: list[tuple[str, float]] = []
        available_langs: list[str] = options["language"]["values"]
        for guild in user.mutual_guilds:
            lang: str = await self.bot.get_config(guild.id, "language")
            languages.append(lang)
        for lang in available_langs:
            if (count := languages.count(lang)) > 0:
                disp_lang.append((
                    lang,
                    round(count/len(languages), 2)
                ))
        disp_lang.sort(key=operator.itemgetter(1), reverse=True)
        if limit == 0:
            return disp_lang
        return disp_lang[:limit]

    async def add_user_eventPoint(self, user_id: int, points: int, override: bool = False, check_event: bool = True):
        """Add some events points to a user
        if override is True, then the number of points will override the old score"""
        try:
            if not self.bot.database_online:
                return True
            if check_event and self.bot.current_event is None:
                return True
            if override:
                query = ("INSERT INTO `{t}` (`userID`,`events_points`) VALUES ('{u}',{p}) ON DUPLICATE KEY UPDATE events_points = '{p}';".format(
                    t=self.table, u=user_id, p=points))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`events_points`) VALUES ('{u}',{p}) ON DUPLICATE KEY UPDATE events_points = events_points + '{p}';".format(
                    t=self.table, u=user_id, p=points))
            async with self.bot.db_query(query):
                pass
            try:
                await self.bot.get_cog("Users").reload_event_rankcard(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False

    async def get_eventsPoints_rank(self, user_id: int):
        "Get the ranking of an user"
        if not self.bot.database_online:
            return None
        query = (
            f"SELECT `userID`, `events_points`, FIND_IN_SET( `events_points`, ( SELECT GROUP_CONCAT( `events_points` ORDER BY `events_points` DESC ) FROM {self.table} ) ) AS rank FROM {self.table} WHERE `userID` = {user_id}")
        async with self.bot.db_query(query, fetchone=True) as query_results:
            return query_results

    async def get_eventsPoints_top(self, number: int):
        "Get the event points leaderboard containing at max the given number of users"
        if not self.bot.database_online:
            return None
        query = f"SELECT `userID`, `events_points` FROM {self.table} WHERE `events_points` != 0 ORDER BY `events_points` DESC LIMIT {number}"
        async with self.bot.db_query(query) as query_results:
            return query_results

    async def get_eventsPoints_nbr(self) -> int:
        if not self.bot.database_online:
            return 0
        query = f"SELECT COUNT(*) as count FROM {self.table} WHERE events_points > 0"
        async with self.bot.db_query(query, fetchone=True) as query_results:
            return query_results['count']

    async def check_votes(self, userid: int) -> list[tuple[str, str]]:
        """check if a user voted on any bots list website"""
        votes = list()
        async with aiohttp.ClientSession() as session:
            try:  # https://top.gg/bot/486896267788812288
                async with session.get(f'https://top.gg/api/bots/486896267788812288/check?userId={userid}', headers={'Authorization': str(self.bot.dbl_token)}) as r:
                    json = await r.json()
                    if json["error"]:
                        raise ValueError("Error while checking votes on top.gg: "+json["error"])
                    elif json["voted"]:
                        votes.append(("Discord Bots List", "https://top.gg/"))
            except Exception as err:
                self.bot.dispatch("error", err)
        return votes


async def setup(bot):
    await bot.add_cog(Utilities(bot))
