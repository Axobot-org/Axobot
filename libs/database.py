import logging
import sys
from types import GeneratorType
from typing import TYPE_CHECKING, Union

from mysql.connector import errors
from mysql.connector.connection import MySQLConnection, MySQLCursor
from mysql.connector.cursor import RE_PY_PARAM, _bytestr_format_dict, _ParamSubstitutor

if TYPE_CHECKING:
    from mysql.connector.connection_cext import CMySQLConnection, CMySQLCursor


def create_database_query(cnx_axobot: Union[MySQLConnection, 'CMySQLConnection']):
    """Create a database query object using a specific database connector"""

    class DatabaseQuery:
        """Represents a context manager to execute a query to a database"""

        def __init__(self, query: str, args: Union[tuple, dict] = None, *,
        fetchone: bool = False, multi: bool = False, returnrowcount: bool = False, astuple: bool = False):
            self.query = query
            self.multi = multi
            self.args = () if args is None else args
            if isinstance(self.args, GeneratorType):
                self.args = tuple(self.args)
            self.fetchone = fetchone
            self.returnrowcount = returnrowcount
            self.astuple = astuple
            self.cursor: Union[MySQLCursor, 'CMySQLCursor'] = None
            self.log = logging.getLogger("bot.db")

        async def _format_query(self):
            if isinstance(self.cursor, MySQLCursor):
                return await self._format_query_native(self.cursor)
            # else: theoretically CMySQLConnection
            return await self._format_query_c(self.cursor)

        async def _format_query_native(self, cursor: MySQLCursor):
            # pylint: disable=protected-access
            operation = self.query
            params = self.args
            try:
                if not isinstance(operation, (bytes, bytearray)):
                    stmt = operation.encode(cursor._connection.python_charset)
                else:
                    stmt = operation
            except (UnicodeDecodeError, UnicodeEncodeError) as err:
                raise errors.ProgrammingError(str(err))

            if params:
                if isinstance(params, dict):
                    stmt = _bytestr_format_dict(stmt, cursor._process_params_dict(params))
                elif isinstance(params, (list, tuple)):
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

        async def _format_query_c(self, cursor: 'CMySQLCursor'):
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
                elif isinstance(prepared, (list, tuple)):
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


        async def __aenter__(self) -> Union[int, list[dict], dict]:
            self.cursor: MySQLCursor = cnx_axobot.cursor(
                dictionary=(not self.astuple)
            )

            query_for_logs = await self._format_query()
            self.log.debug("%s", query_for_logs)

            try:
                execute_result = self.cursor.execute(self.query, self.args, multi=self.multi)
            except errors.ProgrammingError as err:
                self.log.error("%s", self.cursor._executed, exc_info=True)
                await self.__aexit__(*sys.exc_info())
                raise err

            if self.query.strip().startswith("SELECT") or self.query.strip().startswith("SHOW"):
                return_type = tuple if self.astuple else dict
                if self.fetchone:
                    one_row = self.cursor.fetchone()
                    result = return_type() if one_row is None else return_type(one_row)
                else:
                    result = list(map(return_type, self.cursor.fetchall()))
            else:
                if self.multi:
                    # make sure to execute every query
                    for _ in execute_result:
                        execute_result.send(None)
                cnx_axobot.commit()
                if self.returnrowcount:
                    result = self.cursor.rowcount
                else:
                    result = self.cursor.lastrowid

            return result

        async def __aexit__(self, exc_type, value, traceback):
            if self.cursor is not None:
                self.cursor.close()

    return DatabaseQuery
