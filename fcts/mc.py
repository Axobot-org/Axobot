import frmc_lib
import aiohttp
import discord
import re
import datetime
import time
import requests
from discord.ext import commands
from urllib.parse import quote
from classes import zbot, MyContext


class McCog(commands.Cog):
    """Cog gathering all commands related to the Minecraft® game. 
Every information come from the website www.fr-minecraft.net"""
    
    def __init__(self, bot: zbot):
        self.bot = bot
        self.flows = dict()
        self.file = "mc"

    @commands.command(name="mojang", aliases=['mojang_status'])
    @commands.cooldown(5, 20, commands.BucketType.user)
    async def mojang_status(self, ctx: MyContext):
        """Get Mojang server status"""
        desc = await self.bot._(ctx.channel,"mc","mojang_desc")
        async with aiohttp.ClientSession() as session:
            async with session.get('https://status.mojang.com/check') as r:
            # async with session.get('https://api.bowie-co.nz/api/v1/mojang/check') as r:
                data = await r.json()
        if ctx.can_send_embed:
            embed = discord.Embed(color=discord.Colour(0x699bf9), timestamp=ctx.message.created_at)
            embed.set_thumbnail(url="https://www.minecraft-france.fr/wp-content/uploads/2020/05/mojang-logo-2.gif")
            embed.set_author(name="Mojang Studios - Services Status", url="https://status.mojang.com/check", icon_url="https://www.minecraft.net/content/dam/franchise/logos/Mojang-Studios-Logo-Redbox.png")
            embed.set_footer(text="Requested by {}".format(ctx.author.display_name), icon_url=ctx.author.avatar_url_as(format='png',size=512))
        else:
            text = "Mojang Studios - Services Status (requested by {})".format(ctx.author)
        if isinstance(data, dict):
            for K,V in data.items():
                if K == "www.minecraft.net/en-us":
                    K = "minecraft.net"
                if V == "green":
                    k = self.bot.cogs['EmojiCog'].customEmojis['green_check']+K
                elif V == "red":
                    k = self.bot.cogs['EmojiCog'].customEmojis['red_cross']+K
                elif V == 'yellow':
                    k = self.bot.cogs['EmojiCog'].customEmojis['neutral_check']+K
                else:
                    k = self.bot.cogs['EmojiCog'].customEmojis['blurple']+K
                    dm = self.bot.get_user(279568324260528128).dm_channel
                    if dm is None:
                        await self.bot.get_user(279568324260528128).create_dm()
                        dm = self.bot.get_user(279568324260528128).dm_channel
                    await dm.send("Status mojang inconnu : "+V+" (serveur "+K+")")
                if K in desc.keys():
                    v = desc[K]
                else:
                    v = ''
                if ctx.can_send_embed:
                    embed.add_field(name=k,value=v, inline=False)
                else:
                    text += "\n {} *({})*".format(k,v)
        else:
            for item in data:
                if len(item) != 1:
                    continue
                K, V = list(item.items())[0]
                if V == "green":
                    k = self.bot.cogs['EmojiCog'].customEmojis['green_check']+K
                elif V == "red":
                    k = self.bot.cogs['EmojiCog'].customEmojis['red_cross']+K
                elif V == 'yellow':
                    k = self.bot.cogs['EmojiCog'].customEmojis['neutral_check']+K
                else:
                    k = self.bot.cogs['EmojiCog'].customEmojis['blurple']+K
                    dm = self.bot.get_user(279568324260528128).dm_channel
                    if dm is None:
                        await self.bot.get_user(279568324260528128).create_dm()
                        dm = self.bot.get_user(279568324260528128).dm_channel
                    await dm.send("Status mojang inconnu : "+V+" (serveur "+K+")")
                if K in desc.keys():
                    v = desc[K]
                else:
                    v = ''
                if ctx.can_send_embed:
                    embed.add_field(name=k, value=v, inline=False)
                else:
                    text += "\n {} *({})*".format(k, v)
        if ctx.can_send_embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send(text)

    @commands.group(name="minecraft", aliases=["mc"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def mc_main(self, ctx: MyContext):
        """Search for Minecraft game items/servers
        
        ..Doc minecraft.html#mc"""
        if ctx.subcommand_passed is None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['minecraft'])

    @mc_main.command(name="block", aliases=["bloc"])
    async def mc_block(self, ctx: MyContext, *, value='help'):
        """Get info about any block
        
        ..Doc minecraft.html#mc
        
        ..Example mc block stone"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel,"mc","block-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "mc", "no-embed"))
            return
        try:
            Block = frmc_lib.main(value,'Bloc')
        except:
            await ctx.send(await self.bot._(ctx.channel,"mc","no-block"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel,"mc","names"))[0],Block.Name)
        embed = self.bot.get_cog("EmbedCog").Embed(title=title, color=discord.Colour(int('16BD06',16)), url=Block.Url, time=ctx.message.created_at, desc=await self.bot._(ctx.channel,'mc','contact-mail'), thumbnail=Block.Image)
        await embed.create_footer(ctx)
        embed.add_field(name="Nom", value=Block.Name,inline=False)
        l = ("\n".join(Block.ID),Block.Stack,Block.CreativeTab,Block.Damage,Block.Strength,Block.Tool,", ".join(Block.Mobs),Block.Version)
        for e,v in enumerate(await self.bot._(ctx.channel,"mc","block-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.bot._(ctx.channel,"mc","no-entity"))

    @mc_main.command(name="entity", aliases=["entité","mob"])
    async def mc_entity(self, ctx: MyContext, *, value='help'):
        """Get info about any entity
        
        ..Doc minecraft.html#mc
        
        ..Example mc entity slime"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel,"mc","entity-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "mc", "no-embed"))
            return
        try:
            Entity = frmc_lib.main(value,'Entité')
        except:
            await ctx.send(await self.bot._(ctx.channel,"mc","no-entity"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel,"mc","names"))[1],Entity.Name)
        embed = self.bot.get_cog("EmbedCog").Embed(title=title, color=discord.Colour(int('16BD06',16)), url=Entity.Url, time=ctx.message.created_at, desc=await self.bot._(ctx.channel,'mc','contact-mail'), thumbnail=Entity.Image)
        await embed.create_footer(ctx)
        embed.add_field(name="Nom", value=Entity.Name,inline=False)
        l = (Entity.ID,Entity.Type,Entity.PV,Entity.PA,Entity.XP,", ".join(Entity.Biomes),Entity.Version)
        for e,v in enumerate(await self.bot._(ctx.channel,"mc","entity-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        if Entity.Dimensions != [0,0,0]:
            embed.add_field(name="Dimensions",value=await self.bot._(ctx.channel,"mc","dimensions",la=Entity.Dimensions[0],lo=Entity.Dimensions[1],ha=Entity.Dimensions[2]))
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.bot._(ctx.channel,"mc","no-entity"))
    
    @mc_main.command(name="item",aliases=['object'])
    async def mc_item(self, ctx: MyContext, *, value='help'):
        """Get info about any item
        
        ..Doc minecraft.html#mc
        
        ..Example mc item stick"""
        if value=='help':
            await ctx.send(await self.bot._(ctx.channel,"mc","item-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "mc", "no-embed"))
            return
        try:
            Item = frmc_lib.main(value,"Item")
        except:
            await ctx.send(await self.bot._(ctx.channel,"mc","no-item"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel,"mc","names"))[2],Item.Name)
        embed = self.bot.get_cog("EmbedCog").Embed(title=title, color=discord.Colour(int('16BD06',16)), url=Item.Url, time=ctx.message.created_at, desc=await self.bot._(ctx.channel,'mc','contact-mail'))
        if Item.Image is not None:
            embed.thumbnail = Item.Image
        await embed.create_footer(ctx)
        embed.add_field(name="Nom", value=Item.Name,inline=False)
        l = ('\n'.join(Item.ID),Item.Stack,Item.CreativeTab,Item.Damage,Item.Strength,Item.Tool,", ".join(Item.Mobs),Item.Version)
        for e,v in enumerate(await self.bot._(ctx.channel,"mc","item-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.bot._(ctx.channel,"mc","no-entity"))

    @mc_main.command(name="command",aliases=["commande","cmd"])
    async def mc_cmd(self, ctx: MyContext, *, value='help'):
        """Get info about any command
        
        ..Doc minecraft.html#mc
        
        ..Example mc cmd execute if"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel,"mc","cmd-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "mc", "no-embed"))
            return
        try:
            Cmd = frmc_lib.main(value,'Commande')
        except:
            await ctx.send(await self.bot._(ctx.channel,"mc","no-cmd"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel,"mc","names"))[3],Cmd.Name)
        embed = self.bot.get_cog("EmbedCog").Embed(title=title, color=discord.Colour(int('16BD06',16)), url=Cmd.Url, time=ctx.message.created_at, desc=await self.bot._(ctx.channel,'mc','contact-mail'))
        await embed.create_footer(ctx)
        l = (Cmd.Name," ".join(Cmd.Syntax),Cmd.Examples,Cmd.Version)
        for e,v in enumerate(await self.bot._(ctx.channel,"mc","cmd-fields")):
            if e==2:
                if len(l[e]) > 0:
                    examples = list()
                    for ex in l[e]:
                        s = "`{}`\n*{}*".format(ex[0], ex[1])
                        if len("\n".join(examples) + s) > 1024:
                            break
                        examples.append(s)
                    embed.add_field(name=v,value="\n".join(examples),inline=False)
                continue
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.bot._(ctx.channel,"mc","no-cmd"))
    
    @mc_main.command(name="advancement",aliases=["advc","progrès"])
    async def mc_advc(self, ctx: MyContext, *, value='help'):
        """Get info about any advancement"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel,"mc","adv-help"))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "mc", "no-embed"))
            return
        try:
            Adv = frmc_lib.main(value,'Progrès')
        except:
            await ctx.send(await self.bot._(ctx.channel,"mc","no-adv"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel,"mc","names"))[4],Adv.Name)
        embed = self.bot.get_cog("EmbedCog").Embed(title=title, color=discord.Colour(int('16BD06',16)), url=Adv.Url, time=ctx.message.created_at, desc=await self.bot._(ctx.channel,'mc','contact-mail'))
        await embed.create_footer(ctx)
        if Adv.Image is not None:
            embed.thumbnail = Adv.Image
        l = (Adv.Name,Adv.ID,Adv.Type,Adv.Action,Adv.Parent,", ".join(Adv.Children),Adv.Version)   #("Nom","Identifiant","Type","Action","Parent","Enfants","Version d'ajout")
        for e,v in enumerate(await self.bot._(ctx.channel,"mc","adv-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.bot._(ctx.channel,"mc","no-adv"))
    
    @mc_main.command(name="mod")
    async def mc_mod(self, ctx: MyContext, *, value: str='help'):
        """Get info about any mod registered on CurseForge"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "mc", "mod-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "mc", "no-embed"))
            return
        url = 'https://addons-ecs.forgesvc.net/api/v2/addon/'
        h = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:78.0) Gecko/20100101 Firefox/83.0"}
        searchurl = url+'search?gameId=432&sectionId=6&sort=0&pageSize=2&searchFilter='+quote(value.lower())
        await ctx.send(searchurl)
        async with aiohttp.ClientSession(loop=self.bot.loop, headers=h) as session:
            async with session.get(searchurl, timeout=10) as resp:
                search: list = await resp.json()
            if len(search) == 0:
                await ctx.send(await self.bot._(ctx.channel, "mc", "no-mod"))
                return
        user_lang = await self.bot._(ctx.channel, "current_lang", "current")
        search = search[0]
        authors = ", ".join([f"[{x['name']}]({x['url']})" for x in search['authors']])
        d = search['dateModified'][:-1]
        d += '0'*(23-len(d))
        date = await self.bot.get_cog("TimeCog").date(datetime.datetime.fromisoformat(d), user_lang, year=True)
        versions = set(x['gameVersion'] for x in search['gameVersionLatestFiles'])
        versions = " - ".join(sorted(versions, reverse=True, key=lambda a: list(map(int, a.split('.')))))
        l = (
            search['name'],
            authors,
            search['summary'],
            search['primaryLanguage'],
            date,
            versions,
            int(search['downloadCount']),
            search['id']
        )
        title = "{} - {}".format((await self.bot._(ctx.channel, "mc", "names"))[5], search['name'])
        embed = self.bot.get_cog("EmbedCog").Embed(
            title=title, color=discord.Colour(int('16BD06', 16)),
            url=search['websiteUrl'],
            time=ctx.message.created_at)
        await embed.create_footer(ctx)
        if attachments := search['attachments']:
            embed.thumbnail = attachments[0]['thumbnailUrl']
        for e,v in enumerate(await self.bot._(ctx.channel, "mc", "mod-fields")):
            if l[e] not in [None, '']:
                try:
                    embed.add_field(name=v, value=str(l[e]))
                except:
                    pass
        await ctx.send(embed=embed)

    @mc_main.command(name="server")
    async def mc_server(self, ctx: MyContext, ip:str, port:int=None):
        """Get infos about any Minecraft server"""
        if ":" in ip and port is None:
            i = ip.split(":")
            ip, port = i[0], i[1]
        obj = await self.create_server_1(ctx.guild, ip, port)
        await self.send_msg_server(obj,ctx.channel,(ip,port))

    @mc_main.command(name="add")
    @commands.guild_only()
    async def mc_add_server(self, ctx: MyContext, ip, port:int=None):
        """Follow a server's info (regularly displayed on this channel)"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id,"cases","no_database"))
        if ":" in ip and port is None:
            i = ip.split(":")
            ip,port = i[0],i[1]
        elif port is None:
            port = ''
        is_over, flow_limit = await self.bot.cogs['RssCog'].is_overflow(ctx.guild)
        if is_over:
            await ctx.send(str(await self.bot._(ctx.guild.id,"rss","flow-limit")).format(flow_limit))
            return
        try:
            if port is None:
                display_ip = ip
            else:
                display_ip = "{}:{}".format(ip,port)
            await self.bot.cogs['RssCog'].add_flow(ctx.guild.id,ctx.channel.id,'mc',"{}:{}".format(ip,port))
            await ctx.send(str(await self.bot._(ctx.guild,"mc","success-add")).format(display_ip,ctx.channel.mention))
        except Exception as e:
            await ctx.send(await self.bot._(ctx.guild,"rss","fail-add"))
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)


    async def create_server_1(self, guild: discord.Guild, ip: str, port=None):
        if port is None:
            url = "https://api.minetools.eu/ping/"+str(ip)
        else:
            url = "https://api.minetools.eu/ping/"+str(ip)+"/"+str(port)
        try:
            r = requests.get(url,timeout=5).json()
        # except requests.exceptions.ConnectionError:
        #     return await self.create_server_2(guild,ip,port)
        # except requests.exceptions.ReadTimeout:
        #     return await self.create_server_2(guild,ip,port)
        except Exception:
            return await self.create_server_2(guild, ip, port)
            # self.bot.log.warn("[mc-server-1] Erreur sur l'url {} :".format(url))
            # await self.bot.cogs['ErrorsCog'].on_error(e,None)
            # return await self.bot._(guild,"mc","serv-error")
        if "error" in r.keys():
            if r['error'] != 'timed out':
                self.bot.log.warn("(mc-server) Error on: "+url+"\n   "+r['error'])
            return r["error"]
        players=[]
        try:
            for p in r['players']['sample']:
                players.append(p['name'])
                if len(players) > 30:
                    break
        except:
            players = []
        if players==[]:
            if r['players']['online'] == 0:
                players = [str(await self.bot._(guild, "keywords", "none")).capitalize()]
            else:
                players=['Non disponible']
        IP = "{}:{}".format(ip,port) if port is not None else str(ip)
        if r["favicon"] is not None:
            img_url = "https://api.minetools.eu/favicon/"+str(ip) + str("/"+str(port) if port is not None else '')
        else:
            img_url = None
        v = r['version']['name']
        o = r['players']['online']
        m = r['players']['max']
        l = r['latency']
        return await self.mcServer(IP,version=v,online_players=o,max_players=m,players=players,img=img_url,ping=l,desc=r['description'],api='api.minetools.eu').clear_desc()


    async def create_server_2(self, guild: discord.Guild, ip:str, port:str):
        if port is None:
            url = "https://api.mcsrvstat.us/1/"+str(ip)
        else:
            url = "https://api.mcsrvstat.us/1/"+str(ip)+"/"+str(port)
        try:
            r = requests.get(url,timeout=5).json()
        except requests.exceptions.ConnectionError:
            return await self.bot._(guild,"mc","no-api")
        except:
            try:
                r = requests.get("https://api.mcsrvstat.us/1/"+str(ip),timeout=5).json()
            except Exception as e:
                if not isinstance(e,requests.exceptions.ReadTimeout):
                    await self.bot.log.error("[mc-server-2] Erreur sur l'url {} :".format(url))
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
                return await self.bot._(guild,"mc","serv-error")
        if r["debug"]["ping"] == False:
            return await self.bot._(guild,"mc","no-ping")
        if 'list' in r['players'].keys():
            players = r['players']['list'][:20]
        else:
            players = []
        if players == []:
            if r['players']['online'] == 0:
                players = [str(await self.bot._(guild,"keywords","none")).capitalize()]
            else:
                players=['Non disponible']
        if "software" in r.keys():
            version = r["software"]+" "+r['version']
        else:
            version = r['version']
        IP = "{}:{}".format(ip,port) if port is not None else str(ip)
        desc = "\n".join(r['motd']['clean'])
        o = r['players']['online']
        m = r['players']['max']
        l = None
        return await self.mcServer(IP,version=version,online_players=o,max_players=m,players=players,img=None,ping=l,desc=desc,api="api.mcsrvstat.us").clear_desc()

    class mcServer:
        def __init__(self,ip,max_players,online_players,players,ping,img,version,api,desc):
            self.ip = ip
            self.max_players = max_players 
            self.online_players = online_players
            self.players = players
            if str(ping).isnumeric():
                self.ping = round(float(ping),3)
            else:
                self.ping = ping
            self.image = img
            self.version = version
            self.api = api
            self.desc = desc
            
        async def clear_desc(self):
            for m in re.finditer(r"§.",self.desc):
                self.desc = self.desc.replace(m.group(0),"")
            self.desc = self.desc.replace("\n             ","\n")
            return self

        async def create_msg(self, guild: discord.Guild, translate):
            if self.players==[]:
                if self.online_players == 0:
                    p = ["Aucun"]
                else:
                    p = ['Non disponible']
            else:
                p = self.players
            embed = discord.Embed(title=str(await translate(guild,"mc","serv-title")).format(self.ip), color=discord.Colour(0x417505), timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_footer(text="From {}".format(self.api))
            if self.image is not None:
                embed.set_thumbnail(url=self.image)
            embed.add_field(name="Version", value=self.version)
            embed.add_field(name=await translate(guild,"mc","serv-0"), value="{}/{}".format(self.online_players,self.max_players))
            if len(p)>20:
                embed.add_field(name=await translate(guild,"mc","serv-1"), value=", ".join(p[:20]))
            else:
                embed.add_field(name=await translate(guild,"mc","serv-2"), value=", ".join(p))
            if self.ping is not None:
                embed.add_field(name=await translate(guild,"mc","serv-3"), value=str(self.ping)+" ms")
            embed.add_field(name="Description", value=self.desc,inline=False)
            return embed

    async def send_msg_server(self, obj, channel: discord.abc.Messageable, ip: str):
        guild = None if isinstance(channel,discord.DMChannel) else channel.guild
        e = await self.form_msg_server(obj,guild,ip)
        if self.bot.zombie_mode:
            return
        if isinstance(channel,discord.DMChannel) or channel.permissions_for(channel.guild.me).embed_links:
            msg = await channel.send(embed=e)
        else:
            try:
                await channel.send(await self.bot._(guild,"mc","cant-embed"))
            except discord.errors.Forbidden:
                pass
            msg = None
        return msg

    async def form_msg_server(self, obj, guild: discord.Guild, ip: str):
        if type(obj) == str:
            if ip[1] is None:
                ip = ip[0]
            else:
                ip = ip[0]+":"+ip[1]
            return discord.Embed(title=str(await self.bot._(guild,"mc","serv-title")).format(ip), color=discord.Colour(0x417505),description=obj,timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        else:
            return await obj.create_msg(guild,self.bot._)

    async def find_msg(self, channel:discord.TextChannel, ip:list, ID:str):
        if channel is None:
            return None
        if ID.isnumeric():
            try:
                return await channel.fetch_message(int(ID))
            except:
                pass
        return None

    async def check_flow(self, flow: dict):
        i = flow["link"].split(':')
        if i[1] == '':
            i[1] = None
        guild = self.bot.get_guild(flow['guild'])
        if guild is None:
            return
        if flow['link'] in self.flows.keys():
            obj = self.flows[flow['link']]
        else:
            try:
                obj = await self.create_server_1(guild,i[0],i[1])
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
                return
            self.flows[flow['link']] = obj
        try:
            channel = guild.get_channel(flow['channel'])
            if channel is None:
                return
            msg = await self.find_msg(channel,i,flow['structure'])
            if msg is None:
                msg = await self.send_msg_server(obj,channel,i)
                if msg is not None:
                    await self.bot.cogs['RssCog'].update_flow(flow['ID'],[('structure',str(msg.id)),('date',datetime.datetime.utcnow())])
                return
            e = await self.form_msg_server(obj,guild,i)
            await msg.edit(embed=e)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)



def setup(bot):
    bot.add_cog(McCog(bot))
