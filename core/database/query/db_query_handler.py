from typing import TYPE_CHECKING, Any, Literal, overload

from core.type_utils import AnyDict, AnyTuple

from .db_multi_query import DatabaseMutliQueries
from .db_read_query import DatabaseReadQuery
from .db_write_query import DatabaseWriteQuery

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


class DatabaseQueryHandler:
    "Service class to create read and write queries to a database"

    def __init__(self, bot: "Axobot", database: str):
        self.bot = bot
        self.database = database

    @overload
    def read(
        self,
            query: str,
            args: AnyTuple | AnyDict | None = None,
            *,
            fetchone: Literal[True],
            astuple: Literal[True]
    ) -> DatabaseReadQuery[AnyTuple] : ...

    @overload
    def read(
        self,
            query: str,
            args: AnyTuple | AnyDict | None = None,
            *,
            fetchone: Literal[True],
            astuple: Literal[False] = False
    ) -> DatabaseReadQuery[AnyDict] : ...

    @overload
    def read(
        self,
            query: str,
            args: AnyTuple | AnyDict | None = None,
            *,
            fetchone: Literal[False] = False,
            astuple: Literal[True],
    ) -> DatabaseReadQuery[list[AnyTuple]] : ...

    @overload
    def read(
        self,
            query: str,
            args: AnyTuple | AnyDict | None = None,
            *,
            fetchone: Literal[False] = False,
            astuple: Literal[False] = False
    ) -> DatabaseReadQuery[list[AnyDict]] : ...

    def read(
        self,
            query: str,
            args: AnyTuple | AnyDict | None = None,
            fetchone: bool = False,
            astuple: bool = False
    ):
        "Perform a read query to the database"
        cnx = self.bot.db.get_connection(self.database)
        if query_type(query) != "read":
            raise ValueError(
                f"Expected read query, but received {truncate_query(query)}")
        return DatabaseReadQuery[Any](self.bot, cnx, query, args, fetchone, astuple)

    def write(
        self,
            query: str,
            args: AnyTuple | AnyDict | None = None,
            multi: bool = False,
            returnrowcount: bool = False
    ):
        "Perform a write query to the database"
        cnx = self.bot.db.get_connection(self.database)
        if query_type(query) != "write":
            raise ValueError(
                f"Expected write query, but received {truncate_query(query)}")
        return DatabaseWriteQuery(self.bot, cnx, query, args, multi, returnrowcount)

    def multi(self):
        "Create a context manager to execute multiple write queries on the same connection"
        cnx = self.bot.db.get_connection(self.database)
        return DatabaseMutliQueries(self.bot, cnx)


def query_type(query: str) -> Literal["read", "write"]:
    "Determine the type of given query"
    query = query.strip().lower().replace("\n", '')
    if query.startswith("set "):
        query = ';'.join(query.split(';')[1:])
    first_word = query.split()[0]
    if first_word in ("select", "show", "describe"):
        return "read"
    if first_word in ("insert", "update", "delete", "create", "alter", "drop"):
        return "write"
    raise ValueError(f"Unknown query type: {first_word}")


def truncate_query(query: str):
    "Truncate query to 150 characters"
    if len(query) > 150:
        return query[:150] + "..."
    return query
