import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from mysql.connector import errors
from mysql.connector.connection import MySQLConnection, MySQLCursor
from mysql.connector.connection_cext import CMySQLConnection, CMySQLCursor
from mysql.connector.cursor import (RE_PY_PARAM, _bytestr_format_dict,
                                    _ParamSubstitutor)

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
        if isinstance(self.cursor, MySQLCursor):
            return await self._format_query_native(self.cursor)
        # else: theoretically CMySQLConnection
        return await self._format_query_c(self.cursor)

    async def _format_query_native(self, cursor: MySQLCursor):
        # pylint: disable=protected-access
        operation = self.query
        params = self.args
        try:
            if not isinstance(operation, bytes | bytearray):
                stmt = operation.encode(cursor._connection.python_charset)
            else:
                stmt = operation
        except (UnicodeDecodeError, UnicodeEncodeError) as err:
            raise errors.ProgrammingError(str(err))

        if params:
            if isinstance(params, dict):
                stmt = _bytestr_format_dict(stmt, cursor._process_params_dict(params))
            elif isinstance(params, list | tuple):
                psub = _ParamSubstitutor(cursor._process_params(params))
                stmt = RE_PY_PARAM.sub(psub, stmt)
                if psub.remaining != 0:
                    raise errors.ProgrammingError(
                        "Not all parameters were used in the SQL statement")
            else:
                raise errors.ProgrammingError(
                    f"Could not process parameters: {type(params).__name__}({params}),"
                    " it must be of type list, tuple or dict")
        return stmt.decode("unicode_escape")

    async def _format_query_c(self, cursor: "CMySQLCursor"):
        # pylint: disable=protected-access
        operation = self.query
        params = self.args
        try:
            if isinstance(operation, str):
                stmt = operation.encode(cursor._cnx.python_charset)
            else:
                stmt = operation
        except (UnicodeDecodeError, UnicodeEncodeError) as err:
            raise errors.ProgrammingError(str(err))

        if params:
            prepared = cursor._cnx.prepare_for_mysql(params)
            if isinstance(prepared, dict):
                for key, value in prepared.items():
                    stmt = stmt.replace(f"%({key})s".encode(), value)
            elif isinstance(prepared, list | tuple):
                psub = _ParamSubstitutor(prepared)
                stmt = RE_PY_PARAM.sub(psub, stmt)
                if psub.remaining != 0:
                    raise errors.ProgrammingError(
                        "Not all parameters were used in the SQL statement")
            else:
                raise errors.ProgrammingError(
                    f"Could not process parameters: {type(params).__name__}({params}),"
                    " it must be of type list, tuple or dict")
        return stmt.decode("unicode_escape")

    async def _save_execution_time(self, start_time: float):
        if cog := self.bot.get_cog("BotStats"):
            delta_ms = (time.time() - start_time) * 1000
            cog.sql_performance_records.append(delta_ms)
