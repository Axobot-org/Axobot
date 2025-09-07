import asyncio
import datetime
import importlib
import logging
import random
import re
import time
from json import dumps
from math import ceil
from typing import Any, Callable, Literal

import discord
from aiohttp import ClientSession, client_exceptions
from asyncache import cached
from cachetools import TTLCache
from discord import app_commands
from discord.ext import commands, tasks

from core.arguments import args
from core.bot_classes import Axobot
from core.checks import checks
from core.enums import ServerWarningType
from core.formatutils import FormatUtils
from core.paginator import PaginatedSelectView, Paginator
from core.tips import GuildTip
from core.type_utils import AnyStrDict, channel_is_messageable
from core.views import ConfirmView, TextInputModal
from modules.rss.src.rss_bluesky import BlueskyRSS

from .src import FeedObject, RssMessage, YoutubeRSS, feed_parse
from .src.rss_deviantart import DeviantartRSS
from .src.general import InvalidFormatError
from .src.rss_twitch import TwitchRSS
from .src.rss_web import WebRSS

importlib.reload(args)
importlib.reload(checks)


MentionsArgument = discord.app_commands.Transform[
    args.GreedyRolesArgument | Literal["none"] | None,
    args.UnionTransformer(args.GreedyRolesTransformer, "none", None)
]

TIME_BETWEEN_LOOPS = 20
RSS_LOOPS_OCCURRENCES = [
    datetime.time(hour=hours, minute=minutes, tzinfo=datetime.timezone.utc)
    for hours in range(24)
    for minutes in range(5, 60, TIME_BETWEEN_LOOPS) # every 20min starting at 5 minutes past the hour
]


TWITTER_ERROR_MESSAGE = "Due to the latest Twitter API changes, Twitter feeds are no longer supported by Axobot. Join our \
Discord server (command `/about`) to find out more."
FEEDS_PER_SUBLOOP = 20

def is_twitter_url(string: str):
    "Check if an url is a valid Twitter URL"
    matches = re.match(r"(?:http.*://)?(?:www\.)?(?:twitter\.com/)([^?\s/]+)", string)
    return bool(matches)


