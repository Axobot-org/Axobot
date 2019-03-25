import discord, random, time, asyncio, io, imageio, importlib, re, os, operator, platform
from discord.ext import commands
from math import ceil
from PIL import Image, ImageDraw, ImageFont, ImageTk
from urllib.request import urlopen, Request

from fcts import args
importlib.reload(args)

class XPCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.cache = dict() # {ID : [date, xp]}
        self.levels = [0]
        self.embed_color = discord.Colour(0xffcf50)
        self.table = 'xp_beta' if bot.beta else 'xp'
        self.cooldown = 30
        self.minimal_size = 5
        self.spam_rate = 0.30
        self.xp_per_char = 0.12
        self.max_xp_per_msg = 60
        self.file = 'xp'
        bot.add_listener(self.add_xp,'on_message')
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
        self.table = 'xp_beta' if self.bot.beta else 'xp'
        await self.bdd_load_cache()

    async def add_xp(self,msg):
        """Attribue un certain nombre d'xp à un message"""
        if msg.author.bot or msg.guild==None or not self.bot.xp_enabled:
            return
        if len(self.cache)==0:
            await self.bdd_load_cache()
        if msg.author.id in self.cache.keys():
            if time.time() - self.cache[msg.author.id][0] < self.cooldown:
                return
        s = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'enable_xp')
        if not s:
            return
        content = msg.clean_content
        if len(content)<self.minimal_size or await self.check_spam(content) or await self.check_cmd(msg):
            return
        giv_points = await self.calc_xp(msg)
        if msg.author.id in self.cache.keys():
            prev_points = self.cache[msg.author.id][1]
        else:
            prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points,'add')
        self.cache[msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl = await self.calc_level(self.cache[msg.author.id][1])
        if 1 < (await self.calc_level(prev_points))[0] < new_lvl[0]:
            await self.send_levelup(msg,new_lvl)


    async def send_levelup(self,msg,lvl):
        """Envoie le message de levelup"""
        if not msg.channel.permissions_for(msg.guild.me).send_messages:
            return
        text = await self.bot.cogs['ServerCog'].find_staff(msg.guild.id,'levelup_msg')
        if text==None or len(text)==0:
            text = await self.translate(msg.guild.id,'xp','default_levelup')
        await msg.channel.send(text.format_map(self.bot.SafeDict(user=msg.author,level=lvl[0])))
        

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

    async def calc_level(self,xp):
        """Calcule le niveau correspondant à un nombre d'xp"""
        lvl = ceil(0.05*xp**0.65)
        temp = xp
        while ceil(0.05*temp**0.65)==lvl:
            temp += 1
        return [lvl,temp]

    async def bdd_set_xp(self,userID,points,Type='add'):
        """Ajoute/reset de l'xp à un utilisateur dans la database générale"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            if Type=='add':
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = xp + '{p}';".format(t=self.table,p=points,u=userID))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = '{p}';".format(t=self.table,p=points,u=userID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def bdd_get_xp(self,userID):
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT `xp` FROM `{}` WHERE `userID`={}".format(self.table,userID))
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
    
    async def bdd_get_nber(self):
        """Get the number of ranked users"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = False)
            query = ("SELECT COUNT(*) FROM `{}` WHERE `banned`=0".format(self.table))
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

    async def bdd_load_cache(self):
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            self.bot.log.info("Chargement du cache XP")
            query = ("SELECT `userID`,`xp` FROM `{}` WHERE `banned`=0".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            for l in liste:
                self.cache[l['userID']] = [round(time.time())-60,l['xp']]
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_get_top(self,top:int):
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT * FROM `{}` order by `xp` desc limit {}".format(self.table,top))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
        
    async def bdd_get_rank(self,userID:int):
        """Get the rank of a user"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT `xp`, @curRank := @curRank + 1 AS rank FROM `{}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)

    async def bdd_total_xp(self):
        """Get the total number of earned xp"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT SUM(xp) FROM `{}`".format(self.table))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return round(liste[0]['SUM(xp)'])
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


    async def get_raw_image(self,url,size=282):
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        im = Image.open(io.BytesIO(urlopen(req).read()))
        return im

    async def calc_pos(self,text,font,x,y,align='center'):
        w,h = font.getsize(text)
        if align=='center':
            return x-w/2,y-h/2
        elif align=='right':
            return x-w,y-h/2

    async def create_card(self,user,style,xp,rank=[1,0],txt=['NIVEAU','RANG'],force_static=False):
        """Crée la carte d'xp pour un utilisateur"""
        card = Image.open("../cards/model/{}.png".format(style))
        if not user.is_avatar_animated() or force_static:
            pfp = await self.get_raw_image(user.avatar_url_as(format='png',size=256))
            img = await self.add_overlay(pfp.resize(size=(282,282)),user,card,xp,rank,txt)
            img.save('../cards/global/{}-{}-{}.png'.format(user.id,xp,rank[0]))
            return discord.File('../cards/global/{}-{}-{}.png'.format(user.id,xp,rank[0]))
        else:
            pfp = await self.get_raw_image(user.avatar_url_as(format='gif'))
            images = []
            duration = []
            for i in range(pfp.n_frames):
                pfp.seek(i)
                img = await self.add_overlay(pfp.resize(size=(282,282)),user,card,xp,rank,txt)
                images.append(img)
                duration.append(pfp.info['duration']/1000)
            card.close()
            imageio.mimwrite('../cards/global/{}-{}-{}.gif'.format(user.id,xp,rank[0]), images, format="GIF-PIL", duration=duration, subrectangles=True)
            return discord.File('../cards/global/{}-{}-{}.gif'.format(user.id,xp,rank[0]))

    async def add_overlay(self,pfp,user,card,xp,rank,txt):
        img = Image.new('RGBA', (card.width, card.height), color = (250,250,250,0))
        img.paste(pfp, (20, 29))
        img.paste(card, (0, 0), card)

        if platform.system()=='Darwin':
            verdana_name = 'Verdana.ttf'
        else:
            verdana_name = 'Veranda.ttf'
        name_fnt = ImageFont.truetype('Roboto-Medium.ttf', 40)
        xp_fnt = ImageFont.truetype(verdana_name, 24)
        NIVEAU_fnt = ImageFont.truetype(verdana_name, 42)
        levels_fnt = ImageFont.truetype(verdana_name, 65)
        rank_fnt = ImageFont.truetype(verdana_name,29)
        RANK_fnt = ImageFont.truetype(verdana_name,23)
        colors = {'name':(124, 197, 118),'xp':(124, 197, 118),'NIVEAU':(255, 224, 77),'rank':(105, 157, 206)}

        d = ImageDraw.Draw(img)
        d.text(await self.calc_pos(user.name,name_fnt,610,68), user.name, font=name_fnt, fill=colors['name'])
        levels_info = await self.calc_level(xp)
        temp = '{} / {} xp'.format(xp,levels_info[1])
        d.text((await self.calc_pos(temp,xp_fnt,625,237)), temp, font=xp_fnt, fill=colors['xp'])
        d.text((380,140), txt[0], font=NIVEAU_fnt, fill=colors['NIVEAU'])
        d.text((await self.calc_pos(str(levels_info[0]),levels_fnt,740,160,'right')), str(levels_info[0]), font=levels_fnt, fill=colors['xp'])
        temp = '{x[0]}/{x[1]}'.format(x=rank)
        d.text((await self.calc_pos(txt[1],RANK_fnt,893,147,'center')), txt[1], font=RANK_fnt, fill=colors['rank'])
        d.text((await self.calc_pos(temp,rank_fnt,893,180,'center')), temp, font=rank_fnt, fill=colors['rank'])
        return img


    @commands.command(name='rank')
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1,15,commands.BucketType.user)
    async def rank(self,ctx,*,user:args.user=None):
        """Display a user XP.
        If you don't send any user, I'll display your own XP
        """
        try:
            if user==None:
                user = ctx.author
            xp = await self.bdd_get_xp(user.id)
            if xp==None or len(xp)==0:
                if ctx.author==user:
                    return await ctx.send(await self.translate(ctx.guild,'xp','1-no-xp'))
                return await ctx.send(await self.translate(ctx.guild,'xp','2-no-xp'))
            xp = xp[0]['xp']
            ranks = sorted([(v[1],k) for k,v in self.cache.items()],reverse=True)
            ranks_nb = await self.bdd_get_nber()
            rank = ranks.index((xp,user.id))+1
            if ctx.channel.permissions_for(ctx.guild.me).attach_files:
                await self.send_card(ctx,user,xp,rank,ranks_nb)
            elif ctx.channel.permissions_for(ctx.guild.me).embed_links:
                await self.send_embed(ctx,user,xp,rank,ranks_nb)
            else:
                await self.send_txt(ctx,user,xp,rank,ranks_nb)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_command_error(ctx,e)
    
    async def send_card(self,ctx,user,xp,rank,ranks_nb):
        try:
            await ctx.send(file=discord.File('../cards/global/{}-{}-{}.{}'.format(user.id,xp,rank,'gif' if user.is_avatar_animated() else 'png')))
        except FileNotFoundError:
            style = await self.bot.cogs['UtilitiesCog'].get_xp_style(user)
            txts = [await self.translate(ctx.guild,'xp','card-level'), await self.translate(ctx.guild,'xp','card-rank')]
            await ctx.send(file=await self.create_card(user,style,xp,[rank,ranks_nb],txts))
            self.bot.log.debug("XP card for user {} ({}xp - style {})".format(user.id,xp,style))
    
    async def send_embed(self,ctx,user,xp,rank,ranks_nb):
        txts = [await self.translate(ctx.guild,'xp','card-level'), await self.translate(ctx.guild,'xp','card-rank')]
        levels_info = await self.calc_level(xp)
        fields = list()
        fields.append({'name':'XP','value':"{}/{}".format(xp,levels_info[1]),'inline':True})
        fields.append({'name':txts[0],'value':levels_info[0],'inline':True})
        fields.append({'name':txts[1],'value':"{}/{}".format(rank,ranks_nb),'inline':True})
        emb = self.bot.cogs['EmbedCog'].Embed(fields=fields,color=self.embed_color).set_author(user)
        await ctx.send(embed=emb.discord_embed())
    
    async def send_txt(self,ctx,user,xp,rank,ranks_nb):
        txts = [await self.translate(ctx.guild,'xp','card-level'), await self.translate(ctx.guild,'xp','card-rank')]
        levels_info = await self.calc_level(xp)
        msg = """__**{}**__
**XP** {}/{}
**{}** {}
**{}** {}/{}""".format(user.name,xp,levels_info[1],txts[0],levels_info[0],txts[1],rank,ranks_nb)
        await ctx.send(msg)



    @commands.command(name='top')
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def top(self,ctx,page:int=1):
        """Get the list of the highest levels
        Each page has 20 users"""
        max_page = ceil(len(self.cache)/20)
        if page<1:
            return await ctx.send(await self.translate(ctx.guild,"xp",'low-page'))
        elif page>max_page:
            return await ctx.send(await self.translate(ctx.guild,"xp",'high-page'))
        ranks = await self.bdd_get_top(20*page)
        ranks = ranks[(page-1)*20:]
        txt = list()
        i = (page-1)*20
        for u in ranks:
            i +=1
            user = self.bot.get_user(u['userID'])
            if user==None:
                try:
                    user = await self.bot.fetch_user(u['userID'])
                except discord.NotFound:
                    user = await self.translate(ctx.guild,'xp','del-user')
            if isinstance(user,discord.User):
                user = await self.bot.cogs['UtilitiesCog'].remove_markdown(user.name.replace('|',''))
                if len(user)>18:
                    user = user[:15]+'...'
            l = await self.calc_level(u['xp'])
            txt.append('{} • **{} |** `lvl {}` **|** `xp {}`'.format(i,user,l[0],u['xp']))
        f_name = str(await self.translate(ctx.guild,'xp','top-name')).format((page-1)*20+1,i,page,max_page)
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            emb = self.bot.cogs['EmbedCog'].Embed(title=await self.translate(ctx.guild,'xp','top-title-1'),fields=[{'name':f_name,'value':"\n".join(txt)}],color=self.embed_color,author_icon=self.bot.user.avatar_url_as(format='png')).create_footer(ctx.author)
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



def setup(bot):
    bot.add_cog(XPCog(bot))