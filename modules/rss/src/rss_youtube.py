from __future__ import annotations

import datetime as dt
import re
from operator import itemgetter
from typing import TYPE_CHECKING

import aiohttp
import discord
from asyncache import cached
from cachetools import TTLCache
from feedparser.util import FeedParserDict

from . import FeedObject, RssMessage, feed_parse, get_text_from_entry
from .rss_general import FeedFilterConfig, check_filter
from .youtube_search import Service

if TYPE_CHECKING:
    from core.bot_classes import Axobot


class YoutubeRSS:
    "Utilities class for any youtube-related RSS actions"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 120 # seconds
        self.search_service = Service(5, bot.secrets["google_api"])
        self.url_pattern = re.compile(
            r"(?:https?://)?(?:www\.|m\.)?(?:youtube\.com|youtu\.be)/(?:channel/|user/|c/)?@?([^/\s?]+).*$"
        )
        self.cookies = {
            "CONSENT": "YES+cb.20240421-07-p1.fr+FX+785"
        }

    def is_youtube_url(self, string: str):
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    @cached(TTLCache(maxsize=10_000, ttl=3600), key=itemgetter(2))
    async def _is_valid_channel_id(self, session: aiohttp.ClientSession, name: str):
        async with session.get("https://www.youtube.com/channel/"+name) as resp:
            return resp.status < 400

    @cached(TTLCache(maxsize=10_000, ttl=3600), key=itemgetter(2))
    async def _is_valid_channel_name(self, session: aiohttp.ClientSession, name: str):
        async with session.get("https://www.youtube.com/user/"+name) as resp:
            return resp.status < 400

    @cached(TTLCache(maxsize=10_000, ttl=3600), key=itemgetter(2))
    async def _is_valid_channel_custom_url(self, session: aiohttp.ClientSession, name: str):
        async with session.get("https://www.youtube.com/c/"+name) as resp:
            return resp.status < 400

    async def is_valid_channel(self, name: str):
        "Check if a channel identifier is actually valid"
        if name is None or not isinstance(name, str):
            return False
        async with aiohttp.ClientSession(cookies=self.cookies) as session:
            return await self._is_valid_channel_id(session, name) \
                or await self._is_valid_channel_name(session, name) \
                or await self._is_valid_channel_custom_url(session, name)

    @cached(TTLCache(maxsize=10_000, ttl=86400))
    async def get_channel_by_any_url(self, url: str):
        "Find a channel ID from any youtube URL"
        match = re.search(self.url_pattern, url)
        if match is None:
            return None
        return await self.get_channel_by_any_term(match.group(1))

    @cached(TTLCache(maxsize=10_000, ttl=86400))
    async def get_channel_by_any_term(self, name: str):
        "Find a channel ID from any youtube URL"
        _, channels, _ = self.search_service.search_term(
            name, "channel")
        if len(channels) == 0:
            # it may be an unreferenced channel ID
            async with aiohttp.ClientSession(cookies=self.cookies) as session:
                if self._is_valid_channel_id(session, name):
                    return name
            return None
        identifier, _ = channels[0].split(": ", 1)
        return identifier

    @cached(TTLCache(maxsize=10_000, ttl=86400 * 2)) # 2-days cache because we use it really really often
    def get_channel_by_custom_url(self, custom_name: str):
        return self.search_service.find_channel_by_custom_url(custom_name)

    @cached(TTLCache(maxsize=10_000, ttl=86400))
    def get_channel_by_user_name(self, username: str):
        return self.search_service.find_channel_by_user_name(username)

    @cached(TTLCache(maxsize=10_000, ttl=86400))
    def get_channel_name_by_id(self, channel_id: str):
        return self.search_service.query_channel_title(channel_id)

    async def _get_feed_list(self, channel_id: str, filter_config: FeedFilterConfig | None=None,
                             session: aiohttp.ClientSession | None=None) -> list[FeedParserDict]:
        "Get the feed list from a youtube channel"
        url = "https://www.youtube.com/feeds/videos.xml?channel_id="+channel_id
        feed = await feed_parse(url, 7, session)
        if feed is None or not feed.entries:
            return []
        if filter_config is not None:
            # Remove entries that don't match the filter
            return [entry for entry in feed.entries[:50] if await check_filter(entry, filter_config)]
        return feed.entries

    async def _parse_entry(self, entry: FeedParserDict, channel: discord.TextChannel):
        "Parse a feed entry to get the relevant information and return a RssMessage object"
        img_url = None
        if "media_thumbnail" in entry and len(entry["media_thumbnail"]) > 0:
            img_url = entry["media_thumbnail"][0]["url"]
        post_text = await get_text_from_entry(entry)
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("yt", channel.guild.id if channel.guild else None, channel.id),
            url=entry["link"],
            title=entry["title"],
            date=entry["published_parsed"],
            author=entry["author"],
            channel=entry["author"],
            image=img_url,
            post_text=post_text
        )

    async def get_last_post(self, channel: discord.TextChannel, yt_channel_id: str,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None):
        "Get the last post from a youtube channel"
        entries = await self._get_feed_list(yt_channel_id, filter_config, session)
        if len(entries) == 0:
            return await self.bot._(channel, "rss.nothing")
        entry = entries[0]
        return await self._parse_entry(entry, channel)

    async def get_new_posts(self, channel: discord.TextChannel, identifiant: str, date: dt.datetime,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None) -> list[RssMessage]:
        "Get new posts from a youtube channels"
        entries = await self._get_feed_list(identifiant, filter_config, session)
        if len(entries) == 0:
            return []
        posts_list: list[RssMessage] = []
        for entry in entries:
            if len(posts_list) > 10:
                break
            entry_date = entry.get("published_parsed")
            # check if the entry is not too close to (or passed) the last post
            if (dt.datetime(*entry_date[:6], tzinfo=dt.UTC) - date).total_seconds() <= self.min_time_between_posts:
                # we know we can break because entries are sorted by most recent first
                break
            obj = await self._parse_entry(entry, channel)
            posts_list.append(obj)
        posts_list.reverse()
        return posts_list
