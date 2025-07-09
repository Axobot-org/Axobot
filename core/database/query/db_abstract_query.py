import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from mysql.connector.connection import MySQLConnection
from mysql.connector.connection_cext import CMySQLConnection
from mysql.connector.cursor import MySQLCursor
from mysql.connector.cursor_cext import CMySQLCursor

from core.type_utils import AnyDict, AnyTuple

from .utils import format_query, save_execution_time

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


class DatabaseAbstractQuery(ABC):
    "Abstract base class for any database query."

    cursor: MySQLCursor | CMySQLCursor

    def __init__(self,
                 bot: "Axobot", cnx: MySQLConnection | CMySQLConnection, query: str, args: AnyTuple | AnyDict | None = None):
        self.bot = bot
        self.cnx = cnx
        self.query = query
        self.args = args
        self.log = logging.getLogger("bot.sql")

    @abstractmethod
    async def __aenter__(self) -> Any:
        "Enter the context manager and execute the query."

    async def __aexit__(self, exc_type, value, traceback):
        "Exit the context manager and close the cursor."
        self.cursor.close()

    async def _format_query(self):
        "Create a formatted query string from the query and its arguments."
        return await format_query(self.cursor, self.query, self.args)

    async def _save_execution_time(self, start_time: float):
        await save_execution_time(self.bot, start_time)
