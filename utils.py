import argparse
import glob
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING
from LRFutils import progress
from mysql.connector import errors as mysql_errors

import discord
import mysql
from discord.ext import commands

if TYPE_CHECKING:
    from libs.bot_classes import Axobot

OUTAGE_REASON = {
    'fr': "Nous faisons de notre mieux pour rétablir nos services dans les plus brefs délais, mais la panne peut être hors de notre contrôle. Plus d'informations sur https://axobot.statuspage.io/ ou sur notre serveur Discord.",
    'en': "We're doing our best to restore our services as soon as possible, but the failure may be beyond our control. More information on https://axobot.statuspage.io/ or in our Discord server."
}

async def get_prefix(bot:"Axobot", msg: discord.Message) -> list:
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
    log_format = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")
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
    parser.add_argument('--entity-id', '-e', type=int, help="The entity ID to use, if no bot is specified by --token")
    parser.add_argument('--no-main-loop', help="Deactivate the bot main loop",
                        action="store_false", dest="event_loop")
    parser.add_argument('--no-rss', help="Disable any RSS feature (loop and commands)",
                        action="store_false", dest="rss_features")

    return parser

def load_sql_connection(bot: "Axobot"):
    "Load the connection to the database, preferably in local mode"
    try:
        try:
            cnx = mysql.connector.connect(
                user=bot.database_keys['user'],
                password=bot.database_keys['password'],
                host="127.0.0.1",
                database=bot.database_keys['database1']
            )
        except (mysql_errors.InterfaceError, mysql_errors.ProgrammingError, mysql_errors.DatabaseError):
            bot.log.warning("Unable to access local dabatase - attempt via IP")
            cnx = mysql.connector.connect(
                user=bot.database_keys['user'],
                password=bot.database_keys['password'],
                host=bot.database_keys['host'],
                database=bot.database_keys['database1'],
                connection_timeout=5
            )
            bot.log.info("Database connected remotely")
        else:
            bot.log.info("Database connected locally")
            bot.database_keys['host'] = '127.0.0.1'
        cnx.close()
    except Exception as err:
        bot.log.error("---- UNABLE TO REACH THE DATABASE ----")
        bot.log.error(err)
        bot.database_online = False

async def load_cogs(bot: "Axobot"):
    "Load the bot modules"
    initial_extensions = [
        'fcts.languages',
        'fcts.admin',
        'fcts.help_cmd',
        'fcts.antiraid',
        'fcts.antiscam',
        'fcts.bot_events',
        'fcts.bot_info',
        'fcts.bot_stats',
        'fcts.cases',
        'fcts.embeds',
        'fcts.errors',
        'fcts.events',
        'fcts.fun',
        'fcts.halloween',
        'fcts.info',
        'fcts.library',
        'fcts.minecraft',
        'fcts.moderation',
        'fcts.morpions',
        'fcts.partners',
        'fcts.perms',
        'fcts.poll',
        'fcts.reloads',
        'fcts.roles_management',
        'fcts.roles_react',
        'fcts.rss',
        'fcts.s_backups',
        'fcts.serverlogs',
        'fcts.serverconfig',
        'fcts.tickets',
        'fcts.timers',
        'fcts.twitch',
        'fcts.users_cache',
        'fcts.users',
        'fcts.utilities',
        'fcts.voice_channels',
        'fcts.voice_msg',
        'fcts.welcomer',
        'fcts.xp'
    ]
    progress_bar = progress.Bar(max=len(initial_extensions), width=60, prefix="Loading extensions", eta=False, show_duration=False)

    # Here we load our extensions (cogs) listed above in [initial_extensions]
    count = 0
    for i, extension in enumerate(initial_extensions):
        progress_bar(i)
        try:
            await bot.load_extension(extension)
        except discord.DiscordException:
            bot.log.critical('Failed to load extension %s', extension, exc_info=True)
            count += 1
        if count  > 0:
            bot.log.critical("%s modules not loaded\nEnd of program", count)
            sys.exit()
    progress_bar(len(initial_extensions), stop=True)

async def count_code_lines():
    """Count lines of Python code in the current folder

    Comments and empty lines are ignored."""
    count = 0
    path = os.path.dirname(__file__)+'/**/*.py'
    for filename in glob.iglob(path, recursive=True):
        if '/env/' in filename or not filename.endswith('.py'):
            continue
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file.read().split("\n"):
                cleaned_line = line.strip()
                if len(cleaned_line) > 2 and not cleaned_line.startswith('#') or cleaned_line.startswith('"'):
                    count += 1
    return count
