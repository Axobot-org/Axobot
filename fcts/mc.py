import frmc_lib, aiohttp, discord, re, datetime, time, requests
from discord.ext import commands


class McCog(commands.Cog):
    """Cog gathering all commands related to the Minecraft® game. 
Every information come from the website www.fr-minecraft.net"""
    
    def __init__(self,bot):
        self.bot = bot
        self.flows = dict()
        self.file = "mc"
        try:
            self.translate = bot.cogs["LangCog"].tr
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr

    @commands.command(name="mojang",aliases=['mojang_status'])
    @commands.cooldown(5,20,commands.BucketType.user)
    async def mojang_status(self,ctx):
        """Get Mojang server status"""
        desc = await self.translate(ctx.channel,"mc","mojang_desc")
        async with aiohttp.ClientSession() as session:
            async with session.get('https://status.mojang.com/check') as r:
                # data = requests.get("https://status.mojang.com/check").json()
                data = await r.json()
        if ctx.guild==None:
            can_embed = True
        else:
            can_embed = ctx.channel.permissions_for(ctx.guild.me).embed_links
        if can_embed:
            embed = discord.Embed(colour=discord.Colour(0x699bf9), timestamp=ctx.message.created_at)
            embed.set_thumbnail(url="https://pbs.twimg.com/profile_images/623422129502056448/9ehvGDEy.png")
            embed.set_author(name="Mojang - Services Status", url="https://status.mojang.com/check", icon_url="https://pbs.twimg.com/profile_images/623422129502056448/9ehvGDEy.png")
            embed.set_footer(text="Requested by {}".format(ctx.author.display_name), icon_url=ctx.author.avatar_url_as(format='png',size=512))
        else:
            text = "Mojang - Services Status (requested by {})".format(ctx.author)
        for service in data:
            for K,V in service.items():
                if V == "green":
                    k = ":white_check_mark: "+K
                elif V == "red":
                    k = self.bot.cogs['EmojiCog'].customEmojis['red_cross']+K
                else:
                    k = self.bot.cogs['EmojiCog'].customEmojis['blurple']+K
                    dm = self.bot.get_user(279568324260528128).dm_channel
                    if dm == None:
                        await self.bot.get_user(279568324260528128).create_dm()
                        dm = self.bot.get_user(279568324260528128).dm_channel
                    await dm.send("Status mojang inconnu : "+V+" (serveur "+K+")")
                if K in desc.keys():
                    v = desc[K]
                else:
                    v = ''
                if can_embed:
                    embed.add_field(name=k,value=v+self.bot.cogs['EmojiCog'].customEmojis['nothing'], inline=False)
                else:
                    text += "\n {} *({})*".format(k,v)
        if can_embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send(text)

    @commands.group(name="mc")
    @commands.cooldown(5,30,commands.BucketType.user)
    async def mc_main(self,ctx):
        """Search for Minecraft game items/servers"""
        return

    @mc_main.command(name="block",aliases=["bloc"])
    async def mc_block(self,ctx,value='help'):
        """Get infos about any block"""
        if value=='help':
            await ctx.send(await self.translate(ctx.channel,"mc","block-help"))
            return
        try:
            Block = frmc_lib.main(value,'Bloc')
        except:
            await ctx.send(await self.translate(ctx.channel,"mc","no-block"))
            return
        title = "{} - {}".format((await self.translate(ctx.channel,"mc","names"))[0],Block.Name)
        embed = discord.Embed(title=title, colour=discord.Colour(int('16BD06',16)), url=Block.Url, timestamp=ctx.message.created_at,description=await self.translate(ctx.channel,'mc','contact-mail'))
        embed.set_thumbnail(url=Block.Image)
        embed = await self.bot.cogs["UtilitiesCog"].create_footer(embed,ctx.author)
        embed.add_field(name="Nom", value=Block.Name,inline=False)
        l = ("\n".join(Block.ID),Block.Stack,Block.CreativeTab,Block.Damage,Block.Strength,Block.Tool,", ".join(Block.Mobs),Block.Version)
        for e,v in enumerate(await self.translate(ctx.channel,"mc","block-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.translate(ctx.channel,"mc","no-entity"))

    @mc_main.command(name="entity",aliases=["entité","mob"])
    async def mc_entity(self,ctx,value='help'):
        """Get infos about any entity"""
        if value=='help':
            await ctx.send(await self.translate(ctx.channel,"mc","entity-help"))
            return
        try:
            Entity = frmc_lib.main(value,'Entité')
        except:
            await ctx.send(await self.translate(ctx.channel,"mc","no-entity"))
            return
        title = "{} - {}".format((await self.translate(ctx.channel,"mc","names"))[1],Entity.Name)
        embed = discord.Embed(title=title, colour=discord.Colour(int('16BD06',16)), url=Entity.Url, timestamp=ctx.message.created_at,description=await self.translate(ctx.channel,'mc','contact-mail'))
        embed.set_thumbnail(url=Entity.Image)
        embed = await self.bot.cogs["UtilitiesCog"].create_footer(embed,ctx.author)
        embed.add_field(name="Nom", value=Entity.Name,inline=False)
        l = (Entity.ID,Entity.Type,Entity.PV,Entity.PA,Entity.XP,", ".join(Entity.Biomes),Entity.Version)
        for e,v in enumerate(await self.translate(ctx.channel,"mc","entity-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        if Entity.Dimensions != [0,0,0]:
            embed.add_field(name="Dimensions",value=str(await self.translate(ctx.channel,"mc","dimensions")).format(d=Entity.Dimensions))
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.translate(ctx.channel,"mc","no-entity"))
    
    @mc_main.command(name="item",aliases=['object'])
    async def mc_item(self,ctx,value='help'):
        """Get infos about any item"""
        if value=='help':
            await ctx.send(await self.translate(ctx.channel,"mc","item-help"))
            return
        try:
            Item = frmc_lib.main(value,"Item")
        except:
            await ctx.send(await self.translate(ctx.channel,"mc","no-item"))
            return
        title = "{} - {}".format((await self.translate(ctx.channel,"mc","names"))[2],Item.Name)
        embed = discord.Embed(title=title, colour=discord.Colour(int('16BD06',16)), url=Item.Url, timestamp=ctx.message.created_at,description=await self.translate(ctx.channel,'mc','contact-mail'))
        if Item.Image != None:
            embed.set_thumbnail(url=Item.Image)
        embed = await self.bot.cogs["UtilitiesCog"].create_footer(embed,ctx.author)
        embed.add_field(name="Nom", value=Item.Name,inline=False)
        l = ('\n'.join(Item.ID),Item.Stack,Item.CreativeTab,Item.Damage,Item.Strength,Item.Tool,", ".join(Item.Mobs),Item.Version)
        for e,v in enumerate(await self.translate(ctx.channel,"mc","item-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.translate(ctx.channel,"mc","no-entity"))

    @mc_main.command(name="command",aliases=["commande","cmd"])
    async def mc_cmd(self,ctx,value='help'):
        """Get infos about any command"""
        if value=='help':
            await ctx.send(await self.translate(ctx.channel,"mc","cmd-help"))
            return
        try:
            Cmd = frmc_lib.main(value,'Commande')
        except:
            await ctx.send(await self.translate(ctx.channel,"mc","no-cmd"))
            return
        title = "{} - {}".format((await self.translate(ctx.channel,"mc","names"))[3],Cmd.Name)
        embed = discord.Embed(title=title, colour=discord.Colour(int('16BD06',16)), url=Cmd.Url, timestamp=ctx.message.created_at,description=await self.translate(ctx.channel,'mc','contact-mail'))
        embed = await self.bot.cogs["UtilitiesCog"].create_footer(embed,ctx.author)
        l = (Cmd.Name," ".join(Cmd.Syntax),Cmd.Examples,Cmd.Version)
        for e,v in enumerate(await self.translate(ctx.channel,"mc","cmd-fields")):
            if e==2:
                if len(l[e]) > 0:
                    examples = ["`{}`\n*{}*".format(x[0],x[1]) for x in l[e][:5]]
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
            await ctx.send(await self.translate(ctx.channel,"mc","no-cmd"))
    
    @mc_main.command(name="advancement",aliases=["advc","progrès"])
    async def mc_advc(self,ctx,value='help'):
        """Get infos about any advancement"""
        if value=='help':
            await ctx.send(await self.translate(ctx.channel,"mc","adv-help"))
            return
        try:
            Adv = frmc_lib.main(value,'Progrès')
        except:
            await ctx.send(await self.translate(ctx.channel,"mc","no-adv"))
            return
        title = "{} - {}".format((await self.translate(ctx.channel,"mc","names"))[4],Adv.Name)
        embed = discord.Embed(title=title, colour=discord.Colour(int('16BD06',16)), url=Adv.Url, timestamp=ctx.message.created_at,description=await self.translate(ctx.channel,'mc','contact-mail'))
        embed = await self.bot.cogs["UtilitiesCog"].create_footer(embed,ctx.author)
        if Adv.Image != None:
            embed.set_thumbnail(url=Adv.Image)
        l = (Adv.Name,Adv.ID,Adv.Type,Adv.Action,Adv.Parent,", ".join(Adv.Children),Adv.Version)   #("Nom","Identifiant","Type","Action","Parent","Enfants","Version d'ajout")
        for e,v in enumerate(await self.translate(ctx.channel,"mc","adv-fields")):
            if l[e] not in [None,'']:
                try:
                    embed.add_field(name=v, value=l[e])
                except:
                    pass
        try:
            await ctx.send(embed=embed)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await ctx.send(await self.translate(ctx.channel,"mc","no-adv"))


    @mc_main.command(name="server")
    async def mc_server(self,ctx,ip,port:int=None):
        """Get infos about any Minecraft server"""
        if ":" in ip and port==None:
            i = ip.split(":")
            ip,port = i[0],i[1]
        obj = await self.create_server_1(ctx.guild,ip,port)
        await self.send_msg_server(obj,ctx.channel,(ip,port))

    @mc_main.command(name="add")
    @commands.guild_only()
    async def mc_add_server(self,ctx,ip,port:int=None):
        """Follow a server's info (regularly displayed on this channel)"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.translate(ctx.guild.id,"cases","no_database"))
        if ":" in ip and port==None:
            i = ip.split(":")
            ip,port = i[0],i[1]
        elif port == None:
            port = ''
        if len(await self.bot.cogs['RssCog'].get_guild_flows(ctx.guild.id)) >= self.bot.cogs['RssCog'].flow_limit:
            await ctx.send(str(await self.translate(ctx.guild.id,"rss","flow-limit")).format(self.bot.cogs['RssCog'].flow_limit))
            return
        try:
            if port == None:
                display_ip = ip
            else:
                display_ip = "{}:{}".format(ip,port)
            await self.bot.cogs['RssCog'].add_flow(ctx.guild.id,ctx.channel.id,'mc',"{}:{}".format(ip,port))
            await ctx.send(str(await self.translate(ctx.guild,"mc","success-add")).format(display_ip,ctx.channel.mention))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild,"rss","fail-add"))
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)


    async def create_server_1(self,guild,ip,port=None):
        print2 = self.bot.cogs['UtilitiesCog'].print2
        if port == None:
            url = "https://api.minetools.eu/ping/"+str(ip)
        else:
            url = "https://api.minetools.eu/ping/"+str(ip)+"/"+str(port)
        try:
            r = requests.get(url,timeout=5).json()
        except requests.exceptions.ConnectionError:
            return await self.create_server_2(guild,ip,port)
        except requests.exceptions.ReadTimeout:
            return await self.create_server_2(guild,ip,port)
        except Exception as e:
            return await self.create_server_2(guild,ip,port)
            self.bot.log.warn("[mc-server-1] Erreur sur l'url {} :".format(url))
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return await self.translate(guild,"mc","serv-error")
        if "error" in r.keys():
            if r['error'] != 'timed out':
                await print2("(mc-server) Error on: "+url+"\n   "+r['error'])
            return r["error"]
        players=[]
        try:
            for p in r['players']['sample']:
                players.append(p['name'])
                if len(players)>30:
                    break
        except:
            players = []
        if players==[]:
            if r['players']['online']==0:
                players = [str(await self.translate(guild,"keywords","none")).capitalize()]
            else:
                players=['Non disponible']
        IP = "{}:{}".format(ip,port) if port != None else str(ip)
        if r["favicon"] != None:
            img_url = "https://api.minetools.eu/favicon/"+str(ip) + str("/"+str(port) if port != None else '')
        else:
            img_url = None
        v = r['version']['name']
        o = r['players']['online']
        m = r['players']['max']
        l = r['latency']
        return await self.mcServer(IP,version=v,online_players=o,max_players=m,players=players,img=img_url,ping=l,desc=r['description'],api='api.minetools.eu').clear_desc()


    async def create_server_2(self,guild,ip,port):
        if port == None:
            url = "https://api.mcsrvstat.us/1/"+str(ip)
        else:
            url = "https://api.mcsrvstat.us/1/"+str(ip)+"/"+str(port)
        try:
            r = requests.get(url,timeout=5).json()
        except requests.exceptions.ConnectionError:
            return await self.translate(guild,"mc","no-api")
        except:
            try:
                r = requests.get("https://api.mcsrvstat.us/1/"+str(ip),timeout=5).json()
            except Exception as e:
                if not isinstance(e,requests.exceptions.ReadTimeout):
                    await self.bot.log.error("[mc-server-2] Erreur sur l'url {} :".format(url))
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
                return await self.translate(guild,"mc","serv-error")
        if r["debug"]["ping"] == False:
            return await self.translate(guild,"mc","no-ping")
        if 'list' in r['players'].keys():
            players = r['players']['list'][:20]
        else:
            players = []
        if players == []:
            if r['players']['online'] == 0:
                players = [str(await self.translate(guild,"keywords","none")).capitalize()]
            else:
                players=['Non disponible']
        if "software" in r.keys():
            version = r["software"]+" "+r['version']
        else:
            version = r['version']
        IP = "{}:{}".format(ip,port) if port != None else str(ip)
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

        async def create_msg(self,guild,translate):
            if self.players==[]:
                if self.online_players==0:
                    p = ["Aucun"]
                else:
                    p = ['Non disponible']
            else:
                p = self.players
            embed = discord.Embed(title=str(await translate(guild,"mc","serv-title")).format(self.ip), colour=discord.Colour(0x417505), timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_footer(text="From {}".format(self.api))
            if self.image != None:
                embed.set_thumbnail(url=self.image)
            embed.add_field(name="Version", value=self.version)
            embed.add_field(name=await translate(guild,"mc","serv-0"), value="{}/{}".format(self.online_players,self.max_players))
            if len(p)>20:
                embed.add_field(name=await translate(guild,"mc","serv-1"), value=", ".join(p[:20]))
            else:
                embed.add_field(name=await translate(guild,"mc","serv-2"), value=", ".join(p))
            if self.ping != None:
                embed.add_field(name=await translate(guild,"mc","serv-3"), value=str(self.ping)+" ms")
            embed.add_field(name="Description", value=self.desc,inline=False)
            return embed

    async def send_msg_server(self,obj,channel,ip):
        guild = None if isinstance(channel,discord.DMChannel) else channel.guild
        e = await self.form_msg_server(obj,guild,ip)
        if isinstance(channel,discord.DMChannel) or channel.permissions_for(channel.guild.me).embed_links:
            msg = await channel.send(embed=e)
        else:
            try:
                await channel.send(await self.translate(guild,"mc","cant-embed"))
            except discord.errors.Forbidden:
                pass
            msg = None
        return msg

    async def form_msg_server(self,obj,guild,ip):
        if type(obj) == str:
            if ip[1] == None:
                ip = ip[0]
            else:
                ip = ip[0]+":"+ip[1]
            return discord.Embed(title=str(await self.translate(guild,"mc","serv-title")).format(ip), colour=discord.Colour(0x417505),description=obj,timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        else:
            return await obj.create_msg(guild,self.translate)

    async def find_msg(self,channel:discord.TextChannel,ip:list,ID:str):
        if channel == None:
            return None
        if ID.isnumeric():
            try:
                return await channel.fetch_message(int(ID))
            except:
                pass
        return None

    async def check_flow(self,flow):
        i = flow["link"].split(':')
        if i[1] == '':
            i[1] = None
        guild = self.bot.get_guild(flow['guild'])
        if guild==None:
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
            if channel == None:
                return
            msg = await self.find_msg(channel,i,flow['structure'])
            if msg == None:
                msg = await self.send_msg_server(obj,channel,i)
                if msg!=None:
                    await self.bot.cogs['RssCog'].update_flow(flow['ID'],[('structure',str(msg.id)),('date',datetime.datetime.utcnow())])
                return
            e = await self.form_msg_server(obj,guild,i)
            await msg.edit(embed=e)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)



def setup(bot):
    bot.add_cog(McCog(bot))
