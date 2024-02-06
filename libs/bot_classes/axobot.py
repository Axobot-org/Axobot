import datetime
import logging
import sys
import time
from typing import (TYPE_CHECKING, Awaitable, Callable, Literal, Optional,
                    Union, overload)

import aiohttp
import discord
from discord.ext import commands
from mysql.connector import connect as sql_connect
from mysql.connector.connection import MySQLConnection
from mysql.connector.errors import ProgrammingError

from fcts.tokens import get_database_connection, get_secrets_dict
from libs.database import create_database_query
from libs.emojis_manager import EmojisManager
from libs.prefix_manager import PrefixManager
from libs.serverconfig.options_list import options as options_list
from libs.tasks_handler import TaskHandler
from libs.tips import TipsManager

from .consts import PRIVATE_GUILD_ID
from .my_context import MyContext

if TYPE_CHECKING:
    from fcts.antiraid import AntiRaid
    from fcts.bot_events import BotEvents
    from fcts.bot_stats import BotStats
    from fcts.cases import Cases
    from fcts.errors import Errors
    from fcts.help_cmd import Help
    from fcts.minecraft import Minecraft
    from fcts.moderation import Moderation
    from fcts.partners import Partners
    from fcts.rss import Rss
    from fcts.serverconfig import ServerConfig
    from fcts.twitch import Twitch
    from fcts.users import Users
    from fcts.utilities import Utilities
    from fcts.xp import Xp

async def get_prefix(bot: "Axobot", msg: discord.Message) -> list:
    """Get the correct bot prefix from a message
    Prefix can change based on guild, but the bot mention will always be an option"""
    prefixes = [await bot.prefix_manager.get_prefix(msg.guild)]
    if msg.guild is None:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, msg)

