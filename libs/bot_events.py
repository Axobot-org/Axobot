import datetime
from typing import Literal, Optional, TypedDict

EventType = Literal["blurple", "halloween", "fish"]

class EventEmojis(TypedDict):
    "Represents data about available reactions during an event"
    reactions_list: list[str]
    triggers: list[str]
    probability: float

class EventData(TypedDict):
    "Represents data about a specific bot event"
    begin: datetime.datetime
    end: datetime.datetime
    type: EventType
    icon: Optional[str]
    color: int
    objectives: list[str]
    emojis: Optional[EventEmojis]
