from __future__ import annotations

import asyncio
import datetime
import time
from typing import TYPE_CHECKING, Any, Optional, Union

import async_timeout
import discord
import feedparser
from aiohttp import ClientSession, client_exceptions
from feedparser.util import FeedParserDict


if TYPE_CHECKING:
    from fcts.emojis import Emojis
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

def get_emoji(cog: 'Emojis', feed_type: str) -> Union[discord.Emoji, str]:
    if feed_type == 'tw':
        return cog.get_emoji('twitter')
    elif feed_type == 'yt':
        return cog.get_emoji('youtube')
    elif feed_type == 'twitch':
        return cog.get_emoji('twitch')
    elif feed_type == 'reddit':
        return cog.get_emoji('reddit')
    elif feed_type == 'mc':
        return cog.get_emoji('minecraft')
    elif feed_type == 'deviant':
        return cog.get_emoji('deviant')
    else:
        return "📰"

class RssMessage:
    def __init__(self, bot: Zbot, feed_type: str, url: str, title: str, date=datetime.datetime.now(), author=None, msg_format=None, channel=None, retweeted_from=None, image=None):
        self.bot = bot
        self.rss_type = feed_type
        self.url = url
        self.title = title if len(title) < 300 else title[:299]+'…'
        self.embed = False # WARNING COOKIES WARNINNG
        self.image = image
        if isinstance(date, datetime.datetime):
            self.date = date
        elif isinstance(date, time.struct_time):
            self.date = datetime.datetime(*date[:6]).replace(tzinfo=datetime.timezone.utc)
        elif isinstance(date, str):
            self.date = date
        else:
            self.date = None
        self.author = author if author is None or len(author) < 100 else author[:99]+'…'
        self.format: str = msg_format
        self.logo = get_emoji(bot.get_cog('Emojis'), self.rss_type)
        if isinstance(self.logo, discord.Emoji):
            self.logo = str(self.logo)
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
            date = f"<t:{self.date.timestamp():.0f}>"
        else:
            date = self.date
        msg_format = msg_format.replace('\\n','\n')
        if self.rt_from is not None:
            self.author = f"{self.author} (retweeted from @{self.rt_from})"
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
                if self.rss_type != 'tw':
                    emb.title = self.title
                else:
                    emb.title = self.author
            else:
                emb.title = self.embed_data['title']
            emb.add_field(name='URL', value=self.url)
            if self.image is not None:
                emb.set_thumbnail(url=self.image)
            return emb

class FeedSelectView(discord.ui.View):
    "Used to ask to select an rss feed"
    def __init__(self, feeds: list[dict[str, Any]], max_values: int):
        super().__init__()
        options = self.build_options(feeds)
        self.select = discord.ui.Select(placeholder='Choose a RSS feed', min_values=1, max_values=max_values, options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
        self.feeds: list[int] = None

    def build_options(self, feeds: list[dict[str, Any]]) -> list[discord.SelectOption]:
        "Build the options list for Discord"
        res = []
        for feed in feeds:
            if len(feed['name']) > 90:
                feed['name'] = feed['name'][:89] + '…'
            label = f"{feed['tr_type']} - {feed['name']}"
            desc = f"{feed['tr_channel']} - Last post: {feed['tr_lastpost']}"
            res.append(discord.SelectOption(value=feed['ID'], label=label, description=desc, emoji=feed['emoji']))
        return res

    async def callback(self, interaction: discord.Interaction):
        "Called when the dropdown menu has been validated by the user"
        self.feeds = self.select.values
        await interaction.response.defer()
        self.select.disabled = True
        await interaction.edit_original_message(view=self)
        self.stop()
