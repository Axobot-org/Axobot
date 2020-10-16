#!/usr/bin/env python
#coding=utf-8

def check_libs():
    count = 0
    for m in ["mysql","discord","frmc_lib","aiohttp","requests","re","asyncio","datetime","time","importlib","traceback","sys","logging","psutil","platform","subprocess",'json','emoji','imageio','geocoder','tzwhere','pytz','twitter','isbnlib']:
        try:
            exec("import "+m)
            exec("del "+m)
        except ModuleNotFoundError:
            print("Library {} manquante".format(m))
            count +=1
    if count>0:
        return False
    del count
    return True


if check_libs():
    import discord, sys, traceback, asyncio, time, logging, os, mysql.connector, datetime, json
    from signal import SIGTERM
    from random import choice
    from discord.ext import commands
    from fcts import cryptage, tokens
else:
    import sys
    print("Fin de l'exécution")
    sys.exit()


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


class zbot(commands.bot.AutoShardedBot):

    def __init__(self,command_prefix=None,case_insensitive=None,status=None,database_online=True,beta=False,dbl_token=""):
        ALLOWED = discord.AllowedMentions(everyone=False, roles=False)
        intents = discord.Intents.all()
        intents.typing = False
        intents.webhooks = False
        intents.integrations = False
        super().__init__(command_prefix=command_prefix, case_insensitive=case_insensitive, status=status, allowed_mentions=ALLOWED, intents=intents)
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
    def cnx_frm(self):
        if self._cnx[0][1] + 1260 < round(time.time()): # 21min
            self.connect_database_frm()
            self._cnx[0][1] = round(time.time())
            return self._cnx[0][0]
        else:
            return self._cnx[0][0]
    
    @property
    def current_event(self):
        try:
            return self.cogs["BotEventsCog"].current_event
        except Exception as e:
            self.log.warn(f"[current_event] {e}", exc_info=True)
            return None
    
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


