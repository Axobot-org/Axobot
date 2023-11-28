import asyncio
import datetime
import importlib
import random
import re
import time
from json import dumps
from math import ceil
from typing import Any, Callable, Literal, Optional, Union

import discord
from aiohttp import ClientSession, client_exceptions
from cachingutils import acached
from discord import app_commands
from discord.ext import commands, tasks

from libs.arguments import args
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks
from libs.enums import ServerWarningType
from libs.formatutils import FormatUtils
from libs.paginator import PaginatedSelectView, Paginator
from libs.rss import (FeedEmbedData, FeedObject, FeedType, RssMessage,
                      YoutubeRSS, feed_parse)
from libs.rss.rss_deviantart import DeviantartRSS
from libs.rss.rss_twitch import TwitchRSS
from libs.rss.rss_web import WebRSS
from libs.tips import GuildTip
from libs.views import TextInputModal

importlib.reload(args)
importlib.reload(checks)


web_link = {
    'fr-minecraft': 'https://fr-minecraft.net/rss.php',
    'frm': 'https://fr-minecraft.net/rss.php',
    'minecraft.net': 'https://fr-minecraft.net/minecraft_net_rss.xml',
    'gunivers': 'https://gunivers.net/feed/'
}


TWITTER_ERROR_MESSAGE = "Due to the latest Twitter API changes, Twitter feeds are no longer supported by Axobot. Join our \
Discord server (command `/about`) to find out more."
FEEDS_PER_SUBLOOP = 25

def is_twitter_url(string: str):
    "Check if an url is a valid Twitter URL"
    matches = re.match(r'(?:http.*://)?(?:www\.)?(?:twitter\.com/)([^?\s/]+)', string)
    return bool(matches)

async def can_use_rss(ctx: MyContext):
    "Check if the user can manage its guild rss feeds"
    if ctx.guild is None:
        return False
    return ctx.channel.permissions_for(ctx.author).manage_guild or await ctx.bot.get_cog("Admin").check_if_admin(ctx)


