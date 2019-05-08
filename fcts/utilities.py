import discord, sys, traceback, importlib, datetime, random, re, asyncio, operator
from fcts import args
from discord.ext import commands

importlib.reload(args)


class UtilitiesCog(commands.Cog):
    """This cog has various useful functions for the rest of the bot."""

    def __init__(self,bot):
        self.bot = bot
        self.list_prefixs = dict()
        self.file = "utilities"
        self.config = {}
        self.table = 'users'
        self.new_pp = False

    @commands.Cog.listener()
    async def on_ready(self):
        await self.reload()

    async def reload(self):
        self.config = (await self.bot.cogs['ServerCog'].get_bot_infos(self.bot.user.id))[0]
        return self.config

    def find_prefix(self,guild):
        if guild==None or not self.bot.database_online:
            return '!'
        if str(guild.id) in self.list_prefixs.keys():
            return self.list_prefixs[str(guild.id)]
        else:
            cnx = self.bot.cogs['ServerCog'].bot.cnx
            cursor = cnx.cursor(dictionary = True)
            cursor.execute("SELECT `prefix` FROM `{}` WHERE `ID`={}".format(self.bot.cogs["ServerCog"].table,guild.id))
            liste = list()
            for x in cursor:
                if len(x['prefix'])>0:
                    liste.append(x['prefix'])
            if liste == []:
                self.list_prefixs[str(guild.id)] = '!'
                return '!'
            self.list_prefixs[str(guild.id)] = liste[0][0]
            return str(liste[0][0])

    def update_prefix(self,ID,prefix):
        try:
            self.bot.log.debug("Prefix updated for guild {} : changed to {}".format(ID,prefix))
        except:
            pass
        self.list_prefixs[str(ID)] = prefix

    async def print2(self,text):
        try:
            print(text)
        except UnicodeEncodeError:
            text = await self.anti_code(str(text))
            try:
                print(text)
            except UnicodeEncodeError:
                print(text.encode("ascii","ignore").decode("ascii"))

    async def anti_code(self,text):
        if type(text)==str:
            for i,j in [('é','e'),('è','e'),('à','a'),('î','i'),('ê','e'),('ï','i'),('ü','u'),('É','e'),('ë','e'),('–','-'),('“','"'),('’',"'"),('û','u'),('°','°'),('Ç','C'),('ç','c')]:
                text=text.replace(i,j)
            return text
        elif type(text)==list:
            text2=[]
            for i,j in [('é','e'),('è','e'),('à','a'),('î','i'),('ê','e'),('ï','i'),('ü','u'),('É','e'),('ë','e'),('–','-'),('“','"'),('’',"'"),('û','u'),('°','°'),('Ç','C'),('ç','c')]:
                for k in text:
                    text2.append(k.replace(i,j))
                    return text2


    async def find_everything(self,ctx,name,Type=None):
        item = None
        if type(Type) == str:
            Type = Type.lower()
        if Type == None:
            for i in [commands.MemberConverter,commands.RoleConverter,
                    commands.TextChannelConverter,commands.InviteConverter,
                    args.user,commands.VoiceChannelConverter,
                    commands.EmojiConverter,commands.CategoryChannelConverter]:
                try:
                    a = await i().convert(ctx,name)
                    item = a
                    if item != None:
                        return item
                except:
                    pass
            return None
        elif Type == 'member':
            try:
                item = await commands.MemberConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'role':
            try:
                item = await commands.RoleConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'user':
            try:
                item = await commands.UserConverter().convert(ctx,name)
            except:
                if name.isnumeric():
                    item = await self.bot.fetch_user(int(name))
        elif Type == 'textchannel' or Type == "channel":
            try:
                item = await commands.TextChannelConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'invite':
            try:
                item = await commands.InviteConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'voicechannel' or Type == 'channel':
            try:
                item = await commands.VoiceChannelConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'emoji':
            try:
                item = await commands.EmojiConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'category':
            try:
                item = await commands.CategoryChannelConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'guild' and name.isnumeric():
            item = self.bot.get_guild(int(name))
        return item

    async def find_img(self,name):
        return discord.File("../images/{}".format(name))

    async def suppr(self,msg):
        try:
            await msg.delete()
        except:
            await self.print2("Unable to delete message "+str(msg))
            pass

    async def get_bot_infos(self):
        if self.config == None:
            self.config = (await self.bot.cogs['ServerCog'].get_bot_infos(self.bot.user.id))[0]
        return self.config

    async def global_check(self,ctx):
        """Do a lot of checks before executing a command (rss loop, banned guilds etc)"""
        if ctx.bot.cogs['RssCog'].last_update==None or (datetime.datetime.now() - ctx.bot.cogs['RssCog'].last_update).total_seconds() > 20*60:
            self.bot.cogs['RssCog'].last_update = datetime.datetime.now()
            asyncio.run_coroutine_threadsafe(ctx.bot.cogs['RssCog'].main_loop(),asyncio.get_running_loop())
        if type(ctx)!=commands.context.Context:
            return True
        if await self.bot.cogs['AdminCog'].check_if_admin(ctx):
            return True
        if len(self.config)==0:
            self.config = await self.get_bot_infos()
        if len(self.config)==0:
            return True
        if ctx.guild != None:
            if str(ctx.guild.id) in self.config['banned_guilds'].split(";"):
                return False
            if str(ctx.author.id) in self.config['banned_users'].split(";"):
                return False
        return True

    async def create_footer(self,embed,user):
        embed.set_footer(text="Requested by {}".format(user.name), icon_url=str(user.avatar_url_as(format='png')))
        return embed

    async def get_online_number(self,members):
        online = 0
        for m in members:
            if str(m.status) in ["online","idle"]:
                online += 1
        return online

    async def get_bots_number(self,members):
        return len([x for x in members if x.bot])

    async def set_find(self,set,name):
        for x in set:
            if x.name==name:
                return x

    async def check_any_link(self,text):
        ch = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(ch,text)

    async def check_discord_invite(self,text):
        ch = r"((?:discord\.gg|discordapp.com/invite|discord.me)/.+)"
        return re.search(ch,text)

    def sync_check_any_link(self,text):
        ch = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(ch,text)

    def sync_check_discord_invite(self,text):
        ch = r"((?:discord\.gg|discordapp.com/invite|discord.me)/.+)"
        return re.search(ch,text)

    async def clear_msg(self,text,everyone=True,ctx=None):
        """Remove every mass mention from a text, and add custom emojis"""
        if everyone:
            text = text.replace("@everyone","@"+u"\u200B"+"everyone").replace("@here","@"+u"\u200B"+"here")
        #for x in re.finditer(r'<(a?:[^:]+:)\d+>',text):
        #    text = text.replace(x.group(0),x.group(1))
        #for x in self.bot.emojis: #  (?<!<|a)(:[^:<]+:)
        #    text = text.replace(':'+x.name+':',str(x))
        for x in re.finditer(r'(?<!<|a):([^:<]+):',text):
            try:
                if ctx!=None:
                    em = await commands.EmojiConverter().convert(ctx,x.group(1))
                else:
                    if x.group(1).isnumeric():
                        em = self.bot.get_emoji(int(x.group(1)))
                    else:
                        em = discord.utils.find(lambda e: e.name==x.group(1), self.bot.emojis)

            except Exception as e:
                # print(e)
                continue
            if em != None:
                text = text.replace(x.group(0),"<{}:{}:{}>".format('a' if em.animated else '' , em.name , em.id))
        return text


    async def get_db_userinfo(self,columns=[],criters=["userID>1"],relation="AND",Type=dict):
        """Get every info about a user with the database"""
        await self.bot.wait_until_ready()
        if type(columns)!=list or type(criters)!=list:
            raise ValueError
        cnx = self.bot.cnx
        cursor = cnx.cursor(dictionary = True)
        if columns == []:
            cl = "*"
        else:
            cl = "`"+"`,`".join(columns)+"`"
        relation = " "+relation+" "
        query = ("SELECT {} FROM `{}` WHERE {}".format(cl,self.table,relation.join(criters)))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        if len(liste)==1:
            return liste[0]
        elif len(liste)>1:
            return liste
        else:
            return None
    
    async def change_db_userinfo(self,userID:int,key:str,value):
        """Change something about a user in the database"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            if not isinstance(value,(bool,int)):
                value = "'"+value+"'"
            query = ("INSERT INTO `{t}` (`userID`,`{k}`) VALUES ('{u}',{v}) ON DUPLICATE KEY UPDATE {k} = {v};".format(t=self.table,u=userID,k=key,v=value))
            # INSERT INTO `users` (`userID`,`unlocked_blurple`) VALUES ('279568324260528128','True') ON DUPLICATE KEY UPDATE unlocked_blurple = 'True';
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False

    async def get_number_premium(self):
        """Return the number of premium users"""
        try:
            params = await self.get_db_userinfo(criters=['Premium=1'])
            return len(params)
        except Exception as e:
            await self.bot.cogs['Errors'].on_error(e,None)

    async def is_premium(self,user):
        """Check if a user is premium"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['premium'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['premium']

    async def is_support(self,user):
        """Check if a user is support staff"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['support'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['support']

    async def is_contributor(self,user):
        """Check if a user is a contributor"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['contributor'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['contributor']
    
    async def has_rainbow_card(self,user):
        """Check if a user won the rainbow card"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['unlocked_rainbow'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['unlocked_rainbow']
    
    async def has_blurple_card(self,user):
        """Check if a user won the blurple card"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['unlocked_blurple'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['unlocked_blurple']
    
    async def get_xp_style(self,user):
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['xp_style'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None or len(parameters)==0:
            return 'dark'
        return parameters['xp_style']

    async def add_check_reaction(self,message):
        try:
            emoji = discord.utils.get(self.bot.emojis, name='greencheck')
            if emoji:
                await message.add_reaction(emoji)
            else:
                await message.add_reaction('\u2705')
        except discord.Forbidden:
            await message.channel.send(":ok:")
        except:
            pass

    async def remove_markdown(self,txt):
        for x in ('||','*','__','~~'):
            txt = txt.replace(x,'')
        return txt

    async def allowed_card_styles(self,user):
        """Retourne la liste des styles autorisées pour la carte d'xp de cet utilisateur"""
        liste = ['blue','dark','green','grey','orange','purple','red','turquoise','yellow']
        liste2 = []
        if await self.is_support(user):
            liste2.append('support')
        if await self.is_contributor(user):
            liste2.append('contributor')
        if await self.is_premium(user):
            liste2.append('premium')
        if await self.bot.cogs['AdminCog'].check_if_admin(user):
            liste2.append('admin')
        if await self.has_rainbow_card(user):
            liste.append('rainbow')
        if await self.has_blurple_card(user):
            liste.append('blurple')
        return sorted(liste2)+sorted(liste)

    async def get_languages(self,user,limit=0):
        """Get the most used languages of an user
        If limit=0, return every languages"""
        languages = list()
        disp_lang = list()
        for s in self.bot.guilds:
            if user in s.members:
                lang = await self.bot.cogs["ServerCog"].find_staff(s.id,'language')
                if lang==None:
                    lang = 0
                languages.append(lang)
        for e in range(len(self.bot.cogs['LangCog'].languages)):
            if languages.count(e)>0:
                disp_lang.append((self.bot.cogs['LangCog'].languages[e],round(languages.count(e)/len(languages),2)))
        disp_lang.sort(key = operator.itemgetter(1))
        if limit==0:
            return disp_lang
        else:
            return disp_lang[:limit]


def setup(bot):
    bot.add_cog(UtilitiesCog(bot))
