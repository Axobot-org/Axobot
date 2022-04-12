import logging
from types import GeneratorType
from typing import Union

from mysql.connector.connection import MySQLConnection, MySQLCursor
from mysql.connector.cursor import _bytestr_format_dict, _ParamSubstitutor, RE_PY_PARAM
from mysql.connector import errors


def create_database_query(cnx_frm: MySQLConnection):
    """Create a database query object using a specific database connector"""

    class DatabaseQuery:
        """Represents a context manager to execute a query to a database"""

        def __init__(self, query: str, args: Union[tuple, dict] = None, *,
        fetchone: bool = False, returnrowcount: bool = False, astuple: bool = False):
            self.query = query
            self.args = () if args is None else args
            if isinstance(self.args, GeneratorType):
                self.args = tuple(self.args)
            self.fetchone = fetchone
            self.returnrowcount = returnrowcount
            self.astuple = astuple
            self.cursor: MySQLCursor = None

        async def _format_query(self):
            # pylint: disable=protected-access
            operation = self.query
            params = self.args
            try:
                if not isinstance(operation, (bytes, bytearray)):
                    stmt = operation.encode(self.cursor._connection.python_charset)
                else:
                    stmt = operation
            except (UnicodeDecodeError, UnicodeEncodeError) as err:
                raise errors.ProgrammingError(str(err))

            if params:
                if isinstance(params, dict):
                    stmt = _bytestr_format_dict(stmt, self.cursor._process_params_dict(params))
                elif isinstance(params, (list, tuple)):
                    psub = _ParamSubstitutor(self.cursor._process_params(params))
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
            self.cursor: MySQLCursor = cnx_frm.cursor(
                dictionary=(not self.astuple)
            )

            query_for_logs = await self._format_query()
            logging.getLogger("database").debug("%s", query_for_logs)

            try:
                self.cursor.execute(self.query, self.args)
            except errors.ProgrammingError:
                logging.getLogger("database").error("%s", self.cursor._executed)

            if self.query.startswith("SELECT"):
                return_type = tuple if self.astuple else dict
                if self.fetchone:
                    one_row = self.cursor.fetchone()
                    result = return_type() if one_row is None else return_type(one_row)
                else:
                    result = list(map(return_type, self.cursor.fetchall()))
            else:
                cnx_frm.commit()
                if self.returnrowcount:
                    result = self.cursor.rowcount
                else:
                    result = self.cursor.lastrowid

            return result

        async def __aexit__(self, exc_type, value, traceback):
            if self.cursor is not None:
                self.cursor.close()

    return DatabaseQuery
