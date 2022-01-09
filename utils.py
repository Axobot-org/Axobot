import argparse
import datetime
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Callable, Coroutine, Optional, Union

import discord
import mysql
import requests
from discord.ext import commands
from mysql.connector.connection import MySQLConnection
from mysql.connector.errors import ProgrammingError

from fcts import cryptage, tokens
from libs.database import create_database_query
from libs.prefix_manager import PrefixManager

OUTAGE_REASON = {
    'fr': "Un des datacenters de notre hébergeur OVH a pris feu, rendant ,inaccessible le serveur et toutes ses données. Une vieille sauvegarde de la base de donnée sera peut-être utilisée ultérieurement. Plus d'informations sur https://zbot.statuspage.io/",
    'en': "One of the datacenters of our host OVH caught fire, making the server and all its data inaccessible. An old backup of the database may be used later. More information on https://zbot.statuspage.io/"
}


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
        return await super().send(*args, **kwargs)


async def get_prefix(bot:"Zbot", msg: discord.Message) -> list:
    """Get the correct bot prefix from a message
    Prefix can change based on guild, but the bot mention will always be an option"""
    prefixes = [await bot.prefix_manager.get_prefix(msg.guild)]
    if msg.guild is None:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, msg)


class Zbot(commands.bot.AutoShardedBot):
    """Bot class, with everything needed to run it"""

    def __init__(self, case_insensitive: bool = None, status: discord.Status = None, database_online: bool = True, beta: bool = False, dbl_token: str = "", zombie_mode: bool = False):
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
        self.database_keys = dict() # credentials for the database
        self.log = logging.getLogger("runner") # logs module
        self.dbl_token = dbl_token # token for Discord Bot List
        self._cnx = [[None, 0], [None, 0], [None, 0]] # database connections
        self.xp_enabled: bool = True # if xp is enabled
        self.rss_enabled: bool = True # if rss is enabled
        self.alerts_enabled: bool = True # if alerts system is enabled
        self.internal_loop_enabled: bool = True # if internal loop is enabled
        self.zws = "​"  # here's a zero width space
        self.others = dict() # other misc credentials
        self.zombie_mode: bool = zombie_mode # if we should listen without sending any message
        self.prefix_manager = PrefixManager(self)

    allowed_commands = ("eval", "add_cog", "del_cog")

    @property
    def current_event(self) -> Optional[str]:
        """Get the current event, from the date"""
        try:
            return self.get_cog("BotEvents").current_event
        except Exception as err:
            self.log.warning("[current_event] %s", err, exc_info=True)
            return None

    @property
    def current_event_data(self) -> Optional[dict]:
        """Get the current event data, from the date"""
        try:
            return self.get_cog("BotEvents").current_event_data
        except Exception as err:
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
        cog = self.get_cog("Servers")
        if cog:
            if self.database_online:
                return await cog.get_option(guild_id, option)
            return cog.default_opt.get(option, None)
        return None

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


class ConfirmView(discord.ui.View):
    "A simple view used to confirm an action"

    def __init__(self, bot: Zbot, confirm_text: str, cancel_text: str, ephemeral: bool=True):
        super().__init__()
        self.bot = bot
        self.value: bool = None
        self.ephemeral = ephemeral
        # discord.ui.button(label=confirm_text, style=discord.ButtonStyle.green)(self.confirm)
        confirm_btn = discord.ui.Button(label=confirm_text, style=discord.ButtonStyle.green)
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        cancel_btn = discord.ui.Button(label=cancel_text, style=discord.ButtonStyle.grey)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def confirm(self, _button: discord.ui.Button, interaction: discord.Interaction):
        "Confirm the action when clicking"
        await interaction.response.send_message('Confirming', ephemeral=self.ephemeral)
        self.value = True
        self.stop()

    async def cancel(self, _button: discord.ui.Button, interaction: discord.Interaction):
        "Cancel the action when clicking"
        await interaction.response.send_message('Cancelling', ephemeral=self.ephemeral)
        self.value = False
        self.stop()

class RankCardsFlag:
    FLAGS = {
        1 << 0: "rainbow",
        1 << 1: "blurple_19",
        1 << 2: "blurple_20",
        1 << 3: "christmas_19",
        1 << 4: "christmas_20",
        1 << 5: "halloween_20",
        1 << 6: "blurple_21",
        1 << 7: "halloween_21"
    }

    def flagsToInt(self, flags: list) -> int:
        r = 0
        for k, v in self.FLAGS.items():
            if v in flags:
                r |= k
        return r

    def intToFlags(self, i: int) -> list:
        return [v for k, v in self.FLAGS.items() if i & k == k]

class UserFlag:
    FLAGS = {
        1 << 0: "support",
        1 << 1: "contributor",
        1 << 2: "premium",
        1 << 3: "partner",
        1 << 4: "translator",
        1 << 5: "cookie"
    }

    def flagsToInt(self, flags: list) -> int:
        r = 0
        for k, v in self.FLAGS.items():
            if v in flags:
                r |= k
        return r

    def intToFlags(self, i: int) -> list:
        return [v for k, v in self.FLAGS.items() if i & k == k]

def flatten_list(first_list: list) -> list:
    return [item for sublist in first_list for item in sublist]

