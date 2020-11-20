import discord
from discord.ext import commands
import logging
import sys
import time
import mysql

class MyContext(commands.Context):
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

def get_prefix(bot,msg):
    if bot.database_online:
        try:
            prefixes = [bot.cogs['UtilitiesCog'].find_prefix(msg.guild)]
        except KeyError:
            try:
                bot.load_extension('fcts.utilities')
                prefixes = [bot.cogs['UtilitiesCog'].find_prefix(msg.guild)]
            except Exception as e:
                bot.log.warn("[get_prefix]",e)
                prefixes = ['!']
        except Exception as e:
                bot.log.warn("[get_prefix]",e)
                prefixes = ['!']
    else:
        prefixes = ['!']
    if msg.guild==None:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot,msg)


class zbot(commands.bot.AutoShardedBot):

    def __init__(self,case_insensitive=None,status=None,database_online=True,beta=False,dbl_token=""):
        ALLOWED = discord.AllowedMentions(everyone=False, roles=False)
        intents = discord.Intents.all()
        intents.typing = False
        intents.webhooks = False
        intents.integrations = False
        super().__init__(command_prefix=get_prefix, case_insensitive=case_insensitive, status=status, allowed_mentions=ALLOWED, intents=intents)
        self.database_online = database_online
        self.beta = beta
        self.database_keys = dict()
        self.log = logging.getLogger("runner")
        self.dbl_token = dbl_token
        self._cnx = [[None,0],[None,0]]
        self.xp_enabled = True
        self.rss_enabled = True
        self.internal_loop_enabled = False
        self.zws = "​" # here's a zero width space
        self.others = dict()
    
    @property
    def current_event(self):
        try:
            return self.cogs["BotEventsCog"].current_event
        except Exception as e:
            self.log.warn(f"[current_event] {e}", exc_info=True)
            return None
    
    async def get_context(self, message: discord.Message, *, cls=MyContext):
        """Get a custom context class when creating one from a message"""
        # when you override this method, you pass your new Context
        # subclass to the super() method, which tells the bot to
        # use the new MyContext class
        return await super().get_context(message, cls=cls)
    
    @property
    def cnx_frm(self):
        if self._cnx[0][1] + 1260 < round(time.time()): # 21min
            self.connect_database_frm()
            self._cnx[0][1] = round(time.time())
            return self._cnx[0][0]
        else:
            return self._cnx[0][0]
    
    def connect_database_frm(self):
        if len(self.database_keys)>0:
            if self._cnx[0][0] != None:
                self._cnx[0][0].close()
            self.log.debug('Connection à MySQL (user {})'.format(self.database_keys['user']))
            self._cnx[0][0] = mysql.connector.connect(user=self.database_keys['user'],password=self.database_keys['password'],host=self.database_keys['host'],database=self.database_keys['database1'],buffered=True,charset='utf8mb4',collation='utf8mb4_unicode_ci')
            self._cnx[0][1] = round(time.time())
        else:
            raise ValueError(dict)
    
    @property
    def cnx_xp(self):
        if self._cnx[1][1] + 1260 < round(time.time()): # 21min
            self.connect_database_frm()
            self._cnx[1][1] = round(time.time())
            return self._cnx[1][0]
        else:
            return self._cnx[1][0]
    
    def connect_database_xp(self):
        if len(self.database_keys)>0:
            if self._cnx[1][0] != None:
                self._cnx[1][0].close()
            self.log.debug('Connection à MySQL (user {})'.format(self.database_keys['user']))
            self._cnx[1][0] = mysql.connector.connect(user=self.database_keys['user'],password=self.database_keys['password'],host=self.database_keys['host'],database=self.database_keys['database2'],buffered=True)
            self._cnx[1][1] = round(time.time())
        else:
            raise ValueError(dict)
    
    async def user_avatar_as(self,user,size=512):
        """Get the avatar of an user, format gif or png (as webp isn't supported by some browsers)"""
        if not isinstance(user,(discord.User,discord.Member,discord.ClientUser)):
            raise ValueError
        try:
            if user.is_avatar_animated():
                return user.avatar_url_as(format='gif',size=size)
            else:
                return user.avatar_url_as(format='png',size=size)
        except Exception as e:
            await self.cogs['ErrorsCog'].on_error(e,None)
    
    class SafeDict(dict):
        def __missing__(self, key):
            return '{' + key + '}'
    
    async def get_prefix(self,msg):
        return get_prefix(self,msg)

def setup_logger():
    # on chope le premier logger
    log = logging.getLogger("runner")
    # on définis un formatteur
    format = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="[%d/%m/%Y %H:%M]")
    # ex du format : [08/11/2018 14:46] WARNING RSSCog fetch_rss_flux l.288 : Cannot get the RSS flux because of the following error: (suivi du traceback)

    # log vers un fichier
    file_handler = logging.FileHandler("debug.log")
    file_handler.setLevel(logging.DEBUG)  # tous les logs de niveau DEBUG et supérieur sont evoyés dans le fichier
    file_handler.setFormatter(format)

    # log vers la console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)  # tous les logs de niveau INFO et supérieur sont evoyés dans le fichier
    stream_handler.setFormatter(format)

    ## supposons que tu veuille collecter les erreurs sur ton site d'analyse d'erreurs comme sentry
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