class Rss(commands.Cog):
    """Cog which deals with everything related to RSS feeds.
    Whether it is to add automatic tracking to a feed, or just to see the latest post of a feed, this is the right place!"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.time_loop = 20 # min minutes between two rss loops
        self.time_between_feeds_check = 0.15 # seconds between two rss checks within a loop
        self.max_messages = 15 # max messages sent per feed per loop

        self.file = "rss"
        self.embed_color = discord.Color(6017876)
        self.loop_processing = False
        self.errors_treshold = 24 * (60 / self.time_loop) # max errors allowed before disabling a feed (24h)

        self.youtube_rss = YoutubeRSS(self.bot)
        self.web_rss = WebRSS(self.bot)
        self.deviant_rss = DeviantartRSS(self.bot)
        self.twitch_rss = TwitchRSS(self.bot)

        self.cache: dict[str, list[RssMessage]] = {}
        # launch rss loop
        self.rss_loop.change_interval(minutes=self.time_loop) # pylint: disable=no-member

    @property
    def table(self):
        return 'rss_feed_beta' if self.bot.beta else 'rss_flow'

    async def cog_load(self):
        self.rss_loop.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.rss_loop.cancel() # pylint: disable=no-member

    @commands.hybrid_command(name="last-post")
    @app_commands.describe(url="The URL of the feed to search the last post for", feed_type="The type of the feed")
    @app_commands.rename(feed_type="type")
    @commands.cooldown(3, 20, commands.BucketType.user)
    async def rss_last_post(self, ctx: MyContext, url: str,
                            feed_type: Optional[Literal["youtube", "twitter", "twitch", "deviantart", "web"]]):
        """Search the last post of a feed

        ..Example rss last-post https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Example rss last-post aureliensama youtube

        ..Example rss last-post https://www.twitch.tv/aureliensama twitch

        ..Example rss last-post https://fr-minecraft.net/rss.php

        ..Doc rss.html#see-the-last-post"""
        await ctx.defer()
        if feed_type is None:
            feed_type = await self.get_feed_type_from_url(url)
        if feed_type == "youtube":
            await self.last_post_youtube(ctx, url.lower())
        elif feed_type == "twitter":
            await ctx.send(TWITTER_ERROR_MESSAGE)
            return
        elif feed_type == "twitch":
            await self.last_post_twitch(ctx, url)
        elif feed_type == "deviantart":
            await self.last_post_deviant(ctx, url)
        elif feed_type == "web":
            await self.last_post_web(ctx, url)
        else:
            await ctx.send(await self.bot._(ctx.channel, "rss.invalid-flow"))

    async def get_feed_type_from_url(self, url: str):
        "Get the type of a feed from its URL"
        if self.youtube_rss.is_youtube_url(url):
            return "youtube"
        if is_twitter_url(url):
            return "twitter"
        if re.match(r'^https://(www\.)?twitch\.tv/\w+', url):
            return "twitch"
        if self.deviant_rss.is_deviantart_url(url):
            return "deviantart"
        if self.web_rss.is_web_url(url):
            return "web"
        return None


    async def last_post_youtube(self, ctx: MyContext, channel: str):
        "Search for the last video of a youtube channel"
        if self.youtube_rss.is_youtube_url(channel):
            # apparently it's a youtube.com link
            channel = await self.youtube_rss.get_channel_by_any_url(channel)
        else:
            # get the channel ID from its ID, name or custom URL
            channel = await self.youtube_rss.get_channel_by_any_term(channel)
        if channel is None:
            # we couldn't get the ID based on user input
            await ctx.send(await self.bot._(ctx.channel, "rss.yt-invalid"))
            return
        text = await self.youtube_rss.get_last_post(ctx.channel, channel, filter_config=None)
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.yt-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    async def last_post_twitch(self, ctx: MyContext, channel: str):
        "Search for the last video of a twitch channel"
        if self.twitch_rss.is_twitch_url(channel):
            parsed_channel = await self.twitch_rss.get_username_by_url(channel)
            if parsed_channel is None:
                await ctx.send(await self.bot._(ctx.channel, "rss.twitch-invalid"))
                return
            channel = parsed_channel
        text = await self.twitch_rss.get_last_post(ctx.channel, channel, filter_config=None)
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.twitch-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    async def last_post_deviant(self, ctx: MyContext, user: str):
        "Search for the last post of a deviantart user"
        if extracted_user := await self.deviant_rss.get_username_by_url(user):
            user = extracted_user
        text = await self.deviant_rss.get_last_post(ctx.channel, user, filter_config=None)
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.deviant-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj, discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    async def last_post_web(self, ctx: MyContext, link: str):
        "Search for the last post of a web feed"
        link = web_link.get(link, link)
        try:
            text = await self.web_rss.get_last_post(ctx.channel, link, filter_config=None)
        except client_exceptions.InvalidURL:
            await ctx.send(await self.bot._(ctx.channel, "rss.invalid-link"))
            return
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.web-form-last")
            obj = await text.create_msg(form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)


    @commands.hybrid_group(name="rss")
    @app_commands.default_permissions(manage_guild=True)
    @commands.cooldown(2, 15, commands.BucketType.channel)
    async def rss_main(self, ctx: MyContext):
        """Subscribe to RSS feeds in your server

        ..Doc rss.html#rss"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    async def is_overflow(self, guild: discord.Guild) -> tuple[bool, int]:
        """Check if a guild still has at least a slot
        True if max number reached, followed by the feed limit"""
        feed_limit: int = await self.bot.get_config(guild.id, "rss_max_number")
        return len(await self.db_get_guild_feeds(guild.id)) >= feed_limit, feed_limit

    @rss_main.command(name="add")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def system_add(self, ctx: MyContext, link: str):
        """Subscribe to a rss feed, and automatically send updates in this channel

        ..Example rss add https://www.deviantart.com/adri526

        ..Example rss add https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Doc rss.html#follow-a-feed"""
        is_over, feed_limit = await self.is_overflow(ctx.guild)
        if is_over:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.flow-limit", limit=feed_limit))
            return
        await ctx.defer()
        identifiant = await self.youtube_rss.get_channel_by_any_url(link)
        feed_type = None
        if identifiant is not None:
            feed_type = 'yt'
            display_type = 'youtube'
        if identifiant is None and is_twitter_url(link):
            await ctx.send(TWITTER_ERROR_MESSAGE)
            return
        if identifiant is None:
            identifiant = await self.twitch_rss.get_username_by_url(link)
            if identifiant is not None:
                feed_type = 'twitch'
                display_type = 'twitch'
        if identifiant is None:
            identifiant = await self.deviant_rss.get_username_by_url(link)
            if identifiant is not None:
                feed_type = 'deviant'
                display_type = 'deviantart'
        if identifiant is not None and not link.startswith("https://"):
            link = "https://"+link
        if identifiant is None and link.startswith("https"):
            identifiant = link
            feed_type = "web"
            display_type = 'website'
        elif not link.startswith("https"):
            await ctx.send(await self.bot._(ctx.guild, "rss.invalid-link"))
            return
        if feed_type is None or not await self.check_rss_url(link):
            return await ctx.send(await self.bot._(ctx.guild.id, "rss.invalid-flow"))
        try:
            feed_id = await self.db_add_feed(ctx.guild.id,ctx.channel.id,feed_type,identifiant)
            await ctx.send(await self.bot._(
                ctx.guild,"rss.success-add", type=display_type, url=link, channel=ctx.channel.mention
            ))
            self.bot.log.info(f"RSS feed added into server {ctx.guild.id} ({link} - {feed_id})")
            await self.send_log(f"Feed added into server {ctx.guild.id} ({feed_id})", ctx.guild)
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, ctx)
        else:
            if serverlogs_cog := self.bot.get_cog("ServerLogs"):
                await serverlogs_cog.send_botwarning_tip(ctx)

    @rss_main.command(name="remove", aliases=["delete"])
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def systeme_rm(self, ctx: MyContext, feed: Optional[str]=None):
        """Unsubscribe from a RSS feed

        ..Example rss remove

        ..Doc rss.html#delete-a-followed-feed"""
        await ctx.defer()
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            ctx,
            await self.bot._(ctx.guild.id, "rss.choose-delete"),
            max_count=None
        )
        if feed_ids is None:
            return
        await self.db_remove_feeds(feed_ids)
        await ctx.send(await self.bot._(ctx.guild, "rss.delete-success", count=len(feed_ids)))
        ids = ', '.join(map(str, feed_ids))
        self.bot.log.info(f"RSS feed deleted into server {ctx.guild.id} ({ids})")
        await self.send_log(f"Feed deleted into server {ctx.guild.id} ({ids})", ctx.guild)

    @systeme_rm.autocomplete("feed")
    async def systeme_rm_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss remove command"
        try:
            return await self.get_feeds_choice(interaction.guild.id, current.lower())
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="enable")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def feed_enable(self, ctx: MyContext, feed: Optional[str]=None):
        """Re-enable a disabled feed

        ..Example rss enable

        ..Doc rss.html#enable-or-disable-a-feed
        """
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            ctx,
            await self.bot._(ctx.guild.id, "rss.choose-enable"),
            feed_filter=lambda f: not f.enabled,
            max_count=None
        )
        if feed_ids is None:
            return
        await self.db_enable_feeds(feed_ids, enable=True)
        await ctx.send(await self.bot._(ctx.guild, "rss.enable-success", count=len(feed_ids)))
        ids = ', '.join(map(str, feed_ids))
        self.bot.log.info(f"RSS feed enabled into server {ctx.guild.id} ({ids})")
        await self.send_log(f"Feed enabled into server {ctx.guild.id} ({ids})", ctx.guild)

    @feed_enable.autocomplete("feed")
    async def feed_enable_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss enable command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id,
                current.lower(),
                feed_filter=lambda f: not f.enabled,
                )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="disable")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def feed_disable(self, ctx: MyContext, feed: Optional[str]=None):
        """Disable a RSS feed

        ..Example rss disable

        ..Doc rss.html#enable-or-disable-a-feed
        """
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            ctx,
            await self.bot._(ctx.guild.id, "rss.choose-disable"),
            feed_filter=lambda f: f.enabled,
            max_count=None
        )
        if feed_ids is None:
            return
        await self.db_enable_feeds(feed_ids, enable=False)
        await ctx.send(await self.bot._(ctx.guild, "rss.disable-success", count=len(feed_ids)))
        ids = ', '.join(map(str, feed_ids))
        self.bot.log.info(f"RSS feed disabled into server {ctx.guild.id} ({ids})")
        await self.send_log(f"Feed disabled into server {ctx.guild.id} ({ids})", ctx.guild)
        if await self.bot.tips_manager.should_show_guild_tip(ctx.guild.id, GuildTip.RSS_DIFFERENCE_DISABLE_DELETE):
            rss_enable_cmd = await self.bot.get_command_mention("rss enable")
            rss_remove_cmd = await self.bot.get_command_mention("rss remove")
            await self.bot.tips_manager.send_guild_tip(
                ctx,
                GuildTip.RSS_DIFFERENCE_DISABLE_DELETE,
                rss_enable_cmd=rss_enable_cmd,
                rss_remove_cmd=rss_remove_cmd,
            )
            return True

    @feed_disable.autocomplete("feed")
    async def feed_disable_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss disable command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id,
                current.lower(),
                feed_filter=lambda f: f.enabled,
            )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="test")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def feed_test(self, ctx: MyContext, feed: Optional[str]=None):
        """Test a RSS feed format
        This will send the last post of the feed following the format you set up

        ..Example rss test

        ..Doc rss.html#test-a-feed-format"""
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        feed_ids = await self.ask_rss_id(
            input_feed_id,
            ctx,
            await self.bot._(ctx.guild.id, "rss.choose-test"),
            max_count=1
        )
        if feed_ids is None:
            return
        feed_object = await self.db_get_feed(feed_ids[0])
        if feed_object is None:
            return
        if feed_object.type == 'yt':
            msg = await self.youtube_rss.get_last_post(ctx.channel, feed_object.link, feed_object.filter_config)
        elif feed_object.type == "deviant":
            msg = await self.deviant_rss.get_last_post(ctx.channel, feed_object.link, feed_object.filter_config)
        elif feed_object.type == "twitch":
            msg = await self.twitch_rss.get_last_post(ctx.channel, feed_object.link, feed_object.filter_config)
        elif feed_object.type == "web":
            msg = await self.web_rss.get_last_post(ctx.channel, feed_object.link, feed_object.filter_config)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "rss.invalid-flow"))
            return
        if isinstance(msg, str):
            await ctx.send(msg)
            return
        msg.feed = feed_object
        msg.fill_embed_data()
        await msg.fill_mention(ctx.guild)
        allowed_mentions = discord.AllowedMentions.none()
        content = await msg.create_msg()
        if isinstance(content, discord.Embed):
            await ctx.send(embed=content, allowed_mentions=allowed_mentions, silent=feed_object.silent_mention)
        elif content == "":
            await ctx.send(await self.bot._(ctx.guild.id, "rss.test.empty-result"))
        else:
            await ctx.send(content, allowed_mentions=allowed_mentions, silent=feed_object.silent_mention)

    @feed_test.autocomplete("feed")
    async def feed_test_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete feed ID for the /rss test command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id,
                current.lower(),
            )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="list")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def list_feeds(self, ctx: MyContext):
        """Get a list of every subscribed RSS/Minecraft feed

        ..Doc rss.html#see-every-feed"""
        feeds_list = await self.db_get_guild_feeds(ctx.guild.id)
        if len(feeds_list) == 0:
            # no rss feed
            await ctx.send(await self.bot._(ctx.guild.id, "rss.no-feed2"))
            return
        feeds_list.sort(key=lambda feed: (feed.enabled, feed.type), reverse=True)
        await self.send_rss_list(ctx, feeds_list)

    async def send_rss_list(self, ctx: MyContext, feeds: list[FeedObject]):
        "Send the list paginator"
        rss_cog = self
        title = await self.bot._(ctx.guild.id, "rss.list-title", server=ctx.guild.name, count=len(feeds))
        translation = await self.bot._(ctx.guild.id, "rss.list-result")
        feeds_per_page = 10

        class FeedsPaginator(Paginator):
            "Paginator used to display the RSS feeds list"
            async def _get_feeds_for_page(self, page: int):
                feeds_to_display: list[str] = []
                for i in range((page - 1) * feeds_per_page, min(page * feeds_per_page, len(feeds))):
                    feed = feeds[i]
                    channel = self.client.get_channel(feed.channel_id)
                    if channel is not None:
                        channel = channel.mention
                    else:
                        channel = str(feed.channel_id)
                    # feed mentions
                    if len(feed.role_ids) == 0:
                        roles = await self.client._(ctx.guild.id, "misc.none")
                    else:
                        roles = []
                        for item in feed.role_ids:
                            role = discord.utils.get(ctx.guild.roles,id=int(item))
                            if role is not None:
                                roles.append(role.mention)
                            else:
                                roles.append(item)
                        roles = ", ".join(roles)
                        if feed.silent_mention:
                            roles += " <:silent:1093658138567245925>"
                    # feed name
                    feed_name: str = feed.link
                    if feed.type == 'yt' and (channel_name := rss_cog.youtube_rss.get_channel_name_by_id(feed.link)):
                        feed_name = channel_name
                    if feed.enabled and not feed_name.startswith("http"):
                        feed_name = f"**{feed_name}**"
                    elif not feed.enabled:
                        feed_name += " " + await self.client._(ctx.guild.id, "rss.list-disabled")
                    # last post date
                    if isinstance(feed.date, datetime.datetime):
                        last_date = f"<t:{feed.date.timestamp():.0f}>"
                    elif isinstance(feed.date, str):
                        last_date = feed.date
                    else:
                        last_date = await self.client._(ctx.guild.id, "misc.none")
                    feeds_to_display.append(translation.format(
                        emoji=feed.get_emoji(self.client.emojis_manager),
                        channel=channel,
                        link=feed_name,
                        roles=roles,
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
                embed = discord.Embed(title=title, color=rss_cog.embed_color, timestamp=ctx.message.created_at)
                for feed in await self._get_feeds_for_page(page):
                    embed.add_field(name=self.client.zws, value=feed, inline=False)
                footer = f"{ctx.author}  |  {page}/{await self.get_page_count()}"
                embed.set_footer(text=footer, icon_url=ctx.author.display_avatar)
                return {
                    "embed": embed
                }

        _quit = await self.bot._(ctx.guild, "misc.quit")
        view = FeedsPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
        msg = await view.send_init(ctx)
        await self._send_rss_delete_disabled_feeds_tip(ctx, feeds)
        if msg and await view.wait():
            # only manually disable if it was a timeout (ie. not a user stop)
            await view.disable(msg)

    async def _send_rss_delete_disabled_feeds_tip(self, ctx: MyContext, feeds: list[FeedObject]):
        "Check if we should send a tip about deleting disabled feeds"
        has_disabled_feeds = any(not feed.enabled for feed in feeds)
        if has_disabled_feeds and await self.bot.tips_manager.should_show_guild_tip(
            ctx.guild.id, GuildTip.RSS_DELETE_DISABLED_FEEDS
        ):
            rss_remove_cmd = await self.bot.get_command_mention("rss remove")
            await self.bot.tips_manager.send_guild_tip(
                ctx,
                GuildTip.RSS_DELETE_DISABLED_FEEDS,
                rss_remove_cmd=rss_remove_cmd,
            )
            return True

    async def _get_feed_name(self, feed: FeedObject) -> str:
        name = feed.link
        if feed.type == 'yt' and (channel_name := self.youtube_rss.get_channel_name_by_id(feed.link)):
            name = channel_name
        elif feed.type == 'mc' and feed.link.endswith(':'):
            name = name[:-1]
        if len(name) > 90:
            name = name[:89] + '…'
        return name

    async def transform_feeds_to_options(self, feeds: list[FeedObject], guild: discord.Guild) -> list[discord.SelectOption]:
        "Transform a list of FeedObject into a list usable by a discord Select"
        options: list[discord.SelectOption] = []
        for feed in feeds:
            # formatted last post date
            last_post = await FormatUtils.date(
                feed.date,
                lang=await self.bot._(guild.id, '_used_locale'),
                year=True, digital=True
            )
            # formatted feed type name
            tr_type = await self.bot._(guild.id, "rss."+feed.type)
            # formatted channel
            if channel := guild.get_channel_or_thread(feed.channel_id):
                tr_channel = '#' + channel.name
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

    @acached(timeout=30)
    async def _get_feeds_for_choice(self, guild_id: int, feed_filter: Callable[[FeedObject], bool]=None):
        "Return a list of FeedObject for a given Guild, matching the given filter"
        guild_feeds = await self.db_get_guild_feeds(guild_id)
        if feed_filter:
            return [feed for feed in guild_feeds if feed_filter(feed)]
        return guild_feeds

    @acached(timeout=30)
    async def get_feeds_choice(self, guild_id: int, current: str, feed_filter: Callable[[FeedObject], bool]=None
                               ) -> list[app_commands.Choice[str]]:
        "Return a list of feed Choice for a given Guild, matching the current input and the given filter"
        feeds: list[FeedObject] = await self._get_feeds_for_choice(guild_id, feed_filter)
        if len(feeds) == 0:
            return []
        choices: list[tuple[bool, int, app_commands.Choice]] = []
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

    async def ask_rss_id(self, input_id: Optional[int], ctx: MyContext, title: str,
                         feed_filter: Callable[[FeedObject], bool]=None, max_count: Optional[int]=1) -> Optional[list[int]]:
        "Ask the user to select a feed ID"
        selection = []
        if feed_filter is None:
            feed_filter = lambda x: True
        if input_id is not None:
            input_feed = await self.db_get_feed(input_id)
            if not input_feed or input_feed.guild_id != ctx.guild.id:
                input_id = None
            elif not feed_filter(input_feed):
                input_id = None
            else:
                selection = [input_feed.feed_id]
        if input_id is None:
            guild_feeds = await self.db_get_guild_feeds(ctx.guild.id)
            if len(guild_feeds) == 0:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.no-feed"))
                return
            guild_feeds = [f for f in guild_feeds if feed_filter(f)]
            if len(guild_feeds) == 0:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.no-feed-filter"))
                return
            if max_count == 1:
                form_placeholder = await self.bot._(ctx.channel, 'rss.picker-placeholder.single')
            else:
                form_placeholder = await self.bot._(ctx.channel, 'rss.picker-placeholder.multi')
            view = PaginatedSelectView(self.bot, title,
                options=await self.transform_feeds_to_options(guild_feeds, ctx.guild),
                user=ctx.author,
                placeholder=form_placeholder,
                max_values=max_count or len(guild_feeds),
            )
            msg = await view.send_init(ctx)
            await view.wait()
            if view.values is None:
                await view.disable(msg)
                return
            try:
                selection = list(map(int, view.values)) if isinstance(view.values, list) else [int(view.values)]
            except ValueError:
                selection = []
        if len(selection) == 0:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            return
        return selection

    def parse_output(self, arg: str) -> list[str]:
        r = re.findall(r'((?<!\\)\")((?:.(?!(?<!\\)\1))*.?)\1', arg)
        if len(r) > 0:
            flatten = lambda l: [item for sublist in l for item in sublist]
            params = [[x for x in group if x != '"'] for group in r]
            return flatten(params)
        else:
            return arg.split(" ")

    @rss_main.command(name="set-mentions", aliases=['set-mention'])
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_mentions(self, ctx: MyContext, feed: Optional[str]=None, silent: Optional[bool]=None, *, mentions: Optional[str]):
        """Configures a role to be notified when a news is posted
        The "silent" parameter (Yes/No) allows you to send new feeds as silent messages, which won't send push notifications to your users.
        If you want to use the @everyone role, please put the server ID instead of the role name.

        ..Example rss mentions

        ..Example rss mentions 6678466620137 True

        ..Example rss mentions 6678466620137 "Announcements" "Twitch subs"

        ..Doc rss.html#mention-a-role"""
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        try:
            # ask for feed IDs
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                ctx,
                await self.bot._(ctx.guild.id, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.type != "mc",
                max_count=None,
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, ctx)
        if feeds_ids is None:
            return
        feeds: list[FeedObject] = list(filter(None, [await self.db_get_feed(feed_id) for feed_id in feeds_ids]))
        if len(feeds) == 0:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            return
        no_role = {'aucun', 'none', '_', 'del'}
        if mentions is None: # if no roles was specified: we ask for them
            text = await self.bot._(ctx.guild.id, "rss.ask-roles-hint", count=len(feeds))
            text += "\n" + await self.bot._(ctx.guild.id, "rss.ask-roles-hint-example")
            if len(feeds) == 1:
                text += "\n\n"
                if len(feeds[0].role_ids) == 0:
                    text += await self.bot._(ctx.guild.id, "rss.no-roles")
                else:
                    roles = []
                    for item in feeds[0].role_ids:
                        role = discord.utils.get(ctx.guild.roles, id=int(item))
                        if role is None:
                            roles.append(item)
                        else:
                            roles.append(role.mention)
                    text += await self.bot._(ctx.guild.id,"rss.roles.list", roles=", ".join(roles))
                    del roles
            # ask for roles
            embed = discord.Embed(
                title=await self.bot._(ctx.guild.id, "rss.choose-roles"),
                color=discord.Colour(0x77ea5c),
                description=text,
                timestamp=ctx.message.created_at
            )
            emb_msg = await ctx.send(embed=embed)

            cond = False
            while not cond:
                try:
                    msg: discord.Message = await self.bot.wait_for('message',
                        check=lambda msg: msg.author==ctx.author, timeout=30.0)
                    if msg.content.lower() in no_role: # if no role should be mentionned
                        roles_ids: Optional[list[str]] = None
                    else:
                        roles_ids = []
                        names = []
                        for arg in self.parse_output(msg.content):
                            arg = arg.strip()
                            try:
                                roles = await commands.RoleConverter().convert(ctx, arg)
                                roles_ids.append(str(roles.id))
                                names.append(roles.name)
                            except commands.BadArgument:
                                await ctx.send(await self.bot._(ctx.guild.id, "rss.roles.cant-find"))
                                roles_ids = []
                                break
                    if roles_ids is None or len(roles_ids) > 0:
                        cond = True
                except asyncio.TimeoutError:
                    await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
                    await emb_msg.delete(delay=0)
                    return
        else: # if roles were specified
            if mentions in no_role: # if no role should be mentionned
                roles_ids = None
            else: # we need to parse the output
                params = self.parse_output(mentions)
                roles_ids = []
                names = []
                for arg in params:
                    try:
                        roles = await commands.RoleConverter().convert(ctx,arg)
                        roles_ids.append(str(roles.id))
                        names.append(roles.name)
                    except commands.errors.BadArgument:
                        pass
                if len(roles_ids) == 0:
                    await ctx.send(await self.bot._(ctx.guild.id,"rss.roles.cant-find"))
                    return
        try:
            if roles_ids is None:
                for feed in feeds:
                    values = []
                    if len(feed.role_ids) > 0:
                        values.append(('roles', ''))
                    if silent is not None and feed.silent_mention != silent:
                        values.append(('silent_mention', silent))
                    if len(values) > 0:
                        await self.db_update_feed(feed.feed_id, values=values)
                await ctx.send(await self.bot._(ctx.guild.id, "rss.roles.edit-success", count=0))
            else:
                for feed in feeds:
                    values = []
                    if feed.role_ids != roles_ids:
                        values.append(('roles', ';'.join(roles_ids)))
                    if silent is not None and feed.silent_mention != silent:
                        values.append(('silent_mention', silent))
                    if len(values) > 0:
                        await self.db_update_feed(feed.feed_id, values=values)
                await ctx.send(await self.bot._(ctx.guild.id, "rss.roles.edit-success", count=len(names), roles=", ".join(names)))
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, ctx)
            return

    @rss_main.command(name="refresh")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    @commands.cooldown(1, 60*5, commands.BucketType.guild)
    async def refresh_guild_feeds(self, ctx: MyContext):
        """Refresh all the feeds of your server

        ..Doc rss.html#reload-every-feed"""
        try:
            if self.loop_processing:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.loop-processing"))
                ctx.command.reset_cooldown(ctx)
                return
            start = time.time()
            msg = await ctx.send(
                await self.bot._(ctx.guild.id,"rss.guild-loading", emoji=ctx.bot.emojis_manager.customs['loading'])
            )
            feeds = [f for f in await self.db_get_guild_feeds(ctx.guild.id) if f.enabled]
            await self.refresh_feeds(ctx.guild.id)
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-complete", count=len(feeds), time=round(time.time()-start,1)))
            await msg.delete(delay=0)
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=err))

    @rss_main.command(name="move")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def move_guild_feed(self, ctx: MyContext, feed: Optional[str]=None, channel: Optional[discord.TextChannel]=None):
        """Move a rss feed in another channel

        ..Example rss move

        ..Example rss move 3078731683662

        ..Example rss move #cool-channels

        ..Example rss move 3078731683662 #cool-channels

        ..Doc rss.html#move-a-feed"""
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        if channel is None:
            channel = ctx.channel
        try:
            try:
                feeds_ids = await self.ask_rss_id(
                    input_feed_id,
                    ctx,
                    await self.bot._(ctx.guild.id, "rss.choose-mentions-1"),
                    feed_filter=lambda f: f.channel_id != channel.id,
                    max_count=None
                )
                err = None
            except Exception:
                feeds_ids = []
            if feeds_ids is None:
                return
            if len(feeds_ids) == 0:
                cmd = await self.bot.get_command_mention("about")
                await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
                if err is not None:
                    self.bot.dispatch("error", err, ctx)
                return
            for feed in feeds_ids:
                await self.db_update_feed(feed, [('channel',channel.id)])
            await ctx.send(await self.bot._(ctx.guild.id,"rss.move-success", count=len(feeds_ids), channel=channel.mention))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=err))

    @move_guild_feed.autocomplete("feed")
    async def move_guild_feed_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete for the feed ID in the /rss move command"
        try:
            return await self.get_feeds_choice(
                interaction.guild.id,
                current.lower(),
                )
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @rss_main.command(name="set-text")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_text(self, ctx: MyContext, feed: Optional[str]=None):
        """Change the text of an rss feed

        Available variables:
        - `{author}`: the author of the post
        - `{channel}`: the channel name (usually the same as author)
        - `{date}`: the post date, using Discord date markdown
        - `{long_date}`: the post date in UTC, using extended static format
        - `{timestamp}`: the Unix time of the post in seconds, usable in Discord timestamp markdown
        - `{link}` or `{url}`: a link to the post
        - `{logo}`: an emoji representing the type of post (web, Twitter, YouTube...)
        - `{mentions}`: the list of mentioned roles
        - `{title}`: the title of the post
        - `{full_text}`: the full text of the post

        ..Example rss text 3078731683662

        ..Example rss text

        ..Doc rss.html#change-the-text"""
        input_feed_id = int(feed) if feed is not None and feed.isnumeric() else None
        try:
            # ask for feed IDs
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                ctx,
                await self.bot._(ctx.guild.id, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.type != "mc",
                max_count=None,
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, ctx)
        if feeds_ids is None:
            return
        feeds: list[FeedObject] = list(filter(None, [await self.db_get_feed(feed_id) for feed_id in feeds_ids]))
        if len(feeds) == 0:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            return
        if ctx.interaction and not ctx.interaction.response.is_done():
            # ask for text through a modal
            text_modal = TextInputModal(
                title=await self.bot._(ctx.channel, "rss.change-txt.title"),
                label=await self.bot._(ctx.channel, "rss.change-txt.label"),
                placeholder=await self.bot._(ctx.channel, "rss.change-txt.placeholder"),
                default=feeds[0].structure,
                max_length=1800,
                success_message=await self.bot._(ctx.channel, "rss.change-txt.modal-success")
            )
            await ctx.interaction.response.send_modal(text_modal)
            if await text_modal.wait():
                # view timed out -> do nothing
                return
            text = text_modal.value
        else:
            # ask for text through a message
            hint = await self.bot._(ctx.guild.id, "rss.change-txt.text-version")
            if len(feeds) == 1:
                hint += "\n\n" + await self.bot._(ctx.guild.id, "rss.change-txt.previous", text=feeds[0].structure)
            await ctx.send(hint)
            def check(msg: discord.Message):
                return msg.author == ctx.author and msg.channel == ctx.channel
            try:
                msg: discord.Message = await self.bot.wait_for('message', check=check,timeout=90)
            except asyncio.TimeoutError:
                return await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
            text = msg.content
        for guild_feed in feeds:
            if guild_feed.structure != text:
                await self.db_update_feed(guild_feed.feed_id, [('structure', text)])
        if len(feeds) == 1:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.text-success.single", id=feeds[0].feed_id, text=text))
        else:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.text-success.multiple", text=text))

    @rss_main.command(name="set-embed", aliases=['embed'])
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
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
    async def change_embed(self, ctx: MyContext, feed_id: Optional[str] = None, should_use_embed: Optional[bool] = None,
                               color: discord.Color = None,
                               author_text: Optional[commands.Range[str, 2, 256]] = None,
                               title: Optional[commands.Range[str, 2, 256]] = None,
                               footer_text: Optional[commands.Range[str, 2, 2048]] = None,
                               show_date_in_footer: Optional[bool] = None,
                               enable_link_in_title: Optional[bool] = None,
                               image_location: Optional[Literal["thumbnail", "banner", "none"]] = None):
        """Use an embed or not for a feed
        You can also provide arguments to change the color/texts of the embed. Followed variables are usable in text arguments:
        - `{author}`: the author of the post
        - `{channel}`: the channel name (usually the same as author)
        - `{date}`: the post date, using Discord date markdown
        - `{long_date}`: the post date in UTC, using extended static format
        - `{timestamp}`: the Unix time of the post in seconds, usable in Discord timestamp markdown
        - `{link}` or `{url}`: a link to the post
        - `{logo}`: an emoji representing the type of post (web, Twitter, YouTube...)
        - `{mentions}`: the list of mentioned roles
        - `{title}`: the title of the post
        - `{full_text}`: the full text of the post

        ..Example rss set-embed 6678466620137 true title: "New post from {author}!" color: red

        ..Doc rss.html#setup-a-feed-embed"""
        input_feed_id = int(feed_id) if feed_id is not None and feed_id.isnumeric() else None
        try:
            feeds_ids = await self.ask_rss_id(
                input_feed_id,
                ctx,
                await self.bot._(ctx.guild.id, "rss.choose-mentions-1"),
                feed_filter=lambda f: f.type != "mc",
            )
        except Exception as err:
            feeds_ids = []
            self.bot.dispatch("error", err, ctx)
        if feeds_ids is None:
            return
        if len(feeds_ids) == 0:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            return
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()
        try:
            feed = await self.db_get_feed(feeds_ids[0])
            if feed is None:
                cmd = await self.bot.get_command_mention("about")
                await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
                return
            values_to_update = []
            txt = []

            if should_use_embed is not None and should_use_embed != feed.use_embed:
                values_to_update.append(('use_embed', should_use_embed))
                txt.append(await self.bot._(ctx.guild.id, "rss.use_embed-success", v=should_use_embed, id=feed.feed_id))

            embed_data: FeedEmbedData = {}
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
                values_to_update.append(('embed', dumps(embed_data)))
                txt.append(await self.bot._(ctx.guild.id, "rss.embed-json-changed"))
            if len(values_to_update) > 0:
                await self.db_update_feed(feed.feed_id, values_to_update)
            else:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.use_embed-same"))
                return
            await ctx.send("\n".join(txt))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "rss.guild-error", err=err))
            self.bot.dispatch("error", err, ctx)

    @rss_main.command(name="set-filter")
    @app_commands.guild_only()
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    @app_commands.rename(feed_id="feed")
    async def change_feed_filter(self, ctx: MyContext, feed_id: str, filter_type: Literal["blacklist", "whitelist", "none"], *,
                                 words: Optional[str] = None):
        """Add a filter on the feed to only allow posts containing (or not containing) some words

        Words must be separated by a comma (`,`).
        The bot will check their presence in either the title or the category of each post.

        ..Example rss set-filter 6678466620137 blacklist "cars, mechanic"

        ..Example rss set-filter 6678466620137 whitelist "princess, magic"

        ..Example rss set-filter 6678466620137 none

        ..Doc rss.html#filter-a-feed-posts"""
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer()
        feed = await self.db_get_feed(feed_id)
        if feed is None:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            return
        # reset filter for this feed
        if filter_type == "none":
            if feed.filter_config["filter_type"] == "none":
                await ctx.send(await self.bot._(ctx.guild.id, "rss.filter.same"))
                return
            await self.db_update_feed(feed.feed_id, [('filter_config', '{}')])
            await ctx.send(await self.bot._(ctx.guild.id, "rss.filter.success.reset"))
            return
        # check for unchanged filter type
        if filter_type == feed.filter_config["filter_type"] and words is None:
            await ctx.send(await self.bot._(ctx.guild.id, "rss.filter.same"))
            return
        if words:
            # check for unchanged type + words
            words_list = [word.strip().lower() for word in words.split(",")]
            words_list = [word for word in words_list if len(word) > 0]
            if filter_type == feed.filter_config["filter_type"] and words_list == feed.filter_config["words"]:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.filter.same"))
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
        await self.db_update_feed(feed.feed_id, [('filter_config', dumps(new_config))])
        await ctx.send(
            await self.bot._(ctx.guild.id, "rss.filter.success."+filter_type,
                             type=filter_type, words=', '.join(new_config["words"]))
        )


    @change_mentions.autocomplete("feed")
    @change_text.autocomplete("feed")
    @change_embed.autocomplete("feed_id")
    @change_feed_filter.autocomplete("feed_id")
    async def edit_feed_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for the feed_id argument in the /rss set-mention, set-text, set-embed and set-filter commands"""
        try:
            return await self.get_feeds_choice(
                interaction.guild.id,
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
        # check web feed
        feed = await feed_parse(self.bot, url, 8)
        if feed is None:
            return False
        return len(feed.get("entries", [])) > 0

    async def create_id(self, feed_type: FeedType):
        "Create a unique ID for a feed, based on its type"
        numb = str(round(time.time()/2)) + str(random.randint(10,99))
        if feed_type == 'yt':
            numb = int('10'+numb)
        elif feed_type == 'tw':
            numb = int('20'+numb)
        elif feed_type == 'web':
            numb = int('30'+numb)
        elif feed_type == 'reddit':
            numb = int('40'+numb)
        elif feed_type == 'mc':
            numb = int('50'+numb)
        elif feed_type == 'twitch':
            numb = int('60'+numb)
        else:
            numb = int('66'+numb)
        return numb

    async def db_get_feed(self, feed_id: int) -> Optional[FeedObject]:
        "Get a rss feed from its ID"
        query = f"SELECT * FROM `{self.table}` WHERE `ID`='{feed_id}'"
        async with self.bot.db_query(query) as query_results:
            liste = list(query_results)
        return FeedObject(liste[0]) if len(liste) > 0 else None

    async def db_get_guild_feeds(self, guild_id: int):
        """Get every feed of a guild"""
        query = f"SELECT * FROM `{self.table}` WHERE `guild`='{guild_id}'"
        async with self.bot.db_query(query) as query_results:
            liste = [FeedObject(result) for result in query_results]
        return liste

    async def db_add_feed(self, guild_id:int, channel_id:int, _type:str, link:str):
        """Add a feed in the database"""
        feed_id = await self.create_id(_type)
        if _type == 'mc':
            form = ''
        else:
            form = await self.bot._(guild_id, f"rss.{_type}-default-flow")
        query = f"INSERT INTO `{self.table}` (`ID`, `guild`, `channel`, `type`, `link`, `structure`) VALUES (%(i)s, %(g)s, %(c)s, %(t)s, %(l)s, %(f)s)"
        async with self.bot.db_query(query, { 'i': feed_id, 'g': guild_id, 'c': channel_id, 't': _type, 'l': link, 'f': form }):
            pass
        return feed_id

    async def db_remove_feeds(self, feed_ids: list[int]) -> bool:
        """Remove some feeds from the database"""
        if not all(isinstance(feed_id, int) for feed_id in feed_ids):
            raise ValueError("Feed IDs must be integers")
        query = "DELETE FROM `{}` WHERE ID IN ({})".format(
            self.table,
            ",".join(["%s"] * len(feed_ids))
        )
        async with self.bot.db_query(query, feed_ids, returnrowcount=True) as query_result:
            return query_result > 0

    async def db_enable_feeds(self, feed_ids: list[int], *, enable: bool) -> bool:
        "Enable or disable feeds in the database"
        if not all(isinstance(feed_id, int) for feed_id in feed_ids):
            raise ValueError("Feed IDs must be integers")
        query = f"UPDATE `{self.table}` SET `enabled`=%s WHERE ID IN ({','.join(['%s'] * len(feed_ids))})"
        async with self.bot.db_query(query, (enable, *feed_ids), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_get_all_feeds(self):
        """Get every feed of the database"""
        guild_ids = [
            guild.id
            for guild in self.bot.guilds
            if not await self.bot.check_axobot_presence(guild=guild)
        ]
        query = "SELECT * FROM `{}` WHERE `guild` in ({})".format(self.table,','.join(["'{}'".format(g_id) for g_id in guild_ids]))
        async with self.bot.db_query(query) as query_results:
            liste = [FeedObject(result) for result in query_results]
        return liste

    async def db_get_raws_count(self, get_disabled: bool = False):
        """Get the number of rss feeds"""
        query = f"SELECT COUNT(*) as count FROM `{self.table}`"
        if not get_disabled:
            query += " WHERE `guild` in (" + ','.join([f"'{x.id}'" for x in self.bot.guilds]) + ")"
        async with self.bot.db_query(query, fetchone=True) as query_results:
            t = query_results['count']
        return t

    async def db_update_feed(self, feed_id: int, values: Optional[list[tuple[str, Any]]]=None):
        "Update a field values"
        values = values if values is not None else [(None, None)]
        if self.bot.zombie_mode:
            return
        set_query = ', '.join('{}=%s'.format(val[0]) for val in values)
        query = f"UPDATE `{self.table}` SET {set_query} WHERE `ID`=%s"
        async with self.bot.db_query(query, [val[1] for val in values] + [feed_id]):
            pass

    async def _update_feed_last_entry(self, feed_id: int, last_post_date: datetime.datetime, last_entry_id: Optional[str]):
        "Update the last entry of a feed"
        if self.bot.zombie_mode:
            return
        values = [("date", last_post_date)]
        if last_entry_id:
            values.append(("last_entry_id", last_entry_id))
        await self.db_update_feed(feed_id, values=values)

    async def db_increment_errors(self, working_ids: list[int], broken_ids: list[int]) -> int:
        "Increments recent_errors value by 1 for each of these IDs, and set it to 0 for the others"
        if self.bot.zombie_mode:
            return 0
        if working_ids:
            working_ids_list = ', '.join(map(str, working_ids))
            query = f"UPDATE `{self.table}` SET `recent_errors` = 0 WHERE `ID` IN ({working_ids_list})"
            async with self.bot.db_query(query, returnrowcount=True) as query_results:
                self.bot.log.debug("[rss] reset errors for %s feeds", query_results)
        if broken_ids:
            broken_ids_list = ', '.join(map(str, broken_ids))
            query = f"UPDATE `{self.table}` SET `recent_errors` = `recent_errors` + 1 WHERE `ID` IN ({broken_ids_list})"
            async with self.bot.db_query(query, returnrowcount=True) as query_results:
                return query_results

    async def db_set_last_refresh(self, feed_ids: list[int]):
        "Update the last_refresh field for the given feed IDs"
        if self.bot.zombie_mode:
            return
        ids_list = ', '.join(map(str, feed_ids))
        query = f"UPDATE `{self.table}` SET `last_refresh` = %s WHERE `ID` IN ({ids_list})"
        async with self.bot.db_query(query, (datetime.datetime.utcnow(),), returnrowcount=True) as query_results:
            self.bot.log.info("[rss] set last refresh for %s feeds", query_results)

    async def send_rss_msg(self, obj: "RssMessage", channel: Union[discord.TextChannel, discord.Thread], send_stats):
        "Send a RSS message into its Discord channel, with the corresponding mentions"
        content = await obj.create_msg()
        if self.bot.zombie_mode:
            return
        allowed_mentions = discord.AllowedMentions(everyone=False, roles=[
            discord.Object(id=int(role_id)) for role_id in obj.feed.role_ids
        ])
        try:
            if isinstance(content, discord.Embed):
                await channel.send(
                    " ".join(obj.mentions), embed=content, allowed_mentions=allowed_mentions, silent=obj.feed.silent_mention
                )
            else:
                await channel.send(content, allowed_mentions=allowed_mentions, silent=obj.feed.silent_mention)
            if send_stats:
                if statscog := self.bot.get_cog("BotStats"):
                    statscog.rss_stats['messages'] += 1
        except discord.HTTPException as err:
            self.bot.log.info(f"[send_rss_msg] Cannot send message on channel {channel.id}: {err}")
            self.bot.dispatch("error", err, f"While sending feed {obj.feed.feed_id} on channel {channel.id}")
        except Exception as err:
            self.bot.log.info(f"[send_rss_msg] Cannot send message on channel {channel.id}: {err}")
            self.bot.dispatch("error", err, f"While sending feed {obj.feed.feed_id} on channel {channel.id}")

    async def check_feed(self, feed: FeedObject, session: ClientSession = None, send_stats: bool=False):
        """Check one rss feed and send messages if required
        Return True if the operation was a success"""
        try:
            guild = self.bot.get_guild(feed.guild_id)
            if guild is None:
                self.bot.log.info("[send_rss_msg] Cannot send message on server %s (unknown guild)", feed.guild_id)
                return False
            chan: Union[discord.TextChannel, discord.Thread, None] = guild.get_channel_or_thread(feed.channel_id)
            if chan is None:
                self.bot.log.info("[send_rss_msg] Cannot send message on channel %s (unknown channel)", feed.channel_id)
                self.bot.dispatch("server_warning", ServerWarningType.RSS_UNKNOWN_CHANNEL, guild,
                                  channel_id=feed.channel_id, feed_id=feed.feed_id)
                return False
            if feed.link in self.cache:
                objs = self.cache[feed.link]
            else:
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
                else:
                    self.bot.dispatch("error", RuntimeError(f"Unknown feed type {feed.type}"))
                    return False
                # transform single object into list
                if isinstance(objs, RssMessage):
                    objs = [objs]
            if isinstance(objs, (str, type(None), int)) or len(objs) == 0:
                return True
            elif isinstance(objs, list):
                # update cache
                self.cache[feed.link] = objs
                latest_post_date = None
                latest_entry_id = None
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
                        await self.send_rss_msg(obj, chan, send_stats)
                    latest_post_date = obj.date
                    latest_entry_id = obj.entry_id
                if isinstance(latest_post_date, datetime.datetime):
                    await self._update_feed_last_entry(feed.feed_id, latest_post_date, latest_entry_id)
                return True
            else:
                return True
        except Exception as err:
            error_msg = f"RSS error on feed {feed.feed_id} (type {feed.type} - channel {feed.channel_id} )"
            self.bot.dispatch("error", err, error_msg)
            return False

    async def disabled_feeds_check(self, feeds: list[FeedObject]):
        "Check each passed feed and disable it if it has too many recent errors"
        for feed in feeds:
            if feed.recent_errors >= self.errors_treshold:
                await self.db_update_feed(feed.feed_id, [('enabled', False)])
                self.bot.log.info(f"[rss] Disabled feed {feed.feed_id} (too many errors)")
                if guild := self.bot.get_guild(feed.guild_id):
                    self.bot.dispatch("server_warning", ServerWarningType.RSS_DISABLED_FEED,
                                      guild,
                                      channel_id=feed.channel_id,
                                      feed_id=feed.feed_id
                                      )

    async def _loop_refresh_one_feed(self, feed: FeedObject, session: ClientSession, guild_id: Optional[int]) -> Optional[bool]:
        "Refresh one feed (called by the refresh_feeds method loop)"
        if not feed.enabled:
            return None
        try:
            if feed.type == 'mc':
                result = await self.bot.get_cog('Minecraft').check_feed(feed, send_stats=guild_id is None)
            else:
                result = await self.check_feed(feed, session, send_stats=guild_id is None)
        except Exception as err:
            self.bot.dispatch("error", err, f"RSS feed {feed.feed_id}")
            return False
        return result

    async def refresh_feeds(self, guild_id: Optional[int]=None):
        "Loop through feeds and do magic things"
        if not self.bot.rss_enabled:
            return
        start = time.time()
        if self.loop_processing:
            return
        if guild_id is None:
            self.bot.log.info("Check RSS lancé")
            self.loop_processing = True
            feeds_list = await self.db_get_all_feeds()
        else:
            self.bot.log.info(f"Check RSS lancé pour le serveur {guild_id}")
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
                for task_result, feed in zip(results, task_feeds):
                    if task_result is True:
                        checked_count += 1
                        success_ids.append(feed.feed_id)
                    elif task_result is False:
                        checked_count += 1
                        errors_ids.append(feed.feed_id)
                # if it wasn't the last batch, wait a few seconds
                if i+FEEDS_PER_SUBLOOP < len(feeds_list):
                    await asyncio.sleep(self.time_between_feeds_check)
        self.bot.get_cog('Minecraft').feeds.clear()
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
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")
        self.bot.log.info(desc[0])
        if len(errors_ids) > 0:
            self.bot.log.warning("[rss] "+desc[1])
        if guild_id is None:
            self.loop_processing = False
        self.cache.clear()

    @tasks.loop(minutes=20)
    async def rss_loop(self):
        "Main method that call the loop method once every 20min - considering RSS is enabled and working"
        if not self.bot.rss_enabled:
            return
        if not self.bot.database_online:
            self.bot.log.warning('[rss] Database is offline, skipping rss loop')
            return
        self.bot.log.info(" Boucle rss commencée !")
        try:
            await self.refresh_feeds()
        except Exception as err:
            self.bot.dispatch("error", err, "RSS main loop")

    @rss_loop.before_loop
    async def before_printer(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()

    @rss_loop.error
    async def loop_error(self, error: Exception):
        "When the loop fails"
        self.bot.dispatch("error", error, "RSS main loop has stopped <@279568324260528128>")


    @commands.command(name="rss_loop",hidden=True)
    @commands.check(checks.is_bot_admin)
    async def rss_loop_admin(self, ctx: MyContext, new_state: Literal["start", "stop", "once"]):
        """Manage the rss loop
        new_state can be start, stop or once"""
        if not ctx.bot.database_online:
            emoji = random.choice(["crétin ?","? Tu ferais mieux de fixer tes bugs","?","? :rofl:","?"])
            return await ctx.send("Lol, t'as oublié que la base de donnée était hors ligne " + emoji)
        if new_state == "start":
            try:
                self.rss_loop.start() # pylint: disable=no-member
            except RuntimeError:
                await ctx.send("La boucle est déjà en cours !")
            else:
                await ctx.send("Boucle rss relancée !")
        elif new_state == "stop":
            self.rss_loop.cancel() # pylint: disable=no-member
            self.bot.log.info(" Boucle rss arrêtée de force par un admin")
            await ctx.send("Boucle rss arrêtée de force !")
        elif new_state == "once":
            if self.loop_processing:
                await ctx.send("Une boucle rss est déjà en cours !")
            else:
                await ctx.send("Et hop ! Une itération de la boucle en cours !")
                self.bot.log.info(" Boucle rss forcée")
                await self.refresh_feeds()

    async def send_log(self, text: str, guild: discord.Guild):
        """Send a log to the logging channel"""
        try:
            emb = discord.Embed(description="[RSS] "+text, color=5366650, timestamp=self.bot.utcnow())
            emb.set_footer(text=guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)
        except Exception as err:
            self.bot.dispatch("error", err)


async def setup(bot):
    await bot.add_cog(Rss(bot))
