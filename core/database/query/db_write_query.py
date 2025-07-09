import sys
import time
from typing import TYPE_CHECKING

from mysql.connector import errors
from mysql.connector.connection import MySQLConnection
from mysql.connector.connection_cext import CMySQLConnection

from core.database.query.db_abstract_query import DatabaseAbstractQuery
from core.type_utils import AnyDict, AnyTuple

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot

class DatabaseWriteQuery(DatabaseAbstractQuery):
    "Represents a context manager to execute an INSERT, UPDATE, DELETE, or other write query to a database"

    def __init__(self, bot: "Axobot", cnx: MySQLConnection | CMySQLConnection, query: str, args: AnyTuple | AnyDict | None = None,
                 multi: bool = False, returnrowcount: bool = False):
        super().__init__(bot, cnx, query, args)
        self.multi = multi
        self.returnrowcount = returnrowcount

    async def __aenter__(self) -> int | None:
        self.cursor = self.cnx.cursor()

        query_for_logs = await self._format_query()
        self.log.debug("%s", query_for_logs)

        start_time = time.time()

        try:
            execute_result = self.cursor.execute(self.query, self.args, multi=self.multi) # type: ignore
        except errors.ProgrammingError as err:
            self.log.error("%s", self.cursor._executed, exc_info=True) # type: ignore
            await self.__aexit__(*sys.exc_info())
            raise err

        if self.multi and execute_result is not None:
            # make sure to execute every query
            for _ in execute_result:
                execute_result.send(None)
        self.cnx.commit()

        if self.returnrowcount:
            result = self.cursor.rowcount
        else:
            result = self.cursor.lastrowid

        await self._save_execution_time(start_time)
        return result
