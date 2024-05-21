from typing import TypedDict


class DBTopicRow(TypedDict):
    id: int
    guild_id: int
    topic: str | None
    topic_emoji: str | None
    prompt: str | None
    role: int | None
    hint: str | None
    category: int | None
    name_format: str | None
    beta: bool