def main():
    client = zbot(command_prefix=get_prefix,case_insensitive=True,status=discord.Status('online'))

    log = setup_logger()
    log.setLevel(logging.DEBUG)
    log.info("Lancement du bot")

    initial_extensions = ['fcts.language',
                      'fcts.admin',
                      'fcts.aide',
                      'fcts.bot_events',
                      'fcts.bvn',
                      'fcts.cases',
                      'fcts.embeds',
                      'fcts.emojis',
                      'fcts.errors',
                      'fcts.events',
                      'fcts.fun',
                      'fcts.infos',
                      'fcts.library',
                      'fcts.mc',
                      'fcts.moderation',
                      'fcts.morpion',
                      'fcts.partners',
                      'fcts.perms',
                      'fcts.reloads',
                      'fcts.roles_react',
                      'fcts.rss2',
                      'fcts.s_backup',
                      'fcts.server',
                      'fcts.timeclass',
                      'fcts.timers',
                      'fcts.translators',
                      'fcts.users',
                      'fcts.utilities',
                      'fcts.xp',
                      'fcts.halloween'
    ]
    # Suppression du fichier debug.log s'il est trop volumineux
    if os.path.exists("debug.log"):
        s = os.path.getsize('debug.log')/1.e9
        if s>10:
            print("Taille de debug.log supérieure à 10Gb ({}Gb)\n   -> Suppression des logs".format(s))
            os.remove('debug.log')
        del s

    with open('fcts/requirements','r') as file:
        r = file.read().split('\n')
        for s in r:
            if s.startswith("//") or s=='':
                r.remove(s)
        while '' in r:
            r.remove('')
        for e,s in enumerate(['user','password','host','database1','database2']):
            client.database_keys[s] = cryptage.uncrypte(r[e])
        client.others['arcanecenter'] = cryptage.uncrypte(r[5])
        client.others['botsondiscord'] = cryptage.uncrypte(r[6])
        client.others['discordbotsgroup'] = cryptage.uncrypte(r[7])
        client.others['bitly'] = cryptage.uncrypte(r[8])
        client.others['twitter'] = {'consumer_key':cryptage.uncrypte(r[9]),
            'consumer_secret':cryptage.uncrypte(r[10]),
            'access_token_key':cryptage.uncrypte(r[11]),
            'access_token_secret':cryptage.uncrypte(r[12])}
        client.others['botlist.space'] = cryptage.uncrypte(r[13])
        client.others['discordboats'] = cryptage.uncrypte(r[14])
        client.others['discordextremelist'] = cryptage.uncrypte(r[15])
        client.others['statuspage'] = cryptage.uncrypte(r[16])
        client.others['nasa'] = cryptage.uncrypte(r[17])
    try:
        try:
            cnx = mysql.connector.connect(user=client.database_keys['user'],password=client.database_keys['password'],host="127.0.0.1",database=client.database_keys['database1'])
        except (mysql.connector.InterfaceError, mysql.connector.ProgrammingError):
            client.log.warning("Impossible d'accéder à la dabatase locale - tentative via IP")
            cnx = mysql.connector.connect(user=client.database_keys['user'],password=client.database_keys['password'],host=client.database_keys['host'],database=client.database_keys['database1'])
        else:
            client.log.info("Database connectée en local")
            client.database_keys['host'] = '127.0.0.1'
        cnx.close()
    except Exception as e:
        client.log.error("---- ACCES IMPOSSIBLE A LA DATABASE ----")
        client.log.error(e)
        client.database_online = False

    if client.database_online:
        client.connect_database_frm()
        client.connect_database_xp()

    client.dbl_token = tokens.get_dbl_token()

    # Here we load our extensions(cogs) listed above in [initial_extensions]
    count = 0
    for extension in initial_extensions:
        try:
            client.load_extension(extension)
        except:
            print(f'\nFailed to load extension {extension}', file=sys.stderr)
            traceback.print_exc()
            count += 1
        if count >0:
            raise Exception("\n{} modules not loaded".format(count))
    del count
    
    
    utilities = client.cogs["UtilitiesCog"]

    async def on_ready():
        await utilities.print2('\nBot connecté')
        await utilities.print2("Nom : "+client.user.name)
        await utilities.print2("ID : "+str(client.user.id))
        if len(client.guilds) < 200:
            serveurs = [x.name for x in client.guilds]
            await utilities.print2("Connecté sur ["+str(len(client.guilds))+"] "+", ".join(serveurs))
        else:
            await utilities.print2("Connecté sur "+str(len(client.guilds))+" serveurs")
        await utilities.print2(time.strftime("%d/%m  %H:%M:%S"))
        await utilities.print2('------')
        await asyncio.sleep(3)
        if not client.database_online:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=choice(["a signal",'a sign of life','nothing','a signal','a lost database'])))
        elif client.beta:
            await client.change_presence(activity=discord.Game(name=choice(["SNAPSHOOT","snapshot day","somethin iz brokn"])))
        else:
            await client.change_presence(activity=discord.Game(name=choice(["entrer !help","something","type !help","type !help"])))
        emb = client.cogs["EmbedCog"].Embed(desc="**{}** is launching !".format(client.user.name),color=8311585).update_timestamp()
        await client.cogs["EmbedCog"].send([emb])


    async def sigterm_handler(bot):
        print("SIGTERM received. Disconnecting...")
        await bot.logout()
    
    asyncio.get_event_loop().add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(sigterm_handler(client)))

    if client.database_online:
        if len(sys.argv)>1 and sys.argv[1] in ['1','2','3','4']:
            bot_type = sys.argv[1]
        else:
            bot_type = input("Quel bot activer ? (1 release, 2 snapshot, 3 redbot, 4 autre) ")
        if bot_type == '1':
            token = tokens.get_token(client,486896267788812288)
        elif bot_type == '2':
            token = tokens.get_token(client,436835675304755200)
            client.beta = True
        elif bot_type == '3':
            token = tokens.get_token(client,541740438953132032)
            client.beta = True
        elif bot_type == '4':
            token = input("Token?\n> ")
        else:
            return
        if bot_type in ['1','2']:
            # Events loop
            if len(sys.argv)>2 and sys.argv[2] in ['o','n']:
                enable_event_loop = sys.argv[2]
            else:
                enable_event_loop = input("Lancement de la boucle d'events ? (o/n) ")
            if enable_event_loop.lower() == 'o':
                client.cogs['Events'].loop.start()
                client.internal_loop_enabled = True
            # RSS enabled
            if len(sys.argv)>3 and sys.argv[3] in ['o','n']:
                enable_rss = sys.argv[3]
            else:
                enable_rss = input("Activation des flux RSS ? (o/n) ")
            if enable_rss.lower() != 'o':
                client.rss_enabled = False
    else:
        token = input("Token?\n> ")
        if len(token)<10:
            return

    client.add_listener(on_ready)

    client.run(token)


if check_libs() and __name__ == "__main__":
    main()