import datetime
from enum import Enum
import random
from typing import TYPE_CHECKING, Optional, TypedDict, Union

import discord


if TYPE_CHECKING:
    from bot_classes import Axobot, MyContext


class UserTip(Enum):
    RANK_CARD_PERSONALISATION = "rank_card_personalisation"


class GuildTip(Enum):
    ...


minTimeBetweenTips: dict[Union[UserTip, GuildTip], datetime.timedelta] = {
    UserTip.RANK_CARD_PERSONALISATION: datetime.timedelta(days=60),
}


class TipsManager:
    "Handle tips displayed to users"

    def __init__(self, bot: "Axobot"):
        self.bot = bot

    class UserTipsFetchResult(TypedDict):
        tip_id: UserTip
        shown_at: datetime.datetime

    async def db_get_user_tips(self, user_id: int) -> list[UserTipsFetchResult]:
        "Get list of tips shown to a user"
        query = "SELECT tip_id, shown_at FROM tips WHERE user_id = %s"
        async with self.bot.db_query(query, (user_id,)) as query_result:
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
            pass

    async def db_register_guild_tip(self, guild_id: int, tip: GuildTip):
        "Register a tip as shown to a guild"
        query = "INSERT INTO tips (guild_id, tip_id) VALUES (%s, %s)"
        async with self.bot.db_query(query, (guild_id, tip.value)):
            pass

    async def db_get_last_user_tip_shown(self, user_id: int, tip: UserTip) -> Optional[datetime.datetime]:
        "Get the last time a tip has been shown to a user"
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

    async def send_tip(self, ctx: "MyContext", tip: UserTip, **variables: dict[str, str]):
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
