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

class TopGGStatsResponse(TypedDict):
    "Response from the Top.gg API for bot stats."
    server_count: int
    shards: list[int]
    shard_count: int | None

class TopGGBotResponse(TypedDict):
    "Response from the Top.gg API for bot information."
    owners: list[int]
    tags: list[str]

class EmbedField(TypedDict):
    "A field in an embed."
    name: str
    value: str