# pylint: disable=too-many-instance-attributes
class Axobot(commands.bot.AutoShardedBot):
    """Bot class, with everything needed to run it"""

    def __init__(self, case_insensitive: bool = None, status: discord.Status = None, database_online: bool = True, \
            beta: bool = False, zombie_mode: bool = False):
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
        self.entity_id: int = 0 # ID of the bot for the statistics database
        self.database_keys = get_database_connection() # credentials for the database
        self.log = logging.getLogger("bot") # logs module
        self._cnx = [[None, 0], [None, 0], [None, 0]] # database connections
        self.xp_enabled: bool = True # if xp is enabled
        self.rss_enabled: bool = True # if rss is enabled
        self.stats_enabled: bool = True # if the stats system is enabled (for grafana mainly)
        self.files_count_enabled: bool = False # if the files count stats system is enabled
        self.internal_loop_enabled: bool = True # if internal loop is enabled
        self.zws = "\u200B"  # here's a zero width space
        self.others = get_secrets_dict() # other misc credentials
        self.zombie_mode: bool = zombie_mode # if we should listen without sending any message
        self.prefix_manager = PrefixManager(self)
        self.task_handler = TaskHandler(self)
        self.emojis_manager = EmojisManager(self)
        self.tips_manager = TipsManager(self)
        # app commands
        self.tree.on_error = self.on_app_cmd_error
        self.app_commands_list: Optional[list[discord.app_commands.AppCommand]] = None

    @property
    def dbl_token(self):
        return self.others["dbl_axobot"]

    async def on_error(self, event_method: Union[Exception, str], *_args, **_kwargs):
        "Called when an event raises an uncaught exception"
        if isinstance(event_method, str) and event_method.startswith("on_") and event_method != "on_error":
            _, error, _ = sys.exc_info()
            self.dispatch("error", error, f"While handling event `{event_method}`")
        # await super().on_error(event_method, *args, **kwargs)

    async def on_app_cmd_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        self.dispatch("interaction_error", interaction, error)

    allowed_commands = ("eval", "add_cog", "del_cog")

    @property
    def current_event(self):
        """Get the current event, from the date"""
        if cog := self.get_cog("BotEvents"):
            try:
                return cog.current_event
            except Exception as err: # pylint: disable=broad-except
                self.log.warning("[current_event] %s", err, exc_info=True)
        return None

    @property
    def current_event_data(self):
        """Get the current event data, from the date"""
        if cog := self.get_cog("BotEvents"):
            try:
                return cog.current_event_data
            except Exception as err: # pylint: disable=broad-except
                self.log.warning("[current_event_data] %s", err, exc_info=True)
        return None

    # pylint: disable=arguments-differ
    async def get_context(self, source: discord.Message, *, cls=MyContext) -> MyContext:
        """Get a custom context class when creating one from a message"""
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(source, cls=cls)

    @overload
    def get_cog(self, name: Literal["AntiRaid"]) -> Optional["AntiRaid"]:
        ...

    @overload
    def get_cog(self, name: Literal["BotStats"]) -> Optional["BotStats"]:
        ...

    @overload
    def get_cog(self, name: Literal["BotEvents"]) -> Optional["BotEvents"]:
        ...

    @overload
    def get_cog(self, name: Literal["Cases"]) -> Optional["Cases"]:
        ...

    @overload
    def get_cog(self, name: Literal["Errors"]) -> Optional["Errors"]:
        ...

    @overload
    def get_cog(self, name: Literal["Help"]) -> Optional["Help"]:
        ...

    @overload
    def get_cog(self, name: Literal["Minecraft"]) -> Optional["Minecraft"]:
        ...

    @overload
    def get_cog(self, name: Literal["Moderation"]) -> Optional["Moderation"]:
        ...

    @overload
    def get_cog(self, name: Literal["Partners"]) -> Optional["Partners"]:
        ...

    @overload
    def get_cog(self, name: Literal["Rss"]) -> Optional["Rss"]:
        ...

    @overload
    def get_cog(self, name: Literal["ServerConfig"]) -> Optional["ServerConfig"]:
        ...

    @overload
    def get_cog(self, name: Literal["Twitch"]) -> Optional["Twitch"]:
        ...

    @overload
    def get_cog(self, name: Literal["Users"]) -> Optional["Users"]:
        ...

    @overload
    def get_cog(self, name: Literal["Utilities"]) -> Optional["Utilities"]:
        ...

    @overload
    def get_cog(self, name: Literal["Xp"]) -> Optional["Xp"]:
        ...

    def get_cog(self, name: str):
        # pylint: disable=useless-super-delegation
        return super().get_cog(name)

    @property
    def cnx_axobot(self) -> MySQLConnection:
        """Connection to the default database
        Used for almost everything"""
        if self._cnx[0][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_axobot()
            self._cnx[0][1] = round(time.time())
            return self._cnx[0][0]
        return self._cnx[0][0]

    def connect_database_axobot(self):
        "Create a connection to the default database"
        if len(self.database_keys) > 0:
            if self._cnx[0][0] is not None:
                self._cnx[0][0].close()
            self.log.debug(
                'Connecting to MySQL (user %s, database "%s")',
                self.database_keys['user'],
                self.database_keys['name_main']
            )
            self._cnx[0][0] = sql_connect(
                user=self.database_keys['user'],
                password=self.database_keys['password'],
                host=self.database_keys['host'],
                database=self.database_keys['name_main'],
                buffered=True,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
                connection_timeout=5
            )
            self._cnx[0][1] = round(time.time())
        else:
            raise ValueError(dict)

    def close_database_cnx(self):
        "Close any opened database connection"
        try:
            self.cnx_axobot.close()
        except ProgrammingError:
            pass
        try:
            self.cnx_xp.close()
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
            self.log.debug(
                'Connecting to MySQL (user %s, database "%s")',
                self.database_keys['user'],
                self.database_keys['name_xp']
            )
            self._cnx[1][0] = sql_connect(
                user=self.database_keys['user'],
                password=self.database_keys['password'],
                host=self.database_keys['host'],
                database=self.database_keys['name_xp'],
                buffered=True,
                connection_timeout=5
            )
            self._cnx[1][1] = round(time.time())
        else:
            raise ValueError(dict)

    @property
    def db_query(self):
        return create_database_query(self.cnx_axobot)

    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    async def get_config(self, guild_id: int, option: str):
        """Get a configuration option for a specific guild
        Fallbacks to the default values if the guild is not found"""
        cog = self.get_cog("ServerConfig")
        if cog:
            if self.database_online:
                value = await cog.get_option(guild_id, option)
                if value is not None:
                    return value
            return options_list.get(option, {"default": None})["default"]
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
    def _(self) -> Callable[..., Awaitable[str]]:
        """Translate something"""
        cog = self.get_cog('Languages')
        if cog is None:
            self.log.error("Unable to load Languages cog")
            async def fake_tr(*args, **_kwargs):
                return 'en' if args[1] == "_used_locale" else args[1]
            return fake_tr
        return cog.tr

    async def send_embed(self, embeds: Union[list[discord.Embed], discord.Embed], url: str=None):
        """Send a list of embeds to a discord channel"""
        if isinstance(embeds, discord.Embed):
            embeds = [embeds]
        if cog := self.get_cog('Embeds'):
            await cog.send(embeds, url)
        elif url is not None and url.startswith('https://'):
            embeds = (embed.to_dict() for embed in embeds)
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json={"embeds": embeds}) as resp:
                    if resp.status >= 400:
                        self.log.error("Unable to send embed to %s: %s", url, await resp.text())

    async def potential_command(self, message: discord.Message):
        "Check if a message is potentially a bot command"
        prefixes = await self.get_prefix(message)
        is_cmd = False
        for prefix in prefixes:
            is_cmd = is_cmd or message.content.startswith(prefix)
        return is_cmd

    async def fetch_app_commands(self):
        "Populate the app_commands_list attribute from the Discord API"
        target = PRIVATE_GUILD_ID if self.beta else None
        self.app_commands_list = await self.tree.fetch_commands(guild=target)

    async def fetch_app_command_by_name(self, name: str) -> Optional[discord.app_commands.AppCommand]:
        "Get a specific app command from the Discord API"
        if self.app_commands_list is None:
            await self.fetch_app_commands()
        for command in self.app_commands_list:
            if command.name == name:
                return command
        return None

    async def get_command_mention(self, command_name: str):
        "Get how a command should be mentionned (either app-command mention or raw name)"
        if command := await self.fetch_app_command_by_name(command_name.split(' ')[0]):
            return f"</{command_name}:{command.id}>"
        if command := self.get_command(command_name):
            return f"`{command.qualified_name}`"
        self.log.error("Trying to mention invalid command: %s", command_name)
        return f"`{command_name}`"
