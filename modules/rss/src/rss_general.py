from __future__ import annotations

import asyncio
import datetime
import json
import logging
import time
from typing import TYPE_CHECKING, Any, Literal, TypedDict

import discord
import feedparser
from aiohttp import ClientSession, client_exceptions
from cachetools import TTLCache
from feedparser.util import FeedParserDict

from core.caching.postition_cached import position_cached
from core.formatutils import FormatUtils
from core.parse_mentions import parse_allowed_mentions
from core.safedict import SafeDict

FeedType = Literal["tw", "yt", "twitch", "reddit", "mc", "deviant", "bluesky", "web"]

if TYPE_CHECKING:
    from core.bot_classes import Axobot
    from core.emojis_manager import EmojisManager

logger = logging.getLogger("bot.rss")

@position_cached(TTLCache(maxsize=1_000, ttl=60 * 5), key=0)
async def feed_parse(url: str, timeout: int, session: ClientSession | None = None
                     ) -> feedparser.FeedParserDict | None:
    """Asynchronous parsing using cool methods"""
    # if session is provided, we have to not close it
    if session is None:
        _session = ClientSession()
    else:
        _session = session
    try:
        user_agent_header = {"User-Agent": "Axobot feedparser"}
        async with _session.get(url, timeout=timeout, headers=user_agent_header) as response:
            html = await response.text()
            headers = response.raw_headers
    except (UnicodeDecodeError, client_exceptions.ClientError):
        if session is None:
            await _session.close()
        return FeedParserDict(entries=[], feed=FeedParserDict(), status=200)
    except asyncio.exceptions.TimeoutError:
        if session is None:
            await _session.close()
        # request was cancelled by timeout
        logger.warning("feed_parse got a timeout for url %s", url)
        return None
    except Exception as err:
        if session is None:
            await _session.close()
        raise err
    if session is None:
        await _session.close()
    if response.status >= 400:
        logger.info("feed_parse got a %s error for URL %s", response.status, url)
        return FeedParserDict(entries=[], feed=FeedParserDict(), status=response.status)
    headers = {k.decode("utf-8").lower(): v.decode("utf-8") for k, v in headers}
    result = feedparser.parse(html, response_headers=headers)
    result["status"] = response.status
    return result

async def _entry_match_word(entry: FeedParserDict, word: str) -> bool:
    if word in entry.get("title", "").lower():
        return True
    if "tags" in entry:
        for tag in entry["tags"]:
            if word in tag.get("term", "").lower():
                return True
    return False

async def check_filter(entry: FeedParserDict, filter_config: FeedFilterConfig) -> bool:
    "Check if an entry is valid according to the filter"
    if filter_config["filter_type"] == "none":
        return True
    if filter_config["filter_type"] == "blacklist":
        for word in filter_config["words"]:
            if await _entry_match_word(entry, word):
                return False
        return True
    if filter_config["filter_type"] == "whitelist":
        for word in filter_config["words"]:
            if await _entry_match_word(entry, word):
                return True
        return False
    return True