class Rss(commands.Cog):
    """Cog which deals with everything related to RSS feeds.
    Whether it is to add automatic tracking to a feed, or just to see the latest post of a feed, this is the right place!"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.time_between_feeds_check = 0.15 # seconds between two rss checks within a loop
        self.max_messages = 15 # max messages sent per feed per loop

        self.file = "rss"
        self.log = logging.getLogger("bot.rss")
        self.embed_color = discord.Color(6017876)
        self.loop_processing = False
        self.errors_treshold = 24 * (60 / TIME_BETWEEN_LOOPS) # max errors allowed before disabling a feed (24h)

        self.youtube_rss = YoutubeRSS(self.bot)
        self.web_rss = WebRSS(self.bot)
        self.deviant_rss = DeviantartRSS(self.bot)
        self.twitch_rss = TwitchRSS(self.bot)
        self.bluesky_rss = BlueskyRSS(self.bot)

    @property
    def table(self):
        return "rss_feed_beta" if self.bot.beta else "rss_feed"

    async def cog_load(self):
        self.rss_loop.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.rss_loop.cancel() # pylint: disable=no-member

    @app_commands.command(name="last-post")
    @app_commands.describe(url="The URL of the feed to search the last post for", feed_type="The type of the feed")
    @app_commands.rename(feed_type="type")
    @app_commands.checks.cooldown(3, 20)
    async def rss_last_post(self, interaction: discord.Interaction, url: str,
                            feed_type: Literal["bluesky", "deviantart", "twitch", "youtube", "web"] | None):
        """Search the last post of a feed

        ..Example rss last-post https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Example rss last-post aureliensama youtube

        ..Example rss last-post https://www.twitch.tv/aureliensama twitch

        ..Example rss last-post https://fr-minecraft.net/rss.php

        ..Doc rss.html#see-the-last-post"""
        await interaction.response.defer()
        parsed_feed_type: Literal["bluesky", "deviantart", "twitch", "twitter", "youtube", "web"] | None = feed_type
        if feed_type is None:
            parsed_feed_type = await self.get_feed_type_from_url(url)
        if parsed_feed_type == "youtube":
            await self.last_post_youtube(interaction, url.lower())
        elif parsed_feed_type == "twitter":
            await interaction.followup.send(TWITTER_ERROR_MESSAGE)
            return
        elif parsed_feed_type == "twitch":
            await self.last_post_twitch(interaction, url)
        elif parsed_feed_type == "deviantart":
            await self.last_post_deviant(interaction, url)
        elif parsed_feed_type == "bluesky":
            await self.last_post_bluesky(interaction, url)
        elif parsed_feed_type == "web":
            await self.last_post_web(interaction, url)
        else:
            await interaction.followup.send(await self.bot._(interaction, "rss.invalid-flow"))

    async def get_feed_type_from_url(self, url: str):
        "Get the type of a feed from its URL"
        if self.youtube_rss.is_youtube_url(url):
            return "youtube"
        if is_twitter_url(url):
            return "twitter"
        if re.match(r"^https://(www\.)?twitch\.tv/\w+", url):
            return "twitch"
        if self.deviant_rss.is_deviantart_url(url):
            return "deviantart"
        if self.bluesky_rss.is_bluesky_url(url):
            return "bluesky"
        if self.web_rss.is_web_url(url):
            return "web"
        return None


    async def last_post_youtube(self, interaction: discord.Interaction, channel: str):
        "Search for the last video of a youtube channel"
        if not channel_is_messageable(interaction.channel):
            raise TypeError(f"Interaction channel must be a MessageableChannel but is {type(interaction.channel)}")
        if self.youtube_rss.is_youtube_url(channel):
            # apparently it's a youtube.com link
            channel_id = await self.youtube_rss.get_channel_by_any_url(channel)
        else:
            # get the channel ID from its ID, name or custom URL
            channel_id = await self.youtube_rss.get_channel_by_any_term(channel)
        if channel_id is None:
            # we couldn't get the ID based on user input
            await interaction.followup.send(await self.bot._(interaction, "rss.yt-invalid"))
            return
        text = await self.youtube_rss.get_last_post(interaction.channel, channel_id, filter_config=None)
        if isinstance(text, str):
            await interaction.followup.send(text)
        else:
            form = await self.bot._(interaction, "rss.yt-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await interaction.followup.send(embed=obj)
            else:
                await interaction.followup.send(obj)

    async def last_post_twitch(self, interaction: discord.Interaction, channel: str):
        "Search for the last video of a twitch channel"
        if not channel_is_messageable(interaction.channel):
            raise TypeError(f"Interaction channel must be a MessageableChannel but is {type(interaction.channel)}")
        if self.twitch_rss.is_twitch_url(channel):
            parsed_channel = await self.twitch_rss.get_username_by_url(channel)
            if parsed_channel is None:
                await interaction.followup.send(await self.bot._(interaction, "rss.twitch-invalid"))
                return
            channel = parsed_channel
        text = await self.twitch_rss.get_last_post(interaction.channel, channel, filter_config=None)
        if isinstance(text, str):
            await interaction.followup.send(text)
        else:
            form = await self.bot._(interaction, "rss.twitch-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await interaction.followup.send(embed=obj)
            else:
                await interaction.followup.send(obj)

    async def last_post_deviant(self, interaction: discord.Interaction, user: str):
        "Search for the last post of a deviantart user"
        if not channel_is_messageable(interaction.channel):
            raise TypeError(f"Interaction channel must be a MessageableChannel but is {type(interaction.channel)}")
        if extracted_user := await self.deviant_rss.get_username_by_url(user):
            user = extracted_user
        text = await self.deviant_rss.get_last_post(interaction.channel, user, filter_config=None)
        if isinstance(text, str):
            await interaction.followup.send(text)
        else:
            form = await self.bot._(interaction, "rss.deviant-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await interaction.followup.send(embed=obj)
            else:
                await interaction.followup.send(obj)

    async def last_post_bluesky(self, interaction: discord.Interaction, user: str):
        "Search for the last post of a bluesky user"
        if not channel_is_messageable(interaction.channel):
            raise TypeError(f"Interaction channel must be a MessageableChannel but is {type(interaction.channel)}")
        if extracted_user := await self.bluesky_rss.get_username_by_url(user):
            user = extracted_user
        text = await self.bluesky_rss.get_last_post(interaction.channel, user, filter_config=None)
        if isinstance(text, str):
            await interaction.followup.send(text)
        else:
            form = await self.bot._(interaction, "rss.bluesky-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await interaction.followup.send(embed=obj)
            else:
                await interaction.followup.send(obj)

    async def last_post_web(self, interaction: discord.Interaction, link: str):
        "Search for the last post of a web feed"
        if not channel_is_messageable(interaction.channel):
            raise TypeError(f"Interaction channel must be a MessageableChannel but is {type(interaction.channel)}")
        try:
            text = await self.web_rss.get_last_post(interaction.channel, link, filter_config=None)
        except client_exceptions.InvalidURL:
            await interaction.followup.send(await self.bot._(interaction, "rss.invalid-link"))
            return
        if isinstance(text, str):
            await interaction.followup.send(text)
        else:
            form = await self.bot._(interaction, "rss.web-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await interaction.followup.send(embed=obj)
            else:
                await interaction.followup.send(obj)


    rss_main = app_commands.Group(
        name="rss",
        description="Subscribe to RSS feeds in your server",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    async def is_overflow(self, guild: discord.Guild) -> tuple[bool, int]:
        """Check if a guild still has at least a slot
        True if max number reached, followed by the feed limit"""
        feed_limit: int = await self.bot.get_config(guild.id, "rss_max_number") # type: ignore
        return len(await self.db_get_guild_feeds(guild.id)) >= feed_limit, feed_limit

    @rss_main.command(name="add")
    async def system_add(self, interaction: discord.Interaction, link: str,
                         channel: discord.TextChannel | discord.Thread | None=None):
        """Subscribe to a rss feed, and automatically send updates in this channel

        ..Example rss add https://www.deviantart.com/adri526

        ..Example rss add https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Doc rss.html#follow-a-feed"""
        if interaction.guild is None or interaction.guild_id is None:
            raise RuntimeError("This command can only be used in a guild")
        is_over, feed_limit = await self.is_overflow(interaction.guild)
        if is_over:
            await interaction.response.send_message(
                await self.bot._(interaction, "rss.flow-limit", limit=feed_limit), ephemeral=True
            )
            return
        await interaction.response.defer()
        identifiant = await self.youtube_rss.get_channel_by_any_url(link)
        feed_type = display_type = None
        if identifiant is not None:
            feed_type = "yt"
            display_type = "youtube"
        if identifiant is None and is_twitter_url(link):
            await interaction.followup.send(TWITTER_ERROR_MESSAGE, ephemeral=True)
            return
        if identifiant is None:
            identifiant = await self.twitch_rss.get_username_by_url(link)
            if identifiant is not None:
                feed_type = "twitch"
                display_type = "twitch"
        if identifiant is None:
            identifiant = await self.deviant_rss.get_username_by_url(link)
            if identifiant is not None:
                feed_type = "deviant"
                display_type = "deviantart"
        if identifiant is None:
            identifiant = await self.bluesky_rss.get_username_by_url(link)
            if identifiant is not None:
                feed_type = "bluesky"
                display_type = "bluesky"
        if identifiant is not None and not link.startswith("https://"):
            link = "https://"+link
        if identifiant is None and link.startswith("https"):
            identifiant = link
            feed_type = "web"
            display_type = "website"
        elif not link.startswith("https") or identifiant is None:
            await interaction.followup.send(await self.bot._(interaction, "rss.invalid-link"))
            return
        if feed_type is None or display_type is None or not await self.check_rss_url(link):
            await interaction.followup.send(await self.bot._(interaction, "rss.invalid-flow"))
            return
        destination_channel = channel or interaction.channel
        if destination_channel is None:
            raise RuntimeError("No channel provided for the RSS feed")
        try:
            feed_id = await self.db_add_feed(interaction.guild_id, destination_channel.id, feed_type, identifiant)
            await interaction.followup.send(
                await self.bot._(interaction, "rss.success-add",
                                 type=display_type, url=link, channel=destination_channel.mention) # type: ignore
            )
            self.log.info("RSS feed added into server %s (%s - %s)", interaction.guild_id, link, feed_id)
            await self.send_log(f"Feed added into server {interaction.guild_id} ({feed_id})", interaction.guild)
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, interaction)
        else:
            if serverlogs_cog := self.bot.get_cog("ServerLogs"): # type: ignore
                await serverlogs_cog.send_botwarning_tip(interaction)

    @rss_main.command(name="remove")
    async def systeme_rm(self, interaction: discord.Interaction, feed: str | None=None):
        """Unsubscribe from a RSS feed

        ..Example rss remove

        ..Doc rss.html#delete-a-followed-feed"""
        if interaction.guild is None:
            raise RuntimeError("This command can only be used in a guild")
        await interaction.response.defer()
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            interaction,
            await self.bot._(interaction, "rss.choose-delete"),
            max_count=None
        )
        if feed_ids is None:
            return
        await self.db_remove_feeds(feed_ids)
        await interaction.followup.send(await self.bot._(interaction, "rss.delete-success", count=len(feed_ids)))
        ids = ", ".join(map(str, feed_ids))
        self.log.info("RSS feed deleted into server %s (%s)", interaction.guild_id, ids)
        await self.send_log(f"Feed deleted into server {interaction.guild_id} ({ids})", interaction.guild)

    @systeme_rm.autocomplete("feed") # type: ignore
    async def systeme_rm_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss remove command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id, # type: ignore
                current.lower()
            )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="enable")
    async def feed_enable(self, interaction: discord.Interaction, feed: str | None=None):
        """Re-enable a disabled feed

        ..Example rss enable

        ..Doc rss.html#enable-or-disable-a-feed
        """
        if interaction.guild is None:
            raise RuntimeError("This command can only be used in a guild")
        await interaction.response.defer()
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            interaction,
            await self.bot._(interaction, "rss.choose-enable"),
            feed_filter=lambda f: not f.enabled,
            max_count=None
        )
        if feed_ids is None:
            return
        await self.db_enable_feeds(feed_ids, enable=True)
        await interaction.followup.send(await self.bot._(interaction, "rss.enable-success", count=len(feed_ids)))
        ids = ", ".join(map(str, feed_ids))
        self.log.info("RSS feed enabled into server %s (%s)", interaction.guild_id, ids)
        await self.send_log(f"Feed enabled into server {interaction.guild_id} ({ids})", interaction.guild)

    @feed_enable.autocomplete("feed") # type: ignore
    async def feed_enable_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss enable command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id, # type: ignore
                current.lower(),
                feed_filter=lambda f: not f.enabled,
                )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="disable")
    async def feed_disable(self, interaction: discord.Interaction, feed: str | None=None):
        """Disable a RSS feed

        ..Example rss disable

        ..Doc rss.html#enable-or-disable-a-feed
        """
        if interaction.guild is None or interaction.guild_id is None:
            raise RuntimeError("This command can only be used in a guild")
        await interaction.response.defer()
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            interaction,
            await self.bot._(interaction, "rss.choose-disable"),
            feed_filter=lambda f: f.enabled,
            max_count=None
        )
        if feed_ids is None:
            return
        await self.db_enable_feeds(feed_ids, enable=False)
        await interaction.followup.send(await self.bot._(interaction, "rss.disable-success", count=len(feed_ids)))
        ids = ", ".join(map(str, feed_ids))
        self.log.info("RSS feed disabled into server %s (%s)", interaction.guild_id, ids)
        await self.send_log(f"Feed disabled into server {interaction.guild_id} ({ids})", interaction.guild)
        if await self.bot.tips_manager.should_show_guild_tip(interaction.guild_id, GuildTip.RSS_DIFFERENCE_DISABLE_DELETE):
            rss_enable_cmd = await self.bot.get_command_mention("rss enable")
            rss_remove_cmd = await self.bot.get_command_mention("rss remove")
            await self.bot.tips_manager.send_guild_tip(
                interaction,
                GuildTip.RSS_DIFFERENCE_DISABLE_DELETE,
                rss_enable_cmd=rss_enable_cmd,
                rss_remove_cmd=rss_remove_cmd,
            )
            return True

    @feed_disable.autocomplete("feed") # type: ignore
    async def feed_disable_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss disable command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id, # type: ignore
                current.lower(),
                feed_filter=lambda f: f.enabled,
            )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="test")
    async def feed_test(self, interaction: discord.Interaction, feed: str, with_mentions: bool = False):
        """Test a RSS feed format
        This will send the last post of the feed following the format you set up

        ..Example rss test

        ..Doc rss.html#test-a-feed-format"""
        if interaction.guild is None:
            raise RuntimeError("This command can only be used in a guild")
        await interaction.response.defer()
        feed_ids = await self.ask_rss_id(
            int(feed) if feed.isnumeric() else None,
            interaction,
            await self.bot._(interaction, "rss.choose-test"),
            max_count=1
        )
        if feed_ids is None:
            return
        feed_object = await self.db_get_feed(feed_ids[0])
        if feed_object is None:
            return
        if not channel_is_messageable(interaction.channel):
            raise TypeError(f"Interaction channel must be a MessageableChannel but is {type(interaction.channel)}")
        if feed_object.type == "yt":
            msg = await self.youtube_rss.get_last_post(interaction.channel, feed_object.link, feed_object.filter_config)
        elif feed_object.type == "deviant":
            msg = await self.deviant_rss.get_last_post(interaction.channel, feed_object.link, feed_object.filter_config)
        elif feed_object.type == "twitch":
            msg = await self.twitch_rss.get_last_post(interaction.channel, feed_object.link, feed_object.filter_config)
        elif feed_object.type == "web":
            msg = await self.web_rss.get_last_post(interaction.channel, feed_object.link, feed_object.filter_config)
        else:
            await interaction.followup.send(await self.bot._(interaction, "rss.invalid-flow"), ephemeral=True)
            return
        if isinstance(msg, str):
            await interaction.followup.send(msg, ephemeral=True)
            return
        msg.feed = feed_object
        msg.fill_embed_data()
        await msg.fill_mention(interaction.guild)
        if with_mentions:
            allowed_mentions = msg.get_allowed_mentions()
        else:
            allowed_mentions = discord.AllowedMentions.none()
        try:
            content = await msg.create_msg()
        except InvalidFormatError:
            await interaction.followup.send(await self.bot._(interaction, "rss.test.invalid-format"))
            return
        if isinstance(content, discord.Embed):
            await interaction.followup.send(embed=content, allowed_mentions=allowed_mentions, silent=feed_object.silent_mention)
        elif content == "":
            await interaction.followup.send(await self.bot._(interaction, "rss.test.empty-result"))
        else:
            await interaction.followup.send(content, allowed_mentions=allowed_mentions, silent=feed_object.silent_mention)

    @feed_test.autocomplete("feed") # type: ignore
    async def feed_test_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss test command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id, # type: ignore
                current.lower(),
            )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="list")
    async def list_feeds(self, interaction: discord.Interaction):
        """Get a list of every subscribed RSS/Minecraft feed

        ..Doc rss.html#see-every-feed"""
        if interaction.guild is None or interaction.guild_id is None:
            raise RuntimeError("This command can only be used in a guild")
        await interaction.response.defer()
        feeds_list = await self.db_get_guild_feeds(interaction.guild_id)
        if len(feeds_list) == 0:
            # no rss feed
            await interaction.followup.send(await self.bot._(interaction, "rss.no-feed2"), ephemeral=True)
            return
        feeds_list.sort(key=lambda feed: (feed.enabled, feed.type), reverse=True)
        await self.send_rss_list(interaction, feeds_list)

    async def send_rss_list(self, interaction: discord.Interaction, feeds: list[FeedObject]):
        "Send the list paginator"
        if interaction.guild is None:
            raise RuntimeError("This command can only be used in a guild")
        rss_cog = self
        title = await self.bot._(interaction, "rss.list-title", server=interaction.guild.name, count=len(feeds))
        translation = await self.bot._(interaction, "rss.list-result")
        feeds_per_page = 10
        guild = interaction.guild

        class FeedsPaginator(Paginator):
            "Paginator used to display the RSS feeds list"
            async def _get_feeds_for_page(self, page: int):
                feeds_to_display: list[str] = []
                for i in range((page - 1) * feeds_per_page, min(page * feeds_per_page, len(feeds))):
                    feed = feeds[i]
                    channel = self.client.get_channel(feed.channel_id)
                    if isinstance(channel, (discord.abc.GuildChannel, discord.Thread)):
                        channel = channel.mention
                    else:
                        channel = str(feed.channel_id)
                    # feed mentions
                    if len(feed.role_ids) == 0:
                        roles = await self.client._(interaction, "misc.none")
                    else:
                        roles = []
                        for item in feed.role_ids:
                            role = discord.utils.get(guild.roles, id=int(item))
                            if role is not None:
                                roles.append(role.mention)
                            else:
                                roles.append(item)
                        roles = ", ".join(roles)
                        if feed.silent_mention:
                            roles += " <:silent:1093658138567245925>"
                    # feed filter
                    filter_state = await self.client._(
                        interaction,
                        "rss.list-result-filter." + feed.filter_config["filter_type"]
                    )
                    # feed name
                    feed_name: str = feed.link
                    if feed.type == "yt" and (channel_name := rss_cog.youtube_rss.get_channel_name_by_id(feed.link)):
                        feed_name = channel_name
                    if feed.enabled and not feed_name.startswith("http"):
                        feed_name = f"**{feed_name}**"
                    elif not feed.enabled:
                        feed_name += " " + await self.client._(interaction, "rss.list-disabled")
                    # last post date
                    if isinstance(feed.date, datetime.datetime):
                        last_date = f"<t:{feed.date.timestamp():.0f}>"
                    else:
                        last_date = await self.client._(interaction, "misc.none")
                    feeds_to_display.append(translation.format(
                        emoji=feed.get_emoji(self.client.emojis_manager),
                        channel=channel,
                        link=feed_name,
                        roles=roles,
                        filter=filter_state,
                        id=feed.feed_id,
                        last_post=last_date
                    ))
                return feeds_to_display

            async def get_page_count(self) -> int:
                length = len(feeds)
                if length == 0:
                    return 1
                return ceil(length / feeds_per_page)

            async def get_page_content(self, interaction, page):
                "Create one page"
                embed = discord.Embed(title=title, color=rss_cog.embed_color)
                for feed in await self._get_feeds_for_page(page):
                    embed.add_field(name=self.client.zws, value=feed, inline=False)
                if (pages_count := await self.get_page_count()) > 1:
                    footer = f"{page}/{pages_count}"
                    embed.set_footer(text=footer)
                return {
                    "embed": embed
                }

        _quit = await self.bot._(interaction, "misc.quit")
        view = FeedsPaginator(self.bot, interaction.user, stop_label=_quit.capitalize())
        msg = await view.send_init(interaction)
        await self._send_rss_delete_disabled_feeds_tip(interaction, feeds)
        if msg and await view.wait():
            # only manually disable if it was a timeout (ie. not a user stop)
            await view.disable(msg)

    async def _send_rss_delete_disabled_feeds_tip(self, interaction: discord.Interaction, feeds: list[FeedObject]):
        "Check if we should send a tip about deleting disabled feeds"
        if interaction.guild_id is None:
            raise RuntimeError("This command can only be used in a guild")
        has_disabled_feeds = any(not feed.enabled for feed in feeds)
        if has_disabled_feeds and await self.bot.tips_manager.should_show_guild_tip(
            interaction.guild_id, GuildTip.RSS_DELETE_DISABLED_FEEDS
        ):
            rss_remove_cmd = await self.bot.get_command_mention("rss remove")
            await self.bot.tips_manager.send_guild_tip(
                interaction,
                GuildTip.RSS_DELETE_DISABLED_FEEDS,
                rss_remove_cmd=rss_remove_cmd,
            )
            return True

    async def _get_feed_name(self, feed: FeedObject) -> str:
        name = feed.link
        if feed.type == "yt" and (channel_name := self.youtube_rss.get_channel_name_by_id(feed.link)):
            name = channel_name
        elif feed.type == "mc" and feed.link.endswith(':'):
            name = name[:-1]
        if len(name) > 90:
            name = name[:89] + '…'
        return name

    async def transform_feeds_to_options(self, feeds: list[FeedObject], guild: discord.Guild) -> list[discord.SelectOption]:
        "Transform a list of FeedObject into a list usable by a discord Select"
        options: list[discord.SelectOption] = []
        for feed in feeds:
            # formatted last post date
            if feed.date is None:
                last_post = '?'
            else:
                last_post = await FormatUtils.date(
                    feed.date,
                    lang=await self.bot._(guild.id, "_used_locale"),
                    year=True, digital=True
                )
            # formatted feed type name
            tr_type = await self.bot._(guild.id, "rss."+feed.type)
            # formatted channel
            if channel := guild.get_channel_or_thread(feed.channel_id):
                tr_channel = '#' + channel.name
                if len(tr_channel) > 25:
                    tr_channel = tr_channel[:25] + '…'
            else:
                tr_channel = "#deleted"
            # better name format (for Twitter/YouTube ID)
            name = await self._get_feed_name(feed)
            # emoji
            emoji = feed.get_emoji(self.bot.emojis_manager)
            options.append(discord.SelectOption(
                value=str(feed.feed_id),
                label=f"{tr_type} - {name}",
                description=f"{tr_channel} - Last post: {last_post}",
                emoji=emoji
                ))
        return options

    @cached(TTLCache(1_000, ttl=30))
    async def _get_feeds_for_choice(self, guild_id: int, feed_filter: Callable[[FeedObject], bool] | None = None):
        "Return a list of FeedObject for a given Guild, matching the given filter"
        guild_feeds = await self.db_get_guild_feeds(guild_id)
        if feed_filter:
            return [feed for feed in guild_feeds if feed_filter(feed)]
        return guild_feeds

    @cached(TTLCache(1_000, 30))
    async def get_feeds_choice(self, guild_id: int, current: str, feed_filter: Callable[[FeedObject], bool] | None = None
                               ) -> list[app_commands.Choice[str]]:
        "Return a list of feed Choice for a given Guild, matching the current input and the given filter"
        feeds: list[FeedObject] = await self._get_feeds_for_choice(guild_id, feed_filter)
        if len(feeds) == 0:
            return []
        choices: list[tuple[bool, str, app_commands.Choice[str]]] = []
        for feed in feeds:
            # formatted feed type name
            feed_type = await self.bot._(guild_id, "rss."+feed.type)
            # better name format (for Twitter/YouTube ID)
            name = await self._get_feed_name(feed)
            if current not in name.lower() and current not in feed.link.lower() and current not in str(feed.feed_id):
                continue
            choice = app_commands.Choice(name=f"<{feed_type}> {name}", value=str(feed.feed_id))
            choices.append((current not in name, name, choice))
        return [choice for _, _, choice in sorted(choices, key=lambda x: x[0:2])]

    async def ask_rss_id(self, input_id: int | None, interaction: discord.Interaction, title: str,
                         feed_filter: Callable[[FeedObject], bool] | None = None, max_count: int | None = 1) -> list[int] | None:
        "Ask the user to select a feed ID"
        if interaction.guild is None or interaction.guild_id is None:
            raise RuntimeError("This command can only be used in a guild")
        selection = []
        if feed_filter is None:
            feed_filter = lambda x: True
        if input_id is not None:
            input_feed = await self.db_get_feed(input_id)
            if not input_feed or input_feed.guild_id != interaction.guild_id:
                input_id = None
            elif not feed_filter(input_feed):
                input_id = None
            else:
                selection = [input_feed.feed_id]
        if input_id is None:
            guild_feeds = await self.db_get_guild_feeds(interaction.guild_id)
            if len(guild_feeds) == 0:
                await interaction.followup.send(await self.bot._(interaction, "rss.no-feed"), ephemeral=True)
                return
            guild_feeds = [f for f in guild_feeds if feed_filter(f)]
            if len(guild_feeds) == 0:
                await interaction.followup.send(await self.bot._(interaction, "rss.no-feed-filter"), ephemeral=True)
                return
            if max_count == 1:
                form_placeholder = await self.bot._(interaction, "rss.picker-placeholder.single")
            else:
                form_placeholder = await self.bot._(interaction, "rss.picker-placeholder.multi")
            view = PaginatedSelectView(self.bot, title,
                options=await self.transform_feeds_to_options(guild_feeds, interaction.guild),
                user=interaction.user,
                placeholder=form_placeholder,
                max_values=max_count or len(guild_feeds),
            )
            msg = await view.send_init(interaction)
            await view.wait()
            if view.values is None:
                if msg is not None:
                    await view.disable(msg)
                return
            try:
                selection = list(map(int, view.values)) if isinstance(view.values, list) else [int(view.values)]
            except ValueError:
                selection = []
        if len(selection) == 0:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        return selection

    @rss_main.command(name="set-mentions")
    @app_commands.rename(feed_id="feed")
    async def change_mentions(self, interaction: discord.Interaction, feed_id: str | None=None, silent: bool | None = None,
                              mentions: MentionsArgument = None):
        """Configures a role to be notified when a news is posted
        The "silent" parameter (Yes/No) allows to send silent messages, which won't send push notifications to your users.

        ..Example rss mentions

        ..Example rss mentions 6678466620137 Yes

        ..Example rss mentions 6678466620137 @Announcements @Twitch subs

        ..Doc rss.html#mention-a-role"""
        await interaction.response.defer()
        input_feed_id = int(feed_id) if feed_id is not None and feed_id.isnumeric() else None
        try:
            # ask for feed IDs
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                interaction,
                await self.bot._(interaction, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.type != "mc",
                max_count=None,
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, interaction)
        if feeds_ids is None:
            return
        feeds: list[FeedObject] = list(filter(None, [await self.db_get_feed(feed_id) for feed_id in feeds_ids]))
        if len(feeds) == 0:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd), ephemeral=True)
            return
        if mentions is None: # if roles should not change
            if silent is None or all(feed.silent_mention == silent for feed in feeds):
                await interaction.followup.send(await self.bot._(interaction, "rss.roles.no-change"))
                return
            count = 0
            for feed in feeds:
                if feed.silent_mention != silent:
                    await self.db_update_feed(feed.feed_id, values=[("silent_mention", silent)])
                    count += 1
            tr_key = "rss.roles.edit-silent-true" if silent else "rss.roles.edit-silent-false"
            await interaction.followup.send(await self.bot._(interaction, tr_key, count=count))
        elif mentions == "none": # if no role should be mentionned
            for feed in feeds:
                values = []
                if len(feed.role_ids) > 0:
                    values.append(("roles", ''))
                if silent is not None and feed.silent_mention != silent:
                    values.append(("silent_mention", silent))
                if len(values) > 0:
                    await self.db_update_feed(feed.feed_id, values=values)
            await interaction.followup.send(await self.bot._(interaction, "rss.roles.edit-success", count=0))
        else: # we need to parse the output
            roles_ids = [str(role.id) for role in mentions]
            names = [role.mention for role in mentions]
            for feed in feeds:
                values = []
                if feed.role_ids != roles_ids:
                    values.append(("roles", ';'.join(roles_ids)))
                if silent is not None and feed.silent_mention != silent:
                    values.append(("silent_mention", silent))
                if len(values) > 0:
                    await self.db_update_feed(feed.feed_id, values=values)
            await interaction.followup.send(
                await self.bot._(interaction, "rss.roles.edit-success", count=len(names), roles=", ".join(names)),
                allowed_mentions=discord.AllowedMentions.none()
            )

    @rss_main.command(name="refresh")
    @app_commands.checks.cooldown(1, 60*5)
    async def refresh_guild_feeds(self, interaction: discord.Interaction):
        """Refresh all the feeds of your server

        ..Doc rss.html#reload-every-feed"""
        if interaction.guild_id is None:
            raise RuntimeError("This command can only be used in a guild")
        if self.loop_processing:
            await interaction.response.send_message(
                await self.bot._(interaction, "rss.loop-processing"), ephemeral=True
            )
            return
        feeds = [f for f in await self.db_get_guild_feeds(interaction.guild_id) if f.enabled]
        if len(feeds) == 0:
            await interaction.response.send_message(
                await self.bot._(interaction, "rss.no-feed-enabled"), ephemeral=True
            )
            return
        start = time.time()
        await interaction.response.send_message(
            await self.bot._(interaction, "rss.guild-loading", emoji=self.bot.emojis_manager.customs["loading"])
        )
        await self.refresh_feeds(interaction.guild_id)
        await interaction.edit_original_response(
            content=await self.bot._(interaction, "rss.guild-complete", count=len(feeds), time=round(time.time()-start, 1))
        )

    @rss_main.command(name="move")
    @app_commands.rename(feed_id="feed")
    async def move_guild_feed(self, interaction: discord.Interaction, feed_id: str | None = None,
                              channel: discord.TextChannel | discord.Thread | None = None):
        """Move a rss feed in another channel

        ..Example rss move

        ..Example rss move 3078731683662

        ..Example rss move #cool-channels

        ..Example rss move 3078731683662 #cool-channels

        ..Doc rss.html#move-a-feed"""
        await interaction.response.defer()
        input_feed_id = int(feed_id) if feed_id is not None and feed_id.isnumeric() else None
        if channel is None:
            if not isinstance(interaction.channel, (discord.TextChannel, discord.Thread)):
                await interaction.followup.send(await self.bot._(interaction, "rss.move-invalid-channel"), ephemeral=True)
                return
            channel = interaction.channel
        try:
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                interaction,
                await self.bot._(interaction, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.channel_id != channel.id,
                max_count=None
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, interaction)
        if feeds_ids is None:
            return
        if len(feeds_ids) == 0:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        for feed in feeds_ids:
            await self.db_update_feed(feed, [("channel", channel.id)])
        await interaction.followup.send(
            await self.bot._(interaction, "rss.move-success", count=len(feeds_ids), channel=channel.mention)
        )

    @move_guild_feed.autocomplete("feed_id") # type: ignore
    async def move_guild_feed_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete for the feed ID in the /rss move command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id, # type: ignore
                current.lower(),
                )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="set-text")
    async def change_text(self, interaction: discord.Interaction, feed: str | None = None):
        """Change the text of an rss feed

        Available variables:
        - `{author}`: the author of the post
        - `{channel}`: the channel name (usually the same as author)
        - `{date}`: the post date, using Discord date markdown
        - `{long_date}`: the post date in UTC, using extended static format
        - `{timestamp}`: the Unix time of the post in seconds, usable in Discord timestamp markdown
        - `{link}` or `{url}`: a link to the post
        - `{logo}`: an emoji representing the type of post (web, Reddit, YouTube...)
        - `{title}`: the title of the post
        - `{full_text}`: the full text of the post
        - `{description}`: the description/summary of the post

        ..Example rss text 3078731683662

        ..Example rss text

        ..Doc rss.html#change-the-text"""
        await interaction.response.defer()
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        try:
            # ask for feed IDs
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                interaction,
                await self.bot._(interaction, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.type != "mc",
                max_count=None,
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, interaction)
        if feeds_ids is None:
            return
        feeds: list[FeedObject] = list(filter(None, [await self.db_get_feed(feed_id) for feed_id in feeds_ids]))
        if len(feeds) == 0:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        # present current structure and available variables, and wait for confirmation
        confirmed, interaction = await self._send_current_text_and_variabels(interaction, feeds[0].structure)
        if not confirmed or not interaction:
            return
        # ask for text through a modal
        text_modal = TextInputModal(
            title=await self.bot._(interaction, "rss.change-txt.title"),
            label=await self.bot._(interaction, "rss.change-txt.label"),
            placeholder=await self.bot._(interaction, "rss.change-txt.placeholder"),
            default=feeds[0].structure,
            max_length=1800,
            success_message=await self.bot._(interaction, "rss.change-txt.modal-success")
        )
        await interaction.response.send_modal(text_modal)
        if await text_modal.wait():
            # view timed out -> do nothing
            return
        text = text_modal.value
        for guild_feed in feeds:
            if guild_feed.structure != text:
                await self.db_update_feed(guild_feed.feed_id, [("structure", text)])
        if len(feeds) == 1:
            await interaction.followup.send(
                await self.bot._(interaction, "rss.text-success.single", id=feeds[0].feed_id, text=text)
            )
        else:
            await interaction.followup.send(await self.bot._(interaction, "rss.text-success.multiple", text=text))

    async def _send_current_text_and_variabels(self, interaction: discord.Interaction, current_feed_structure: str):
        "Send the current feed structure and the available variables, with a button to open the edition modal"
        confirm_label = await self.bot._(interaction, "misc.btn.confirm.label")
        text = await self.bot._(interaction, "rss.change-txt.confirmation.current-structure", button_label=confirm_label)
        text += f"\n```{current_feed_structure}```"
        embed_description = await self.bot._(interaction, "rss.change-txt.confirmation.variables-explanation")
        for variable in sorted(
            ("author", "channel", "date", "long_date", "timestamp", "link", "logo", "title", "full_text", "description")):
            embed_description += "\n- " + await self.bot._(interaction, f"rss.change-txt.confirmation.variables.{variable}")
        embed = discord.Embed(
            title=await self.bot._(interaction, "rss.change-txt.confirmation.variables-title"),
            description=embed_description,
            color=discord.Colour.green(),
        )
        view = ConfirmView(
            self.bot, interaction,
            validation=lambda inter: inter.user == interaction.user,
            ephemeral=False,
            send_confirmation=False,
            timeout=150, # 2:30min
        )
        await view.init()
        msg = await interaction.followup.send(text, embed=embed, view=view)
        await view.wait()
        if msg is not None:
            await view.disable(msg)
        if not view.response_interaction:
            raise RuntimeError("No response interaction")
        return bool(view.value), view.response_interaction

    @rss_main.command(name="set-embed")
    @app_commands.describe(
        should_use_embed="Use an embed or not for this feed",
        color="Color of the embed (eg. #FF00FF)",
        author_text="Text displayed in the author field of the embed (max 256 characters), 'none' to disable",
        title="Embed title (max 256 characters), 'none' to disable",
        footer_text="Small text displayed at the bottom of the embed (max 2048 characters), 'none' to disable",
        show_date_in_footer="Whether to show the post date in the footer or not",
        enable_link_in_title="Whether to enable the link in the embed title or not",
        image_location="Where to put the image in the embed (thumbnail, image, or None)",
    )
    @app_commands.rename(feed_id="feed")
    async def change_embed(self, interaction: discord.Interaction, feed_id: str | None = None,
                           should_use_embed: bool | None = None,
                           color: args.ColorArgument | None = None,
                           author_text: app_commands.Range[str, 2, 256] | None = None,
                           title: app_commands.Range[str, 2, 256] | None = None,
                           footer_text: app_commands.Range[str, 2, 2048] | None = None,
                           show_date_in_footer: bool | None = None,
                           enable_link_in_title: bool | None = None,
                           image_location: Literal["thumbnail", "banner", "none"] | None = None):
        """Use an embed or not for a feed
        You can also provide arguments to change the color/texts of the embed. Followed variables are usable in text arguments:
        - `{author}`: the author of the post
        - `{channel}`: the channel name (usually the same as author)
        - `{date}`: the post date, using Discord date markdown
        - `{long_date}`: the post date in UTC, using extended static format
        - `{timestamp}`: the Unix time of the post in seconds, usable in Discord timestamp markdown
        - `{link}` or `{url}`: a link to the post
        - `{logo}`: an emoji representing the type of post (web, Reddit, YouTube...)
        - `{title}`: the title of the post
        - `{full_text}`: the full text of the post
        - `{description}`: the description/summary of the post

        ..Example rss set-embed 6678466620137 true title: "New post from {author}!" color: red

        ..Doc rss.html#setup-a-feed-embed"""
        await interaction.response.defer()
        input_feed_id = int(feed_id) if feed_id is not None and feed_id.isnumeric() else None
        try:
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                interaction,
                await self.bot._(interaction, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.type != "mc",
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, interaction)
        if feeds_ids is None:
            return
        if len(feeds_ids) == 0:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        feed = await self.db_get_feed(feeds_ids[0])
        if feed is None:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        values_to_update = []
        txt = []

        if should_use_embed is not None and should_use_embed != feed.use_embed:
            values_to_update.append(("use_embed", should_use_embed))
            txt.append(await self.bot._(interaction, "rss.use_embed-success", v=should_use_embed, id=feed.feed_id))

        embed_data: AnyStrDict = {}
        if color is not None:
            embed_data["color"] = color.value
        if author_text is not None:
            embed_data["author_text"] = author_text
        if title is not None:
            embed_data["title"] = title
        if footer_text is not None:
            embed_data["footer_text"] = footer_text
        if show_date_in_footer is not None:
            embed_data["show_date_in_footer"] = show_date_in_footer
        if enable_link_in_title is not None:
            embed_data["enable_link_in_title"] = enable_link_in_title
        if image_location is not None:
            embed_data["image_location"] = image_location

        if embed_data:
            embed_data = feed.embed_data | embed_data
            if embed_data.get("author_text", "").lower() == "none":
                del embed_data["author_text"]
            if embed_data.get("title", "").lower() == "none":
                del embed_data["title"]
            if embed_data.get("footer_text", "").lower() == "none":
                del embed_data["footer_text"]
            values_to_update.append(("embed", dumps(embed_data)))
            txt.append(await self.bot._(interaction, "rss.embed-json-changed"))
        if len(values_to_update) > 0:
            await self.db_update_feed(feed.feed_id, values_to_update)
        else:
            await interaction.followup.send(await self.bot._(interaction, "rss.use_embed-same"))
            return
        await interaction.followup.send("\n".join(txt))

    @rss_main.command(name="set-filter")
    @app_commands.rename(feed_id="feed")
    async def change_feed_filter(self, interaction: discord.Interaction, feed_id: str,
                                 filter_type: Literal["blacklist", "whitelist", "none"], words: str | None = None):
        """Add a filter on the feed to only allow posts containing (or not containing) some words

        Words must be separated by a comma (`,`), and are case-insensitive (meaning capitalization doesn't matter)
        The bot will check their presence in either the title or the category of each post.

        ..Example rss set-filter 6678466620137 blacklist "cars, mechanic"

        ..Example rss set-filter 6678466620137 whitelist "princess, magic"

        ..Example rss set-filter 6678466620137 none

        ..Doc rss.html#filter-a-feed-posts"""
        await interaction.response.defer()
        feed = await self.db_get_feed(int(feed_id))
        if feed is None:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        # reset filter for this feed
        if filter_type == "none":
            if feed.filter_config["filter_type"] == "none":
                await interaction.followup.send(await self.bot._(interaction, "rss.filter.same"))
                return
            await self.db_update_feed(feed.feed_id, [("filter_config", "{}")])
            await interaction.followup.send(await self.bot._(interaction, "rss.filter.success.reset"))
            return
        # check for unchanged filter type
        if filter_type == feed.filter_config["filter_type"] and words is None:
            await interaction.followup.send(await self.bot._(interaction, "rss.filter.same"))
            return
        if words:
            # check for unchanged type + words
            words_list = [word.strip().lower() for word in words.split(",")]
            words_list = [word for word in words_list if len(word) > 0]
            if filter_type == feed.filter_config["filter_type"] and words_list == feed.filter_config["words"]:
                await interaction.followup.send(await self.bot._(interaction, "rss.filter.same"))
                return
            # update filter with words
            new_config = {
                "filter_type": filter_type,
                "words": words_list
            }
        else:
            # update filter without words
            new_config = {
                "filter_type": filter_type,
                "words": feed.filter_config["words"]
            }
        await self.db_update_feed(feed.feed_id, [("filter_config", dumps(new_config))])
        await interaction.followup.send(
            await self.bot._(interaction, "rss.filter.success."+filter_type,
                             type=filter_type, words=", ".join(new_config["words"]))
        )


    @change_mentions.autocomplete("feed_id")
    @change_text.autocomplete("feed")
    @change_embed.autocomplete("feed_id")
    @change_feed_filter.autocomplete("feed_id") # type: ignore
    async def edit_feed_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for the feed_id argument in the /rss set-mention, set-text, set-embed and set-filter commands"""
        try:
            return await self.get_feeds_choice(
                interaction.guild.id, # type: ignore
                current.lower(),
                feed_filter=lambda f: f.type != "mc"
                )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)


    async def check_rss_url(self, url: str):
        "Check if a given URL is a valid rss feed"
        if self.youtube_rss.is_youtube_url(url):
            return True
        if self.twitch_rss.is_twitch_url(url):
            return True
        if self.deviant_rss.is_deviantart_url(url):
            return True
        if self.bluesky_rss.is_bluesky_url(url):
            return True
        # check web feed
        feed = await feed_parse(url, 8)
        if feed is None:
            return False
        return len(feed.get("entries", [])) > 0

    async def create_id(self, feed_type: str):
        "Create a unique ID for a feed, based on its type"
        numb = str(round(time.time()/2)) + str(random.randint(10,99))
        if feed_type == "yt":
            numb = int("10" + numb)
        elif feed_type == "tw":
            numb = int("20" + numb)
        elif feed_type == "web":
            numb = int("30" + numb)
        elif feed_type == "reddit":
            numb = int("40" + numb)
        elif feed_type == "mc":
            numb = int("50" + numb)
        elif feed_type == "twitch":
            numb = int("60" + numb)
        elif feed_type == "bluesky":
            numb = int("70" + numb)
        else:
            numb = int("66" + numb)
        return numb

    async def db_get_feed(self, feed_id: int) -> FeedObject | None:
        "Get a rss feed from its ID"
        query = f"SELECT * FROM `{self.table}` WHERE `ID`='{feed_id}'"
        async with self.bot.db_main.read(query) as query_results:
            liste = list(query_results)
        return FeedObject(liste[0]) if len(liste) > 0 else None

    async def db_get_guild_feeds(self, guild_id: int):
        """Get every feed of a guild"""
        query = f"SELECT * FROM `{self.table}` WHERE `guild`='{guild_id}'"
        async with self.bot.db_main.read(query) as query_results:
            liste = [FeedObject(result) for result in query_results]
        return liste

    async def db_add_feed(self, guild_id: int, channel_id: int, _type: str, link: str):
        """Add a feed in the database"""
        feed_id = await self.create_id(_type)
        if _type == "mc":
            form = ''
        else:
            form = await self.bot._(guild_id, f"rss.{_type}-default-flow")
        query = f"INSERT INTO `{self.table}` (`ID`, `guild`, `channel`, `type`, `link`, `structure`) \
            VALUES (%(i)s, %(g)s, %(c)s, %(t)s, %(l)s, %(f)s)"
        async with self.bot.db_main.write(
            query, {'i': feed_id, 'g': guild_id, 'c': channel_id, 't': _type, 'l': link, 'f': form}
        ):
            pass
        return feed_id

    async def db_remove_feeds(self, feed_ids: list[int]) -> bool:
        """Remove some feeds from the database"""
        args_placeholder = ",".join(["%s"] * len(feed_ids))
        query = f"DELETE FROM `{self.table}` WHERE ID IN ({args_placeholder})"
        async with self.bot.db_main.write(query, tuple(feed_ids), returnrowcount=True) as query_result:
            return query_result is not None and query_result > 0

    async def db_enable_feeds(self, feed_ids: list[int], *, enable: bool) -> bool:
        "Enable or disable feeds in the database"
        args_placeholder = ",".join(["%s"] * len(feed_ids))
        query = f"UPDATE `{self.table}` SET `enabled`=%s WHERE ID IN ({args_placeholder})"
        async with self.bot.db_main.write(query, (enable, *feed_ids), returnrowcount=True) as query_result:
            return query_result is not None and query_result > 0

    async def db_get_all_feeds(self):
        """Get every feed of the database from known guilds"""
        guild_ids = [guild.id for guild in self.bot.guilds]
        args_placeholder = ",".join(["%s"] * len(guild_ids))
        query = f"SELECT * FROM `{self.table}` WHERE `guild` in ({args_placeholder}) AND `enabled`=1"
        async with self.bot.db_main.read(query, tuple(guild_ids)) as query_results:
            feeds_list = [FeedObject(result) for result in query_results]
        return feeds_list

    async def db_get_raws_count(self, get_disabled: bool = False):
        """Get the number of rss feeds"""
        query = f"SELECT COUNT(*) as count FROM `{self.table}`"
        if not get_disabled:
            query += " WHERE `guild` in (" + ", ".join([f"'{x.id}'" for x in self.bot.guilds]) + ")"
        async with self.bot.db_main.read(query, fetchone=True) as query_results:
            t = query_results["count"]
        return t

    async def db_update_feed(self, feed_id: int, values: list[tuple[str, Any]] | None=None):
        "Update a field values"
        parsed_values = values if values is not None else [(None, None)]
        if self.bot.zombie_mode:
            return
        set_query = ", ".join(f"{val[0]}=%s" for val in parsed_values)
        query = f"UPDATE `{self.table}` SET {set_query} WHERE `ID`=%s"
        async with self.bot.db_main.write(query, tuple(val[1] for val in parsed_values) + (feed_id,)):
            pass

    async def _update_feed_last_entry(self, feed_id: int, last_post_date: datetime.datetime, last_entry_id: str | None):
        "Update the last entry of a feed"
        if self.bot.zombie_mode:
            return
        values: list[tuple[str, Any]] = [("date", last_post_date)]
        if last_entry_id:
            values.append(("last_entry_id", last_entry_id))
        await self.db_update_feed(feed_id, values=values)

    async def db_increment_errors(self, working_ids: list[int], broken_ids: list[int]) -> int:
        "Increments recent_errors value by 1 for each of these IDs, and set it to 0 for the others"
        if self.bot.zombie_mode:
            return 0
        if working_ids:
            working_ids_list = ", ".join(map(str, working_ids))
            query = f"UPDATE `{self.table}` SET `recent_errors` = 0 WHERE `ID` IN ({working_ids_list})"
            async with self.bot.db_main.write(query, returnrowcount=True) as query_results:
                self.log.debug("Reset errors for %s feeds", query_results)
        if broken_ids:
            broken_ids_list = ", ".join(map(str, broken_ids))
            query = f"UPDATE `{self.table}` SET `recent_errors` = `recent_errors` + 1 WHERE `ID` IN ({broken_ids_list})"
            async with self.bot.db_main.write(query, returnrowcount=True) as query_results:
                return query_results or 0
        return 0

    async def db_set_last_refresh(self, feed_ids: list[int]):
        "Update the last_refresh field for the given feed IDs"
        if self.bot.zombie_mode:
            return
        ids_list = ", ".join(map(str, feed_ids))
        query = f"UPDATE `{self.table}` SET `last_refresh` = %s WHERE `ID` IN ({ids_list})"
        async with self.bot.db_main.write(query, (self.bot.utcnow(),), returnrowcount=True) as query_results:
            self.log.info("Set last refresh date for %s feeds", query_results)

    async def send_rss_msg(self, obj: "RssMessage", channel: discord.TextChannel | discord.Thread):
        "Send a RSS message into its Discord channel, with the corresponding mentions"
        content = await obj.create_msg()
        if self.bot.zombie_mode:
            return True
        allowed_mentions = obj.get_allowed_mentions()
        try:
            if isinstance(content, discord.Embed):
                await channel.send(
                    " ".join(obj.mentions), embed=content, allowed_mentions=allowed_mentions, silent=obj.feed.silent_mention
                )
            else:
                await channel.send(content, allowed_mentions=allowed_mentions, silent=obj.feed.silent_mention)
            return True
        except discord.HTTPException as err:
            self.log.info("Cannot send message on channel %s: %s", channel.id, err)
            self.bot.dispatch("error", err, f"While sending feed {obj.feed.feed_id} on channel {channel.id}")
        return False

    async def _get_channel_or_thread(self, guild: discord.Guild, channel_id: int
                                     ) -> discord.TextChannel | discord.Thread | None:
        """Get a channel or thread from its ID
        If not in cache, fetch it from Discord"""
        if (channel := guild.get_channel_or_thread(channel_id)) and isinstance(channel, (discord.TextChannel, discord.Thread)):
            return channel
        try:
            channel = await guild.fetch_channel(channel_id)
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                return channel
            self.bot.dispatch("error", RuntimeError(
                f"Channel {channel_id} is not a TextChannel or Thread, but {type(channel)}"
            ))
        except discord.NotFound:
            pass
        return None

    async def check_feed(self, feed: FeedObject, session: ClientSession | None = None, should_send_stats: bool = False):
        """Check one rss feed and send messages if required
        Return True if the operation was a success"""
        try:
            guild = self.bot.get_guild(feed.guild_id)
            if guild is None:
                self.log.info("Cannot send message on server %s (unknown guild)", feed.guild_id)
                return False
            chan = await self._get_channel_or_thread(guild, feed.channel_id)
            if chan is None:
                self.log.info("Cannot send message on channel %s (unknown channel)", feed.channel_id)
                self.bot.dispatch("server_warning", ServerWarningType.RSS_UNKNOWN_CHANNEL, guild,
                                  channel_id=feed.channel_id, feed_id=feed.feed_id)
                return False
            if feed.type == "yt":
                if feed.date is None:
                    objs = await self.youtube_rss.get_last_post(chan, feed.link, feed.filter_config, session)
                else:
                    objs = await self.youtube_rss.get_new_posts(chan, feed.link, feed.date, feed.filter_config, session)
            elif feed.type == "tw":
                self.bot.dispatch("server_warning", ServerWarningType.RSS_TWITTER_DISABLED, guild,
                                    channel_id=feed.channel_id, feed_id=feed.feed_id)
                return False
            elif feed.type == "web":
                if feed.date is None:
                    objs = await self.web_rss.get_last_post(chan, feed.link, feed.filter_config, session)
                else:
                    objs = await self.web_rss.get_new_posts(chan, feed.link, feed.date, feed.filter_config,
                                                            feed.last_entry_id, session)
            elif feed.type == "deviant":
                if feed.date is None:
                    objs = await self.deviant_rss.get_last_post(chan, feed.link, feed.filter_config, session)
                else:
                    objs = await self.deviant_rss.get_new_posts(chan, feed.link, feed.date, feed.filter_config, session)
            elif feed.type == "twitch":
                if feed.date is None:
                    objs = await self.twitch_rss.get_last_post(chan, feed.link, feed.filter_config, session)
                else:
                    objs = await self.twitch_rss.get_new_posts(chan, feed.link, feed.date, feed.filter_config, session)
            elif feed.type == "bluesky":
                if feed.date is None:
                    objs = await self.bluesky_rss.get_last_post(chan, feed.link, feed.filter_config, session)
                else:
                    objs = await self.bluesky_rss.get_new_posts(chan, feed.link, feed.date, feed.filter_config, session)
            else:
                self.bot.dispatch("error", RuntimeError(f"Unknown feed type {feed.type}"))
                return False
            # transform single object into list
            if isinstance(objs, RssMessage):
                objs = [objs]
            if isinstance(objs, str | int | None) or len(objs) == 0:
                return True
            if len(objs) == 0:
                return True
            latest_post_date = None
            latest_entry_id = None
            sent_messages = 0
            for obj in objs[:self.max_messages]:
                # if the guild was marked as inactive (ie. the bot wasn't there in the previous loop),
                #  mark the feeds as completed but do not send any message, to avoid spamming channels
                if feed.has_recently_been_refreshed():
                    # if we can't post messages: abort
                    if not chan.permissions_for(guild.me).send_messages:
                        self.bot.dispatch("server_warning", ServerWarningType.RSS_MISSING_TXT_PERMISSION, guild,
                                            channel=chan, feed_id=feed.feed_id)
                        return False
                    # same if we need to be able to send embeds
                    if feed.use_embed and not chan.permissions_for(guild.me).embed_links:
                        self.bot.dispatch("server_warning", ServerWarningType.RSS_MISSING_EMBED_PERMISSION, guild,
                                            channel=chan, feed_id=feed.feed_id)
                        return False
                    obj.feed = feed
                    obj.fill_embed_data()
                    await obj.fill_mention(guild)
                    try:
                        if await self.send_rss_msg(obj, chan):
                            sent_messages += 1
                    except InvalidFormatError:
                        self.bot.dispatch("server_warning", ServerWarningType.RSS_INVALID_FORMAT, guild,
                                            channel=chan, feed_id=feed.feed_id)
                        break
                latest_post_date = obj.date
                latest_entry_id = obj.entry_id
            if sent_messages > 0 and isinstance(latest_post_date, datetime.datetime):
                await self._update_feed_last_entry(feed.feed_id, latest_post_date, latest_entry_id)
            if should_send_stats and sent_messages and (statscog := self.bot.get_cog("BotStats")):
                statscog.rss_stats["messages"] += sent_messages
            return sent_messages > 0
        except Exception as err:
            error_msg = f"RSS error on feed {feed.feed_id} (type {feed.type} - channel {feed.channel_id} )"
            self.bot.dispatch("error", err, error_msg)
            return False

    async def disabled_feeds_check(self, feeds: list[FeedObject]):
        "Check each passed feed and disable it if it has too many recent errors"
        for feed in feeds:
            if feed.recent_errors >= self.errors_treshold:
                await self.db_update_feed(feed.feed_id, [("enabled", False)])
                self.log.info("Disabled feed %s (too many errors)", feed.feed_id)
                if guild := self.bot.get_guild(feed.guild_id):
                    self.bot.dispatch("server_warning", ServerWarningType.RSS_DISABLED_FEED,
                                      guild,
                                      channel_id=feed.channel_id,
                                      feed_id=feed.feed_id
                                      )

    async def _loop_refresh_one_feed(self, feed: FeedObject, session: ClientSession, guild_id: int | None) -> bool | None:
        """Refresh one feed (called by the refresh_feeds method loop)

        Returns True if the feed was checked and messages were sent, False if it was checked but no messages were sent,
        None if the feed was not checked (eg. disabled feed)"""
        if not feed.enabled:
            return None
        try:
            if feed.type == "mc":
                if mc_cog := self.bot.get_cog("Minecraft"):
                    result = await mc_cog.check_feed(feed, send_stats=guild_id is None)
                else:
                    return None
            else:
                result = await self.check_feed(feed, session, should_send_stats=guild_id is None)
        except Exception as err:
            self.bot.dispatch("error", err, f"RSS feed {feed.feed_id}")
            return False
        return result

    async def refresh_feeds(self, guild_id: int | None=None):
        "Loop through feeds and do magic things"
        if not self.bot.rss_enabled:
            return
        start = time.time()
        if self.loop_processing:
            return
        if guild_id is None:
            self.log.info("Started RSS check")
            self.loop_processing = True
            feeds_list = await self.db_get_all_feeds()
        else:
            self.log.info("Started RSS check for guild %s", guild_id)
            feeds_list = await self.db_get_guild_feeds(guild_id)
        # remove disabled feeds
        feeds_list = [feed for feed in feeds_list if feed.enabled]
        success_ids: list[int] = []
        errors_ids: list[int] = []
        checked_count = 0
        async with ClientSession() as session:
            # execute asyncio.gather by group of 'FEEDS_PER_SUBLOOP' feeds
            for i in range(0, len(feeds_list), FEEDS_PER_SUBLOOP):
                task_feeds = feeds_list[i:i+FEEDS_PER_SUBLOOP]
                results = await asyncio.gather(*[self._loop_refresh_one_feed(feed, session, guild_id) for feed in task_feeds])
                for task_result, feed in zip(results, task_feeds, strict=True):
                    if task_result is True:
                        checked_count += 1
                        success_ids.append(feed.feed_id)
                    elif task_result is False:
                        checked_count += 1
                        errors_ids.append(feed.feed_id)
                # if it wasn't the last batch, wait a few seconds
                if i+FEEDS_PER_SUBLOOP < len(feeds_list):
                    await asyncio.sleep(self.time_between_feeds_check)
        if mc_cog := self.bot.get_cog("Minecraft"):
            mc_cog.feeds.clear()
        elapsed_time = round(time.time() - start)
        desc = [f"**RSS loop done** in {elapsed_time}s ({len(success_ids)}/{checked_count} feeds)"]
        if guild_id is None:
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats["checked"] = checked_count
                statscog.rss_stats["errors"] = len(errors_ids)
                statscog.rss_stats["time"] = elapsed_time
                statscog.rss_loop_finished = True
        await self.db_set_last_refresh(list(feed.feed_id for feed in feeds_list))
        if len(errors_ids) > 0:
            desc.append(f"{len(errors_ids)} errors: {' '.join(str(x) for x in errors_ids)}")
            # update errors count in database
            await self.db_increment_errors(working_ids=success_ids, broken_ids=errors_ids)
            # disable feeds that have too many errors
            await self.disabled_feeds_check([feed for feed in feeds_list if feed.feed_id in errors_ids])
        emb = discord.Embed(description='\n'.join(desc), color=1655066, timestamp=self.bot.utcnow())
        if self.bot.user:
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        else:
            self.bot.dispatch("error", RuntimeError("Bot user is not set, but we're already at the end of the RSS loop"))
        await self.bot.send_embed(emb, url="loop")
        self.log.info(desc[0])
        if len(errors_ids) > 0:
            self.log.warning(desc[1])
        if guild_id is None:
            self.loop_processing = False

    @tasks.loop(time=RSS_LOOPS_OCCURRENCES)
    async def rss_loop(self):
        "Main method that call the loop method once every 20min - considering RSS is enabled and working"
        if not self.bot.rss_enabled:
            return
        if not self.bot.database_online:
            self.log.warning("[rss] Database is offline, skipping rss loop")
            return
        self.log.info(" RSS loop starting!")
        try:
            await self.refresh_feeds()
        except Exception as err:
            self.bot.dispatch("error", err, "RSS main loop")

    @rss_loop.before_loop
    async def before_printer(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()

    @rss_loop.error
    async def loop_error(self, error: BaseException):
        "When the loop fails"
        self.bot.dispatch("error", error, "RSS main loop has stopped <@279568324260528128>")

    async def send_log(self, text: str, guild: discord.Guild):
        """Send a log to the logging channel"""
        try:
            emb = discord.Embed(description="[RSS] "+text, color=5366650, timestamp=self.bot.utcnow())
            emb.set_footer(text=guild.name)
            if self.bot.user:
                emb.set_author(name=self.bot.user, icon_url=self.bot.display_avatar)
            else:
                self.bot.dispatch("error", RuntimeError("Bot user is not set, but we're already at the end of the RSS loop"))
            await self.bot.send_embed(emb)
        except Exception as err:
            self.bot.dispatch("error", err)


async def setup(bot):
    await bot.add_cog(Rss(bot))
