from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Optional

import aiohttp
import discord
from feedparser.util import FeedParserDict

from .rss_general import FeedObject, RssMessage, feed_parse

if TYPE_CHECKING:
    from libs.bot_classes import Axobot

class DeviantartRSS:
    "Utilities class for any deviantart RSS action"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.min_time_between_posts = 120 # seconds
        self.url_pattern = r'^https://(?:www\.)?deviantart\.com/(\w+)'

    def is_deviantart_url(self, string: str):
        "Check if an url is a valid deviantart URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def get_username_by_url(self, url: str) -> Optional[str]:
        "Extract the DevianArt username from a URL"
        matches = re.match(self.url_pattern, url)
        if not matches:
            return None
        return matches.group(1)

    async def _get_feed(self, username: str, session: Optional[aiohttp.ClientSession]=None) -> FeedParserDict:
        "Get a list of feeds from a deviantart username"
        url = 'https://backend.deviantart.com/rss.xml?q=gallery%3A' + username
        feed = await feed_parse(self.bot, url, 9, session)
        if feed is None or 'bozo_exception' in feed or not feed.entries:
            return None
        return feed

    async def get_last_post(self, channel: discord.TextChannel, username: str, session: Optional[aiohttp.ClientSession]=  None):
        "Get the last post from a DeviantArt user"
        feed = await self._get_feed(username, session)
        if feed is None:
            return await self.bot._(channel.guild, "rss.nothing")
        entry = feed.entries[0]
        img_url = entry['media_content'][0]['url'] if "media_content" in entry else None
        title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feed.feed['title']).group(1)
        url = "https://www.deviantart.com/" + username
        return RssMessage(
            bot=self.bot,
            feed=FeedObject.unrecorded("deviant", channel.guild.id if channel.guild else None, link=url),
            url=entry['link'],
            title=entry['title'],
            date=entry['published_parsed'],
            author=title,
            image=img_url
        )

    async def get_new_posts(self, channel: discord.TextChannel, username: str, date: dt.datetime,
                            session: Optional[aiohttp.ClientSession]=None) -> list[RssMessage]:
        "Get all new posts from a DeviantArt user"
        feed = await self._get_feed(username, session)
        if feed is None:
            return []
        posts_list: list[RssMessage] = []
        url = "https://www.deviantart.com/" + username
        for entry in feed.entries:
            if dt.datetime(*entry['published_parsed'][:6]) <= date:
                break
            img_url = entry['media_content'][0]['url'] if "media_content" in entry else None
            title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feed.feed['title']).group(1)
            obj = RssMessage(
                bot=self.bot,
                feed=FeedObject.unrecorded("deviant", channel.guild.id if channel.guild else None, link=url),
                url=entry['link'],
                title=entry['title'],
                date=entry['published_parsed'],
                author=title,
                image=img_url
            )
            posts_list.append(obj)
        posts_list.reverse()
        return posts_list
