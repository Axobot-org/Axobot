from datetime import datetime
from typing import Literal, Optional, TypedDict


class DbTask(TypedDict):
    "A task stored in the database"
    ID: int
    guild: Optional[int]
    channel: Optional[int]
    user: int
    action: Literal["mute", "ban", "timer"]
    begin: datetime
    duration: int
    message: Optional[str]
    data: Optional[str]
    beta: bool
