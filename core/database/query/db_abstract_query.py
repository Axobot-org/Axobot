import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from mysql.connector.connection import MySQLConnection, MySQLCursor
from mysql.connector.connection_cext import CMySQLConnection, CMySQLCursor

from .utils import format_query, save_execution_time

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


class DatabaseAbstractQuery(ABC):
    "Abstract base class for any database query."

    def __init__(self, bot: "Axobot", cnx: MySQLConnection | CMySQLConnection, query: str, args: tuple | dict | None = None):
        self.bot = bot
        self.cnx = cnx
        self.query = query
        self.args = args
        self.cursor: MySQLCursor | CMySQLCursor = None
        self.log = logging.getLogger("bot.sql")

    @abstractmethod
    async def __aenter__(self):
        "Enter the context manager and execute the query."

    async def __aexit__(self, exc_type, value, traceback):
        "Exit the context manager and close the cursor."
        if self.cursor is not None:
            self.cursor.close()

    async def _format_query(self):
        "Create a formatted query string from the query and its arguments."
        await format_query(self.cursor, self.query, self.args)

    async def _save_execution_time(self, start_time: float):
        await save_execution_time(self.bot, start_time)
