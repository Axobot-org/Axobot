import discord
from discord.ext import commands
import logging
import sys
import time
import mysql
from typing import Any, Callable, Optional, Coroutine, Union


OUTAGE_REASON = {
    'fr': "Un des datacenters de notre hébergeur OVH a pris feu, rendant ,inaccessible le serveur et toutes ses données. Une vieille sauvegarde de la base de donnée sera peut-être utilisée ultérieurement. Plus d'informations sur https://zbot.statuspage.io/",
    'en': "One of the datacenters of our host OVH caught fire, making the server and all its data inaccessible. An old backup of the database may be used later. More information on https://zbot.statuspage.io/"
}


class MyContext(commands.Context):
    """Replacement for the official commands.Context class
    It allows us to add more methods and properties in the whole bot code"""

    bot: 'zbot'

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


def get_prefix(bot:"zbot", msg: discord.Message) -> list:
    """Get the correct bot prefix from a message
    Prefix can change based on guild, but the bot mention will always be an option"""
    if bot.database_online:
        try:
            prefixes = [bot.get_cog('Utilities').find_prefix(msg.guild)]
        except KeyError:
            try:
                bot.load_extension('fcts.utilities')
                prefixes = [bot.get_cog('Utilities').find_prefix(msg.guild)]
            except Exception as e:
                bot.log.warn("[get_prefix]", e)
                prefixes = ['!']
        except Exception as e:
            bot.log.warn("[get_prefix]", e)
            prefixes = ['!']
    else:
        if cog := bot.get_cog("Servers"):
            prefixes = [cog.default_opt.get("prefix")]
        else:
            prefixes = ['!']
    if msg.guild is None:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, msg)


