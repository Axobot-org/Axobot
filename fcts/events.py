import discord, datetime, asyncio, logging, time



class Events:
    """Cog for the management of major events that do not belong elsewhere. Like when a new server invites the bot."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "events"
        self.embed_colors = {"welcome":5301186,
        "mute":4868682,
        "kick":16730625,
        "ban":13632027,
        "slowmode":5671364,
        "clear":16312092,
        "warn":9131818,
        "softban":16720385}
        self.points = 0
        self.table = {'kick':3,
            'ban':7,
            'invite':22,
            'emoji':30,
            'channel':45,
            'role':60,
            'guild':75}
    
    async def on_guild_add(self,guild):
        """Called when the bot joins a guild"""
        await self.send_guild_log(guild,"join")


    async def on_guild_del(self,guild):
        """Called when the bot left a guild"""
        await self.send_guild_log(guild,"left")

    async def send_guild_log(self,guild,Type):
        """Send a log to the logging channel when the bot joins/leave a guild"""
        try:
            if Type == "join":
                self.bot.log.info("Le bot a rejoint le serveur {}".format(guild.id))
                desc = "Bot **joins the server** {} ({})".format(guild.name,guild.id)
            else:
                self.bot.log.info("Le bot a quitté le serveur {}".format(guild.id))
                desc = "Bot **left the server** {} ({})".format(guild.name,guild.id)
            emb = self.bot.cogs["EmbedCog"].Embed(desc=desc,color=self.embed_colors['welcome']).update_timestamp().set_author(self.bot.user)
            await self.bot.cogs["EmbedCog"].send([emb])
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)


    async def on_new_message(self,msg):
        if msg.guild == None:
            await self.send_mp(msg)
        else:
            try:
                await self.bot.cogs['FunCog'].check_suggestion(msg)
            except KeyError:
                pass
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,msg)
        if msg.author.bot==False and await self.bot.cogs['AdminCog'].check_if_admin(msg.author) == False and msg.guild!=None:
            cond = True
            if self.bot.database_online:
                cond = str(await self.bot.cogs["ServerCog"].find_staff(msg.guild,"anti_caps_lock")) in ['1','True']
            if cond:
                if len(msg.content)>0 and sum(1 for c in msg.content if c.isupper())/len(msg.content.replace('|','')) > 0.75 and len(msg.content.replace('|',''))>7 and not msg.channel.permissions_for(msg.author).administrator:
                    try:
                        await msg.channel.send(str(await self.bot.cogs["LangCog"].tr(msg.guild,"modo","caps-lock")).format(msg.author.mention),delete_after=4.0)
                    except:
                        pass
        

    async def send_mp(self,msg):
        if "vient d'être ajouté dans la base de donnée" in msg.content:
            return
        if msg.channel.recipient.id in [392766377078816789,279568324260528128]:
            return
        channel = self.bot.get_channel(488768968891564033)
        if channel==None:
            return print("[send_mp] Salon de MP introuvable")
        emb = msg.embeds[0] if len(msg.embeds)>0 else None
        text = "__`{} ({} - {})`__\n{}".format(msg.author,msg.channel.recipient,await self.bot.cogs["TimeCog"].date(msg.created_at,digital=True),msg.content)
        if len(msg.attachments)>0:
            text += "".join(["\n{}".format(x.url) for x in msg.attachments])
        await channel.send(text,embed=emb)



    async def send_logs_per_server(self,guild,Type,message,author=None):
        """Send a log in a server. Type is used to define the color of the embed"""
        if not self.bot.database_online:
            return
        c = self.embed_colors[Type.lower()]
        try:
            config = str(await self.bot.cogs["ServerCog"].find_staff(guild.id,"modlogs_channel")).split(';')[0]
            if config == "" or config.isnumeric()==False:
                return
            channel = guild.get_channel(int(config))
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)
            return
        if channel == None:
            return
        emb = self.bot.cogs["EmbedCog"].Embed(desc=message,color=c).update_timestamp()
        if author != None:
            emb.set_author(author)
        try:
            await channel.send(embed=emb.discord_embed())
        except:
            pass



    async def add_points(self,points):
        """Ajoute ou enlève un certain nombre de points au score
        La principale utilité de cette fonction est de pouvoir check le nombre de points à chaque changement"""
        self.points += points
        if self.points<0:
            self.points = 0

    async def add_event(self,event):
        print("Points b4:",self.points)
        if event == "kick":
            await self.add_points(-self.table['kick'])
        elif event == "ban":
            await self.add_points(-self.table['ban'])
        print("Points aftr:",self.points)


    async def check_user_left(self,member):
        """Vérifie si un joueur a été banni ou kick par ZBot"""
        try:
            async for entry in member.guild.audit_logs(user=member.guild.me,limit=15):
                if entry.created_at < datetime.datetime.utcnow()-datetime.timedelta(seconds=60):
                    break
                if entry.action==discord.AuditLogAction.kick and entry.target==member:
                    await self.add_points(self.table['kick'])
                    break
                elif entry.action==discord.AuditLogAction.ban and entry.target==member:
                    await self.add_points(self.table['ban'])
                    break
        except Exception as e:
            if member.guild.id!=264445053596991498:
                self.bot.log.warn("[check_user_left] {} (user {}/server {})".format(e,member.id,member.guild.id))



    async def get_events_from_db(self,all=False,IDonly=False):
        """Renvoie une liste de tous les events qui doivent être exécutés"""
        try:
            cnx = self.bot.cogs['ServerCog'].connect()
            cursor = cnx.cursor(dictionary = True)
            if IDonly:
                query = ("SELECT `ID` FROM `timed`")
            else:
                query = ("SELECT * FROM `timed`")
            cursor.execute(query)
            liste = list()
            for x in cursor:
                if all:
                    liste.append(x)
                else:
                    if IDonly or x['begin'].timestamp()+x['duration'] < time.time():
                        liste.append(x)
            cnx.close()
            if len(liste)>0:
                return liste
            else:
                return []
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


    async def check_tasks(self):
        tasks = await self.get_events_from_db()
        if len(tasks)==0:
            return
        self.bot.log.debug("[tasks_loop] Itération ({} tâches trouvées)".format(len(tasks)))
        for task in tasks:
            if task['action']=='mute':
                try:
                    guild = self.bot.get_guild(task['guild'])
                    if guild==None:
                        continue
                    user = guild.get_member(task['user'])
                    if user==None:
                        continue
                    await self.bot.cogs['ModeratorCog'].unmute_event(guild,user,guild.me)
                    await self.remove_task(task['ID'])
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                    self.bot.log.error("[unmute_task] Impossible d'unmute automatiquement : {}".format(e))

    async def add_task(self,guildID,userID,action,duration):
        """Ajoute une tâche à la liste"""
        cnx = self.bot.cogs['ServerCog'].connect()
        cursor = cnx.cursor()
        ids = await self.get_events_from_db(all=True,IDonly=True)
        if len(ids)>0:
            ID = max([x['ID'] for x in ids])+1
        else:
            ID = 0
        query = ("INSERT INTO `timed` (`ID`,`guild`,`user`,`action`,`duration`) VALUES ({},{},{},'{}',{})".format(ID,guildID,userID,action,duration))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True

    async def remove_task(self,ID:int):
        """Enlève une tâche exécutée"""
        cnx = self.bot.cogs['ServerCog'].connect()
        cursor = cnx.cursor()
        query = ("DELETE FROM `timed` WHERE `timed`.`ID` = {}".format(ID))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True

    async def loop(self):
        await self.bot.wait_until_ready()
        self.bot.log.info("[tasks_loop] Lancement de la boucle")
        while not self.bot.is_closed():
            if int(datetime.datetime.now().second)%30 == 0:
                await self.check_tasks()
            await asyncio.sleep(0.5)

def setup(bot):
    bot.add_cog(Events(bot))