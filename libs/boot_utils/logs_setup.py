import logging
import sys
from logging.handlers import RotatingFileHandler

from discord.utils import stream_supports_colour


def setup_logger():
    """Create the logger module for the whole bot"""
    bot_logger = logging.getLogger("bot")

    # DEBUG logs to a file
    file_handler = RotatingFileHandler("logs/debug.log", maxBytes=5e6, backupCount=2, delay=True)
    file_handler.setLevel(logging.DEBUG)
    _set_logging_formatter(file_handler)
    file_handler.set_name("file")

    # INFO logs to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    _set_logging_formatter(console_handler)
    console_handler.set_name("console")

    # add handlers to the logger
    bot_logger.addHandler(file_handler)
    bot_logger.addHandler(console_handler)

    # set the logging level to DEBUG (so handlers can filter it)
    bot_logger.setLevel(logging.DEBUG)

    # add specific logger for database logs
    _setup_database_logger()

    return bot_logger

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


def _setup_database_logger():
    "Create the logger module for the database, as a sub-logger of the bot logger"
    db_logger = logging.getLogger("bot.db")

    # DEBUG logs to a file
    file_handler = RotatingFileHandler("logs/sql-debug.log", maxBytes=5e6, backupCount=2, delay=True)
    file_handler.setLevel(logging.DEBUG)
    _set_logging_formatter(file_handler)
    file_handler.set_name("file")

    # INFO logs to console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    _set_logging_formatter(console_handler)
    console_handler.set_name("console")

    # add handlers to the logger
    db_logger.addHandler(file_handler)
    db_logger.addHandler(console_handler)

    # set the logging level to DEBUG (so handlers can filter it)
    db_logger.setLevel(logging.DEBUG)
    # don't propagate the logs to the bot logger (so DEBUG logs don't appear in the console)
    db_logger.propagate = False

def _set_logging_formatter(handler: logging.StreamHandler):
    "Return a logging formatter with or without colors"
    if not stream_supports_colour(handler.stream):
        formatter = logging.Formatter(
            fmt="[{asctime}] {levelname:<7} [{name}]: {message}",
            datefmt="%Y-%m-%d %H:%M:%S",
            style='{'
        )
    else:
        formatter = _ColourFormatter()
    handler.setFormatter(formatter)

class _ColourFormatter(logging.Formatter):
    "A formatter that adds colors to the log messages"
    LEVEL_COLOURS = [
        (logging.DEBUG, '\x1b[40;1m'),
        (logging.INFO, '\x1b[34;1m'),
        (logging.WARNING, '\x1b[33;1m'),
        (logging.ERROR, '\x1b[31m'),
        (logging.CRITICAL, '\x1b[41m'),
    ]

    FORMATS = {
        level: logging.Formatter(
            f'\x1b[30;1m%(asctime)s\x1b[0m {colour}%(levelname)-7s\x1b[0m \x1b[35m[%(name)s]\x1b[0m: %(message)s',
            '%Y-%m-%d %H:%M:%S',
        )
        for level, colour in LEVEL_COLOURS
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        if formatter is None:
            formatter = self.FORMATS[logging.DEBUG]

        # Override the traceback to always print in red
        if record.exc_info:
            text = formatter.formatException(record.exc_info)
            record.exc_text = f'\x1b[31m{text}\x1b[0m'

        output = formatter.format(record)

        # Remove the cache layer
        record.exc_text = None
        return output
