from typing import TYPE_CHECKING

import discord
from cachetools import TTLCache

from core.serverconfig.options_list import options as options_list

if TYPE_CHECKING:
    from core.bot_classes import Axobot


class PrefixManager:
    """Manage prefixes for the bot, with cache and everything"""

    def __init__(self, bot: "Axobot"):
        self.bot = bot
        self.cache = TTLCache[int, str](maxsize=1_000, ttl=60*60)

    async def get_prefix(self, guild: discord.Guild) -> str:
        "Find the prefix attached to a guild"
        # if using DMs
        if guild is None:
            return '!'
        # if prefix is in cache
        if cached := self.cache.get(guild.id):
            return cached
        # if bot is not fully loaded
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()
        # if database is offline
        if not self.bot.database_online:
            return options_list["prefix"]["default"]
        # get the prefix from the database
        prefix = await self.fetch_prefix(guild.id)
        # cache it
        self.cache[guild.id] = prefix
        # and return
        return prefix

    async def fetch_prefix(self, guild_id: int) -> str:
        "Search a prefix in the database, skipping the cache"
        # if database is offline
        if not self.bot.database_online:
            raise RuntimeError("Database is not loaded")
        # prepare the SQL query
        query = "SELECT `value` FROM `serverconfig` WHERE `guild_id` = %s AND `option_name` = 'prefix' AND `beta` = %s"
        # get the thing
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta), fetchone=True) as query_result:
            if query_result and len(query_result["value"]) > 0:
                prefix: str = query_result["value"]
            else:
                prefix = options_list["prefix"]["default"]
        # and return
        return prefix

    async def update_prefix(self, guild_id: int, prefix: str):
        "Update a prefix for a guild"
        self.bot.log.debug(
            "Prefix updated for guild %s : changed to %s", guild_id, prefix)
        self.cache[guild_id] = prefix

    async def reset_prefix(self, guild_id: int):
        "Reset the prefix cache for a guild"
        self.bot.log.debug("Prefix reset for guild %s", guild_id)
        if guild_id in self.cache:
            self.cache.pop(guild_id)
