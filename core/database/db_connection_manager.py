import logging
import time
from typing import NamedTuple

from mysql.connector import connect as sql_connect
from mysql.connector import errors as mysql_errors
from mysql.connector.connection import MySQLConnection

from core.boot_utils.conf_loader import get_secrets_dict


class ConnectionDetails(NamedTuple):
    "Store info about a database connection."
    cnx: MySQLConnection
    creation: int


class DatabaseConnectionManager:
    "Handles all database connections."

    def __init__(self):
        self.__database_keys = get_secrets_dict()["database"]
        self.__connections: dict[str, ConnectionDetails] = {}
        self.__log = logging.getLogger("bot.db")

    def test_connection(self):
        "Test the connection to the database."
        try:
            try:
                cnx = sql_connect(
                    user=self.__database_keys["user"],
                    password=self.__database_keys["password"],
                    host="127.0.0.1",
                    database="axobot",
                    connection_timeout=5
                )
            except (mysql_errors.InterfaceError, mysql_errors.ProgrammingError, mysql_errors.DatabaseError):
                self.__log.warning("Unable to access local dabatase - attempt via IP")
                cnx = sql_connect(
                    user=self.__database_keys["user"],
                    password=self.__database_keys["password"],
                    host=self.__database_keys["host"],
                    database="axobot",
                    connection_timeout=10
                )
                self.__log.info("Database connected remotely")
            else:
                self.__log.info("Database connected locally")
                self.__database_keys["host"] = "127.0.0.1"
            cnx.close()
        except Exception:
            self.__log.error("---- UNABLE TO REACH THE DATABASE ----", exc_info=True)
            return False
        return True

    def get_connection(self, database: str):
        """Get a connection to the database.
        If a connection is already open, return it. Else, create a new one."""
        if database not in self.__connections or not self.__connections[database].cnx.is_connected():
            return self.__create_connection(database)
        return self.__connections[database].cnx

    def disconnect_all(self):
        "Close all database connections."
        connection: ConnectionDetails | None
        for connection in self.__connections.values():
            if connection is not None:
                connection.cnx.close()
        self.__connections.clear()

    def __create_connection(self, database: str) -> MySQLConnection:
        "Create a new connection to the database."
        self.__log.info("Opening new connection to database '%s'", database)
        cnx = sql_connect(
            host=self.__database_keys["host"],
            user=self.__database_keys["user"],
            password=self.__database_keys["password"],
            database=database,
            buffered=True,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            connection_timeout=5
        )
        self.__connections[database] = ConnectionDetails(cnx, int(time.time()))
        return cnx
