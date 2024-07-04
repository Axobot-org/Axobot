import datetime
import sys
import time
from typing import TYPE_CHECKING

from mysql.connector import errors
from mysql.connector.connection import MySQLConnection
from mysql.connector.connection_cext import CMySQLConnection

from core.database.query.db_abstract_query import DatabaseAbstractQuery

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


class DatabaseReadQuery(DatabaseAbstractQuery):
    "Represents a context manager to execute a SELECT or SHOW query to a database"

    def __init__(self, bot: "Axobot", cnx: MySQLConnection | CMySQLConnection, query: str, args: tuple | dict | None = None,
                 fetchone: bool = False, astuple: bool = False):
        super().__init__(bot, cnx, query, args)
        self.fetchone = fetchone
        self.astuple = astuple

    async def __aenter__(self) -> tuple | dict | None:
        self.cursor = self.cnx.cursor(
            dictionary=(not self.astuple)
        )

        query_for_logs = await self._format_query()
        self.log.debug("%s", query_for_logs)

        start_time = time.time()

        try:
            self.cursor.execute(self.query, self.args)
        except errors.ProgrammingError as err:
            self.log.error("%s", self.cursor._executed, exc_info=True)
            await self.__aexit__(*sys.exc_info())
            raise err

        return_type = tuple if self.astuple else dict
        if self.fetchone:
            one_row = self.cursor.fetchone()
            result = return_type() if one_row is None else return_type(one_row)
        else:
            result = list(map(return_type, self.cursor.fetchall()))
            # convert datetime objects to UTC
            for row in result:
                for key, value in (row.items() if isinstance(row, dict) else enumerate(row)):
                    if isinstance(value, datetime.datetime) and value.tzinfo is None:
                        row[key] = value.replace(tzinfo=datetime.UTC)

        await self._save_execution_time(start_time)
        return result
