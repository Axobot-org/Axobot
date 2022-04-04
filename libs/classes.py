import datetime
import logging
import time
from typing import Any, Callable, Coroutine, Optional

import discord
import mysql
import requests
from discord.ext import commands
from mysql.connector.connection import MySQLConnection
from mysql.connector.errors import ProgrammingError
from utils import get_prefix

from libs.database import create_database_query
from libs.prefix_manager import PrefixManager
from libs.tasks_handler import TaskHandler


class MyContext(commands.Context):
    """Replacement for the official commands.Context class
    It allows us to add more methods and properties in the whole bot code"""

    bot: 'Zbot'

    @property
    def bot_permissions(self) -> discord.Permissions:
        """Permissions of the bot in the current context"""
        if self.guild:
            # message in a guild
            return self.channel.permissions_for(self.guild.me)
        else:
            # message in DM
            return self.channel.permissions_for(self.bot)

    @property
    def user_permissions(self) -> discord.Permissions:
        """Permissions of the message author in the current context"""
        return self.channel.permissions_for(self.author)

    @property
    def can_send_embed(self) -> bool:
        """If the bot has the right permissions to send an embed in the current context"""
        return self.bot_permissions.embed_links

    async def send(self, *args, **kwargs) -> Optional[discord.Message]:
        if self.bot.zombie_mode and self.command.name not in self.bot.allowed_commands:
            return
        if self.message.type == discord.MessageType.reply and self.message.reference:
            kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", self.bot.allowed_mentions)
            kwargs["allowed_mentions"].replied_user = False
            return await super().send(reference=self.message.reference, *args, **kwargs)
        return await super().send(*args, **kwargs)


