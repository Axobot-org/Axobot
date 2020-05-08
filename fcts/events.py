import discord, datetime, asyncio, logging, time, aiohttp, json, random, shutil, mysql
from discord.ext import commands, tasks
from fcts.checks import is_fun_enabled

class Events(commands.Cog):
    """Cog for the management of major events that do not belong elsewhere. Like when a new server invites the bot."""

    def __init__(self,bot):
        self.bot = bot
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
        self.file = "events"
        self.dbl_last_sending = datetime.datetime.utcfromtimestamp(0)
        self.partner_last_check = datetime.datetime.utcfromtimestamp(0)
        self.last_tr_backup = datetime.datetime.utcfromtimestamp(0)
        self.last_eventDay_check = datetime.datetime.utcfromtimestamp(0)
        self.statslogs_last_push = datetime.datetime.utcfromtimestamp(0)
        self.last_statusio = datetime.datetime.utcfromtimestamp(0)
        self.loop_errors = [0,datetime.datetime.utcfromtimestamp(0)]
        self.latencies_list = list()
        self.embed_colors = {"welcome":5301186,
        "mute":4868682,
        "kick":16730625,
        "ban":13632027,
        "slowmode":5671364,
        "clear":16312092,
        "warn":9131818,
        "softban":16720385,
        "error":16078115,
        "case-edit":10197915}
        self.points = 0
        self.table = {'kick':3,
            'ban':7,
            'invite':22,
            'emoji':30,
            'channel':45,
            'role':60,
            'guild':75}
        self.statuspage_header = {"Content-Type": "application/json", "Authorization": "OAuth " + self.bot.others["statuspage"]}
        bot.add_listener(self.on_new_message,'on_message')


    def cog_unload(self):
        self.loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
        if self.bot.database_online:
            await asyncio.sleep(0.1)
            await self.send_sql_statslogs()


    @commands.Cog.listener()
    async def on_member_update(self,before:discord.Member,after:discord.Member):
        """Called when a member change something (status, activity, nickame, roles)"""
        if before.nick != after.nick:
            config_option = await self.bot.cogs['UtilitiesCog'].get_db_userinfo(['allow_usernames_logs'],["userID="+str(before.id)])
            if config_option != None and config_option['allow_usernames_logs']==False:
                return
            await self.updade_memberslogs_name(before, after)

    async def updade_memberslogs_name(self, before:discord.Member, after:discord.Member, tries:int=0):
        if tries>5:
            return
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        ID = round(time.time()/2) * 10 + random.randrange(0,9)
        b = '' if before.nick==None else before.nick.replace("'","\\'")
        a = '' if after.nick==None else after.nick.replace("'","\\'")
        query = ("INSERT INTO `usernames_logs` (`ID`,`user`,`old`,`new`,`guild`,`beta`) VALUES ('{}','{}','{}','{}','{}',{})".format(ID,before.id,b,a,before.guild.id,self.bot.beta))
        try:
            cursor.execute(query)
            cnx.commit()
            cursor.close()
        except mysql.connector.errors.IntegrityError as e:
            self.bot.log.warn(e)
            await self.updade_memberslogs_name(before, after, tries+1)

    @commands.Cog.listener()
    async def on_user_update(self,before:discord.User,after:discord.User):
        """Called when a user change something (avatar, username, discrim)"""
        if before.name != after.name:
            config_option = await self.bot.cogs['UtilitiesCog'].get_db_userinfo(['allow_usernames_logs'],["userID="+str(before.id)])
            if config_option != None and config_option['allow_usernames_logs']==False:
                return
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor()
            ID = round(time.time()/2) * 10 + random.randrange(0,9)
            query = ("INSERT INTO `usernames_logs` (`ID`,`user`,`old`,`new`,`guild`,`beta`) VALUES ('{}','{}','{}','{}','{}',{})".format(ID,before.id,before.name.replace("'","\\'"),after.name.replace("'","\\'"),0,self.bot.beta))
            cursor.execute(query)
            cnx.commit()
            cursor.close()


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
                desc = "Bot **joins the server** {} ({}) - {} users".format(guild.name,guild.id,len(guild.members))
            else:
                self.bot.log.info("Le bot a quitté le serveur {}".format(guild.id))
                desc = "Bot **left the server** {} ({}) - {} users".format(guild.name,guild.id,len(guild.members))
            emb = self.bot.cogs["EmbedCog"].Embed(desc=desc,color=self.embed_colors['welcome']).update_timestamp().set_author(self.bot.user)
            await self.bot.cogs["EmbedCog"].send([emb])
            if self.bot.database_online:
                await self.send_sql_statslogs()
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)


    async def on_new_message(self, msg:discord.Message):
        """Called for each new message because it's cool"""
        if msg.guild == None:
            await self.send_mp(msg)
        else:
            try:
                await self.bot.cogs['FunCog'].check_suggestion(msg)
            except KeyError:
                pass
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,msg)
            await self.bot.cogs['FunCog'].check_afk(msg)
        if msg.author != self.bot.user:
            await self.bot.cogs['InfoCog'].emoji_analysis(msg)
        if "send nudes" in msg.content.lower() and len(msg.content)<13 and random.random()>0.0:
            try:
                nudes_reacts = [':eyes:',':innocent:',':rolling_eyes:',':confused:',':smirk:']
                if msg.guild==None or msg.channel.permissions_for(msg.guild.me).external_emojis:
                    nudes_reacts += ['<:whut:485924115199426600>','<:thinksmart:513105826530197514>','<:excusemewhat:418154673523130398>','<:blobthinking:499661417012527104>','<a:ano_U:568494122856611850>','<:catsmirk:523929843331498015>','<a:ablobno:537680872820965377>']
                await msg.channel.send(random.choice(nudes_reacts))
            except:
                pass
        # Halloween event
        elif (msg.channel.id==635569244507209749 and random.random()<0.3) or (("booh" in msg.content.lower() or "halloween" in msg.content.lower() or "witch" in msg.content.lower()) and random.random()<0.05 and self.bot.current_event=="halloween"):
            try:
                react = random.choice(['🦇','🎃','🕷️']*2+['👀'])
                await msg.add_reaction(react)
            except:
                pass
        # April Fool event
        elif random.random()<0.1 and self.bot.current_event=="fish" and is_fun_enabled(msg, self.bot.get_cog("FunCog")):
            try:
                react = random.choice(['🐟','🎣', '🐠', '🐡']*4+['👀'])
                await msg.add_reaction(react)
            except:
                pass
            pass
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
        await self.check_mp_adv(msg)
        if msg.channel.recipient.id in [392766377078816789,279568324260528128,552273019020771358]:
            return
        channel = self.bot.get_channel(625320165621497886)
        if channel==None:
            return self.bot.log.warn("[send_mp] Salon de MP introuvable")
        emb = msg.embeds[0] if len(msg.embeds)>0 else None
        text = "__`{} ({} - {})`__\n{}".format(msg.author,msg.channel.recipient,await self.bot.cogs["TimeCog"].date(msg.created_at,digital=True),msg.content)
        if len(msg.attachments)>0:
            text += "".join(["\n{}".format(x.url) for x in msg.attachments])
        await channel.send(text,embed=emb)

    async def check_mp_adv(self,msg):
        """Teste s'il s'agit d'une pub MP"""
        if msg.author.id==self.bot.user.id or 'discord.gg/' not in msg.content:
            return
        try:
            _ = await self.bot.fetch_invite(msg.content)
        except:
            return
        # d = datetime.datetime.utcnow() - (await msg.channel.history(limit=2).flatten())[1].created_at
        # if d.total_seconds() > 600:
        await msg.channel.send(await self.translate(msg.channel,"events","mp-adv"))


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
        if event == "kick":
            await self.add_points(-self.table['kick'])
        elif event == "ban":
            await self.add_points(-self.table['ban'])


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
        except discord.Forbidden:
            pass
        except Exception as e:
            if member.guild.id!=264445053596991498:
                self.bot.log.warn("[check_user_left] {} (user {}/server {})".format(e,member.id,member.guild.id))


    async def task_timer(self, task:dict):
        if task["guild"] != None:
            guild = self.bot.get_guild(task['guild'])
            if guild == None:
                return
            channel = guild.get_channel(task["channel"])
            if channel == None:
                return
        else:
            channel = self.bot.get_channel(task["channel"])
            if channel == None:
                return
        if task["user"] != None:
            user = self.bot.get_user(task["user"])
            if user == None:
                raise discord.errors.NotFound
            try:
                f_duration = await self.bot.get_cog('TimeCog').time_delta(task['duration'],lang=await self.translate(channel,'current_lang','current'), form='developed', precision=0)
                t = (await self.translate(channel, "fun", "reminds-title")).capitalize()
                foot = await self.translate(channel, "fun", "reminds-date")
                emb = self.bot.get_cog("EmbedCog").Embed(title=t, desc=task["message"], color=4886754, time=task["begin"], footer_text=foot)
                msg = await self.translate(channel, "fun", "reminds-asked", user=user.mention, duration=f_duration)
                await channel.send(msg, embed=emb)
            except discord.errors.Forbidden:
                pass
            except Exception as e:
                raise e


    async def get_events_from_db(self,all=False,IDonly=False):
        """Renvoie une liste de tous les events qui doivent être exécutés"""
        try:
            cnx = self.bot.cnx_frm
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
            if len(liste)>0:
                return liste
            else:
                return []
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


    async def check_tasks(self):
        await self.bot.wait_until_ready()
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
            if task['action']=='ban':
                try:
                    guild = self.bot.get_guild(task['guild'])
                    if guild==None:
                        continue
                    try:
                        user = await self.bot.fetch_user(task['user'])
                    except:
                        continue
                    await self.bot.cogs['ModeratorCog'].unban_event(guild,user,guild.me)
                    await self.remove_task(task['ID'])
                except discord.errors.NotFound:
                    await self.remove_task(task['ID'])
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                    self.bot.log.error("[unban_task] Impossible d'unban automatiquement : {}".format(e))
            if task['action']=="timer":
                try:
                    await self.task_timer(task)
                except discord.errors.NotFound:
                    await self.remove_task(task['ID'])
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,None)
                    self.bot.log.error("[unban_task] Impossible d'envoyer un timer : {}".format(e))
                else:
                    await self.remove_task(task['ID'])



    async def add_task(self, action:str, duration:int, userID: int, guildID:int=None, channelID:int=None, message:str=None):
        """Ajoute une tâche à la liste"""
        tasks = await self.get_events_from_db(all=True)
        for t in tasks:
            if (t['user']==userID and t['guild']==guildID and t['action']==action and t["channel"]==channelID) and t['action']!='timer':
                return await self.update_duration(t['ID'],duration)
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        if len(tasks)>0:
            ID = max([x['ID'] for x in tasks])+1
        else:
            ID = 0
        # if message != None:
        #     message = message.replace('"', "\\")
        # query = ("INSERT INTO `timed` (`ID`,`guild`,`channel`,`user`,`action`,`duration`,`message`) VALUES ({},{},{},{},'{}',{},\"{}\")".format(ID,guildID,channelID, userID, action, duration, message))
        # cursor.execute(query)
        #  %(username)s
        query = "INSERT INTO `timed` (`ID`,`guild`,`channel`,`user`,`action`,`duration`,`message`) VALUES (%(ID)s,%(guild)s,%(channel)s,%(user)s,%(action)s,%(duration)s,%(message)s)"
        cursor.execute(query, {'ID':ID, 'guild':guildID, 'channel':channelID, 'user':userID, 'action':action, 'duration':duration, 'message':message})
        cnx.commit()
        return True

    async def update_duration(self,ID,new_duration):
        """Modifie la durée d'une tâche"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = ("UPDATE `timed` SET `duration`={} WHERE `ID`={}".format(new_duration,ID))
        cursor.execute(query)
        cnx.commit()
        return True

    async def remove_task(self,ID:int):
        """Enlève une tâche exécutée"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = ("DELETE FROM `timed` WHERE `timed`.`ID` = {}".format(ID))
        cursor.execute(query)
        cnx.commit()
        return True

    @tasks.loop(seconds=1.0)
    async def loop(self):
        try:
            d = datetime.datetime.now()
            # Timed tasks - every 20s
            if d.second%20 == 0:
                await self.check_tasks()
            # Latency usage - every 30s
            if d.second%30 == 0:
                await self.status_loop(d)
            # Clear old rank cards - every 20min
            elif d.minute%20 == 0:
                await self.bot.cogs['XPCog'].clear_cards()
                await self.rss_loop()
            # Partners reload - every 7h (start from 1am)
            elif d.hour%7 == 1 and d.hour != self.partner_last_check.hour:
                await self.partners_loop()
            # Bots lists updates - every day
            elif d.hour == 0 and d.day != self.dbl_last_sending.day:
                await self.dbl_send_data()
            # Translation backup - every 12h (start from 1am)
            elif d.hour%12 == 1 and (d.hour != self.last_tr_backup.hour or d.day != self.last_tr_backup.day):
                await self.translations_backup()
            # Check current event - every 12h (start from 0:45 am)
            elif int(d.hour)%12 == 0 and int(d.minute)%45 == 0 and (d.hour != self.last_eventDay_check.hour or d.day != self.last_eventDay_check.day):
                await self.botEventLoop()
            # Send stats logs - every 2h (start from 0:05 am)
            elif int(d.hour)%2 == 0 and int(d.minute)%5 == 0 and (d.day != self.statslogs_last_push.day or d.hour != self.statslogs_last_push.hour):
                await self.send_sql_statslogs()
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            self.loop_errors[0] += 1
            if (datetime.datetime.now() - self.loop_errors[1]).total_seconds() > 120:
                self.loop_errors[0] = 0
                self.loop_errors[1] = datetime.datetime.now()
            if self.loop_errors[0] > 10:
                await self.bot.cogs['ErrorsCog'].senf_err_msg(":warning: **Trop d'erreurs : ARRET DE LA BOUCLE PRINCIPALE** <@279568324260528128> :warning:")
                self.loop.cancel()

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        await self.rss_loop()
        self.bot.log.info("[tasks_loop] Lancement de la boucle")


    async def status_loop(self, d:datetime.datetime):
        "Send average latency to zbot.statuspage.io"
        if self.bot.beta:
            return
        self.latencies_list.append(round(self.bot.latency*1000))
        if d.minute % 4 == 0 and d.minute != self.last_statusio.minute:
            average = round(sum(self.latencies_list)/len(self.latencies_list))
            params = {"data": {"timestamp": round(d.timestamp()), "value":average}}
            async with aiohttp.ClientSession(loop=self.bot.loop, headers=self.statuspage_header) as session:
                async with session.post("https://api.statuspage.io/v1/pages/g9cnphg3mhm9/metrics/x4xs4clhkmz0/data", json=params) as r:
                    r.raise_for_status()
                    self.bot.log.info(f"StatusPage API returned {r.status} for {params}")
            self.latencies_list = list()
            self.last_statusio = d

    async def rss_loop(self):
        if self.bot.cogs['RssCog'].last_update==None or (datetime.datetime.now() - self.bot.cogs['RssCog'].last_update).total_seconds()  > 5*60:
            self.bot.cogs['RssCog'].last_update = datetime.datetime.now()
            asyncio.run_coroutine_threadsafe(self.bot.cogs['RssCog'].main_loop(),asyncio.get_running_loop())
    
    async def botEventLoop(self):
        self.bot.cogs["BotEventsCog"].updateCurrentEvent()
        e = self.bot.cogs["BotEventsCog"].current_event
        emb = self.bot.cogs["EmbedCog"].Embed(desc=f'**Bot event** updated (current event is {e})',color=1406147).update_timestamp().set_author(self.bot.user)
        await self.bot.cogs["EmbedCog"].send([emb],url="loop")
        self.last_eventDay_check = datetime.datetime.today()
    
    async def dbl_send_data(self):
        """Send guilds count to Discord Bots Lists"""
        if self.bot.beta:
            return
        t = time.time()
        answers = ['None','None','None','None','None']
        self.bot.log.info("[DBL] Envoi des infos sur le nombre de guildes...")
        try:
            guildCount = await self.bot.cogs['InfoCog'].get_guilds_count()
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            guildCount = len(self.bot.guilds)
        session = aiohttp.ClientSession(loop=self.bot.loop)
        try:# https://top.gg/bot/486896267788812288
            payload = {'server_count': guildCount}
            async with session.post('https://top.gg/api/bots/486896267788812288/stats',data=payload,headers={'Authorization':str(self.bot.dbl_token)}) as resp:
                self.bot.log.debug('discordbots.org returned {} for {}'.format(resp.status, payload))
                answers[0] = resp.status
        except Exception as e:
            answers[0] = "0"
            await self.bot.get_cog("ErrorsCog").on_error(e,None)
        try: # https://bots.ondiscord.xyz/bots/486896267788812288
            payload = json.dumps({
            'guildCount': guildCount
            })
            headers = {
                'Authorization': self.bot.others['botsondiscord'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://bots.ondiscord.xyz/bot-api/bots/{}/guilds'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('BotsOnDiscord returned {} for {}'.format(resp.status, payload))
                answers[1] = resp.status
        except Exception as e:
            answers[1] = "0"
            await self.bot.get_cog("ErrorsCog").on_error(e,None)
        try: # https://botlist.space/bot/486896267788812288
            payload = json.dumps({
            'server_count': guildCount
            })
            headers = {
                'Authorization': self.bot.others['botlist.space'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://api.botlist.space/v1/bots/{}'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('botlist.space returned {} for {}'.format(resp.status, payload))
                answers[2] = resp.status
        except Exception as e:
            answers[2] = "0"
            await self.bot.get_cog("ErrorsCog").on_error(e,None)
        try: # https://discord.boats/bot/486896267788812288
            headers = {
                'Authorization': self.bot.others['discordboats'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://discord.boats/api/bot/{}'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('discord.boats returned {} for {}'.format(resp.status, payload))
                answers[3] = resp.status
        except Exception as e:
            answers[3] = "0"
            await self.bot.get_cog("ErrorsCog").on_error(e,None)
        try: # https://arcane-center.xyz/bot/486896267788812288
            headers = {
                'Authorization': self.bot.others['arcanecenter'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://arcane-botcenter.xyz/api/{}/stats'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('Arcane Center returned {} for {}'.format(resp.status, payload))
                answers[4] = resp.status
        except Exception as e:
            answers[4] = "0"
            await self.bot.get_cog("ErrorsCog").on_error(e,None)
        await session.close()
        answers = [str(x) for x in answers]
        emb = self.bot.cogs["EmbedCog"].Embed(desc='**Guilds count updated** in {}s ({})'.format(round(time.time()-t,3),'-'.join(answers)),color=7229109).update_timestamp().set_author(self.bot.user)
        await self.bot.cogs["EmbedCog"].send([emb],url="loop")
        self.dbl_last_sending = datetime.datetime.now()

    async def partners_loop(self):
        """Update partners channels (every 7 hours)"""
        t = time.time()
        self.partner_last_check = datetime.datetime.now()
        channels_list = await self.bot.cogs['ServerCog'].get_server(criters=["`partner_channel`<>''"],columns=['ID','partner_channel','partner_color'])
        self.bot.log.info("[Partners] Rafraîchissement des salons ({} serveurs prévus)...".format(len(channels_list)))
        count = [0,0]
        for guild in channels_list:
            try:
                chan = guild['partner_channel'].split(';')[0]
                if not chan.isnumeric():
                    continue
                chan = self.bot.get_channel(int(chan))
                if chan==None:
                    continue
                count[0] += 1
                count[1] += await self.bot.cogs['PartnersCog'].update_partners(chan,guild['partner_color'])
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
        emb = self.bot.cogs["EmbedCog"].Embed(desc='**Partners channels updated** in {}s ({} channels - {} partners)'.format(round(time.time()-t,3),count[0],count[1]),color=10949630).update_timestamp().set_author(self.bot.user)
        await self.bot.cogs["EmbedCog"].send([emb],url="loop")
        
    async def translations_backup(self):
        """Do a backup of the translations files"""
        from os import remove
        t = time.time()
        self.last_tr_backup = datetime.datetime.now()
        try:
            remove('translation-backup.tar')
        except:
            pass
        try:
           shutil.make_archive('translation-backup','tar','translation')
        except FileNotFoundError:
            await self.bot.cogs['ErrorsCog'].senf_err_msg("Translators backup: Unable to find backup folder")
            return
        emb = self.bot.cogs["EmbedCog"].Embed(desc='**Translations files backup** completed in {}s'.format(round(time.time()-t,3)),color=10197915).update_timestamp().set_author(self.bot.user)
        await self.bot.cogs["EmbedCog"].send([emb],url="loop")    

    async def send_sql_statslogs(self):
        "Send some stats about the current bot stats"
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        rss_feeds = await self.bot.get_cog("RssCog").get_raws_count(True)
        active_rss_feeds = await self.bot.get_cog("RssCog").get_raws_count()
        query = ("INSERT INTO `log_stats` (`time`, `servers_count`, `members_count`, `bots_count`, `dapi_heartbeat`, `codelines_count`, `earned_xp_total`, `rss_feeds`, `active_rss_feeds`, `beta`) VALUES (CURRENT_TIMESTAMP, '{server_count}', '{members_count}', '{bots_count}', '{ping}', '{codelines}', '{xp}', '{rss_feeds}', '{active_rss_feeds}','{beta}')".format(
            server_count = len(self.bot.guilds),
            members_count = len(self.bot.users),
            bots_count = len([1 for x in self.bot.users if x.bot]),
            ping = round(self.bot.latency,3),
            codelines = self.bot.cogs["InfoCog"].codelines,
            xp = await self.bot.cogs['XPCog'].bdd_total_xp(),
            rss_feeds = rss_feeds,
            active_rss_feeds = active_rss_feeds,
            beta = 1 if self.bot.beta else 0
        ))
        try:
            cursor.execute(query)
        except Exception as e:
            await self.bot.get_cog("ErrorsCog").senf_err_msg(query)
            raise e
        cnx.commit()
        cursor.close()
        emb = self.bot.cogs["EmbedCog"].Embed(desc='**Stats logs** updated',color=5293283).update_timestamp().set_author(self.bot.user)
        await self.bot.cogs["EmbedCog"].send([emb],url="loop")
        self.statslogs_last_push = datetime.datetime.now()
        

def setup(bot):
    bot.add_cog(Events(bot))
    if bot.internal_loop_enabled:
        try:
            bot.get_cog("Events").loop.start()
        except RuntimeError:
            pass
