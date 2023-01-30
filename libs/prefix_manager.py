from typing import TYPE_CHECKING

import discord
from cachingutils import LRUCache

from libs.serverconfig.options_list import default_values as serverconfig_defaults

if TYPE_CHECKING:
    from libs.bot_classes import Axobot


class PrefixManager:
    """Manage prefixes for the bot, with cache and everything"""

    def __init__(self, bot: 'Axobot'):
        self.bot = bot
        self.cache: LRUCache[int, str] = LRUCache(max_size=1000, timeout=3600)

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
            if server_cog := self.bot.get_cog("Servers"):
                return serverconfig_defaults.get("prefix")
            return '!'
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
        # if we can't load the server cog
        # pylint: disable=superfluous-parens
        if not (server_cog := self.bot.get_cog("Servers")):
            raise RuntimeError("Server cog not loaded")
        # prepare the SQL query
        query = f"SELECT `prefix` FROM `servers` WHERE `ID` = %s AND `beta` = %s"
        # get the thing
        async with self.bot.db_query(query, (guild_id, self.bot.beta), fetchone=True) as query_result:
            if query_result and len(query_result['prefix']) > 0:
                prefix: str = query_result['prefix']
            else:
                prefix = '!'
        # and return
        return prefix

    async def update_prefix(self, guild_id: int, prefix: str):
        "Update a prefix for a guild"
        self.bot.log.debug(
            "Prefix updated for guild %s : changed to %s", guild_id, prefix)
        self.cache[guild_id] = prefix
