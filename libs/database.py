from typing import Union
from types import GeneratorType
from mysql.connector.connection import MySQLConnection, MySQLCursor


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

        async def __aenter__(self) -> Union[int, list[dict], dict]:
            self.cursor: MySQLCursor = cnx_frm.cursor(
                dictionary=(not self.astuple)
            )

            self.cursor.execute(self.query, self.args)
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