def setup_bot_logger():
    """Create the logger module for the bot, used for logs"""
    # on chope le premier logger
    log = logging.getLogger("runner")
    # on définis un formatteur
    log_format = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="[%d/%m/%Y %H:%M]")
    # ex du format : [08/11/2018 14:46] WARNING: Rss fetch_rss_flux l.288 : Cannot get the RSS flux because of the following error: (suivi du traceback)

    # log vers un fichier
    file_handler = RotatingFileHandler("logs/debug.log", maxBytes=1e6, backupCount=2, delay=True)
    # tous les logs de niveau DEBUG et supérieur sont evoyés dans le fichier
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)

    # log vers la console
    stream_handler = logging.StreamHandler(sys.stdout)
    # tous les logs de niveau INFO et supérieur sont evoyés dans le fichier
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)

    # supposons que tu veuille collecter les erreurs sur ton site d'analyse d'erreurs comme sentry
    #sentry_handler = x
    #sentry_handler.setLevel(logging.ERROR)  # on veut voir que les erreurs et au delà, pas en dessous
    #sentry_handler.setFormatter(format)

    log.addHandler(file_handler)
    log.addHandler(stream_handler)
    #log.addHandler(sentry_handler)

    log.setLevel(logging.DEBUG)
    return log

def setup_database_logger():
    "Create the logger module for database access"
    log = logging.getLogger("database")
    log_format = logging.Formatter("%(asctime)s %(levelname)s: [SQL] %(message)s", datefmt="[%d/%m/%Y %H:%M]")
    file_handler = RotatingFileHandler("logs/sql-debug.log", maxBytes=2e6, backupCount=2, delay=True)

    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)

    log.addHandler(file_handler)
    log.addHandler(stream_handler)
    log.setLevel(logging.DEBUG)
    return log

def setup_start_parser():
    "Create a parser for the command-line interface"
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', '-t', help="The bot token to use", required=True)
    parser.add_argument('--no-main-loop', help="Deactivate the bot main loop",
                        action="store_false", dest="event_loop")
    parser.add_argument('--no-rss', help="Disable any RSS feature (loop and commands)",
                        action="store_false", dest="rss_features")

    return parser

def parse_crypted_file(bot: Zbot):
    "Parse the secret file containing all types of tokens and private things"
    with open('fcts/requirements', 'r') as file:
        lines = file.read().split('\n')
    # remove comments, empty lines and all
    for line in lines:
        if line.startswith("//") or line == '':
            lines.remove(line)
    while '' in lines:
        lines.remove('')
    # database
    for i, line in enumerate(['user', 'password', 'host', 'database1', 'database2']):
        bot.database_keys[line] = cryptage.uncrypte(lines[i])
    # misc APIs
    bot.others['botsondiscord'] = cryptage.uncrypte(lines[6])
    bot.others['discordbotsgroup'] = cryptage.uncrypte(lines[7])
    bot.others['bitly'] = cryptage.uncrypte(lines[8])
    bot.others['twitter'] = {'consumer_key': cryptage.uncrypte(lines[9]),
                             'consumer_secret': cryptage.uncrypte(lines[10]),
                             'access_token_key': cryptage.uncrypte(lines[11]),
                             'access_token_secret': cryptage.uncrypte(lines[12])}
    bot.others['discordlist.space'] = cryptage.uncrypte(lines[13])
    bot.others['discordboats'] = cryptage.uncrypte(lines[14])
    bot.others['discordextremelist'] = cryptage.uncrypte(lines[15])
    bot.others['statuspage'] = cryptage.uncrypte(lines[16])
    bot.others['nasa'] = cryptage.uncrypte(lines[17])
    bot.others['random_api_token'] = cryptage.uncrypte(lines[18])
    bot.dbl_token = tokens.get_dbl_token()

def load_sql_connection(bot: Zbot):
    "Load the connection to the database, preferably in local mode"
    try:
        try:
            cnx = mysql.connector.connect(user=bot.database_keys['user'],
                                          password=bot.database_keys['password'],
                                          host="127.0.0.1",
                                          database=bot.database_keys['database1'])
        except (mysql.connector.InterfaceError, mysql.connector.ProgrammingError):
            bot.log.warning("Unable to access local dabatase - attempt via IP")
            cnx = mysql.connector.connect(user=bot.database_keys['user'],
                                          password=bot.database_keys['password'],
                                          host=bot.database_keys['host'],
                                          database=bot.database_keys['database1'])
        else:
            bot.log.info("Database connected locally")
            bot.database_keys['host'] = '127.0.0.1'
        cnx.close()
    except Exception as err:
        bot.log.error("---- UNABLE TO REACH THE DATABASE ----")
        bot.log.error(err)
        bot.database_online = False

def load_cogs(bot: Zbot):
    "Load the bot modules"
    initial_extensions = ['fcts.languages',
                      'fcts.admin',
                      'fcts.aide',
                      'fcts.bot_events',
                      'fcts.bot_stats',
                      'fcts.cases',
                      'fcts.embeds',
                      'fcts.emojis',
                      'fcts.errors',
                      'fcts.events',
                      'fcts.fun',
                      'fcts.info',
                      'fcts.library',
                      'fcts.minecraft',
                      'fcts.moderation',
                      'fcts.morpions',
                      'fcts.partners',
                      'fcts.perms',
                      'fcts.reloads',
                      'fcts.roles_react',
                      'fcts.rss',
                      'fcts.s_backups',
                      'fcts.servers',
                      'fcts.timers',
                      'fcts.timeutils',
                    #   'fcts.translations',
                      'fcts.users',
                      'fcts.utilities',
                      'fcts.voices',
                      'fcts.welcomer',
                      'fcts.xp'
    ]

    # Here we load our extensions(cogs) listed above in [initial_extensions]
    count = 0
    for extension in initial_extensions:
        try:
            bot.load_extension(extension)
        except discord.DiscordException:
            bot.log.critical('Failed to load extension %s', extension, exc_info=True)
            count += 1
        if count  > 0:
            bot.log.critical("%s modules not loaded\nEnd of program", count)
            sys.exit()
