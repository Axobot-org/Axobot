import discord, datetime, sys, psutil, os, aiohttp, importlib, time, asyncio, typing, random, re
from discord.ext import commands
from inspect import signature
from platform   import system as system_name  # Returns the system/OS name
from subprocess import call   as system_call  # Execute a shell command

default_color = discord.Color(0x50e3c2)

from docs import conf
importlib.reload(conf)
from fcts import reloads, args
importlib.reload(reloads)
importlib.reload(args)

bot_version = conf.release


class InfosCog(commands.Cog):
    """Here you will find various useful commands to get information about ZBot."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "infos"
        try:
            self.translate = bot.cogs["LangCog"].tr
            self.timecog = bot.cogs["TimeCog"]
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
        self.timecog = self.bot.cogs["TimeCog"]
        self.codelines = await self.count_lines_code()
    

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
            for file in [x.file for x in self.bot.cogs.values()]+['args']:
                with open('fcts/'+file+'.py','r') as file:
                    for line in file.read().split("\n"):
                        if len(line.strip())>2 and line[0]!='#':
                            count += 1
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
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
                if b_conf == None:
                    b_conf = await self.bot.cogs['UtilitiesCog'].reload()
                ignored_guilds = [int(x) for x in self.bot.cogs['UtilitiesCog'].config['banned_guilds'].split(";") if len(x)>0]
                ignored_guilds += self.bot.cogs['ReloadsCog'].ignored_guilds
                len_servers = len([x for x in ctx.bot.guilds if x.id not in ignored_guilds])
                langs_list = await self.bot.cogs['ServerCog'].get_languages(ignored_guilds)
                lang_total = sum([x[1] for x in langs_list])
                langs_list = ' | '.join(["{}: {}%".format(x[0],round(x[1]/lang_total*100)) for x in langs_list if x[1]>0])
                del lang_total
                #premium_count = await self.bot.cogs['UtilitiesCog'].get_number_premium()
                try:
                    users,bots = self.get_users_nber(ignored_guilds)
                except Exception as e:
                    users = bots = 'unknown'
                total_xp = await self.bot.cogs['XPCog'].bdd_total_xp()
                d = str(await self.translate(ctx.channel,"infos","stats")).format(bot_v=bot_version,s_count=len_servers,m_count=users,b_count=bots,l_count=self.codelines,lang=langs_list,p_v=version,d_v=discord.__version__,ram=ram_cpu[0],cpu=ram_cpu[1],api=latency,xp=total_xp)
            if isinstance(ctx.channel,discord.DMChannel) or ctx.channel.permissions_for(ctx.guild.me).embed_links:
                embed = ctx.bot.cogs['EmbedCog'].Embed(title=await self.translate(ctx.channel,"infos","stats-title"), color=ctx.bot.cogs['HelpCog'].help_color, time=ctx.message.created_at,desc=d,thumbnail=self.bot.user.avatar_url_as(format="png"))
                embed.create_footer(ctx.author)
                await ctx.send(embed=embed.discord_embed())
            else:
                await ctx.send(d)
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)

    def get_users_nber(self,ignored_guilds):
        members = [x.members for x in self.bot.guilds if x.id not in ignored_guilds]
        members = [x for x in members for x in x]
        return len(members),len([x for x in members if x.bot])


    @commands.command(name="ping",aliases=['rep'])
    async def rep(self,ctx,ip=None):
        """Get bot latency
        You can also use this command to ping any other server"""
        if ip==None:
            m = await ctx.send("Pong !")
            t = (m.created_at - ctx.message.created_at).total_seconds()
            await m.edit(content="Pong ! ("+str(round(t*1000,3))+"ms)")
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

    @commands.command(name="docs")
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
            lang = await self.translate(ctx.guild.id,"current_lang","current")
            find = self.bot.cogs['UtilitiesCog'].find_everything
            if Type in ["guild","server"]:
                if name==None or not await self.bot.cogs['AdminCog'].check_if_admin(ctx):
                    return await self.guild_info(ctx,ctx.guild,lang)
            if name == None: # include Type==None bc of line 141
                item = ctx.author
            else:
                try:
                    item = await find(ctx,name,Type)
                except:
                    await ctx.send(str(await self.translate(ctx.guild.id,"modo","cant-find-user")).format(name))
                    return
            critical = ctx.author.guild_permissions.manage_guild or await self.bot.cogs['AdminCog'].check_if_god(ctx)
            #-----
            if item == None:
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
            else:
                await ctx.send(str(type(item))+" / "+str(item))
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            await ctx.send("`Error`: "+str(e))

    async def member_infos(self,ctx,item,lang,critical_info=False):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        if item.activity==None:
            m_activity = str(await self.translate(ctx.guild.id,"activity","rien")).capitalize()
        elif item.activity.type==discord.ActivityType.playing:
            m_activity = str(await self.translate(ctx.guild.id,"activity","play")).capitalize() + " " + item.activity.name
        elif item.activity.type==discord.ActivityType.streaming:
            m_activity = str(await self.translate(ctx.guild.id,"activity","stream")).capitalize() + " (" + item.activity.name + ")"
        elif item.activity.type==discord.ActivityType.listening:
            m_activity = str(await self.translate(ctx.guild.id,"activity","listen")).capitalize() + " " + item.activity.name
        elif item.activity.type==discord.ActivityType.watching:
            m_activity = str(await self.translate(ctx.guild.id,"activity","watch")).capitalize() +" " + item.activity.name
        else:
            m_activity="Error"
        if item.bot:
            botb = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            botb = await self.translate(ctx.guild.id,"keywords","non")
        if item.permissions_in(ctx.channel).administrator:
            admin = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            admin = await self.translate(ctx.guild.id,"keywords","non")
        list_role = list()
        for role in item.roles:
            if str(role)!='@everyone':
                list_role.append(role.mention)
        position = str(sorted(ctx.guild.members, key=lambda m: m.joined_at).index(item) + 1) + "/" + str(len(ctx.guild.members))
        embed = discord.Embed(colour=item.color, timestamp=ctx.message.created_at)
        embed.set_thumbnail(url=item.avatar_url_as(format='gif') if item.is_avatar_animated() else item.avatar_url_as(format='png'))
        embed.set_author(name=str(item), icon_url=str(item.avatar_url_as(format='png')))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=str(ctx.author.avatar_url_as(format='png')))

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=item.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-0"), value=item.nick if item.nick else str(await self.translate(ctx.channel,"keywords","none")).capitalize(),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(item.id))
        embed.add_field(name="Bot", value=botb.capitalize())
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(item.created_at,lang=lang,year=True),since,await self.timecog.time_delta(item.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-2"), value = "{} ({} {})".format(await self.timecog.date(item.joined_at,lang=lang,year=True),since,await self.timecog.time_delta(item.joined_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-3"), value = position,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-4"), value = str(await self.translate(ctx.guild.id,"keywords",str(item.status))).capitalize(),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-5"), value = m_activity,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-6"), value = admin.capitalize(),inline=True)
        if len(list_role)>0:
            embed.add_field(name="Roles [{}]".format(len(list_role)), value = ", ".join(list_role), inline=False)
        else:
            embed.add_field(name="Roles [0]", value = await self.translate(ctx.guild.id,"activity","rien"), inline=False)
        if critical_info:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-7"), value = await self.bot.cogs['CasesCog'].get_nber(item.id,ctx.guild.id),inline=True)
        if item.bot:
            session = aiohttp.ClientSession(loop=self.bot.loop)
            guilds_count = await self.bot.cogs['PartnersCog'].get_guilds(item.id,session)
            if guilds_count!=None:
                embed.add_field(name=str(await self.translate(ctx.guild.id,'keywords','servers')).capitalize(),value=guilds_count)
            uptime = await self.bot.cogs['PartnersCog'].get_uptimes(item.id,session)
            if uptime!=None:
                embed.add_field(name=await self.translate(ctx.guild,'partners','bot-uptime'),value=f'{round(uptime)}%')
            await session.close()
        await ctx.send(embed=embed)


    async def role_infos(self,ctx,item,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        if item.mentionable:
            mentio = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            mentio = await self.translate(ctx.guild.id,"keywords","non")
        if item.hoist:
            hoist = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            hoist = await self.translate(ctx.guild.id,"keywords","non")
        embed = discord.Embed(colour=item.color, timestamp=ctx.message.created_at)
        embed.set_author(name=str(item), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
 
        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=item.mention,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(item.id),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-1"), value=str(item.color),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-2"), value=mentio.capitalize(),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value=len(item.members),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-4"), value=hoist.capitalize(),inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(item.created_at,lang=lang,year=True),since,await self.timecog.time_delta(item.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-5"), value=str(len(ctx.guild.roles) - item.position),inline=True)
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
            uptime = await self.bot.cogs['PartnersCog'].get_uptimes(item.id,session)
            if uptime!=None:
                embed.add_field(name=await self.translate(ctx.guild,'partners','bot-uptime'),value=f'{round(uptime)}%')
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
        await ctx.send(embed=embed)

    async def textChannel_infos(self,ctx,chan,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        if chan.nsfw:
            nsfw = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            nsfw = await self.translate(ctx.guild.id,"keywords","non")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","textchan-5"),chan.name), icon_url=ctx.guild.icon_url_as(format='png'))
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url_as(format='png'))

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=chan.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(chan.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-0"), value=str(chan.category))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-2"), value=nsfw.capitalize())
        try:
            web = len(await chan.webhooks())
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            web = await self.translate(ctx.guild.id,"stats_infos","textchan-4")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-3"), value=str(web))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value = str(len(chan.members))+"/"+str(len(ctx.guild.members)), inline=False)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(chan.created_at,lang=lang,year=True),since,await self.timecog.time_delta(chan.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        if chan.permissions_for(ctx.author).read_messages:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-1"), value = chan.topic if chan.topic not in ['',None] else str(await self.translate(ctx.guild.id,"keywords","aucune")).capitalize(), inline=False)
        await ctx.send(embed=embed)

    async def voiceChannel_info(self,ctx,chan,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at)
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","voicechan-0"),chan.name), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=chan.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(chan.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-0"), value=str(chan.category))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(chan.created_at,lang=lang,year=True),since,await self.timecog.time_delta(chan.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        embed.add_field(name="Bitrate",value=str(chan.bitrate/1000)+" kbps")
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value="{}/{}".format(len(chan.members),chan.user_limit if chan.user_limit>0 else "∞"))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-2"), value=str(ctx.guild.region).capitalize())
        await ctx.send(embed=embed)

    async def guild_info(self,ctx:commands.Context,guild:discord.Guild,lang:str,critical_info:bool=False):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        bot = await self.bot.cogs["UtilitiesCog"].get_bots_number(guild.members)
        online = await self.bot.cogs["UtilitiesCog"].get_online_number(guild.members)
        if guild.mfa_level:
            a2f = await self.translate(ctx.guild.id,"keywords","oui")
        else:
            a2f = await self.translate(ctx.guild.id,"keywords","non")
        desc = await self.bot.cogs['ServerCog'].find_staff(guild.id,'description')
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at, description=desc)
        embed.set_author(name="{} '{}'".format(await self.translate(guild.id,"stats_infos","guild-0"),guild.name), icon_url=guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        embed.set_thumbnail(url=guild.icon_url)

        embed.add_field(name=str(await self.translate(ctx.guild.id,"keywords","nom")).capitalize(), value=guild.name,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(guild.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-1"), value=str(guild.owner))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-2"), value=str(guild.region).capitalize())
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","member-1"), value = "{} ({} {})".format(await self.timecog.date(guild.created_at,lang=lang,year=True),since,await self.timecog.time_delta(guild.created_at,datetime.datetime.now(),lang=lang,year=True,precision=0,hour=False)), inline=False)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-3"), value = str(await self.translate(ctx.guild.id,"stats_infos","guild-7")).format(len(guild.members),bot,online))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-6"), value=str(await self.translate(ctx.guild.id,"stats_infos","guild-3")).format(len(guild.text_channels),len(guild.voice_channels),len(guild.categories)))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-5"), value="{}/{}".format(len(guild.emojis),guild.emoji_limit))
        if guild.me.guild_permissions.manage_guild:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-12"), value=str(len(await guild.invites())))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-10"), value = str(int(guild.afk_timeout/60))+" minutes")
        if critical_info:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-8"), value=a2f.capitalize())
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-9"), value=str(await self.translate(guild.id,"keywords",str(guild.verification_level))).capitalize())
        splash_url = str(guild.splash_url_as(format='png'))
        if splash_url != '':
            embed.add_field(name="Splash url", value=splash_url)
        try:
            if ctx.guild==guild:
                roles = [x.mention for x in guild.roles if len(x.members)>1][1:]
            else:
                roles = [x.name for x in guild.roles if len(x.members)>1][1:]
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await self.bot.cogs['UtilitiesCog'].print2(str([x.mention for x in guild.roles if len(x.members)>1]))
            roles = guild.roles
        roles.reverse()
        if len(roles)>20:
            embed.add_field(name=str(await self.translate(ctx.guild.id,"stats_infos","guild-11.1")).format(len(guild.roles)-1), value=", ".join(roles[:20]))
        else:
            embed.add_field(name=str(await self.translate(ctx.guild.id,"stats_infos","guild-11.2")).format(len(guild.roles)-1), value=", ".join(roles))
        if guild.premium_subscription_count>0:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-13"), value=await self.translate(ctx.guild.id,"stats_infos","guild-13v",b=guild.premium_subscription_count,p=guild.premium_tier))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-14"), value=await self.translate(ctx.guild.id,"stats_infos","guild-14v",
            bit=round(guild.bitrate_limit/1000),
            fil=round(guild.filesize_limit/1.049e+6),
            emo=guild.emoji_limit,
            mem=guild.max_presences))
        await ctx.send(embed=embed)
        if guild.features != []:
            owner = self.bot.get_user(279568324260528128)
            await owner.send("Chef ! On a trouvé un serveur avec des *features* !\nID = {}\nFeatures = {}".format(guild.id,guild.features))
   
    async def invite_info(self,ctx,invite,lang):
        since = await self.translate(ctx.guild.id,"keywords","depuis")
        embed = discord.Embed(colour=default_color, timestamp=ctx.message.created_at,description=await self.translate(ctx.guild.id,"stats_infos","inv-5"))
        embed.set_author(name="{} '{}'".format(await self.translate(ctx.guild.id,"stats_infos","inv-4"),invite.code), icon_url=ctx.guild.icon_url)
        embed.set_footer(text='Requested by {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)

        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-0"), value=invite.url,inline=True)
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(invite.id))
        embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-1"), value=str(invite.inviter) if invite.inviter!= None else await self.translate(ctx.guild,'keywords','unknown'))
        if invite.max_uses!=None and invite.uses!=None:
            if invite.max_uses == 0:
                uses = "{}/∞".format(invite.uses)
            else:
                uses = "{}/{}".format(invite.uses,invite.max_uses)
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-2"), value=uses)
        if invite.max_age!=None:
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","inv-3"), value=str(invite.max_age) if invite.max_age != 0 else "∞")
        if isinstance(invite.channel,(discord.PartialInviteChannel,discord.TextChannel)):
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","guild-0"), value=str(invite.guild.name))
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","textchan-5"), value="#"+str(invite.channel.name))
            embed.set_thumbnail(url=invite.guild.icon_url)
            embed.add_field(name=await self.translate(ctx.guild.id,"stats_infos","role-0"), value=str(invite.guild.id))
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


    @commands.group(name="find")
    @commands.check(reloads.is_support_staff)
    async def find_main(self,ctx):
        """Same as info, but in a lighter version"""
        if ctx.invoked_subcommand is None:
            await ctx.send(await self.translate(ctx.channel,"find","help"))

    @find_main.command(name="user")
    async def find_user(self,ctx,*,user:discord.User):
        servers_in = list()
        owners = list()
        for s in self.bot.guilds:
            if user in s.members:
                servers_in.append(s.name)
                if s.owner==user:
                    owners.append(s.name)
        disp_lang = ""
        xp_card = await self.bot.cogs['UtilitiesCog'].get_xp_style(user)
        perks = list()
        if await self.bot.cogs["AdminCog"].check_if_admin(user):
            perks.append('admin')
        if await self.bot.cogs['UtilitiesCog'].is_support(user):
            perks.append("support")
        if await self.bot.cogs['UtilitiesCog'].is_contributor(user):
            perks.append("contributor")
        if await self.bot.cogs['UtilitiesCog'].is_premium(user):
            perks.append("premium")
        async with aiohttp.ClientSession() as session:
            async with session.get('https://discordbots.org/api/bots/486896267788812288/check?userId={}'.format(user.id),headers={'Authorization':str(self.bot.dbl_token)}) as r:
                js = await r.json()
                if js['voted']:
                    r = await self.translate(ctx.channel,'keywords','oui')
                else:
                    r = await self.translate(ctx.channel,'keywords','non')
                r = r.capitalize()
        disp_lang = str()
        for lang in await self.bot.cogs['UtilitiesCog'].get_languages(user):
            disp_lang += '{} ({}%)   '.format(lang[0],round(lang[1]*100))
        await ctx.send(str(await self.translate(ctx.channel,"find","user-1")).format(name=user,id=user.id,servers=", ".join(servers_in),own=", ".join(owners),lang=disp_lang,vote=r,card=xp_card,rangs=" - ".join(perks)))

    @find_main.command(name="guild",aliases=['server'])
    async def find_guild(self,ctx,*,guild):
        s = None
        if guild.isnumeric():
            s = ctx.bot.get_guild(int(guild))
        else:
            for x in self.bot.guilds:
                if x.name==guild:
                    s = x
        if s == None:
            await ctx.send(await self.translate(ctx.channel,"find","guild-0"))
            return
        msglang = await self.translate(ctx.channel,'current_lang','current')
        # Bots
        bots = len([x for x in s.members if x.bot])
        # Lang
        lang = await ctx.bot.cogs["ServerCog"].find_staff(s.id,'language')
        if lang==None:
            lang = 'default'
        else:
            lang = ctx.bot.cogs['LangCog'].languages[lang]
        # Roles rewards
        rr_len = await self.bot.cogs['ServerCog'].find_staff(s.id,'rr_max_number')
        rr_len = self.bot.cogs["ServerCog"].default_opt['rr_max_number'] if rr_len==None else rr_len
        rr_len = '{}/{}'.format(len(await self.bot.cogs['XPCog'].rr_list_role(s.id)),rr_len)
        # Prefix
        pref = self.bot.cogs['UtilitiesCog'].find_prefix(s)
        # Rss
        rss_numb = len(await self.bot.cogs['RssCog'].get_guild_flows(s.id))
        await ctx.send(str(await self.translate(ctx.channel,"find","guild-1")).format(name=s.name,
            id=s.id,
            owner=s.owner,ownerid=s.owner.id,
            join=await self.bot.cogs['TimeCog'].date(s.me.joined_at,msglang,year=True,digital=True),
            members=len(s.members),bots=bots,
            lang=lang,
            prefix=pref,
            rss=rss_numb,
            rr=rr_len))

    @find_main.command(name='channel')
    async def find_channel(self,ctx,ID:int):
        c = self.bot.get_channel(ID)
        if c == None:
            await ctx.send(await self.translate(ctx.channel,"find","chan-0"))
            return
        await ctx.send(str(await self.translate(ctx.channel,"find","chan-1")).format(c.name,c.id,c.guild.name,c.guild.id))
    
    @find_main.command(name='role')
    async def find_role(self,ctx,ID:int):
        every_roles = list()
        for serv in ctx.bot.guilds:
            every_roles += serv.roles
        c = discord.utils.find(lambda role:role.id==ID,every_roles)
        if c == None:
            await ctx.send(await self.translate(ctx.channel,"find","role-0"))
            return
        await ctx.send(str(await self.translate(ctx.channel,"find","role-1")).format(c.name,c.id,c.guild.name,c.guild.id,len(c.members),c.colour))
    
    @find_main.command(name='rss')
    async def find_rss(self,ctx,ID:int):
        flow = await self.bot.cogs['RssCog'].get_flow(ID)
        if len(flow)==0:
            await ctx.send("Invalid ID")
        else:
            flow = flow[0]
        temp = self.bot.get_guild(flow['guild'])
        if temp == None:
            g = "Unknown ({})".format(flow['guild'])
            
        else:
            g = "{} `{}`".format(temp.id,temp.name)
            temp = self.bot.get_channel(flow['channel'])
        if temp != None:
            c = "{} `{}`".format(temp.id,temp.name)
        else:
            c = "Unknown ({})".format(flow['channel'])
        d = await self.bot.cogs['TimeCog'].date(flow['date'],digital=True)
        await ctx.send("ID: {}\nGuild: {}\nChannel: {}\nLink: <{}>\nType: {}\nLast post: {}".format(flow['ID'],g,c,flow['link'],flow['type'],d))

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
        if datetime.datetime.today().day==1:
            self.bot.fishes += 1
            l.append((await self.translate(ctx.guild.id,"infos_2","fish-1"),"{} {}".format(random.randrange(100),random.choice([':fish:',':tropical_fish:','']))))
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

    @commands.command(name="prefix")
    async def get_prefix(self,ctx):
        """Show the usable prefix(s) for this server"""
        txt = await self.translate(ctx.channel,"infos","prefix")
        prefix = "\n".join(await ctx.bot.get_prefix(ctx.message))
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me):
            emb = ctx.bot.cogs['EmbedCog'].Embed(title=txt,desc=prefix,time=ctx.message.created_at,color=ctx.bot.cogs['HelpCog'].help_color).create_footer(ctx.author)
            return await ctx.send(embed=emb.discord_embed())
        await ctx.send(txt+"\n"+prefix)
    
    @commands.command(name="discordlinks",aliases=['discord','discordurls'])
    async def discord_status(self,ctx):
        """Get some useful links about Discord"""
        can_embed = True if isinstance(ctx.channel,discord.DMChannel) else ctx.channel.permissions_for(ctx.guild.me).embed_links
        if can_embed:
            txt = "\n".join([f'[{k}]({v})' for k,v in (await self.translate(ctx.channel,'infos','discordlinks')).items()])
            em = self.bot.cogs["EmbedCog"].Embed(desc=txt).update_timestamp().create_footer(ctx.author).discord_embed()
            await ctx.send(embed=em)
        else:
            txt = "\n".join([f'• {k}: <{v}>' for k,v in (await self.translate(ctx.channel,'infos','discordlinks')).items()])
            await ctx.send(txt)
    

    async def emoji_analysis(self,msg):
        """Lists the emojis used in a message"""
        try:
            liste = list(set(re.findall(r'<:[\w-]+:(\d{18})>',msg.content)))
            if len(liste)==0:
                return
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor()
            current_timestamp = datetime.datetime.fromtimestamp(round(time.time()))
            table = 'emojis_beta' if self.bot.beta else 'emojis'
            query = ["INSERT INTO `{t}` (`ID`,`count`,`last_update`) VALUES ('{i}',1,'{l}') ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = '{l}';".format(t=table,i=x,l=current_timestamp) for x in liste]
            cursor.execute(*query)
            cnx.commit()
            cursor.close()
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


def setup(bot):
    bot.add_cog(InfosCog(bot))
    
