import json
import os
from typing import Literal

from .dict_types import (EventData, EventItem, EventRewardRole,
                         EventsTranslation, EventType)


def get_events_translations() -> dict[Literal["fr", "en"], EventsTranslation]:
    """Get the translations for the events"""
    with open(os.path.dirname(__file__)+"/events-translations.json", "r", encoding="utf-8") as file:
        return json.load(file)

__all__ = (
    "get_events_translations",
    "EventData",
    "EventItem",
    "EventRewardRole",
    "EventType",
)