class Zbot(commands.bot.AutoShardedBot):
    """Bot class, with everything needed to run it"""

    def __init__(self, case_insensitive: bool = None, status: discord.Status = None, database_online: bool = True, \
            beta: bool = False, dbl_token: str = "", zombie_mode: bool = False):
        # pylint: disable=assigning-non-slot
        # defining allowed default mentions
        allowed_mentions = discord.AllowedMentions(everyone=False, roles=False)
        # defining intents usage
        intents = discord.Intents.all()
        intents.typing = False
        intents.webhooks = False
        intents.integrations = False
        # we now initialize the bot class
        super().__init__(command_prefix=get_prefix, case_insensitive=case_insensitive,
                         status=status, allowed_mentions=allowed_mentions, intents=intents, enable_debug_events=True)
        self.database_online = database_online  # if the mysql database works
        self.beta = beta # if the bot is in beta mode
        self.database_keys = {} # credentials for the database
        self.log = logging.getLogger("runner") # logs module
        self.dbl_token = dbl_token # token for Discord Bot List
        self._cnx = [[None, 0], [None, 0], [None, 0]] # database connections
        self.xp_enabled: bool = True # if xp is enabled
        self.rss_enabled: bool = True # if rss is enabled
        self.alerts_enabled: bool = True # if alerts system is enabled
        self.internal_loop_enabled: bool = True # if internal loop is enabled
        self.zws = "\u200B"  # here's a zero width space
        self.others = {} # other misc credentials
        self.zombie_mode: bool = zombie_mode # if we should listen without sending any message
        self.prefix_manager = PrefixManager(self)
        self.task_handler = TaskHandler(self)

    allowed_commands = ("eval", "add_cog", "del_cog")

    @property
    def current_event(self) -> Optional[str]:
        """Get the current event, from the date"""
        try:
            return self.get_cog("BotEvents").current_event
        except Exception as err: # pylint: disable=broad-except
            self.log.warning("[current_event] %s", err, exc_info=True)
            return None

    @property
    def current_event_data(self) -> Optional[dict]:
        """Get the current event data, from the date"""
        try:
            return self.get_cog("BotEvents").current_event_data
        except Exception as err: # pylint: disable=broad-except
            self.log.warning("[current_event_data] %s", err, exc_info=True)
            return None

    async def get_context(self, message: discord.Message, *, cls=MyContext) -> MyContext:
        """Get a custom context class when creating one from a message"""
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(message, cls=cls)

    @property
    def cnx_frm(self) -> MySQLConnection:
        """Connection to the default database
        Used for almost everything"""
        if self._cnx[0][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_frm()
            self._cnx[0][1] = round(time.time())
            return self._cnx[0][0]
        return self._cnx[0][0]

    def connect_database_frm(self):
        "Create a connection to the default database"
        if len(self.database_keys) > 0:
            if self._cnx[0][0] is not None:
                self._cnx[0][0].close()
            self.log.debug('Connecting to MySQL (user %s, database "%s")',
                           self.database_keys['user'], self.database_keys['database1'])
            self._cnx[0][0] = mysql.connector.connect(user=self.database_keys['user'],
                password=self.database_keys['password'],
                host=self.database_keys['host'],
                database=self.database_keys['database1'],
                buffered=True,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci')
            self._cnx[0][1] = round(time.time())
        else:
            raise ValueError(dict)

    def close_database_cnx(self):
        "Close any opened database connection"
        try:
            self.cnx_frm.close()
        except ProgrammingError:
            pass
        try:
            self.cnx_xp.close()
        except ProgrammingError:
            pass
        try:
            self.cnx_stats.close()
        except ProgrammingError:
            pass

    @property
    def cnx_xp(self) -> MySQLConnection:
        """Connection to the xp database
        Used for guilds using local xp (1 table per guild)"""
        if self._cnx[1][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_xp()
            self._cnx[1][1] = round(time.time())
            return self._cnx[1][0]
        return self._cnx[1][0]

    def connect_database_xp(self):
        "Create a connection to the xp database"
        if len(self.database_keys) > 0:
            if self._cnx[1][0] is not None:
                self._cnx[1][0].close()
            self.log.debug('Connecting to MySQL (user %s, database "%s")',
                           self.database_keys['user'], self.database_keys['database2'])
            self._cnx[1][0] = mysql.connector.connect(user=self.database_keys['user'],
                password=self.database_keys['password'],
                host=self.database_keys['host'],
                database=self.database_keys['database2'],
                buffered=True)
            self._cnx[1][1] = round(time.time())
        else:
            raise ValueError(dict)

    @property
    def cnx_stats(self) -> MySQLConnection:
        """Connection to the xp database
        Used for guilds using local xp (1 table per guild)"""
        if self._cnx[2][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_stats()
            self._cnx[2][1] = round(time.time())
            return self._cnx[2][0]
        return self._cnx[2][0]

    def connect_database_stats(self):
        "Create a connection to the stats database"
        if len(self.database_keys) > 0:
            if self._cnx[2][0] is not None:
                self._cnx[2][0].close()
            self.log.debug(
                'Connecting to MySQL (user %s, database "statsbot")', self.database_keys['user'])
            self._cnx[2][0] = mysql.connector.connect(user=self.database_keys['user'],
                                                      password=self.database_keys['password'],
                                                      host=self.database_keys['host'], database='statsbot',
                                                      buffered=True)
            self._cnx[2][1] = round(time.time())
        else:
            raise ValueError(dict)

    @property
    def db_query(self):
        return create_database_query(self.cnx_frm)

    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    async def get_config(self, guild_id: int, option: str) -> Optional[str]:
        "Get a configuration option for a specific guild"
        cog = self.get_cog("Servers")
        if cog:
            if self.database_online:
                return await cog.get_option(guild_id, option)
            return cog.default_opt.get(option, None)
        return None

    async def get_recipient(self, channel: discord.DMChannel) -> Optional[discord.User]:
        """Get the recipient of the given DM channel

        This method is required because most of the time Discord doesn't properly give that info"""
        if not isinstance(channel, discord.DMChannel):
            return None
        if channel.recipient is None:
            # recipient couldn't be loaded
            channel = await self.fetch_channel(channel.id)
        return channel.recipient

    def utcnow(self) -> datetime.datetime:
        """Get the current date and time with UTC timezone"""
        return datetime.datetime.now(datetime.timezone.utc)

    @property
    def _(self) -> Callable[[Any, str], Coroutine[Any, Any, str]]:
        """Translate something"""
        cog = self.get_cog('Languages')
        if cog is None:
            self.log.error("Unable to load Languages cog")
            return lambda *args, **kwargs: args[1]
        return cog.tr

    async def send_embed(self, embeds: list[discord.Embed], url:str=None):
        """Send a list of embeds to a discord channel"""
        if cog := self.get_cog('Embeds'):
            await cog.send(embeds, url)
        elif url is not None and url.startswith('https://'):
            embeds = (embed.to_dict() for embed in embeds)
            requests.post(url, json={"embeds": embeds})

    async def potential_command(self, message: discord.Message):
        "Check if a message is potentially a bot command"
        prefixes = await self.get_prefix(message)
        is_cmd = False
        for prefix in prefixes:
            is_cmd = is_cmd or message.content.startswith(prefix)
        return is_cmd


class ConfirmView(discord.ui.View):
    "A simple view used to confirm an action"

    def __init__(self, bot: Zbot, ctx, validation: Callable[[discord.Interaction], bool], ephemeral: bool=True, timeout: int=60):
        super().__init__(timeout=timeout)
        self.value: bool = None
        self.bot = bot
        self.ctx = ctx
        self.validation = validation
        self.ephemeral = ephemeral

    async def init(self):
        "Initialize buttons with translations"
        confirm_label = await self.bot._(self.ctx, "misc.btn.confirm.label")
        confirm_btn = discord.ui.Button(label=confirm_label, style=discord.ButtonStyle.green)
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        cancel_label = await self.bot._(self.ctx, "misc.btn.cancel.label")
        cancel_btn = discord.ui.Button(label=cancel_label, style=discord.ButtonStyle.grey)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def confirm(self, interaction: discord.Interaction):
        "Confirm the action when clicking"
        if not self.validation(interaction):
            return
        await interaction.response.send_message(await self.bot._(self.ctx, "misc.btn.confirm.answer"), ephemeral=self.ephemeral)
        self.value = True
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        "Cancel the action when clicking"
        if not self.validation(interaction):
            return
        await interaction.response.send_message(await self.bot._(self.ctx, "misc.btn.cancel.answer"), ephemeral=self.ephemeral)
        self.value = False
        self.stop()

class DeleteView(discord.ui.View):
    "A simple view used to delete a bot message after reading it"

    def __init__(self, delete_text: str, validation: Callable[[discord.Interaction], bool], \
            timeout: int=60):
        super().__init__(timeout=timeout)
        self.validation = validation
        delete_btn = discord.ui.Button(label=delete_text, style=discord.ButtonStyle.red, emoji='🗑')
        delete_btn.callback = self.delete
        self.add_item(delete_btn)

    async def delete(self, interaction: discord.Interaction):
        "Delete the message when clicking"
        if not self.validation(interaction):
            return
        await interaction.message.delete(delay=0)
        self.stop()

class RankCardsFlag:
    "Flags used for unlocked rank cards"
    FLAGS = {
        1 << 0: "rainbow",
        1 << 1: "blurple_19",
        1 << 2: "blurple_20",
        1 << 3: "christmas_19",
        1 << 4: "christmas_20",
        1 << 5: "halloween_20",
        1 << 6: "blurple_21",
        1 << 7: "halloween_21",
        1 << 8: "april_22"
    }

    def flagsToInt(self, flags: list) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def intToFlags(self, i: int) -> list:
        "Convert an integer value to its list of flags"
        return [v for k, v in self.FLAGS.items() if i & k == k]

class UserFlag:
    "Flags used for user permissions/roles"
    FLAGS = {
        1 << 0: "support",
        1 << 1: "contributor",
        1 << 2: "premium",
        1 << 3: "partner",
        1 << 4: "translator",
        1 << 5: "cookie"
    }

    def flagsToInt(self, flags: list) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def intToFlags(self, i: int) -> list:
        "Convert an integer value to its list of flags"
        return [v for k, v in self.FLAGS.items() if i & k == k]
