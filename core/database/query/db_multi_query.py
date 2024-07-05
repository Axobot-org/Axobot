import logging
import sys
from typing import TYPE_CHECKING, Self

from mysql.connector import errors
from mysql.connector.connection import MySQLConnection, MySQLCursor
from mysql.connector.connection_cext import CMySQLConnection, CMySQLCursor

from .utils import format_query

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


class DatabaseMutliQueries():
    "Represents a context manager to execute multiple write queries with the same cursor"

    def __init__(self, bot: "Axobot", cnx: MySQLConnection | CMySQLConnection):
        self.bot = bot
        self.cnx = cnx
        self.cursor: MySQLCursor | CMySQLCursor | None = None
        self.log = logging.getLogger("bot.sql")

    async def __aenter__(self) -> Self:
        if self.cursor is None:
            self.cursor = self.cnx.cursor()
        return self

    async def __aexit__(self, exc_type, value, traceback):
        if self.cursor is not None:
            self.cnx.commit()
            self.cursor.close()

    async def write(self, query: str, args: tuple | dict | None = None):
        """Execute a write query, but delay the commit until the context manager exits"""
        query_for_logs = await format_query(self.cursor, query, args)
        self.log.debug("%s", query_for_logs)

        try:
            self.cursor.execute(query, args)
        except errors.ProgrammingError as err:
            # pylint: disable=protected-access
            self.log.error("%s", self.cursor._executed, exc_info=True)
            await self.__aexit__(*sys.exc_info())
            raise err
