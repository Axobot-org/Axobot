import discord, random, time, asyncio, io, imageio, importlib, re, os, operator, platform, typing, aiohttp, mysql
from discord.ext import commands
from math import ceil
from json import dumps
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageTk, ImageSequence, ImageEnhance
from urllib.request import urlopen, Request

from io import BytesIO
from math import sqrt

from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)



class XPCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.cache = {'global':{}}
        self.levels = [0]
        self.embed_color = discord.Colour(0xffcf50)
        self.table = 'xp_beta' if bot.beta else 'xp'
        self.cooldown = 30
        self.minimal_size = 5
        self.spam_rate = 0.20
        self.xp_per_char = 0.11
        self.max_xp_per_msg = 60
        self.file = 'xp'
        self.xp_channels_cache = dict()
        bot.add_listener(self.add_xp,'on_message')
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
        self.types = ['global','mee6-like','local']
        if platform.system()=='Darwin':
            verdana_name = 'Verdana.ttf'
        else:
            verdana_name = 'Veranda.ttf'
        self.fonts = {'xp_fnt': ImageFont.truetype(verdana_name, 24),
        'NIVEAU_fnt': ImageFont.truetype(verdana_name, 42),
        'levels_fnt': ImageFont.truetype(verdana_name, 65),
        'rank_fnt': ImageFont.truetype(verdana_name,29),
        'RANK_fnt': ImageFont.truetype(verdana_name,23)}
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
        self.table = 'xp_beta' if self.bot.beta else 'xp'
        await self.bdd_load_cache(-1)
        if not self.bot.database_online:
            self.bot.unload_extension("fcts.xp")

    async def add_xp(self,msg):
        """Attribue un certain nombre d'xp à un message"""
        if msg.author.bot or msg.guild==None or not self.bot.xp_enabled:
            return
        used_xp_type = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'xp_type')
        if not ( await self.check_noxp(msg) and await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'enable_xp') ):
            return
        rate = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'xp_rate')
        if used_xp_type==0:
            await self.add_xp_0(msg,rate)
        elif used_xp_type==1:
            await self.add_xp_1(msg,rate)
        elif used_xp_type==2:
            await self.add_xp_2(msg,rate)
    
    async def add_xp_0(self,msg:discord.Message,rate:float):
        if msg.author.id in self.cache['global'].keys():
            if time.time() - self.cache['global'][msg.author.id][0] < self.cooldown:
                return
        content = msg.clean_content
        if len(content)<self.minimal_size or await self.check_spam(content) or await self.check_cmd(msg):
            return
        if len(self.cache["global"])==0:
            await self.bdd_load_cache(-1)
        giv_points = await self.calc_xp(msg)
        if msg.author.id in self.cache['global'].keys():
            prev_points = self.cache['global'][msg.author.id][1]
        else:
            try:
                prev_points = (await self.bdd_get_xp(msg.author.id,None))
                if len(prev_points)>0:
                    prev_points = prev_points[0]['xp']
                else:
                    prev_points = 0
            except:
                prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points, 'add')
        self.cache['global'][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl = await self.calc_level(self.cache['global'][msg.author.id][1],0)
        if 0 < (await self.calc_level(prev_points,0))[0] < new_lvl[0]:
            await self.send_levelup(msg,new_lvl)
            await self.give_rr(msg.author,new_lvl[0],await self.rr_list_role(msg.guild.id))
    
    async def add_xp_1(self,msg:discord.Message,rate:float):
        if msg.guild.id not in self.cache.keys() or len(self.cache[msg.guild.id])==0:
            await self.bdd_load_cache(msg.guild.id)
        if msg.author.id in self.cache[msg.guild.id].keys():
            if time.time() - self.cache[msg.guild.id][msg.author.id][0] < 60:
                return
        if await self.check_cmd(msg):
            return
        giv_points = random.randint(15,25) * rate
        if msg.author.id in self.cache[msg.guild.id].keys():
            prev_points = self.cache[msg.guild.id][msg.author.id][1]
        else:
            try:
                prev_points = (await self.bdd_get_xp(msg.author.id,msg.guild.id))
                if len(prev_points)>0:
                    prev_points = prev_points[0]['xp']
                else:
                    prev_points = 0
            except:
                prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points, 'add', msg.guild.id)
        self.cache[msg.guild.id][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl = await self.calc_level(self.cache[msg.guild.id][msg.author.id][1],1)
        if 0 < (await self.calc_level(prev_points,1))[0] < new_lvl[0]:
            await self.send_levelup(msg,new_lvl)
            await self.give_rr(msg.author,new_lvl[0],await self.rr_list_role(msg.guild.id))

    async def add_xp_2(self,msg:discord.Message,rate:float):
        if msg.guild.id not in self.cache.keys() or len(self.cache[msg.guild.id])==0:
            await self.bdd_load_cache(msg.guild.id)
        if msg.author.id in self.cache[msg.guild.id].keys():
            if time.time() - self.cache[msg.guild.id][msg.author.id][0] < self.cooldown:
                return
        content = msg.clean_content
        if len(content)<self.minimal_size or await self.check_spam(content) or await self.check_cmd(msg):
            return
        giv_points = await self.calc_xp(msg) * rate
        if msg.author.id in self.cache[msg.guild.id].keys():
            prev_points = self.cache[msg.guild.id][msg.author.id][1]
        else:
            try:
                prev_points = (await self.bdd_get_xp(msg.author.id,msg.guild.id))
                if len(prev_points)>0:
                    prev_points = prev_points[0]['xp']
                else:
                    prev_points = 0
            except:
                prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points, 'add', msg.guild.id)
        self.cache[msg.guild.id][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl = await self.calc_level(self.cache[msg.guild.id][msg.author.id][1],2)
        if 0 < (await self.calc_level(prev_points,2))[0] < new_lvl[0]:
            await self.send_levelup(msg,new_lvl)
            await self.give_rr(msg.author,new_lvl[0],await self.rr_list_role(msg.guild.id))
    
    


    async def check_noxp(self,msg):
        """Check if this channel/user can get xp"""
        if msg.guild == None:
            return False
        if msg.guild.id in self.xp_channels_cache.keys():
            if msg.channel.id in self.xp_channels_cache[msg.guild.id]:
                return False
        else:
            chans = await self.bot.cogs["ServerCog"].find_staff(msg.guild.id,'noxp_channels')
            if chans != None:
                chans = [int(x) for x in chans.split(';') if x.isnumeric()]
                if msg.channel.id in chans:
                    return False
            else:
                chans = []
            self.xp_channels_cache[msg.guild.id] = chans
        return True


    async def send_levelup(self,msg,lvl):
        """Envoie le message de levelup"""
        await self.bot.cogs["UtilitiesCog"].add_user_eventPoint(msg.author.id,round(lvl[0]/5))
        if msg.guild!=None and not msg.channel.permissions_for(msg.guild.me).send_messages:
            return
        text = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'levelup_msg')
        if text==None or len(text)==0:
            text = random.choice(await self.bot.cogs['LangCog'].tr(msg.channel,'xp','default_levelup'))
            while (not '{random}' in text) and random.random()<0.8:
                text = random.choice(await self.bot.cogs['LangCog'].tr(msg.channel,'xp','default_levelup'))
        if '{random}' in text:
            item = random.choice(await self.bot.cogs['LangCog'].tr(msg.channel,'xp','levelup-items'))
        else:
            item = ''
        await msg.channel.send(text.format_map(self.bot.SafeDict(user=msg.author.mention,level=lvl[0],random=item,username=msg.author.display_name)))
        
    async def check_cmd(self,msg):
        """Vérifie si un message est une commande"""
        pr = await self.bot.get_prefix(msg)
        is_cmd = False
        for p in pr:
            is_cmd = is_cmd or msg.content.startswith(p)
        return is_cmd

    async def check_spam(self,text):
        """Vérifie si un text contient du spam"""
        d = dict()
        for c in text:
            if c in d.keys():
                d[c] += 1
            else:
                d[c] = 1
        for v in d.values():
            if v/len(text) > self.spam_rate:
                return True
        return False

    async def calc_xp(self,msg):
        """Calcule le nombre d'xp correspondant à un message"""
        content = msg.clean_content
        matches = re.finditer(r"<a?(:\w+:)\d+>", content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0),match.group(1))
        matches = re.finditer(r'((?:http|www)[^\s]+)', content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0),"")
        return min(round(len(content)*self.xp_per_char), self.max_xp_per_msg)

    async def calc_level(self,xp:int,system:int):
        """Calcule le niveau correspondant à un nombre d'xp"""
        if system != 1:
            if xp==0:
                return [0,ceil((1*125/7)**(20/13)),0]
            lvl = ceil(0.056*xp**0.65)
            next_step = xp
            while ceil(0.056*next_step**0.65)==lvl:
                next_step += 1
            return [lvl,next_step,ceil(((lvl-1)*125/7)**(20/13))]
        # Niveau actuel - XP total pour le prochain niveau - XP total pour le niveau actuel
        else:
            def recursive(lvl):
                t = 0
                for i in range(lvl):
                    t += 5*pow(i,2) + 50*i + 100
                return t

            if xp==0:
                return [0,100,0]
            lvl = 0
            total_xp = 0
            while xp >= total_xp:
                total_xp += 5*pow(lvl,2) + 50*lvl + 100
                lvl += 1
            return [lvl-1,recursive(lvl),recursive(lvl-1)]

    async def give_rr(self,member:discord.Member,level:int,rr_list:list,remove=False):
        """Give (and remove?) roles rewards to a member"""
        c = 0
        has_roles = [x.id for x in member.roles]
        for role in [x for x in rr_list if x['level']<=level and x['role'] not in has_roles]:
            try:
                r = member.guild.get_role(role['role'])
                if r==None:
                    continue
                if not self.bot.beta:
                    await member.add_roles(r,reason="Role reward (lvl {})".format(role['level']))
                c += 1
            except Exception as e:
                if self.bot.beta:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                pass
        if not remove:
            return c
        for role in [x for x in rr_list if x['level']>level and x['role'] in has_roles]:
            try:
                r = member.guild.get_role(role['role'])
                if r==None:
                    continue
                if not self.bot.beta:
                    await member.remove_roles(r,reason="Role reward (lvl {})".format(role['level']))
                c += 1
            except Exception as e:
                if self.bot.beta:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                pass
        return c

    async def get_table(self,guild:int,createIfNeeded:bool=True):
        """Get the table name of a guild, and create one if no one exist"""
        if guild==None:
            return self.table
        cnx = self.bot.cnx_xp
        cursor = cnx.cursor()
        try:
            cursor.execute("SELECT 1 FROM `{}` LIMIT 1;".format(guild))
            return guild
        except mysql.connector.errors.ProgrammingError:
            if createIfNeeded:
                cursor.execute("CREATE TABLE `{}` LIKE `example`;".format(guild))
                cursor.execute("SELECT 1 FROM `{}` LIMIT 1;".format(guild))
                return guild
            else:
                return None


    async def bdd_set_xp(self,userID,points,Type='add',guild:int=None):
        """Ajoute/reset de l'xp à un utilisateur dans la database"""
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return None
            if points==0:
                return True
            if guild==None:
                cnx = self.bot.cnx_frm
            else:
                cnx = self.bot.cnx_xp
            table = await self.get_table(guild)
            cursor = cnx.cursor(dictionary = True)
            if Type=='add':
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = xp + '{p}';".format(t=table,p=points,u=userID))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = '{p}';".format(t=table,p=points,u=userID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def bdd_get_xp(self,userID,guild:int):
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return None
            if guild==None:
                cnx = self.bot.cnx_frm
            else:
                cnx = self.bot.cnx_xp
            query = ("SELECT `xp` FROM `{}` WHERE `userID`={} AND `banned`=0".format(await self.get_table(guild),userID))
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            if len(liste)==1:
                if userID in self.cache.keys():
                    self.cache[userID][1] = liste[0]['xp']
                else:
                    self.cache[userID] = [round(time.time())-60,liste[0]['xp']]
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
    
    async def bdd_get_nber(self,guild:int=None):
        """Get the number of ranked users"""
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return None
            if guild==None:
                cnx = self.bot.cnx_frm
            else:
                cnx = self.bot.cnx_xp
            query = ("SELECT COUNT(*) FROM `{}` WHERE `banned`=0".format(await self.get_table(guild)))
            cursor = cnx.cursor(dictionary = False)
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            if liste!=None and len(liste)==1:
                return liste[0][0]
            return 0
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_load_cache(self,guild:int):
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return
            globalS = guild==-1
            if globalS:
                self.bot.log.info("Chargement du cache XP (global)")
                cnx = self.bot.cnx_frm
                query = ("SELECT `userID`,`xp` FROM `{}` WHERE `banned`=0".format(self.table))
            else:
                self.bot.log.info("Chargement du cache XP (guild {})".format(guild))
                table = await self.get_table(guild,False)
                if table==None:
                    self.cache[guild] = dict()
                    return 
                cnx = self.bot.cnx_xp
                query = ("SELECT `userID`,`xp` FROM `{}` WHERE `banned`=0".format(table))
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            if globalS:
                if len(self.cache['global'].keys())==0:
                    self.cache['global'] = dict()
                for l in liste:
                    self.cache['global'][l['userID']] = [round(time.time())-60,l['xp']]
            else:
                if guild not in self.cache.keys():
                    self.cache[guild] = dict()
                for l in liste:
                    self.cache[guild][l['userID']] = [round(time.time())-60,l['xp']]
            cursor.close()
            return
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_get_top(self,top:int,guild:discord.Guild=None):
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return None
            if guild!=None and await self.bot.cogs['ServerCog'].find_staff(guild.id,'xp_type')!=0:
                cnx = self.bot.cnx_xp
                query = ("SELECT * FROM `{}` order by `xp` desc".format(await self.get_table(guild.id)))
            else:
                cnx = self.bot.cnx_frm
                query = ("SELECT * FROM `{}` order by `xp` desc".format(self.table))
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            liste = list()
            if guild==None:
                liste = [x for x in cursor][:top]
            else:
                ids = [x.id for x in guild.members]
                i = 0
                l2 = [x for x in cursor]
                while len(liste)<top and i<len(l2):
                    if l2[i]['userID'] in ids:
                        liste.append(l2[i])
                    i += 1
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
        
    async def bdd_get_rank(self,userID:int,guild:discord.Guild=None):
        """Get the rank of a user"""
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return None
            if guild!=None and await self.bot.cogs['ServerCog'].find_staff(guild.id,'xp_type')!=0:
                cnx = self.bot.cnx_xp
                query = ("SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;".format(await self.get_table(guild.id)))
            else:
                cnx = self.bot.cnx_frm
                query = ("SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;".format(self.table))
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            userdata = dict()
            i = 0
            if guild!=None:
                users = [x.id for x in guild.members]
            for x in cursor:
                if (guild!=None and x['userID'] in users) or guild==None:
                    i += 1
                if x['userID']== userID:
                    x['rank'] = i
                    userdata = x
                    break
            cursor.close()
            return userdata
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_total_xp(self):
        """Get the total number of earned xp"""
        try:
            if not self.bot.database_online:
                self.bot.unload_extension("fcts.xp")
                return None
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT SUM(xp) FROM `{}`".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            result = round(liste[0]['SUM(xp)'])

            cnx = self.bot.cnx_xp
            cursor = cnx.cursor()
            cursor.execute("show tables")
            tables = [x[0] for x in cursor if x[0].isnumeric()]
            for table in tables:
                cursor.execute("SELECT SUM(xp) FROM `{}`".format(table))
                res = [x for x in cursor]
                if res[0][0]!=None:
                    result += round(res[0][0])
            cursor.close()
            return result
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


    async def get_raw_image(self,url,size=282):
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        im = Image.open(io.BytesIO(urlopen(req).read()))
        return im

    def calc_pos(self,text,font,x,y,align='center'):
        w,h = font.getsize(text)
        if align=='center':
            return x-w/2,y-h/2
        elif align=='right':
            return x-w,y-h/2

    async def create_card(self,user,style,xp,used_system:int,rank=[1,0],txt=['NIVEAU','RANG'],force_static=False,levels_info=None):
        """Crée la carte d'xp pour un utilisateur"""
        card = Image.open("../cards/model/{}.png".format(style))
        bar_colors = await self.get_xp_bar_color(user.id)
        if levels_info==None:
            levels_info = await self.calc_level(xp,used_system)
        colors = {'name':(124, 197, 118),'xp':(124, 197, 118),'NIVEAU':(255, 224, 77),'rank':(105, 157, 206),'bar':bar_colors}
        if style=='blurple':
            colors = {'name':(35,35,50),'xp':(235, 235, 255),'NIVEAU':(245, 245, 255),'rank':(255, 255, 255),'bar':(70, 83, 138)}
        
        name_fnt = ImageFont.truetype('Roboto-Medium.ttf', 40)

        if not user.is_avatar_animated() or force_static:
            pfp = await self.get_raw_image(user.avatar_url_as(format='png',size=256))
            img = await self.bot.loop.run_in_executor(None,self.add_overlay,pfp.resize(size=(282,282)),user,card,xp,rank,txt,colors,levels_info,name_fnt)
            img.save('../cards/global/{}-{}-{}.png'.format(user.id,xp,rank[0]))
            return discord.File('../cards/global/{}-{}-{}.png'.format(user.id,xp,rank[0]))

        else:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(str(user.avatar_url)) as r:
                    response = await r.read()
                    pfp = Image.open(BytesIO(response))

            images = []
            duration = []
            frames = [frame.copy() for frame in ImageSequence.Iterator(pfp)]
            for frame in frames:
                frame = frame.convert(mode='RGBA')
                img = await self.bot.loop.run_in_executor(None,self.add_overlay,frame.resize(size=(282,282)),user,card.copy(),xp,rank,txt,colors,levels_info,name_fnt)
                img = ImageEnhance.Contrast(img).enhance(1.5).resize((800,265))
                images.append(img)
                duration.append(pfp.info['duration']/1000)
                
            card.close()

            image_file_object = BytesIO()
            gif = images[0]
            gif.save(image_file_object, format='gif', save_all=True, append_images=images[1:], loop=0, duration=duration[0], subrectangles=True)
            image_file_object.seek(0)
            # print(image_file_object.getbuffer().nbytes)
            return discord.File(fp=image_file_object, filename='card.gif')
            # imageio.mimwrite('../cards/global/{}-{}-{}.gif'.format(user.id,xp,rank[0]), images, format="GIF-PIL", duration=duration, subrectangles=True)
            # return discord.File('../cards/global/{}-{}-{}.gif'.format(user.id,xp,rank[0]))

    def compress(self,original_file, max_size, scale):
        assert(0.0 < scale < 1.0)
        orig_image = Image.open(original_file)
        cur_size = orig_image.size

        while True:
            cur_size = (int(cur_size[0] * scale), int(cur_size[1] * scale))
            resized_file = orig_image.resize(cur_size, Image.ANTIALIAS)

            with io.BytesIO() as file_bytes:
                resized_file.save(file_bytes, optimize=True, quality=95, format='png')

                if file_bytes.tell() <= max_size:
                    file_bytes.seek(0, 0)
                    return file_bytes

    def add_overlay(self,pfp,user,img,xp,rank,txt,colors,levels_info,name_fnt):
        #img = Image.new('RGBA', (card.width, card.height), color = (250,250,250,0))
        #img.paste(pfp, (20, 29))
        #img.paste(card, (0, 0), card)
        cardL = img.load()
        pfpL = pfp.load()
        for x in range(list(img.size)[0]):
            for y in range(img.size[1]):
                if sqrt((x-162)**2 + (y-170)**2) < 139:
                    cardL[x,y] = pfpL[x-20,y-29]
                elif cardL[x, y][3]<128:
                    cardL[x,y] = (255,255,255,0)
                    
        
        xp_fnt = self.fonts['xp_fnt']
        NIVEAU_fnt = self.fonts['NIVEAU_fnt']
        levels_fnt = self.fonts['levels_fnt']
        rank_fnt = self.fonts['rank_fnt']
        RANK_fnt = self.fonts['RANK_fnt']
        
        img = self.add_xp_bar(img,xp-levels_info[2],levels_info[1]-levels_info[2],colors['bar'])
        d = ImageDraw.Draw(img)
        d.text(self.calc_pos(user.name,name_fnt,610,68), user.name, font=name_fnt, fill=colors['name'])
        temp = '{} / {} xp ({}/{})'.format(xp-levels_info[2],levels_info[1]-levels_info[2],xp,levels_info[1])
        d.text((self.calc_pos(temp,xp_fnt,625,237)), temp, font=xp_fnt, fill=colors['xp'])
        d.text((380,140), txt[0], font=NIVEAU_fnt, fill=colors['NIVEAU'])
        d.text((self.calc_pos(str(levels_info[0]),levels_fnt,740,160,'right')), str(levels_info[0]), font=levels_fnt, fill=colors['xp'])
        temp = '{x[0]}/{x[1]}'.format(x=rank)
        d.text((self.calc_pos(txt[1],RANK_fnt,893,147,'center')), txt[1], font=RANK_fnt, fill=colors['rank'])
        d.text((self.calc_pos(temp,rank_fnt,893,180,'center')), temp, font=rank_fnt, fill=colors['rank'])
        return img

    def add_xp_bar(self,img,xp,needed_xp,color):
        """Colorize the xp bar"""
        error_rate = 25
        data = np.array(img)   # "data" is a height x width x 4 numpy array
        red, green, blue, alpha = data.T # Temporarily unpack the bands for readability

        # Replace white with red... (leaves alpha values alone...)
        white_areas = (abs(red)-180<error_rate) & (abs(blue)-180<error_rate) & (abs(green)-180<error_rate)
        white_areas[:298] = False & False & False
        max_x = round(298 + (980-298)*xp/needed_xp)
        white_areas[max_x:] = False & False & False
        #white_areas[298:980] = True & True & True
        data[..., :-1][white_areas.T] = color # Transpose back needed
        return Image.fromarray(data)

    async def get_xp_bar_color(self,userID:int):
        return (45,180,105)

    @commands.command(name='rank')
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1,20,commands.BucketType.user)
    async def rank(self,ctx,*,user:args.user=None):
        """Display a user XP.
        If you don't send any user, I'll display your own XP
        """
        try:
            if user==None:
                user = ctx.author
            if user.bot:
                return await ctx.send(await self.translate(ctx.channel,'xp','bot-rank'))
            if ctx.guild != None:
                if not await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'enable_xp'):
                    return await ctx.send(await self.translate(ctx.guild.id,'xp','xp-disabled'))
                xp_used_type = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')
            else:
                xp_used_type = 0
            xp = await self.bdd_get_xp(user.id,None if xp_used_type==0 else ctx.guild.id)
            if xp==None or (isinstance(xp,list) and len(xp)==0):
                if ctx.author==user:
                    return await ctx.send(await self.translate(ctx.channel,'xp','1-no-xp'))
                return await ctx.send(await self.translate(ctx.channel,'xp','2-no-xp'))
            levels_info = None
            xp = xp[0]['xp']
            if xp_used_type==0:
                ranks_nb = await self.bdd_get_nber()
                try:
                    rank = (await self.bdd_get_rank(user.id))['rank']
                except KeyError:
                    rank = "?"
            else:
                ranks_nb = await self.bdd_get_nber(ctx.guild.id)
                try:
                    rank = (await self.bdd_get_rank(user.id,ctx.guild))['rank']
                except KeyError:
                    rank = "?"
            if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).attach_files:
                await self.send_card(ctx,user,xp,rank,ranks_nb,xp_used_type,levels_info)
            elif ctx.channel.permissions_for(ctx.guild.me).embed_links:
                await self.send_embed(ctx,user,xp,rank,ranks_nb,xp_used_type,levels_info)
            else:
                await self.send_txt(ctx,user,xp,rank,ranks_nb,levels_info,xp_used_type)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)
    
    async def send_card(self,ctx:commands.context,user:discord.User,xp,rank,ranks_nb,used_system,levels_info=None):
        try:
            await ctx.send(file=discord.File('../cards/global/{}-{}-{}.{}'.format(user.id,xp,rank,'gif' if user.is_avatar_animated() else 'png')))
        except FileNotFoundError:
            style = await self.bot.cogs['UtilitiesCog'].get_xp_style(user)
            txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
            static = await self.bot.cogs['UtilitiesCog'].get_db_userinfo(['animated_card'],[f'`userID`={user.id}'])
            if user.is_avatar_animated():
                if static!=None:
                    static = not static['animated_card']
                else:
                    static = True
            await ctx.send(file=await self.create_card(user,style,xp,used_system,[rank,ranks_nb],txts,force_static=static,levels_info=levels_info))
            self.bot.log.debug("XP card for user {} ({}xp - style {})".format(user.id,xp,style))
    
    async def send_embed(self,ctx,user,xp,rank,ranks_nb,levels_info,used_system):
        txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
        if levels_info==None:
            levels_info = await self.calc_level(xp,used_system)
        fields = list()
        fields.append({'name':'XP','value':"{}/{}".format(xp,levels_info[1]),'inline':True})
        fields.append({'name':txts[0],'value':levels_info[0],'inline':True})
        fields.append({'name':txts[1],'value':"{}/{}".format(rank,ranks_nb),'inline':True})
        emb = self.bot.cogs['EmbedCog'].Embed(fields=fields,color=self.embed_color).set_author(user)
        await ctx.send(embed=emb.discord_embed())
    
    async def send_txt(self,ctx,user,xp,rank,ranks_nb,levels_info,used_system):
        txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
        if levels_info==None:
            levels_info = await self.calc_level(xp,used_system)
        msg = """__**{}**__
**XP** {}/{}
**{}** {}
**{}** {}/{}""".format(user.name,xp,levels_info[1],txts[0],levels_info[0],txts[1],rank,ranks_nb)
        await ctx.send(msg)


    async def create_top_main(self,ranks,nbr,page,ctx,used_system):
        txt = list()
        i = (page-1)*nbr
        for u in ranks[:nbr]:
            i +=1
            user = self.bot.get_user(u['user'])
            if user==None:
                try:
                    user = await self.bot.fetch_user(u['user'])
                except discord.NotFound:
                    user = await self.translate(ctx.channel,'xp','del-user')
            if isinstance(user,discord.User):
                user_name = await self.bot.cogs['UtilitiesCog'].remove_markdown(user.name.replace('|',''))
                if len(user_name)>18:
                    user_name = user_name[:15]+'...'
            l = await self.calc_level(u['xp'],used_system)
            txt.append('{} • **{} |** `lvl {}` **|** `xp {}`'.format(i,"__"+user_name+"__" if user==ctx.author else user_name,l[0],u['xp']))
        return txt,i

    @commands.command(name='top')
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def top(self,ctx,page:typing.Optional[int]=1,Type:args.LeaderboardType='global'):
        """Get the list of the highest levels
        Each page has 20 users"""
        if ctx.guild!=None:
            if not await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'enable_xp'):
                return await ctx.send(await self.translate(ctx.guild.id,'xp','xp-disabled'))
            xp_system_used = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')
        else:
            xp_system_used = 0
        if xp_system_used==0:
            if Type=='global':
                #ranks = await self.bdd_get_top(20*page)
                ranks = sorted([{'userID':key, 'xp':value[1]} for key,value in self.cache['global'].items()], key=lambda x:x['xp'], reverse=True)
                max_page = ceil(len(self.cache['global'])/20)
            elif Type=='guild':
                ranks = await self.bdd_get_top(10000,guild=ctx.guild)
                max_page = ceil(len(ranks)/20)
        else:
            #ranks = await self.bdd_get_top(20*page,guild=ctx.guild)
            if not ctx.guild.id in self.cache.keys():
                await self.bdd_load_cache(ctx.guild.id)
            ranks = sorted([{'userID':key, 'xp':value[1]} for key,value in self.cache[ctx.guild.id].items()], key=lambda x:x['xp'], reverse=True)
            max_page = ceil(len(ranks)/20)
        if page<1:
            return await ctx.send(await self.translate(ctx.channel,"xp",'low-page'))
        elif page>max_page:
            return await ctx.send(await self.translate(ctx.channel,"xp",'high-page'))
        ranks = ranks[(page-1)*20:]
        ranks = [{'user':x['userID'],'xp':x['xp']} for x in ranks]
        nbr = 20
        txt,i = await self.create_top_main(ranks,nbr,page,ctx,xp_system_used)
        while len("\n".join(txt))>1000 and nbr>0:
            nbr -= 1
            txt,i = await self.create_top_main(ranks,nbr,page,ctx,xp_system_used)
            await asyncio.sleep(0.2)
        f_name = str(await self.translate(ctx.channel,'xp','top-name')).format((page-1)*20+1,i,page,max_page)
        # author
        rank = await self.bdd_get_rank(ctx.author.id,ctx.guild if (Type=='guild' or xp_system_used!=0) else None)
        if len(rank)==0:
            your_rank = {'name':"__"+await self.translate(ctx.channel,"xp","top-your")+"__",'value':await self.translate(ctx.guild,"xp","1-no-xp")}
        else:
            lvl = await self.calc_level(rank['xp'],xp_system_used)
            lvl = lvl[0]
            your_rank = {'name':"__"+await self.translate(ctx.channel,"xp","top-your")+"__", 'value':"**#{} |** `lvl {}` **|** `xp {}`".format(rank['rank'] if 'rank' in rank.keys() else '?',lvl,rank['xp'])}
        # title
        if Type=='guild' or xp_system_used!=0:
            t = await self.translate(ctx.channel,'xp','top-title-2')
        else:
            t = await self.translate(ctx.channel,'xp','top-title-1')
        if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            emb = await self.bot.cogs['EmbedCog'].Embed(title=t,fields=[{'name':f_name,'value':"\n".join(txt)},your_rank],color=self.embed_color,author_icon=self.bot.user.avatar_url_as(format='png')).create_footer(ctx)
            await ctx.send(embed=emb.discord_embed())
        else:
            await ctx.send(f_name+"\n\n"+'\n'.join(txt))


    async def clear_cards(self,all=False):
        """Delete outdated rank cards"""
        files =  os.listdir('../cards/global')
        done = list()
        for f in sorted([f.split('-')+['../cards/global/'+f] for f in files],key=operator.itemgetter(1),reverse=True):
            if f[0] in done:
                os.remove(f[3])
            else:
                done.append(f[0])
    

    @commands.command(name='set_xp')
    @commands.guild_only()
    @commands.check(checks.has_admin)
    async def set_xp(self,ctx,xp:int,*,user:args.user):
        """Set the XP of a user"""
        if user.bot:
            return await ctx.send(await self.translate(ctx.guild.id,'xp','no-bot'))
        if await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')==0:
            return await ctx.send(await self.translate(ctx.guild.id,'xp','change-global-xp'))
        try:
            await self.bdd_set_xp(user.id, xp, Type='set', guild=ctx.guild.id)
            await ctx.send(await self.translate(ctx.guild.id,'xp','change-xp-ok',user=str(user),xp=xp))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,'mc','serv-error'))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
        else:
            self.cache[ctx.guild.id][user.id] = [round(time.time()), xp]

    async def gen_rr_id(self):
        return round(time.time()/2)

    async def rr_add_role(self,guild:int,role:int,level:int):
        """Add a role reward in the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        ID = await self.gen_rr_id()
        query = ("INSERT INTO `roles_rewards` (`ID`,`guild`,`role`,`level`) VALUES ('{i}','{g}','{r}','{l}');".format(i=ID,g=guild,r=role,l=level))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True
    
    async def rr_list_role(self,guild:int,level:int=-1):
        """List role rewards in the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("SELECT * FROM `roles_rewards` WHERE guild={g} ORDER BY level;".format(g=guild)) if level<0 else ("SELECT * FROM `roles_rewards` WHERE guild={g} AND level={l} ORDER BY level;".format(g=guild,l=level))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste
    
    async def rr_remove_role(self,ID:int):
        """Remove a role reward from the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("DELETE FROM `roles_rewards` WHERE `ID`={};".format(ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    @commands.group(name="roles_rewards",aliases=['rr'])
    @commands.guild_only()
    async def rr_main(self,ctx):
        """Manage your roles rewards like a boss"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['rr'])
    
    @rr_main.command(name="add")
    @commands.check(checks.has_manage_guild)
    async def rr_add(self,ctx,level:int,*,role:discord.Role):
        """Add a role reward
        This role will be given to every member who reaches the level"""
        try:
            if role.name == '@everyone':
                raise commands.BadArgument(f'Role "{role.name}" not found')
            l = await self.rr_list_role(ctx.guild.id)
            if len([x for x in l if x['level']==level])>0:
                return await ctx.send(await self.translate(ctx.guild.id,'xp','already-1-rr'))
            max_rr = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'rr_max_number')
            max_rr = self.bot.cogs["ServerCog"].default_opt['rr_max_number'] if max_rr==None else max_rr
            if len(l) >= max_rr:
                return await ctx.send(str(await self.translate(ctx.guild.id,'xp','too-many-rr')).format(len(l)))
            await self.rr_add_role(ctx.guild.id,role.id,level)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            await ctx.send(str(await self.translate(ctx.guild.id,'xp','rr-added')).format(role.name,level))
    
    @rr_main.command(name="list")
    async def rr_list(self,ctx):
        """List every roles rewards of your server"""
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.translate(ctx.guild.id,"fun","no-embed-perm"))
        try:
            l = await self.rr_list_role(ctx.guild.id)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            des = '\n'.join(["• <@&{}> : lvl {}".format(x['role'], x['level']) for x in l])
            max_rr = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'rr_max_number')
            max_rr = self.bot.cogs["ServerCog"].default_opt['rr_max_number'] if max_rr==None else max_rr
            title = str(await self.translate(ctx.guild.id,"xp",'rr_list')).format(len(l),max_rr)
            emb = await self.bot.cogs['EmbedCog'].Embed(title=title,desc=des).update_timestamp().create_footer(ctx)
            await ctx.send(embed=emb.discord_embed())
    
    @rr_main.command(name="remove")
    @commands.check(checks.has_manage_guild)
    async def rr_remove(self,ctx,level:int):
        """Remove a role reward
        When a member reaches this level, no role will be given anymore"""
        try:
            l = await self.rr_list_role(ctx.guild.id,level)
            if len(l)==0:
                return await ctx.send(await self.translate(ctx.guild.id,'xp','no-rr'))
            await self.rr_remove_role(l[0]['ID'])
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            await ctx.send(str(await self.translate(ctx.guild.id,'xp','rr-removed')).format(level))
    
    @rr_main.command(name="reload")
    @commands.check(checks.has_manage_guild)
    @commands.cooldown(1,300,commands.BucketType.guild)
    async def rr_reload(self,ctx):
        """Refresh roles rewards for the whole server"""
        try:
            if not ctx.guild.me.guild_permissions.manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,'modo','cant-mute'))
            c = 0
            rr_list = await self.rr_list_role(ctx.guild.id)
            used_system = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'xp_type')
            xps = [{'user':x['userID'],'xp':x['xp'],'level':(await self.calc_level(x['xp'],used_system))[0]} for x in await self.bdd_get_top(ctx.guild.member_count, ctx.guild if used_system>0 else None)]
            for member in xps:
                m = ctx.guild.get_member(member['user'])
                if m!=None:
                    c += await self.give_rr(m,member['level'],rr_list,remove=True)
            await ctx.send(str(await self.translate(ctx.guild.id,'xp','rr-reload')).format(c,ctx.guild.member_count))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
    


def setup(bot):
    if bot.database_online:
        bot.add_cog(XPCog(bot))
