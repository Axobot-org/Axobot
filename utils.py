import argparse
import glob
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING

import discord
import mysql
from discord.ext import commands

from fcts import cryptage, tokens  # pylint: disable=no-name-in-module

if TYPE_CHECKING:
    from libs.classes import Zbot

OUTAGE_REASON = {
    'fr': "Un des datacenters de notre hébergeur OVH a pris feu, rendant ,inaccessible le serveur et toutes ses données. Une vieille sauvegarde de la base de donnée sera peut-être utilisée ultérieurement. Plus d'informations sur https://zbot.statuspage.io/",
    'en': "One of the datacenters of our host OVH caught fire, making the server and all its data inaccessible. An old backup of the database may be used later. More information on https://zbot.statuspage.io/"
}

async def get_prefix(bot:"Zbot", msg: discord.Message) -> list:
    """Get the correct bot prefix from a message
    Prefix can change based on guild, but the bot mention will always be an option"""
    prefixes = [await bot.prefix_manager.get_prefix(msg.guild)]
    if msg.guild is None:
        prefixes.append("")
    return commands.when_mentioned_or(*prefixes)(bot, msg)



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

def parse_crypted_file(bot: "Zbot"):
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
    bot.others['google_api'] = cryptage.uncrypte(lines[19])
    bot.dbl_token = tokens.get_dbl_token()

def load_sql_connection(bot: "Zbot"):
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

def load_cogs(bot: "Zbot"):
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

async def count_code_lines():
    """Count lines of Python code in the current folder
    
    Comments and empty lines are ignored."""
    count = 0
    path = os.path.dirname(__file__)+'/**/*.py'
    for filename in glob.iglob(path, recursive=True):
        if '/env/' in filename or not filename.endswith('.py'):
            continue
        with open(filename, 'r') as file:
            for line in file.read().split("\n"):
                cleaned_line = line.strip()
                if len(cleaned_line) > 2 and not cleaned_line.startswith('#'):
                    count += 1
    return count
