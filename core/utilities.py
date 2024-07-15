import asyncio
import operator
import re
from typing import Any

import aiohttp
import discord
from asyncache import cached
from cachetools import TTLCache
from discord.ext import commands

from core.bot_classes import Axobot, MyContext


class Utilities(commands.Cog):
    """This cog has various useful functions for the rest of the bot."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "utilities"
        self.config = {}
        self.table = "users"
        self.new_pp = False
        bot.add_check(self.global_check)

    async def cog_unload(self):
        self.bot.remove_check(self.global_check)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.get_bot_infos()

    async def get_bot_infos(self):
        """Get the bot's infos from the database"""
        if not self.bot.database_online:
            return {}
        query = "SELECT * FROM `bot_infos` WHERE `ID` = %s"
        async with self.bot.db_main.read(query, (self.bot.user.id,)) as query_results:
            config_list: list[dict] = list(query_results)
        if len(config_list) > 0:
            self.config = config_list[0]
            self.config.pop("token", None)
            return self.config
        return None

    async def edit_bot_infos(self, bot_id: int, values: list[tuple[str, Any]]):
        """Edit the bot's infos in the database"""
        if not isinstance(values, list) or len(values) == 0:
            raise ValueError
        set_query = ", ".join(f"{val[0]}=%s" for val in values)
        query = f"UPDATE `bot_infos` SET {set_query} WHERE `ID`=%s"
        async with self.bot.db_main.write(query, tuple(val[1] for val in values) + (bot_id,)):
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
        if self.config is None:
            await self.get_bot_infos()
        if not isinstance(ctx, commands.Context) or self.config is None:
            return True
        if ctx.message.type not in {
            discord.MessageType.default, discord.MessageType.reply, discord.MessageType.chat_input_command
        }:
            if not ctx.message.type.value == discord.MessageType.chat_input_command:
                return False
        if await self.bot.get_cog("Admin").check_if_admin(ctx):
            return True
        elif not self.config:
            await self.get_bot_infos()
        if len(self.config) == 0 or self.config is None:
            return True
        if ctx.guild is not None:
            if str(ctx.guild.id) in self.config["banned_guilds"].split(";"):
                return False
        if str(ctx.author.id) in self.config["banned_users"].split(";"):
            return False
        return True

    def sync_check_any_link(self, text: str):
        "Check if a text contains a http url"
        pattern = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(pattern, text)

    def sync_check_discord_invite(self, text: str):
        "Check if a text contains a discord invite url"
        pattern = r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)"
        return re.search(pattern, text)

    async def get_xp_style(self, user: discord.User) -> str:
        "Return the chosen rank card style for a user"
        if config := await self.bot.get_cog("Users").db_get_userinfo(user.id):
            if config["xp_style"]:
                return config["xp_style"]
        return self.bot.get_cog("Xp").default_xp_style

    @cached(TTLCache(maxsize=10_000, ttl=60))
    async def allowed_card_styles(self, user: discord.User):
        """Retourne la liste des styles autorisées pour la carte d'xp de cet utilisateur"""
        liste = ["blue", "dark", "green", "grey", "orange",
                 "purple", "red", "turquoise", "yellow"]
        if not self.bot.database_online:
            return sorted(liste)
        liste2 = []
        if await self.bot.get_cog("Admin").check_if_admin(user):
            liste2.append("admin")
        if not self.bot.database_online:
            return sorted(liste2)+sorted(liste)
        userflags = await self.bot.get_cog("Users").get_userflags(user)
        for flag in ("support", "contributor", "partner", "premium"):
            if flag in userflags:
                liste2.append(flag)
        for card in await self.bot.get_cog("Users").get_rankcards(user):
            liste.append(card)
        return sorted(liste2)+sorted(liste)

    async def get_languages(self, user: discord.User, limit: int=0):
        """Get the most used languages of an user
        If limit=0, return every languages"""
        if not self.bot.database_online:
            return [("en", 1.0)]
        languages = []
        disp_lang: list[tuple[str, float]] = []
        available_langs: list[str] = (await self.bot.get_options_list())["language"]["values"]
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

    async def check_votes(self, userid: int) -> list[tuple[str, str]]:
        """check if a user voted on any bots list website"""
        votes = []
        async with aiohttp.ClientSession() as session:
            try:  # https://top.gg/bot/1048011651145797673
                async with session.get(
                    f"https://top.gg/api/bots/{self.bot.user.id}/check?userId={userid}",
                    headers={"Authorization": str(self.bot.secrets["dbl"])}
                ) as r:
                    json = await r.json()
                    if "error" in json:
                        raise ValueError("Error while checking votes on top.gg: "+json["error"])
                    if json["voted"]:
                        votes.append(("Discord Bots List", "https://top.gg/"))
            except Exception as err:
                self.bot.dispatch("error", err)
        return votes


async def setup(bot):
    await bot.add_cog(Utilities(bot))
