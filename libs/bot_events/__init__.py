import json
import os
from typing import Literal

from .abstract_subcog import AbstractSubcog
from .dict_types import (EventData, EventItem, EventItemWithCount,
                         EventRewardRole, EventsTranslation, EventType)
from .random_collect_subcog import RandomCollectSubcog


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
    "EventItemWithCount",
    "AbstractSubcog",
    "RandomCollectSubcog"
)
