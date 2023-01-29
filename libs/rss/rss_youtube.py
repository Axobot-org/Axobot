from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Union

import aiohttp
import discord
from cachingutils import acached, cached

from libs.youtube_search import Service

from .rss_general import FeedObject, RssMessage, feed_parse

if TYPE_CHECKING:
    from libs.bot_classes import Zbot


class YoutubeRSS:
    "Utilities class for any youtube-related RSS actions"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.min_time_between_posts = 120
        self.search_service = Service(5, bot.others['google_api'])
        self.url_pattern = re.compile(
            r'(?:https?://)?(?:www.)?(?:youtube.com|youtu.be)/(?:channel/|user/|c/)?@?([^/\s?]+).*?$'
        )
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
    async def get_channel_by_any_url(self, url: str):
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
        identifier, name = channels[0].split(": ", 1)
        return identifier

    @cached(timeout=86400*2) # 2-days cache because we use it really really often
    def get_channel_by_custom_url(self, custom_name: str):
        return self.search_service.find_channel_by_custom_url(custom_name)

    @cached(timeout=86400)
    def get_channel_by_user_name(self, username: str):
        return self.search_service.find_channel_by_user_name(username)

    @cached(timeout=86400)
    def get_channel_name_by_id(self, channel_id: str):
        return self.search_service.query_channel_title(channel_id)

    async def get_feed(self, channel: discord.TextChannel, identifiant: str, date: dt.datetime=None, session: aiohttp.ClientSession=None) -> Union[str, list[RssMessage]]:
        if identifiant == 'help':
            return await self.bot._(channel, "rss.yt-help")
        url = 'https://www.youtube.com/feeds/videos.xml?channel_id='+identifiant
        feeds = await feed_parse(self.bot, url, 7, session)
        if feeds is None:
            return await self.bot._(channel, "rss.research-timeout")
        if not feeds.entries:
            url = 'https://www.youtube.com/feeds/videos.xml?user='+identifiant
            feeds = await feed_parse(self.bot, url, 7, session)
            if feeds is None:
                return await self.bot._(channel, "rss.nothing")
            if not feeds.entries:
                return await self.bot._(channel, "rss.nothing")
        if not date:
            feed = feeds.entries[0]
            img_url = None
            if 'media_thumbnail' in feed.keys() and len(feed['media_thumbnail']) > 0:
                img_url = feed['media_thumbnail'][0]['url']
            obj = RssMessage(
                bot=self.bot,
                feed=FeedObject.unrecorded("yt", channel.guild.id if channel.guild else None, channel.id),
                url=feed['link'],
                title=feed['title'],
                date=feed['published_parsed'],
                author=feed['author'],
                channel=feed['author'],
                image=img_url
            )
            return [obj]
        else:
            liste = []
            for feed in feeds.entries:
                if len(liste) > 10:
                    break
                if 'published_parsed' not in feed or (dt.datetime(*feed['published_parsed'][:6]) - date).total_seconds() <= self.min_time_between_posts:
                    break
                img_url = None
                if 'media_thumbnail' in feed.keys() and len(feed['media_thumbnail']) > 0:
                    img_url = feed['media_thumbnail'][0]['url']
                obj = RssMessage(
                    bot=self.bot,
                    feed=FeedObject.unrecorded("yt", channel.guild.id if channel.guild else None, channel.id),
                    url=feed['link'],
                    title=feed['title'],
                    date=feed['published_parsed'],
                    author=feed['author'],
                    channel=feed['author'],
                    image=img_url
                )
                liste.append(obj)
            liste.reverse()
            return liste
