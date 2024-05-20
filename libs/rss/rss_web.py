from __future__ import annotations

import datetime as dt
import re
import time
from typing import TYPE_CHECKING, Literal

import aiohttp
import discord
from feedparser import CharacterEncodingOverride
from feedparser.util import FeedParserDict

from .convert_post_to_text import get_summary_from_entry, get_text_from_entry
from .rss_general import (FeedFilterConfig, FeedObject, RssMessage,
                          check_filter, feed_parse)

if TYPE_CHECKING:
    from libs.bot_classes import Axobot

class WebRSS:
    "Utilities class for any web-related RSS actions"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 120 # seconds
        self.url_pattern = r'^(?:https://)(?:www\.)?(\S+)$'

    def is_web_url(self, string: str):
        "Check if an url is a valid HTTPS web URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def _get_feed(self, url: str, filter_config: FeedFilterConfig | None=None,
                        session: aiohttp.ClientSession | None=None) -> FeedParserDict:
        "Get a list of feeds from a web URL"
        feed = await feed_parse(url, 9, session)
        if feed is None or not feed.entries:
            return None
        if 'bozo_exception' in feed and not isinstance(feed['bozo_exception'], CharacterEncodingOverride):
            # CharacterEncodingOverride exceptions are ignored
            return None
        date_field_key = await self._get_feed_date_key(feed.entries[0])
        if date_field_key is not None and len(feed.entries) > 1:
            # Remove entries that are older than the next one
            try:
                while (len(feed.entries) > 1) \
                    and (feed.entries[1][date_field_key] is not None) \
                        and (feed.entries[0][date_field_key] < feed.entries[1][date_field_key]):
                    del feed.entries[0]
            except KeyError:
                pass
        if filter_config is not None:
            # Remove entries that don't match the filter
            feed.entries = [entry for entry in feed.entries[:50] if await check_filter(entry, filter_config)]
            if not feed.entries:
                return None
        return feed

    async def _get_feed_date_key(self, entry: FeedParserDict
                                 ) -> Literal['published_parsed', 'published', 'updated_parsed'] | None:
        "Compute which key to use to get the date from a feed"
        for i in ['published_parsed', 'published', 'updated_parsed']:
            if entry.get(i) is not None:
                return i

    async def _get_entry_title(self, entry: FeedParserDict) -> str | None:
        "Try to find the article ID or title"
        for i in ['id', 'title', 'updated_parsed']:
            if value := entry.get(i):
                return value

    async def get_last_post(self, channel: discord.TextChannel, url: str,
                            filter_config: FeedFilterConfig | None,
                            session: aiohttp.ClientSession | None=None):
        "Get the last post from a web feed"
        feed = await self._get_feed(url, filter_config, session)
        if not feed:
            return await self.bot._(channel, "rss.web-invalid")
        entry = feed.entries[0]
        date_field_key = await self._get_feed_date_key(entry)
        if date_field_key is None:
            date = 'Unknown'
        else:
            date = entry[date_field_key]
        if 'link' in entry:
            link = entry['link']
        elif 'link' in feed:
            link = feed['link']
        else:
            link = url
        if 'author' in entry:
            author = entry['author']
        elif 'author' in feed:
            author = feed['author']
        elif 'title' in feed['feed']:
            author = feed['feed']['title']
        else:
            author = '?'
        if 'title' in entry:
            title = entry['title']
        elif 'title' in feed:
            title = feed['title']
        else:
            title = '?'
        post_text = await get_text_from_entry(entry)
        post_description = await get_summary_from_entry(entry)
        img = None
        img_match = re.search(r'(http(s?):)([/|.\w\s-])*\.(?:jpe?g|gif|png|webp)', str(entry))
        if img_match is not None:
            img = img_match.group(0)
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("web", channel.guild.id if channel.guild else None, channel.id, url),
            url=link,
            title=title,
            date=date,
            entry_id=await self._get_entry_title(entry),
            author=author,
            channel=feed.feed['title'] if 'title' in feed.feed else '?',
            image=img,
            post_text=post_text,
            post_description=post_description
        )

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
            entry_date = entry.get(date_field_key)
            # check if the entry is not too close to (or passed) the last post
            if entry_date is None or (
                    dt.datetime(*entry_date[:6]) - date).total_seconds() < self.min_time_between_posts:
                # we know we can break because entries are sorted by most recent first
                break
            entry_id = await self._get_entry_title(entry)
            if last_entry_id is not None:
                if entry_id == last_entry_id:
                    continue
            if 'link' in entry:
                link = entry['link']
            elif 'link' in feed:
                link = feed['link']
            else:
                link = url
            if 'author' in entry:
                author = entry['author']
            elif 'author' in feed:
                author = feed['author']
            elif 'title' in feed['feed']:
                author = feed['feed']['title']
            else:
                author = '?'
            if 'title' in entry:
                title = entry['title']
            elif 'title' in feed:
                title = feed['title']
            else:
                title = '?'
            post_text = await get_text_from_entry(entry)
            img = None
            img_match = re.search(r'(http(s?):)([/|.\w\s-])*\.(?:jpe?g|gif|png|webp)', str(entry))
            if img_match is not None:
                img = img_match.group(0)
            obj = RssMessage(
                bot=self.bot,
                feed=FeedObject.unrecorded("web", channel.guild.id if channel.guild else None, channel.id, url),
                url=link,
                title=title,
                date=entry_date,
                entry_id=entry_id,
                author=author,
                channel=feed.feed['title'] if 'title' in feed.feed else '?',
                image=img,
                post_text=post_text
            )
            posts_list.append(obj)
        posts_list.reverse()
        return posts_list
