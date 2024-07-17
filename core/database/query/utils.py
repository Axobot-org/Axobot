import time
from typing import TYPE_CHECKING

from mysql.connector import errors
from mysql.connector.connection import MySQLCursor
from mysql.connector.connection_cext import CMySQLCursor
from mysql.connector.cursor import (RE_PY_PARAM, _bytestr_format_dict,
                                    _ParamSubstitutor)

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


async def save_execution_time(bot: "Axobot", start_time: float):
    "Save the execution time of a query to the bot's stats cog."
    if cog := bot.get_cog("BotStats"):
        delta_ms = (time.time() - start_time) * 1000
        cog.sql_performance_records.append(delta_ms)

async def format_query(cursor: MySQLCursor | CMySQLCursor, query: str, args: tuple | dict | None):
    "Create a formatted query string from the query and its arguments."
    if isinstance(cursor, MySQLCursor):
        return await _format_query_native(cursor, query, args)
    # else: theoretically CMySQLConnection
    return await _format_query_c(cursor, query, args)

async def _format_query_native(cursor: MySQLCursor, operation: str | bytes, params: tuple | dict | None):
    # pylint: disable=protected-access
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

async def _format_query_c(cursor: CMySQLCursor, operation: str | bytes, params: tuple | dict | None):
    # pylint: disable=protected-access
    try:
        if isinstance(operation, str):
            stmt = operation.encode(cursor._connection.python_charset)
        else:
            stmt = operation
    except (UnicodeDecodeError, UnicodeEncodeError) as err:
        raise errors.ProgrammingError(str(err))

    if params:
        prepared = cursor._connection.prepare_for_mysql(params)
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
