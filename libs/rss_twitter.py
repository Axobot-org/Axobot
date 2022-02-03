from __future__ import annotations

import datetime as dt
import html
import re
from typing import TYPE_CHECKING, Optional, Union

import discord
import twitter
from cachingutils import acached

from libs.rss_general import RssMessage

if TYPE_CHECKING:
    from libs.classes import Zbot


class TwitterRSS:
    "Utilities class for any twitter-related RSS actions"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.min_time_between_posts = 15
        self.api = twitter.Api(**bot.others['twitter'], tweet_mode="extended", timeout=15)
        self.url_pattern = r'(?:http.*://)?(?:www\.)?(?:twitter\.com/)([^?\s]+)'

    def is_twitter_url(self, string: str):
        "Check if an url is a valid Twitter URL"
        matches = re.match(self.url_pattern, string)
        return bool(matches)

    async def get_userid_from_url(self, url: str) -> Optional[int]:
        "Get a Twitter user ID from a twitter url"
        match = re.search(self.url_pattern, url)
        if match is None:
            return None
        name = match.group(1)
        usr = await self.get_user_from_name(name)
        return usr.id if usr else None

    @acached(timeout=86400)
    async def get_user_from_name(self, name: str):
        "Get a Twitter user object from a twitter username"
        try:
            return self.api.GetUser(screen_name=name)
        except twitter.TwitterError:
            return None

    @acached(timeout=86400)
    async def get_user_from_id(self, user_id: int):
        "Get a Twitter user object from a Twitter user ID"
        try:
            return self.api.GetUser(user_id=user_id)
        except twitter.TwitterError:
            return None

    async def get_feed(self, channel: discord.TextChannel, name: str, date: dt.datetime=None) -> Union[str, list[RssMessage]]:
        "Get tweets from a given Twitter user"
        if name == 'help':
            return await self.bot._(channel, "rss.tw-help")
        try:
            if isinstance(name, int) or name.isnumeric():
                posts = self.api.GetUserTimeline(user_id=int(name), exclude_replies=True)
                username = (await self.get_user_from_id(int(name))).screen_name
            else:
                posts = self.api.GetUserTimeline(screen_name=name, exclude_replies=True)
                username = name
        except twitter.error.TwitterError as err:
            if err.message == "Not authorized." or 'Unknown error' in err.message:
                return await self.bot._(channel, "rss.nothing")
            if err.message[0]['code'] == 34:
                return await self.bot._(channel, "rss.nothing")
            raise err
        if not date:
            if len(posts) == 0:
                return []
            lastpost = posts[0]
            is_rt = None
            text = html.unescape(getattr(lastpost, 'full_text', lastpost.text))
            if lastpost.retweeted:
                if possible_rt := re.search(r'^RT @([\w-]+):', text):
                    is_rt = possible_rt.group(1)
            url = "https://twitter.com/{}/status/{}".format(username.lower(), lastpost.id)
            img = None
            if lastpost.media: # if exists and is not empty
                img = lastpost.media[0].media_url_https
            obj = RssMessage(
                bot=self.bot,
                Type='tw',
                url=url,
                title=text,
                emojis=self.bot.get_cog('Emojis').customEmojis,
                date=dt.datetime.fromtimestamp(lastpost.created_at_in_seconds),
                author=lastpost.user.screen_name,
                retweeted_from=is_rt,
                channel=lastpost.user.name,
                image=img)
            return [obj]
        else:
            liste = list()
            for post in posts:
                if len(liste)>10:
                    break
                if (dt.datetime.fromtimestamp(post.created_at_in_seconds) - date).total_seconds() < self.min_time_between_posts:
                    break
                is_rt = None
                text: str = html.unescape(getattr(post, 'full_text', post.text))
                if post.retweeted:
                    if possible_rt := re.search(r'^RT @([\w-]+):', text):
                        is_rt = possible_rt.group(1)
                # remove images links if needed
                if channel.permissions_for(channel.guild.me).embed_links:
                    find_url = self.bot.get_cog("Utilities").find_url_redirection
                    for match in re.finditer(r"https://t.co/([^\s]+)", text):
                        final_url = await find_url(match.group(0))
                        if "/photo/" in final_url:
                            text = text.replace(match.group(0), '')
                url = "https://twitter.com/{}/status/{}".format(name.lower(), post.id)
                img = None
                if post.media: # if exists and is not empty
                    img = post.media[0].media_url_https
                obj = RssMessage(
                    bot=self.bot,
                    Type='tw',
                    url=url,
                    title=text,
                    emojis=self.bot.get_cog('Emojis').customEmojis,
                    date=dt.datetime.fromtimestamp(post.created_at_in_seconds),
                    author=post.user.screen_name,
                    retweeted_from=is_rt,
                    channel=post.user.name,
                    image=img)
                liste.append(obj)
            liste.reverse()
            return liste
