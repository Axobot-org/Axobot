import json
import os

from libs.xp_cards.card_types import CardData, CardMetaData, TextData, TextMetaData, ColorsData

V1_CARDS = {
    "admin",
    "april22",
    "blue",
    "blurple19",
    "blurple20",
    "blurple21",
    "blurple22",
    "christmas19",
    "christmas20",
    "christmas22",
    "contributor",
    "dark",
    "green",
    "grey",
    "halloween20",
    "halloween21",
    "halloween22",
    "orange",
    "partner",
    "premium",
    "purple",
    "rainbow",
    "red",
    "support",
    "turquoise",
    "yellow",
}

V2_CARDS = {
}

JSON_DATA_FILE = os.path.dirname(__file__) + "/cards_data.json"


def get_card_meta(card_name: str) -> CardMetaData:
    """Return the metadata for the card"""
    if card_name in V1_CARDS:
        version = "v1"
    elif card_name in V2_CARDS:
        version = "v2"
    else:
        raise ValueError(f"Unknown card type: {card_name}")
    with open(JSON_DATA_FILE, "r", encoding="utf8") as file:
        cards_data = json.load(file)
    return cards_data["meta"][version]

def get_card_colors(card_name: str) -> ColorsData:
    "Return the colors for the card"
    with open(JSON_DATA_FILE, "r", encoding="utf8") as file:
        cards_data = json.load(file)
    colors = cards_data["colors"]
    if card_name in colors:
        return colors[card_name]
    return colors["default"]


def get_card_data(
        card_name: str,
        translation_map: dict[str, str],
        username: str,
        level: int,
        rank: int,
        participants: int,
        current_xp: int,
        xp_to_next_level: int,
        total_xp: int
) -> CardData:
    "Return every required info to generate the card"
    meta = get_card_meta(card_name)
    colors = get_card_colors(card_name)
    text_values = get_card_texts(translation_map,
                                 username, level,
                                 rank, participants,
                                 current_xp, xp_to_next_level,
                                 total_xp)
    texts: dict[str, TextData] = {}
    for text_key, text_meta in meta["texts"].items():  # type: ignore
        text_meta: TextMetaData
        label = text_values[text_key]
        texts[label] = {
            **text_meta,
            "color": tuple(colors["texts"][text_key])
        }
    return {
        "type": card_name,
        "avatar_size": (meta["avatar_size"], meta["avatar_size"]),
        "avatar_position": meta["avatar_position"],
        "xp_bar_color": tuple(colors["xp_bar"]),
        "xp_bar_position": meta["xp_bar_position"],
        "card_version": 1 if card_name in V1_CARDS else 2,
        "xp_percent": current_xp / xp_to_next_level,
        "texts": texts
    }


def get_card_texts(
        translation_map: dict[str, str],
        username: str,
        level: int,
        rank: int,
        participants: int,
        current_xp: int,
        xp_to_next_level: int,
        total_xp: int
):
    "Return the texts to be added to the card"
    return {
        "username": username,
        "level_label": translation_map.get("LEVEL", "Level"),
        "level": str(level),
        "rank_label": translation_map.get("RANK", "RANK"),
        "rank": f"{rank}/{participants}",
        "current_xp": f"{current_xp}/{xp_to_next_level}",
        "total_xp": f"{total_xp}/{total_xp + xp_to_next_level - current_xp}",
        "xp": f"{current_xp}/{xp_to_next_level} ({total_xp}/{total_xp + xp_to_next_level - current_xp})"
    }
