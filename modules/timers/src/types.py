from datetime import datetime
from typing import Literal, TypedDict


class ReminderData(TypedDict):
    "Data structure for a reminder"
    ID: int
    guild: int | None
    channel: int
    user: int
    action: Literal["timer"]
    begin: datetime
    duration: int
    message: str
    data: str | None

class TransformReminderData(TypedDict):
    "Data structure passed to transform_reminders_options"
    id: int
    message: str
    tr_channel: str
    tr_duration: str
