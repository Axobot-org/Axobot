from __future__ import annotations

import asyncio
import datetime
import time
from typing import TYPE_CHECKING, Any, Optional

import async_timeout
import discord
import feedparser
from aiohttp import ClientSession, client_exceptions
from feedparser.util import FeedParserDict

if TYPE_CHECKING:
    from libs.classes import Zbot

async def feed_parse(bot: Zbot, url: str, timeout: int, session: ClientSession = None) -> Optional[feedparser.FeedParserDict]:
    """Asynchronous parsing using cool methods"""
    # if session is provided, we have to not close it
    _session = session or ClientSession()
    try:
        async with async_timeout.timeout(timeout) as cm:
            async with _session.get(url) as response:
                html = await response.text()
                headers = response.raw_headers
    except (UnicodeDecodeError, client_exceptions.ClientError):
        if session is None:
            await _session.close()
        return FeedParserDict(entries=[])
    except asyncio.exceptions.TimeoutError:
        if session is None:
            await _session.close()
        return None
    except Exception as e:
        if session is None:
            await _session.close()
        raise e
    if session is None:
        await _session.close()
    if cm.expired:
        # request was cancelled by timeout
        bot.log.info("[RSS] feed_parse got a timeout")
        return None
    headers = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in headers}
    return feedparser.parse(html, response_headers=headers)


class RssMessage:
    def __init__(self,bot:Zbot,Type,url,title,emojis,date=datetime.datetime.now(),author=None,Format=None,channel=None,retweeted_from=None,image=None):
        self.bot = bot
        self.Type = Type
        self.url = url
        self.title = title if len(title) < 300 else title[:299]+'…'
        self.embed = False # WARNING COOKIES WARNINNG
        self.image = image
        if isinstance(date, datetime.datetime):
            self.date = date
        elif isinstance(date, time.struct_time):
            self.date = datetime.datetime(*date[:6])
        elif isinstance(date, str):
            self.date = date
        else:
            self.date = None
        self.author = author if author is None or len(author) < 100 else author[:99]+'…'
        self.format: str = Format
        if Type == 'yt':
            self.logo = emojis['youtube']
        elif Type == 'tw':
            self.logo = emojis['twitter']
        elif Type == 'reddit':
            self.logo = emojis['reddit']
        elif Type == 'twitch':
            self.logo = emojis['twitch']
        elif Type == 'deviant':
            self.logo = emojis['deviant']
        else:
            self.logo = ':newspaper:'
        self.channel = channel
        self.mentions = []
        self.rt_from = retweeted_from
        if self.author is None:
            self.author = channel
        self.embed_data: dict[str, Any]

    def fill_embed_data(self, flow: dict):
        "Fill any interesting value to send in an embed"
        self.embed_data = {'color':discord.Colour(0).default(),
            'footer':'',
            'title':None}
        if flow['embed_title'] != '':
            self.embed_data['title'] = flow['embed_title'][:256]
        if flow['embed_footer'] != '':
            self.embed_data['footer'] = flow['embed_footer'][:2048]
        if flow['embed_color'] != 0:
            self.embed_data['color'] = flow['embed_color']

    async def fill_mention(self, guild: discord.Guild, roles: list[str], translate):
        if roles == []:
            self.mentions = await translate(guild.id, "misc.none")
        else:
            r = list()
            for item in roles:
                if len(item) == 0:
                    continue
                role = discord.utils.get(guild.roles,id=int(item))
                if role is not None:
                    r.append(role.mention)
                else:
                    r.append(item)
            self.mentions = r
        return self

    async def create_msg(self, msg_format: str=None):
        if msg_format is None:
            msg_format = self.format
        if isinstance(self.date, datetime.datetime):
            date = f"<t:{self.date.timestamp():.0f}:d> <t:{self.date.timestamp():.0f}:T>"
        else:
            date = self.date
        msg_format = msg_format.replace('\\n','\n')
        if self.rt_from is not None:
            self.author = "{} (retweeted from @{})".format(self.author,self.rt_from)
        _channel = discord.utils.escape_markdown(self.channel) if self.channel else "?"
        _author = discord.utils.escape_markdown(self.author) if self.author else "?"
        text = msg_format.format_map(self.bot.SafeDict(channel=_channel, title=self.title, date=date, url=self.url,
                                                    link=self.url, mentions=", ".join(self.mentions), logo=self.logo,
                                                    author=_author))
        if not self.embed:
            return text
        else:
            emb = discord.Embed(description=text, color=self.embed_data['color'])
            emb.set_footer(text=self.embed_data['footer'])
            if self.embed_data['title'] is None:
                if self.Type != 'tw':
                    emb.title = self.title
                else:
                    emb.title = self.author
            else:
                emb.title = self.embed_data['title']
            emb.add_field(name='URL', value=self.url)
            if self.image is not None:
                emb.set_thumbnail(url=self.image)
            return emb
