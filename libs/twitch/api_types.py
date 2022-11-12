from typing import Literal, TypedDict, Any

class HttpTokenNotSet(Exception):
    pass

class TokenResponse(TypedDict):
    access_token: str
    expires_in: int
    token_type: Literal["bearer"]