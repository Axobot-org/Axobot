#!/usr/bin/env python
#coding=utf-8

def check_libs():
    count = 0
    for m in ["mysql","discord","frmc_lib","requests","re","asyncio","datetime","time","importlib","traceback","sys","logging","sympy","psutil","platform","subprocess",'json','emoji','imageio','platform']:
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
    import discord, sys, traceback, asyncio, time, logging, os, mysql.connector
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


class zbot(commands.bot.BotBase,discord.Client):

    def __init__(self,command_prefix=None,case_insensitive=None,status=None,database_online=True,beta=False,dbl_token=""):
        super().__init__(command_prefix=command_prefix,case_insensitive=case_insensitive,status=status)
        self.database_online = database_online
        self.beta = beta
        self.database_keys = dict()
        self.log = logging.getLogger("runner")
        self.dbl_token = dbl_token
        self._cnx = [None,0]
        self.xp_enabled = True
    
    @property
    def cnx(self):
        if self._cnx[1] + 1260 < round(time.time()): # 21min
            self.connect_database()
            self._cnx[1] = round(time.time())
            return self._cnx[0]
        else:
            return self._cnx[0]
    
    def connect_database(self):
        if len(self.database_keys)>0:
            if self._cnx[0] != None:
                self._cnx[0].close()
            self.log.debug('Connection à MySQL (user {})'.format(self.database_keys['user']))
            self._cnx[0] = mysql.connector.connect(user=self.database_keys['user'],password=self.database_keys['password'],host=self.database_keys['host'],database=self.database_keys['database'])
            self._cnx[1] = round(time.time())
        else:
            raise ValueError(dict)
    
    async def user_avatar_as(self,user,size=512):
        """Get the avatar of an user, format gif or png (as webp isn't supported by some browsers)"""
        if not isinstance(user,(discord.User,discord.Member)):
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
            l = [bot.cogs['UtilitiesCog'].find_prefix(msg.guild)]
        except KeyError:
            try:
                bot.load_extension('fcts.utilities')
                l = [bot.cogs['UtilitiesCog'].find_prefix(msg.guild)]
            except Exception as e:
                bot.log.warn("[get_prefix]",e)
                l = ['!']
        except Exception as e:
                bot.log.warn("[get_prefix]",e)
                l = ['!']
    else:
        l = ['!']
    if msg.guild != None:
        return l+[msg.guild.me.mention+" "]
    else:
        return l+[bot.user.mention+" "]


def main():
    client = zbot(command_prefix=get_prefix,case_insensitive=True,status=discord.Status('online'))

    initial_extensions = ['fcts.admin',
                      'fcts.utilities',
                      'fcts.reloads',
                      'fcts.language',
                      'fcts.server',
                      'fcts.errors',
                      'fcts.perms',
                      'fcts.aide',
                      'fcts.mc',
                      'fcts.infos',
                      'fcts.timeclass',
                      'fcts.fun',
                      'fcts.rss',
                      'fcts.moderation',
                      'fcts.cases',
                      'fcts.bvn',
                      'fcts.emoji',
                      'fcts.embeds',
                      'fcts.events',
                      'fcts.timed',
                      'fcts.morpion',
                      'fcts.xp',
                      'fcts.users'
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
        for e,s in enumerate(['user','password','host','database']):
            client.database_keys[s] = cryptage.uncrypte(r[e])
    try:
        cnx = mysql.connector.connect(user=client.database_keys['user'],password=client.database_keys['password'],host=client.database_keys['host'],database=client.database_keys['database'])
        cnx.close()
    except Exception as e:
        print("---- ACCES IMPOSSIBLE A LA DATABASE ----")
        print(e)
        client.database_online = False

    if client.database_online:
        client.connect_database()

    client.dbl_token = tokens.get_dbl_token()

    # Here we load our extensions(cogs) listed above in [initial_extensions]
    count = 0
    for extension in initial_extensions:
        if not client.database_online:
            extension = extension.replace('fcts','fctshl')
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
        serveurs = []
        for i in client.guilds:
            serveurs.append(i.name)
        ihvbsdi="Connecté sur ["+str(len(client.guilds))+"] "+", ".join(serveurs)
        await utilities.print2(ihvbsdi)
        await utilities.print2(time.strftime("%d/%m  %H:%M:%S"))
        await utilities.print2('------')
        await asyncio.sleep(3)
        if not client.database_online:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=choice(["a signal",'a sign of life','nothing','a signal','a lost database'])))
        elif r=='1':
            await client.change_presence(activity=discord.Game(name=choice(["entrer !help","something","type !help","type !help"])))
        elif r=='2':
            await client.change_presence(activity=discord.Game(name=choice(["SNAPSHOOT","snapshot day","somethin iz brokn"])))
        emb = client.cogs["EmbedCog"].Embed(desc="**{}** is launching !".format(client.user.name),color=8311585).update_timestamp()
        await client.cogs["EmbedCog"].send([emb])
    
    async def check_once(ctx):
        try:
            return await ctx.bot.cogs['UtilitiesCog'].global_check(ctx)
        except Exception as e:
            ctx.bot.log.error("ERROR on global_check:",e,ctx.guild)
            return True

    async def on_member_join(member):
        await client.cogs['WelcomerCog'].new_member(member)

    async def on_member_remove(member):
        await client.cogs['WelcomerCog'].bye_member(member)

    async def on_guild_join(guild):
        await client.cogs["Events"].on_guild_add(guild)

    async def on_guild_remove(guild):
        await client.cogs["Events"].on_guild_del(guild)

    async def on_message(msg):
        await client.cogs["Events"].on_new_message(msg)


    async def sigterm_handler(bot):
        print("SIGTERM received. Disconnecting...")
        await bot.logout()
    
    asyncio.get_event_loop().add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(sigterm_handler(client)))


    if client.database_online:
        r=input("Quel bot activer ? (1 release, 2 snapshot, 3 redbot, 4 autre) ")
        if r=='1':
            token = tokens.get_token(client,486896267788812288)
        elif r=='2':
            token = tokens.get_token(client,436835675304755200)
            client.beta = True
        elif r=='3':
            token = tokens.get_token(client,541740438953132032)
            client.beta = True
        elif r=='4':
            token = input("Token?\n> ")
        else:
            return
        if r in ['1','2']:
            r3=input("Lancement de la boucle d'events' ? (o/n) ")
            if r3=='o':
                client.loop.create_task(client.cogs["Events"].loop())
    else:
        token = input("Token?\n> ")
        if len(token)<10:
            return

    client.add_listener(on_ready)
    client.add_check(check_once,call_once=True)
    client.add_listener(on_member_join)
    client.add_listener(on_member_remove)
    client.add_listener(on_message)
    client.add_listener(on_guild_join)
    client.add_listener(on_guild_remove)
    
    log = setup_logger()
    log.setLevel(logging.DEBUG)
    log.info("Lancement du bot")

    client.run(token)


if check_libs() and __name__ == "__main__":
    main()