import discord, sys, traceback, importlib, datetime,random, re
from fcts import utilities
from discord.ext import commands



class UtilitiesCog:
    """This cog has various useful functions for the rest of the bot."""

    def __init__(self,bot):
        self.bot = bot
        self.list_prefixs = dict()
        self.file = "utilities"
        self.config = None
        self.table = 'users'
        
    async def on_ready(self):
        self.config = await self.bot.cogs['ServerCog'].get_bot_infos(self.bot.user.id)

    async def reload(self,liste):
        for m in liste:
            exec("importlib.reload({})".format(m))

    def find_prefix(self,guild):
        if guild==None or not self.bot.database_online:
            return '!'
        if str(guild.id) in self.list_prefixs.keys():
            return self.list_prefixs[str(guild.id)]
        else:
            cnx = self.bot.cogs['ServerCog'].connect()
            cursor = cnx.cursor(dictionary = False)
            cursor.execute("SELECT `prefix` FROM `servers` WHERE `ID`="+str(guild.id))
            liste = list()
            for x in cursor:
                if len(liste)>0:
                    liste.append(x)
            cnx.close()
            if liste == []:
                self.list_prefixs[str(guild.id)] = '!'
                return '!'
            self.list_prefixs[str(guild.id)] = liste[0][0]
            return str(liste[0][0])

    def update_prefix(self,ID,prefix):
        try:
            print("Prefix updated for guild {} : changed to {}".format(ID,prefix))
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
            for i in [commands.RoleConverter,commands.MemberConverter,
                    commands.TextChannelConverter,commands.InviteConverter,
                    commands.UserConverter,commands.VoiceChannelConverter,
                    commands.EmojiConverter,commands.CategoryChannelConverter]:
                try:
                    a = await i().convert(ctx,name)
                    item = a
                    if item != None:
                        return item
                except:
                    if name.isnumeric() and i==commands.MemberConverter:
                        item = await self.bot.get_user_info(int(name))
                        if item != None:
                            return item
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
                    item = await self.bot.get_user_info(int(name))
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
                item = await commands.CategoryConverter().convert(ctx,name)
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

    async def global_check(self,ctx):
        """Check if the guild is a banned guild (aka ignored commands)"""
        if type(ctx)==commands.context:
            ctx = ctx.guild
        elif type(ctx) != discord.guild:
            return True
        if self.config == None:
            self.config = await self.bot.cogs['ServerCog'].get_bot_infos(self.bot.user.id)
        if len(self.config)==0:
            return True
        return not str(ctx.id) in self.config[0]['banned_guilds'].split(";")

    async def create_footer(self,embed,user):
        embed.set_footer(text="Requested by {}".format(user.name), icon_url=user.avatar_url_as(format='png'))
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
        """Remove every mass mention form a text, and add custom emojis"""
        if everyone:
            text = text.replace("@everyone","@"+u"\u200B"+"everyone").replace("@here","@"+u"\u200B"+"here")
        #for x in re.finditer(r'<(a?:[^:]+:)\d+>',text):
        #    text = text.replace(x.group(0),x.group(1))
        #for x in self.bot.emojis: #  (?<!<|a)(:[^:<]+:)
        #    text = text.replace(':'+x.name+':',str(x))
        for x in re.finditer(r'(?<!<|a):([^:<]+):',text):
            try:
                em = await commands.EmojiConverter().convert(ctx,x.group(1))
            except Exception as e:
                print(e)
                continue
            if em != None:
                text = text.replace(x.group(0),"<{}:{}:{}>".format('a' if em.animated else '' , em.name , em.id))
        return text


    async def get_db_userinfo(self,columns=[],criters=["ID>1"],relation="AND",Type=dict):
        """Get every info about a user with the database"""
        await self.bot.wait_until_ready()
        if type(columns)!=list or type(criters)!=list:
            raise ValueError
        cnx = self.bot.cogs['ServerCog'].connect()
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
        cnx.close()
        if len(liste)==1:
            return liste[0]
        elif len(liste)>1:
            return liste
        else:
            return None

    async def get_number_premium(self):
        """Return the number of premium users"""
        try:
            params = await self.get_db_userinfo(criters=['Premium=1'])
            return len(params)
        except Exception as e:
            await self.bot.cogs['Errors'].on_error(e,None)

    async def is_premium(self,user):
        """Check if a user is premium"""
        try:
            parameters = await self.get_db_userinfo(criters=["ID="+str(user.id)],columns=['premium'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e,None)
        if parameters==None:
            return False
        return parameters['premium']

    async def add_check_reaction(self,message):
        try:
            emoji = discord.utils.get(self.bot.emojis, name='greencheck')
            if emoji:
                await message.add_reaction(emoji)
            else:
                await message.add_reaction('\u2705')
        except:
            pass


def setup(bot):
    bot.add_cog(UtilitiesCog(bot))
