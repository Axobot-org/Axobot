import json
from typing import Literal

from .dict_types import EventsTranslation, EventData, EventRewardRole, EventType

def get_events_translations() -> dict[Literal["fr", "en"], EventsTranslation]:
    """Get the translations for the events"""
    with open("events-translations.json", "r", encoding="utf-8") as file:
        return json.load(file)

__all__ = (
    "get_events_translations",
    "EventData",
    "EventRewardRole",
    "EventType",
)
