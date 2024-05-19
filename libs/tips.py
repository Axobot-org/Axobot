import datetime
import random
from enum import Enum
from typing import TYPE_CHECKING, Optional, TypedDict, Union

import discord
from cachetools import TTLCache

if TYPE_CHECKING:
    from bot_classes import Axobot, MyContext


class UserTip(str, Enum):
    "Tips that can be shown to users"
    RANK_CARD_PERSONALISATION = "rank_card_personalisation"


class GuildTip(str, Enum):
    "Tips that can be shown to guilds"
    SERVERLOG_ENABLE_ANTISCAM = "serverlog_enable_antiscam"
    SERVERLOG_ENABLE_ANTIRAID = "serverlog_enable_antiraid"
    SERVERLOG_ENABLE_BOTWARNING = "serverlog_enable_botwarning"
    RSS_DIFFERENCE_DISABLE_DELETE = "rss_difference_disable_delete"
    RSS_DELETE_DISABLED_FEEDS = "rss_delete_disabled_feeds"


minTimeBetweenTips: dict[Union[UserTip, GuildTip], datetime.timedelta] = {
    UserTip.RANK_CARD_PERSONALISATION: datetime.timedelta(days=60),
    GuildTip.SERVERLOG_ENABLE_ANTISCAM: datetime.timedelta(days=14),
    GuildTip.SERVERLOG_ENABLE_ANTIRAID: datetime.timedelta(days=14),
    GuildTip.SERVERLOG_ENABLE_BOTWARNING: datetime.timedelta(days=25),
    GuildTip.RSS_DIFFERENCE_DISABLE_DELETE: datetime.timedelta(days=60),
    GuildTip.RSS_DELETE_DISABLED_FEEDS: datetime.timedelta(days=30),
}


