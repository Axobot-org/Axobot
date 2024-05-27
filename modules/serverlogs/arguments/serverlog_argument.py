from typing import TYPE_CHECKING

from core.arguments.errors import InvalidServerLogError

if TYPE_CHECKING:
    from core.bot_classes import MyContext


class ServerLog(str):
    "Convert arguments to a server log type"
    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str) -> str:
        "Do the conversion"
        from modules.serverlogs.serverlogs import \
            ServerLogs  # pylint: disable=import-outside-toplevel

        if argument in ServerLogs.available_logs() or argument == 'all':
            return argument
        raise InvalidServerLogError(argument)
