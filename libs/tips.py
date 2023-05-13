import datetime
import random
from enum import Enum
from typing import TYPE_CHECKING, Optional, TypedDict, Union

import discord
from cachingutils import LRUCache

if TYPE_CHECKING:
    from bot_classes import Axobot, MyContext


class UserTip(str, Enum):
    RANK_CARD_PERSONALISATION = "rank_card_personalisation"


class GuildTip(str, Enum):
    SERVERLOG_ENABLE_ANTISCAM = "serverlog_enable_antiscam"
    SERVERLOG_ENABLE_ANTIRAID = "serverlog_enable_antiraid"


minTimeBetweenTips: dict[Union[UserTip, GuildTip], datetime.timedelta] = {
    UserTip.RANK_CARD_PERSONALISATION: datetime.timedelta(days=60),
    GuildTip.SERVERLOG_ENABLE_ANTISCAM: datetime.timedelta(days=14),
    GuildTip.SERVERLOG_ENABLE_ANTIRAID: datetime.timedelta(days=14),
}


class TipsManager:
    "Handle tips displayed to users"

    def __init__(self, bot: "Axobot"):
        self.bot = bot
        _cache_init: dict[int, list[self.UserTipsFetchResult]] = {}
        self.user_cache = LRUCache(max_size=10_000, timeout=3_600 * 2, values=_cache_init)
        self.guild_cache = LRUCache(max_size=10_000, timeout=3_600 * 2, values=dict(_cache_init))

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
        query = "SELECT tip_id, shown_at FROM tips WHERE guild_id = %s"
        async with self.bot.db_query(query, (guild_id,)) as query_result:
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
                return query_result[0][0].replace(tzinfo=datetime.timezone.utc)
            return None

    async def db_get_last_guild_tip_shown(self, guild_id: int, tip: GuildTip) -> Optional[datetime.datetime]:
        "Get the last time a tip has been shown to a guild"
        query = "SELECT MAX(shown_at) FROM tips WHERE guild_id = %s AND tip_id = %s"
        async with self.bot.db_query(query, (guild_id, tip.value), astuple=True) as query_result:
            if query_result[0][0]:
                return query_result[0][0].replace(tzinfo=datetime.timezone.utc)
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

    async def send_user_tip(self, ctx: "MyContext", tip: UserTip, **variables: dict[str, str]):
        "Send a tip to a user"
        possible_titles = await self.bot._(ctx, "tips.embed.title")
        text = await self.bot._(ctx, f"tips.{tip.value}", **variables)
        embed = discord.Embed(
            title=random.choice(possible_titles),
            description=text,
            color=discord.Color.blurple(),
        )
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
