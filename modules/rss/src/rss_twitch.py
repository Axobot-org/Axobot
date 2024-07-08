from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING

import aiohttp
import discord
from feedparser.util import FeedParserDict

from .rss_general import (FeedFilterConfig, FeedObject, RssMessage,
                          check_filter, feed_parse)

if TYPE_CHECKING:
    from core.bot_classes import Axobot

class TwitchRSS:
    "Utilities class for any Twitch clip RSS action"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 120 # seconds
        self.url_pattern = r"^https://(?:www\.)?twitch\.tv/(\w+)"

    def is_twitch_url(self, string: str):
        "Check if an url is a valid twitch URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def get_username_by_url(self, url: str) -> str | None:
        "Extract the Twitch username from a URL"
        matches = re.match(self.url_pattern, url)
        if not matches:
            return None
        return matches.group(1)

    async def _get_feed(self, username: str, filter_config: FeedFilterConfig | None=None,
                        session: aiohttp.ClientSession | None=None) -> FeedParserDict:
        "Get a list of feeds from a twitch username"
        url = "https://twitchrss.appspot.com/vod/" + username
        feed = await feed_parse(url, 5, session)
        if feed is None or "bozo_exception" in feed or not feed.entries:
            return None
        if filter_config is not None:
            feed.entries = [entry for entry in feed.entries[:50] if await check_filter(entry, filter_config)]
        return feed

    async def _parse_entry(self, entry: FeedParserDict, feed: FeedParserDict, username: str, channel: discord.TextChannel):
        "Parse a feed entry to get the relevant information and return a RssMessage object"
        url = "https://www.twitch.tv/" + username
        img_url = None
        if img_match := re.search(r'<img src="([^"]+)" />', entry["summary"]):
            img_url = img_match.group(1)
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("twitch", channel.guild.id if channel.guild else None, channel.id, url),
            url=entry["link"],
            title=entry["title"],
            date=entry["published_parsed"],
            author=feed.feed["title"].replace("'s Twitch video RSS", ""),
            image=img_url,
            channel=username
        )

    async def get_last_post(self, channel: discord.TextChannel, username: str,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None= None):
        "Get the last video of a Twitch user"
        feed = await self._get_feed(username, filter_config, session)
        if feed is None:
            return await self.bot._(channel.guild, "rss.nothing")
        entry = feed.entries[0]
        return await self._parse_entry(entry, feed, username, channel)

    async def get_new_posts(self, channel: discord.TextChannel, username: str, date: dt.datetime,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None) -> list[RssMessage]:
        "Get all new videos from a Twitch user"
        feed = await self._get_feed(username, filter_config, session)
        if feed is None:
            return []
        posts_list: list[RssMessage] = []
        for entry in feed.entries:
            if len(posts_list) > 10:
                break
            if dt.datetime(*entry["published_parsed"][:6], tzinfo=dt.UTC) <= date:
                break
            obj = await self._parse_entry(entry, feed, username, channel)
            posts_list.append(obj)
        posts_list.reverse()
        return posts_list
