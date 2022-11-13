import datetime
import logging
import sys
import time
from typing import Any, Callable, Coroutine, Literal, Optional, TYPE_CHECKING, Union, overload

import discord
import requests
from discord.ext import commands
from mysql.connector import connect as sql_connect
from mysql.connector.connection import MySQLConnection
from mysql.connector.errors import ProgrammingError
from utils import get_prefix

from libs.database import create_database_query
from libs.emojis_manager import EmojisManager
from libs.prefix_manager import PrefixManager
from libs.tasks_handler import TaskHandler


if TYPE_CHECKING:
    from fcts.aide import Help
    from fcts.bot_events import BotEvents
    from fcts.bot_stats import BotStats
    from fcts.cases import Cases
    from fcts.errors import Errors
    from fcts.minecraft import Minecraft
    from fcts.partners import Partners
    from fcts.rss import Rss
    from fcts.servers import Servers
    from fcts.users import Users
    from fcts.utilities import Utilities
    from fcts.xp import Xp

PRIVATE_GUILD_ID = discord.Object(625316773771608074)
SUPPORT_GUILD_ID = discord.Object(356067272730607628)

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
    
    async def send_help(self, command: Union[str, commands.Command]):
        """Send the help message of the given command"""
        cmd_arg = command.split(' ') if isinstance(command, str) else command.qualified_name.split(' ')
        await self.bot.get_command("help")(self, *cmd_arg)

# pylint: disable=too-many-instance-attributes
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
        self.emojis_manager = EmojisManager(self)
        # app commands
        self.tree.on_error = self.on_app_cmd_error
        self.app_commands_list: Optional[list[discord.app_commands.AppCommand]] = None

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
        try:
            return self.get_cog("BotEvents").current_event
        except Exception as err: # pylint: disable=broad-except
            self.log.warning("[current_event] %s", err, exc_info=True)
            return None

    @property
    def current_event_data(self):
        """Get the current event data, from the date"""
        try:
            return self.get_cog("BotEvents").current_event_data
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
    def get_cog(self, name: Literal["Partners"]) -> Optional["Partners"]:
        ...

    @overload
    def get_cog(self, name: Literal["Rss"]) -> Optional["Rss"]:
        ...

    @overload
    def get_cog(self, name: Literal["Servers"]) -> Optional["Servers"]:
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
            self._cnx[0][0] = sql_connect(user=self.database_keys['user'],
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
            self._cnx[1][0] = sql_connect(user=self.database_keys['user'],
                password=self.database_keys['password'],
                host=self.database_keys['host'],
                database=self.database_keys['database2'],
                buffered=True)
            self._cnx[1][1] = round(time.time())
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
    def _(self) -> Callable[..., Coroutine[Any, Any, str]]:
        """Translate something"""
        cog = self.get_cog('Languages')
        if cog is None:
            self.log.error("Unable to load Languages cog")
            async def fake_tr(*args, **_kwargs):
                return 'en' if args[1] == "_used_locale" else args[1]
            return fake_tr
        return cog.tr

    async def send_embed(self, embeds: Union[list[discord.Embed], discord.Embed], url:str=None):
        """Send a list of embeds to a discord channel"""
        if isinstance(embeds, discord.Embed):
            embeds = [embeds]
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
        self.log.error(f"Trying to mention invalid command: {command_name}")
        return f"`{command_name}`"
