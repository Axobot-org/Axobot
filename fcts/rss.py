import asyncio
import datetime
import importlib
import random
import re
import time
from typing import Callable, Literal, Optional, Union

import discord
import twitter
from aiohttp import ClientSession, client_exceptions
from discord.ext import commands, tasks
from libs.bot_classes import MyContext, Axobot
from libs.enums import ServerWarningType
from libs.formatutils import FormatUtils
from libs.paginator import PaginatedSelectView
from libs.rss import RssMessage, TwitterRSS, YoutubeRSS, feed_parse
from libs.rss.rss_general import FeedObject, FeedType

from . import args, checks

importlib.reload(args)
importlib.reload(checks)



web_link={'fr-minecraft':'http://fr-minecraft.net/rss.php',
          'frm':'http://fr-minecraft.net/rss.php',
          'minecraft.net':'https://fr-minecraft.net/minecraft_net_rss.xml',
          'gunivers':'https://gunivers.net/feed/'
          }

reddit_link={'minecraft':'https://www.reddit.com/r/Minecraft',
             'reddit':'https://www.reddit.com/r/news',
             'discord':'https://www.reddit.com/r/discordapp'
             }

async def can_use_rss(ctx: MyContext):
    "Check if the user can manage its guild rss feeds"
    if ctx.guild is None:
        return False
    return ctx.channel.permissions_for(ctx.author).manage_guild or await ctx.bot.get_cog("Admin").check_if_admin(ctx)