class zbot(commands.bot.AutoShardedBot):
    """Bot class, with everything needed to run it"""

    def __init__(self, case_insensitive: bool = None, status: discord.Status = None, database_online: bool = True, beta: bool = False, dbl_token: str = "", zombie_mode: bool = False):
        # defining allowed default mentions
        ALLOWED = discord.AllowedMentions(everyone=False, roles=False)
        # defining intents usage
        intents = discord.Intents.all()
        intents.typing = False
        intents.webhooks = False
        intents.integrations = False
        # we now initialize the bot class
        super().__init__(command_prefix=get_prefix, case_insensitive=case_insensitive,
                         status=status, allowed_mentions=ALLOWED, intents=intents)
        self.database_online = database_online # if the mysql database works
        self.beta = beta # if the bot is in beta mode
        self.database_keys = dict() # credentials for the database
        self.log = logging.getLogger("runner") # logs module
        self.dbl_token = dbl_token # token for Discord Bot List
        self._cnx = [[None, 0], [None, 0], [None, 0]] # database connections
        self.xp_enabled: bool = True # if xp is enabled
        self.rss_enabled: bool = True # if rss is enabled
        self.alerts_enabled: bool = True # if alerts system is enabled
        self.internal_loop_enabled: bool = False # if internal loop is enabled
        self.zws = "​"  # here's a zero width space
        self.others = dict() # other misc credentials
        self.zombie_mode: bool = zombie_mode # if we should listen without sending any message
    
    allowed_commands = ("eval", "add_cog", "del_cog")

    @property
    def current_event(self) -> Optional[str]:
        """Get the current event, from the date"""
        try:
            return self.get_cog("BotEvents").current_event
        except Exception as e:
            self.log.warn(f"[current_event] {e}", exc_info=True)
            return None
    
    @property
    def current_event_data(self) -> Optional[dict]:
        """Get the current event data, from the date"""
        try:
            return self.get_cog("BotEvents").current_event_data
        except Exception as e:
            self.log.warn(f"[current_event_data] {e}", exc_info=True)
            return None

    async def get_context(self, message: discord.Message, *, cls=MyContext) -> MyContext:
        """Get a custom context class when creating one from a message"""
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(message, cls=cls)

    @property
    def cnx_frm(self) -> mysql.connector.connection.MySQLConnection:
        """Connection to the default database
        Used for almost everything"""
        if self._cnx[0][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_frm()
            self._cnx[0][1] = round(time.time())
            return self._cnx[0][0]
        else:
            return self._cnx[0][0]

    def connect_database_frm(self):
        if len(self.database_keys) > 0:
            if self._cnx[0][0] is not None:
                self._cnx[0][0].close()
            self.log.debug('Connection à MySQL (user {})'.format(
                self.database_keys['user']))
            self._cnx[0][0] = mysql.connector.connect(user=self.database_keys['user'], password=self.database_keys['password'], host=self.database_keys['host'],
                                                      database=self.database_keys['database1'], buffered=True, charset='utf8mb4', collation='utf8mb4_unicode_ci')
            self._cnx[0][1] = round(time.time())
        else:
            raise ValueError(dict)

    @property
    def cnx_xp(self) -> mysql.connector.connection.MySQLConnection:
        """Connection to the xp database
        Used for guilds using local xp (1 table per guild)"""
        if self._cnx[1][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_xp()
            self._cnx[1][1] = round(time.time())
            return self._cnx[1][0]
        else:
            return self._cnx[1][0]

    def connect_database_xp(self):
        if len(self.database_keys) > 0:
            if self._cnx[1][0] is not None:
                self._cnx[1][0].close()
            self.log.debug('Connection à MySQL (user {})'.format(
                self.database_keys['user']))
            self._cnx[1][0] = mysql.connector.connect(user=self.database_keys['user'], password=self.database_keys['password'],
                                                      host=self.database_keys['host'], database=self.database_keys['database2'], buffered=True)
            self._cnx[1][1] = round(time.time())
        else:
            raise ValueError(dict)
    
    @property
    def cnx_stats(self) -> mysql.connector.connection.MySQLConnection:
        """Connection to the xp database
        Used for guilds using local xp (1 table per guild)"""
        if self._cnx[2][1] + 1260 < round(time.time()):  # 21min
            self.connect_database_stats()
            self._cnx[2][1] = round(time.time())
            return self._cnx[2][0]
        else:
            return self._cnx[2][0]

    def connect_database_stats(self):
        if len(self.database_keys) > 0:
            if self._cnx[2][0] is not None:
                self._cnx[2][0].close()
            self.log.debug('Connection à MySQL (user {})'.format(
                self.database_keys['user']))
            self._cnx[2][0] = mysql.connector.connect(user=self.database_keys['user'], password=self.database_keys['password'],
                                                      host=self.database_keys['host'], database='statsbot',
                                                      buffered=True)
            self._cnx[2][1] = round(time.time())
        else:
            raise ValueError(dict)
    
    async def db_query(self, query: str, args: Union[tuple, dict]=None, *, fetchone: bool=False, returnrowcount: bool=False, astuple: bool=False) -> Union[int, list[dict], dict]:
        """Do any query to the bot database
        If SELECT, it will return a list of results, or only the first result (if fetchone)
        For any other query, it will return the affected row ID if returnrowscount, or the amount of affected rows (if returnrowscount)"""
        cursor = self.cnx_frm.cursor(dictionary=(not astuple))
        args = () if args is None else args
        try:
            cursor.execute(query, args)
            if query.startswith("SELECT"):
                _type = tuple if astuple else dict
                if fetchone:
                    v = cursor.fetchone()
                    result = _type() if v is None else _type(v)
                else:
                    result = list(map(_type, cursor.fetchall()))
            else:
                self.cnx_frm.commit()
                if returnrowcount:
                    result = cursor.rowcount
                else:
                    result = cursor.lastrowid
        except Exception as e:
            cursor.close()
            raise e
        cursor.close()
        return result

    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'

    async def get_prefix(self, msg: discord.Message):
        """Get a prefix from a message... what did you expect?"""
        return get_prefix(self, msg)
    
    async def get_config(self, guildID: int, option: str) -> Optional[str]:
        cog = self.get_cog("Servers")
        if cog:
            if self.database_online:
                return await cog.get_option(guildID, option)
            return cog.default_opt.get(option, None)
        return None
    
    @property
    def _(self) -> Callable[[Any, str], Coroutine[Any, Any, str]]:
        """Translate something"""
        cog = self.get_cog('Languages')
        if cog is None:
            self.log.error("Unable to load Languages cog")
            return lambda *args, **kwargs: args[1]
        return cog.tr


class RankCardsFlag:
        FLAGS = {
            1 << 0: "rainbow",
            1 << 1: "blurple_19",
            1 << 2: "blurple_20",
            1 << 3: "christmas_19",
            1 << 4: "christmas_20",
            1 << 5: "halloween_20",
            1 << 6: "blurple_21"
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

def setup_logger():
    """Create the logger module, used for logs"""
    # on chope le premier logger
    log = logging.getLogger("runner")
    # on définis un formatteur
    format = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="[%d/%m/%Y %H:%M]")
    # ex du format : [08/11/2018 14:46] WARNING Rss fetch_rss_flux l.288 : Cannot get the RSS flux because of the following error: (suivi du traceback)

    # log vers un fichier
    file_handler = logging.FileHandler("debug.log")
    # tous les logs de niveau DEBUG et supérieur sont evoyés dans le fichier
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(format)

    # log vers la console
    stream_handler = logging.StreamHandler(sys.stdout)
    # tous les logs de niveau INFO et supérieur sont evoyés dans le fichier
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(format)

    # supposons que tu veuille collecter les erreurs sur ton site d'analyse d'erreurs comme sentry
    #sentry_handler = x
    #sentry_handler.setLevel(logging.ERROR)  # on veut voir que les erreurs et au delà, pas en dessous
    #sentry_handler.setFormatter(format)

    # log.debug("message de debug osef")
    # log.info("message moins osef")
    # log.warn("y'a un problème")
    # log.error("y'a un gros problème")
    # log.critical("y'a un énorme problème")

    log.addHandler(file_handler)
    log.addHandler(stream_handler)
    #log.addHandler(sentry_handler)

    return log
