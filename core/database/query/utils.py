import time
from typing import TYPE_CHECKING

from mysql.connector import errors
from mysql.connector.cursor import (RE_PY_PARAM, MySQLCursor,
                                    _bytestr_format_dict, _ParamSubstitutor) # type: ignore
from mysql.connector.cursor_cext import CMySQLCursor

from core.type_utils import AnyDict, AnyTuple

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


async def save_execution_time(bot: "Axobot", start_time: float):
    "Save the execution time of a query to the bot's stats cog."
    if cog := bot.get_cog("BotStats"):
        delta_ms = (time.time() - start_time) * 1000
        cog.sql_performance_records.append(delta_ms)

async def format_query(cursor: MySQLCursor | CMySQLCursor, query: str, args: AnyTuple | AnyDict | None):
    "Create a formatted query string from the query and its arguments."
    if isinstance(cursor, MySQLCursor):
        return await _format_query_native(cursor, query, args)
    # else: theoretically CMySQLConnection
    return await _format_query_c(cursor, query, args)

async def _format_query_native(cursor: MySQLCursor, operation: str | bytes, params: AnyTuple | AnyDict | None):
    # pylint: disable=protected-access
    try:
        if not isinstance(operation, bytes | bytearray):
            stmt = operation.encode(cursor._connection.python_charset) # type: ignore
        else:
            stmt = operation
    except (UnicodeDecodeError, UnicodeEncodeError) as err:
        raise errors.ProgrammingError(str(err))

    if params:
        if isinstance(params, dict):
            stmt = _bytestr_format_dict(stmt, cursor._process_params_dict(params)) # type: ignore
        else:
            psub = _ParamSubstitutor(cursor._process_params(params)) # type: ignore
            stmt = RE_PY_PARAM.sub(psub, stmt)
            if psub.remaining != 0:
                raise errors.ProgrammingError(
                    "Not all parameters were used in the SQL statement")
    return stmt.decode("unicode_escape")

async def _format_query_c(cursor: CMySQLCursor, operation: str | bytes, params: AnyTuple | AnyDict | None):
    # pylint: disable=protected-access
    try:
        if isinstance(operation, str):
            stmt = operation.encode(cursor._connection.python_charset) # type: ignore
        else:
            stmt = operation
    except (UnicodeDecodeError, UnicodeEncodeError) as err:
        raise errors.ProgrammingError(str(err))

    if params:
        prepared = cursor._connection.prepare_for_mysql(params) # type: ignore
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
