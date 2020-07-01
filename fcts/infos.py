import discord, datetime, sys, psutil, os, aiohttp, importlib, time, asyncio, typing, random, re, copy, requests
from discord.ext import commands
from inspect import signature
from platform import system as system_name  # Returns the system/OS name
from subprocess import call as system_call  # Execute a shell command

default_color = discord.Color(0x50e3c2)

from docs import conf
importlib.reload(conf)
from fcts import reloads, args, checks
# importlib.reload(reloads)
importlib.reload(args)
importlib.reload(checks)
from libs import bitly_api
importlib.reload(bitly_api)


class InfoCog(commands.Cog):
    """Here you will find various useful commands to get information about ZBot."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "infos"
        self.bot_version = conf.release
        try:
            self.translate = bot.cogs["LangCog"].tr
            self.timecog = bot.cogs["TimeCog"]
        except:
            pass
        self.emoji_table = 'emojis_beta' if self.bot.beta else 'emojis'
        self.BitlyClient = bitly_api.Bitly(login='zrunner',api_key=self.bot.others['bitly'])

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
        self.timecog = self.bot.cogs["TimeCog"]
        self.codelines = await self.count_lines_code()
        self.emoji_table = 'emojis_beta' if self.bot.beta else 'emojis'
    

    async def is_support(self,ctx):
        """Check if a user is part of the ZBot team"""
        return await reloads.is_support_staff(ctx)
    
    async def count_lines_code(self):
        """Count the number of lines for the whole project"""
        count = 0
        try:
            with open('start.py','r') as file:
                for line in file.read().split("\n"):
                    if len(line.strip())>2 and line[0]!='#':
                        count += 1
            for file in [x.file for x in self.bot.cogs.values()]+['args','checks']:
                with open('fcts/'+file+'.py','r') as file:
                    for line in file.read().split("\n"):
                        if len(line.strip())>2 and line[0]!='#':
                            count += 1
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
        self.codelines = count
        return count

    @commands.command(name='admins')
    async def admin_list(self,ctx):
        """Get the list of ZBot administrators"""
        l  = list()
        for u in reloads.admins_id:
            if u==552273019020771358:
                continue
            l.append(str(self.bot.get_user(u)))
        await ctx.send(str(await self.translate(ctx.channel,"infos","admins-list")).format(", ".join(l)))

    async def get_guilds_count(self,ignored_guilds:list=None) -> int:
        """Get the number of guilds where Zbot is"""
        if ignored_guilds==None:
            if 'banned_guilds' not in self.bot.cogs['UtilitiesCog'].config.keys():
                await self.bot.cogs['UtilitiesCog'].get_bot_infos()
            ignored_guilds = [int(x) for x in self.bot.cogs['UtilitiesCog'].config['banned_guilds'].split(";") if len(x)>0] + self.bot.cogs['ReloadsCog'].ignored_guilds
        return len([x for x in self.bot.guilds if x.id not in ignored_guilds])

    @commands.command(name="stats",enabled=True)
    @commands.cooldown(2,60,commands.BucketType.guild)
    async def stats(self,ctx):
        """Display some statistics about the bot"""
        v = sys.version_info
        version = str(v.major)+"."+str(v.minor)+"."+str(v.micro)
        pid = os.getpid()
        py = psutil.Process(pid)
        ram_cpu = [round(py.memory_info()[0]/2.**30,3), psutil.cpu_percent()]
        latency = round(self.bot.latency*1000,3)
        try:
            async with ctx.channel.typing():
                b_conf = self.bot.cogs['UtilitiesCog'].config
                if b_conf is None:
                    b_conf = await self.bot.cogs['UtilitiesCog'].get_bot_infos()
                ignored_guilds = list()
                if self.bot.database_online:
                    ignored_guilds = [int(x) for x in self.bot.cogs['UtilitiesCog'].config['banned_guilds'].split(";") if len(x)>0]
                ignored_guilds += self.bot.cogs['ReloadsCog'].ignored_guilds
                len_servers = await self.get_guilds_count(ignored_guilds)
                langs_list = await self.bot.cogs['ServerCog'].get_languages(ignored_guilds)
                lang_total = sum([x[1] for x in langs_list])
                langs_list = ' | '.join(["{}: {}%".format(x[0],round(x[1]/lang_total*100)) for x in langs_list if x[1]>0])
                del lang_total
                #premium_count = await self.bot.cogs['UtilitiesCog'].get_number_premium()
                try:
                    users,bots = self.get_users_nber(ignored_guilds)
                except Exception as e:
                    users = bots = 'unknown'
                if self.bot.database_online:
                    total_xp = await self.bot.cogs['XPCog'].bdd_total_xp()
                else:
                    total_xp = ""
                d = str(await self.translate(ctx.channel,"infos","stats")).format(bot_v=self.bot_version,s_count=len_servers,m_count=users,b_count=bots,l_count=self.codelines,lang=langs_list,p_v=version,d_v=discord.__version__,ram=ram_cpu[0],cpu=ram_cpu[1],api=latency,xp=total_xp)
            if isinstance(ctx.channel,discord.DMChannel) or ctx.channel.permissions_for(ctx.guild.me).embed_links:
                embed = ctx.bot.cogs['EmbedCog'].Embed(title=await self.translate(ctx.channel,"infos","stats-title"), color=ctx.bot.cogs['HelpCog'].help_color, time=ctx.message.created_at,desc=d,thumbnail=self.bot.user.avatar_url_as(format="png"))
                await embed.create_footer(ctx)
                await ctx.send(embed=embed.discord_embed())
            else:
                await ctx.send(d)
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)

    def get_users_nber(self,ignored_guilds):
        members = [x.members for x in self.bot.guilds if x.id not in ignored_guilds]
        members = list(set([x for x in members for x in x])) # filter users
        return len(members),len([x for x in members if x.bot])
    
    @commands.command(name="botinvite", aliases=["botinv"])
    async def botinvite(self, ctx:commands.Context):
        """Get a link to invite me
        
        ..Doc infos.html#bot-invite"""
        try:
            requests.get("https://zrunner.me/invitezbot", timeout=3)
        except requests.exceptions.Timeout:
            url = "https://discord.com/oauth2/authorize?client_id=486896267788812288&scope=bot"
        else:
            url = "https://zrunner.me/invitezbot"
        await ctx.send(await self.translate(ctx.channel, "infos", "botinvite", url=url))

    @commands.command(name="ping",aliases=['rep'])
    async def rep(self,ctx,ip=None):
        """Get bot latency
        You can also use this command to ping any other server"""
        if ip==None:
            m = await ctx.send("Ping...")
            t = (m.created_at - ctx.message.created_at).total_seconds()
            await m.edit(content=":ping_pong:  Pong !\nBot ping: {}ms\nDiscord ping: {}ms".format(round(t*1000),round(self.bot.latency*1000)))
        else:
            asyncio.run_coroutine_threadsafe(self.ping_adress(ctx,ip),asyncio.get_event_loop())

    async def ping_adress(self,ctx,ip):
        packages = 40
        wait = 0.3
        try:
            try:
                m = await ctx.send("Ping...",file=await self.bot.cogs['UtilitiesCog'].find_img('discord-loading.gif'))
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
            await ctx.send("Pong ! (average of {}ms per 64 byte, sent at {})".format(round(t,2), ip))
        else:
            await ctx.send("Unable to ping this adress")
        if m!=None:
            await m.delete()

    @commands.command(name="docs",aliases=['doc','documentation'])
    async def display_doc(self,ctx):
        """Get the documentation url"""
        text = str(self.bot.cogs['EmojiCog'].customEmojis['readthedocs']) + str(await self.translate(ctx.channel,"infos","docs")) + " https://zbot.rtfd.io"
        if self.bot.beta:
            text += '/en/indev'
        await ctx.send(text)

    @commands.command(name='info',aliases=['infos'])
    @commands.guild_only()
    async def infos(self,ctx,Type:typing.Optional[args.infoType]=None,*,name:str=None):
        """Find informations about someone/something
Available types: member, role, user, emoji, channel, server, invite, category"""
        if Type!=None and name==None and Type not in ["guild","server"]:
            raise commands.MissingRequiredArgument(self.infos.clean_params['name'])
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.translate(ctx.guild.id,"fun","no-embed-perm"))
        try:
            item = None
            lang = await self.translate(ctx.guild.id,"current_lang","current")
            find = self.bot.cogs['UtilitiesCog'].find_everything
            if Type in ["guild","server"]:
                if name==None or not await self.bot.cogs['AdminCog'].check_if_admin(ctx):
                    item = ctx.guild
                    #return await self.guild_info(ctx,ctx.guild,lang)
            if item is None:
                if name is None: # include Type==None bc of line 141
                    item = ctx.author
                else:
                    try:
                        item = await find(ctx,name,Type)
                    except:
                        name = name.replace('@everyone',"@"+u"\u200B"+"everyone").replace("@here","@"+u"\u200B"+"here")
                        await ctx.send(str(await self.translate(ctx.guild.id,"modo","cant-find-user")).format(name))
                        return
            critical = ctx.author.guild_permissions.manage_guild or await self.bot.cogs['AdminCog'].check_if_god(ctx)
            #-----
            if item is None:
                msg = await self.translate(ctx.guild.id,"stats_infos","not-found")
                await ctx.send(msg.format(N=name))
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
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            await ctx.send("`Error`: "+str(e))

    async def member_infos(self,ctx,item,lang,critical_info=False):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=item.color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.avatar_url_as(format='gif') if item.is_avatar_animated() else item.avatar_url_as(format='png'))
        embed.set_author(name=str(item), icon_url=str(item.avatar_url_as(format='png')))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=str(ctx.author.avatar_url_as(format='png')))
        # Name
        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        # Nickname
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-0"), value=item.nick if item.nick else str(await self.translate(ctx.channel,"keywords","none")).capitalize(),inline=True)
        # ID
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        # Roles
        list_role = list()
        for role in item.roles:
            if str(role)!='@everyone':
                list_role.append(role.mention)
        # Created at
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(item.created_at,lang=lang,year=True),since,await self.timecog.time_delta(item.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        # Joined at
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-2"), value = "{} ({} {})".format(await self.timecog.date(item.joined_at,lang=lang,year=True),since,await self.timecog.time_delta(item.joined_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        # Join position
        position = str(sorted(ctx.guild.members, key=lambda m: m.joined_at).index(item) + 1) + "/" + str(len(ctx.guild.members))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-3"), value = position,inline=True)
        # Status
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-4"), value = str(await self.translate(ctx.guild.id,"keywords",str(item.status))).capitalize(),inline=True)
        # Activity
        if item.activity==None:
            m_activity = str(await self.translate(ctx.guild.id,"activity","nothing")).capitalize()
        elif item.activity.type==discord.ActivityType.playing:
            m_activity = str(await self.translate(ctx.guild.id,"activity","play")).capitalize() + " " + item.activity.name
        elif item.activity.type==discord.ActivityType.streaming:
            m_activity = str(await self.translate(ctx.guild.id,"activity","stream")).capitalize() + " (" + item.activity.name + ")"
        elif item.activity.type==discord.ActivityType.listening:
            m_activity = str(await self.translate(ctx.guild.id,"activity","listen")).capitalize() + " " + item.activity.name
        elif item.activity.type==discord.ActivityType.watching:
            m_activity = str(await self.translate(ctx.guild.id,"activity","watch")).capitalize() +" " + item.activity.name
        elif item.activity.type==discord.ActivityType.custom:
            m_activity = item.activity.name
        else:
            m_activity="Error"
        if item.activity==None or item.activity.type != 4:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-5"), value = m_activity,inline=True)
        else:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-8"), value = item.activity.state, inline=True)
        # Bot
        if item.bot:
            botb = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            botb = await self.translate(ctx.guild.id,"keywords","non")
        embed.add_field(name="Bot", value=botb.capitalize())
        # Administrator
        if item.permissions_in(ctx.channel).administrator:
            admin = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            admin = await self.translate(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-6"), value = admin.capitalize(),inline=True)
        # Infractions count
        if critical_info and not item.bot:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-7"), value = await self.bot.cogs['CasesCog'].get_nber(item.id,ctx.guild.id),inline=True)
        # Guilds count
        if item.bot:
            session = aiohttp.ClientSession(loop=self.bot.loop)
            guilds_count = await self.bot.cogs['PartnersCog'].get_guilds(item.id,session)
            if guilds_count!=None:
                embed.add_field(name=str(await self.translate(ctx.guild.id,'keywords','servers')).capitalize(),value=guilds_count)
            await session.close()
        # Roles
        if len(list_role)>0:
            embed.add_field(name="Roles [{}]".format(len(list_role)), value = ", ".join(list_role), inline=False)
        else:
            embed.add_field(name="Roles [0]", value = await self.translate(ctx.guild.id,"activity","nothing"), inline=False)
        await ctx.send(embed=embed)


    async def role_infos(self,ctx,item,lang):
        embed = discord.Embed(colour=item.color, timestamp=ctx.message.created_at)
        embed.set_author(name=str(item), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        # Name
        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=item.mention,inline=True)
        # ID
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(item.id),inline=True)
        # Color
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-1"), value=str(item.color),inline=True)
        # Mentionnable
        if item.mentionable:
            mentio = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            mentio = await self.translate(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-2"), value=mentio.capitalize(),inline=True)
        # Members nbr
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value=len(item.members),inline=True)
        # Hoisted
        if item.hoist:
            hoist = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            hoist = await self.translate(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-4"), value=hoist.capitalize(),inline=True)
        # Created at
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(item.created_at,lang=lang,year=True),since,await self.timecog.time_delta(item.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        # Hierarchy position
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-5"), value=str(len(ctx.guild.roles) - item.position),inline=True)
        # Unique member
        if len(item.members)==1:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-6"), value=str(item.members[0].mention),inline=True)
        await ctx.send(embed=embed)


    async def user_infos(self,ctx,item,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        if item.bot:
            botb = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            botb = await self.translate(ctx.guild.id,"keywords","non")
        if item in ctx.guild.members:
            on_server = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            on_server = await self.translate(ctx.guild.id,"keywords","non")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.avatar_url_as(format='gif') if item.is_avatar_animated() else item.avatar_url_as(format='png'))
        embed.set_author(name=str(item), icon_url=item.avatar_url_as(format='png'))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(item.created_at,lang=lang,year=True),since,await self.timecog.time_delta(item.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        embed.add_field(name="Bot", value=botb.capitalize())
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","user-0"), value=on_server.capitalize())
        if item.bot:
            session = aiohttp.ClientSession(loop=self.bot.loop)
            guilds_count = await self.bot.cogs['PartnersCog'].get_guilds(item.id,session)
            if guilds_count!=None:
                embed.add_field(name=str(await self.translate(ctx.guild.id,'keywords','servers')).capitalize(),value=guilds_count)
            await session.close()
        await ctx.send(embed=embed)

    async def emoji_infos(self,ctx,item,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        if item.animated:
            animate = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            animate = await self.translate(ctx.guild.id,"keywords","non")
        if item.managed:
            manage = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            manage = await self.translate(ctx.guild.id,"keywords","non")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.url)
        embed.set_author(name="Emoji '{}'".format(item.name), icon_url=item.url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","emoji-0"), value=animate.capitalize())
        if item.guild != ctx.guild:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","emoji-3"), value=item.guild.name)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","emoji-2"), value="`<:{}:{}>`".format(item.name,item.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","emoji-1"), value=manage.capitalize())
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(item.created_at,lang=lang,year=True),since,await self.timecog.time_delta(item.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        if len(item.roles)>0:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","emoji-4"), value=" ".join([x.mention for x in item.roles]))
        infos_uses = await self.get_emojis_info(item.id)
        if len(infos_uses)>0:
            infos_uses = infos_uses[0]
            lang = await self.translate(ctx.channel,'current_lang','current')
            date = await self.bot.cogs['TimeCog'].date(infos_uses['added_at'],lang,year=True,hour=False)
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","emoji-5"), value=await self.translate(ctx.guild.id,"stats_infos","emoji-5v",nbr=infos_uses['count'],date=date))
        await ctx.send(embed=embed)

    async def textChannel_infos(self,ctx,chan,lang):
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","textchan-5"),chan.name), icon_url=ctx.guild.icon_url_as(format='png'))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        # Name
        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=chan.name,inline=True)
        # ID
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(chan.id))
        # Category
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-0"), value=str(chan.category))
        # NSFW
        if chan.nsfw:
            nsfw = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            nsfw = await self.translate(ctx.guild.id,"keywords","non")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-2"), value=nsfw.capitalize())
        # Webhooks count
        try:
            web = len(await chan.webhooks())
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            web = await self.translate(ctx.guild.id,"stats_infos","textchan-4")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-3"), value=str(web))
        # Members nber
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value = str(len(chan.members))+"/"+str(len(ctx.guild.members)), inline=True)
        # Created at
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(chan.created_at,lang=lang,year=True),since,await self.timecog.time_delta(chan.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        # Topic
        if chan.permissions_for(ctx.author).read_messages:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-1"), value = chan.topic if chan.topic not in ['',None] else str(await self.translate(ctx.guild.id,"keywords","aucune")).capitalize(), inline=False)
        await ctx.send(embed=embed)

    async def voiceChannel_info(self,ctx,chan,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","voicechan-0"),chan.name), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        # Name
        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=chan.name,inline=True)
        # ID
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(chan.id))
        # Category
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-0"), value=str(chan.category))
        # Created at
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(chan.created_at,lang=lang,year=True),since,await self.timecog.time_delta(chan.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        # Bitrate
        embed.add_field(name="Bitrate",value=str(chan.bitrate/1000)+" kbps")
        # Members count
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value="{}/{}".format(len(chan.members),chan.user_limit if chan.user_limit>0 else "∞"))
        # Region
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-2"), value=str(ctx.guild.region).capitalize())
        await ctx.send(embed=embed)

    async def guild_info(self,ctx:commands.Context,guild:discord.Guild,lang:str,critical_info:bool=False):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        bot = await self.bot.cogs["UtilitiesCog"].get_bots_number(guild.members)
        online = await self.bot.cogs["UtilitiesCog"].get_online_number(guild.members)
       
        desc = await self.bot.cogs['ServerCog'].find_staff(guild.id,'description')
        if (desc==None or len(desc)==0) and guild.description!=None:
            desc = guild.description
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at, description=desc)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        # Guild icon
        icon_url = guild.icon_url_as(format = "gif" if guild.is_icon_animated() else 'png')
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","guild-0"),guild.name), icon_url=icon_url)
        embed.set_thumbnail(url=icon_url)
        # Guild banner
        if guild.banner != None:
            embed.set_image(url=guild.banner_url)
        # Name
        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=guild.name,inline=True)
        # ID
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(guild.id))
        # Owner
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-1"), value=str(guild.owner))
        # Created at
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(guild.created_at,lang=lang,year=True),since,await self.timecog.time_delta(guild.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        # Voice region
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-2"), value=str(guild.region).capitalize())
        # Member count
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value = str(await self.translate(ctx.guild.id,"stats_infos","guild-7")).format(len(guild.members),bot,online))
        # Channel count
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-6"), value=str(await self.translate(ctx.guild.id,"stats_infos","guild-3")).format(len(guild.text_channels),len(guild.voice_channels),len(guild.categories)))
        # Invite count
        if guild.me.guild_permissions.manage_guild:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-12"), value=str(len(await guild.invites())))
        # Emojis count
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-5"), value="{}/{}".format(len(guild.emojis),guild.emoji_limit))
        # AFK timeout
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-10"), value = str(int(guild.afk_timeout/60))+" minutes")
        # Splash url
        try:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-15"), value=str(await guild.vanity_invite()))
        except Exception as e:
            if isinstance(e,(discord.errors.Forbidden, discord.errors.HTTPException)):
                pass
            else:
                await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
        # Premium subscriptions count
        if isinstance(guild.premium_subscription_count,int) and guild.premium_subscription_count>0:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-13"), value=await self.translate(ctx.guild.id,"stats_infos","guild-13v",b=guild.premium_subscription_count,p=guild.premium_tier))
        # Roles list
        try:
            if ctx.guild==guild:
                roles = [x.mention for x in guild.roles if len(x.members)>1][1:]
            else:
                roles = [x.name for x in guild.roles if len(x.members)>1][1:]
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            roles = guild.roles
        roles.reverse()
        if len(roles) == 0:
            temp = (await self.translate(ctx.guild.id,"keywords","none")).capitalize()
            embed.add_field(name=str(await self.translate(ctx.guild.id,"stats_infos","guild-11.2")).format(len(guild.roles)-1), value=temp)
        elif len(roles)>20:
            embed.add_field(name=str(await self.translate(ctx.guild.id,"stats_infos","guild-11.1")).format(len(guild.roles)-1), value=", ".join(roles[:20]))
        else:
            embed.add_field(name=str(await self.translate(ctx.guild.id,"stats_infos","guild-11.2")).format(len(guild.roles)-1), value=", ".join(roles))
        # Limitations
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-14"), value=await self.translate(ctx.guild.id,"stats_infos","guild-14v",
            bit=round(guild.bitrate_limit/1000),
            fil=round(guild.filesize_limit/1.049e+6),
            emo=guild.emoji_limit,
            mem=guild.max_presences))
        # Features
        if guild.features != []:
            features_tr = await self.translate(ctx.guild.id,"stats_infos","guild-features")
            features = [features_tr[x] if x in features_tr.keys() else x for x in guild.features]
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-9"), value=" - ".join(features))
        if critical_info:
            # A2F activation
            if guild.mfa_level:
                a2f = await self.translate(ctx.guild.id,"keywords","oui")
            else:
                a2f = await self.translate(ctx.guild.id,"keywords","non")
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-8"), value=a2f.capitalize())
            # Verification level
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-9"), value=str(await self.translate(ctx.guild.id,"keywords",str(guild.verification_level))).capitalize())
        await ctx.send(embed=embed)
        
   
    async def invite_info(self,ctx,invite,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","inv-4"),invite.code), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=str(await self.bot.user_avatar_as(ctx.author,size=256)))
        # Try to get the complete invite
        if invite.guild in self.bot.guilds:
            try:
                temp = [x for x in await invite.guild.invites() if x.id == invite.id]
                if len(temp)>0:
                    invite = temp[0]
            except discord.errors.Forbidden:
                pass
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
        # Invite URL
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-0"), value=invite.url,inline=True)
        # Inviter
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-1"), value=str(invite.inviter) if invite.inviter!= None else await self.translate(ctx.guild,'keywords','unknown'))
        # Invite uses
        if invite.max_uses != None and invite.uses != None:
            if invite.max_uses == 0:
                uses = "{}/∞".format(invite.uses)
            else:
                uses = "{}/{}".format(invite.uses,invite.max_uses)
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-2"), value=uses)
        # Duration
        if invite.max_age!=None:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-3"), value=str(invite.max_age) if invite.max_age != 0 else "∞")
        if isinstance(invite.channel,(discord.PartialInviteChannel,discord.abc.GuildChannel)):
            # Guild name
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-0"), value=str(invite.guild.name))
            # Channel name
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-5"), value="#"+str(invite.channel.name))
            # Guild icon
            url = str(invite.guild.icon_url)
            r = requests.get(url.replace(".webp",".gif"))
            if r.ok:
                url = url.replace(".webp",".gif")
            else:
                url = url.replace(".webp",".png")
            embed.set_thumbnail(url=url)
            # Guild ID
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-6"), value=str(invite.guild.id))
            # Members count
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-7"), value=str(invite.approximate_member_count))
        # Guild banner
        if invite.guild.banner_url != None:
            embed.set_image(url=invite.guild.banner_url)
        # Guild description
        if invite.guild.description != None:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-8"), value=invite.guild.description)
        # Guild features
        if len(invite.guild.features)>0:
            features_tr = await self.translate(ctx.guild.id,"stats_infos","guild-features")
            features = [features_tr[x] if x in features_tr.keys() else x for x in invite.guild.features]
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-9"), value=" - ".join(features))
        # Creation date
        if invite.created_at != None:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(invite.created_at,lang=lang,year=True),since,await self.timecog.time_delta(invite.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        await ctx.send(embed=embed)

    async def category_info(self,ctx,categ,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        tchan = 0
        vchan = 0
        for channel in categ.channels:
            if type(channel)==discord.TextChannel:
                tchan += 1
            elif type(channel) == discord.VoiceChannel:
                vchan +=1
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","categ-0"),categ.name), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=categ.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(categ.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","categ-1"), value="{}/{}".format(categ.position+1,len(ctx.guild.categories)))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-6"), value=str(await self.translate(ctx.guild.id,"stats_infos","categ-2")).format(tchan,vchan))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(categ.created_at,lang=lang,year=True),since,await self.timecog.time_delta(categ.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        await ctx.send(embed=embed)
    
    async def snowflake_infos(self ,ctx, snowflake: args.snowflake, lang):
        date = await self.bot.cogs["TimeCog"].date(snowflake.date,lang,year=True)
        embed = await self.bot.cogs["EmbedCog"].Embed(color = default_color, time = ctx.message.created_at, fields = [
            {"name": await self.translate(ctx.channel,"stats_infos","snowflake-0"), "value": date, "inline": True},
            {"name": await self.translate(ctx.channel,"stats_infos","snowflake-2"), "value": round(snowflake.date.timestamp()), "inline": True},
            {"name": await self.translate(ctx.channel,"stats_infos","snowflake-1"), "value": snowflake.binary, "inline": False},
            {"name": await self.translate(ctx.channel,"stats_infos","snowflake-3"), "value": snowflake.worker_id, "inline": True},
            {"name": await self.translate(ctx.channel,"stats_infos","snowflake-4"), "value": snowflake.process_id, "inline": True},
            {"name": await self.translate(ctx.channel,"stats_infos","snowflake-5"), "value": snowflake.increment, "inline": True}
        ]).create_footer(ctx)
        await ctx.send(embed=embed)


    @commands.group(name="find")
    @commands.check(reloads.is_support_staff)
    async def find_main(self,ctx):
        """Same as info, but in a lighter version"""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.translate(ctx.channel,"find","help"))

    @find_main.command(name="user")
    async def find_user(self,ctx,*,user:discord.User):
        use_embed = ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links
        # Servers list
        servers_in = list()
        owned, membered = 0, 0
        for s in self.bot.guilds:
            if user in s.members:
                if s.owner==user:
                    servers_in.append(":crown: "+s.name)
                    owned += 1
                else:
                    servers_in.append("- "+s.name)
                    membered += 1
        if len(servers_in)==0:
            servers_in = ["No server"]
        elif len("\n".join(servers_in)) > 1020:
            servers_in = [f"{owned} serveurs possédés, membre sur {membered} autres serveurs"]
        # XP card
        xp_card = await self.bot.cogs['UtilitiesCog'].get_xp_style(user)
        # Perks
        perks = list()
        if await self.bot.cogs["AdminCog"].check_if_admin(user):
            perks.append('admin')
        if await self.bot.cogs['UtilitiesCog'].is_support(user):
            perks.append("support")
        if await self.bot.cogs['UtilitiesCog'].is_contributor(user):
            perks.append("contributor")
        if await self.bot.cogs['UtilitiesCog'].is_premium(user):
            perks.append("premium")
        if await self.bot.cogs['UtilitiesCog'].is_partner(user):
            perks.append("partner")
        if await self.bot.cogs['UtilitiesCog'].is_translator(user):
            perks.append("translator")
        if len(perks)==0:
            perks = ["None"]
        # Has voted
        # async with aiohttp.ClientSession() as session:
        #     async with session.get('https://top.gg/api/bots/486896267788812288/check?userId={}'.format(user.id),headers={'Authorization':str(self.bot.dbl_token)}) as r:
        #         js = await r.json()
        #         if js['voted']:
        #             has_voted = await self.translate(ctx.channel,'keywords','oui')
        #         else:
        #             has_voted = await self.translate(ctx.channel,'keywords','non')
        #         has_voted = has_voted.capitalize()
        votes = await ctx.bot.get_cog("UtilitiesCog").check_votes(user.id)
        if use_embed:
            votes = " - ".join([f"[{x[0]}]({x[1]})" for x in votes])
        else:
            votes = " - ".join([x[0] for x in votes])
        if len(votes) == 0:
            votes = "Nowhere"
        # Languages
        disp_lang = list()
        for lang in await self.bot.cogs['UtilitiesCog'].get_languages(user):
            disp_lang.append('{} ({}%)'.format(lang[0],round(lang[1]*100)))
        if len(disp_lang)==0:
            disp_lang = ["Unknown"]
        # User name
        user_name = str(user)+' <:BOT:544149528761204736>' if user.bot else str(user)
        # ----
        if use_embed:
            if ctx.guild==None:
                color = None
            else:
                color = None if ctx.guild.me.color.value==0 else ctx.guild.me.color
            
            await ctx.send(embed = await self.bot.cogs['EmbedCog'].Embed(title=user_name, thumbnail=str(await self.bot.user_avatar_as(user,1024)) ,color=color, fields = [
                {"name": "ID", "value": user.id},
                {"name": "Perks", "value": "-".join(perks), "inline":False},
                {"name": "Servers", "value": "\n".join(servers_in), "inline":True},
                {"name": "Language", "value": "\n".join(disp_lang), "inline":True},
                {"name": "XP card", "value": xp_card, "inline":True},
                {"name": "Upvoted the bot?", "value": votes, "inline":True},
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
                " - ".join(perks),
                " - ".join(disp_lang),
                xp_card,
                votes,
                "\n".join(servers_in)
                )
            await ctx.send(txt)

    @find_main.command(name="guild",aliases=['server'])
    async def find_guild(self,ctx,*,guild):
        if guild.isnumeric():
            guild = ctx.bot.get_guild(int(guild))
        else:
            for x in self.bot.guilds:
                if x.name==guild:
                    guild = x
                    break
        if isinstance(guild,str) or guild==None:
            await ctx.send(await self.translate(ctx.channel,"find","guild-0"))
            return
        msglang = await self.translate(ctx.channel,'current_lang','current')
        # Bots
        bots = len([x for x in guild.members if x.bot])
        # Lang
        lang = await ctx.bot.cogs["ServerCog"].find_staff(guild.id,'language')
        if lang==None:
            lang = 'default'
        else:
            lang = ctx.bot.cogs['LangCog'].languages[lang]
        # Roles rewards
        rr_len = await self.bot.cogs['ServerCog'].find_staff(guild.id,'rr_max_number')
        rr_len = self.bot.cogs["ServerCog"].default_opt['rr_max_number'] if rr_len==None else rr_len
        rr_len = '{}/{}'.format(len(await self.bot.cogs['XPCog'].rr_list_role(guild.id)),rr_len)
        # Prefix
        pref = self.bot.cogs['UtilitiesCog'].find_prefix(guild)
        if "`" not in pref:
            pref = "`" + pref + "`"
        # Rss
        rss_len = await self.bot.cogs['ServerCog'].find_staff(guild.id,'rss_max_number')
        rss_len = self.bot.cogs["ServerCog"].default_opt['rss_max_number'] if rss_len==None else rss_len
        rss_numb = "{}/{}".format(len(await self.bot.cogs['RssCog'].get_guild_flows(guild.id)), rss_len)
        # Join date
        joined_at = await self.bot.cogs['TimeCog'].date(guild.me.joined_at,msglang,year=True,digital=True)
        # ----
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            if ctx.guild==None:
                color = None
            else:
                color = None if ctx.guild.me.color.value==0 else ctx.guild.me.color
            guild_icon = str(guild.icon_url_as(format = "gif" if guild.is_icon_animated() else 'png'))
            await ctx.send(embed = await self.bot.cogs['EmbedCog'].Embed(title=guild.name, color=color, thumbnail=guild_icon, fields=[
                {"name": "ID", "value": guild.id},
                {"name": "Owner", "value": "{} ({})".format(guild.owner, guild.owner.id)},
                {"name": "Joined at", "value": joined_at},
                {"name": "Members", "value": len(guild.members), "inline":True},
                {"name": "Language", "value": lang, "inline":True},
                {"name": "Prefix", "value": pref, "inline":True},
                {"name": "RSS feeds count", "value": rss_numb, "inline":True},
                {"name": "Roles rewards count", "value": rr_len, "inline":True},
            ]).create_footer(ctx))
        else:
            txt = str(await self.translate(ctx.channel,"find","guild-1")).format(name = guild.name,
                id = guild.id,
                owner = guild.owner,
                ownerid = guild.owner.id,
                join = joined_at,
                members = len(guild.members),
                bots = bots,
                lang = lang,
                prefix = pref,
                rss = rss_numb,
                rr = rr_len)
            await ctx.send(txt)

    @find_main.command(name='channel')
    async def find_channel(self,ctx,ID:int):
        c = self.bot.get_channel(ID)
        if c is None:
            await ctx.send(await self.translate(ctx.channel,"find","chan-0"))
            return
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            if ctx.guild==None:
                color = None
            else:
                color = None if ctx.guild.me.color.value==0 else ctx.guild.me.color
            await ctx.send(embed = await self.bot.cogs['EmbedCog'].Embed(title="#"+c.name,color=color,fields=[
                {"name": "ID", "value": c.id},
                {"name": "Server", "value": f"{c.guild.name} ({c.guild.id})"}
            ]).create_footer(ctx))
        else:
            await ctx.send(await self.translate(ctx.channel,"find","chan-1").format(c.name,c.id,c.guild.name,c.guild.id))
    
    @find_main.command(name='role')
    async def find_role(self,ctx,ID:int):
        every_roles = list()
        for serv in ctx.bot.guilds:
            every_roles += serv.roles
        role = discord.utils.find(lambda role:role.id==ID,every_roles)
        if role is None:
            await ctx.send(await self.translate(ctx.channel,"find","role-0"))
            return
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            if ctx.guild==None:
                color = None
            else:
                color = None if ctx.guild.me.color.value==0 else ctx.guild.me.color
            await ctx.send(embed = await self.bot.cogs['EmbedCog'].Embed(title="@"+role.name,color=color,fields=[
                {"name": "ID", "value": role.id},
                {"name": "Server", "value": f"{role.guild.name} ({role.guild.id})"},
                {"name": "Members", "value": len(role.members), "inline": True},
                {"name": "Colour", "value": str(role.colour), "inline": True}
            ]).create_footer(ctx))
        else:
            await ctx.send(await self.translate(ctx.channel,"find","role-1").format(role.name,role.id,role.guild.name,role.guild.id,len(role.members),role.colour))
    
    @find_main.command(name='rss')
    async def find_rss(self,ctx,ID:int):
        flow = await self.bot.cogs['RssCog'].get_flow(ID)
        if len(flow)==0:
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
        if temp != None:
            c = "`{}`\n{}".format(temp.name,temp.id)
        else:
            c = "Unknown ({})".format(flow['channel'])
        d = await self.bot.cogs['TimeCog'].date(flow['date'],digital=True)
        if d==None or len(d)==0:
            d = "never"
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            if ctx.guild==None:
                color = None
            else:
                color = None if ctx.guild.me.color.value==0 else ctx.guild.me.color
            await ctx.send(embed = await self.bot.cogs['EmbedCog'].Embed(title=f"RSS N°{ID}",color=color,fields=[
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
    async def membercount(self,ctx):
        """Get some digits on the number of server members"""
        if ctx.channel.permissions_for(ctx.guild.me).send_messages==False:
            return
        bots = c_co = 0
        total = len(ctx.guild.members)
        for u in ctx.guild.members:
            if u.bot:
                bots+=1
            if str(u.status) != "offline":
                c_co+=1
        h = total - bots
        l = [(await self.translate(ctx.guild.id,"infos_2","membercount-0"),str(total)),
        (await self.translate(ctx.guild.id,"infos_2","membercount-2"),"{} ({}%)".format(h,int(round(h*100/total,0)))),
        (await self.translate(ctx.guild.id,"infos_2","membercount-1"),"{} ({}%)".format(bots,int(round(bots*100/total,0)))),
        (await self.translate(ctx.guild.id,"infos_2","membercount-3"),"{} ({}%)".format(c_co,int(round(c_co*100/total,0))))]
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
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
    async def get_prefix(self,ctx:commands.Context):
        """Show the usable prefix(s) for this server"""
        if ctx.invoked_subcommand != None:
            return
        txt = await self.translate(ctx.channel,"infos","prefix")
        prefix = "\n".join((await ctx.bot.get_prefix(ctx.message))[1:])
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me):
            emb = await ctx.bot.cogs['EmbedCog'].Embed(title=txt,desc=prefix,time=ctx.message.created_at,color=ctx.bot.cogs['HelpCog'].help_color).create_footer(ctx)
            return await ctx.send(embed=emb.discord_embed())
        await ctx.send(txt+"\n"+prefix)
    
    @get_prefix.command(name="change")
    @commands.guild_only()
    async def prefix_change(self,ctx,new_prefix):
        """Change the used prefix"""
        msg = copy.copy(ctx.message)
        msg.content = ctx.prefix + 'config change prefix '+new_prefix
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)
    
    @commands.command(name="discordlinks",aliases=['discord','discordurls'])
    async def discord_status(self,ctx):
        """Get some useful links about Discord"""
        can_embed = True if isinstance(ctx.channel,discord.DMChannel) else ctx.channel.permissions_for(ctx.guild.me).embed_links
        if can_embed:
            l = await self.translate(ctx.channel,'infos','discordlinks')
            links = ["https://dis.gd/status","https://dis.gd/tos","https://dis.gd/report","https://dis.gd/feedback","https://support.discord.com/hc/en-us/articles/115002192352","https://discord.com/developers/docs/legal","https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-","https://support.discord.com/hc/en-us/articles/360040724612"]
            txt = "\n".join(['['+l[i]+']('+links[i]+')' for i in range(len(l))])
            em = await self.bot.cogs["EmbedCog"].Embed(desc=txt).update_timestamp().create_footer(ctx)
            await ctx.send(embed=em)
        else:
            txt = "\n".join([f'• {k}: <{v}>' for k,v in (await self.translate(ctx.channel,'infos','discordlinks')).items()])
            await ctx.send(txt)
    

    async def emoji_analysis(self,msg):
        """Lists the emojis used in a message"""
        try:
            if not self.bot.database_online:
                return
            ctx = await self.bot.get_context(msg)
            if ctx.command!=None:
                return
            liste = list(set(re.findall(r'<a?:[\w-]+:(\d{18})>',msg.content)))
            if len(liste)==0:
                return
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor()
            current_timestamp = datetime.datetime.fromtimestamp(round(time.time()))
            query = ["INSERT INTO `{t}` (`ID`,`count`,`last_update`) VALUES ('{i}',1,'{l}') ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = '{l}';".format(t=self.emoji_table,i=x,l=current_timestamp) for x in liste]
            for q in query:
                cursor.execute(q)
            cnx.commit()
            cursor.close()
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
    
    async def get_emojis_info(self,ID:typing.Union[int,list]):
        """Get info about an emoji"""
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
    async def bitly_main(self,ctx:commands.Context):
        """Bit.ly website, but in Discord
        Create shortened url and unpack them by using Bitly services"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['bitly'])
        elif ctx.invoked_subcommand==None and ctx.subcommand_passed!=None:
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
    async def bitly_create(self,ctx,url:args.url):
        """Create a shortened url"""
        await ctx.send(await self.translate(ctx.channel,'infos','bitly_short',url=self.BitlyClient.shorten_url(url.url)))
    
    @bitly_main.command(name="find")
    async def bitly_find(self,ctx,url:args.url):
        """Find the long url from a bitly link"""
        if url.domain != 'bit.ly':
            return await ctx.send(await self.translate(ctx.channel,'infos','bitly_nobit'))
        await ctx.send(await self.translate(ctx.channel,'infos','bitly_long',url=self.BitlyClient.expand_url(url.url)))
    
    @commands.command(name='changelog',aliases=['changelogs'])
    @commands.check(checks.database_connected)
    async def changelog(self,ctx:commands.Context,version:str=None):
        """Get the changelogs of the bot"""
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
            title = await self.translate(ctx.channel,'infos','changelogs-index')
        else:
            if version==None:
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
                used_lang = await self.translate(ctx.channel,'current_lang','current')
                if used_lang not in results[0].keys():
                    used_lang = "en"
                desc = results[0][used_lang]
                time = results[0]['utc_release']
                title = (await self.translate(ctx.channel,'keywords','version')).capitalize() + ' ' + results[0]['version']
        if len(results)==0:
            await ctx.send(await self.translate(ctx.channel,'infos','changelog-notfound'))
        elif isinstance(ctx.channel,discord.DMChannel) or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            emb = ctx.bot.cogs['EmbedCog'].Embed(title=title,desc=desc,time=time,color=ctx.bot.cogs['ServerCog'].embed_color)
            await ctx.send(embed=emb)
        else:
            await ctx.send(desc)

    @commands.command(name="usernames",aliases=["username","usrnm"])
    async def username(self,ctx:commands.Context,*,user:discord.User=None):
        """Get the names history of an user
        Default user is you"""
        if user==None:
            user = ctx.author
        language = await self.translate(ctx.channel,"current_lang","current")
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
        if ctx.guild != None:
            this_guild = [x for x in results if x['guild']==ctx.guild.id]
        # title
        t = await self.translate(ctx.channel,'infos','usernames-title',u=user.name)
        # Embed creation
        if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            date = ""
            desc = None
            f = list()
            if len(global_list)>0:
            # Usernames part
                temp = [x['new'] for x in global_list if x['new']!='']
                if len(temp) > 30:
                    temp = temp[:30] + [await self.translate(ctx.channel, 'infos', 'usernames-more', nbr=len(temp)-30)]
                f.append({'name':await self.translate(ctx.channel,'infos','usernames-global'), 'value':"\n".join(temp)})
                if global_list[-1]['old'] != '':
                    f[-1]["value"] += "\n" + global_list[-1]['old']
                date += await self.bot.cogs['TimeCog'].date([x['utc_date'] for x in global_list][0] ,year=True, lang=language)
            if len(this_guild)>0:
            # Nicknames part
                temp = [x['new'] for x in this_guild if x['new']!='']
                if len(temp) > 30:
                    temp = temp[:30] + [await self.translate(ctx.channel, 'infos', 'usernames-more', nbr=len(temp)-30)]
                f.append({'name':await self.translate(ctx.channel,'infos','usernames-local'), 'value':"\n".join(temp)})
                if this_guild[-1]['old'] != '':
                    f[-1]["value"] += "\n" + this_guild[-1]['old']
                date += "\n" + await self.bot.cogs['TimeCog'].date([x['utc_date'] for x in this_guild][0], year=True, lang=language)
            if len(date)>0:
                f.append({'name':await self.translate(ctx.channel,'infos','usernames-last-date'), 'value':date})
            else:
                desc = await self.translate(ctx.channel,'infos','usernames-empty')
            if ctx.guild != None and ctx.guild.get_member(user.id)!=None and ctx.guild.get_member(user.id).color!=discord.Color(0):
                c = ctx.guild.get_member    (user.id).color
            else:
                c = 1350390
            allowing_logs = await self.bot.cogs["UtilitiesCog"].get_db_userinfo(["allow_usernames_logs"],["userID="+str(user.id)])
            if allowing_logs==None or allowing_logs["allow_usernames_logs"]:
                footer = await self.translate(ctx.channel,'infos','usernames-disallow')
            else:
                footer = await self.translate(ctx.channel,'infos','usernames-allow')
            emb = self.bot.cogs['EmbedCog'].Embed(title=t,fields=f,desc=desc,color=c,footer_text=footer)
            await ctx.send(embed=emb)
        # Raw text creation
        else:
            await ctx.send(results)


def setup(bot):
    bot.add_cog(InfoCog(bot))
    
