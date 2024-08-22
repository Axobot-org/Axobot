from datetime import datetime
from typing import TypedDict


class TrackedInvite(TypedDict):
    "Represents a tracked invite as stored in the database"
    guild_id: int
    invite_id: str
    name: str | None
    user_id: int | None
    creation_date: datetime
    tracking_date: datetime
    last_count: int
    last_tracking: datetime
    beta: bool
