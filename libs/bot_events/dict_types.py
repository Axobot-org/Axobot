import datetime
from typing import Literal, TypedDict

EventType = Literal["blurple", "halloween", "fish", "christmas"]

class EventsTranslation(TypedDict):
    "Represents the translations for the bot events in one language"
    events_desc: dict[str, str]
    events_prices: dict[str, dict[str, str]]
    events_title: dict[str, str]

class EventEmojis(TypedDict):
    "Represents data about available reactions during an event"
    reactions_list: list[str]
    triggers: list[str]
    probability: float

class EventRewardCard(TypedDict):
    "Represents the rank card reward for an event"
    points: int
    reward_type: Literal["rankcard"]
    rank_card: str
    min_date: str | None

class EventRewardRole(TypedDict):
    "Represents the special role reward for an event"
    points: int
    reward_type: Literal["role"]
    role_id: int
    min_date: str | None

class EventRewardCustom(TypedDict):
    "Represents a custom reward for an event"
    points: int
    reward_type: Literal["custom"]

class EventData(TypedDict):
    "Represents data about a specific bot event"
    begin: datetime.datetime
    end: datetime.datetime
    type: EventType
    icon: str | None
    color: int
    objectives: list[EventRewardCard | EventRewardCustom | EventRewardRole]
    emojis: EventEmojis | None

class EventItem(TypedDict):
    "Represents an item that can be obtained during an event"
    item_id: int
    emoji: str
    english_name: str
    french_name: str
    points: int
    event_type: EventType
    frequency: float

class EventItemWithCount(TypedDict):
    "Represents an item type collected by a user, with how many they have"
    count: int
    item_id: int
    emoji: str
    english_name: str
    french_name: str
    points: int
    event_type: EventType
    frequency: float
