from classes import zbot, MyContext
import discord
import datetime
import time
import re
import asyncio
import mysql
import random
import typing
import importlib
import socket
import requests
import twitter
from libs import feedparser
from discord.ext import commands
from fcts import reloads, args, checks
# importlib.reload(reloads)
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

yt_link={'grand_corbeau':'UCAt_W0Rgr33OePJ8jylkx0A',
         'mojang':'UC1sELGmy5jp5fQUugmuYlXQ',
         'frm':'frminecraft',
         'fr-minecraft':'frminecraft',
         'freebuild':'UCFl41Y9Hf-BtZBn7LGPHNAQ',
         'fb':'UCFl41Y9Hf-BtZBn7LGPHNAQ',
         'aurelien_sama':'AurelienSama',
         'asilis':'UC2_9zcNSfEBecm3yaojexXw',
         'leirof':'UCimA2SBz78Mj-TQ2n4TmEVw',
         'gunivers':'UCtQb5O95cCGp9iquLjY9O1g',
         'platon_neutron':'UC2xPiOqjQ-nZeCka_ZNCtCQ',
         'aragorn1202':'UCjDG6KLKOm6_8ax--zgeB6Q'
         }


async def check_admin(ctx: MyContext):
    return await ctx.bot.cogs['AdminCog'].check_if_admin(ctx)

async def can_use_rss(ctx: MyContext):
    if ctx.guild is None:
        return False
    return ctx.channel.permissions_for(ctx.author).manage_guild or await ctx.bot.cogs["AdminCog"].check_if_admin(ctx)

