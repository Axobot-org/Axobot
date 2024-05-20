from datetime import datetime
from typing import Literal, TypedDict


class DbTask(TypedDict):
    "A task stored in the database"
    ID: int
    guild: int | None
    channel: int | None
    user: int
    action: Literal["mute", "ban", "timer"]
    begin: datetime
    duration: int
    message: str | None
    data: str | None
    beta: bool
