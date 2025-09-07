from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING

import aiohttp
import discord
from feedparser.util import FeedParserDict

from .general import (FeedFilterConfig, FeedObject, RssMessage,
                          check_filter, feed_parse)

if TYPE_CHECKING:
    from core.bot_classes import Axobot

class DeviantartRSS:
    "Utilities class for any deviantart RSS action"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 120 # seconds
        self.url_pattern = r"^https://(?:www\.)?deviantart\.com/(\w+)"

    def is_deviantart_url(self, string: str):
        "Check if an url is a valid deviantart URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def get_username_by_url(self, url: str) -> str | None:
        "Extract the DevianArt username from a URL"
        matches = re.match(self.url_pattern, url)
        if not matches:
            return None
        return matches.group(1)

    async def _get_feed(self, username: str, filter_config: FeedFilterConfig | None=None,
                        session: aiohttp.ClientSession | None=None) -> FeedParserDict | None:
        "Get a list of feeds from a deviantart username"
        url = "https://backend.deviantart.com/rss.xml?q=gallery%3A" + username
        feed = await feed_parse(url, 9, session)
        if feed is None or "bozo_exception" in feed or not feed.entries:
            return None
        if filter_config is not None:
            feed['entries'] = [entry for entry in feed.entries[:50] if await check_filter(entry, filter_config)]
        return feed

    async def _parse_entry(self, entry: FeedParserDict, feed: FeedParserDict, url: str, channel:"discord.abc.MessageableChannel"):
        "Parse a feed entry to get the relevant information and return a RssMessage object"
        img_url = entry["media_content"][0]["url"] if "media_content" in entry else None
        if (title_match := re.search(r"DeviantArt: ([^ ]+)'s gallery", feed.feed["title"])) is None:
            raise ValueError("Title not found in feed title, cannot create RssMessage")
        title = title_match.group(1).strip()
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("deviant", channel.guild.id if channel.guild else None, link=url),
            url=entry["link"],
            title=entry["title"],
            date=entry["published_parsed"],
            author=title,
            image=img_url
        )

    async def get_last_post(self, channel:"discord.abc.MessageableChannel", username: str,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None =  None):
        "Get the last post from a DeviantArt user"
        feed = await self._get_feed(username, filter_config, session)
        if feed is None:
            return await self.bot._(channel.guild, "rss.nothing")
        entry = feed.entries[0]
        url = "https://www.deviantart.com/" + username
        return await self._parse_entry(entry, feed, url, channel)

    async def get_new_posts(self, channel:"discord.abc.MessageableChannel", username: str, date: dt.datetime,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None) -> list[RssMessage]:
        "Get all new posts from a DeviantArt user"
        feed = await self._get_feed(username, filter_config, session)
        if feed is None:
            return []
        posts_list: list[RssMessage] = []
        url = "https://www.deviantart.com/" + username
        for entry in feed.entries:
            if (dt.datetime(*entry["published_parsed"][:6], tzinfo=dt.UTC) - date).total_seconds() <= self.min_time_between_posts:
                break
            obj = await self._parse_entry(entry, feed, url, channel)
            posts_list.append(obj)
        posts_list.reverse()
        return posts_list
