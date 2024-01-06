import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_logger():
    """Create the logger module for the whole bot"""
    bot_logger = logging.getLogger("bot")
    log_format = logging.Formatter("[{asctime}] {levelname:<7} [{name}]: {message}", datefmt="%Y-%m-%d %H:%M:%S", style='{')

    # DEBUG logs to a file
    file_handler = RotatingFileHandler("logs/debug.log", maxBytes=1e6, backupCount=2, delay=True)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    file_handler.set_name("file")

    # INFO logs to console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)
    stream_handler.set_name("console")

    # add handlers to the logger
    bot_logger.addHandler(file_handler)
    bot_logger.addHandler(stream_handler)

    # set the logging level to DEBUG (so handlers can filter it)
    bot_logger.setLevel(logging.DEBUG)

    # add specific logger for database logs
    _setup_database_logger()

    return bot_logger

def _setup_database_logger():
    "Create the logger module for the database, as a sub-logger of the bot logger"
    db_logger = logging.getLogger("bot.db")
    log_format = logging.Formatter("[{asctime}] {levelname:<7} [{name}]: {message}", datefmt="%Y-%m-%d %H:%M:%S", style='{')

    # DEBUG logs to a file
    file_handler = RotatingFileHandler("logs/sql-debug.log", maxBytes=2e6, backupCount=2, delay=True)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)
    file_handler.set_name("file")

    # INFO logs to console
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(log_format)
    stream_handler.set_name("console")

    # add handlers to the logger
    db_logger.addHandler(file_handler)
    db_logger.addHandler(stream_handler)

    # set the logging level to DEBUG (so handlers can filter it)
    db_logger.setLevel(logging.DEBUG)
    # don't propagate the logs to the bot logger (so DEBUG logs don't appear in the console)
    db_logger.propagate = False

def set_beta_logs():
    "Edit the logging handlers to be more verbose in console, when the beta bot is used"
    # set the console logger to DEBUG
    bot_logger = logging.getLogger("bot")
    for handler in bot_logger.handlers:
        if handler.name == "console":
            handler.setLevel(logging.DEBUG)
            break
    # add discord.py logs to console
    discord_logger = logging.getLogger('discord')
    discord_logger.setLevel(logging.INFO)
    for handler in bot_logger.handlers:
        if handler.name == "console":
            discord_logger.addHandler(handler)
            break
