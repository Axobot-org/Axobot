import asyncio
import datetime
import importlib
import random
import re
import time
from typing import Optional

import discord
import mysql
import twitter
from aiohttp import ClientSession, client_exceptions
from discord.ext import commands, tasks
from libs.classes import MyContext, Zbot
from libs.formatutils import FormatUtils
from libs.rss import RssMessage, feed_parse, TwitterRSS, YoutubeRSS

from fcts import args, checks
from libs.rss.rss_general import FeedSelectView, get_emoji

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
    if ctx.guild is None:
        return False
    return ctx.channel.permissions_for(ctx.author).manage_guild or await ctx.bot.get_cog("Admin").check_if_admin(ctx)


class Rss(commands.Cog):
    """Cog which deals with everything related to rss flows. Whether it is to add automatic tracking to a stream, or just to see the latest video released by Discord, it is this cog that will be used."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.time_loop = 20 # min minutes between two rss loops
        self.time_between_flows_check = 0.15 # seconds between two rss checks within a loop
        self.max_messages = 20 # max messages sent per flow per loop

        self.file = "rss"
        self.embed_color = discord.Color(6017876)
        self.loop_processing = False
        self.last_update = None

        self.youtube_rss = YoutubeRSS(self.bot)
        self.twitter_rss = TwitterRSS(self.bot)

        self.twitter_over_capacity = False
        self.min_time_between_posts = {
            'web': 120
        }
        self.cache = {}
        if bot.user is not None:
            self.table = 'rss_flow' if bot.user.id==486896267788812288 else 'rss_flow_beta'
        # launch rss loop
        self.loop_child.change_interval(minutes=self.time_loop) # pylint: disable=no-member


    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'rss_flow' if self.bot.user.id==486896267788812288 else 'rss_flow_beta'

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
            await self.bot.get_cog('Help').help_command(ctx,['rss'])

    @rss_main.command(name="youtube",aliases=['yt'])
    async def request_yt(self, ctx: MyContext, channel):
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
        if re.match(r'https://(?:www\.)twitch.tv/', channel):
            channel = await self.parse_twitch_url(channel)
        text = await self.rss_twitch(ctx.channel,channel)
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
            text = await self.twitter_rss.get_feed(ctx.channel,name)
        except Exception as err:
            return await self.bot.get_cog('Errors').on_error(err,ctx)
        if isinstance(text, str):
            await ctx.send(text)
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
        if link in web_link.keys():
            link = web_link[link]
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
        True if max number reached, followed by the flow limit"""
        flow_limit = await self.bot.get_config(guild.id,'rss_max_number')
        if flow_limit is None:
            flow_limit = self.bot.get_cog('Servers').default_opt['rss_max_number']
        return len(await self.get_guild_flows(guild.id)) >= flow_limit, flow_limit

    @rss_main.command(name="add")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def system_add(self, ctx: MyContext, link: str):
        """Subscribe to a rss feed, displayed on this channel regularly

        ..Example rss add https://www.deviantart.com/adri526

        ..Example rss add https://www.youtube.com/channel/UCZ5XnGb-3t7jCkXdawN2tkA

        ..Doc rss.html#follow-a-feed"""
        is_over, flow_limit = await self.is_overflow(ctx.guild)
        if is_over:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.flow-limit", limit=flow_limit))
            return
        identifiant = await self.youtube_rss.get_channel_by_any_url(link)
        flow_type = None
        if identifiant is not None:
            flow_type = 'yt'
            display_type = 'youtube'
        if identifiant is None:
            identifiant = await self.twitter_rss.get_userid_from_url(link)
            if identifiant is not None:
                flow_type = 'tw'
                display_type = 'twitter'
        if identifiant is None:
            identifiant = await self.parse_twitch_url(link)
            if identifiant is not None:
                flow_type = 'twitch'
                display_type = 'twitch'
        if identifiant is None:
            identifiant = await self.parse_deviant_url(link)
            if identifiant is not None:
                flow_type = 'deviant'
                display_type = 'deviantart'
        if identifiant is not None and not link.startswith("https://"):
            link = "https://"+link
        if identifiant is None and link.startswith("http"):
            identifiant = link
            flow_type = "web"
            display_type = 'website'
        elif not link.startswith("http"):
            await ctx.send(await self.bot._(ctx.guild, "rss.invalid-link"))
            return
        if flow_type is None or not await self.check_rss_url(link):
            return await ctx.send(await self.bot._(ctx.guild.id, "rss.invalid-flow"))
        try:
            flow_id = await self.add_flow(ctx.guild.id,ctx.channel.id,flow_type,identifiant)
            await ctx.send(await self.bot._(ctx.guild,"rss.success-add", type=display_type, url=link, channel=ctx.channel.mention))
            self.bot.log.info("RSS feed added into server {} ({} - {})".format(ctx.guild.id,link,flow_id))
            await self.send_log("Feed added into server {} ({})".format(ctx.guild.id,flow_id),ctx.guild)
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
            await self.bot.get_cog("Errors").on_error(e,ctx)

    @rss_main.command(name="remove",aliases=['delete'])
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def systeme_rm(self, ctx: MyContext, ID:int=None):
        """Delete an rss feed from the list

        ..Example rss remove

        ..Doc rss.html#delete-a-followed-feed"""
        flows = await self.ask_rss_id(ID,
                                ctx,
                                await self.bot._(ctx.guild.id, "rss.choose-delete"),
                                include_mc=True,
                                max_count=None
                                )
        if flows is None:
            return
        for flow in flows:
            await self.remove_flow(flow)
        await ctx.send(await self.bot._(ctx.guild, "rss.delete-success", count=len(flows)))
        ids = ', '.join(map(str, flows))
        self.bot.log.info(f"RSS feed deleted into server {ctx.guild.id} ({ids})")
        await self.send_log(f"Feed deleted into server {ctx.guild.id} ({ids})", ctx.guild)

    @rss_main.command(name="list")
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def list_flows(self, ctx: MyContext):
        """Get a list of every rss/Minecraft feed

        ..Doc rss.html#see-every-feed"""
        flows_list = await self.get_guild_flows(ctx.guild.id)
        if len(flows_list) == 0:
            # no rss feed
            await ctx.send(await self.bot._(ctx.guild.id, "rss.no-feed2"))
            return
        title = await self.bot._(ctx.guild.id, "rss.list-title", server=ctx.guild.name)
        translation = await self.bot._(ctx.guild.id, "rss.list-result")
        flows_to_display: list[str] = []
        for flow in flows_list:
            channel = self.bot.get_channel(flow['channel'])
            if channel is not None:
                channel = channel.mention
            else:
                channel = flow['channel']
            # flow mentions
            if flow['roles'] == '':
                roles = await self.bot._(ctx.guild.id, "misc.none")
            else:
                roles = []
                for item in flow['roles'].split(';'):
                    role = discord.utils.get(ctx.guild.roles,id=int(item))
                    if role is not None:
                        roles.append(role.mention)
                    else:
                        roles.append(item)
                roles = ", ".join(roles)
            # flow name
            flow_name: str = flow['link']
            if flow['type'] == 'tw' and flow['link'].isnumeric():
                if tw_user := await self.twitter_rss.get_user_from_id(int(flow['link'])):
                    flow_name = tw_user.screen_name
            elif flow['type'] == 'yt' and (channel_name := self.youtube_rss.get_channel_name_by_id(flow['link'])):
                flow_name = channel_name
            # send embed
            if len(flows_to_display) > 20:
                embed = discord.Embed(title=title, color=self.embed_color, timestamp=ctx.message.created_at)
                embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
                for text in flows_to_display:
                    embed.add_field(name=self.bot.zws, value=text, inline=False)
                await ctx.send(embed=embed)
                flows_to_display.clear()
            if flow['date']:
                last_date = f"<t:{flow['date'].timestamp():.0f}>"
            else:
                last_date = await self.bot._(ctx.guild.id, "misc.none")
            flows_to_display.append(translation.format(
                emoji=get_emoji(self.bot.get_cog('Emojis'), flow['type']),
                channel=channel,
                link=flow_name if flow_name.startswith('https') else f"**{flow_name}**",
                roles=roles,
                id=flow['ID'],
                last_post=last_date
            ))
        if len(flows_to_display) > 0:
            embed = discord.Embed(title=title, color=self.embed_color, timestamp=ctx.message.created_at)
            embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            for flow in flows_to_display:
                embed.add_field(name=self.bot.zws, value=flow, inline=False)
            await ctx.send(embed=embed)

    async def ask_rss_id(self, input_id: Optional[int], ctx: MyContext, title:str, include_mc: bool=False, max_count:int=1) -> Optional[list[int]]:
        "Ask the user to select a feed ID"
        selection = []
        if input_id is not None:
            input_flow = await self.get_flow(input_id)
            if not input_flow or str(input_flow['guild']) != str(ctx.guild.id):
                input_id = None
            elif (not include_mc) and input_flow['type']=='mc':
                input_id = None
            else:
                selection = [input_flow['ID']]
        if input_id is None:
            guild_feeds = await self.get_guild_flows(ctx.guild.id)
            if len(guild_feeds) == 0:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.no-feed"))
                return
            if not include_mc:
                guild_feeds = [f for f in guild_feeds if f['type']!='mc']
            for feed in guild_feeds:
                # better type format
                feed['tr_type'] = await self.bot._(ctx.guild.id, "rss."+feed['type'])
                feed['tr_lastpost'] = await FormatUtils.date(feed['date'], lang=await self.bot._(ctx.channel,'_used_locale'), year=True, digital=True)
                if channel := ctx.guild.get_channel(feed['channel']):
                    feed['tr_channel'] = "#"+channel.name
                else:
                    feed['tr_channel'] = "#deleted"
                # better name format (for Twitter/YouTube ID)
                feed['name'] = feed['link']
                if feed['type'] == 'tw' and feed['link'].isnumeric():
                    if user := await self.twitter_rss.get_user_from_id(int(feed['link'])):
                        feed['name'] = user.screen_name
                elif feed['type'] == 'yt' and (channel_name := self.youtube_rss.get_channel_name_by_id(feed['link'])):
                    feed['name'] = channel_name
                # emoji
                feed['emoji'] = get_emoji(self.bot.get_cog('Emojis'), feed['type'])
            form_placeholder = await self.bot._(ctx.channel, 'rss.picker-placeholder')
            view = FeedSelectView(guild_feeds, max_count or len(guild_feeds), form_placeholder)
            await ctx.send(title, view=view)
            await view.wait()
            if view.feeds is None:
                return
            try:
                selection = list(map(int, view.feeds))
            except ValueError:
                selection = []  
        if len(selection) == 0:
            await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
            return
        return selection

    def parse_output(self, arg):
        r = re.findall(r'((?<![\\])[\"])((?:.(?!(?<![\\])\1))*.?)\1', arg)
        if len(r) > 0:
            flatten = lambda l: [item for sublist in l for item in sublist]
            params = [[x for x in group if x != '"'] for group in r]
            return flatten(params)
        else:
            return arg.split(" ")

    @rss_main.command(name="roles", aliases=['mentions', 'mention'])
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def roles_flows(self, ctx: MyContext, ID:int=None, *, mentions: Optional[str]):
        """Configures a role to be notified when a news is posted
        If you want to use the @everyone role, please put the server ID instead of the role name.
        
        ..Example rss mentions

        ..Example rss mentions 6678466620137

        ..Example rss mentions 6678466620137 "Announcements" "Twitch subs"

        ..Doc rss.html#mention-a-role"""
        try:
            # ask for flow ID
            flows = await self.ask_rss_id(ID,
                                    ctx,
                                    await self.bot._(ctx.guild.id, "rss.choose-mentions-1"))
        except Exception as e:
            flows = []
            await self.bot.get_cog("Errors").on_error(e,ctx)
        if flows is None:
            return
        if len(flows) == 0:
            await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
            return
        flow = await self.get_flow(flows[0])
        no_role = ['aucun','none','_','del']
        if mentions is None: # if no roles was specified: we ask for them
            if flow['roles'] == '':
                text = await self.bot._(ctx.guild.id, "rss.no-roles")
            else:
                r = []
                for item in flow['roles'].split(';'):
                    role = discord.utils.get(ctx.guild.roles,id=int(item))
                    if role is not None:
                        r.append(role.mention)
                    else:
                        r.append(item)
                r = ", ".join(r)
                text = await self.bot._(ctx.guild.id,"rss.roles.list", roles=r)
            # ask for roles
            embed = discord.Embed(title=await self.bot._(ctx.guild.id, "rss.choose-roles"), color=discord.Colour(0x77ea5c), description=text, timestamp=ctx.message.created_at)
            emb_msg = await ctx.send(embed=embed)

            cond = False
            while not cond:
                try:
                    msg: discord.Message = await self.bot.wait_for('message',
                        check=lambda msg: msg.author==ctx.author, timeout=30.0)
                    if msg.content.lower() in no_role: # if no role should be mentionned
                        IDs = [None]
                    else:
                        l = self.parse_output(msg.content)
                        IDs = list()
                        Names = list()
                        for x in l:
                            x = x.strip()
                            try:
                                r = await commands.RoleConverter().convert(ctx,x)
                                IDs.append(str(r.id))
                                Names.append(r.name)
                            except commands.ConversionError:
                                await ctx.send(await self.bot._(ctx.guild.id, "rss.roles.cant-find"))
                                IDs = []
                                break
                    if len(IDs) > 0:
                        cond = True
                except asyncio.TimeoutError:
                    await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
                    await emb_msg.delete(delay=0)
                    return
        else: # if roles were specified
            if mentions in no_role: # if no role should be mentionned
                IDs = [None]
            else: # we need to parse the output
                params = self.parse_output(mentions)
                IDs = list()
                Names = list()
                for x in params:
                    try:
                        r = await commands.RoleConverter().convert(ctx,x)
                        IDs.append(str(r.id))
                        Names.append(r.name)
                    except commands.errors.BadArgument:
                        pass
                if len(IDs) == 0:
                    await ctx.send(await self.bot._(ctx.guild.id,"rss.roles.cant-find"))
                    return
        try:
            if IDs[0] is None:
                await self.update_flow(flow['ID'],values=[('roles','')])
                await ctx.send(await self.bot._(ctx.guild.id,"rss.roles.edit-success", count=0))
            else:
                await self.update_flow(flow['ID'],values=[('roles',';'.join(IDs))])
                txt = await self.bot.get_cog("Utilities").clear_msg(", ".join(Names))
                await ctx.send(await self.bot._(ctx.guild.id,"rss.roles.edit-success", count=len(Names), roles=txt))
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
            await self.bot.get_cog("Errors").on_error(e,ctx)
            return


    @rss_main.command(name="reload")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    @commands.cooldown(1,600,commands.BucketType.guild)
    async def reload_guild_flows(self, ctx: MyContext):
        """Reload every rss feeds from your server
        
        ..Doc rss.html#reload-every-feed"""
        try:
            if self.loop_processing:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.loop-processing"))
                ctx.command.reset_cooldown(ctx)
                return
            t = time.time()
            msg = await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-loading", emoji=ctx.bot.get_cog('Emojis').customs['loading']))
            liste = await self.get_guild_flows(ctx.guild.id)
            await self.main_loop(ctx.guild.id)
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-complete", count=len(liste),time=round(time.time()-t,1)))
            await msg.delete(delay=0)
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=e))

    @rss_main.command(name="move")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def move_guild_flow(self, ctx:MyContext, ID:Optional[int]=None, channel:discord.TextChannel=None):
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
                flows = await self.ask_rss_id(ID, ctx, await self.bot._(ctx.guild.id, "rss.choose-mentions-1"), max_count=None)
                e = None
            except Exception as e:
                flows = []
            if flows is None:
                return
            if len(flows) == 0:
                await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
                if e is not None:
                    await self.bot.get_cog("Errors").on_error(e,ctx)
                return
            for flow in flows:
                await self.update_flow(flow,[('channel',channel.id)])
            await ctx.send(await self.bot._(ctx.guild.id,"rss.move-success", count=len(flows), channel=channel.mention))
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=e))

    @rss_main.command(name="text")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_text_flow(self, ctx: MyContext, ID: Optional[int]=None, *, text=None):
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
            try:
                flows = await self.ask_rss_id(ID,
                                        ctx,
                                        await self.bot._(ctx.guild.id, "rss.choose-mentions-1"))
            except Exception as e:
                flows = []
            if flows is None:
                return
            if len(flows) == 0:
                await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
                return
            flow = await self.get_flow(flows[0])
            if text is None:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.change-txt", text=flow['structure']))
                def check(msg: discord.Message):
                    return msg.author==ctx.author and msg.channel==ctx.channel
                try:
                    msg = await self.bot.wait_for('message', check=check,timeout=90)
                except asyncio.TimeoutError:
                    return await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
                text = msg.content
            await self.update_flow(flow['ID'],[('structure',text)])
            await ctx.send(await self.bot._(ctx.guild.id,"rss.text-success", id=flow['ID'], text=text))
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=e))
            await ctx.bot.get_cog('Errors').on_error(e,ctx)

    @rss_main.command(name="use_embed",aliases=['embed'])
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_use_embed(self,ctx:MyContext,ID:Optional[int]=None,value:bool=None,*,arguments:args.arguments=None):
        """Use an embed or not for a flow
        You can also provide arguments to change the color/text of the embed. Followed arguments are usable:
        - color: color of the embed (hex or decimal value)
        - title: title override, which will disable the default one (max 256 characters)
        - footer: small text displayed at the bottom of the embed

        ..Example rss embed 6678466620137 true title="hey u" footer = "Hi \\n i'm a footer"
        
        ..Doc rss.html#setup-a-feed-embed"""
        try:
            e = None
            try:
                flows = await self.ask_rss_id(ID,
                                        ctx,
                                        await self.bot._(ctx.guild.id, "rss.choose-mentions-1"))
            except Exception as e:
                flows = []
                await self.bot.get_cog("Errors").on_error(e,ctx)
            if flows is None:
                return
            if len(flows) == 0:
                await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
                if e is not None:
                    await self.bot.get_cog("Errors").on_error(e,ctx)
                return
            if arguments is None or len(arguments.keys()) == 0:
                arguments = None
            flow = await self.get_flow(flows[0])
            values_to_update = list()
            txt = list()
            if value is None and arguments is None:
                await ctx.send(await self.bot._(ctx.guild.id,"rss.use_embed_" + ("true" if flow['use_embed'] else "false")))
                def check(msg):
                    try:
                        _ = commands.converter._convert_to_bool(msg.content)
                    except:
                        return False
                    return msg.author==ctx.author and msg.channel==ctx.channel
                try:
                    msg = await self.bot.wait_for('message', check=check,timeout=20)
                except asyncio.TimeoutError:
                    return await ctx.send(await self.bot._(ctx.guild.id, "rss.too-long"))
                value = commands.converter._convert_to_bool(msg.content)
            if value is not None and value != flow['use_embed']:
                values_to_update.append(('use_embed',value))
                txt.append(await self.bot._(ctx.guild.id,"rss.use_embed-success", v=value, id=flow['ID']))
            elif value == flow['use_embed'] and arguments is None:
                await ctx.send(await self.bot._(ctx.guild.id, "rss.use_embed-same"))
                return
            if arguments is not None:
                if 'color' in arguments.keys():
                    c = await args.Color().convert(ctx,arguments['color'])
                    if c is not None:
                        values_to_update.append(('embed_color',c))
                if 'title' in arguments.keys():
                    values_to_update.append(('embed_title',arguments['title']))
                if 'footer' in arguments.keys():
                    values_to_update.append(('embed_footer',arguments['footer']))
                txt.append(await self.bot._(ctx.guild.id, "rss.embed-json-changed"))
            if len(values_to_update) > 0:
                await self.update_flow(flow['ID'],values_to_update)
            await ctx.send("\n".join(txt))
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild.id,"rss.guild-error", err=e))
            await ctx.bot.get_cog('Errors').on_error(e,ctx)

    @rss_main.command(name="test")
    @commands.check(checks.is_support_staff)
    async def test_rss(self, ctx: MyContext, url, *, args=None):
        """Test if an rss feed is usable"""
        url = url.replace('<','').replace('>','')
        try:
            feeds = await feed_parse(self.bot, url, 8)
            txt = "feeds.keys()\n```py\n{}\n```".format(feeds.keys())
            if 'bozo_exception' in feeds.keys():
                txt += "\nException ({}): {}".format(feeds['bozo'],str(feeds['bozo_exception']))
                return await ctx.send(txt)
            if len(str(feeds.feed))<1400-len(txt):
                txt += "feeds.feed\n```py\n{}\n```".format(feeds.feed)
            else:
                txt += "feeds.feed.keys()\n```py\n{}\n```".format(feeds.feed.keys())
            if len(feeds.entries) > 0:
                if len(str(feeds.entries[0]))<1950-len(txt):
                    txt += "feeds.entries[0]\n```py\n{}\n```".format(feeds.entries[0])
                else:
                    txt += "feeds.entries[0].keys()\n```py\n{}\n```".format(feeds.entries[0].keys())
            if args is not None and 'feeds' in args and 'ctx' not in args:
                txt += "\n{}\n```py\n{}\n```".format(args,eval(args))
            try:
                await ctx.send(txt)
            except Exception as e:
                print("[rss_test] Error:",e)
                await ctx.send("`Error`: "+str(e))
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
                        txt.append("<:twitter:958325391196585984>  "+tw)
                    elif 'link' in feeds.feed.keys():
                        txt.append(":newspaper:  <"+feeds.feed['link']+'>')
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
        except Exception as e:
            await ctx.bot.get_cog('Errors').on_command_error(ctx,e)

    async def check_rss_url(self, url):
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
        except:
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


    async def rss_twitch(self, channel: discord.TextChannel, nom: str, date: datetime.datetime=None, session: ClientSession=None):
        url = 'https://twitchrss.appspot.com/vod/'+nom
        feeds = await feed_parse(self.bot, url, 5, session)
        if feeds is None:
            return await self.bot._(channel, "rss.research-timeout")
        if len(feeds.entries) == 0:
            return await self.bot._(channel, "rss.nothing")
        if not date:
            feed = feeds.entries[0]
            r = re.search(r'<img src="([^"]+)" />',feed['summary'])
            img_url = None
            if r is not None:
                img_url = r.group(1)
            obj = RssMessage(bot=self.bot,feed_type='twitch',url=feed['link'],title=feed['title'],date=feed['published_parsed'],author=feeds.feed['title'].replace("'s Twitch video RSS",""),image=img_url,channel=nom)
            return [obj]
        else:
            liste = list()
            for feed in feeds.entries:
                if len(liste) > 10:
                    break
                if datetime.datetime(*feed['published_parsed'][:6]) <= date:
                    break
                r = re.search(r'<img src="([^"]+)" />',feed['summary'])
                img_url = None
                if r is not None:
                    img_url = r.group(1)
                obj = RssMessage(bot=self.bot,feed_type='twitch',url=feed['link'],title=feed['title'],date=feed['published_parsed'],author=feeds.feed['title'].replace("'s Twitch video RSS",""),image=img_url,channel=nom)
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
                feed_type='web',
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
                        feed_type='web',
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
            obj = RssMessage(bot=self.bot,feed_type='deviant',url=feed['link'],title=feed['title'],date=feed['published_parsed'],author=title,image=img_url)
            return [obj]
        else:
            liste = list()
            for feed in feeds.entries:
                if datetime.datetime(*feed['published_parsed'][:6]) <= date:
                    break
                img_url = feed['media_content'][0]['url'] if "media_content" in feed else None
                title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feeds.feed['title']).group(1)
                obj = RssMessage(bot=self.bot,feed_type='deviant',url=feed['link'],title=feed['title'],date=feed['published_parsed'],author=title,image=img_url)
                liste.append(obj)
            liste.reverse()
            return liste



    async def create_id(self, Type: str):
        numb = str(round(time.time()/2)) + str(random.randint(10,99))
        if Type == 'yt':
            numb = int('10'+numb)
        elif Type == 'tw':
            numb == int('20'+numb)
        elif Type == 'web':
            numb = int('30'+numb)
        elif Type == 'reddit':
            numb = int('40'+numb)
        elif Type == 'mc':
            numb = int('50'+numb)
        elif Type == 'twitch':
            numb = int('60'+numb)
        else:
            numb = int('66'+numb)
        return numb

    def connect(self):
        return mysql.connector.connect(user=self.bot.database_keys['user'],password=self.bot.database_keys['password'],host=self.bot.database_keys['host'],database=self.bot.database_keys['database'])

    async def get_flow(self, ID: int) -> Optional[dict]:
        query = ("SELECT * FROM `{}` WHERE `ID`='{}'".format(self.table,ID))
        async with self.bot.db_query(query) as query_results:
            liste = list(query_results)
        return liste[0] if len(liste) > 0 else None

    async def get_guild_flows(self, guildID: int):
        """Get every flow of a guild"""
        query = ("SELECT * FROM `{}` WHERE `guild`='{}'".format(self.table,guildID))
        async with self.bot.db_query(query) as query_results:
            liste = list(query_results)
        return liste

    async def add_flow(self, guildID:int, channelID:int, _type:str, link:str):
        """Add a flow in the database"""
        ID = await self.create_id(_type)
        if _type == 'mc':
            form = ''
        else:
            form = await self.bot._(guildID, f"rss.{_type}-default-flow")
        query = "INSERT INTO `{}` (`ID`, `guild`,`channel`,`type`,`link`,`structure`) VALUES (%(i)s,%(g)s,%(c)s,%(t)s,%(l)s,%(f)s)".format(self.table)
        async with self.bot.db_query(query, { 'i': ID, 'g': guildID, 'c': channelID, 't': _type, 'l': link, 'f': form }):
            pass
        return ID

    async def remove_flow(self, ID: int):
        """Remove a flow from the database"""
        if not isinstance(ID, int):
            raise ValueError
        query = ("DELETE FROM `{}` WHERE `ID`='{}'".format(self.table,ID))
        async with self.bot.db_query(query):
            pass
        return True

    async def get_all_flows(self):
        """Get every flow of the database"""
        query = ("SELECT * FROM `{}` WHERE `guild` in ({})".format(self.table,','.join(["'{}'".format(x.id) for x in self.bot.guilds])))
        async with self.bot.db_query(query) as query_results:
            liste = list(query_results)
        return liste

    async def get_raws_count(self, get_disabled:bool=False):
        """Get the number of rss feeds"""
        query = "SELECT COUNT(*) as count FROM `{}`".format(self.table)
        if not get_disabled:
            query += " WHERE `guild` in (" + ','.join(["'{}'".format(x.id) for x in self.bot.guilds]) + ")"
        async with self.bot.db_query(query, fetchone=True) as query_results:
            t = query_results['count']
        return t

    async def update_flow(self, id: int, values=[(None,None)]):
        if self.bot.zombie_mode:
            return
        set_query = ', '.join('{}=%s'.format(val[0]) for val in values)
        query = """UPDATE `{t}` SET {v} WHERE `ID`={id}""".format(t=self.table, v=set_query, id=id)
        async with self.bot.db_query(query, (val[1] for val in values)):
            pass

    async def send_rss_msg(self, obj: "RssMessage", channel: discord.TextChannel, roles: list[str], send_stats):
        if channel is not None:
            t = await obj.create_msg()
            mentions = list()
            for item in roles:
                if item == '':
                    continue
                role = discord.utils.get(channel.guild.roles,id=int(item))
                if role is not None:
                    mentions.append(role)
            try:
                if self.bot.zombie_mode:
                    return
                allowed_mentions = discord.AllowedMentions(everyone=False, roles=True)
                if isinstance(t, discord.Embed):
                    await channel.send(" ".join(obj.mentions), embed=t, allowed_mentions=allowed_mentions)
                else:
                    await channel.send(t, allowed_mentions=allowed_mentions)
                if send_stats:
                    if statscog := self.bot.get_cog("BotStats"):
                        statscog.rss_stats['messages'] += 1
            except discord.HTTPException as e:
                self.bot.log.info("[send_rss_msg] Cannot send message on channel {}: {}".format(channel.id,e))
                await self.bot.get_cog("Errors").on_error(e)
                await self.bot.get_cog("Errors").senf_err_msg(str(t.to_dict()) if hasattr(t, "to_dict") else str(t))
            except Exception as e:
                self.bot.log.info("[send_rss_msg] Cannot send message on channel {}: {}".format(channel.id,e))

    async def check_flow(self, flow: dict, session: ClientSession = None, send_stats: bool=False):
        try:
            guild = self.bot.get_guild(flow['guild'])
            if guild is None:
                self.bot.log.info("[send_rss_msg] Cannot send message on server {} (unknown guild)".format(flow['guild']))
                return False
            chan: discord.TextChannel = guild.get_channel(flow['channel'])
            if chan is None:
                self.bot.log.info("[send_rss_msg] Cannot send message on channel {} (unknown channel)".format(flow['channel']))
                return True
            if flow['link'] in self.cache.keys():
                objs = self.cache[flow['link']]
            else:
                if flow['type'] == "yt":
                    objs = await self.youtube_rss.get_feed(chan, flow['link'], flow['date'], session)
                elif flow['type'] == "tw":
                    objs = await self.twitter_rss.get_feed(chan,flow['link'], flow['date'])
                else:
                    funct = getattr(self, f"rss_{flow['type']}")
                    objs = await funct(chan,flow['link'], flow['date'], session=session)
                if isinstance(objs, twitter.error.TwitterError):
                    self.twitter_over_capacity = True
                    self.bot.log.warning("[send_rss_msg] Twitter over capacity detected")
                    return False
                flow['link'] = objs
            if isinstance(objs,twitter.TwitterError):
                await self.bot.get_user(279568324260528128).send(f"[send_rss_msg] twitter error dans `await check_flow(): {objs}`")
                raise objs
            if isinstance(objs,(str,type(None),int)) or len(objs) == 0:
                return True
            elif isinstance(objs, list):
                for o in objs[:self.max_messages]:
                    # if we can't post messages: abort
                    if not chan.permissions_for(guild.me).send_messages:
                        return True
                    o.format = flow['structure']
                    o.embed = flow['use_embed']
                    o.fill_embed_data(flow)
                    await o.fill_mention(guild, flow['roles'].split(';'), self.bot._)
                    await self.send_rss_msg(o, chan, flow['roles'].split(';'), send_stats)
                await self.update_flow(flow['ID'], [('date', o.date)],)
                return True
            else:
                return True
        except Exception as e:
            await self.bot.get_cog('Errors').senf_err_msg("Erreur rss sur le flux {} (type {} - salon {})".format(flow['link'],flow['type'],flow['channel']))
            await self.bot.get_cog('Errors').on_error(e,None)
            return False


    async def main_loop(self, guildID: int=None):
        if not self.bot.rss_enabled:
            return
        t = time.time()
        if self.loop_processing:
            return
        if guildID is None:
            self.bot.log.info("Check RSS lancé")
            self.loop_processing = True
            liste = await self.get_all_flows()
        else:
            self.bot.log.info(f"Check RSS lancé pour le serveur {guildID}")
            liste = await self.get_guild_flows(guildID)
        check = 0
        errors = []
        if guildID is None:
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats['messages'] = 0
        session = ClientSession()
        for flow in liste:
            try:
                if flow['type'] == 'tw' and self.twitter_over_capacity:
                    continue
                if flow['type'] == 'mc':
                    await self.bot.get_cog('Minecraft').check_flow(flow, send_stats=(guildID is None))
                    check +=1
                else:
                    if await self.check_flow(flow, session, send_stats=(guildID is None)):
                        check += 1
                    else:
                        errors.append(flow['ID'])
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,None)
            await asyncio.sleep(self.time_between_flows_check)
        await session.close()
        self.bot.get_cog('Minecraft').flows.clear()
        d = ["**RSS loop done** in {}s ({}/{} flows)".format(round(time.time()-t,3),check,len(liste))]
        if guildID is None:
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats['checked'] = check
                statscog.rss_stats['errors'] = len(errors)
        if len(errors) > 0:
            d.append('{} errors: {}'.format(len(errors),' '.join([str(x) for x in errors])))
        emb = discord.Embed(description='\n'.join(d), color=1655066, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed([emb], url="loop")
        self.bot.log.debug(d[0])
        if len(errors) > 0:
            self.bot.log.warning("[Rss loop] "+d[1])
        if guildID is None:
            self.loop_processing = False
        self.twitter_over_capacity = False
        self.cache.clear()

    @tasks.loop(minutes=20)
    async def loop_child(self):
        if not self.bot.rss_enabled:
            return
        if not self.bot.database_online:
            self.bot.log.warning('Base de donnée hors ligne - check rss annulé')
            return
        self.bot.log.info(" Boucle rss commencée !")
        t1 = time.time()
        await self.main_loop()
        self.bot.log.info(" Boucle rss terminée en {}s!".format(round(time.time()-t1,2)))

    @loop_child.before_loop
    async def before_printer(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()


    @commands.command(name="rss_loop",hidden=True)
    @commands.check(checks.is_bot_admin)
    async def rss_loop_admin(self, ctx: MyContext, new_state: str = "start"):
        """Manage the rss loop
        new_state can be start, stop or once"""
        if not ctx.bot.database_online:
            return await ctx.send("Lol, t'as oublié que la base de donnée était hors ligne "+random.choice(["crétin ?","? Tu ferais mieux de fixer tes bugs","?","? :rofl:","?"]))
        if new_state == "start":
            try:
                self.loop_child.start() # pylint: disable=no-member
            except RuntimeError:
                await ctx.send("La boucle est déjà en cours !")
            else:
                await ctx.send("Boucle rss relancée !")
        elif new_state == "stop":
            await self.loop_child.cancel() # pylint: disable=no-member
            self.bot.log.info(" Boucle rss arrêtée de force par un admin")
            await ctx.send("Boucle rss arrêtée de force !")
        elif new_state == "once":
            if self.loop_processing:
                await ctx.send("Une boucle rss est déjà en cours !")
            else:
                await ctx.send("Et hop ! Une itération de la boucle en cours !")
                self.bot.log.info(" Boucle rss forcée")
                await self.main_loop()
        else:
            await ctx.send("Option `new_start` invalide - choisissez start, stop ou once")

    async def send_log(self, text: str, guild: discord.Guild):
        """Send a log to the logging channel"""
        try:
            emb = discord.Embed(description="[RSS] "+text, color=5366650, timestamp=self.bot.utcnow())
            emb.set_footer(text=guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed([emb])
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e,None)


async def setup(bot):
    await bot.add_cog(Rss(bot))
