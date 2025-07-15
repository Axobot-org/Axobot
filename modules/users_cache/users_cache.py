import time
from collections import defaultdict

import discord
from discord.ext import commands, tasks

from core.bot_classes import Axobot


class UsersCache(commands.Cog):
    "Cache usernames and avatars into our database"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "users_cache"
        self.last_save: dict[int, int] = defaultdict(int)

    async def cog_load(self):
        # pylint: disable=no-member
        self.delete_old_cache_loop.start()

    async def cog_unload(self):
        # pylint: disable=no-member
        if self.delete_old_cache_loop.is_running():
            self.delete_old_cache_loop.stop()

    async def register_user(self, user: discord.User | discord.Member):
        "Register a user into our database"
        if (user.global_name is None and not user.bot) or time.time() - self.last_save[user.id] < 60*30:
            return
        self.last_save[user.id] = int(time.time())
        avatar_hash = user.avatar.key if user.avatar else None
        global_name = user.global_name or user.name
        query = "INSERT INTO `users_cache` (`user_id`, `username`, `global_name`, `avatar_hash`, `is_bot`, `last_seen`) \
VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP()) ON DUPLICATE KEY UPDATE `username` = VALUES(`username`), \
`global_name` = VALUES(`global_name`), `avatar_hash` = VALUES(`avatar_hash`), `is_bot` = VALUES(`is_bot`), \
`last_seen` = VALUES(`last_seen`);"
        async with self.bot.db_main.write(query, (user.id, user.name, global_name, avatar_hash, user.bot)):
            pass


    @tasks.loop(hours=24)
    async def delete_old_cache_loop(self):
        "Remove old cache data (older than 30 days)"
        query = "DELETE FROM `users_cache` WHERE `last_seen` < DATE_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY);"
        async with self.bot.db_main.write(query):
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        "Use messages event to update user data"
        if message.webhook_id:
            return
        await self.register_user(message.author)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        "Use member join event to update user data"
        await self.register_user(member)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        "Use interaction event to update user data"
        await self.register_user(interaction.user)


async def setup(bot: Axobot):
    await bot.add_cog(UsersCache(bot))