class RssCog(commands.Cog):
    """Cog which deals with everything related to rss flows. Whether it is to add automatic tracking to a stream, or just to see the latest video released by Discord, it is this cog that will be used."""

    def __init__(self, bot: zbot):
        self.bot = bot
        self.time_loop = 10
        self.time_between_flows_check = 0.15
        
        self.file = "rss2"
        self.embed_color = discord.Color(6017876)
        self.loop_processing = False
        self.last_update = None
        self.twitterAPI = twitter.Api(**bot.others['twitter'], tweet_mode="extended")
        self.twitter_over_capacity = False
        self.min_time_between_posts = {
            'web': 120,
            'tw': 15,
            'yt': 120
        }
        self.cache = dict()
        if bot.user is not None:
            self.table = 'rss_flow' if bot.user.id==486896267788812288 else 'rss_flow_beta'
        try:
            self.date = bot.cogs["TimeCog"].date
        except:
            pass
        if feedparser.parse('http://twitrss.me/twitter_user_to_rss/?user=Dinnerbone').entries == list():
            self.twitter_api_url = 'http://twitrss.me/mobile_twitter_to_rss/?user='
        else:
            self.twitter_api_url = 'http://twitrss.me/twitter_user_to_rss/?user='

    @commands.Cog.listener()
    async def on_ready(self):
        self.date = self.bot.cogs["TimeCog"].date
        self.table = 'rss_flow' if self.bot.user.id==486896267788812288 else 'rss_flow_beta'


    class rssMessage:
        def __init__(self,bot:zbot,Type,url,title,emojis,date=datetime.datetime.now(),author=None,Format=None,channel=None,retweeted_by=None,image=None):
            self.bot = bot
            self.Type = Type
            self.url = url
            self.title = title
            self.embed = False # WARNING COOKIES WARNINNG
            self.image = image
            if type(date) == datetime.datetime:
                self.date = date
            elif type(date) == time.struct_time:
                self.date = datetime.datetime(*date[:6])
            elif type(date) == str:
                self.date = date
            else:
                date = None
            self.author = author
            self.format = Format
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
            self.rt_by = retweeted_by
            if self.author is None:
                self.author = channel
        
        def fill_embed_data(self, flow: dict):
            self.embed_data = {'color':discord.Colour(0).default(),
                'footer':'',
                'title':None}
            if flow['embed_title'] != '':
                self.embed_data['title'] = flow['embed_title'][:256]
            if flow['embed_footer'] != '':
                self.embed_data['footer'] = flow['embed_footer'][:2048]
            if flow['embed_color'] != 0:
                self.embed_data['color'] = flow['embed_color']
            return

        async def fill_mention(self, guild: discord.Guild, roles: typing.List[str], translate):
            if roles == []:
                r = await translate(guild.id,"keywords","none")
            else:
                r = list()
                for item in roles:
                    if item=='':
                        continue
                    role = discord.utils.get(guild.roles,id=int(item))
                    if role is not None:
                        r.append(role.mention)
                    else:
                        r.append(item)
                self.mentions = r
            return self

        async def create_msg(self, language, Format=None):
            if Format is None:
                Format = self.format
            if not isinstance(self.date,str):
                d = await self.bot.cogs["TimeCog"].date(self.date,lang=language,year=False,hour=True,digital=True)
            else:
                d = self.date
            Format = Format.replace('\\n','\n')
            if self.rt_by is not None:
                self.author = "{} (retweeted by @{})".format(self.author,self.rt_by)
            text = Format.format_map(self.bot.SafeDict(channel=self.channel,title=self.title,date=d,url=self.url,link=self.url,mentions=", ".join(self.mentions),logo=self.logo,author=self.author))
            if not self.embed:
                return text
            else:
                emb = self.bot.cogs['EmbedCog'].Embed(desc=text,time=self.date,color=self.embed_data['color'],footer_text=self.embed_data['footer'])
                if self.embed_data['title'] is None:
                    if self.Type != 'tw':
                        emb.title = self.title
                    else:
                        emb.title = self.author
                emb.add_field(name='URL',value=self.url)
                if self.image is not None:
                    emb.thumbnail = self.image
                return emb


    @commands.group(name="rss")
    @commands.cooldown(2,15,commands.BucketType.channel)
    async def rss_main(self, ctx: MyContext):
        """See the last post of a rss feed
        
        ..Doc rss.html#rss"""
        if ctx.subcommand_passed is None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['rss'])

    @rss_main.command(name="youtube",aliases=['yt'])
    async def request_yt(self, ctx: MyContext, ID):
        """The last video of a YouTube channel"""
        if ID in yt_link.keys():
            ID = yt_link[ID]
        if "youtube.com" in ID or "youtu.be" in ID:
            ID = await self.parse_yt_url(ID)
        if ID is None:
            return await ctx.send(await self.bot._(ctx.channel, "rss", "web-invalid"))
        text = await self.rss_yt(ctx.channel,ID)
        if type(text) == str:
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel,"rss","yt-form-last")
            obj = await text[0].create_msg(await self.bot._(ctx.channel,"current_lang","current"),form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)
    
    @rss_main.command(name="twitch",aliases=['tv'])
    async def request_twitch(self, ctx: MyContext, channel):
        """The last video of a Twitch channel"""
        if "twitch.tv" in channel:
            channel = await self.parse_twitch_url(channel)
        text = await self.rss_twitch(ctx.channel,channel)
        if type(text) == str:
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel,"rss","twitch-form-last")
            obj = await text[0].create_msg(await self.bot._(ctx.channel,"current_lang","current"),form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)

    @rss_main.command(name='twitter',aliases=['tw'])
    async def request_tw(self, ctx: MyContext, name):
        """The last tweet of a Twitter account"""
        if "twitter.com" in name:
            name = await self.parse_tw_url(name)
        try:
            text = await self.rss_tw(ctx.channel,name)
        except Exception as e:
            return await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
        if type(text) == str:
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel,"rss","tw-form-last")
            for single in text[:5]:
                obj = await single.create_msg(await self.bot._(ctx.channel,"current_lang","current"),form)
                if isinstance(obj,discord.Embed):
                    await ctx.send(embed=obj)
                else:
                    await ctx.send(obj)

    @rss_main.command(name="web")
    async def request_web(self, ctx: MyContext, link):
        """The last post on any other rss feed"""
        if link in web_link.keys():
            link = web_link[link]
        text = await self.rss_web(ctx.channel,link)
        if type(text) == str:
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel,"rss","web-form-last")
            obj = await text[0].create_msg(await self.bot._(ctx.channel,"current_lang","current"),form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)
    
    @rss_main.command(name="deviantart",aliases=['deviant'])
    async def request_deviant(self, ctx: MyContext, user):
        """The last pictures of a DeviantArt user"""
        if "deviantart.com" in user:
            user = await self.parse_deviant_url(user)
        text = await self.rss_deviant(ctx.guild,user)
        if type(text) == str:
            await ctx.send(text)
        else:
            form = await self.bot._(ctx.channel,"rss","deviant-form-last")
            obj = await text[0].create_msg(await self.bot._(ctx.channel,"current_lang","current"),form)
            if isinstance(obj,discord.Embed):
                await ctx.send(embed=obj)
            else:
                await ctx.send(obj)


    async def is_overflow(self, guild: discord.Guild) -> typing.Tuple[bool, int]:
        """Check if a guild still has at least a slot
        True if max number reached, followed by the flow limit"""
        flow_limit = await self.bot.cogs['ServerCog'].find_staff(guild.id,'rss_max_number')
        if flow_limit is None:
            flow_limit = self.bot.cogs['ServerCog'].default_opt['rss_max_number']
        return len(await self.get_guild_flows(guild.id)) >= flow_limit, flow_limit

    @rss_main.command(name="add")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def system_add(self, ctx: MyContext, link):
        """Subscribe to a rss feed, displayed on this channel regularly
        
        ..Doc rss.html#follow-a-feed"""
        is_over, flow_limit = await self.is_overflow(ctx.guild)
        if is_over:
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","flow-limit")).format(flow_limit))
            return
        identifiant = await self.parse_yt_url(link)
        Type = None
        if identifiant is not None:
            Type = 'yt'
            display_type = 'youtube'
        if identifiant is None:
            identifiant = await self.parse_tw_url(link)
            if identifiant is not None:
                Type = 'tw'
                display_type = 'twitter'
        if identifiant is None:
            identifiant = await self.parse_twitch_url(link)
            if identifiant is not None:
                Type = 'twitch'
                display_type = 'twitch'
        if identifiant is None:
            identifiant = await self.parse_deviant_url(link)
            if identifiant is not None:
                Type = 'deviant'
                display_type = 'deviantart'
        if identifiant is not None and not link.startswith("https://"):
            link = "https://"+link
        if identifiant is None and link.startswith("http"):
            identifiant = link
            Type = "web"
            display_type = 'website'
        elif not link.startswith("http"):
            await ctx.send(await self.bot._(ctx.guild,"rss","invalid-link"))
            return
        if Type is None or not await self.check_rss_url(link):
            return await ctx.send(await self.bot._(ctx.guild.id,"rss","invalid-flow"))
        try:
            ID = await self.add_flow(ctx.guild.id,ctx.channel.id,Type,identifiant)
            await ctx.send(str(await self.bot._(ctx.guild,"rss","success-add")).format(display_type,link,ctx.channel.mention))
            self.bot.log.info("RSS feed added into server {} ({} - {})".format(ctx.guild.id,link,ID))
            await self.send_log("Feed added into server {} ({})".format(ctx.guild.id,ID),ctx.guild)
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)

    @rss_main.command(name="remove",aliases=['delete'])
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def systeme_rm(self, ctx: MyContext, ID:int=None):
        """Delete an rss feed from the list
        
        ..Doc rss.html#delete-a-followed-feed"""
        flow = []
        if ID is not None:
            flow = await self.get_flow(ID)
            if flow == []:
                ID = None
            elif str(flow[0]['guild']) != str(ctx.guild.id):
                ID = None
        if ID is None:
            userID = ctx.author.id
            gl = await self.get_guild_flows(ctx.guild.id)
            if len(gl) == 0:
                await ctx.send(await self.bot._(ctx.guild.id,"rss","no-feed"))
                return
            text = [await self.bot._(ctx.guild.id,'rss','list2')]
            list_of_IDs = list()
            for e,x in enumerate(gl):
                list_of_IDs.append(x['ID'])
                c = self.bot.get_channel(x['channel'])
                if c is not None:
                    c = c.mention
                else:
                    c = x['channel']
                MAX = e+1
                if len("\n".join(text)) > 1950:
                    embed = self.bot.get_cog("EmbedCog").Embed(title=await self.bot._(ctx.guild.id,"rss","choose-delete"), color=self.embed_color, desc="\n".join(text), time=ctx.message.created_at)
                    await embed.create_footer(ctx)
                    emb_msg = await ctx.send(embed=embed)
                    text = [await self.bot._(ctx.guild.id,'rss','list2')]
                text.append("{}) {} - {} - {}".format(e+1,await self.bot._(ctx.guild.id,'rss',x['type']),x['link'],c))
            if len(text) > 0:
                embed = self.bot.get_cog("EmbedCog").Embed(title=await self.bot._(ctx.guild.id,"rss","choose-delete"), color=self.embed_color, desc="\n".join(text), time=ctx.message.created_at)
                await embed.create_footer(ctx)
                emb_msg = await ctx.send(embed=embed)
            def check(msg):
                if not msg.content.isnumeric():
                    return False
                return msg.author.id==userID and int(msg.content) in range(1,MAX+1)
            try:
                msg = await self.bot.wait_for('message',check=check,timeout=20.0)
            except asyncio.TimeoutError:
                await ctx.send(await self.bot._(ctx.guild.id,"rss","too-long"))
                await self.bot.cogs['UtilitiesCog'].suppr(emb_msg)
                return
            flow = await self.get_flow(list_of_IDs[int(msg.content)-1])
        if len(flow) == 0:
            await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            return
        try:
            await self.remove_flow(flow[0]['ID'])
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            return
        await ctx.send(await self.bot._(ctx.guild,"rss","delete-success"))
        self.bot.log.info("RSS feed deleted into server {} ({})".format(ctx.guild.id,flow[0]['ID']))
        await self.send_log("Feed deleted into server {} ({})".format(ctx.guild.id,flow[0]['ID']),ctx.guild)

    @rss_main.command(name="list")
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(can_use_rss)
    async def list_flows(self, ctx: MyContext):
        """Get a list of every rss/Minecraft feed
        
        ..Doc rss.html#see-every-feed"""
        liste = await self.get_guild_flows(ctx.guild.id)
        l = list()
        translation = await self.bot._(ctx.guild.id,"rss","list-result")
        for x in liste:
            c = self.bot.get_channel(x['channel'])
            if c is not None:
                c = c.mention
            else:
                c = x['channel']
            if x['roles'] == '':
                r = await self.bot._(ctx.guild.id,"keywords","none")
            else:
                r = list()
                for item in x['roles'].split(';'):
                    role = discord.utils.get(ctx.guild.roles,id=int(item))
                    if role is not None:
                        r.append(role.mention)
                    else:
                        r.append(item)
                r = ", ".join(r)
            Type = await self.bot._(ctx.guild.id,'rss',x['type'])
            if len(l) > 20:
                embed = await self.bot.get_cog('EmbedCog').Embed(title="Liste des flux rss du serveur {}".format(ctx.guild.name), color=self.embed_color, time=ctx.message.created_at).create_footer(ctx)
                for text in l:
                    embed.add_field(name="\uFEFF", value=text, inline=False)
                await ctx.send(embed=embed)
                l.clear()
            l.append(translation.format(Type,c,x['link'],r,x['ID'],x['date']))
        if len(l) > 0:
            embed = await self.bot.get_cog('EmbedCog').Embed(title="Liste des flux rss du serveur {}".format(ctx.guild.name), color=self.embed_color, time=ctx.message.created_at).create_footer(ctx)
            for x in l:
                embed.add_field(name="\uFEFF", value=x, inline=False)
            await ctx.send(embed=embed)

    async def askID(self, ID, ctx: MyContext):
        """Demande l'ID d'un flux rss"""
        if ID is not None:
            flow = await self.get_flow(ID)
            if flow == []:
                ID = None
            elif str(flow[0]['guild']) != str(ctx.guild.id) or flow[0]['type']=='mc':
                ID = None
        userID = ctx.author.id
        if ID is None:
            gl = await self.get_guild_flows(ctx.guild.id)
            if len(gl) == 0:
                await ctx.send(await self.bot._(ctx.guild.id,"rss","no-feed"))
                return
            text = [await self.bot._(ctx.guild.id,'rss','list')]
            list_of_IDs = list()
            iterator = 1
            for x in gl:
                if x['type']=='mc':
                    continue
                list_of_IDs.append(x['ID'])
                c = self.bot.get_channel(x['channel'])
                if c is not None:
                    c = c.mention
                else:
                    c = x['channel']
                if x['roles'] == '':
                    r = await self.bot._(ctx.guild.id,"keywords","none")
                else:
                    r = list()
                    for item in x['roles'].split(';'):
                        role = discord.utils.get(ctx.guild.roles,id=int(item))
                        if role is not None:
                            r.append(role.mention)
                        else:
                            r.append(item)
                    r = ", ".join(r)
                text.append("{}) {} - {} - {} - {}".format(iterator,await self.bot._(ctx.guild.id,'rss',x['type']),x['link'],c,r))
                iterator += 1
            if len("\n".join(text)) < 2048:
                desc = "\n".join(text)
                fields = None
            else:
                desc = text[0].split("\n")[0]
                fields = [{'name': text[0].split("\n")[-2], 'value': "\n".join(text[i:i+10])} for i in range(1,len(text), 10)]
            embed = await self.bot.get_cog('EmbedCog').Embed(title=await self.bot._(ctx.guild.id,"rss","choose-mentions-1"), color=self.embed_color, desc=desc, fields=fields, time=ctx.message.created_at).create_footer(ctx)
            emb_msg = await ctx.send(embed=embed)
            def check(msg):
                if not msg.content.isnumeric():
                    return False
                return msg.author.id==userID and int(msg.content) in range(1,iterator)
            try:
                msg = await self.bot.wait_for('message', check = check, timeout = max(10, 1.5*len(text)))
            except asyncio.TimeoutError:
                await ctx.send(await self.bot._(ctx.guild.id,"rss","too-long"))
                await self.bot.cogs['UtilitiesCog'].suppr(emb_msg)
                return
            flow = await self.get_flow(list_of_IDs[int(msg.content)-1])
        return flow

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
    async def roles_flows(self, ctx: MyContext, ID:int=None, *, mentions:typing.Optional[str]):
        """Configures a role to be notified when a news is posted
        If you want to use the @everyone role, please put the server ID instead of the role name.
        
        ..Example rss mentions

        ..Example rss mentions 6678466620137

        ..Example rss mentions 6678466620137 "Announcements" "Twitch subs"

        ..Doc rss.html#mention-a-role"""
        try:
            # ask for flow ID
            flow = await self.askID(ID,ctx)
        except Exception as e:
            flow = []
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
        if flow is None:
            return
        if len(flow) == 0:
            await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
            return
        flow = flow[0]
        no_role = ['aucun','none','_','del']
        if mentions is None: # if no roles was specified: we ask for them
            if flow['roles'] == '':
                text = await self.bot._(ctx.guild.id,"rss","no-roles")
            else:
                r = list()
                for item in flow['roles'].split(';'):
                    role = discord.utils.get(ctx.guild.roles,id=int(item))
                    if role is not None:
                        r.append(role.mention)
                    else:
                        r.append(item)
                r = ", ".join(r)
                text = str(await self.bot._(ctx.guild.id,"rss","roles-list")).format(r)
            # ask for roles
            embed = self.bot.cogs['EmbedCog'].Embed(title=await self.bot._(ctx.guild.id,"rss","choose-roles"), color=discord.Colour(0x77ea5c), desc=text, time=ctx.message.created_at)
            emb_msg = await ctx.send(embed=embed.discord_embed())
            err = await self.bot._(ctx.guild.id,"find",'role-0')
            userID = ctx.author.id
            def check2(msg):
                return msg.author.id == userID
            cond = False
            while cond==False:
                try:
                    msg = await self.bot.wait_for('message', check=check2, timeout=30.0)
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
                            except:
                                await ctx.send(err)
                                IDs = []
                                break
                    if len(IDs) > 0:
                        cond = True
                except asyncio.TimeoutError:
                    await ctx.send(await self.bot._(ctx.guild.id,"rss","too-long"))
                    await self.bot.cogs['UtilitiesCog'].suppr(emb_msg)
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
                    await ctx.send(await self.bot._(ctx.guild.id,"find",'role-0'))
                    return
        try:
            if IDs[0] is None:
                await self.update_flow(flow['ID'],values=[('roles','')])
                await ctx.send(await self.bot._(ctx.guild.id,"rss","roles-1"))
            else:
                await self.update_flow(flow['ID'],values=[('roles',';'.join(IDs))])
                txt = await self.bot.get_cog("UtilitiesCog").clear_msg(", ".join(Names))
                await ctx.send(str(await self.bot._(ctx.guild.id,"rss","roles-0")).format(txt))
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
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
            t = time.time()
            msg = await ctx.send(str(await self.bot._(ctx.guild.id,"rss","guild-loading")).format(ctx.bot.cogs['EmojiCog'].customEmojis['loading']))
            liste = await self.get_guild_flows(ctx.guild.id)
            await self.main_loop(ctx.guild.id)
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","guild-complete")).format(len(liste),round(time.time()-t,1)))
            await ctx.bot.cogs['UtilitiesCog'].suppr(msg)
        except Exception as e:
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","guild-error")).format(e))

    @rss_main.command(name="move")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def move_guild_flow(self,ctx:MyContext,ID:typing.Optional[int]=None,channel:discord.TextChannel=None):
        """Move a rss feed in another channel
        
        ..Doc rss.html#move-a-feed"""
        try:
            if channel is None:
                channel = ctx.channel
            try:
                flow = await self.askID(ID,ctx)
                e = None
            except Exception as e:
                flow = []
            if flow is None:
                return
            if len(flow) == 0:
                await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
                if e is not None:
                    await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
                return
            flow = flow[0]
            await self.update_flow(flow['ID'],[('channel',channel.id)])
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","move-success")).format(flow['ID'],channel.mention))
        except Exception as e:
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","guild-error")).format(e))

    @rss_main.command(name="text")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_text_flow(self, ctx: MyContext, ID: typing.Optional[int]=None, *, text=None):
        """Change the text of an rss feed
        
        ..Doc rss.html#change-the-text"""
        try:
            try:
                flow = await self.askID(ID,ctx)
            except Exception as e:
                flow = []
            if flow is None:
                return
            if len(flow) == 0:
                await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
                await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
                return
            flow = flow[0]
            if text is None:
                await ctx.send(str(await self.bot._(ctx.guild.id,"rss","change-txt")).format_map(self.bot.SafeDict(text=flow['structure'])))
                def check(msg):
                    return msg.author==ctx.author and msg.channel==ctx.channel
                try:
                    msg = await self.bot.wait_for('message', check=check,timeout=90)
                except asyncio.TimeoutError:
                    return await ctx.send(await self.bot._(ctx.guild.id,"rss","too-long"))
                text = msg.content
            await self.update_flow(flow['ID'],[('structure',text)])
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","text-success")).format(flow['ID'],text))
        except Exception as e:
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","guild-error")).format(e))
            await ctx.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @rss_main.command(name="use_embed",aliases=['embed'])
    @commands.guild_only()
    @commands.check(can_use_rss)
    @commands.check(checks.database_connected)
    async def change_use_embed(self,ctx:MyContext,ID:typing.Optional[int]=None,value:bool=None,*,arguments:args.arguments=None):
        """Use an embed or not for a flow
        You can also provide arguments to change the color/text of the embed. Followed arguments are usable:
        - color: color of the embed (hex or decimal value)
        - title: title override, which will disable the default one (max 256 characters)
        - footer: small text displayed at the bottom of the embed

        ..Example rss embed 6678466620137 true title="hey u" footer = "Hi \\n i'm a footer"
        
        ..Doc rss.html#setup-a-feed-embed"""
        try:
            try:
                flow = await self.askID(ID,ctx)
            except Exception as e:
                flow = []
                await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            if flow is None:
                return
            try:
                e
            except UnboundLocalError:
                e = None
            if len(flow) == 0:
                await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
                if e is not None:
                    await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
                return
            if arguments is None or len(arguments.keys()) == 0:
                arguments = None
            flow = flow[0]
            values_to_update = list()
            txt = list()
            if value is None and arguments is None:
                await ctx.send(await self.bot._(ctx.guild.id,"rss","use_embed_true" if flow['use_embed'] else 'use_embed_false'))
                def check(msg):
                    try:
                        _ = commands.core._convert_to_bool(msg.content)
                    except:
                        return False
                    return msg.author==ctx.author and msg.channel==ctx.channel
                try:
                    msg = await self.bot.wait_for('message', check=check,timeout=20)
                except asyncio.TimeoutError:
                    return await ctx.send(await self.bot._(ctx.guild.id,"rss","too-long"))
                value = commands.core._convert_to_bool(msg.content)
            if value is not None and value != flow['use_embed']:
                values_to_update.append(('use_embed',value))
                txt.append(await self.bot._(ctx.guild.id,"rss","use_embed-success",v=value,f=flow['ID']))
            elif value == flow['use_embed'] and arguments is None:
                await ctx.send(await self.bot._(ctx.guild.id,"rss","use_embed-same"))
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
                txt.append(await self.bot._(ctx.guild.id,"rss","embed-json-changed"))
            if len(values_to_update) > 0:
                await self.update_flow(flow['ID'],values_to_update)
            await ctx.send("\n".join(txt))
        except Exception as e:
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","guild-error")).format(e))
            await ctx.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @rss_main.command(name="test")
    @commands.check(reloads.is_support_staff)
    async def test_rss(self, ctx: MyContext, url, *, args=None):
        """Test if an rss feed is usable"""
        url = url.replace('<','').replace('>','')
        try:
            feeds = feedparser.parse(url,timeout=8)
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
                yt = await self.parse_yt_url(url)
                if yt is None:
                    tw = await self.parse_tw_url(url)
                    if tw is not None:
                        txt.append("<:twitter:437220693726330881>  "+tw)
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
            await ctx.bot.cogs['ErrorsCog'].on_command_error(ctx,e)

    async def check_rss_url(self, url):
        r = await self.parse_yt_url(url)
        if r is not None:
            return True
        r = await self.parse_tw_url(url)
        if r is not None:
            return True
        r = await self.parse_twitch_url(url)
        if r is not None:
            return True
        r = await self.parse_deviant_url(url)
        if r is not None:
            return True
        try:
            f = feedparser.parse(url)
            _ = f.entries[0]
            return True
        except:
            return False


    async def parse_yt_url(self, url):
        r = r'(?:http.*://)?(?:www.)?(?:youtube.com|youtu.be)(?:(?:/channel/|/user/)(.+)|/[\w-]+$)'
        match = re.search(r,url)
        if match is None:
            return None
        else:
            return match.group(1)

    async def parse_tw_url(self, url):
        r = r'(?:http.*://)?(?:www.)?(?:twitter.com/)([^?\s]+)'
        match = re.search(r,url)
        if match is None:
            return None
        else:
            return match.group(1)
    
    async def parse_twitch_url(self, url):
        r = r'(?:http.*://)?(?:www.)?(?:twitch.tv/)([^?\s]+)'
        match = re.search(r,url)
        if match is None:
            return None
        else:
            return match.group(1)
    
    async def parse_deviant_url(self, url):
        r = r'(?:http.*://)?(?:www.)?(?:deviantart.com/)([^?\s]+)'
        match = re.search(r,url)
        if match is None:
            return None
        else:
            return match.group(1)


    async def rss_yt(self, channel: discord.TextChannel, identifiant: str, date=None):
        if identifiant=='help':
            return await self.bot._(channel,"rss","yt-help")
        url = 'https://www.youtube.com/feeds/videos.xml?channel_id='+identifiant
        feeds = feedparser.parse(url)
        if feeds.entries==[]:
            url = 'https://www.youtube.com/feeds/videos.xml?user='+identifiant
            feeds = feedparser.parse(url)
            if feeds.entries==[]:
                return await self.bot._(channel,"rss","nothing")
        if not date:
            feed = feeds.entries[0]
            img_url = None
            if 'media_thumbnail' in feed.keys() and len(feed['media_thumbnail']) > 0:
                img_url = feed['media_thumbnail'][0]['url']
            obj = self.rssMessage(bot=self.bot,Type='yt',url=feed['link'],title=feed['title'],emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=feed['author'],image=img_url)
            return [obj]
        else:
            liste = list()
            for feed in feeds.entries:
                if 'published_parsed' not in feed or (datetime.datetime(*feed['published_parsed'][:6]) - date).total_seconds() <= self.min_time_between_posts['yw']:
                    break
                img_url = None
                if 'media_thumbnail' in feed.keys() and len(feed['media_thumbnail']) > 0:
                    img_url = feed['media_thumbnail'][0]['url']
                obj = self.rssMessage(bot=self.bot,Type='yt',url=feed['link'],title=feed['title'],emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=feed['author'],image=img_url)
                liste.append(obj)
            liste.reverse()
            return liste


    async def get_tw_official(self, nom:str, count:int=None):
        try:
            return [x for x in self.twitterAPI.GetUserTimeline(screen_name=nom,exclude_replies=True,trim_user=True,count=count)]
        except twitter.error.TwitterError as e:
            if str(e) == "Not authorized.":
                self.bot.log.warn(f"[rss] Unable to reach channel {nom}: Not authorized")
                return []
            try:
                if e.message[0]['code'] == 130: # Over capacity - Corresponds with HTTP 503. Twitter is temporarily over capacity.
                    return e
                elif e.message[0]['code'] == 131: # Internal error - Corresponds with HTTP 500. An unknown internal error occurred.
                    return e
                elif e.message[0]['code'] == 34: # Sorry, that page does not exist - Corresponds with HTTP 404. The specified resource was not found. (can also be an internal problem with Twitter)
                    return e
            except:
                pass
            await self.bot.get_user(279568324260528128).send("```py\n{}\n``` \n```py\n{}\n```".format(e,e.args))
            return []
        except requests.exceptions.ConnectionError:
            return []

    async def rss_tw_old(self, guild: discord.Guild, nom: str, date: datetime.datetime=None):
        if nom == 'help':
            return await self.bot._(guild,"rss","tw-help")
        try:
            url = self.twitter_api_url+nom
            feeds = feedparser.parse(url,timeout=15)
            if feeds.entries==[]:
                url = self.twitter_api_url+nom.capitalize()
                feeds = feedparser.parse(url,timeout=15)
                if feeds.entries==[]:
                    url = self.twitter_api_url+nom.lower()
                    feeds = feedparser.parse(url,timeout=15)
        except socket.timeout:
            return []
        tweets_list_official = await self.get_tw_official(nom)
        if isinstance(tweets_list_official,twitter.error.TwitterError):
            return tweets_list_official
        tweets_ids = [x.id_str for x in tweets_list_official]
        try:
            entries = [x for x in feeds.entries if hasattr(x,'link') and x.link.split('/')[-1].replace('?p=v','') in tweets_ids]
        except:
            entries = []
        if len(entries) == 0:
            return await self.bot._(guild,"rss","nothing")
        if len(entries) > 1:
            while entries[0]['published_parsed'] < entries[1]['published_parsed']:
                del entries[0]
                if len(entries)==1:
                    break
        if not date:
            feed = entries[0]
            r = re.search(r"(pic.twitter.com/[^\s]+)",feed['title'])
            if r is not None:
                t = feed['title'].replace(r.group(1),'')
            else:
                t = feed['title']
            author = feed['author'].replace('(','').replace(')','')
            rt = None
            if author.replace('@','') not in feed['link']:
                rt = url.split("=")[1]
            obj = self.rssMessage(bot=self.bot,Type='tw',url=feed['link'].replace('mobile.',''),title=t,emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=author,retweeted_by=rt,channel=feeds.feed['title'])
            return [obj]
        else:
            liste = list()
            for feed in entries:
                if (datetime.datetime(*feed['published_parsed'][:6]) - date).total_seconds() < self.min_time_between_posts['tw']:
                    break
                author = feed['author'].replace('(','').replace(')','')
                rt = None
                if author.replace('@','') not in feed['link']:
                    rt = url.split("=")[1]
                if rt is not None:
                    t = feed['title'].replace(rt,'')
                else:
                    t = feed['title']
                obj = self.rssMessage(bot=self.bot,Type='tw',url=feed['link'].replace('mobile.',''),title=t,emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=author,retweeted_by=rt,channel= feeds.feed['title'])
                liste.append(obj)
            liste.reverse()
            return liste


    async def rss_tw(self, channel: discord.TextChannel, nom: str, date: datetime.datetime=None):
        if nom == 'help':
            return await self.bot._(channel,"rss","tw-help")
        try:
            posts = self.twitterAPI.GetUserTimeline(screen_name=nom,exclude_replies=True)
        except twitter.error.TwitterError as e:
            if e.message == "Not authorized.":
                return await self.bot._(channel,"rss","nothing")
            if e.message[0]['code'] == 34:
                return await self.bot._(channel,"rss","nothing")
            raise e
        if not date:
            # lastpost = self.twitterAPI.GetUserTimeline(screen_name=nom,exclude_replies=True,trim_user=True)
            if len(posts) == 0:
                return []
            lastpost = posts[0]
            rt = None
            if lastpost.retweeted:
                rt = "retweet"
            text =  getattr(lastpost, 'full_text', lastpost.text)
            url = "https://twitter.com/{}/status/{}".format(nom.lower(), lastpost.id)
            img = None
            if lastpost.media: # if exists and is not empty
                img = lastpost.media[0].media_url_https
            obj = self.rssMessage(
                bot=self.bot,
                Type='tw',
                url=url,
                title=text,
                emojis=self.bot.cogs['EmojiCog'].customEmojis,
                date=datetime.datetime.fromtimestamp(lastpost.created_at_in_seconds), 
                author=lastpost.user.screen_name,
                retweeted_by=rt,
                channel=lastpost.user.name,
                image=img)
            return [obj]
        else:
            liste = list()
            for post in posts:
                if (datetime.datetime.fromtimestamp(post.created_at_in_seconds) - date).total_seconds() < self.min_time_between_posts['tw']:
                    break
                rt = None
                if post.retweeted:
                    rt = "retweet"
                url = None
                if len(post.urls) > 0:
                    url = post.urls[0].url
                text =  getattr(post, 'full_text', post.text)
                r = re.search(r"https://t.co/([^\s]+)", text)
                if r is not None:
                    text = text.replace(r.group(0),'')
                    url = r.group(0)
                else:
                    if post.urls == []:
                        url = "https://twitter.com/{}/status/{}".format(nom.lower(), post.id)
                    else:
                        url = post.urls[0].url
                img = None
                if post.media: # if exists and is not empty
                    img = post.media[0].media_url_https
                obj = self.rssMessage(
                    bot=self.bot,
                    Type='tw',
                    url=url,
                    title=text,
                    emojis=self.bot.cogs['EmojiCog'].customEmojis,
                    date=datetime.datetime.fromtimestamp(post.created_at_in_seconds),
                    author=post.user.screen_name,
                    retweeted_by=rt,
                    channel=post.user.name,
                    image=img)
                liste.append(obj)
            liste.reverse()
            return liste

    async def rss_twitch(self, channel: discord.TextChannel, nom: str, date: datetime.datetime=None):
        url = 'https://twitchrss.appspot.com/vod/'+nom
        feeds = feedparser.parse(url,timeout=5)
        if feeds.entries==[]:
            return await self.bot._(channel,"rss","nothing")
        if not date:
            feed = feeds.entries[0]
            r = re.search(r'<img src="([^"]+)" />',feed['summary'])
            img_url = None
            if r is not None:
                img_url = r.group(1)
            obj = self.rssMessage(bot=self.bot,Type='twitch',url=feed['link'],title=feed['title'],emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=feeds.feed['title'].replace("'s Twitch video RSS",""),image=img_url)
            return [obj]
        else:
            liste = list()
            for feed in feeds.entries:
                if datetime.datetime(*feed['published_parsed'][:6]) <= date:
                    break
                r = re.search(r'<img src="([^"]+)" />',feed['summary'])
                img_url = None
                if r is not None:
                    img_url = r.group(1)
                obj = self.rssMessage(bot=self.bot,Type='twitch',url=feed['link'],title=feed['title'],emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=feeds.feed['title'].replace("'s Twitch video RSS",""),image=img_url)
                liste.append(obj)
            liste.reverse()
            return liste

    async def rss_web(self, channel: discord.TextChannel, url: str, date: datetime.datetime=None):
        if url == 'help':
            return await self.bot._(channel,"rss","web-help")
        try:
            feeds = feedparser.parse(url,timeout=5)
        except socket.timeout:
            return await self.bot._(channel,"rss","research-timeout")
        if 'bozo_exception' in feeds.keys() or len(feeds.entries) == 0:
            return await self.bot._(channel,"rss","web-invalid")
        published = None
        for i in ['published_parsed','published','updated_parsed']:
            if i in feeds.entries[0].keys() and feeds.entries[0][i] is not None:
                published = i
                break
        if published is not None and len(feeds.entries) > 1:
            while (len(feeds.entries) > 1)  and (feeds.entries[1][published] is not None) and (feeds.entries[0][published] < feeds.entries[1][published]):
                del feeds.entries[0]
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
            r = re.search(r'(http(s?):)([/|.|\w|\s|-])*\.(?:jpe?g|gif|png|webp)', str(feed))
            if r is not None:
                img = r.group(0)
            obj = self.rssMessage(
                bot=self.bot,
                Type='web',
                url=l,
                title=title,
                emojis=self.bot.cogs['EmojiCog'].customEmojis,
                date=datz,
                author=author,
                channel=feeds.feed['title'] if 'title' in feeds.feed.keys() else '?',
                image=img)
            return [obj]
        else: # published in ['published_parsed','updated_parsed']
            liste = list()
            for feed in feeds.entries:
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
                    r = re.search(r'(http(s?):)([/|.|\w|\s|-])*\.(?:jpe?g|gif|png|webp)', str(feed))
                    if r is not None:
                        img = r.group(0)
                    obj = self.rssMessage(
                        bot=self.bot,
                        Type='web',
                        url=l,
                        title=title,
                        emojis=self.bot.cogs['EmojiCog'].customEmojis,
                        date=datz,
                        author=author,
                        channel=feeds.feed['title'] if 'title' in feeds.feed.keys() else '?',
                        image=img)
                    liste.append(obj)
                except:
                    pass
            liste.reverse()
            return liste


    async def rss_deviant(self, guild: discord.Guild, nom: str, date: datetime.datetime=None):
        url = 'https://backend.deviantart.com/rss.xml?q=gallery%3A'+nom
        feeds = feedparser.parse(url,timeout=5)
        if feeds.entries==[]:
            return await self.bot._(guild,"rss","nothing")
        if not date:
            feed = feeds.entries[0]
            img_url = feed['media_content'][0]['url']
            title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feeds.feed['title']).group(1)
            obj = self.rssMessage(bot=self.bot,Type='deviant',url=feed['link'],title=feed['title'],emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=title,image=img_url)
            return [obj]
        else:
            liste = list()
            for feed in feeds.entries:
                if datetime.datetime(*feed['published_parsed'][:6]) <= date:
                    break
                img_url = feed['media_content'][0]['url']
                title = re.search(r"DeviantArt: ([^ ]+)'s gallery",feeds.feed['title']).group(1)
                obj = self.rssMessage(bot=self.bot,Type='deviant',url=feed['link'],title=feed['title'],emojis=self.bot.cogs['EmojiCog'].customEmojis,date=feed['published_parsed'],author=title,image=img_url)
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

    async def get_flow(self, ID: int):
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("SELECT * FROM `{}` WHERE `ID`='{}'".format(self.table,ID))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste

    async def get_guild_flows(self, guildID: int):
        """Get every flow of a guild"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("SELECT * FROM `{}` WHERE `guild`='{}'".format(self.table,guildID))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste

    async def add_flow(self, guildID:int, channelID:int, _type:str, link:str):
        """Add a flow in the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        ID = await self.create_id(_type)
        if _type == 'mc':
            form = ''
        else:
            form = await self.bot._(guildID, "rss", _type+"-default-flow")
        # query = ("INSERT INTO `{}` (`ID`,`guild`,`channel`,`type`,`link`,`structure`) VALUES ('{}','{}','{}','{}','{}','{}')".format(self.table,ID,guildID,channelID,Type,link,form))
        query = "INSERT INTO `{}` (`ID`, `guild`,`channel`,`type`,`link`,`structure`) VALUES (%(i)s,%(g)s,%(c)s,%(t)s,%(l)s,%(f)s)".format(self.table)
        cursor.execute(query, { 'i': ID, 'g': guildID, 'c': channelID, 't': _type, 'l': link, 'f': form })
        cnx.commit()
        cursor.close()
        return ID

    async def remove_flow(self, ID: int):
        """Remove a flow from the database"""
        if type(ID)!=int:
            raise ValueError
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = ("DELETE FROM `{}` WHERE `ID`='{}'".format(self.table,ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    async def get_all_flows(self):
        """Get every flow of the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("SELECT * FROM `{}` WHERE `guild` in ({})".format(self.table,','.join(["'{}'".format(x.id) for x in self.bot.guilds])))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste
    
    async def get_raws_count(self, get_disabled:bool=False):
        """Get the number of rss feeds"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = "SELECT COUNT(*) FROM `{}`".format(self.table)
        if not get_disabled:
            query += " WHERE `guild` in (" + ','.join(["'{}'".format(x.id) for x in self.bot.guilds]) + ")"
        cursor.execute(query)
        t = list(cursor)[0][0]
        cursor.close()
        return t

    async def update_flow(self, ID: int, values=[(None,None)]):
        if self.bot.zombie_mode:
            return
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        v = list()
        for x in values:
            if isinstance(x[1],(bool,int)):
                v.append("""`{x[0]}`={x[1]}""".format(x=x))
            elif isinstance(x[1],(datetime.datetime,float)) or x[0]=='roles':
                v.append("""`{x[0]}`=\"{x[1]}\"""".format(x=x))
            else:
                v.append("`{}`=\"{}\"".format(x[0],x[1].replace('"','\\"')))
        query = """UPDATE `{t}` SET {v} WHERE `ID`={id}""".format(t=self.table,v=",".join(v),id=ID)
        cursor.execute(query)
        cnx.commit()
        cursor.close()

    async def send_rss_msg(self, obj, channel: discord.TextChannel, roles: typing.List[str]):
        if channel is not None:
            t = await obj.create_msg(await self.bot._(channel.guild,"current_lang","current"))
            mentions = list()
            for item in roles:
                if item=='':
                    continue
                role = discord.utils.get(channel.guild.roles,id=int(item))
                if role is not None:
                    mentions.append(role)
            try:
                if self.bot.zombie_mode:
                    return
                if isinstance(t,(self.bot.cogs['EmbedCog'].Embed,discord.Embed)):
                    await channel.send(" ".join(obj.mentions), embed=t, allowed_mentions=discord.AllowedMentions(everyone=False, roles=True))
                else:
                    await channel.send(t, allowed_mentions=discord.AllowedMentions(everyone=False, roles=True))
            except Exception as e:
                self.bot.log.info("[send_rss_msg] Cannot send message on channel {}: {}".format(channel.id,e))

    async def check_flow(self, flow: dict):
        try:
            guild = self.bot.get_guild(flow['guild'])
            if flow['link'] in self.cache.keys():
                objs = self.cache[flow['link']]
            else:
                funct = eval('self.rss_{}'.format(flow['type']))
                if isinstance(funct,twitter.error.TwitterError):
                    self.twitter_over_capacity = True
                    return False
                objs = await funct(guild,flow['link'],flow['date'])
                flow['link'] = objs
            if isinstance(objs,twitter.TwitterError):
                await self.bot.get_user(279568324260528128).send(f"[send_rss_msg] twitter error dans `await check_flow(): {objs}`")
                raise objs
            if isinstance(objs,(str,type(None),int)) or len(objs) == 0:
                return True
            elif type(objs) == list:
                for o in objs:
                    guild = self.bot.get_guild(flow['guild'])
                    if guild is None:
                        self.bot.log.info("[send_rss_msg] Can not send message on server {} (unknown)".format(flow['guild']))
                        return False
                    chan = guild.get_channel(flow['channel'])
                    if guild is None:
                        self.bot.log.info("[send_rss_msg] Can not send message on channel {} (unknown)".format(flow['channel']))
                        return False
                    o.format = flow['structure']
                    o.embed = flow['use_embed']
                    o.fill_embed_data(flow)
                    await o.fill_mention(guild,flow['roles'].split(';'), self.bot._)
                    await self.send_rss_msg(o,chan,flow['roles'].split(';'),)
                await self.update_flow(flow['ID'],[('date',o.date)])
                return True
            else:
                return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].senf_err_msg("Erreur rss sur le flux {} (type {} - salon {})".format(flow['link'],flow['type'],flow['channel']))
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
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
        for flow in liste:
            try:
                if flow['type'] == 'tw' and self.twitter_over_capacity:
                    continue
                if flow['type'] != 'mc':
                    if await self.check_flow(flow):
                        check += 1
                    else:
                        errors.append(flow['ID'])
                else:
                    await self.bot.cogs['McCog'].check_flow(flow)
                    check +=1
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
            await asyncio.sleep(self.time_between_flows_check)
        self.bot.cogs['McCog'].flows = dict()
        d = ["**RSS loop done** in {}s ({}/{} flows)".format(round(time.time()-t,3),check,len(liste))]
        if len(errors) > 0:
            d.append('{} errors: {}'.format(len(errors),' '.join([str(x) for x in errors])))
        emb = self.bot.cogs["EmbedCog"].Embed(desc='\n'.join(d),color=1655066).update_timestamp().set_author(self.bot.user)
        await self.bot.cogs["EmbedCog"].send([emb],url="loop")
        self.bot.log.debug(d[0])
        if len(errors) > 0:
            self.bot.log.warn("[Rss loop] "+d[1])
        if guildID is None:
            self.loop_processing = False
        self.twitter_over_capacity = False
        self.cache = dict()

    async def loop_child(self):
        if not self.bot.database_online:
            self.bot.log.warn('Base de donnée hors ligne - check rss annulé')
            return
        self.bot.log.info(" Boucle rss commencée !")
        await self.bot.cogs["RssCog"].main_loop()
        self.bot.log.info(" Boucle rss terminée !")

    async def loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(0.5)
        await self.loop_child()
        await asyncio.sleep((int(datetime.datetime.now().minute)%self.time_loop)*60-2)
        while not self.bot.is_closed():
            if int(datetime.datetime.now().minute)%self.time_loop == 0:
                await self.loop_child()
                await asyncio.sleep(self.time_loop*60-5)


    @commands.command(name="rss_loop",hidden=True)
    @commands.check(check_admin)
    async def rss_loop_admin(self, ctx: MyContext, permanent: bool=False):
        """Force the rss loop"""
        if not ctx.bot.database_online:
            return await ctx.send("Lol, t'as oublié que la base de donnée était hors ligne "+random.choice(["crétin ?","? Tu ferais mieux de fixer tes bugs","?","? :rofl:","?"]))
        if permanent:
            await ctx.send("Boucle rss relancée !")
            await self.loop()
        else:
            if self.loop_processing:
                await ctx.send("Une boucle rss est déjà en cours !")
            else:
                await ctx.send("Et hop ! Une itération de la boucle en cours !")
                self.bot.log.info(" Boucle rss forcée")
                await self.main_loop()
    
    async def send_log(self, text: str, guild: discord.Guild):
        """Send a log to the logging channel"""
        try:
            emb = self.bot.cogs["EmbedCog"].Embed(desc="[RSS] "+text,color=5366650,footer_text=guild.name).update_timestamp().set_author(self.bot.user)
            await self.bot.cogs["EmbedCog"].send([emb])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)


def setup(bot):
    bot.add_cog(RssCog(bot))