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
    if count > 0:
        return False
    del count
    return True


if check_libs():
    import discord, sys, traceback, asyncio, time, logging, os, mysql.connector, datetime, json
    from signal import SIGTERM
    from random import choice
    from discord.ext import commands
    from fcts import cryptage, tokens
    from classes import zbot, setup_logger
else:
    import sys
    print("Fin de l'exécution")
    sys.exit()


def main():
    client = zbot(case_insensitive=True,status=discord.Status('online'))

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
                      'fcts.voices',
                      'fcts.xp',
                      'fcts.halloween'
    ]
    # Suppression du fichier debug.log s'il est trop volumineux
    if os.path.exists("debug.log"):
        s = os.path.getsize('debug.log')/1.e9
        if s > 10:
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
        client.others['random_api_token'] = cryptage.uncrypte(r[18])
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
        if count  > 0:
            raise Exception("\n{} modules not loaded".format(count))
    del count
    
    
    async def on_ready():
        print('\nBot connecté')
        print("Nom : "+client.user.name)
        print("ID : "+str(client.user.id))
        if len(client.guilds) < 200:
            serveurs = [x.name for x in client.guilds]
            print("Connecté sur ["+str(len(client.guilds))+"] "+", ".join(serveurs))
        else:
            print("Connecté sur "+str(len(client.guilds))+" serveurs")
        print(time.strftime("%d/%m  %H:%M:%S"))
        print('------')
        await asyncio.sleep(3)
        if not client.database_online:
            await client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening,name=choice(["a signal",'a sign of life','nothing','a signal','a lost database'])))
        elif client.beta:
            await client.change_presence(activity=discord.Game(name=choice(["SNAPSHOOT","snapshot day","somethin iz brokn"])))
        else:
            await client.change_presence(activity=discord.Game(name=choice(["entrer !help","something","type !help","type !help"])))
        emb = client.cogs["Embeds"].Embed(desc="**{}** is launching !".format(client.user.name),color=8311585).update_timestamp()
        await client.cogs["Embeds"].send([emb])


    async def sigterm_handler(bot):
        print("SIGTERM received. Disconnecting...")
        await bot.logout()
    
    asyncio.get_event_loop().add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(sigterm_handler(client)))

    if client.database_online:
        if len(sys.argv) > 1 and sys.argv[1] in ['1','2','3','4']:
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
            if len(sys.argv) > 3 and sys.argv[3] in ['o','n']:
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