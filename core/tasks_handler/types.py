from datetime import datetime
from typing import Literal, TypedDict

from core.type_utils import AnyStrDict


class DbTask(TypedDict):
    "A task stored in the database"
    ID: int
    guild: int | None
    channel: int | None
    user: int
    action: Literal["mute", "ban", "timer", "role-grant"]
    begin: datetime
    duration: int
    message: str | None
    data: str | None
    beta: bool

class ReminderTask(TypedDict):
    "A task that is a reminder"
    ID: int
    guild: int | None
    channel: int | None
    user: int
    action: Literal["reminder"]
    begin: datetime
    duration: int
    message: str
    data: AnyStrDict
    beta: bool
