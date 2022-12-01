from typing import Literal, TypedDict

class HttpTokenNotSet(Exception):
    pass

class TokenResponse(TypedDict):
    access_token: str
    expires_in: int
    token_type: Literal["bearer"]

class StreamObject(TypedDict):
    id: str
    user_id: str
    user_login: str
    user_name: str
    game_id: str
    game_name: str
    type: Literal["live"]
    title: str
    viewer_count: int
    started_at: str
    language: str
    thumbnail_url: str
    tag_ids: list[str]
    is_mature: bool

class StreamerObject(TypedDict):
    id: str
    login: str
    display_name: str
    type: Literal["staff", "admin", "global_mod", ""]
    broadcaster_type: Literal["partner", "affiliate", ""]
    description: str
    profile_image_url: str
    offline_image_url: str
    view_count: int
    created_at: str

PlatformId = Literal["twitch"]

class StreamersDBObject(TypedDict):
    id: int
    guild_id: int
    platform: PlatformId
    user_id: str
    user_name: str
    is_streaming: bool
    beta: bool

class GroupedStreamerDBObject(TypedDict):
    platform: PlatformId
    user_id: str
    user_name: str
    is_streaming: bool
    guild_ids: list[int]
