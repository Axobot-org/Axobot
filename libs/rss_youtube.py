import re

import aiohttp
from cachingutils import acached, cached

from libs.classes import Zbot
from libs.youtube_search import Service


class YoutubeRSS:
    "Utilities class for any youtube-related RSS actions"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.search_service = Service(5, bot.others['google_api'])
        self.url_pattern = re.compile(
            r'(?:https?://)?(?:www.)?(?:youtube.com|youtu.be)(?:(?:/channel/|/user/|/c/)(.+)|/[\w-]+$)')
        self.cookies = {
            "CONSENT": "YES+cb.20220907-07-p1.fr+FX+785"
        }

    def is_youtube_url(self, string: str):
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    @acached(timeout=3600, include_posargs=[2])
    async def _is_valid_channel_id(self, session: aiohttp.ClientSession, name: str):
        async with session.get("https://www.youtube.com/channel/"+name) as resp:
            return resp.status < 400

    @acached(timeout=3600, include_posargs=[2])
    async def _is_valid_channel_name(self, session: aiohttp.ClientSession, name: str):
        async with session.get("https://www.youtube.com/user/"+name) as resp:
            return resp.status < 400

    async def is_valid_channel(self, name: str):
        "Check if a channel identifier is actually valid"
        if name is None or not isinstance(name, str):
            return False
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            return await self._is_valid_channel_id(session, name) \
                or await self._is_valid_channel_name(session, name)

    @acached(timeout=86400)
    async def get_chanel_by_any_url(self, url: str):
        "Find a channel ID from any youtube URL"
        match = re.search(self.url_pattern, url)
        if match is None:
            return None
        _, channels, _ = self.search_service.search_term(
            match.group(1), "channel")
        if len(channels) == 0:
            # it may be an unreferenced channel ID
            async with aiohttp.ClientSession(cookies=self.cookies) as session:
                if self._is_valid_channel_id(session, match.group(1)):
                    return match.group(1)
            return None
        identifier, name = channels[0].split(": ")
        if name.lower() == match.group(1).lower() \
            or identifier.lower() == match.group(1).lower():
            return identifier
        return None

    @cached(timeout=86400*2) # 2-days cache because we use it really really often
    def get_channel_by_custom_url(self, custom_name: str):
        return self.search_service.find_channel_by_custom_url(custom_name)

    @cached(timeout=86400)
    def get_channel_by_user_name(self, username: str):
        return self.search_service.find_channel_by_user_name(username)
