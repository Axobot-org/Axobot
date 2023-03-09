from typing import Optional, TypedDict


class DBTopicRow(TypedDict):
    id: int
    guild_id: int
    topic: Optional[str]
    topic_emoji: Optional[str]
    prompt: Optional[str]
    role: Optional[int]
    hint: Optional[str]
    category: Optional[int]
    name_format: Optional[str]
    beta: bool
