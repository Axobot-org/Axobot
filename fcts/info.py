from utils import zbot, MyContext
from libs import bitly_api
from fcts import reloads, args, checks
from docs import conf
import discord
import datetime
import sys
import psutil
import os
import aiohttp
import importlib
import time
import asyncio
import typing
import re
import copy
import requests
from discord.ext import commands
from platform import system as system_name  # Returns the system/OS name
from subprocess import call as system_call  # Execute a shell command

default_color = discord.Color(0x50e3c2)

importlib.reload(conf)
# importlib.reload(reloads)
importlib.reload(args)
importlib.reload(checks)
importlib.reload(bitly_api)


async def in_support_server(ctx):
    return ctx.guild is not None and ctx.guild.id == 625316773771608074

class Info(commands.Cog):
    """Here you will find various useful commands to get information about ZBot."""

    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "info"
        self.bot_version = conf.release
        try:
            self.TimeUtils = bot.get_cog("TimeUtils")
        except:
            pass
        self.emoji_table = 'emojis_beta' if self.bot.beta else 'emojis'
        self.BitlyClient = bitly_api.Bitly(login='zrunner',api_key=self.bot.others['bitly'])

    @commands.Cog.listener()
    async def on_ready(self):
        self.TimeUtils = self.bot.get_cog("TimeUtils")
        self.codelines = await self.count_lines_code()
        self.emoji_table = 'emojis_beta' if self.bot.beta else 'emojis'
    
    async def count_lines_code(self):
        """Count the number of lines for the whole project"""
        count = 0
        try:
            for filename in ['start.py', 'utils.py']:
                with open(filename, 'r') as file:
                    for line in file.read().split("\n"):
                        if len(line.strip()) > 2 and line[0] != '#':
                            count += 1
            for filename in [x.file for x in self.bot.cogs.values()]+['args', 'checks']:
                with open('fcts/'+filename+'.py', 'r') as file:
                    for line in file.read().split("\n"):
                        if len(line.strip()) > 2 and line[0] != '#':
                            count += 1
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e, None)
        self.codelines = count
        return count

    @commands.command(name='admins')
    async def admin_list(self, ctx: MyContext):
        """Get the list of ZBot administrators
        
        ..Doc miscellaneous.html#admins"""
        l  = list()
        for u in reloads.admins_id:
            if u==552273019020771358:
                continue
            l.append(str(self.bot.get_user(u)))
        await ctx.send(str(await self.bot._(ctx.channel,"infos","admins-list")).format(", ".join(l)))

    async def get_guilds_count(self, ignored_guilds:list=None) -> int:
        """Get the number of guilds where Zbot is"""
        if ignored_guilds is None:
            if self.bot.database_online:
                if 'banned_guilds' not in self.bot.get_cog('Utilities').config.keys():
                    await self.bot.get_cog('Utilities').get_bot_infos()
                ignored_guilds = [int(x) for x in self.bot.get_cog('Utilities').config['banned_guilds'].split(";") if len(x) > 0] + self.bot.get_cog('Reloads').ignored_guilds
            else:
                return len(self.bot.guilds)
        return len([x for x in self.bot.guilds if x.id not in ignored_guilds])

    @commands.command(name="stats", enabled=True)
    @commands.cooldown(2,60,commands.BucketType.guild)
    async def stats(self, ctx: MyContext):
        """Display some statistics about the bot
        
        ..Doc infos.html#statistics"""
        v = sys.version_info
        version = str(v.major)+"."+str(v.minor)+"."+str(v.micro)
        pid = os.getpid()
        py = psutil.Process(pid)
        latency = round(self.bot.latency*1000, 3)
        try:
            async with ctx.channel.typing():
                # RAM/CPU
                ram_cpu = [round(py.memory_info()[0]/2.**30,3), py.cpu_percent(interval=1)]
                # Guilds count
                b_conf = self.bot.get_cog('Utilities').config
                if b_conf is None:
                    b_conf = await self.bot.get_cog('Utilities').get_bot_infos()
                ignored_guilds = list()
                if self.bot.database_online:
                    ignored_guilds = [int(x) for x in self.bot.get_cog('Utilities').config['banned_guilds'].split(";") if len(x) > 0]
                ignored_guilds += self.bot.get_cog('Reloads').ignored_guilds
                len_servers = await self.get_guilds_count(ignored_guilds)
                # Languages
                langs_list: list = await self.bot.get_cog('Servers').get_languages(ignored_guilds)
                langs_list.sort(reverse=True, key=lambda x: x[1])
                lang_total = sum([x[1] for x in langs_list])
                langs_list = ' | '.join(["{}: {}%".format(x[0],round(x[1]/lang_total*100)) for x in langs_list if x[1] > 0])
                del lang_total
                # Users/bots
                try:
                    users,bots = self.get_users_nber(ignored_guilds)
                except Exception as e:
                    users = bots = 'unknown'
                # Total XP
                if self.bot.database_online:
                    total_xp = await self.bot.get_cog('Xp').bdd_total_xp()
                else:
                    total_xp = ""
                # Commands within 24h
                cmds_24h = await self.bot.get_cog("BotStats").get_stats("wsevent.CMD_USE", 60*24)
                # Generating message
                d = ""
                for key, var in [
                    ('bot_version', self.bot_version),
                    ('servers_count', len_servers),
                    ('users_count', (users, bots)),
                    ('codes_lines', self.codelines),
                    ('languages', langs_list),
                    ('python_version', version),
                    ('lib_version', discord.__version__),
                    ('ram_usage', ram_cpu[0]),
                    ('cpu_usage', ram_cpu[1]),
                    ('api_ping', latency),
                    ('cmds_24h', cmds_24h),
                    ('total_xp', total_xp)]:
                    d += await self.bot._(ctx.channel, "infos", "stats."+key, v=var) + "\n"
            if ctx.can_send_embed: # if we can use embed
                embed = ctx.bot.get_cog('Embeds').Embed(title=await self.bot._(ctx.channel,"infos","stats-title"), color=ctx.bot.get_cog('Help').help_color, time=ctx.message.created_at,desc=d,thumbnail=self.bot.user.avatar_url_as(format="png"))
                await embed.create_footer(ctx)
                await ctx.send(embed=embed.discord_embed())
            else:
                await ctx.send(d)
        except Exception as e:
            await ctx.bot.get_cog('Errors').on_command_error(ctx,e)

    def get_users_nber(self, ignored_guilds: list):
        members = [x.members for x in self.bot.guilds if x.id not in ignored_guilds]
        members = list(set([x for x in members for x in x])) # filter users
        return len(members),len([x for x in members if x.bot])
    
    @commands.command(name="botinvite", aliases=["botinv"])
    async def botinvite(self, ctx:MyContext):
        """Get a link to invite me
        
        ..Doc infos.html#bot-invite"""
        raw_oauth = "<" + discord.utils.oauth_url(self.bot.user.id) + ">"
        try:
            r = requests.get("https://zrunner.me/invitezbot", timeout=3)
        except requests.exceptions.Timeout:
            url = raw_oauth
        else:
            if r.status_code < 400:
                url = "https://zrunner.me/invitezbot"
            else:
                url = raw_oauth
        await ctx.send(await self.bot._(ctx.channel, "infos", "botinvite", url=url))
    
    @commands.command(name="pig", hidden=True)
    async def pig(self, ctx: MyContext):
        """Get bot latency
        You can also use this command to ping any other server"""
        m = await ctx.send("Pig...")
        t = (m.created_at - ctx.message.created_at).total_seconds()
        await m.edit(content=":pig:  Groink!\nBot ping: {}ms\nDiscord ping: {}ms".format(round(t*1000),round(self.bot.latency*1000)))

    @commands.command(name="ping",aliases=['rep'])
    async def rep(self, ctx: MyContext, ip=None):
        """Get bot latency
        You can also use this command to ping any other server

        ..Example ping

        ..Example ping google.fr
        
        ..Doc infos.html#ping"""
        if ip is None:
            m = await ctx.send("Ping...")
            t = (m.created_at - ctx.message.created_at).total_seconds()
            try:
                p = round(self.bot.latency*1000)
            except OverflowError:
                p = "∞"
            await m.edit(content=":ping_pong:  Pong !\nBot ping: {}ms\nDiscord ping: {}ms".format(round(t*1000),p))
        else:
            asyncio.run_coroutine_threadsafe(self.ping_address(ctx,ip),asyncio.get_event_loop())

    async def ping_address(self, ctx: MyContext, ip: str):
        packages = 40
        wait = 0.3
        try:
            try:
                m = await ctx.send("Ping...",file=await self.bot.get_cog('Utilities').find_img('discord-loading.gif'))
            except:
                m = None
            t1 = time.time()
            param = '-n' if system_name().lower()=='windows' else '-c'
            command = ['ping', param, str(packages),'-i',str(wait), ip]
            result = system_call(command) == 0
        except Exception as e:
            await ctx.send("`Error:` {}".format(e))
            return
        if result:
            t = (time.time() - t1 - wait*(packages-1))/(packages)*1000
            await ctx.send(await self.bot._(ctx.channel, "infos", "ping-found", tps=round(t,2), url=ip))
        else:
            await ctx.send(await self.bot._(ctx.channel, "infos", "ping-notfound"))
        if m is not None:
            await m.delete()

    @commands.command(name="docs", aliases=['doc','documentation'])
    async def display_doc(self, ctx: MyContext):
        """Get the documentation url"""
        text = str(self.bot.get_cog('Emojis').customEmojis['readthedocs']) + str(await self.bot._(ctx.channel,"infos","docs")) + " https://zbot.rtfd.io"
        if self.bot.beta:
            text += '/en/indev'
        await ctx.send(text)

    @commands.command(name='info',aliases=['infos'])
    @commands.guild_only()
    async def infos(self, ctx: MyContext, Type: typing.Optional[args.infoType]=None, *, name: str=None):
        """Find informations about someone/something
Available types: member, role, user, emoji, channel, server, invite, category

..Example info role The VIP

..Example info 436835675304755200

..Example info :owo:

..Example info server

.. Doc infos.html#info"""
        if Type is not None and name is None and Type not in ["guild","server"]:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['name'])
        if not ctx.can_send_embed:
            return await ctx.send(await self.bot._(ctx.guild.id,"fun","no-embed-perm"))
        try:
            item = None
            lang = await self.bot._(ctx.guild.id,"current_lang","current")
            find = self.bot.get_cog('Utilities').find_everything
            if Type in ["guild","server"]:
                if name is None or not await self.bot.get_cog('Admin').check_if_admin(ctx):
                    item = ctx.guild
                    #return await self.guild_info(ctx,ctx.guild,lang)
            if item is None:
                if name is None: # include Type is None bc of line 141
                    item = ctx.author
                else:
                    try:
                        item = await find(ctx,name,Type)
                    except:
                        await ctx.send(str(await self.bot._(ctx.guild.id,"modo","cant-find-user")).format(name))
                        return
            critical = ctx.author.guild_permissions.manage_guild or await self.bot.get_cog('Admin').check_if_god(ctx)
            #-----
            if item is None:
                msg = await self.bot._(ctx.guild.id,"stats_infos","not-found")
                await ctx.send(msg.format(N=name[:1900]))
            elif type(item) == discord.Member:
                await self.member_infos(ctx,item,lang,critical)
            elif type(item) == discord.Role:
                await self.role_infos(ctx,item,lang)
            elif type(item) == discord.User:
                await self.user_infos(ctx,item,lang)
            elif type(item) == discord.Emoji:
                await self.emoji_infos(ctx,item,lang)
            elif type(item) == discord.TextChannel:
                await self.textChannel_infos(ctx,item,lang)
            elif type(item) == discord.VoiceChannel:
                await self.voiceChannel_info(ctx,item,lang)
            elif type(item) == discord.Invite:
                await self.invite_info(ctx,item,lang)
            elif type(item) == discord.CategoryChannel:
                await self.category_info(ctx,item,lang)
            elif type(item) == discord.Guild:
                await self.guild_info(ctx,item,lang,critical)
            elif isinstance(item,discord.user.ClientUser):
                await self.member_infos(ctx,ctx.guild.me,lang,critical)
            elif isinstance(item,args.snowflake().Snowflake):
                await self.snowflake_infos(ctx,item,lang)
            else:
                await ctx.send(str(type(item))+" / "+str(item))
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e,ctx)
            await ctx.send(await self.bot._(ctx.channel,'errors','unknown'))

    async def member_infos(self, ctx: MyContext,item: discord.Member, lang: str, critical_info=False):
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=item.color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.avatar_url_as(format='gif') if item.is_avatar_animated() else item.avatar_url_as(format='png'))
        embed.set_author(name=str(item), icon_url=str(item.avatar_url_as(format='png')))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=str(ctx.author.avatar_url_as(format='png')))
        # Name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        # Nickname
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-0"), value=item.nick if item.nick else str(await self.bot._(ctx.channel,"keywords","none")).capitalize(),inline=True)
        # ID
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        # Roles
        list_role = list()
        for role in item.roles:
            if str(role)!='@everyone':
                list_role.append(role.mention)
        # Created at
        now = datetime.datetime.utcnow()
        delta = abs(item.created_at - now)
        created_date = await self.TimeUtils.date(item.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        if item.created_at.day == now.day and item.created_at.month == now.month and item.created_at.year != now.year:
            created_date = "🎂 " + created_date
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # Joined at
        if item.joined_at is not None:
            delta = abs(item.joined_at - now)
            join_date = await self.TimeUtils.date(item.joined_at, lang=lang, year=True)
            since_date = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
            embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-2"), value = "{} ({} {})".format(join_date, since, since_date), inline=False)
        # Join position
        if sum([1 for x in ctx.guild.members if not x.joined_at]) > 0 and ctx.guild.large:
            await self.bot.request_offline_members(ctx.guild)
        position = str(sorted(ctx.guild.members, key=lambda m: m.joined_at).index(item) + 1) + "/" + str(len(ctx.guild.members))
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-3"), value = position,inline=True)
        # Status
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-4"), value = str(await self.bot._(ctx.guild.id,"keywords",str(item.status))).capitalize(),inline=True)
        # Activity
        if item.activity is None:
            m_activity = str(await self.bot._(ctx.guild.id,"activity","nothing")).capitalize()
        elif item.activity.type==discord.ActivityType.playing:
            m_activity = str(await self.bot._(ctx.guild.id,"activity","play")).capitalize() + " " + item.activity.name
        elif item.activity.type==discord.ActivityType.streaming:
            m_activity = str(await self.bot._(ctx.guild.id,"activity","stream")).capitalize() + " (" + item.activity.name + ")"
        elif item.activity.type==discord.ActivityType.listening:
            m_activity = str(await self.bot._(ctx.guild.id,"activity","listen")).capitalize() + " " + item.activity.name
        elif item.activity.type==discord.ActivityType.watching:
            m_activity = str(await self.bot._(ctx.guild.id,"activity","watch")).capitalize() +" " + item.activity.name
        elif item.activity.type==discord.ActivityType.custom:
            m_activity = str(item.activity.emoji if item.activity.emoji else '') + " " + (item.activity.name if item.activity.name else '')
            m_activity = m_activity.strip()
        else:
            m_activity="Error"
        if item.activity is None or item.activity.type != 4:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-5"), value = m_activity,inline=True)
        else:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-8"), value = item.activity.state, inline=True)
        # Bot
        if item.bot:
            botb = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            botb = await self.bot._(ctx.guild.id,"keywords","non")
        embed.add_field(name="Bot", value=botb.capitalize())
        # Administrator
        if item.permissions_in(ctx.channel).administrator:
            admin = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            admin = await self.bot._(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-6"), value = admin.capitalize(),inline=True)
        # Infractions count
        if critical_info and not item.bot and self.bot.database_online:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-7"), value = await self.bot.get_cog('Cases').get_nber(item.id,ctx.guild.id),inline=True)
        # Guilds count
        if item.bot:
            session = aiohttp.ClientSession(loop=self.bot.loop)
            guilds_count = await self.bot.get_cog('Partners').get_bot_guilds(item.id,session)
            if guilds_count is not None:
                embed.add_field(name=str(await self.bot._(ctx.guild.id,'keywords','servers')).capitalize(),value=guilds_count)
            await session.close()
        # Roles
        _roles = await self.bot._(ctx.guild.id, 'stats_infos', 'member-9') + f' [{len(list_role)}]'
        if len(list_role) > 0:
            c = len(list_role)
            list_role = list_role[:40]
            embed.add_field(name=_roles, value = ", ".join(list_role), inline=False)
        else:
            embed.add_field(name=_roles, value = await self.bot._(ctx.guild.id,"activity","nothing"), inline=False)
        # member verification gate
        if item.pending:
            _waiting = await self.bot._(ctx.guild.id, 'stats_infos', 'member-10')
            embed.add_field(name=_waiting, value='\u200b', inline=False)
        await ctx.send(embed=embed)


    async def role_infos(self, ctx: MyContext, item: discord.Role, lang: str):
        embed = discord.Embed(colour=item.color, timestamp=ctx.message.created_at)
        embed.set_author(name=str(item), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        # Name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=item.mention,inline=True)
        # ID
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(item.id),inline=True)
        # Color
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-1"), value=str(item.color),inline=True)
        # Mentionnable
        if item.mentionable:
            mentio = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            mentio = await self.bot._(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-2"), value=mentio.capitalize(),inline=True)
        # Members nbr
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-3"), value=len(item.members),inline=True)
        # Hoisted
        if item.hoist:
            hoist = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            hoist = await self.bot._(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-4"), value=hoist.capitalize(),inline=True)
        # Created at
        delta = abs(item.created_at - datetime.datetime.utcnow())
        created_date = await self.TimeUtils.date(item.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # Hierarchy position
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-5"), value=str(len(ctx.guild.roles) - item.position),inline=True)
        # Unique member
        if len(item.members)==1:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-6"), value=str(item.members[0].mention),inline=True)
        await ctx.send(embed=embed)


    async def user_infos(self, ctx: MyContext, item: discord.User, lang: str):
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        if item.bot:
            botb = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            botb = await self.bot._(ctx.guild.id,"keywords","non")
        if item in ctx.guild.members:
            on_server = await self.bot._(ctx.guild.id,"keywords","oui")
            banned = None
        else:
            on_server = await self.bot._(ctx.guild.id,"keywords","non")
            # try:
            #     banned = str((await ctx.guild.fetch_ban(item)).reason)
            # except (discord.Forbidden, discord.NotFound):
            #     banned = None
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.avatar_url_as(format='gif') if item.is_avatar_animated() else item.avatar_url_as(format='png'))
        embed.set_author(name=str(item), icon_url=item.avatar_url_as(format='png'))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))

        # name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        # ID
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        # created at
        now = datetime.datetime.utcnow()
        delta = abs(item.created_at - now)
        created_date = await self.TimeUtils.date(item.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        if item.created_at.day == now.day and item.created_at.month == now.month and item.created_at.year != now.year:
            created_date = "🎂 " + created_date
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # is bot
        embed.add_field(name="Bot", value=botb.capitalize())
        # is in server
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","user-0"), value=on_server.capitalize())
        if item.bot:
            session = aiohttp.ClientSession(loop=self.bot.loop)
            guilds_count = await self.bot.get_cog('Partners').get_bot_guilds(item.id,session)
            if guilds_count is not None:
                embed.add_field(name=str(await self.bot._(ctx.guild.id,'keywords','servers')).capitalize(),value=guilds_count)
            await session.close()
        # ban reason
        # if banned:
        #     embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "user-1"), value=banned.capitalize())
        await ctx.send(embed=embed)

    async def emoji_infos(self, ctx: MyContext, item: discord.Emoji, lang: str):
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        if item.animated:
            animate = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            animate = await self.bot._(ctx.guild.id,"keywords","non")
        if item.managed:
            manage = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            manage = await self.bot._(ctx.guild.id,"keywords","non")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.url)
        embed.set_author(name="Emoji '{}'".format(item.name), icon_url=item.url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))
        # name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        # id
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        # animated
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","emoji-0"), value=animate.capitalize())
        # guild name
        if item.guild != ctx.guild:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","emoji-3"), value=item.guild.name)
        # string
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","emoji-2"), value="`<:{}:{}>`".format(item.name,item.id))
        # managed
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","emoji-1"), value=manage.capitalize())
        # created at
        delta = abs(item.created_at - datetime.datetime.utcnow())
        created_date = await self.TimeUtils.date(item.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # allowed roles
        if len(item.roles) > 0:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","emoji-4"), value=" ".join([x.mention for x in item.roles]))
        # uses
        infos_uses = await self.get_emojis_info(item.id)
        if len(infos_uses) > 0:
            infos_uses = infos_uses[0]
            lang = await self.bot._(ctx.channel,'current_lang','current')
            date = await self.bot.get_cog('TimeUtils').date(infos_uses['added_at'],lang,year=True,hour=False)
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","emoji-5"), value=await self.bot._(ctx.guild.id,"stats_infos","emoji-5v",nbr=infos_uses['count'],date=date))
        await ctx.send(embed=embed)

    async def textChannel_infos(self, ctx: MyContext, chan: discord.TextChannel, lang: str):
        if not chan.permissions_for(ctx.author).view_channel:
            await ctx.send(await self.bot._(ctx.guild.id, "infos", "cant-see-channel"))
            return
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.bot._(ctx.guild.id,"stats_infos","textchan-5"),chan.name), icon_url=ctx.guild.icon_url_as(format='png'))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        # Name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=chan.name,inline=True)
        # ID
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(chan.id))
        # Category
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","textchan-0"), value=str(chan.category))
        # NSFW
        if chan.nsfw:
            nsfw = await self.bot._(ctx.guild.id,"keywords","oui")
        else:
            nsfw = await self.bot._(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","textchan-2"), value=nsfw.capitalize())
        # Webhooks count
        try:
            web = len(await chan.webhooks())
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,ctx)
            web = await self.bot._(ctx.guild.id,"stats_infos","textchan-4")
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","textchan-3"), value=str(web))
        # Members nber
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-3"), value = str(len(chan.members))+"/"+str(ctx.guild.member_count), inline=True)
        # Created at
        delta = abs(chan.created_at - datetime.datetime.utcnow())
        created_date = await self.TimeUtils.date(chan.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # Topic
        if chan.permissions_for(ctx.author).read_messages:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","textchan-1"), value = chan.topic if chan.topic not in ['',None] else str(await self.bot._(ctx.guild.id,"keywords","aucune")).capitalize(), inline=False)
        await ctx.send(embed=embed)

    async def voiceChannel_info(self, ctx: MyContext, chan: discord.VoiceChannel, lang: str):
        if not chan.permissions_for(ctx.author).view_channel:
            await ctx.send(await self.bot._(ctx.guild.id, "infos", "cant-see-channel"))
            return
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.bot._(ctx.guild.id,"stats_infos","voicechan-0"),chan.name), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        # Name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=chan.name,inline=True)
        # ID
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(chan.id))
        # Category
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","textchan-0"), value=str(chan.category))
        # Created at
        delta = abs(chan.created_at - datetime.datetime.utcnow())
        created_date = await self.TimeUtils.date(chan.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # Bitrate
        embed.add_field(name="Bitrate",value=str(chan.bitrate/1000)+" kbps")
        # Members count
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-3"), value="{}/{}".format(len(chan.members),chan.user_limit if chan.user_limit > 0 else "∞"))
        # Region
        if chan.rtc_region is not None:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-2"), value=str(chan.rtc_region).capitalize())
        await ctx.send(embed=embed)

    async def guild_info(self, ctx:MyContext, guild:discord.Guild, lang:str, critical_info:bool=False):
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        _, bots, online = await self.bot.get_cog("Utilities").get_members_repartition(guild.members)
       
        desc = await self.bot.get_config(guild.id,'description')
        if (desc is None or len(desc) == 0) and guild.description is not None:
            desc = guild.description
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at, description=desc)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        # Guild icon
        icon_url = guild.icon_url_as(format = "gif" if guild.is_icon_animated() else 'png')
        embed.set_author(name="{} '{}'".format(await self.bot._(ctx.guild.id,"stats_infos","guild-0"),guild.name), icon_url=icon_url)
        embed.set_thumbnail(url=icon_url)
        # Guild banner
        if guild.banner is not None:
            embed.set_image(url=guild.banner_url)
        # Name
        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=guild.name,inline=True)
        # ID
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(guild.id))
        # Owner
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-1"), value=str(guild.owner))
        # Created at
        delta = abs(guild.created_at - datetime.datetime.utcnow())
        created_date = await self.TimeUtils.date(guild.created_at, lang=lang, year=True)
        created_since = await self.TimeUtils.time_delta(delta.total_seconds(), lang=lang, year=True, precision=0, hour=delta.total_seconds() < 86400)
        embed.add_field(name=await self.bot._(ctx.guild.id, "stats_infos", "member-1"), value = "{} ({} {})".format(created_date, since, created_since), inline=False)
        # Voice region
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-2"), value=str(guild.region).capitalize())
        # Member count
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-3"), value = str(await self.bot._(ctx.guild.id,"stats_infos","guild-7")).format(guild.member_count, bots, online))
        # Channel count
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-6"), value=str(await self.bot._(ctx.guild.id,"stats_infos","guild-3")).format(len(guild.text_channels), len(guild.voice_channels), len(guild.categories)))
        # Invite count
        if guild.me.guild_permissions.manage_guild:
            len_invites = str(len(await guild.invites()))
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-12"), value=len_invites)
        # Emojis count
        c = [0, 0]
        for x in guild.emojis:
            c[1 if x.animated else 0] += 1
        emojis_txt = await self.bot._(ctx.guild.id, "stats_infos", "guild-16", l=guild.emoji_limit, s=c[0], a=c[1])
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-5"), value=emojis_txt)
        # AFK timeout
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-10"), value = str(int(guild.afk_timeout/60))+" minutes")
        # Splash url
        try:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-15"), value=str(await guild.vanity_invite()))
        except Exception as e:
            if isinstance(e,(discord.errors.Forbidden, discord.errors.HTTPException)):
                pass
            else:
                await self.bot.get_cog('Errors').on_error(e,ctx)
        # Premium subscriptions count
        if isinstance(guild.premium_subscription_count,int) and guild.premium_subscription_count > 0:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-13"), value=await self.bot._(ctx.guild.id,"stats_infos","guild-13v",b=guild.premium_subscription_count,p=guild.premium_tier))
        # Roles list
        try:
            if ctx.guild==guild:
                roles = [x.mention for x in guild.roles if len(x.members) > 1][1:]
            else:
                roles = [x.name for x in guild.roles if len(x.members) > 1][1:]
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,ctx)
            roles = guild.roles
        roles.reverse()
        if len(roles) == 0:
            temp = (await self.bot._(ctx.guild.id,"keywords","none")).capitalize()
            embed.add_field(name=str(await self.bot._(ctx.guild.id,"stats_infos","guild-11.2")).format(len(guild.roles)-1), value=temp)
        elif len(roles)>20:
            embed.add_field(name=str(await self.bot._(ctx.guild.id,"stats_infos","guild-11.1")).format(len(guild.roles)-1), value=", ".join(roles[:20]))
        else:
            embed.add_field(name=str(await self.bot._(ctx.guild.id,"stats_infos","guild-11.2")).format(len(guild.roles)-1), value=", ".join(roles))
        # Limitations
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-14"), value=await self.bot._(ctx.guild.id,"stats_infos","guild-14v",
            bit=round(guild.bitrate_limit/1000),
            fil=round(guild.filesize_limit/1.049e+6),
            emo=guild.emoji_limit,
            mem=guild.max_presences))
        # Features
        if guild.features != []:
            features_tr = await self.bot._(ctx.guild.id,"stats_infos","guild-features")
            features = [features_tr[x] if x in features_tr.keys() else x for x in guild.features]
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-9"), value=" - ".join(features))
        if critical_info:
            # A2F activation
            if guild.mfa_level:
                a2f = await self.bot._(ctx.guild.id,"keywords","oui")
            else:
                a2f = await self.bot._(ctx.guild.id,"keywords","non")
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-8"), value=a2f.capitalize())
            # Verification level
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-9"), value=str(await self.bot._(ctx.guild.id,"keywords",str(guild.verification_level))).capitalize())
        await ctx.send(embed=embed)
        
   
    async def invite_info(self, ctx: MyContext, invite: discord.Invite, lang: str):
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.bot._(ctx.guild.id,"stats_infos","inv-4"),invite.code), icon_url=invite.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=str(await self.bot.user_avatar_as(ctx.author,size=256)))
        # Try to get the complete invite
        if invite.guild in self.bot.guilds:
            try:
                temp = [x for x in await invite.guild.invites() if x.id == invite.id]
                if len(temp) > 0:
                    invite = temp[0]
            except discord.errors.Forbidden:
                pass
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,ctx)
        # Invite URL
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-0"), value=invite.url,inline=True)
        # Inviter
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-1"), value=str(invite.inviter) if invite.inviter!= None else await self.bot._(ctx.guild,'keywords','unknown'))
        # Invite uses
        if invite.max_uses is not None and invite.uses is not None:
            if invite.max_uses == 0:
                uses = "{}/∞".format(invite.uses)
            else:
                uses = "{}/{}".format(invite.uses,invite.max_uses)
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-2"), value=uses)
        # Duration
        if invite.max_age is not None:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-3"), value=str(invite.max_age) if invite.max_age != 0 else "∞")
        if isinstance(invite.channel,(discord.PartialInviteChannel,discord.abc.GuildChannel)):
            # Guild name
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-0"), value=str(invite.guild.name))
            # Channel name
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","textchan-5"), value="#"+str(invite.channel.name))
            # Guild icon
            url = str(invite.guild.icon_url)
            if url:
                r = requests.get(url.replace(".webp",".gif"))
                if r.ok:
                    url = url.replace(".webp",".gif")
                else:
                    url = url.replace(".webp",".png")
                embed.set_thumbnail(url=url)
            # Guild ID
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-6"), value=str(invite.guild.id))
            # Members count
            if invite.approximate_member_count:
                embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-7"), value=str(invite.approximate_member_count))
        # Guild banner
        if invite.guild.banner_url is not None:
            embed.set_image(url=invite.guild.banner_url)
        # Guild description
        if invite.guild.description is not None and len(invite.guild.description) > 0:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-8"), value=invite.guild.description)
        # Guild features
        if len(invite.guild.features) > 0:
            features_tr = await self.bot._(ctx.guild.id,"stats_infos","guild-features")
            features = [features_tr[x] if x in features_tr.keys() else x for x in invite.guild.features]
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","inv-9"), value=" - ".join(features))
        # Creation date
        if invite.created_at is not None:
            embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.TimeUtils.date(invite.created_at,lang=lang,year=True),since,await self.TimeUtils.time_delta(invite.created_at,datetime.datetime.utcnow(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        await ctx.send(embed=embed)

    async def category_info(self, ctx: MyContext, categ: discord.CategoryChannel, lang: str):
        if not categ.permissions_for(ctx.author).view_channel:
            await ctx.send(await self.bot._(ctx.guild.id, "infos", "cant-see-channel"))
            return
        since = await self.bot._(ctx.guild.id,"keywords","depuis")
        tchan = 0
        vchan = 0
        for channel in categ.channels:
            if type(channel)==discord.TextChannel:
                tchan += 1
            elif type(channel) == discord.VoiceChannel:
                vchan +=1
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.bot._(ctx.guild.id,"stats_infos","categ-0"),categ.name), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)

        embed.add_field(name=str(await self.bot._(ctx.guild.id,"keywords","nom")).capitalize(), value=categ.name,inline=True)
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","role-0"), value=str(categ.id))
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","categ-1"), value="{}/{}".format(categ.position+1,len(ctx.guild.categories)))
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","guild-6"), value=str(await self.bot._(ctx.guild.id,"stats_infos","categ-2")).format(tchan,vchan))
        embed.add_field(name=await self.bot._(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.TimeUtils.date(categ.created_at,lang=lang,year=True),since,await self.TimeUtils.time_delta(categ.created_at,datetime.datetime.utcnow(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        await ctx.send(embed=embed)
    
    async def snowflake_infos(self, ctx: MyContext, snowflake: args.snowflake, lang: str):
        date = await self.bot.get_cog("TimeUtils").date(snowflake.date,lang,year=True)
        embed = await self.bot.get_cog("Embeds").Embed(color = default_color, time = ctx.message.created_at, fields = [
            {"name": await self.bot._(ctx.channel,"stats_infos","snowflake-0"), "value": date, "inline": True},
            {"name": await self.bot._(ctx.channel,"stats_infos","snowflake-2"), "value": round(snowflake.date.timestamp()), "inline": True},
            {"name": await self.bot._(ctx.channel,"stats_infos","snowflake-1"), "value": snowflake.binary, "inline": False},
            {"name": await self.bot._(ctx.channel,"stats_infos","snowflake-3"), "value": snowflake.worker_id, "inline": True},
            {"name": await self.bot._(ctx.channel,"stats_infos","snowflake-4"), "value": snowflake.process_id, "inline": True},
            {"name": await self.bot._(ctx.channel,"stats_infos","snowflake-5"), "value": snowflake.increment, "inline": True}
        ]).create_footer(ctx)
        await ctx.send(embed=embed)


    @commands.group(name="find")
    @commands.check(reloads.is_support_staff)
    @commands.check(in_support_server)
    async def find_main(self, ctx: MyContext):
        """Same as info, but in a lighter version"""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.bot._(ctx.channel,"find","help"))

    @find_main.command(name="user")
    async def find_user(self, ctx: MyContext, *, user:discord.User):
        use_embed = ctx.can_send_embed
        # Servers list
        servers_in = list()
        owned, membered = 0, 0
        for s in user.mutual_guilds:
            if s.owner==user:
                servers_in.append(":crown: "+s.name)
                owned += 1
            else:
                servers_in.append("- "+s.name)
                membered += 1
        if len(servers_in) == 0:
            servers_in = ["No server"]
        elif len("\n".join(servers_in)) > 1020:
            servers_in = [f"{owned} serveurs possédés, membre sur {membered} autres serveurs"]
        # XP card
        xp_card = await self.bot.get_cog('Utilities').get_xp_style(user)
        # Flags
        userflags: list = await self.bot.get_cog('Users').get_userflags(user)
        if await self.bot.get_cog("Admin").check_if_admin(user):
            userflags.append('admin')
        if len(userflags) == 0:
            userflags = ["None"]
        # Votes
        votes = await ctx.bot.get_cog("Utilities").check_votes(user.id)
        if use_embed:
            votes = " - ".join([f"[{x[0]}]({x[1]})" for x in votes])
        else:
            votes = " - ".join([x[0] for x in votes])
        if len(votes) == 0:
            votes = "Nowhere"
        # Languages
        disp_lang = list()
        for lang in await self.bot.get_cog('Utilities').get_languages(user):
            disp_lang.append('{} ({}%)'.format(lang[0],round(lang[1]*100)))
        if len(disp_lang) == 0:
            disp_lang = ["Unknown"]
        # User name
        user_name = str(user)+' <:BOT:544149528761204736>' if user.bot else str(user)
        # XP sus
        xp_sus = "Unknown"
        if Xp := self.bot.get_cog("Xp"):
            if Xp.sus is not None:
                xp_sus = str(user.id in Xp.sus)
        # ----
        if use_embed:
            if ctx.guild is None:
                color = None
            else:
                color = None if ctx.guild.me.color.value == 0 else ctx.guild.me.color
            
            await ctx.send(embed = await self.bot.get_cog('Embeds').Embed(title=user_name, thumbnail=str(await self.bot.user_avatar_as(user,1024)) ,color=color, fields = [
                {"name": "ID", "value": user.id},
                {"name": "Flags", "value": "-".join(userflags), "inline":False},
                {"name": "Servers", "value": "\n".join(servers_in), "inline":True},
                {"name": "Language", "value": "\n".join(disp_lang), "inline":True},
                {"name": "XP card", "value": xp_card, "inline":True},
                {"name": "Upvoted the bot?", "value": votes, "inline":True},
                {"name": "XP sus?", "value": xp_sus, "inline":True},
            ]).create_footer(ctx))
        else:
            txt = """Name: {}
ID: {}
Perks: {}
Language: {}
XP card: {}
Voted? {}
Servers:
{}""".format(user_name,
                user.id,
                " - ".join(userflags),
                " - ".join(disp_lang),
                xp_card,
                votes,
                "\n".join(servers_in)
                )
            await ctx.send(txt)

    @find_main.command(name="guild",aliases=['server'])
    async def find_guild(self, ctx: MyContext, *, guild: str):
        if guild.isnumeric():
            guild = ctx.bot.get_guild(int(guild))
        else:
            for x in self.bot.guilds:
                if x.name==guild:
                    guild = x
                    break
        if isinstance(guild, str) or guild is None:
            await ctx.send(await self.bot._(ctx.channel,"find","guild-0"))
            return
        msglang = await self.bot._(ctx.channel,'current_lang','current')
        # Bots
        bots = len([x for x in guild.members if x.bot])
        # Lang
        lang = await ctx.bot.get_config(guild.id,'language')
        if lang is None:
            lang = 'default'
        else:
            lang = ctx.bot.get_cog('Languages').languages[lang]
        # Roles rewards
        rr_len = await self.bot.get_config(guild.id,'rr_max_number')
        rr_len = self.bot.get_cog("Servers").default_opt['rr_max_number'] if rr_len is None else rr_len
        rr_len = '{}/{}'.format(len(await self.bot.get_cog('Xp').rr_list_role(guild.id)),rr_len)
        # Prefix
        class FakeMsg:
            pass
        fake_msg = FakeMsg
        fake_msg.guild = guild
        pref = (await self.bot.get_prefix(fake_msg))[2]
        if "`" not in pref:
            pref = "`" + pref + "`"
        # Rss
        rss_len = await self.bot.get_config(guild.id,'rss_max_number')
        rss_len = self.bot.get_cog("Servers").default_opt['rss_max_number'] if rss_len is None else rss_len
        rss_numb = "{}/{}".format(len(await self.bot.get_cog('Rss').get_guild_flows(guild.id)), rss_len)
        # Join date
        joined_at = await self.bot.get_cog('TimeUtils').date(guild.me.joined_at,msglang,year=True,digital=True)
        # ----
        if ctx.can_send_embed:
            if ctx.guild is None:
                color = None
            else:
                color = None if ctx.guild.me.color.value == 0 else ctx.guild.me.color
            guild_icon = str(guild.icon_url_as(format = "gif" if guild.is_icon_animated() else 'png'))
            await ctx.send(embed = await self.bot.get_cog('Embeds').Embed(title=guild.name, color=color, thumbnail=guild_icon, fields=[
                {"name": "ID", "value": guild.id},
                {"name": "Owner", "value": "{} ({})".format(guild.owner, guild.owner_id)},
                {"name": "Joined at", "value": joined_at},
                {"name": "Members", "value": guild.member_count, "inline":True},
                {"name": "Language", "value": lang, "inline":True},
                {"name": "Prefix", "value": pref, "inline":True},
                {"name": "RSS feeds count", "value": rss_numb, "inline":True},
                {"name": "Roles rewards count", "value": rr_len, "inline":True},
            ]).create_footer(ctx))
        else:
            txt = str(await self.bot._(ctx.channel,"find","guild-1")).format(name = guild.name,
                id = guild.id,
                owner = guild.owner,
                ownerid = guild.owner_id,
                join = joined_at,
                members = guild.member_count,
                bots = bots,
                lang = lang,
                prefix = pref,
                rss = rss_numb,
                rr = rr_len)
            await ctx.send(txt)

    @find_main.command(name='channel')
    async def find_channel(self, ctx: MyContext, ID:int):
        c = self.bot.get_channel(ID)
        if c is None:
            await ctx.send(await self.bot._(ctx.channel,"find","chan-0"))
            return
        if ctx.can_send_embed:
            if ctx.guild is None:
                color = None
            else:
                color = None if ctx.guild.me.color.value == 0 else ctx.guild.me.color
            await ctx.send(embed = await self.bot.get_cog('Embeds').Embed(title="#"+c.name,color=color,fields=[
                {"name": "ID", "value": c.id},
                {"name": "Server", "value": f"{c.guild.name} ({c.guild.id})"}
            ]).create_footer(ctx))
        else:
            await ctx.send(await self.bot._(ctx.channel,"find","chan-1").format(c.name,c.id,c.guild.name,c.guild.id))
    
    @find_main.command(name='role')
    async def find_role(self, ctx: MyContext, ID:int):
        every_roles = list()
        for serv in ctx.bot.guilds:
            every_roles += serv.roles
        role = discord.utils.find(lambda role:role.id==ID,every_roles)
        if role is None:
            await ctx.send(await self.bot._(ctx.channel,"find","role-0"))
            return
        if ctx.can_send_embed:
            if ctx.guild is None:
                color = None
            else:
                color = None if ctx.guild.me.color.value == 0 else ctx.guild.me.color
            await ctx.send(embed = await self.bot.get_cog('Embeds').Embed(title="@"+role.name,color=color,fields=[
                {"name": "ID", "value": role.id},
                {"name": "Server", "value": f"{role.guild.name} ({role.guild.id})"},
                {"name": "Members", "value": len(role.members), "inline": True},
                {"name": "Colour", "value": str(role.colour), "inline": True}
            ]).create_footer(ctx))
        else:
            await ctx.send(await self.bot._(ctx.channel,"find","role-1").format(role.name,role.id,role.guild.name,role.guild.id,len(role.members),role.colour))
    
    @find_main.command(name='rss')
    async def find_rss(self, ctx: MyContext, ID:int):
        flow = await self.bot.get_cog('Rss').get_flow(ID)
        if len(flow) == 0:
            await ctx.send("Invalid ID")
            return
        else:
            flow = flow[0]
        temp = self.bot.get_guild(flow['guild'])
        if temp is None:
            g = "Unknown ({})".format(flow['guild'])
        else:
            g = "`{}`\n{}".format(temp.name,temp.id)
            temp = self.bot.get_channel(flow['channel'])
        if temp is not None:
            c = "`{}`\n{}".format(temp.name,temp.id)
        else:
            c = "Unknown ({})".format(flow['channel'])
        d = await self.bot.get_cog('TimeUtils').date(flow['date'],digital=True)
        if d is None or len(d) == 0:
            d = "never"
        if ctx.can_send_embed:
            if ctx.guild is None:
                color = None
            else:
                color = None if ctx.guild.me.color.value == 0 else ctx.guild.me.color
            await ctx.send(embed = await self.bot.get_cog('Embeds').Embed(title=f"RSS N°{ID}",color=color,fields=[
                {"name": "Server", "value": g, "inline": True},
                {"name": "Channel", "value": c, "inline": True},
                {"name": "URL", "value": flow['link']},
                {"name": "Type", "value": flow['type'], "inline": True},
                {"name": "Last post", "value": d, "inline": True},
            ]).create_footer(ctx))
        else:
            await ctx.send("ID: {}\nGuild: {}\nChannel: {}\nLink: <{}>\nType: {}\nLast post: {}".format(flow['ID'],g.replace("\n"," "),c.replace("\n"," "),flow['link'],flow['type'],d))

    @commands.command(name="membercount",aliases=['member_count'])
    @commands.guild_only()
    @commands.bot_has_permissions(send_messages=True)
    async def membercount(self, ctx: MyContext):
        """Get some digits on the number of server members
        
        ..Doc infos.html#membercount"""
        if ctx.channel.permissions_for(ctx.guild.me).send_messages == False:
            return
        total, bots, c_co = await self.bot.get_cog("Utilities").get_members_repartition(ctx.guild.members)
        h = total - bots
        h_p = "< 1" if 0 < h / total < 0.01 else ("> 99" if 1 > h/total > 0.99 else round(h*100/total))
        b_p = "< 1" if 0 < bots / total < 0.01 else ("> 99" if 1 > bots/total > 0.99 else round(bots*100/total))
        c_p = "< 1" if 0 < c_co / total < 0.01 else ("> 99" if 1 > c_co/total > 0.99 else round(c_co*100/total))
        l = [(await self.bot._(ctx.guild.id, "infos_2", "membercount-0"), str(total)),
             (await self.bot._(ctx.guild.id, "infos_2", "membercount-2"), "{} ({}%)".format(h, h_p)),
             (await self.bot._(ctx.guild.id, "infos_2", "membercount-1"), "{} ({}%)".format(bots, b_p)),
             (await self.bot._(ctx.guild.id, "infos_2", "membercount-3"), "{} ({}%)".format(c_co, c_p))]
        if ctx.can_send_embed:
            embed = discord.Embed(colour=ctx.guild.me.color)
            for i in l:
                embed.add_field(name=i[0], value=i[1], inline=True)
            await ctx.send(embed=embed)
        else:
            text = str()
            for i in l:
                text += "- {i[0]} : {i[1]}\n".format(i=i)
            await ctx.send(text)

    @commands.group(name="prefix")
    async def get_prefix(self, ctx: MyContext):
        """Show the usable prefix(s) for this server
        
        ..Doc infos.html#prefix"""
        if ctx.invoked_subcommand is not None:
            return
        txt = await self.bot._(ctx.channel,"infos","prefix")
        prefix = "\n".join((await ctx.bot.get_prefix(ctx.message))[1:])
        if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me):
            emb = await ctx.bot.get_cog('Embeds').Embed(title=txt,desc=prefix,time=ctx.message.created_at,color=ctx.bot.get_cog('Help').help_color).create_footer(ctx)
            return await ctx.send(embed=emb.discord_embed())
        await ctx.send(txt+"\n"+prefix)
    
    @get_prefix.command(name="change")
    @commands.guild_only()
    async def prefix_change(self, ctx: MyContext, *, new_prefix: str):
        """Change the used prefix
        
        ..Example prefix change "Hey Zbot, "

        ..Doc infos.html#prefix"""
        msg: discord.Message = copy.copy(ctx.message)
        if new_prefix.startswith('"') and new_prefix.endswith('"'):
            new_prefix = new_prefix[1:-1]
        msg.content =  f'{ctx.prefix}config change prefix "{new_prefix}"'
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)
    
    @commands.command(name="discordlinks",aliases=['discord','discordurls'])
    async def discord_status(self, ctx: MyContext):
        """Get some useful links about Discord"""
        l = await self.bot._(ctx.channel,'infos','discordlinks')
        links = ["https://dis.gd/status","https://dis.gd/tos","https://dis.gd/report","https://dis.gd/feedback","https://support.discord.com/hc/en-us/articles/115002192352","https://discord.com/developers/docs/legal","https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-","https://support.discord.com/hc/en-us/articles/360040724612", " https://twitter.com/discordapp/status/1060411427616444417", "https://support.discord.com/hc/en-us/articles/360035675191"]
        if ctx.can_send_embed:
            txt = "\n".join(['['+l[i]+']('+links[i]+')' for i in range(len(l))])
            em = await self.bot.get_cog("Embeds").Embed(desc=txt).update_timestamp().create_footer(ctx)
            await ctx.send(embed=em)
        else:
            txt = "\n".join([f'• {l[i]}: <{links[i]}>' for i in range(len(l))])
            await ctx.send(txt)
    

    async def emoji_analysis(self, msg: discord.Message):
        """Lists the emojis used in a message"""
        try:
            if not self.bot.database_online:
                return
            ctx = await self.bot.get_context(msg)
            if ctx.command is not None:
                return
            liste = list(set(re.findall(r'<a?:[\w-]+:(\d{18})>',msg.content)))
            if len(liste) == 0:
                return
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor()
            current_timestamp = datetime.datetime.fromtimestamp(round(time.time()))
            query = "INSERT INTO `{}` (`ID`,`count`,`last_update`) VALUES (%(i)s, 1, %(l)s) ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = %(l)s;".format(self.emoji_table)
            for data in [{ 'i': x, 'l': current_timestamp } for x in liste]:
                cursor.execute(query, data)
            cnx.commit()
            cursor.close()
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,None)
    
    async def get_emojis_info(self, ID: typing.Union[int,list]):
        """Get info about an emoji"""
        if not self.bot.database_online:
            return list()
        if isinstance(ID,int):
            query = "Select * from `{}` WHERE `ID`={}".format(self.emoji_table,ID)
        else:
            query = "Select * from `{}` WHERE {}".format(self.emoji_table,"OR".join([f'`ID`={x}' for x in ID]))
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        cursor.execute(query)
        liste = list()
        for x in cursor:
            x['emoji'] = self.bot.get_emoji(x['ID'])
            liste.append(x)
        cursor.close()
        return liste
    

    @commands.group(name="bitly")
    async def bitly_main(self, ctx: MyContext):
        """Bit.ly website, but in Discord
        Create shortened url and unpack them by using Bitly services
        
        ..Doc miscellaneous.html#bitly-urls"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx,['bitly'])
        elif ctx.invoked_subcommand is None and ctx.subcommand_passed is not None:
            try:
                url = await args.url().convert(ctx,ctx.subcommand_passed)
            except:
                return
            if url.domain in ['bit.ly','bitly.com','bitly.is']:
                msg = copy.copy(ctx.message)
                msg.content = ctx.prefix + 'bitly find '+url.url
                new_ctx = await self.bot.get_context(msg)
                await self.bot.invoke(new_ctx)
            else:
                msg = copy.copy(ctx.message)
                msg.content = ctx.prefix + 'bitly create '+url.url
                new_ctx = await self.bot.get_context(msg)
                await self.bot.invoke(new_ctx)

    @bitly_main.command(name="create")
    async def bitly_create(self, ctx: MyContext, url: args.url):
        """Create a shortened url
        
        ..Example bitly create https://fr-minecraft.net

        ..Doc miscellaneous.html#bitly-urls"""
        await ctx.send(await self.bot._(ctx.channel,'infos','bitly_short',url=self.BitlyClient.shorten_url(url.url)))
    
    @bitly_main.command(name="find")
    async def bitly_find(self, ctx: MyContext, url: args.url):
        """Find the long url from a bitly link
        
        ..Example bitly find https://bit.ly/2JEHsUf
        
        ..Doc miscellaneous.html#bitly-urls"""
        if url.domain != 'bit.ly':
            return await ctx.send(await self.bot._(ctx.channel,'infos','bitly_nobit'))
        await ctx.send(await self.bot._(ctx.channel,'infos','bitly_long',url=self.BitlyClient.expand_url(url.url)))
    
    @commands.command(name='changelog',aliases=['changelogs'])
    @commands.check(checks.database_connected)
    async def changelog(self, ctx: MyContext, version: str=None):
        """Get the changelogs of the bot
        
        ..Example changelog

        ..Example changelog 3.7.0

        ..Doc miscellaneous.html#changelogs"""
        if version=='list':
            cnx = self.bot.cnx_frm
            if not ctx.bot.beta:
                query = "SELECT `version`, CONVERT_TZ(`release_date`, @@session.time_zone, '+00:00') AS `utc_release` FROM `changelogs` WHERE beta=False ORDER BY release_date"
            else:
                query = f"SELECT `version`, CONVERT_TZ(`release_date`, @@session.time_zone, '+00:00') AS `utc_release` FROM `changelogs` ORDER BY release_date"
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(query)
            results = list(cursor)
            cursor.close()
            desc = "\n".join(reversed(["**v{}:** {}".format(x['version'],x['utc_release']) for x in results]))
            time = discord.Embed.Empty
            title = await self.bot._(ctx.channel,'infos','changelogs-index')
        else:
            if version is None:
                if not ctx.bot.beta:
                    query = "SELECT *, CONVERT_TZ(`release_date`, @@session.time_zone, '+00:00') AS `utc_release` FROM `changelogs` WHERE beta=False ORDER BY release_date DESC LIMIT 1"
                else:
                    query = f"SELECT *, CONVERT_TZ(`release_date`, @@session.time_zone, '+00:00') AS `utc_release` FROM `changelogs` ORDER BY release_date DESC LIMIT 1"
            else:
                query = f"SELECT *, CONVERT_TZ(`release_date`, @@session.time_zone, '+00:00') AS `utc_release` FROM `changelogs` WHERE `version`='{version}'"
                if not ctx.bot.beta:
                    query += " AND `beta`=0"
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary=True)
            cursor.execute(query)
            results = list(cursor)
            cursor.close()
            if len(results) > 0:
                used_lang = await self.bot._(ctx.channel,'current_lang','current')
                if used_lang not in results[0].keys():
                    used_lang = "en"
                desc = results[0][used_lang]
                time = results[0]['utc_release']
                title = (await self.bot._(ctx.channel,'keywords','version')).capitalize() + ' ' + results[0]['version']
        if len(results) == 0:
            await ctx.send(await self.bot._(ctx.channel,'infos','changelog-notfound'))
        elif ctx.can_send_embed:
            emb = ctx.bot.get_cog('Embeds').Embed(title=title,desc=desc,time=time,color=ctx.bot.get_cog('Servers').embed_color)
            await ctx.send(embed=emb)
        else:
            await ctx.send(desc)

    @commands.command(name="usernames", aliases=["username","usrnm"])
    @commands.check(checks.database_connected)
    async def username(self, ctx: MyContext, *, user: discord.User=None):
        """Get the names history of an user
        Default user is you
        
        ..Doc infos.html#usernames-history"""
        if user is None:
            user = ctx.author
        language = await self.bot._(ctx.channel,"current_lang","current")
        cond = f"user='{user.id}'"
        if not self.bot.beta:
            cond += " AND beta=0"
        query = f"SELECT `old`, `new`, `guild`, CONVERT_TZ(`date`, @@session.time_zone, '+00:00') AS `utc_date` FROM `usernames_logs` WHERE {cond} ORDER BY date DESC"
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        cursor.execute(query)
        results = list(cursor)
        cursor.close()
        # List creation
        this_guild = list()
        global_list = [x for x in results if x['guild'] in (None,0)]
        if ctx.guild is not None:
            this_guild = [x for x in results if x['guild']==ctx.guild.id]
        # title
        t = await self.bot._(ctx.channel,'infos','usernames-title',u=user.name)
        # Embed creation
        if ctx.can_send_embed:
            MAX = 28
            date = ""
            desc = None
            f = list()
            if len(global_list) > 0:
            # Usernames part
                temp = [x['new'] for x in global_list if x['new']!='']
                if len(temp) > 0:
                    if len(temp) > MAX:
                        temp = temp[:MAX] + [await self.bot._(ctx.channel, 'infos', 'usernames-more', nbr=len(temp)-MAX)]
                    f.append({'name':await self.bot._(ctx.channel,'infos','usernames-global'), 'value':"\n".join(temp)})
                    # if global_list[-1]['old'] != '':
                    #     f[-1]["value"] += "\n" + global_list[-1]['old']
                    date += await self.bot.get_cog('TimeUtils').date([x['utc_date'] for x in global_list][0] ,year=True, lang=language)
            if len(this_guild) > 0:
            # Nicknames part
                temp = [x['new'] for x in this_guild if x['new']!='']
                if len(temp) > 0:
                    if len(temp) > MAX:
                        temp = temp[:MAX] + [await self.bot._(ctx.channel, 'infos', 'usernames-more', nbr=len(temp)-MAX)]
                    f.append({'name':await self.bot._(ctx.channel,'infos','usernames-local'), 'value':"\n".join(temp)})
                    # if this_guild[-1]['old'] != '':
                    #     f[-1]["value"] += "\n" + this_guild[-1]['old']
                    date += "\n" + await self.bot.get_cog('TimeUtils').date([x['utc_date'] for x in this_guild][0], year=True, lang=language)
            if len(date) > 0:
                f.append({'name':await self.bot._(ctx.channel,'infos','usernames-last-date'), 'value':date})
            else:
                desc = await self.bot._(ctx.channel,'infos','usernames-empty')
            if ctx.guild is not None and ctx.guild.get_member(user.id) is not None and ctx.guild.get_member(user.id).color!=discord.Color(0):
                c = ctx.guild.get_member(user.id).color
            else:
                c = 1350390
            allowing_logs = await self.bot.get_cog("Utilities").get_db_userinfo(["allow_usernames_logs"],["userID="+str(user.id)])
            if allowing_logs is None or allowing_logs["allow_usernames_logs"]:
                footer = await self.bot._(ctx.channel,'infos','usernames-disallow')
            else:
                footer = await self.bot._(ctx.channel,'infos','usernames-allow')
            emb = self.bot.get_cog('Embeds').Embed(title=t,fields=f,desc=desc,color=c,footer_text=footer)
            await ctx.send(embed=emb)
        # Raw text creation
        else:
            MAX = 25
            text = ""
            if len(global_list) > 0:
                temp = [x['new'] for x in global_list if x['new']!='']
                if len(temp) > MAX:
                    temp = temp[:MAX] + [await self.bot._(ctx.channel, 'infos', 'usernames-more', nbr=len(temp)-MAX)]
                text += "**" + await self.bot._(ctx.channel,'infos','usernames-global') + "**\n" + "\n".join(temp)
            if len(this_guild) > 0:
                if len(text) > 0:
                    text += "\n\n"
                temp = [x['new'] for x in this_guild if x['new']!='']
                if len(temp) > MAX:
                    temp = temp[:MAX] + [await self.bot._(ctx.channel, 'infos', 'usernames-more', nbr=len(temp)-MAX)]
                text += "**" + await self.bot._(ctx.channel,'infos','usernames-local') + "**\n" + "\n".join(temp)
            if len(text) == 0:
                # no change known
                text = await self.bot._(ctx.channel, 'infos', 'usernames-empty')
            await ctx.send(text)


def setup(bot):
    bot.add_cog(Info(bot))
    
