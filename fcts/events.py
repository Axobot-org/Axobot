import discord
import datetime
import asyncio
import time
import aiohttp
import json
import random
import shutil
import mysql
import psutil
import re
import marshal
from discord.ext import commands, tasks
from fcts.checks import is_fun_enabled
from utils import Zbot

class Events(commands.Cog):
    """Cog for the management of major events that do not belong elsewhere. Like when a new server invites the bot."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "events"
        self.dbl_last_sending = datetime.datetime.utcfromtimestamp(0)
        self.partner_last_check = datetime.datetime.utcfromtimestamp(0)
        self.last_tr_backup = datetime.datetime.utcfromtimestamp(0)
        self.last_eventDay_check = datetime.datetime.utcfromtimestamp(0)
        self.statslogs_last_push = datetime.datetime.utcfromtimestamp(0)
        self.last_statusio = datetime.datetime.utcfromtimestamp(0)
        self.loop_errors = [0,datetime.datetime.utcfromtimestamp(0)]
        self.last_membercounter = datetime.datetime.utcfromtimestamp(0)
        self.latencies_list = list()
        self.embed_colors = {"welcome":5301186,
            "mute":4868682,
            "unmute":8311585,
            "kick":16730625,
            "ban":13632027,
            "unban":8311585,
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


    def cog_unload(self):
        self.loop.cancel() # pylint: disable=no-member

    @commands.Cog.listener()
    async def on_ready(self):
        if self.bot.database_online:
            await asyncio.sleep(0.1)
            await self.send_sql_statslogs()


    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Called when a member change something (status, activity, nickame, roles)"""
        if before.nick != after.nick:
            config_option = await self.bot.get_cog('Utilities').get_db_userinfo(['allow_usernames_logs'],["userID="+str(before.id)])
            if config_option is not None and config_option['allow_usernames_logs'] is False:
                return
            await self.updade_memberslogs_name(before, after)

    async def updade_memberslogs_name(self, before:discord.Member, after:discord.Member, tries:int=0):
        if tries > 5:
            return
        if not self.bot.database_online:
            return
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        if isinstance(before, discord.Member):
            b = '' if before.nick is None else before.nick
            a = '' if after.nick is None else after.nick
        else:
            b = '' if before.name is None else before.name
            a = '' if after.name is None else after.name
        guild = before.guild.id if hasattr(before, 'guild') else 0
        query = "INSERT INTO `usernames_logs` (`user`,`old`,`new`,`guild`,`beta`) VALUES (%(u)s,%(o)s,%(n)s,%(g)s,%(b)s)"
        try:
            cursor.execute(query, { 'u': before.id, 'o': b, 'n': a, 'g': guild, 'b': self.bot.beta })
            cnx.commit()
        except mysql.connector.errors.IntegrityError as e:
            self.bot.log.warning(e)
            await self.updade_memberslogs_name(before, after, tries+1)
        cursor.close()

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Called when a user change something (avatar, username, discrim)"""
        if before.name != after.name:
            config_option = await self.bot.get_cog('Utilities').get_db_userinfo(['allow_usernames_logs'],["userID="+str(before.id)])
            if config_option is not None and config_option['allow_usernames_logs'] is False:
                return
            await self.updade_memberslogs_name(before, after)


    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a guild"""
        await self.send_guild_log(guild,"join")
        if guild.owner:
            await self.check_owner_server(guild.owner)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot left a guild"""
        await self.send_guild_log(guild,"left")
        if guild.owner:
            await self.check_owner_server(guild.owner)

    async def send_guild_log(self, guild: discord.Guild, Type: str):
        """Send a log to the logging channel when the bot joins/leave a guild"""
        try:
            if Type == "join":
                self.bot.log.info("Bot joined the server {}".format(guild.id))
                desc = "Bot **joined the server** {} ({}) - {} users".format(guild.name,guild.id,len(guild.members))
            else:
                self.bot.log.info("Bot left the server {}".format(guild.id))
                if guild.name is None and guild.unavailable:
                    desc = "Bot **may have left** the server {} (guild unavailable)".format(guild.id)
                else:
                    desc = "Bot **left the server** {} ({}) - {} users".format(guild.name,guild.id,len(guild.members))
            emb = self.bot.get_cog("Embeds").Embed(desc=desc,color=self.embed_colors['welcome']).update_timestamp().set_author(self.bot.user)
            await self.bot.get_cog("Embeds").send([emb])
            if self.bot.database_online:
                await self.send_sql_statslogs()
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e,None)


    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Called for each new message because it's cool"""
        if self.bot.zombie_mode:
            return
        if msg.guild is None:
            await self.send_mp(msg)
        else:
            try:
                await self.bot.get_cog('Fun').check_suggestion(msg)
            except KeyError:
                pass
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,msg)
            await self.bot.get_cog('Fun').check_afk(msg)
        if msg.author != self.bot.user:
            await self.bot.get_cog('Info').emoji_analysis(msg)
        if "send nudes" in msg.content.lower() and len(msg.content)<13 and random.random() > 0.0:
            try:
                nudes_reacts = [':eyes:',':innocent:',':rolling_eyes:',':confused:',':smirk:']
                if msg.guild is None or msg.channel.permissions_for(msg.guild.me).external_emojis:
                    nudes_reacts += ['<:whut:485924115199426600>','<:thinksmart:513105826530197514>','<:excusemewhat:418154673523130398>','<:blobthinking:499661417012527104>','<a:ano_U:568494122856611850>','<:catsmirk:523929843331498015>','<a:ablobno:537680872820965377>']
                await msg.channel.send(random.choice(nudes_reacts))
            except:
                pass
        # Halloween event
        elif ("booh" in msg.content.lower() or "halloween" in msg.content.lower() or "witch" in msg.content.lower()) and random.random() < 0.05 and self.bot.current_event=="halloween":
            try:
                react = random.choice(['🦇','🎃','🕷️']*2+['👀' ])
                await msg.add_reaction(react)
            except:
                pass
        # April Fool event
        elif random.random() < 0.07 and self.bot.current_event=="fish" and await is_fun_enabled(msg, self.bot.get_cog("Fun")):
            try:
                react = random.choice(['🐟','🎣', '🐠', '🐡']*4+['👀'])
                await msg.add_reaction(react)
            except:
                pass
            pass
        if not msg.author.bot:
            cond = False
            if self.bot.database_online:
                cond = str(await self.bot.get_config(msg.guild,"anti_caps_lock")) in ['1','True']
            if cond:
                clean_content = msg.content
                for rgx_match in (r'\|', r'\*', r'_', r'<a?:\w+:\d+>', r'<(#|@&?!?)\d+>', r'https?://\w+\.\S+'):
                    clean_content = re.sub(rgx_match, '', clean_content)
                clean_content = clean_content.replace(' ', '')
                if len(clean_content) > 0 and sum(1 for c in clean_content if c.isupper())/len(clean_content) > 0.8 and len(clean_content)>7 and not msg.channel.permissions_for(msg.author).administrator:
                    try:
                        await msg.channel.send(await self.bot._(msg.guild, "moderation.caps-lock", user=msg.author.mention), delete_after=4.0)
                    except:
                        pass


    async def send_mp(self, msg: discord.Message):
        await self.check_mp_adv(msg)
        if msg.channel.recipient is None:
            # recipient couldn't be loaded
            msg.channel = await self.bot.fetch_channel(msg.channel.id)
            if msg.channel.recipient is None:
                return
        if msg.channel.recipient.id in [392766377078816789,279568324260528128,552273019020771358,281404141841022976]:
            return
        channel = self.bot.get_channel(625320165621497886)
        if channel is None:
            return self.bot.log.warning("[send_mp] Salon de MP introuvable")
        emb = msg.embeds[0] if len(msg.embeds) > 0 else None
        arrow = ":inbox_tray:" if msg.author == msg.channel.recipient else ":outbox_tray:"
        text = "{} **{}** ({} - {})\n{}".format(arrow, msg.channel.recipient, msg.channel.recipient.id, await self.bot.get_cog("TimeUtils").date(msg.created_at,digital=True), msg.content)
        if len(msg.attachments) > 0:
            text += "".join(["\n{}".format(x.url) for x in msg.attachments])
        await channel.send(text,embed=emb)

    async def check_mp_adv(self, msg: discord.Message):
        """Teste s'il s'agit d'une pub MP"""
        if self.bot.zombie_mode:
            return
        if msg.author.id == self.bot.user.id or 'discord.gg/' not in msg.content:
            return
        try:
            _ = await self.bot.fetch_invite(msg.content)
        except:
            return
        # d = datetime.datetime.utcnow() - (await msg.channel.history(limit=2).flatten())[1].created_at
        # if d.total_seconds() > 600:
        await msg.channel.send(await self.bot._(msg.channel,"events.mp-adv"))

    async def check_owner_server(self, owner: discord.User):
        """Check if a server owner should get/loose the server owner role in support server"""
        guild = self.bot.get_guild(356067272730607628)
        if not guild:
            return
        member = guild.get_member(owner.id)
        if not member:
            return
        role = guild.get_role(486905171738361876)
        if not role:
            self.bot.log.warning('[check_owner_server] Owner role not found')
            return
        guilds_owned = [x for x in self.bot.guilds if x.owner ==owner and x.member_count > 10]
        if len(guilds_owned) > 0 and role not in member.roles:
            await member.add_roles(role, reason="This user support me")
        elif len(guilds_owned) == 0 and role in member.roles:
            await member.remove_roles(role, reason="This user doesn't support me anymore")


    async def send_logs_per_server(self, guild: discord.Guild, Type:str, message: str, author: discord.User=None, fields: list[dict]=None):
        """Send a log in a server. Type is used to define the color of the embed"""
        if self.bot.zombie_mode:
            return
        if not self.bot.database_online:
            return
        c = self.embed_colors[Type.lower()]
        try:
            config = str(await self.bot.get_config(guild.id,"modlogs_channel")).split(';')[0]
            if config == "" or not config.isnumeric():
                return
            channel = guild.get_channel(int(config))
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e,None)
            return
        if channel is None:
            return
        emb = self.bot.get_cog("Embeds").Embed(desc=message, color=c, fields=fields).update_timestamp()
        if author is not None:
            emb.set_author(author)
        try:
            await channel.send(embed=emb.discord_embed())
        except:
            pass



    async def add_points(self, points: int):
        """Ajoute ou enlève un certain nombre de points au score
        La principale utilité de cette fonction est de pouvoir check le nombre de points à chaque changement"""
        self.points += points
        if self.points < 0:
            self.points = 0

    async def add_event(self, event: str):
        if event == "kick":
            await self.add_points(-self.table['kick'])
        elif event == "ban":
            await self.add_points(-self.table['ban'])


    async def check_user_left(self, member: discord.Member):
        """Vérifie si un joueur a été banni ou kick par ZBot"""
        try:
            async for entry in member.guild.audit_logs(user=member.guild.me, limit=15):
                if entry.created_at < self.bot.utcnow()-datetime.timedelta(seconds=60):
                    break
                if entry.action == discord.AuditLogAction.kick and entry.target == member:
                    await self.add_points(self.table['kick'])
                    break
                elif entry.action == discord.AuditLogAction.ban and entry.target == member:
                    await self.add_points(self.table['ban'])
                    break
        except discord.Forbidden:
            pass
        except Exception as e:
            if member.guild.id != 264445053596991498:
                self.bot.log.warning("[check_user_left] {} (user {}/server {})".format(e, member.id, member.guild.id))


    async def task_timer(self, task: dict) -> bool:
        """Send a reminder
        Returns True if the reminder has been sent"""
        if task["user"] is None:
            return True
        if task["guild"] is not None:
            guild = self.bot.get_guild(task['guild'])
            if guild is None:
                return False
            channel = guild.get_channel(task["channel"])
            member = await guild.fetch_member(task["user"])
            if channel is None or member is None: # if channel has been deleted, or if member left the guild, we send it in DM
                channel = self.bot.get_user(task["user"])
                if channel is None:
                    return False
        else:
            channel = self.bot.get_channel(task["channel"])
            if channel is None:
                return False
        user = self.bot.get_user(task["user"])
        if user is None:
            raise discord.errors.NotFound
        try:
            if self.bot.zombie_mode:
                return False
            f_duration = await self.bot.get_cog('TimeUtils').time_delta(task['duration'],lang=await self.bot._(channel,'_used_locale'), form='developed', precision=0)
            t = (await self.bot._(channel, "timers.rmd.embed-title")).capitalize()
            foot = await self.bot._(channel, "timers.rmd.embed-date")
            imgs = re.findall(r'(https://\S+\.(?:png|jpe?g|webp|gif))', task['message'])
            img = imgs[0] if len(imgs)==1 else ""
            if task['data'] is not None:
                task['data'] = json.loads(task['data'])
                if 'msg_url' in task['data']:
                    task["message"] += "\n\n[{}]({})".format(await self.bot._(channel, "timers.rmd.embed-link"), task['data']['msg_url'])
            emb = self.bot.get_cog("Embeds").Embed(title=t, desc=task["message"], color=4886754, time=task["utc_begin"], footer_text=foot, image=img)
            msg = await self.bot._(channel, "timers.rmd.embed-asked", user=user.mention, duration=f_duration)
            await channel.send(msg, embed=emb)
        except discord.errors.Forbidden:
            return False
        except Exception as e:
            raise e
        return True


    async def get_events_from_db(self, all: bool=False, IDonly: bool=False):
        """Renvoie une liste de tous les events qui doivent être exécutés"""
        try:
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            if IDonly:
                query = ("SELECT `ID` FROM `timed`")
            else:
                query = ("SELECT *, CONVERT_TZ(`begin`, @@session.time_zone, '+00:00') AS `utc_begin` FROM `timed`")
            cursor.execute(query)
            liste = list()
            for x in cursor:
                if all:
                    liste.append(x)
                else:
                    if IDonly or x['begin'].timestamp()+x['duration'] < time.time():
                        liste.append(x)
            cursor.close()
            if len(liste) > 0:
                return liste
            else:
                return []
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,None)
    
    async def cancel_unmute(self, userID: int, guildID: int):
        """Cancel every automatic unmutes for a member"""
        try:
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            query = 'DELETE FROM `timed` WHERE action="mute" AND guild=%s AND user=%s;'
            cursor.execute(query, (guildID, userID))
            cnx.commit()
            cursor.close()
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,None)


    async def check_tasks(self):
        await self.bot.wait_until_ready()
        tasks = await self.get_events_from_db()
        if len(tasks) == 0:
            return
        self.bot.log.debug("[tasks_loop] Itération ({} tâches trouvées)".format(len(tasks)))
        for task in tasks:
            if task['action']=='mute':
                try:
                    guild = self.bot.get_guild(task['guild'])
                    if guild is None:
                        continue
                    user = guild.get_member(task['user'])
                    if user is None:
                        continue
                    await self.bot.get_cog('Moderation').unmute_event(guild,user,guild.me)
                    await self.remove_task(task['ID'])
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e,None)
                    self.bot.log.error("[unmute_task] Impossible d'unmute automatiquement : {}".format(e))
            if task['action']=='ban':
                try:
                    guild = self.bot.get_guild(task['guild'])
                    if guild is None:
                        continue
                    try:
                        user = await self.bot.fetch_user(task['user'])
                    except:
                        continue
                    await self.bot.get_cog('Moderation').unban_event(guild,user,guild.me)
                    await self.remove_task(task['ID'])
                except discord.errors.NotFound:
                    await self.remove_task(task['ID'])
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e,None)
                    self.bot.log.error("[unban_task] Impossible d'unban automatiquement : {}".format(e))
            if task['action']=="timer":
                try:
                    sent = await self.task_timer(task)
                except discord.errors.NotFound:
                    await self.remove_task(task['ID'])
                except Exception as e:
                    await self.bot.get_cog('Errors').on_error(e,None)
                    self.bot.log.error("[timer_task] Impossible d'envoyer un timer : {}".format(e))
                else:
                    if sent:
                        await self.remove_task(task['ID'])



    async def add_task(self, action:str, duration:int, userID: int, guildID:int=None, channelID:int=None, message:str=None, data:dict=None):
        """Ajoute une tâche à la liste"""
        tasks = await self.get_events_from_db(all=True)
        for t in tasks:
            if (t['user']==userID and t['guild']==guildID and t['action']==action and t["channel"]==channelID) and t['action']!='timer':
                return await self.update_duration(t['ID'],duration)
        data = None if data is None else json.dumps(data)
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = "INSERT INTO `timed` (`guild`,`channel`,`user`,`action`,`duration`,`message`, `data`) VALUES (%(guild)s,%(channel)s,%(user)s,%(action)s,%(duration)s,%(message)s,%(data)s)"
        cursor.execute(query, {'guild':guildID, 'channel':channelID, 'user':userID, 'action':action, 'duration':duration, 'message':message, 'data':data})
        cnx.commit()
        cursor.close()
        return True

    async def update_duration(self, ID: int, new_duration: int):
        """Modifie la durée d'une tâche"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = ("UPDATE `timed` SET `duration`={} WHERE `ID`={}".format(new_duration,ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    async def remove_task(self, ID:int):
        """Enlève une tâche exécutée"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        query = ("DELETE FROM `timed` WHERE `timed`.`ID` = {}".format(ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    @tasks.loop(seconds=1.0)
    async def loop(self):
        try:
            d = datetime.datetime.now()
            # Timed tasks - every 20s
            if d.second%20 == 0 and self.bot.database_online:
                await self.check_tasks()
            # Latency usage - every 30s
            if d.second%30 == 0:
                await self.status_loop(d)
            # Clear old rank cards - every 20min
            elif d.minute%20 == 0 and self.bot.database_online:
                await self.bot.get_cog('Xp').clear_cards()
            # Partners reload - every 7h (start from 1am)
            elif d.hour%7 == 1 and d.hour != self.partner_last_check.hour and self.bot.database_online:
                await self.partners_loop()
            # Bots lists updates - every day
            elif d.hour == 0 and d.day != self.dbl_last_sending.day:
                await self.dbl_send_data()
            # Translation backup - every 12h (start from 1am)
            elif d.hour%12 == 1 and (d.hour != self.last_tr_backup.hour or d.day != self.last_tr_backup.day):
                await self.translations_backup()
            # Check current event - every 12h (start from 0:02 am)
            elif int(d.hour)%12 == 0 and int(d.minute)%2 == 0 and (d.hour != self.last_eventDay_check.hour or d.day != self.last_eventDay_check.day):
                await self.botEventLoop()
            # Send stats logs - every 1h (start from 0:05 am)
            elif d.minute > 5 and (d.day != self.statslogs_last_push.day or d.hour != self.statslogs_last_push.hour) and self.bot.database_online:
                await self.send_sql_statslogs()
            # Refresh needed membercounter channels - every 1min
            elif abs((self.last_membercounter - d).total_seconds()) > 60 and self.bot.database_online:
                await self.bot.get_cog('Servers').update_everyMembercounter()
                self.last_membercounter = d
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,None)
            self.loop_errors[0] += 1
            if (datetime.datetime.now() - self.loop_errors[1]).total_seconds() > 120:
                self.loop_errors[0] = 0
                self.loop_errors[1] = datetime.datetime.now()
            if self.loop_errors[0] > 10:
                await self.bot.get_cog('Errors').senf_err_msg(":warning: **Trop d'erreurs : ARRET DE LA BOUCLE PRINCIPALE** <@279568324260528128> :warning:")
                self.loop.cancel() # pylint: disable=no-member

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        self.bot.log.info("[tasks_loop] Lancement de la boucle")


    async def status_loop(self, d:datetime.datetime):
        "Send average latency to zbot.statuspage.io"
        if self.bot.beta:
            return
        try:
            self.latencies_list.append(round(self.bot.latency*1000))
        except OverflowError: # Usually because latency is infinite
            self.latencies_list.append(10e6)
        if d.minute % 4 == 0 and d.minute != self.last_statusio.minute:
            average = round(sum(self.latencies_list)/len(self.latencies_list))
            async with aiohttp.ClientSession(loop=self.bot.loop, headers=self.statuspage_header) as session:
                params = {"data": {"timestamp": round(d.timestamp()), "value":average}}
                async with session.post("https://api.statuspage.io/v1/pages/g9cnphg3mhm9/metrics/x4xs4clhkmz0/data", json=params) as r:
                    r.raise_for_status()
                    self.bot.log.debug(f"StatusPage API returned {r.status} for {params} (latency)")
                params["data"]["value"] = psutil.virtual_memory().available
                async with session.post("https://api.statuspage.io/v1/pages/g9cnphg3mhm9/metrics/72bmf4nnqbwb/data", json=params) as r:
                    r.raise_for_status()
                    self.bot.log.debug(f"StatusPage API returned {r.status} for {params} (available RAM)")
            self.latencies_list = list()
            self.last_statusio = d
    
    async def botEventLoop(self):
        self.bot.get_cog("BotEvents").updateCurrentEvent()
        e = self.bot.get_cog("BotEvents").current_event
        emb = self.bot.get_cog("Embeds").Embed(desc=f'**Bot event** updated (current event is {e})',color=1406147).update_timestamp().set_author(self.bot.user)
        await self.bot.get_cog("Embeds").send([emb],url="loop")
        self.last_eventDay_check = datetime.datetime.today()
    
    async def dbl_send_data(self):
        """Send guilds count to Discord Bots Lists"""
        if self.bot.beta:
            return
        t = time.time()
        answers = ['None' for _ in range(5)]
        self.bot.log.info("[DBL] Envoi des infos sur le nombre de guildes...")
        try:
            guildCount = await self.bot.get_cog('Info').get_guilds_count()
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,None)
            guildCount = len(self.bot.guilds)
        session = aiohttp.ClientSession(loop=self.bot.loop)
        try:# https://top.gg/bot/486896267788812288
            payload = {'server_count': guildCount}
            async with session.post('https://top.gg/api/bots/486896267788812288/stats',data=payload,headers={'Authorization':str(self.bot.dbl_token)}) as resp:
                self.bot.log.debug('discordbots.org returned {} for {}'.format(resp.status, payload))
                answers[0] = resp.status
        except Exception as e:
            answers[0] = "0"
            await self.bot.get_cog("Errors").on_error(e,None)
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
            await self.bot.get_cog("Errors").on_error(e,None)
        try: # https://discordlist.space/bot/486896267788812288
            payload = json.dumps({
                'serverCount': guildCount
            })
            headers = {
                'Authorization': self.bot.others['discordlist.space'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://api.discordlist.space/v2/bots/{}'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('discordlist.space returned {} for {}'.format(resp.status, payload))
                answers[2] = resp.status
        except Exception as e:
            answers[2] = "0"
            await self.bot.get_cog("Errors").on_error(e,None)
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
            await self.bot.get_cog("Errors").on_error(e,None)
        try: # https://api.discordextremelist.xyz/v2/bot/486896267788812288/stats
            payload = json.dumps({
                'guildCount': guildCount
            })
            headers = {
                'Authorization': self.bot.others['discordextremelist'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://api.discordextremelist.xyz/v2/bot/{}/stats'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('DiscordExtremeList returned {} for {}'.format(resp.status, payload))
                answers[4] = resp.status
        except Exception as e:
            answers[4] = "0"
            await self.bot.get_cog("Errors").on_error(e,None)
        await session.close()
        answers = [str(x) for x in answers]
        emb = self.bot.get_cog("Embeds").Embed(desc='**Guilds count updated** in {}s ({})'.format(round(time.time()-t,3),'-'.join(answers)),color=7229109).update_timestamp().set_author(self.bot.user)
        await self.bot.get_cog("Embeds").send([emb],url="loop")
        self.dbl_last_sending = datetime.datetime.now()

    async def partners_loop(self):
        """Update partners channels (every 7 hours)"""
        t = time.time()
        self.partner_last_check = datetime.datetime.now()
        channels_list = await self.bot.get_cog('Servers').get_server(criters=["`partner_channel`<>''"],columns=['ID','partner_channel','partner_color'])
        self.bot.log.info("[Partners] Rafraîchissement des salons ({} serveurs prévus)...".format(len(channels_list)))
        count = [0,0]
        for guild in channels_list:
            try:
                chan = guild['partner_channel'].split(';')[0]
                if not chan.isnumeric():
                    continue
                chan = self.bot.get_channel(int(chan))
                if chan is None:
                    continue
                count[0] += 1
                count[1] += await self.bot.get_cog('Partners').update_partners(chan,guild['partner_color'])
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,None)
        emb = self.bot.get_cog("Embeds").Embed(desc='**Partners channels updated** in {}s ({} channels - {} partners)'.format(round(time.time()-t,3),count[0],count[1]),color=10949630).update_timestamp().set_author(self.bot.user)
        await self.bot.get_cog("Embeds").send([emb],url="loop")
        
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
            await self.bot.get_cog('Errors').senf_err_msg("Translators backup: Unable to find backup folder")
            return
        emb = self.bot.get_cog("Embeds").Embed(desc='**Translations files backup** completed in {}s'.format(round(time.time()-t,3)),color=10197915).update_timestamp().set_author(self.bot.user)
        await self.bot.get_cog("Embeds").send([emb],url="loop")    

    async def send_sql_statslogs(self):
        "Send some stats about the current bot stats"
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        rss_feeds = await self.bot.get_cog("Rss").get_raws_count(True)
        active_rss_feeds = await self.bot.get_cog("Rss").get_raws_count()
        if infoCog := self.bot.get_cog("Info"):
            member_count, bot_count = infoCog.get_users_nber(list())
        else:
            member_count = len(self.bot.users)
            bot_count = len([1 for x in self.bot.users if x.bot])
        lang_stats = await self.bot.get_cog('Servers').get_languages([], return_dict=True)
        rankcards_stats = await self.bot.get_cog('Users').get_rankcards_stats()
        xptypes_stats = await self.bot.get_cog('Servers').get_xp_types([], return_dict=True)
        supportserver_members = self.bot.get_guild(356067272730607628).member_count
        query = "INSERT INTO `log_stats` (`servers_count`, `members_count`, `bots_count`, `dapi_heartbeat`, `codelines_count`, `earned_xp_total`, `rss_feeds`, `active_rss_feeds`, `supportserver_members`, `languages`, `used_rankcards`, `xp_types`, `beta`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        data = (len(self.bot.guilds),
            member_count,
            bot_count,
            round(self.bot.latency,3),
            self.bot.get_cog("Info").codelines,
            await self.bot.get_cog('Xp').bdd_total_xp(),
            rss_feeds,
            active_rss_feeds,
            supportserver_members,
            marshal.dumps(lang_stats),
            marshal.dumps(rankcards_stats),
            marshal.dumps(xptypes_stats),
            int(self.bot.beta),
        )
        try:
            cursor.execute(query, data)
        except Exception as e:
            await self.bot.get_cog("Errors").senf_err_msg(query)
            raise e
        cnx.commit()
        cursor.close()
        emb = self.bot.get_cog("Embeds").Embed(desc='**Stats logs** updated',color=5293283).update_timestamp().set_author(self.bot.user)
        await self.bot.get_cog("Embeds").send([emb],url="loop")
        self.statslogs_last_push = datetime.datetime.now()
        

def setup(bot):
    bot.add_cog(Events(bot))
    if bot.internal_loop_enabled:
        try:
            bot.get_cog("Events").loop.start()
        except RuntimeError:
            pass
