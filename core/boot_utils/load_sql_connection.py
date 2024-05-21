from typing import TYPE_CHECKING

import mysql
from mysql.connector import errors as mysql_errors

if TYPE_CHECKING:
    from core.bot_classes import Axobot


def load_sql_connection(bot: "Axobot"):
    "Load the connection to the database, preferably in local mode"
    try:
        try:
            cnx = mysql.connector.connect(
                user=bot.database_keys['user'],
                password=bot.database_keys['password'],
                host="127.0.0.1",
                database=bot.database_keys['name_main'],
                connection_timeout=5
            )
        except (mysql_errors.InterfaceError, mysql_errors.ProgrammingError, mysql_errors.DatabaseError):
            bot.log.warning("Unable to access local dabatase - attempt via IP")
            cnx = mysql.connector.connect(
                user=bot.database_keys['user'],
                password=bot.database_keys['password'],
                host=bot.database_keys['host'],
                database=bot.database_keys['name_main'],
                connection_timeout=10
            )
            bot.log.info("Database connected remotely")
        else:
            bot.log.info("Database connected locally")
            bot.database_keys['host'] = '127.0.0.1'
        cnx.close()
    except Exception:
        bot.log.error("---- UNABLE TO REACH THE DATABASE ----", exc_info=True)
        bot.database_online = False