class RssMessage:
    "Represents a message ready to be sent"

    def __init__(self,
                 bot: Axobot,
                 feed: "FeedObject",
                 url: str,
                 title: str,
                 date: datetime.datetime | time.struct_time | str = datetime.datetime.now(),
                 entry_id: str | None = None,
                 author: str | None = None,
                 channel: str | None = None,
                 retweeted_from: str | None = None,
                 image: str | None = None,
                 post_text: str | None = None,
                 post_description: str | None = None,
                 ):
        self.bot = bot
        self.feed = feed
        self.url = url
        self.title = title if len(title) < 300 else title[:299]+'…'
        self.image = image
        self.post_text = post_text
        self.post_description = post_description
        if isinstance(date, datetime.datetime):
            self.date = date.replace(tzinfo=datetime.UTC)
        elif isinstance(date, time.struct_time):
            struct_timezone = date.tm_zone
            self.date = datetime.datetime(*date[:6])
            if struct_timezone is None:
                self.date = self.date.replace(tzinfo=datetime.UTC)
            else:
                timezone = datetime.timezone(datetime.timedelta(seconds=date.tm_gmtoff))
                self.date = self.date.replace(tzinfo=timezone)
        elif isinstance(date, str):
            try:
                self.date = datetime.datetime.fromisoformat(date)
            except ValueError:
                self.date = None
        else:
            self.date = None
        self.entry_id = entry_id
        self.author = author if author is None or len(author) < 100 else author[:99]+'…'
        self.logo = feed.get_emoji(bot.emojis_manager)
        if isinstance(self.logo, discord.Emoji):
            self.logo = str(self.logo)
        self.channel = channel
        self.rt_from = retweeted_from
        if self.author is None:
            self.author = channel
        # lazy loading
        self.mentions: list[str] = []
        self.embed_data: dict[str, Any] = {}

    def fill_embed_data(self):
        "Fill any interesting value to send in an embed"
        self.embed_data = {
            "color": discord.Colour.light_grey(),
            "author_text": None,
            "footer_text": None,
            "title": None,
            "show_date_in_footer": True,
            "enable_link_in_title": False,
            "image_location": "thumbnail",
        }
        if author_text := self.feed.embed_data.get("author_text"):
            self.embed_data["author_text"] = author_text
        if title := self.feed.embed_data.get("title"):
            self.embed_data["title"] = title
        if footer := self.feed.embed_data.get("footer_text"):
            self.embed_data["footer_text"] = footer
        if color := self.feed.embed_data.get("color"):
            self.embed_data["color"] = color
        if (show_date_in_footer := self.feed.embed_data.get("show_date_in_footer")) is not None:
            self.embed_data["show_date_in_footer"] = show_date_in_footer
        if (enable_link_in_title := self.feed.embed_data.get("enable_link_in_title")) is not None:
            self.embed_data["enable_link_in_title"] = enable_link_in_title
        if image_location := self.feed.embed_data.get("image_location"):
            self.embed_data["image_location"] = image_location

    async def fill_mention(self, guild: discord.Guild):
        "Fill the mentions attribute with required roles mentions"
        if len(self.feed.role_ids) == 0:
            self.mentions = []
        else:
            roles = []
            for item in self.feed.role_ids:
                if len(item) == 0:
                    continue
                role = discord.utils.get(guild.roles, id=int(item))
                if role is None:
                    roles.append(item)
                elif role.is_default():
                    roles.append("@everyone")
                else:
                    roles.append(role.mention)
            self.mentions = roles
        return self

    async def _generate_safedict(self):
        if isinstance(self.date, datetime.datetime):
            date = f"<t:{self.date.timestamp():.0f}>"
            lang = await self.bot._(self.feed.guild_id, "_used_locale")
            long_date = await FormatUtils.date(self.date, lang=lang, year=True, weekday=True, seconds=False)
            timestamp = round(self.date.timestamp())
        elif self.date is None:
            date = ""
            long_date = ""
            timestamp = ""
        else:
            date = self.date
            long_date = self.date
            timestamp = ""
        _channel = discord.utils.escape_markdown(self.channel) if self.channel else "?"
        _author = discord.utils.escape_markdown(self.author) if self.author else "?"
        # full post text
        post_text = self.post_text or ""
        # post description/summary
        description = self.post_description or ""
        return SafeDict(
            channel=_channel,
            title=self.title,
            date=date,
            long_date=long_date,
            timestamp=timestamp,
            url=self.url,
            link=self.url,
            mentions=", ".join(self.mentions),
            logo=self.logo,
            author=_author,
            full_text=post_text,
            description=description
        )

    def get_allowed_mentions(self) -> discord.AllowedMentions:
        "Parse the feed template to get the allowed users/roles mentions"
        # By default, no mentions are allowed
        allowed_mentions = discord.AllowedMentions.none()
        # Add configured role IDs
        if self.feed.role_ids:
            allowed_mentions.roles = [
                discord.Object(id=int(role_id))
                for role_id in self.feed.role_ids
            ]
        # Parse role and user mentions from the template
        allowed_mentions = parse_allowed_mentions(self.feed.structure, base=allowed_mentions)
        # Return result
        return allowed_mentions

    async def create_msg(self, msg_format: str | None = None):
        "Create a message ready to be sent, either in string or in embed"
        if msg_format is None:
            msg_format = self.feed.structure
        msg_format = msg_format.replace("\\n","\n")
        if self.rt_from is not None:
            self.author = f"{self.author} (retweeted from @{self.rt_from})"

        safedict = await self._generate_safedict()
        text = _format_text(msg_format, safedict, 3900 if self.feed.use_embed else 2000)
        if not self.feed.use_embed:
            return text[:2000]

        emb = discord.Embed(description=text[:4096], color=self.embed_data["color"])
        if self.embed_data["author_text"]:
            emb.set_author(name=_format_text(self.embed_data["author_text"], safedict, 256))
        if self.embed_data["footer_text"]:
            emb.set_footer(text=_format_text(self.embed_data["footer_text"], safedict, 2048))
        if self.embed_data["title"] is None:
            if self.feed.type != "tw":
                emb.title = self.title[:256]
            else:
                emb.title = self.author[:256]
        else:
            emb.title = _format_text(self.embed_data["title"], safedict, 256)
        if "{url}" not in msg_format and "{link}" not in msg_format:
            emb.add_field(name="URL", value=self.url[:1024])
        if self.image is not None:
            if self.embed_data["image_location"] == "thumbnail":
                emb.set_thumbnail(url=self.image)
            elif self.embed_data["image_location"] == "banner":
                emb.set_image(url=self.image)
        if self.embed_data["show_date_in_footer"] and isinstance(self.date, datetime.datetime):
            emb.timestamp = self.date
        if self.embed_data["enable_link_in_title"]:
            emb.url = self.url
        return emb

