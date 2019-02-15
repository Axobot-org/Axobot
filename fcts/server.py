#!/usr/bin/env python
#coding=utf-8

import mysql.connector, time, datetime, emoji
import discord
from discord.ext import commands
from fcts import cryptage

roles_options = ["clear","slowmode","mute","kick","ban","warn","say","gived_roles"]
bool_options = ["save_roles","enable_xp","anti_caps_lock","enable_fun","help_in_dm"]
textchan_options = ["hunter","welcome_channel","bot_news","poll_channels","modlogs_channel"]
vocchan_options = ["membercounter"]
text_options = ["welcome","leave"]
prefix_options = ['prefix']
emoji_option = ['vote_emojis']
numb_options = []
raid_options = ["anti_raid"]

class ServerCog:
    """"Cog in charge of all the bot configuration management for your server. As soon as an option is searched, modified or deleted, this cog will handle the operations."""

    def __init__(self,bot):
        self.bot = bot
        self.default_language = 'fr'
        self.embed_color = discord.Colour(0x3fb9ef)
        self.log_color = 1793969
        self.file = "server"
        self.raids_levels = ["None","Smooth","Careful","High","(╯°□°）╯︵ ┻━┻"]
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
        if bot.user != None:
            self.table = 'servers' if bot.user.id==486896267788812288 else 'servers_beta'
        self.default_opt = {"language":0,
               "clear":"",
               "slowmode":"",
               "mute":"",
               "kick":"",
               "ban":"",
               "say":"",
               "hunter":"",
               "welcome_channel":'',
               "welcome":"",
               "leave":"",
               "gived_roles":"",
               "bot_news":'',
               "save_roles":0,
               "poll_channels":"",
               "modlogs_channel":"",
               "enable_xp":1,
               "anti_caps_lock":1,
               "enable_fun":1,
               "prefix":'!',
               "membercounter":"",
               "anti_raid":1,
               "vote_emojis":":thumbsup:;:thumbsdown:;",
               "help_in_dm":0}
        self.optionsList = ["ID","Created at","prefix","language","clear","slowmode","mute","kick","ban","warn","say","hunter","welcome_channel","welcome","leave","gived_roles","bot_news","save_roles","poll_channels","modlogs_channel","enable_xp","anti_caps_lock","enable_fun","membercounter","anti_raid","vote_emojis","help_in_dm"]

    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
        self.table = 'servers' if self.bot.user.id==486896267788812288 else 'servers_beta'


    async def get_bot_infos(self,botID):
        """return every options of a server"""
        if not self.bot.database_online:
            return list()
        cnx = self.connect()
        cursor = cnx.cursor(dictionary=True)
        query = ("SELECT * FROM `bot_infos` WHERE `ID`={}".format(botID))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cnx.close()
        return liste

    async def get_languages(self,ignored_guilds):
        """Return percentages of languages"""
        if not self.bot.database_online:
            return list()
        cnx = self.connect()
        cursor = cnx.cursor(dictionary=True)
        query = ("SELECT `language`,`ID` FROM `{}` WHERE 1".format(self.table))
        cursor.execute(query)
        liste,langs = list(), list()
        for x in cursor:
            if x['ID'] not in ignored_guilds:
                liste.append(x['language'])
        for e,l in enumerate(self.bot.cogs['LangCog'].languages):
            langs.append((l,liste.count(e)))
        cnx.close()
        return langs


    def connect(self):
        return mysql.connector.connect(user=self.bot.database_keys['user'],password=self.bot.database_keys['password'],host=self.bot.database_keys['host'],database=self.bot.database_keys['database'])

    async def staff_finder(self,user,option):
        """Check is user is part of a staff"""
        if option not in roles_options:
            raise TypeError
        if await self.bot.cogs['AdminCog'].check_if_admin(user) or user==user.guild.owner:
            return True
        if not self.bot.database_online:
            return False
        staff = str(await self.find_staff(user.guild.id,option)).split(";")
        for r in user.roles:
            if str(r.id) in staff:
                return True
        return False

    async def find_staff(self,ID,name,channel=None):
        """return the value of an option
        Return None if this option doesn't exist or if no value has been set"""
        if type(ID)==discord.Guild:
            ID = ID.id
        elif type(ID)==None or not self.bot.database_online:
            return None
        l = await self.get_server([name],criters=["ID="+str(ID)],ID=ID,channel=channel,Type=list)
        if l == []:
            return None
        else:
            return l[0][0]
        
    async def get_server(self,columns=[],criters=["ID>1"],relation="AND",ID=None,channel=None,Type=dict):
        """return every options of a server"""
        await self.bot.wait_until_ready()
        if type(columns)!=list or type(criters)!=list:
            raise ValueError
        cnx = self.connect()
        cursor = cnx.cursor(dictionary = (Type==dict))
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
        return liste    

    async def modify_server(self,ID,values=[()],channel=None):
        if type(values)!=list:
            raise ValueError
        v = list()
        cnx = self.connect()
        cursor = cnx.cursor()
        for x in values:
            if type(x) == bool:
                v.append("`{x[0]}`={x[1]}".format(x=x))
            else:
                v.append("""`{x[0]}`="{x[1]}" """.format(x=x))
        query = ("UPDATE `{t}` SET {v} WHERE `ID`='{id}'".format(t=self.table,v=",".join(v),id=ID))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True

    async def delete_option(self,ID,opt,channel=None):
        """reset an option"""
        if opt not in self.default_opt.keys():
            raise ValueError
        value = self.default_opt[opt]
        if opt == 'language':
            await self.bot.cogs['LangCog'].change_cache(ID,value)
        elif opt == 'prefix':
            self.bot.cogs['UtilitiesCog'].update_prefix(ID,value)
        return await self.modify_server(ID,values=[(opt,value)],channel=channel)

    async def add_server(self,ID):
        """add a new server to the db"""
        if type(ID) == str:
            if not ID.isnumeric():
                raise ValueError
        cnx = self.connect()
        cursor = cnx.cursor()
        query = ("INSERT INTO `{}` (`ID`) VALUES ('{}')".format(self.table,ID))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True

    async def is_server_exist(self,ID,channel=None):
        """Check if a server is already in the db"""
        i = await self.find_staff(ID,"ID")
        if i == None:
            if channel != None:
                await channel.send(await self.translate(channel.guild.id,"server","new_server"))
            # await self.bot.get_user(279568324260528128).send("Le serveur n°{} vient d'être ajouté dans la base de donnée".format(ID))
            g = self.bot.get_guild(ID)
            emb = self.bot.cogs["EmbedCog"].Embed(desc="New server in the database :tada: `{}` ({})".format(g.name,g.id),color=self.log_color).update_timestamp()
            await self.bot.cogs["EmbedCog"].send([emb])
            return await self.add_server(ID)
        return True

    async def delete_server(self,ID):
        """remove a server from the db"""
        if type(ID)!=int:
            raise ValueError
        cnx = self.connect()
        cursor = cnx.cursor()
        query = ("DELETE FROM `{}` WHERE `ID`='{}'".format(self.table,ID))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True

                 

    @commands.group(name='config')
    @commands.guild_only()
    @commands.cooldown(1,2,commands.BucketType.guild)
    async def sconfig_main(self,ctx):
        """Function for setting the bot on a server"""
        if ctx.bot.database_online:
            await self.is_server_exist(ctx.guild.id,ctx.channel)
        if ctx.invoked_subcommand is None:
            msg = await self.translate(ctx.guild,"server","config-help")
            await ctx.send(msg.format(ctx.guild.owner.name))

    @sconfig_main.command(name="del")
    async def sconfig_del(self,ctx,option):
        """Reset an option to zero"""
        if not (ctx.channel.permissions_for(ctx.author).administrator or await self.bot.cogs["AdminCog"].check_if_admin(ctx)):
            return
        if not ctx.bot.database_online:
            return await ctx.send(await self.translate(ctx.guild.id,"cases","no_database"))
        await self.sconfig_del2(ctx,option)
    
    @sconfig_main.command(name="change")
    async def sconfig_change(self,ctx,option,*,value):
        """Allows you to modify an option"""
        if not (ctx.channel.permissions_for(ctx.author).administrator or await self.bot.cogs["AdminCog"].check_if_admin(ctx)):
            return
        if not ctx.bot.database_online:
            return await ctx.send(await self.translate(ctx.guild.id,"cases","no_database"))
        if value=='del':
            await self.sconfig_del2(ctx,option)
            return
        try:
            if option in roles_options:
                await self.conf_roles(ctx,option,value)
            elif option in bool_options:
                await self.conf_bool(ctx,option,value)
            elif option in textchan_options:
                await self.conf_textchan(ctx,option,value)
            elif option in text_options:
                await self.conf_text(ctx,option,value)
            elif option in numb_options:
                await self.conf_numb(ctx,option,value)
            elif option in vocchan_options:
                await self.conf_vocal(ctx,option,value)
            elif option == "language":
                await self.conf_lang(ctx,option,value)
            elif option in prefix_options:
                await self.conf_prefix(ctx,option,value)
            elif option in raid_options:
                await self.conf_raid(ctx,option,value)
            elif option in emoji_option:
                await self.conf_emoji(ctx,option,value)
            else:
                await ctx.send(await self.translate(ctx.guild.id,"server","change-0"))
                return
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            await ctx.send(await self.translate(ctx.guild.id,"server","change-1"))
    
    async def sconfig_del2(self,ctx,option):
        try:
            t = await self.delete_option(ctx.guild.id,option,channel=ctx.channel)
            if t:
                msg = await self.translate(ctx.guild.id,"server","change-2")
            else:
                msg = await self.translate(ctx.guild.id,"server","change-1")
            await ctx.send(msg.format(option))
            emb = self.bot.cogs["EmbedCog"].Embed(desc="Reset option in server `{}`: {}".format(ctx.guild.id,option),color=self.log_color).update_timestamp().set_author(ctx.guild.me)
            await self.bot.cogs["EmbedCog"].send([emb])
        except ValueError:
            await ctx.send(await self.translate(ctx.guild.id,"server","change-0"))
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            await ctx.send(await self.translate(ctx.guild.id,"server","change-1"))

    async def send_embed(self,guild,option,value):
        emb = self.bot.cogs["EmbedCog"].Embed(desc="Changed option in server `{}`: {} = {}".format(guild.id,option,value),color=self.log_color).update_timestamp().set_author(guild.me)
        await self.bot.cogs["EmbedCog"].send([emb])


    async def conf_roles(self,ctx,option,value):
        if value == "scret-desc":
            roles = await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
            return await self.form_roles(ctx.guild,roles)
        else:
            roles = value.split(",")
            liste = list()
            liste2 = list()
            for role in roles:
                role = role.strip()
                try:
                    r = await commands.RoleConverter().convert(ctx,role)
                except commands.errors.BadArgument:
                    msg = await self.translate(ctx.guild.id,"server","change-3")
                    await ctx.send(msg.format(role))
                    return
                if str(r.id) in liste:
                    continue
                liste.append(str(r.id))
                liste2.append(r.name)
            await self.modify_server(ctx.guild.id,values=[(option,";".join(liste))],channel=ctx.channel)
            msg = await self.translate(ctx.guild.id,"server","change-role")
            await ctx.send(msg.format(option,", ".join(liste2)))
            await self.send_embed(ctx.guild,option,value)

    async def form_roles(self,guild,roles,ext=False):
        if len(roles) == 0:
            return "Ø"
        roles = roles.split(";")
        g_roles = list()
        for r in roles:
            g_role = discord.utils.get(guild.roles, id=int(r))
            if g_role == None:
                g_roles.append("<unfindable role>")
            elif ext:
                g_roles.append("@"+g_role.name)
            else:
                g_roles.append(g_role.mention)
        return g_roles
        
    async def conf_bool(self,ctx,option,value):
        if value == "scret-desc":
            v = await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
            return await self.form_bool(v)
        else:
            if value.lower() in ["true","vrai","1","oui","yes","activé"]:
                value = True
                v = 1
            elif value.lower() in ["false","faux","non","no","désactivé","wrong"]:
                value = False
                v = 0
            else:
                msg = await self.translate(ctx.guild.id,"server","change-4")
                await ctx.send(msg.format(option))
                return
            if option == "enable_fun":
                await self.bot.cogs["FunCog"].cache_update(ctx.guild.id,v)
            await self.modify_server(ctx.guild.id,values=[(option,v)],channel=ctx.channel)
            msg = await self.translate(ctx.guild.id,"server","change-bool")
            await ctx.send(msg.format(option,value))
            await self.send_embed(ctx.guild,option,value)
    
    async def form_bool(self,boolean):
        if boolean == 1:
            v = True
        else:
            v = False
        return v
    
    async def conf_textchan(self,ctx,option,value):
        if value == "scret-desc":
            chans = await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
            return await self.form_textchan(ctx.guild,chans)
        else:
            chans = value.split(",")
            liste = list()
            liste2 = list()
            for chan in chans:
                chan = chan.strip()
                if len(chan)==0:
                    continue
                try:
                    c = await commands.TextChannelConverter().convert(ctx,chan)
                except commands.errors.BadArgument:
                    msg = await self.translate(ctx.guild.id,"server","change-5")
                    await ctx.send(msg.format(chan))
                    return
                if str(c.id) in liste:
                    continue
                liste.append(str(c.id))
                liste2.append(c.mention)
            await self.modify_server(ctx.guild.id,values=[(option,";".join(liste))],channel=ctx.channel)
            msg = await self.translate(ctx.guild.id,"server","change-textchan")
            await ctx.send(msg.format(option,", ".join(liste2)))
            await self.send_embed(ctx.guild,option,value)

    async def form_textchan(self,guild,chans,ext=False):
        if len(chans) == 0:
            return "Ø"
        chans = chans.split(";")
        g_chans = list()
        for r in chans:
            g_chan = discord.utils.get(guild.text_channels, id=int(r))
            if g_chan == None:
                g_chans.append("<unfindable channel>")
            elif ext:
                g_chans.append("#"+g_chan.name)
            else:
                g_chans.append(g_chan.mention)
        return g_chans

    async def conf_emoji(self,ctx,option,value):
        if value == "scret-desc":
            emojis = await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
            return await self.form_emoji(emojis)
        else:
            emojis = value.split(",")
            liste = list()
            liste2 = list()
            for e in emojis:
                e = e.strip()
                if len(e)==0:
                    continue
                try:
                    e = await commands.EmojiConverter().convert(ctx,e)
                except commands.errors.BadArgument:
                    if e not in self.bot.cogs["EmojiCog"].unicode_list:
                        msg = await self.translate(ctx.guild.id,"server","change-9")
                        await ctx.send(msg.format(e))
                        return
                    if emoji.demojize(e) not in liste:
                        liste.append(emoji.demojize(e))
                        liste2.append(e)
                else:
                    if str(e.id) not in liste:
                        liste.append(str(e.id))
                        liste2.append("<:{}:{}>".format(e.name,e.id))
            await self.modify_server(ctx.guild.id,values=[(option,";".join(liste))],channel=ctx.channel)
            msg = await self.translate(ctx.guild.id,"server","change-emojis")
            await ctx.send(msg.format(option,", ".join(liste2)))
            await self.send_embed(ctx.guild,option,value)

    async def form_emoji(self,emojis):
        if len(emojis) == 0:
            return [":thumbsup:", ":thumbsdown:"]
        emojis = emojis.split(";")
        l_em = list()
        for r in emojis:
            if r.isnumeric():
                d_em = discord.utils.get(self.bot.emojis, id=int(r))
                if d_em == None:
                    l_em.append("<unfindable emoji>")
                else:
                    l_em.append("<:{}:{}>".format(d_em.name,d_em.id))
            else:
                l_em.append(emoji.emojize(r, use_aliases=True))
        return l_em

    async def conf_vocal(self,ctx,option,value):
        if value == "scret-desc":
            chans = await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
            return await self.form_vocal(ctx.guild,chans)
        else:
            chans = value.split(",")
            liste = list()
            liste2 = list()
            for chan in chans:
                chan = chan.strip()
                try:
                    c = await commands.VoiceChannelConverter().convert(ctx,chan)
                except commands.errors.BadArgument:
                    msg = await self.translate(ctx.guild.id,"server","change-5")
                    await ctx.send(msg.format(chan))
                    return
                if str(c.id) in liste:
                    continue
                liste.append(str(c.id))
                liste2.append(c.mention)
            await self.modify_server(ctx.guild.id,values=[(option,";".join(liste))],channel=ctx.channel)
            msg = await self.translate(ctx.guild.id,"server","change-textchan")
            await ctx.send(msg.format(option,", ".join(liste2)))
            await self.send_embed(ctx.guild,option,value)

    async def form_vocal(self,guild,chans):
        if len(chans) == 0:
            return "Ø"
        chans = chans.split(";")
        g_chans = list()
        for r in chans:
            g_chan = discord.utils.get(guild.voice_channels, id=int(r))
            if g_chan == None:
                g_chans.append("<unfindable channel>")
            else:
                g_chans.append(g_chan.mention)
        return g_chans

    async def conf_text(self,ctx,option,value):
        if value == "scret-desc":
            text = await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
            return await self.form_text(text)
        else:
            await self.modify_server(ctx.guild.id,values=[(option,value.replace('"','\"'))],channel=ctx.channel)
            msg = await self.translate(ctx.guild.id,"server","change-text")
            await ctx.send(msg.format(option,value))
            await self.send_embed(ctx.guild,option,value)

    async def form_text(self,text):
        if len(text) == 0:
            text = "Ø"
        else:
            text = "```\n"+text+"\```"
        return text

    async def conf_prefix(self,ctx,option,value):
        if value == "scret-desc":
            text = await self.find_staff(ctx.guild.id,'prefix',channel=ctx.channel)
            return await self.form_prefix(text)
        else:
            if len(value)>5:
                await ctx.send(await self.translate(ctx.guild.id,"server","change-prefix-1"))
                return
            try:
                await self.modify_server(ctx.guild.id,values=[('prefix',value)],channel=ctx.channel)
            except:
                await ctx.send(await self.translate(ctx.guild.id,"server","wrong-prefix"))
                return
            self.bot.cogs['UtilitiesCog'].update_prefix(ctx.guild.id,value)
            msg = await self.translate(ctx.guild.id,"server","change-prefix")
            await ctx.send(msg.format(value))
            await self.send_embed(ctx.guild,option,value)

    async def form_prefix(self,text):
        if len(text) == 0:
            text = "!"
        return '`'+text+'`'

    async def conf_numb(self,ctx,option,value):
        if value == "scret-desc":
            return await self.find_staff(ctx.guild.id,option,channel=ctx.channel)
        else:
            if value.isnumeric():
                value = eval(value)
                await self.send_embed(ctx.guild,option,value)
            else:
                msg = await self.translate(ctx.guild.id,"server","change-6")
                await ctx.send(msg.format(option))

    async def conf_lang(self,ctx,option,value):
        if value == "scret-desc":
            if type(ctx) == commands.Context:
                guild = ctx.guild.id
            elif type(ctx) == str:
                if ctx.isnumeric():
                    guild = int(ctx)
            elif type(ctx) == int:
                guild = ctx
            else:
                return self.default_language
            v = await self.find_staff(guild,option,channel=None)
            return await self.form_lang(v)
        else:
            languages = self.bot.cogs["LangCog"].languages
            if value in languages:
                v = languages.index(value)
                await self.modify_server(ctx.guild.id,values=[(option,v)],channel=ctx.channel)
                await self.bot.cogs['LangCog'].change_cache(ctx.guild.id,value)
                msg = await self.translate(ctx.guild.id,"server","change-lang")
                await ctx.send(msg.format(value))
                await self.send_embed(ctx.guild,option,value)
            else:
                msg = await self.translate(ctx.guild.id,"server","change-7")
                await ctx.send(msg.format(", ".join(languages)))

    async def form_lang(self,value):
        if value == None:
            return self.default_language
        else:
            return self.bot.cogs["LangCog"].languages[value]
    
    async def conf_raid(self,ctx,option,value):
        try:
            if value == "scret-desc":
                if type(ctx) == commands.Context:
                    guild = ctx.guild.id
                elif type(ctx) == str:
                    if ctx.isnumeric():
                        guild = int(ctx)
                elif type(ctx) == int:
                    guild = ctx
                else:
                    return self.default_opt['anti_raid']
                v = await self.find_staff(guild,option,channel=None)
                return await self.form_raid(v)
            else:
                raids = self.raids_levels
                value = value.capitalize()
                if value.isnumeric():
                    value = int(value)
                    if value in range(0,len(raids)):
                        value = raids[value]
                if value in raids:
                    v = raids.index(value)
                    await self.modify_server(ctx.guild.id,values=[(option,v)],channel=ctx.channel)
                    msg = await self.translate(ctx.guild.id,"server","change-raid")
                    await ctx.send(msg.format(value,raids.index(value)))
                    await self.send_embed(ctx.guild,option,value)
                else:
                    msg = await self.translate(ctx.guild.id,"server","change-8")
                    await ctx.send(msg.format(", ".join(raids)))
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)

    async def form_raid(self,value):
        if value == None:
            return self.default_opt['anti_raid']
        else:
            return self.raids_levels[value]
    
    @sconfig_main.command(name="see")
    @commands.cooldown(1,10,commands.BucketType.guild)
    async def sconfig_see(self,ctx,option=None):
        """Displays the value of an option, or all options if none is specified"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.translate(ctx.guild.id,"cases","no_database"))
        await self.send_see(ctx.guild,ctx.channel,option,ctx.message,ctx)
        
    async def send_see(self,guild,channel,option,msg,ctx):
        """Envoie l'embed dans un salon"""
        if option==None:
            liste = await self.get_server([],criters=["ID="+str(guild.id)],ID=guild.id,channel=channel)
            if len(liste)==0:
                return await channel.send(str(await self.translate(channel.guild,"server","not-found")).format(guild.name))
            liste=liste[0]
            embed = ctx.bot.cogs['EmbedCog'].Embed(title=str(await self.translate(guild.id,"server","see-1")).format(guild.name), color=self.embed_color, desc=str(await self.translate(guild.id,"server","see-0")), time=msg.created_at,thumbnail=guild.icon_url_as(format='png'))
            embed.create_footer(msg.author)
            diff = channel.guild != guild
            for i,v in liste.items():
                if i in roles_options:
                    r = await self.form_roles(guild,v,diff)
                    r = ", ".join(r)
                elif i in bool_options:
                    r = str(await self.form_bool(v))
                elif i in textchan_options:
                    r = await self.form_textchan(guild,v,diff)
                    r = ", ".join(r)
                elif i in text_options:
                    #r = await self.form_text(v)
                    r = v
                elif i in numb_options:
                    r = str(v)
                elif i in vocchan_options:
                    r = await self.form_vocal(guild,v)
                    r = ", ".join(r)
                elif i == "language":
                    r = await self.form_lang(v)
                elif i in prefix_options:
                    r = await self.form_prefix(v)
                elif i in raid_options:
                    r = await self.form_raid(v)
                elif i in emoji_option:
                    r = ", ".join(await self.form_emoji(v))
                else:
                    continue
                if len(r) == 0:
                    r = "Ø"
                embed.fields.append({'name':i, 'value':r, 'inline':True})
            await channel.send(embed=embed.discord_embed())
            embed.fields.clear()
            return
        elif ctx != None:
            if option in roles_options:
                r = await self.conf_roles(ctx,option,'scret-desc')
                r = ", ".join(r)
            elif option in bool_options:
                r = str(await self.conf_bool(ctx,option,'scret-desc'))
            elif option in textchan_options:
                r = await self.conf_textchan(ctx,option,'scret-desc')
                r = ", ".join(r)
            elif option in text_options:
                r = await self.conf_text(ctx,option,'scret-desc')
            elif option in numb_options:
                r = str(v)
            elif option in vocchan_options:
                r = await self.conf_vocal(ctx,option,'scret-desc')
                r = ", ".join(r)
            elif option == "language":
                r = await self.conf_lang(ctx,option,'scret-desc')
            elif option in prefix_options:
                r = await self.conf_prefix(ctx,option,'scret-desc')
            elif option in raid_options:
                r = await self.conf_raid(ctx,option,'scret-desc')
            elif option in emoji_option:
                r = await self.conf_emoji(ctx,option,"scret-desc")
            else:
                r = await self.translate(ctx.guild.id,"server","change-0")
            if option in self.optionsList:
                try:
                    r = str(await self.translate(ctx.guild,"server_desc",option)).format(r)
                except:
                    pass
            try:
                if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
                    await ctx.send(await self.translate(ctx.guild.id,"mc","cant-embed"))
                    return
                embed = ctx.bot.cogs["EmbedCog"].Embed(title=str(await self.translate(ctx.guild.id,"server","opt_title")).format(option,ctx.guild.name), color=self.embed_color, desc=r, time=ctx.message.created_at)
                embed.create_footer(ctx.author)
                await ctx.send(embed=embed.discord_embed())
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

            
    @sconfig_main.command(name="delete",hidden=True)
    @commands.is_owner()
    async def admin_delete(self,ctx,ID:int):
        if await self.delete_server(ID):
            await ctx.send("Le serveur n°{} semble avoir correctement été supprimé !".format(ID))



    async def update_memberChannel(self,guild):
        ch = await self.find_staff(guild.id,"membercounter")
        if ch not in ['',None]:
            ch = guild.get_channel(int(ch))
            if ch==None:
                return
            lang = await self.translate(guild.id,"current_lang","current")
            text = "{}{}: {}".format(str(await self.translate(guild.id,"keywords","membres")).capitalize() , " " if lang=='fr' else "" , len(guild.members))
            try:
                await ch.edit(name=text,reason="Automated action")
            except Exception as e:
                await self.bot.cogs['UtilitiesCog'].print2("[UpdateMemberChannel] "+str(e))
    
    
def setup(bot):
    bot.add_cog(ServerCog(bot))
