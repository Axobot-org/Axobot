from __future__ import annotations

import datetime as dt
import re
import time
from typing import TYPE_CHECKING, Any, Literal

import aiohttp
import discord
from cachetools import TTLCache
from feedparser import CharacterEncodingOverride
from feedparser.util import FeedParserDict

from .convert_post_to_text import get_summary_from_entry, get_text_from_entry
from .rss_general import (FeedFilterConfig, FeedObject, RssMessage,
                          check_filter, feed_parse)

if TYPE_CHECKING:
    from core.bot_classes import Axobot

class WebRSS:
    "Utilities class for any web-related RSS actions"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 120 # seconds
        self.url_pattern = r"^(?:https://)(?:www\.)?(\S+)$"
        self._cache = TTLCache[str, FeedParserDict](maxsize=1_000, ttl=60 * 5)

    def is_web_url(self, string: str):
        "Check if an url is a valid HTTPS web URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def _get_feed(self, url: str, filter_config: FeedFilterConfig | None=None,
                        session: aiohttp.ClientSession | None=None) -> FeedParserDict:
        "Get a list of feeds from a web URL"
        if (feed := self._cache.get(url)) is None:
            feed = await feed_parse(url, 9, session)
            if feed is not None:
                self._cache[url] = feed
        if feed is None or not feed.entries:
            return None
        if "bozo_exception" in feed and not isinstance(feed["bozo_exception"], CharacterEncodingOverride):
            # CharacterEncodingOverride exceptions are ignored
            return None
        if len(feed.entries) > 1:
            # Remove entries that are older than the next one
            try:
                entry_date = await self._get_entry_datetime(feed.entries[0])
                while entry_date is not None \
                    and (len(feed.entries) > 1) \
                    and (next_entry_date := await self._get_entry_datetime(feed.entries[1])) \
                    and (entry_date < next_entry_date):
                    del feed.entries[0]
                    entry_date = next_entry_date
            except KeyError:
                pass
        if filter_config is not None:
            # Remove entries that don't match the filter
            feed.entries = [entry for entry in feed.entries[:50] if await check_filter(entry, filter_config)]
            if not feed.entries:
                return None
        return feed

    async def _get_feed_date_key(self, entry: FeedParserDict
                                 ) -> Literal["published_parsed", "published", "updated_parsed"] | None:
        "Compute which key to use to get the date from a feed"
        for i in ["published_parsed", "published", "updated_parsed"]:
            if entry.get(i) is not None:
                return i

    async def _get_entry_datetime(self, entry: FeedParserDict) -> dt.datetime | None:
        "Try to find the entry publication date and return it as a datetime object"
        entry_date = entry.get(await self._get_feed_date_key(entry))
        if isinstance(entry_date, time.struct_time):
            if entry_date.tm_zone is None:
                timezone = dt.UTC
            else:
                timezone = dt.timezone(dt.timedelta(seconds=entry_date.tm_gmtoff))
            return dt.datetime(*entry_date[:6], tzinfo=timezone)
        if isinstance(entry_date, dt.datetime):
            if entry_date.tzinfo is None:
                return entry_date.replace(tzinfo=dt.UTC)
            return entry_date
        self.bot.dispatch("error", f"Invalid date type for entry {entry.get('title', 'Unknown')}: {type(entry_date)}")
        return None

    async def _get_entry_id(self, entry: FeedParserDict) -> str | None:
        "Try to find the article ID or title"
        for i in ["id", "title", "updated_parsed"]:
            if value := entry.get(i):
                return value

    async def _parse_entry(self, entry: FeedParserDict, feed: FeedParserDict, url: str, date: Any, channel: discord.TextChannel):
        "Parse a feed entry to get the relevant information and return a RssMessage object"
        if "link" in entry:
            link = entry["link"]
        elif "link" in feed:
            link = feed["link"]
        else:
            link = url
        if "author" in entry:
            author = entry["author"]
        elif "author" in feed:
            author = feed["author"]
        elif "title" in feed["feed"]:
            author = feed["feed"]["title"]
        else:
            author = '?'
        if "title" in entry:
            title = entry["title"]
        elif "title" in feed:
            title = feed["title"]
        else:
            title = '?'
        post_text = await get_text_from_entry({"link": link} | entry)
        post_description = await get_summary_from_entry({"link": link} | entry)
        img: str | None = None
        if "media_thumbnail" in entry and len(entry["media_thumbnail"]) > 0 and "url" in entry["media_thumbnail"][0]:
            img = entry["media_thumbnail"][0]["url"]
        elif img_match := re.search(r"(http(s?):)([/|.\w\s-])*\.(?:jpe?g|gif|png|webp)", str(entry)):
            img = img_match.group(0)
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("web", channel.guild.id if channel.guild else None, channel.id, url),
            url=link,
            title=title,
            date=date,
            entry_id=await self._get_entry_id(entry),
            author=author,
            channel=feed.feed["title"] if "title" in feed.feed else '?',
            image=img,
            post_text=post_text,
            post_description=post_description
        )

    async def get_last_post(self, channel: discord.TextChannel, url: str,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None):
        "Get the last post from a web feed"
        feed = await self._get_feed(url, filter_config, session)
        if not feed:
            return await self.bot._(channel, "rss.web-invalid")
        entry = feed.entries[0]
        entry_date = await self._get_entry_datetime(entry) or "Unknown"
        return await self._parse_entry(entry, feed, url, entry_date, channel)

    async def get_new_posts(self, channel: discord.TextChannel, url: str, date: dt.datetime,
                            filter_config: FeedFilterConfig | None,
                            last_entry_id: str | None=None,
                            session: aiohttp.ClientSession | None=None) -> list[RssMessage]:
        "Get new posts from a web feed"
        feed = await self._get_feed(url, filter_config, session)
        if not feed or not feed.entries:
            return []
        posts_list: list[RssMessage] = []
        date_field_key = await self._get_feed_date_key(feed.entries[0])
        if date_field_key is None or date_field_key == "published":
            last_entry = await self.get_last_post(channel, url, filter_config, session)
            if isinstance(last_entry, RssMessage):
                return [last_entry]
            return []
        for entry in feed.entries:
            if len(posts_list) > 10:
                break
            entry_date = await self._get_entry_datetime(entry)
            # check if the entry is not too close to (or passed) the last post
            if entry_date is None or (entry_date - date).total_seconds() < self.min_time_between_posts:
                # we know we can break because entries are sorted by most recent first
                break
            entry_id = await self._get_entry_id(entry)
            if last_entry_id is not None:
                if entry_id == last_entry_id:
                    continue
            obj = await self._parse_entry(entry, feed, url, entry_date, channel)
            posts_list.append(obj)
        posts_list.reverse()
        return posts_list