def _format_text(source: str, data: SafeDict, max_length: int):
    "Try to safely format a string with a dictionary of data, raise a custom error if it fails"
    fixed_message_data = SafeDict(data)
    for key in ("full_text", "description"):
        fixed_message_data.pop(key)
    try:
        fixed_message_length = len(source.format_map(fixed_message_data))
    except (ValueError, TypeError) as err:
        raise InvalidFormatError from err
    if (
        "{full_text}" in source
        and "{description}" in source
        and data["full_text"]
        and data["description"]
        and fixed_message_length + len(data["description"]) + len(data["full_text"]) > max_length
    ):
        # distribute remaining length between full_text and description with a 80/20 ratio
        remaining_length = max_length - fixed_message_length
        description_max_length = int(0.2 * remaining_length)
        if len(data["description"]) > description_max_length:
            data["description"] = data["description"][:description_max_length] + '…'
        full_text_max_length = remaining_length - len(data["description"])
        if len(data["full_text"]) > full_text_max_length:
            data["full_text"] = data["full_text"][:full_text_max_length] + '…'
    elif "{full_text}" in source and fixed_message_length + len(data["full_text"]) > max_length:
        # reduce full_text to fit in the max_length
        full_text_max_length = max_length - fixed_message_length
        if len(data["full_text"]) > full_text_max_length:
            data["full_text"] = data["full_text"][:full_text_max_length] + '…'
    elif "{description}" in source and fixed_message_length + len(data["description"]) > max_length:
        # reduce description to fit in the max_length
        description_max_length = max_length - fixed_message_length
        if len(data["description"]) > description_max_length:
            data["description"] = data["description"][:max_length - fixed_message_length] + '…'

    try:
        return source.format_map(data)[:max_length]
    except (ValueError, TypeError) as err:
        raise InvalidFormatError from err

class InvalidFormatError(Exception):
    pass

