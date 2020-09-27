import discord, sys, traceback, importlib, datetime, random, re, asyncio, operator, aiohttp
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
        await self.get_bot_infos()

    async def get_bot_infos(self):
        config_list = await self.bot.cogs['ServerCog'].get_bot_infos(self.bot.user.id)
        if len(config_list)>0:
            self.config = config_list[0]
            self.config.pop('token',None)
            return self.config
        return None

    def find_prefix(self,guild):
        if guild==None or not self.bot.database_online:
            return '!'
        if str(guild.id) in self.list_prefixs.keys():
            return self.list_prefixs[str(guild.id)]
        else:
            cnx = self.bot.cogs['ServerCog'].bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            cursor.execute("SELECT `prefix` FROM `{}` WHERE `ID`={}".format(self.bot.cogs["ServerCog"].table,guild.id))
            liste = list()
            for x in cursor:
                if len(x['prefix'])>0:
                    liste.append(x['prefix'])
            if liste == []:
                self.list_prefixs[str(guild.id)] = '!'
                return '!'
            self.list_prefixs[str(guild.id)] = liste[0]
            return str(liste[0])

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
        if Type is None:
            for i in [commands.MemberConverter,commands.RoleConverter,
                    commands.TextChannelConverter,commands.VoiceChannelConverter,commands.InviteConverter,
                    args.user, commands.EmojiConverter,commands.CategoryChannelConverter,args.snowflake]:
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
        elif Type == 'textchannel':
            try:
                item = await commands.TextChannelConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'invite':
            try:
                item = await commands.InviteConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'voicechannel':
            try:
                item = await commands.VoiceChannelConverter().convert(ctx,name)
            except:
                pass
        elif Type == 'channel':
            try:
                item = await commands.TextChannelConverter().convert(ctx,name)
            except:
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
        elif (Type == 'guild' or Type == "server") and name.isnumeric():
            item = self.bot.get_guild(int(name))
        elif Type in ["snowflake","id"]:
            try:
                item = await args.snowflake().convert(ctx,name)
            except:
                pass
        return item

    async def find_img(self,name):
        return discord.File("../images/{}".format(name))

    async def suppr(self,msg):
        try:
            await msg.delete()
        except:
            await self.print2("Unable to delete message "+str(msg))
            pass

    async def global_check(self,ctx):
        """Do a lot of checks before executing a command (rss loop, banned guilds etc)"""
        #if ctx.bot.cogs['RssCog'].last_update==None or (datetime.datetime.now() - ctx.bot.cogs['RssCog'].last_update).total_seconds() > 20*60:
        #    self.bot.cogs['RssCog'].last_update = datetime.datetime.now()
        #    asyncio.run_coroutine_threadsafe(ctx.bot.cogs['RssCog'].main_loop(),asyncio.get_running_loop())
        if type(ctx)!=commands.context.Context or self.config==None:
            return True
        if await self.bot.cogs['AdminCog'].check_if_admin(ctx):
            return True
        elif len(self.config)==0:
            await self.get_bot_infos()
        if len(self.config)==0 or self.config==None:
            return True
        if ctx.guild != None:
            if str(ctx.guild.id) in self.config['banned_guilds'].split(";"):
                return False
            if str(ctx.author.id) in self.config['banned_users'].split(";"):
                return False
        return True

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
        ch = r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)"
        return re.search(ch,text)

    def sync_check_any_link(self,text):
        ch = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(ch,text)

    def sync_check_discord_invite(self,text):
        ch = r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)"
        return re.search(ch,text)

    async def clear_msg(self,text:str,everyone=False,ctx=None,emojis=True):
        """Remove every mass mention from a text, and add custom emojis"""
        # if everyone:
        #     text = text.replace("@everyone","@"+u"\u200B"+"everyone").replace("@here","@"+u"\u200B"+"here")
        #for x in re.finditer(r'<(a?:[^:]+:)\d+>',text):
        #    text = text.replace(x.group(0),x.group(1))
        #for x in self.bot.emojis: #  (?<!<|a)(:[^:<]+:)
        #    text = text.replace(':'+x.name+':',str(x))
        if emojis:
            for x in re.finditer(r'(?<!<|a):([^:<]+):',text):
                try:
                    if ctx!=None:
                        em = await commands.EmojiConverter().convert(ctx,x.group(1))
                    else:
                        if x.group(1).isnumeric():
                            em = self.bot.get_emoji(int(x.group(1)))
                        else:
                            em = discord.utils.find(lambda e: e.name==x.group(1), self.bot.emojis)
                except:
                #except Exception as e:
                    # print(e)
                    continue
                if em != None:
                    text = text.replace(x.group(0),"<{}:{}:{}>".format('a' if em.animated else '' , em.name , em.id))
        return text


    async def get_db_userinfo(self,columns=[],criters=["userID>1"],relation="AND",Type=dict):
        """Get every info about a user with the database"""
        await self.bot.wait_until_ready()
        if not (isinstance(columns,(list,tuple)) and isinstance(criters,(list,tuple))):
            raise ValueError
        cnx = self.bot.cnx_frm
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
        cursor.close()
        if len(liste)==1:
            return liste[0]
        elif len(liste)>1:
            return liste
        else:
            return None
    
    async def change_db_userinfo(self,userID:int,key:str,value):
        """Change something about a user in the database"""
        try:
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            # if not isinstance(value,(bool,int)):
            #     value = "'"+value+"'"
            # query = ("INSERT INTO `{t}` (`userID`,`{k}`) VALUES ('{u}',{v}) ON DUPLICATE KEY UPDATE {k} = {v};".format(t=self.table,u=userID,k=key,v=value))
            # INSERT INTO `users` (`userID`,`unlocked_blurple`) VALUES ('279568324260528128','True') ON DUPLICATE KEY UPDATE unlocked_blurple = 'True';
            query = "INSERT INTO `{t}` (`userID`,`{k}`) VALUES (%(u)s,%(v)s) ON DUPLICATE KEY UPDATE {k} = %(v)s;".format(t=self.table, k=key)
            cursor.execute(query, { 'u': userID, 'v': value })
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
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['premium']

    async def is_support(self,user):
        """Check if a user is support staff"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['support'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['support']
    
    async def is_partner(self,user):
        """Check if a user is support staff"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['partner'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['partner']

    async def is_contributor(self,user):
        """Check if a user is a contributor"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['contributor'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['contributor']
    
    async def is_translator(self,user):
        """Check if a user is a translator"""
        if self.bot.database_online==False:
            return False
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['translator'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['translator']
    
    async def has_rainbow_card(self,user):
        """Check if a user won the rainbow card"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['unlocked_rainbow'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['unlocked_rainbow']
    
    async def has_blurple_card(self,user,year=19):
        """Check if a user won the blurple card"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=[f'unlocked_blurple_{year}'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            return False
        if (year==20) and not parameters['unlocked_blurple_20'] and self.bot.current_event=="blurple":
            points = await self.get_db_userinfo(["events_points"],["userID="+str(user.id)])
            if points != None and points["events_points"] >= 150:
                await self.change_db_userinfo(user.id,'unlocked_blurple_20',True)
                parameters['unlocked_blurple_20'] = True
        return parameters[f'unlocked_blurple_{year}']
    
    async def has_christmas_card(self,user):
        """Check if a user won the christmas card"""
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['unlocked_christmas'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None:
            parameters = {'unlocked_christmas': False}
        if not parameters['unlocked_christmas'] and self.bot.current_event=="christmas":
            points = await self.get_db_userinfo(["events_points"],["userID="+str(user.id)])
            if points != None and points["events_points"] >= 50:
                await self.change_db_userinfo(user.id,'unlocked_christmas',True)
                parameters['unlocked_christmas'] = True
        return parameters['unlocked_christmas']
    
    async def get_xp_style(self,user):
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)],columns=['xp_style'])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
        if parameters==None or parameters['xp_style']=='':
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
        if not self.bot.database_online:
            return sorted(liste)
        liste2 = []
        if await self.bot.cogs['AdminCog'].check_if_admin(user):
            liste2.append('admin')
        if await self.is_support(user):
            liste2.append('support')
        if await self.is_contributor(user):
            liste2.append('contributor')
        if await self.is_partner(user):
            liste2.append('partner')
        if await self.is_premium(user):
            liste2.append('premium')
        if await self.has_blurple_card(user,19):
            liste.append('blurple19')
        if await self.has_blurple_card(user,20):
            liste.append('blurple20')
        if await self.has_rainbow_card(user):
            liste.append('rainbow')
        if await self.has_christmas_card(user):
            liste.append('christmas')
        return sorted(liste2)+sorted(liste)

    async def get_languages(self,user,limit=0):
        """Get the most used languages of an user
        If limit=0, return every languages"""
        if not self.bot.database_online:
            return ["en"]
        languages = list()
        disp_lang = list()
        available_langs = self.bot.cogs['LangCog'].languages
        for s in self.bot.guilds:
            if user in s.members:
                lang = await self.bot.cogs["ServerCog"].find_staff(s.id,'language')
                if lang==None:
                    lang = available_langs.index(self.bot.cogs['ServerCog'].default_language)
                languages.append(lang)
        for e in range(len(self.bot.cogs['LangCog'].languages)):
            if languages.count(e)>0:
                disp_lang.append((available_langs[e],round(languages.count(e)/len(languages),2)))
        disp_lang.sort(key = operator.itemgetter(1),reverse=True)
        if limit==0:
            return disp_lang
        else:
            return disp_lang[:limit]
    
    async def add_user_eventPoint(self,userID:int,points:int,override:bool=False,check_event:bool=True):
        """Add some events points to a user
        if override is True, then the number of points will override the old score"""
        try:
            if check_event and self.bot.current_event==None:
                return True
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            if override:
                query = ("INSERT INTO `{t}` (`userID`,`events_points`) VALUES ('{u}',{p}) ON DUPLICATE KEY UPDATE events_points = '{p}';".format(t=self.table,u=userID,p=points))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`events_points`) VALUES ('{u}',{p}) ON DUPLICATE KEY UPDATE events_points = events_points + '{p}';".format(t=self.table,u=userID,p=points))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def get_eventsPoints_rank(self,userID:int):
        "Get the ranking of an user"
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = (f"SELECT userID, events_points, FIND_IN_SET( events_points, ( SELECT GROUP_CONCAT( events_points ORDER BY events_points DESC ) FROM {self.table} ) ) AS rank FROM {self.table} WHERE userID = {userID}")
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        if len(liste)==0:
            return None
        return liste[0]
    
    async def get_eventsPoints_nbr(self) -> int:
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = False)
        query = f"SELECT COUNT(*) FROM {self.table} WHERE events_points>0"
        cursor.execute(query)
        result = list(cursor)[0][0]
        cursor.close()
        return result
    

    async def check_votes(self, userid: int) -> list:
        """check if a user voted on any bots list website"""
        votes = list()
        async with aiohttp.ClientSession() as session:
            try: # https://top.gg/bot/486896267788812288
                async with session.get(f'https://top.gg/api/bots/486896267788812288/check?userId={userid}',headers={'Authorization':str(self.bot.dbl_token)}) as r:
                    js = await r.json()
                    if js["voted"]:
                        votes.append(("Discord Bots List","https://top.gg/"))
            except Exception as e:
                await self.bot.get_cog("ErrorsCog").on_error(e,None)
            try: # https://botlist.space/bot/486896267788812288
                headers = {'Authorization': self.bot.others['botlist.space']}
                async with session.get('https://api.botlist.space/v1/bots/486896267788812288/upvotes', headers=headers) as r:
                    js = await r.json()
                    if str(userid) in [x["user"]['id'] for x in js]:
                        votes.append(("botlist.space","https://botlist.space/"))
            except Exception as e:
                await self.bot.get_cog("ErrorsCog").on_error(e,None)
            try: # https://discord.boats/bot/486896267788812288
                headers = {'Authorization': self.bot.others['discordboats']}
                async with session.get(f"https://discord.boats/api/bot/486896267788812288/voted?id={userid}", headers=headers) as r:
                    js = await r.json()
                    if (not js["error"]) and js["voted"]:
                        votes.append(("Discord Boats","https://discord.boats/"))
            except Exception as e:
                await self.bot.get_cog("ErrorsCog").on_error(e,None)
            return votes

def setup(bot):
    bot.add_cog(UtilitiesCog(bot))
