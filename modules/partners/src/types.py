from datetime import datetime
from typing import Literal, TypedDict

PartnerType = Literal["bot"] | Literal["guild"]

class DbPartner(TypedDict):
    """A partner in the database."""
    ID: int
    added_at: datetime
    guild: int
    messageID: int
    target: str
    type: PartnerType
    description: str

class TopGGBotResponse(TypedDict):
    "Response from the Top.gg API for bot information."
    id: str
    name: str
    owners: list[str]
    tags: list[str]
    server_count: int

class EmbedField(TypedDict):
    "A field in an embed."
    name: str
    value: str
