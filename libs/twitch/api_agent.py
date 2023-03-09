from datetime import datetime, timedelta, timezone
from typing import Optional

import aiohttp
from cachingutils import acached

from libs.twitch.types import (HttpTokenNotSet, StreamerObject, StreamObject,
                               TokenResponse)


class TwitchApiAgent:
    "Handle the HTTP API usage for you"

    def __init__(self):
        self.client_id: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self._token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def is_token_valid(self):
        "Check if the HTTPS API token is set and still valid"
        if self._token is None or self.token_expires_at is None:
            return False
        return self.token_expires_at > datetime.now(timezone.utc)

    @property
    def is_connected(self):
        "Check if the HTTP session is still open"
        return self._session is not None and not self._session.closed

    @acached(timeout=3600) # 1h
    async def api_login(self, client_id: str, client_secret: str):
        "Request a token for the Twitch API"
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": client_id,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }
        self._session = self._session = aiohttp.ClientSession()
        async with self._session.post(url, params=params) as resp:
            data: TokenResponse = await resp.json()
            self._token = data["access_token"]
            now = datetime.now(timezone.utc)
            self.token_expires_at = now + timedelta(seconds=data["expires_in"])
            self.client_id = client_id

    async def close_session(self):
        "Close the HTTP session"
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _get_headers(self):
        "Get the authentication headers for the API"
        if not self.is_token_valid:
            raise HttpTokenNotSet()
        return {
            "Client-ID": self.client_id,
            "Authorization": f"Bearer {self._token}"
        }

    @acached(timeout=1 * 60 * 60) # 1h
    async def get_user_by_name(self, username: str) -> Optional[StreamerObject]:
        "Get the ID of a user from their username"
        if not self.is_token_valid:
            raise HttpTokenNotSet()
        if not self._session:
            self._session = aiohttp.ClientSession()
        url = "https://api.twitch.tv/helix/users"
        params = {"login": username}
        async with self._session.get(url, params=params, headers=await self._get_headers()) as resp:
            data = await resp.json()
            if not "data" in data:
                raise ValueError(data["message"])
            try:
                return data["data"][0]
            except IndexError:
                return None

    @acached(timeout=6 * 60 * 60) # 6h
    async def get_user_by_id(self, user_id: str) -> Optional[StreamerObject]:
        "Get the user object from their ID"
        if not self.is_token_valid:
            raise HttpTokenNotSet()
        if not self._session:
            self._session = aiohttp.ClientSession()
        url = "https://api.twitch.tv/helix/users"
        params = {"id": user_id}
        async with self._session.get(url, headers=await self._get_headers(), params=params) as resp:
            data = await resp.json()
            try:
                return data["data"][0]
            except IndexError:
                return None

    @acached(timeout=2 * 60) # 2min
    async def get_user_stream_by_id(self, *user_ids: str) -> list[StreamObject]:
        "Get the stream of users specified by their IDs"
        if not self.is_token_valid:
            raise HttpTokenNotSet()
        if not self._session:
            self._session = aiohttp.ClientSession()
        url = "https://api.twitch.tv/helix/streams"
        params = {"user_id": user_ids}
        async with self._session.get(url, headers=await self._get_headers(), params=params) as resp:
            return (await resp.json())["data"]