class FeedEmbedData(TypedDict):
    "Embed configuration for an RSS feed"
    author_text: str | None
    title: str | None
    footer_text: str | None
    color: int | None
    show_date_in_footer: bool | None
    enable_link_in_title: bool | None
    image_location: Literal["thumbnail", "banner", "none"] | None

class FeedFilterConfig(TypedDict):
    "Filter configuration for an RSS feed"
    filter_type: Literal["blacklist", "whitelist", "none"]
    words: list[str]

class FeedObject:
    "A feed record from the database"
    def __init__(self, from_dict: dict):
        self.feed_id: int = from_dict["ID"]
        self.added_at: datetime.datetime | None = (
            from_dict["added_at"]
            if from_dict["added_at"]
            else None
        )
        self.structure: str = from_dict["structure"]
        self.guild_id: int = from_dict["guild"]
        self.channel_id: int = from_dict["channel"]
        self.type: FeedType = from_dict["type"]
        self.link: str = from_dict["link"]
        self.date: datetime.datetime | None= from_dict["date"]
        self.last_entry_id: str | None = from_dict["last_entry_id"]
        self.role_ids: list[str] = [role for role in from_dict["roles"].split(';') if role.isnumeric()]
        self.use_embed: bool = from_dict["use_embed"]
        self.embed_data: FeedEmbedData = json.loads(from_dict["embed"])
        self.silent_mention: bool = bool(from_dict["silent_mention"])
        self.filter_config: FeedFilterConfig = json.loads(from_dict["filter_config"]) or {"filter_type": "none", "words": []}
        self.last_update: datetime.datetime | None = (
            from_dict["last_update"]
            if from_dict["last_update"]
            else None
        )
        self.last_refresh: datetime.datetime | None = (
            from_dict["last_refresh"]
            if from_dict["last_refresh"]
            else None
        )
        self.recent_errors: int = from_dict["recent_errors"]
        self.enabled: bool = bool(from_dict["enabled"])

    def has_recently_been_refreshed(self):
        "Return True if the feed has been refreshed in the last 7 days"
        if self.last_refresh is None:
            return False
        now = datetime.datetime.now(datetime.UTC)
        return self.last_refresh > now - datetime.timedelta(days=7)

    @classmethod
    def unrecorded(cls, from_type: str, guild_id: int | None=None, channel_id: int | None=None, link: str | None=None):
        return cls({
            "ID": None,
            "added_at": None,
            "structure": None,
            "guild": guild_id,
            "channel": channel_id,
            "type": from_type,
            "link": link,
            "date": None,
            "last_entry_id": None,
            "roles": "",
            "use_embed": False,
            "embed": "{}",
            "silent_mention": False,
            "filter_config": "{}",
            "last_update": None,
            "last_refresh": None,
            "recent_errors": 0,
            "active_guild": True,
            "enabled": True
        })

    def get_emoji(self, cog: "EmojisManager") -> discord.Emoji | str:
        "Get the representative emoji of a feed type"
        if self.type == "yt":
            return cog.get_emoji("youtube")
        if self.type == "twitch":
            return cog.get_emoji("twitch")
        if self.type == "reddit":
            return cog.get_emoji("reddit")
        if self.type == "mc":
            return cog.get_emoji("minecraft")
        if self.type == "deviant":
            return cog.get_emoji("deviant")
        if self.type == "bluesky":
            return cog.get_emoji("bluesky")
        if self.link is not None:
            if self.link.startswith("https://github.com/"):
                return cog.get_emoji("github")
            if self.link.startswith("https://reddit.com/"):
                return cog.get_emoji("reddit")
            if self.link.startswith("https://youtube.com/"):
                return cog.get_emoji("youtube")
            if self.link.startswith("https://twitrss.me/"):
                return cog.get_emoji("twitter")
            if self.link.startswith("https://minecraft.net/"):
                return cog.get_emoji("minecraft")
        return "📰"
