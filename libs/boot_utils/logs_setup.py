import logging
import sys
from logging.handlers import RotatingFileHandler


def setup_bot_logger():
    """Create the logger module for the bot, used for logs"""
    log = logging.getLogger("runner")
    log_format = logging.Formatter("%(asctime)s %(levelname)s: %(message)s", datefmt="[%d/%m/%Y %H:%M:%S]")

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
    log.addHandler(file_handler)
    log.addHandler(stream_handler)

    # set the logging level to DEBUG (so handlers can filter it)
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

def set_beta_logs():
    "Edit the logging level to DEBUG, when the beta bot is used"
    log = logging.getLogger("runner")
    for handler in log.handlers:
        if handler.name == "console":
            handler.setLevel(logging.DEBUG)
            break
