from typing import Literal, TypedDict

RgbColor = tuple[int, int, int]
RgbaColor = tuple[int, int, int, int]


class TextMetaData(TypedDict):
    "Contains info about text position and size for a given card style"
    position: tuple[tuple[int, int], tuple[int, int]] # (x1, y1), (x2, y2)
    font_size: int
    alignment: Literal["left", "center", "right"]
    font: str

class CardMetaData(TypedDict):
    "Metadata about the card"
    avatar_size: int
    avatar_position: tuple[int, int]
    texts: TextMetaData
    xp_bar_position: tuple[tuple[int, int], tuple[int, int]] # (x1, y1), (x2, y2)

class ColorsData(TypedDict):
    "Contains info about colors to apply to a card style"
    xp_bar: RgbColor
    texts: dict[str, RgbColor]

class TextData(TextMetaData):
    "Contains info about a text ready to be rendered"
    color: RgbColor

class CardData(TypedDict):
    "Regroup every needed info to generate a card"
    type: str
    avatar_size: tuple[int, int]
    avatar_position: tuple[int, int]
    xp_bar_color: RgbColor
    xp_bar_position: tuple[tuple[int, int], tuple[int, int]] # (x1, y1), (x2, y2)
    card_version: Literal[1, 2]
    xp_percent: float
    texts: dict[str, TextData]
