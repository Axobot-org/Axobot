from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING

import aiohttp
import discord
from feedparser.util import FeedParserDict

from .convert_post_to_text import get_text_from_entry
from .rss_general import (FeedFilterConfig, FeedObject, RssMessage,
                          check_filter, feed_parse)

if TYPE_CHECKING:
    from core.bot_classes import Axobot

class BlueskyRSS:
    "Utilities class for any Bluesky RSS action"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 60 # seconds
        self.url_pattern = r"^https://(?:www\.)?bsky.app/profile/([\w._:-]+)$"

    def is_bluesky_url(self, string: str):
        "Check if an url is a valid Bluesky URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def get_username_by_url(self, url: str) -> str | None:
        "Extract the Bluesky username from a URL"
        matches = re.match(self.url_pattern, url)
        if not matches:
            return None
        return matches.group(1)

    async def _get_feed(self, username: str, filter_config: FeedFilterConfig | None=None,
                        session: aiohttp.ClientSession | None=None) -> FeedParserDict:
        "Get a list of feeds from a Bluesky username"
        url = f"https://bsky.app/profile/{username}/rss"
        feed = await feed_parse(url, 9, session)
        if feed is None or "bozo_exception" in feed or not feed.entries:
            return None
        if filter_config is not None:
            feed.entries = [entry for entry in feed.entries[:50] if await check_filter(entry, filter_config)]
        return feed

    async def _parse_entry(self, entry: FeedParserDict, feed: FeedParserDict, url: str, channel: discord.TextChannel):
        "Parse a feed entry to get the relevant information and return a RssMessage object"
        full_author = feed["feed"]["title"]
        author = re.search(r"^@[\w.-_]+ - (\S+)$", full_author).group(1)
        post_text = await get_text_from_entry(entry)
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("bluesky", channel.guild.id if channel.guild else None, link=url),
            url=entry["link"],
            date=entry["published_parsed"],
            entry_id=entry["id"],
            title=post_text,
            author=author,
            channel=full_author,
            post_text=post_text
       )

    async def get_last_post(self, channel: discord.TextChannel, username: str,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None) -> RssMessage | str:
        "Get the last post from a Bluesky user"
        feed = await self._get_feed(username, filter_config, session)
        if feed is None or not feed.entries:
            return await self.bot._(channel.guild, "rss.nothing")
        entry = feed.entries[0]
        url = f"https://bsky.app/profile/{username}/rss"
        return await self._parse_entry(entry, feed, url, channel)

    async def get_new_posts(self, channel: discord.TextChannel, username: str, date: dt.datetime,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None) -> list[RssMessage]:
        "Get all new posts from a Bluesky user"
        feed = await self._get_feed(username, filter_config, session)
        if feed is None or not feed.entries:
            return []
        posts_list: list[RssMessage] = []
        url = f"https://bsky.app/profile/{username}/rss"
        for entry in feed.entries:
            # don't return more than 10 posts
            if len(posts_list) > 10:
                break
            # don't return posts older than the date
            if (dt.datetime(*entry["published_parsed"][:6], tzinfo=dt.UTC) - date).total_seconds() < self.min_time_between_posts:
                break
            posts_list.append(await self._parse_entry(entry, feed, url, channel))
        posts_list.reverse()
        return posts_list