class Rss(commands.Cog):
    """Cog which deals with everything related to rss feeds. Whether it is to add automatic tracking to a stream, or just to see the latest video released by Discord, it is this cog that will be used."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.time_loop = 20 # min minutes between two rss loops
        self.time_between_feeds_check = 0.15 # seconds between two rss checks within a loop
        self.max_messages = 20 # max messages sent per feed per loop

        self.file = "rss"
        self.embed_color = discord.Color(6017876)
        self.loop_processing = False
        self.errors_treshold = 24 * 3 # max errors allowed before disabling a feed (24h)

        self.youtube_rss = YoutubeRSS(self.bot)
        self.twitter_rss = TwitterRSS(self.bot)

        self.twitter_over_capacity = False
        self.min_time_between_posts = {
            'web': 120
        }
        self.cache = {}
        if bot.user is not None:
            self.table = 'rss_flow_beta' if bot.beta else 'rss_flow'
        # launch rss loop
        self.loop_child.change_interval(minutes=self.time_loop) # pylint: disable=no-member


    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'rss_flow_beta' if self.bot.beta else 'rss_flow'

    async def cog_load(self):
        self.loop_child.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.loop_child.cancel() # pylint: disable=no-member


    @commands.group(name="rss")
    @commands.cooldown(2,15,commands.BucketType.channel)
    async def rss_main(self, ctx: MyContext):
        """See the last post of a rss feed

        ..Doc rss.html#rss"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @rss_main.command(name="youtube",aliases=['yt'])
    async def request_yt(self, ctx: MyContext, *, channel):
        """The last video of a YouTube channel

        ..Example rss youtube UCZ5XnGb-3t7jCkXdawN2tkA

        ..Example rss youtube https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Doc rss.html#see-the-last-post"""
        if self.youtube_rss.is_youtube_url(channel):
            # apparently it's a youtube.com link
            channel = await self.youtube_rss.get_channel_by_any_url(channel)
        if channel is not None and not await self.youtube_rss.is_valid_channel(channel):
            # argument is not a channel name or ID, but it may be a custom name
            channel = self.youtube_rss.get_channel_by_custom_url(channel)
        if channel is None:
            # we couldn't get the ID based on user input
            await ctx.send(await self.bot._(ctx.channel, "rss.yt-invalid"))
            return
        text = await self.youtube_rss.get_feed(ctx.channel, channel)
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.yt-form-last")
            obj = await text[0].create_msg(form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    @rss_main.command(name="twitch",aliases=['tv'])
    async def request_twitch(self, ctx: MyContext, channel):
        """The last video of a Twitch channel

        ..Example rss twitch aureliensama

        ..Example rss tv https://www.twitch.tv/aureliensama

        ..Doc rss.html#see-the-last-post"""
        if re.match(r'^https://(www\.)?twitch\.tv/\w+', channel):
            channel = await self.parse_twitch_url(channel)
            if channel is None:
                await ctx.send(await self.bot._(ctx.channel, "rss.twitch-invalid"))
                return
        text = await self.rss_twitch(ctx.channel, channel)
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.twitch-form-last")
            obj = await text[0].create_msg(form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    @rss_main.command(name='twitter',aliases=['tw'])
    async def request_tw(self, ctx: MyContext, name):
        """The last tweet of a Twitter account

        ..Example rss twitter https://twitter.com/z_runnerr

        ..Example rss tw z_runnerr

        ..Doc rss.html#see-the-last-post"""
        if re.match(r'https://(?:www\.)?twitter\.com/', name):
            name = await self.twitter_rss.get_userid_from_url(name)
        try:
            text = await self.twitter_rss.get_feed(ctx.channel, name)
        except Exception as err:
            return self.bot.dispatch("error", err, ctx)
        if isinstance(text, str):
            await ctx.send(text)
        elif len(text) == 0:
            await ctx.send(await self.bot._(ctx.channel, "rss.tw-no-tweet"))
        else:
            form = await self.bot._(ctx.channel, "rss.tw-form-last")
            for single in text[:5]:
                obj = await single.create_msg(form)
                if isinstance(obj,discord.Embed):
                    await ctx.send(embed=obj)
                else:
                    await ctx.send(obj)

    @rss_main.command(name="web")
    async def request_web(self, ctx: MyContext, link):
        """The last post on any other rss feed

        ..Example rss web https://fr-minecraft.net/rss.php

        ..Doc rss.html#see-the-last-post"""
        link = web_link.get(link, link)
        try:
            text = await self.rss_web(ctx.channel,link)
        except client_exceptions.InvalidURL:
            await ctx.send(await self.bot._(ctx.channel, "rss.invalid-link"))
            return
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.web-form-last")
            obj = await text[0].create_msg(form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    @rss_main.command(name="deviantart",aliases=['deviant'])
    async def request_deviant(self, ctx: MyContext, user):
        """The last pictures of a DeviantArt user

        ..Example rss deviant https://www.deviantart.com/adri526

        ..Doc rss.html#see-the-last-post"""
        if re.match(r'https://(?:www\.)deviantart.com/', user):
            user = await self.parse_deviant_url(user)
        text = await self.rss_deviant(ctx.guild,user)
        if isinstance(text, str):
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel, "rss.deviant-form-last")
            obj = await text[0].create_msg(form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)


    async def is_overflow(self, guild: discord.Guild) -> tuple[bool, int]:
        """Check if a guild still has at least a slot
        True if max number reached, followed by the feed limit"""
        feed_limit = await self.bot.get_config(guild.id,'rss_max_number')
        return len(await self.db_get_guild_feeds(guild.id)) >= feed_limit, feed_limit

    @rss_main.command(name="add")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def system_add(self, ctx: MyContext, link: str):
        """Subscribe to a rss feed, displayed on this channel regularly

        ..Example rss add https://www.deviantart.com/adri526

        ..Example rss add https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Doc rss.html#follow-a-feed"""
        is_over, feed_limit = await self.is_overflow(ctx.guild)
        if is_over:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.flow-limit", limit=feed_limit))
            return
        identifiant = await self.youtube_rss.get_channel_by_any_url(link)
        feed_type = None
        if identifiant is not None:
            feed_type = 'yt'
            display_type = 'youtube'
        if identifiant is None:
            identifiant = await self.twitter_rss.get_userid_from_url(link)
            if identifiant is not None:
                feed_type = 'tw'
                display_type = 'twitter'
        if identifiant is None:
            identifiant = await self.parse_twitch_url(link)
            if identifiant is not None:
                feed_type = 'twitch'
                display_type = 'twitch'
        if identifiant is None:
            identifiant = await self.parse_deviant_url(link)
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
            await ctx.send(await self.bot._(ctx.guild,"rss.success-add", type=display_type, url=link, channel=ctx.channel.mention))
            self.bot.log.info("RSS feed added into server {} ({} - {})".format(ctx.guild.id,link,feed_id))
            await self.send_log("Feed added into server {} ({})".format(ctx.guild.id,feed_id),ctx.guild)
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, ctx)

    @rss_main.command(name="remove", aliases=["delete"])
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def systeme_rm(self, ctx: MyContext, feed_id:int=None):
        """Delete an rss feed from the list

        ..Example rss remove

        ..Doc rss.html#delete-a-followed-feed"""
        feed_ids = await self.ask_rss_id(
            feed_id,
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

    @rss_main.command(name="enable")
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def feed_enable(self, ctx: MyContext, feed_id:int=None):
        """Re-enable a disabled feed

        ..Example rss enable

        ..Doc rss.html#enable-or-disable-a-feed
        """
        feed_ids = await self.ask_rss_id(
            feed_id,
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

    @rss_main.command(name="disable")
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def feed_disable(self, ctx: MyContext, feed_id:int=None):
        """Disable a RSS feed

        ..Example rss disable

        ..Doc rss.html#enable-or-disable-a-feed
        """
        feed_ids = await self.ask_rss_id(
            feed_id,
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

    @rss_main.command(name="list")
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def list_feeds(self, ctx: MyContext):
        """Get a list of every rss/Minecraft feed

        ..Doc rss.html#see-every-feed"""
        feeds_list = await self.db_get_guild_feeds(ctx.guild.id)
        if len(feeds_list) == 0:
            # no rss feed
            await ctx.send(await self.bot._(ctx.guild.id, "rss.no-feed2"))
            return
        title = await self.bot._(ctx.guild.id, "rss.list-title", server=ctx.guild.name)
        translation = await self.bot._(ctx.guild.id, "rss.list-result")
        feeds_to_display: list[str] = []
        feeds_list.sort(key=lambda feed: feed.enabled, reverse=True)
        for feed in feeds_list:
            channel = self.bot.get_channel(feed.channel_id)
            if channel is not None:
                channel = channel.mention
            else:
                channel = str(feed.channel_id)
            # feed mentions
            if len(feed.role_ids) == 0:
                roles = await self.bot._(ctx.guild.id, "misc.none")
            else:
                roles = []
                for item in feed.role_ids:
                    role = discord.utils.get(ctx.guild.roles,id=int(item))
                    if role is not None:
                        roles.append(role.mention)
                    else:
                        roles.append(item)
                roles = ", ".join(roles)
            # feed name
            feed_name: str = feed.link
            if feed.type == 'tw' and feed.link.isnumeric():
                if tw_user := await self.twitter_rss.get_user_from_id(int(feed.link)):
                    feed_name = tw_user.screen_name
            elif feed.type == 'yt' and (channel_name := self.youtube_rss.get_channel_name_by_id(feed.link)):
                feed_name = channel_name
            if feed.enabled and not feed_name.startswith("http"):
                feed_name = f"**{feed_name}**"
            elif not feed.enabled:
                feed_name += " " + await self.bot._(ctx.guild.id, "rss.list-disabled")
            # send embed
            if len(feeds_to_display) > 20:
                embed = discord.Embed(title=title, color=self.embed_color, timestamp=ctx.message.created_at)
                embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
                for text in feeds_to_display:
                    embed.add_field(name=self.bot.zws, value=text, inline=False)
                await ctx.send(embed=embed)
                feeds_to_display.clear()
            # last post date
            if isinstance(feed.date, datetime.datetime):
                last_date = f"<t:{feed.date.timestamp():.0f}>"
            elif isinstance(feed.date, str):
                last_date = feed.date
            else:
                last_date = await self.bot._(ctx.guild.id, "misc.none")
            # append data
            feeds_to_display.append(translation.format(
                emoji=feed.get_emoji(self.bot.emojis_manager),
                channel=channel,
                link=feed_name,
                roles=roles,
                id=feed.feed_id,
                last_post=last_date
            ))
        if len(feeds_to_display) > 0:
            embed = discord.Embed(title=title, color=self.embed_color, timestamp=ctx.message.created_at)
            embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            for feed in feeds_to_display:
                embed.add_field(name=self.bot.zws, value=feed, inline=False)
            await ctx.send(embed=embed)

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
                tr_channel = channel.mention
            else:
                tr_channel = "#deleted"
            # better name format (for Twitter/YouTube ID)
            name = feed.link
            if feed.type == 'tw' and feed.link.isnumeric():
                if user := await self.twitter_rss.get_user_from_id(int(feed.link)):
                    name = user.screen_name
            elif feed.type == 'yt' and (channel_name := self.youtube_rss.get_channel_name_by_id(feed.link)):
                name = channel_name
            if len(name) > 90:
                name = name[:89] + '…'
            # emoji
            emoji = feed.get_emoji(self.bot.emojis_manager)
            options.append(discord.SelectOption(
                value=str(feed.feed_id),
                label=f"{tr_type} - {name}",
                description=f"{tr_channel} - Last post: {last_post}",
                emoji=emoji
                ))
        return options

    async def ask_rss_id(self, input_id: Optional[int], ctx: MyContext, title:str, feed_filter: Callable[[FeedObject], bool]=None, max_count: Optional[int]=1) -> Optional[list[int]]:
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
            if max_count:
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
        r = re.findall(r'((?<![\\])[\"])((?:.(?!(?<![\\])\1))*.?)\1', arg)
        if len(r) > 0:
            flatten = lambda l: [item for sublist in l for item in sublist]
            params = [[x for x in group if x != '"'] for group in r]
            return flatten(params)
        else:
            return arg.split(" ")

    @rss_main.command(name="mentions", aliases=['roles', 'mention'])
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def roles_feeds(self, ctx: MyContext, ID:int=None, *, mentions: Optional[str]):
        """Configures a role to be notified when a news is posted
        If you want to use the @everyone role, please put the server ID instead of the role name.
        
        ..Example rss mentions

        ..Example rss mentions 6678466620137

        ..Example rss mentions 6678466620137 "Announcements" "Twitch subs"

        ..Doc rss.html#mention-a-role"""
        try:
            # ask for feed IDs
            feeds_ids = await self.ask_rss_id(
                ID,
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
                    if len(feed.role_ids) > 0:
                        await self.db_update_feed(feed.feed_id, values=[('roles', '')])
                await ctx.send(await self.bot._(ctx.guild.id, "rss.roles.edit-success", count=0))
            else:
                for feed in feeds:
                    if feed.role_ids != roles_ids:
                        await self.db_update_feed(feed.feed_id, values=[('roles', ';'.join(roles_ids))])
                await ctx.send(await self.bot._(ctx.guild.id, "rss.roles.edit-success", count=len(names), roles=", ".join(names)))
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, ctx)
            return


    @rss_main.command(name="reload")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    @commands.cooldown(1,600,commands.BucketType.guild)
    async def reload_guild_feeds(self, ctx: MyContext):
        """Reload every rss feeds from your server

        ..Doc rss.html#reload-every-feed"""
        try:
            if self.loop_processing:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.loop-processing"))
                ctx.command.reset_cooldown(ctx)
                return
            start = time.time()
            msg = await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-loading", emoji=ctx.bot.emojis_manager.customs['loading']))
            feeds = [f for f in await self.db_get_guild_feeds(ctx.guild.id) if f.enabled]
            await self.main_loop(ctx.guild.id)
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-complete", count=len(feeds), time=round(time.time()-start,1)))
            await msg.delete(delay=0)
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=err))

    @rss_main.command(name="move")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def move_guild_feed(self, ctx:MyContext, ID:Optional[int]=None, channel:discord.TextChannel=None):
        """Move a rss feed in another channel

        ..Example rss move

        ..Example rss move 3078731683662

        ..Example rss move #cool-channels

        ..Example rss move 3078731683662 #cool-channels
        
        ..Doc rss.html#move-a-feed"""
        try:
            if channel is None:
                channel = ctx.channel
            try:
                feeds_ids = await self.ask_rss_id(
                    ID,
                    ctx,
                    await self.bot._(ctx.guild.id, "rss.choose-mentions-1"),
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

    @rss_main.command(name="text")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_text_feed(self, ctx: MyContext, ID: Optional[int]=None, *, text=None):
        """Change the text of an rss feed

        Available variables:
        - `{author}`: the author of the post
        - `{channel}`: the channel name (usually the same as author)
        - `{date}`: the post date (UTC)
        - `{link}` or `{url}`: a link to the post
        - `{logo}`: an emoji representing the type of post (web, Twitter, YouTube...)
        - `{mentions}`: the list of mentioned roles
        - `{title}`: the title of the post

        ..Example rss text 3078731683662

        ..Example rss text 3078731683662 {logo} | New post of {author} right here: {url}! [{date}]

        ..Example rss text

        ..Doc rss.html#change-the-text"""
        try:
            # ask for feed IDs
            feeds_ids = await self.ask_rss_id(
                ID,
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
        if text is None:
            # if no text was specified: we ask for it
            hint = await self.bot._(ctx.guild.id, "rss.change-txt")
            if len(feeds) == 1:
                hint += "\n\n" + await self.bot._(ctx.guild.id, "rss.change-txt-previous", text=feeds[0].structure)
            await ctx.send(hint)
            def check(msg: discord.Message):
                return msg.author == ctx.author and msg.channel == ctx.channel
            try:
                msg: discord.Message = await self.bot.wait_for('message', check=check,timeout=90)
            except asyncio.TimeoutError:
                return await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
            text = msg.content
        for feed in feeds:
            if feed.structure != text:
                await self.db_update_feed(feed.feed_id, [('structure', text)])
        if len(feeds) == 1:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.text-success.single", id=feed.feed_id, text=text))
        else:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.text-success.multiple", text=text))

    @rss_main.command(name="use_embed",aliases=['embed'])
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_use_embed(self, ctx: MyContext, feed_id: Optional[int] = None, value: bool = None, *, arguments: args.arguments = None):
        """Use an embed or not for a feed
        You can also provide arguments to change the color/text of the embed. Followed arguments are usable:
        - color: color of the embed (hex or decimal value)
        - title: title override, which will disable the default one (max 256 characters)
        - footer: small text displayed at the bottom of the embed

        ..Example rss embed 6678466620137 true title="hey u" footer = "Hi \\n i'm a footer"

        ..Doc rss.html#setup-a-feed-embed"""
        try:
            err = None
            try:
                feeds_ids = await self.ask_rss_id(
                    feed_id,
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
                if err is not None:
                    self.bot.dispatch("error", err, ctx)
                return
            if arguments is None or len(arguments.keys()) == 0:
                arguments = None
            feed = await self.db_get_feed(feeds_ids[0])
            values_to_update = []
            txt = []
            if value is None and arguments is None:
                await ctx.send(await self.bot._(ctx.guild.id,"rss.use_embed_" + ("true" if feed.use_embed else "false")))
                def check(msg: discord.Message):
                    try:
                        commands.converter._convert_to_bool(msg.content)
                    except commands.BadArgument:
                        return False
                    return msg.author==ctx.author and msg.channel==ctx.channel
                try:
                    msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=20)
                except asyncio.TimeoutError:
                    return await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
                value = commands.converter._convert_to_bool(msg.content)
            if value is not None and value != feed.use_embed:
                values_to_update.append(('use_embed', value))
                txt.append(await self.bot._(ctx.guild.id, "rss.use_embed-success", v=value, id=feed.feed_id))
            elif value == feed.use_embed and arguments is None:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.use_embed-same"))
                return
            if arguments is not None:
                if 'color' in arguments.keys():
                    c = await args.Color().convert(ctx, arguments['color'])
                    if c is not None:
                        values_to_update.append(('embed_color', c))
                if 'title' in arguments.keys():
                    values_to_update.append(('embed_title', arguments['title']))
                if 'footer' in arguments.keys():
                    values_to_update.append(('embed_footer', arguments['footer']))
                txt.append(await self.bot._(ctx.guild.id, "rss.embed-json-changed"))
            if len(values_to_update) > 0:
                await self.db_update_feed(feed.feed_id, values_to_update)
            await ctx.send("\n".join(txt))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "rss.guild-error", err=err))
            self.bot.dispatch("error", err, ctx)

    @rss_main.command(name="test")
    @commands.check(checks.is_support_staff)
    async def test_rss(self, ctx: MyContext, url, *, args=None):
        """Test if an rss feed is usable"""
        url = url.replace('<','').replace('>','')
        feeds = await feed_parse(self.bot, url, 8)
        txt = f"feeds.keys()\n```py\n{feeds.keys()}\n```"
        if 'bozo_exception' in feeds.keys():
            txt += f"\nException ({feeds['bozo']}): {feeds['bozo_exception']}"
            return await ctx.send(txt)
        if len(str(feeds.feed)) < 1400-len(txt):
            txt += f"feeds.feed\n```py\n{feeds.feed}\n```"
        else:
            txt += f"feeds.feed.keys()\n```py\n{feeds.feed.keys()}\n```"
        if len(feeds.entries) > 0:
            if len(str(feeds.entries[0])) < 1950-len(txt):
                txt += f"feeds.entries[0]\n```py\n{feeds.entries[0]}\n```"
            else:
                txt += f"feeds.entries[0].keys()\n```py\n{feeds.entries[0].keys()}\n```"
        if args is not None and 'feeds' in args and 'ctx' not in args:
            txt += "\n{}\n```py\n{}\n```".format(args, eval(args))
        try:
            await ctx.send(txt)
        except discord.DiscordException as err:
            print("[rss_test] Error:",err)
            await ctx.send("`Error`: "+str(err))
            print(txt)
        if args is None:
            ok = '<:greencheck:513105826555363348>'
            notok = '<:redcheck:513105827817717762>'
            nothing = '<:_nothing:446782476375949323>'
            txt = ['**__Analyse :__**','']
            yt = await self.youtube_rss.get_channel_by_any_url(feeds.feed['link'])
            if yt is None:
                tw = self.twitter_rss.is_twitter_url(feeds.feed['link'])
                if tw is not None:
                    txt.append(f"<:twitter:958325391196585984>  {tw}")
                elif 'link' in feeds.feed.keys():
                    txt.append(f":newspaper:  <{feeds.feed['link']}>")
                else:
                    txt.append(":newspaper:  No 'link' var")
            else:
                txt.append("<:youtube:447459436982960143>  "+yt)
            txt.append("Entrées : {}".format(len(feeds.entries)))
            if len(feeds.entries) > 0:
                entry = feeds.entries[0]
                if 'title' in entry.keys():
                    txt.append(nothing+ok+" title: ")
                    if len(entry['title'].split('\n')) > 1:
                        txt[-1] += entry['title'].split('\n')[0]+"..."
                    else:
                        txt[-1] += entry['title']
                else:
                    txt.append(nothing+notok+' title')
                if 'published_parsed' in entry.keys():
                    txt.append(nothing+ok+" published_parsed")
                elif 'published' in entry.keys():
                    txt.append(nothing+ok+" published")
                elif 'updated_parsed' in entry.keys():
                    txt.append(nothing+ok+" updated_parsed")
                else:
                    txt.append(nothing+notok+' date')
                if 'author' in entry.keys():
                    txt.append(nothing+ok+" author: "+entry['author'])
                else:
                    txt.append(nothing+notok+' author')
            await ctx.send("\n".join(txt))

    async def check_rss_url(self, url: str):
        "Check if a given URL is a valid rss feed"
        r = self.youtube_rss.is_youtube_url(url)
        if r is not None:
            return True
        r = self.twitter_rss.is_twitter_url(url)
        if r is not None:
            return True
        r = await self.parse_twitch_url(url)
        if r is not None:
            return True
        r = await self.parse_deviant_url(url)
        if r is not None:
            return True
        try:
            f = await feed_parse(self.bot, url, 8)
            _ = f.entries[0]
            return True
        except IndexError:
            return False


    async def parse_twitch_url(self, url):
        r = r'(?:http.*://)?(?:www\.)?(?:twitch\.tv/)([^?\s]+)'
        match = re.search(r,url)
        if match is None:
            return None
        else:
            return match.group(1)

    async def parse_deviant_url(self, url):
        r = r'(?:http.*://)?(?:www\.)?(?:deviantart\.com/)([^?\s]+)'
        match = re.search(r,url)
        if match is None:
            return None
        else:
            return match.group(1)


    async def rss_twitch(self, channel: discord.TextChannel, name: str, date: datetime.datetime=None, session: ClientSession=None):
        url = 'https://twitchrss.appspot.com/vod/' + name
        feeds = await feed_parse(self.bot, url, 5, session)
        if feeds is None:
            return await self.bot._(channel, "rss.research-timeout")
        if len(feeds.entries) == 0:
            return await self.bot._(channel, "rss.nothing")
        if not date:
            feed: dict = feeds.entries[0]
            r = re.search(r'<img src="([^"]+)" />',feed['summary'])
            img_url = None
            if r is not None:
                img_url = r.group(1)
            obj = RssMessage(
                bot=self.bot,
                feed=FeedObject.unrecorded("twitch", channel.guild.id if channel.guild else None, channel.id),
                url=feed['link'],
                title=feed['title'],
                date=feed['published_parsed'],
                author=feeds.feed['title'].replace("'s Twitch video RSS",""),
                image=img_url,
                channel=name
            )
            return [obj]
        else:
            liste = []
            for feed in feeds.entries:
                if len(liste) > 10:
                    break
                if datetime.datetime(*feed['published_parsed'][:6]) <= date:
                    break
                r = re.search(r'<img src="([^"]+)" />',feed['summary'])
                img_url = None
                if r is not None:
                    img_url = r.group(1)
                obj = RssMessage(
                    bot=self.bot,
                    feed=FeedObject.unrecorded("twitch", channel.guild.id if channel.guild else None, channel.id),
                    url=feed['link'],
                    title=feed['title'],
                    date=feed['published_parsed'],
                    author=feeds.feed['title'].replace("'s Twitch video RSS",""),
                    image=img_url,
                    channel=name
                )
                liste.append(obj)
            liste.reverse()
            return liste

    async def rss_web(self, channel: discord.TextChannel, url: str, date: datetime.datetime=None, session: ClientSession=None):
        if url == 'help':
            return await self.bot._(channel, "rss.web-help")
        feeds = await feed_parse(self.bot, url, 9, session)
        if feeds is None:
            return await self.bot._(channel, "rss.research-timeout")
        if 'bozo_exception' in feeds.keys() or len(feeds.entries) == 0:
            return await self.bot._(channel, "rss.web-invalid")
        published = None
        for i in ['updated_parsed', 'published_parsed', 'published']:
            if i in feeds.entries[0].keys() and feeds.entries[0][i] is not None:
                published = i
                break
        if published is not None and len(feeds.entries) > 1:
            try:
                while (len(feeds.entries) > 1)  and (feeds.entries[1][published] is not None) and (feeds.entries[0][published] < feeds.entries[1][published]):
                    del feeds.entries[0]
            except KeyError:
                pass
        if not date or published not in ['published_parsed','updated_parsed']:
            feed = feeds.entries[0]
            if published is None:
                datz = 'Unknown'
            else:
                datz = feed[published]
            if 'link' in feed.keys():
                l = feed['link']
            elif 'link' in feeds.keys():
                l = feeds['link']
            else:
                l = url
            if 'author' in feed.keys():
                author = feed['author']
            elif 'author' in feeds.keys():
                author = feeds['author']
            elif 'title' in feeds['feed'].keys():
                author = feeds['feed']['title']
            else:
                author = '?'
            if 'title' in feed.keys():
                title = feed['title']
            elif 'title' in feeds.keys():
                title = feeds['title']
            else:
                title = '?'
            img = None
            r = re.search(r'(http(s?):)([/|.\w\s-])*\.(?:jpe?g|gif|png|webp)', str(feed))
            if r is not None:
                img = r.group(0)
            obj = RssMessage(
                bot=self.bot,
                feed=FeedObject.unrecorded("web", channel.guild.id if channel.guild else None, channel.id),
                url=l,
                title=title,
                date=datz,
                author=author,
                channel=feeds.feed['title'] if 'title' in feeds.feed.keys() else '?',
                image=img)
            return [obj]
        else: # published in ['published_parsed','updated_parsed']
            liste = list()
            for feed in feeds.entries:
                if len(liste)>10:
                    break
                try:
                    datz = feed[published]
                    if feed[published] is None or (datetime.datetime(*feed[published][:6]) - date).total_seconds() < self.min_time_between_posts['web']:
                        break
                    if 'link' in feed.keys():
                        l = feed['link']
                    elif 'link' in feeds.keys():
                        l = feeds['link']
                    else:
                        l = url
                    if 'author' in feed.keys():
                        author = feed['author']
                    elif 'author' in feeds.keys():
                        author = feeds['author']
                    elif 'title' in feeds['feed'].keys():
                        author = feeds['feed']['title']
                    else:
                        author = '?'
                    if 'title' in feed.keys():
                        title = feed['title']
                    elif 'title' in feeds.keys():
                        title = feeds['title']
                    else:
                        title = '?'
                    img = None
                    r = re.search(r'(http(s?):)([/|.\w\s-])*\.(?:jpe?g|gif|png|webp)', str(feed))
                    if r is not None:
                        img = r.group(0)
                    obj = RssMessage(
                        bot=self.bot,
                        feed=FeedObject.unrecorded("web", channel.guild.id if channel.guild else None, channel.id),
                        url=l,
                        title=title,
                        date=datz,
                        author=author,
                        channel=feeds.feed['title'] if 'title' in feeds.feed.keys() else '?',
                        image=img)
                    liste.append(obj)
                except:
                    pass
            liste.reverse()
            return liste


    async def rss_deviant(self, guild: discord.Guild, nom: str, date: datetime.datetime=None, session: ClientSession=None):
        url = 'https://backend.deviantart.com/rss.xml?q=gallery%3A'+nom
        feeds = await feed_parse(self.bot, url, 5, session)
        if feeds is None:
            return await self.bot._(guild, "rss.research-timeout")
        if len(feeds.entries) == 0:
            return await self.bot._(guild, "rss.nothing")
        if not date:
            feed = feeds.entries[0]
            img_url = feed['media_content'][0]['url'] if "media_content" in feed else None
            title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feeds.feed['title']).group(1)
            obj = RssMessage(
                bot=self.bot,
                feed=FeedObject.unrecorded("deviant", guild.id if guild else None),
                url=feed['link'],
                title=feed['title'],
                date=feed['published_parsed'],
                author=title,
                image=img_url
            )
            return [obj]
        else:
            liste = []
            for feed in feeds.entries:
                if datetime.datetime(*feed['published_parsed'][:6]) <= date:
                    break
                img_url = feed['media_content'][0]['url'] if "media_content" in feed else None
                title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feeds.feed['title']).group(1)
                obj = RssMessage(
                    bot=self.bot,
                    feed=FeedObject.unrecorded("deviant", guild.id if guild else None),
                    url=feed['link'],
                    title=feed['title'],
                    date=feed['published_parsed'],
                    author=title,
                    image=img_url
                )
                liste.append(obj)
            liste.reverse()
            return liste



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
        query = "INSERT INTO `{}` (`ID`, `guild`, `channel`, `type`, `link`, `structure`) VALUES (%(i)s, %(g)s, %(c)s, %(t)s, %(l)s, %(f)s)".format(self.table)
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
            query += " WHERE `guild` in (" + ','.join(["'{}'".format(x.id) for x in self.bot.guilds]) + ")"
        async with self.bot.db_query(query, fetchone=True) as query_results:
            t = query_results['count']
        return t

    async def db_update_feed(self, feed_id: int, values=None):
        "Update a field values"
        values = values if values is not None else [(None, None)]
        if self.bot.zombie_mode:
            return
        set_query = ', '.join('{}=%s'.format(val[0]) for val in values)
        query = """UPDATE `{t}` SET {v} WHERE `ID`={id}""".format(t=self.table, v=set_query, id=feed_id)
        async with self.bot.db_query(query, (val[1] for val in values)):
            pass

    async def db_increment_errors(self, working_ids: list[int], broken_ids: list[int]) -> int:
        "Increments recent_errors value by 1 for each of these IDs, and set it to 0 for the others"
        if self.bot.zombie_mode:
            return
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

    async def db_set_active_guilds(self, active_guild_ids: list[int]):
        "DEPRECATED - Mark any guild in the list as an active guild, and every other as inactive (ie. the bot has no access to them anymore)"
        if self.bot.zombie_mode:
            return
        ids_list = ', '.join(map(str, active_guild_ids))
        query = f"UPDATE `{self.table}` SET `active_guild` = 0 WHERE `guild` NOT IN ({ids_list})"
        async with self.bot.db_query(query, returnrowcount=True) as query_results:
            self.bot.log.info("[rss] set guild as inactive for %s feeds", query_results)
        query = f"UPDATE `{self.table}` SET `active_guild` = 1 WHERE `guild` IN ({ids_list})"
        async with self.bot.db_query(query, returnrowcount=True) as query_results:
            if query_results:
                self.bot.log.info("[rss] set guild as active for %s feeds", query_results)

    async def db_set_last_refresh(self, feed_ids: list[int]):
        "Update the last_refresh field for the given feed IDs"
        if self.bot.zombie_mode:
            return
        ids_list = ', '.join(map(str, feed_ids))
        query = f"UPDATE `{self.table}` SET `last_refresh` = %s WHERE `ID` IN ({ids_list})"
        async with self.bot.db_query(query, (datetime.datetime.utcnow(),), returnrowcount=True) as query_results:
            self.bot.log.info("[rss] set last refresh for %s feeds", query_results)

    async def send_rss_msg(self, obj: "RssMessage", channel: Union[discord.TextChannel, discord.Thread], roles: list[str], send_stats):
        "Send a RSS message into its Discord channel, with the corresponding mentions"
        t = await obj.create_msg()
        mentions = []
        for item in roles:
            if item == '':
                continue
            role = discord.utils.get(channel.guild.roles,id=int(item))
            if role is not None:
                mentions.append(role)
        if self.bot.zombie_mode:
            return
        allowed_mentions = discord.AllowedMentions(everyone=False, roles=True)
        try:
            if isinstance(t, discord.Embed):
                await channel.send(" ".join(obj.mentions), embed=t, allowed_mentions=allowed_mentions)
            else:
                await channel.send(t, allowed_mentions=allowed_mentions)
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
                self.bot.dispatch("server_warning", ServerWarningType.RSS_UNKNOWN_CHANNEL, guild, channel_id=feed.channel_id, feed_id=feed.feed_id)
                return False
            if feed.link in self.cache:
                objs = self.cache[feed.link]
            else:
                if feed.type == "yt":
                    objs = await self.youtube_rss.get_feed(chan, feed.link, feed.date, session)
                elif feed.type == "tw":
                    objs = await self.twitter_rss.get_feed(chan, feed.link, feed.date)
                else:
                    funct = getattr(self, f"rss_{feed.type}")
                    objs: Union[str, list[RssMessage]] = await funct(chan, feed.link, feed.date, session=session)
                if isinstance(objs, twitter.error.TwitterError):
                    self.twitter_over_capacity = True
                    self.bot.log.warning("[send_rss_msg] Twitter over capacity detected")
                    return False
                self.cache[feed.link] = objs
            if isinstance(objs, twitter.TwitterError):
                await self.bot.get_user(279568324260528128).send(f"[send_rss_msg] twitter error dans `await check_feed(): {objs}`")
                raise objs
            if isinstance(objs, (str, type(None), int)) or len(objs) == 0:
                return True
            elif isinstance(objs, list):
                latest_post_date = None
                for obj in objs[:self.max_messages]:
                    # if the guild was marked as inactive (ie the bot wasn't there in the previous loop),
                    #  mark the feeds as completed but do not send any message, to avoid spamming channels
                    if feed.has_recently_been_refreshed():
                        # if we can't post messages: abort
                        if not chan.permissions_for(guild.me).send_messages:
                            self.bot.dispatch("server_warning", ServerWarningType.RSS_MISSING_TXT_PERMISSION, guild, channel=chan, feed_id=feed.feed_id)
                            return False
                        # same if we need to be able to send embeds
                        if feed.use_embed and not chan.permissions_for(guild.me).embed_links:
                            self.bot.dispatch("server_warning", ServerWarningType.RSS_MISSING_EMBED_PERMISSION, guild, channel=chan, feed_id=feed.feed_id)
                            return False
                        obj.feed = feed
                        obj.fill_embed_data()
                        await obj.fill_mention(guild)
                        await self.send_rss_msg(obj, chan, feed.role_ids, send_stats)
                    latest_post_date = obj.date
                if isinstance(latest_post_date, datetime.datetime):
                    await self.db_update_feed(feed.feed_id, [('date', latest_post_date)],)
                return True
            else:
                return True
        except Exception as err:
            error_msg = f"Erreur rss sur le flux {feed.feed_id} (type {feed.type} - salon {feed.channel_id} - id {feed.feed_id})"
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

    async def main_loop(self, guild_id: int=None):
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
        success_ids: list[int] = []
        errors_ids: list[int] = []
        checked_count = 0
        if guild_id is None:
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats['messages'] = 0
                statscog.rss_stats['warnings'] = 0
        session = ClientSession()
        for feed in feeds_list:
            if not feed.enabled:
                continue
            try:
                if feed.type == 'tw' and self.twitter_over_capacity:
                    continue
                checked_count += 1
                if feed.type == 'mc':
                    if await self.bot.get_cog('Minecraft').check_feed(feed, send_stats=(guild_id is None)):
                        success_ids.append(feed.feed_id)
                    else:
                        errors_ids.append(feed.feed_id)
                else:
                    if await self.check_feed(feed, session, send_stats=(guild_id is None)):
                        success_ids.append(feed.feed_id)
                    else:
                        errors_ids.append(feed.feed_id)
            except Exception as err:
                self.bot.dispatch("error", err, f"RSS feed {feed.feed_id}")
            await asyncio.sleep(self.time_between_feeds_check)
        await session.close()
        self.bot.get_cog('Minecraft').feeds.clear()
        desc = [f"**RSS loop done** in {time.time()-start:.3f}s ({len(success_ids)}/{checked_count} feeds)"]
        if guild_id is None:
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats["checked"] = checked_count
                statscog.rss_stats["errors"] = len(errors_ids)
            # await self.db_set_active_guilds(set(feed.guild_id for feed in feeds_list))
            await self.db_set_last_refresh(set(feed.feed_id for feed in feeds_list))
        if len(errors_ids) > 0:
            desc.append(f"{len(errors_ids)} errors: {' '.join(str(x) for x in errors_ids)}")
            # update errors count in database
            await self.db_increment_errors(working_ids=success_ids, broken_ids=errors_ids)
            # disable feeds that have too many errors
            await self.disabled_feeds_check([feed for feed in feeds_list if feed.feed_id in errors_ids])
        emb = discord.Embed(description='\n'.join(desc), color=1655066, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")
        self.bot.log.debug(desc[0])
        if len(errors_ids) > 0:
            self.bot.log.warning("[rss] "+desc[1])
        if guild_id is None:
            self.loop_processing = False
        self.twitter_over_capacity = False
        self.cache.clear()

    @tasks.loop(minutes=20)
    async def loop_child(self):
        "Main method that call the loop method once every 20min - considering RSS is enabled and working"
        if not self.bot.rss_enabled:
            return
        if not self.bot.database_online:
            self.bot.log.warning('Base de donnée hors ligne - check rss annulé')
            return
        self.bot.log.info(" Boucle rss commencée !")
        start_time = time.time()
        try:
            await self.main_loop()
        except Exception as err:
            self.bot.dispatch("error", err, "RSS main loop")
        else:
            self.bot.log.info(f" Boucle rss terminée en {time.time() - start_time:.2f}s!")

    @loop_child.before_loop
    async def before_printer(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()

    @loop_child.error
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
                self.loop_child.start() # pylint: disable=no-member
            except RuntimeError:
                await ctx.send("La boucle est déjà en cours !")
            else:
                await ctx.send("Boucle rss relancée !")
        elif new_state == "stop":
            self.loop_child.cancel() # pylint: disable=no-member
            self.bot.log.info(" Boucle rss arrêtée de force par un admin")
            await ctx.send("Boucle rss arrêtée de force !")
        elif new_state == "once":
            if self.loop_processing:
                await ctx.send("Une boucle rss est déjà en cours !")
            else:
                await ctx.send("Et hop ! Une itération de la boucle en cours !")
                self.bot.log.info(" Boucle rss forcée")
                await self.main_loop()

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