class TipsManager:
    "Handle tips displayed to users"

    def __init__(self, bot: "Axobot"):
        self.bot = bot
        self.user_cache = TTLCache[int, list[self.UserTipsFetchResult]](maxsize=10_000, ttl=60 * 60 * 2)
        self.guild_cache = TTLCache[int, list[self.GuildTipsFetchResult]](maxsize=10_000, ttl=60 * 60 * 2)
        self._random_tips_params: Optional[dict[str, str]] = None

    async def get_random_tips_params(self) -> dict[str, str]:
        "Get the translation parameters for the random tips"
        if self._random_tips_params:
            return self._random_tips_params
        self._random_tips_params  = {
            "about_cmd": await self.bot.get_command_mention("about"),
            "bigtext_cmd": await self.bot.get_command_mention("bigtext"),
            "clear_cmd": await self.bot.get_command_mention("clear"),
            "config_cmd": await self.bot.get_command_mention("config"),
            "discordlinks_cmd": await self.bot.get_command_mention("discordlinks"),
            "event_cmd": await self.bot.get_command_mention("event info"),
            "stats_cmd": await self.bot.get_command_mention("stats"),
            "say_cmd": await self.bot.get_command_mention("say"),
            "sponsor_url": "https://github.com/sponsors/ZRunner",
            "rss_disable_cmd": await self.bot.get_command_mention("rss disable"),
            "rss_delete_cmd": await self.bot.get_command_mention("rss delete"),
            "support_server_url": "https://discord.gg/N55zY88",
            "antiscam_enable_cmd": await self.bot.get_command_mention("antiscam enable"),
        }
        return self._random_tips_params

    class UserTipsFetchResult(TypedDict):
        tip_id: UserTip
        shown_at: datetime.datetime

    async def db_get_user_tips(self, user_id: int) -> list[UserTipsFetchResult]:
        "Get list of tips shown to a user"
        if value := self.user_cache.get(user_id):
            return value
        query = "SELECT tip_id, shown_at FROM tips WHERE user_id = %s"
        async with self.bot.db_query(query, (user_id,)) as query_result:
            self.user_cache[user_id] = query_result
            return query_result

    class GuildTipsFetchResult(TypedDict):
        tip_id: GuildTip
        shown_at: datetime.datetime

    async def db_get_guild_tips(self, guild_id: int) -> list["GuildTipsFetchResult"]:
        "Get list of tips shown to a guild"
        if value := self.guild_cache.get(guild_id):
            return value
        query = "SELECT tip_id, shown_at FROM tips WHERE guild_id = %s"
        async with self.bot.db_query(query, (guild_id,)) as query_result:
            self.guild_cache[guild_id] = query_result
            return query_result

    async def db_register_user_tip(self, user_id: int, tip: UserTip):
        "Register a tip as shown to a user"
        query = "INSERT INTO tips (user_id, tip_id) VALUES (%s, %s)"
        async with self.bot.db_query(query, (user_id, tip.value)):
            new_record = {"tip_id": tip, "shown_at": self.bot.utcnow()}
            if tips_list := self.user_cache.get(user_id):
                tips_list.append(new_record)
            else:
                self.user_cache[user_id] = [new_record]

    async def db_register_guild_tip(self, guild_id: int, tip: GuildTip):
        "Register a tip as shown to a guild"
        query = "INSERT INTO tips (guild_id, tip_id) VALUES (%s, %s)"
        async with self.bot.db_query(query, (guild_id, tip.value)):
            pass

    async def db_get_last_user_tip_shown(self, user_id: int, tip: UserTip) -> Optional[datetime.datetime]:
        "Get the last time a tip has been shown to a user"
        if user_tips := self.user_cache.get(user_id):
            sorted_tips = sorted(user_tips, key=lambda x: x["shown_at"], reverse=True)
            for tip_dict in sorted_tips:
                if tip_dict["tip_id"] == tip:
                    return tip_dict["shown_at"]
        query = "SELECT MAX(shown_at) FROM tips WHERE user_id = %s AND tip_id = %s"
        async with self.bot.db_query(query, (user_id, tip.value), astuple=True) as query_result:
            if query_result[0][0]:
                return query_result[0][0].replace(tzinfo=datetime.UTC)
            return None

    async def db_get_last_guild_tip_shown(self, guild_id: int, tip: GuildTip) -> Optional[datetime.datetime]:
        "Get the last time a tip has been shown to a guild"
        query = "SELECT MAX(shown_at) FROM tips WHERE guild_id = %s AND tip_id = %s"
        async with self.bot.db_query(query, (guild_id, tip.value), astuple=True) as query_result:
            if query_result[0][0]:
                return query_result[0][0].replace(tzinfo=datetime.UTC)
            return None

    async def should_show_user_tip(self, user_id: int, tip: UserTip) -> bool:
        "Check if a tip should be shown to a user"
        last_tip = await self.db_get_last_user_tip_shown(user_id, tip)
        if last_tip is None:
            return True
        return self.bot.utcnow() - last_tip > minTimeBetweenTips[tip]

    async def should_show_guild_tip(self, guild_id: int, tip: GuildTip) -> bool:
        "Check if a tip should be shown into a guild"
        last_tip = await self.db_get_last_guild_tip_shown(guild_id, tip)
        if last_tip is None:
            return True
        return self.bot.utcnow() - last_tip > minTimeBetweenTips[tip]

    async def send_user_tip(self, ctx: "MyContext", tip: UserTip, ephemeral: Optional[bool]=None, **variables: dict[str, str]):
        "Send a tip to a user"
        possible_titles = await self.bot._(ctx, "tips.embed.title")
        text = await self.bot._(ctx, f"tips.{tip.value}", **variables)
        embed = discord.Embed(
            title=random.choice(possible_titles),
            description=text,
            color=discord.Color.blurple(),
        )
        if ephemeral is not None:
            await ctx.send(embed=embed, ephemeral=ephemeral)
        else:
            await ctx.send(embed=embed)
        await self.db_register_user_tip(ctx.author.id, tip)

    async def send_guild_tip(self, ctx: "MyContext", tip: GuildTip, **variables: dict[str, str]):
        "Send a tip into a guild"
        possible_titles = await self.bot._(ctx, "tips.embed.title")
        text = await self.bot._(ctx, f"tips.{tip.value}", **variables)
        embed = discord.Embed(
            title=random.choice(possible_titles),
            description=text,
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)
        await self.db_register_guild_tip(ctx.guild.id, tip)

    async def generate_random_tip(self, translation_context) -> str:
        "Pick a random tip from the translations list, and format it"
        params = await self.get_random_tips_params()
        return random.choice(await self.bot._(translation_context, "fun.tip-list", **params))
