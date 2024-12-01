import asyncio
import datetime
import logging
import sys
from typing import (TYPE_CHECKING, Awaitable, Callable, Literal, Optional,
                    overload)

import discord
from aiohttp import ClientSession
from discord.ext import commands

from core.boot_utils.conf_loader import get_secrets_dict
from core.database import DatabaseConnectionManager, DatabaseQueryHandler
from core.emojis_manager import EmojisManager
from core.tasks_handler import TaskHandler
from core.tips import TipsManager

from .bot_embeds_manager import send_log_embed
from .my_context import MyContext

if TYPE_CHECKING:
    from core.utilities import Utilities
    from modules.antiraid.antiraid import AntiRaid
    from modules.bot_events.bot_events import BotEvents
    from modules.bot_stats.bot_stats import BotStats
    from modules.cases.cases import Cases
    from modules.errors.errors import Errors
    from modules.help_cmd.help_cmd import Help
    from modules.minecraft.minecraft import Minecraft
    from modules.moderation.moderation import Moderation
    from modules.partners.partners import Partners
    from modules.rss.rss import Rss
    from modules.serverconfig.serverconfig import ServerConfig
    from modules.serverconfig.src.converters import AllRepresentation
    from modules.twitch.twitch import Twitch
    from modules.users.users import Users
    from modules.xp.xp import Xp

async def get_prefix(bot: "Axobot", msg: discord.Message) -> list:
    """Get the correct bot prefix from a message
    Prefix can change based on guild, but the bot mention will always be an option"""
    if msg.guild is None:
        return commands.when_mentioned_or("")(bot, msg)
    return commands.when_mentioned(bot, msg)

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
        super().__init__(command_prefix=get_prefix, case_insensitive=case_insensitive, max_messages=100_000,
                         status=status, allowed_mentions=allowed_mentions, intents=intents, enable_debug_events=True)
        self.database_online = database_online  # if the mysql database works
        self.beta = beta # if the bot is in beta mode
        self.entity_id: int = 0 # ID of the bot for the statistics database
        self.db = DatabaseConnectionManager()
        self.db_main = DatabaseQueryHandler(self, "axobot")
        self.db_xp = DatabaseQueryHandler(self, "axobot-xp")
        self.log = logging.getLogger("bot") # logs module
        self.xp_enabled: bool = True # if xp is enabled
        self.rss_enabled: bool = True # if rss is enabled
        self.stats_enabled: bool = True # if the stats system is enabled (for grafana mainly)
        self.files_count_enabled: bool = False # if the files count stats system is enabled
        self.internal_loop_enabled: bool = True # if internal loop is enabled
        self.zws = "\u200B"  # here's a zero width space
        self.secrets = get_secrets_dict() # other misc credentials
        self.zombie_mode: bool = zombie_mode # if we should listen without sending any message
        self.task_handler = TaskHandler(self)
        self.emojis_manager = EmojisManager(self)
        self.tips_manager = TipsManager(self)
        self._options_list: dict[str, "AllRepresentation"] | None = None
        self._options_list_lock = asyncio.Lock()
        # app commands
        self.tree.on_error = self.on_app_cmd_error
        self.app_commands_list: Optional[list[discord.app_commands.AppCommand]] = None

    async def on_error(self, event_method: Exception | str, *_args, **_kwargs):
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

    @property
    def doc_url(self):
        return (
            "https://axobot.readthedocs.io/en/latest/",
            "https://axobot.readthedocs.io/en/develop/",
            "https://axobot.readthedocs.io/en/latest/",
        )[self.entity_id]

    async def get_options_list(self):
        "Fetch the list of server config options from the API"
        async with self._options_list_lock:
            if self._options_list is None:
                url = "https://api-beta.zrunner.me" if self.beta else "https://api.zrunner.me"
                url += "/discord/default-guild-config"
                self.log.info("Fetching options list from %s", url)
                async with ClientSession() as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        api_result = await response.json()
                self._options_list = {}
                for _category, options in api_result.items():
                    self._options_list.update(options)
        return self._options_list

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

    async def load_module(self, module_name: str):
        "Load a module"
        await self.load_extension(f"modules.{module_name}.{module_name}")

    async def unload_module(self, module_name: str):
        "Unload a module"
        await self.unload_extension(f"modules.{module_name}.{module_name}")

    async def reload_module(self, module_name: str):
        "Reload a module"
        await self.reload_extension(f"modules.{module_name}.{module_name}")

    @property
    def cnx_axobot(self):
        """Connection to the default database
        Used for almost everything"""
        return self.db.get_connection("axobot")

    def close_database_cnx(self):
        "Close any opened database connection"
        self.db.disconnect_all()

    async def get_config(self, guild_id: discord.Guild | int, option: str):
        """Get a configuration option for a specific guild
        Fallbacks to the default values if the guild is not found"""
        cog = self.get_cog("ServerConfig")
        if cog:
            if self.database_online:
                value = await cog.get_option(guild_id, option)
                if value is not None:
                    return value
        options_list = await self.get_options_list()
        return options_list.get(option, {"default": None})["default"]

    async def get_guilds_with_value(self, option_name: str, option_value: str):
        """Get a list of guilds with a specific config option set to a specific value"""
        cog = self.get_cog("ServerConfig")
        if cog and self.database_online:
            return await cog.db_get_guilds_with_value(option_name, option_value)
        return []

    async def db_get_guilds_with_option(self, option_name: str):
        """Get a list of guilds with a specific config option set to anything but None"""
        cog = self.get_cog("ServerConfig")
        if cog and self.database_online:
            return await cog.db_get_guilds_with_option(option_name)
        return {}

    async def get_recipient(self, channel: discord.DMChannel) -> discord.User | None:
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
        cog = self.get_cog("Languages")
        if cog is None:
            self.log.error("Unable to load Languages cog")
            async def fake_tr(*args, **_kwargs):
                return "en" if args[1] == "_used_locale" else args[1]
            return fake_tr
        return cog.tr

    async def send_embed(self, embeds: list[discord.Embed] | discord.Embed, url: str | None=None):
        """Send a list of embeds to a discord channel"""
        if isinstance(embeds, discord.Embed):
            embeds = [embeds]
        await send_log_embed(self, embeds, url)

    async def fetch_app_commands(self):
        "Populate the app_commands_list attribute from the Discord API"
        self.app_commands_list = await self.tree.fetch_commands(guild=None)

    async def fetch_app_command_by_name(self, name: str) -> discord.app_commands.AppCommand | None:
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

    async def get_message_from_cache(self, message_id: int) -> discord.Message | None:
        "Get a message from the cache"
        for msg in self.cached_messages:
            if msg.id == message_id:
                return msg
        return None

    async def add_message_to_cache(self, message: discord.Message):
        "Force add a message to the cache"
        if await self.get_message_from_cache(message.id) is None:
            # pylint: disable=protected-access
            self._connection._messages.append(message)
