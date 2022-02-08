import asyncio
import datetime
import json
import marshal
import random
import re
import shutil
import time

import aiohttp
import discord
import mysql
import psutil
from discord.ext import commands, tasks
from libs.classes import Zbot

from fcts.checks import is_fun_enabled


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
        if self.bot.internal_loop_enabled:
            self.loop.start() # pylint: disable=no-member


    def cog_unload(self):
        self.loop.cancel() # pylint: disable=no-member

    @commands.Cog.listener()
    async def on_ready(self):
        "Send a first log on connect"
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
        if isinstance(before, discord.Member):
            before_nick = '' if before.nick is None else before.nick
            after_nick = '' if after.nick is None else after.nick
        else:
            before_nick = '' if before.name is None else before.name
            after_nick = '' if after.name is None else after.name
        guild = before.guild.id if hasattr(before, 'guild') else 0
        query = "INSERT INTO `usernames_logs` (`user`,`old`,`new`,`guild`,`beta`) VALUES (%(u)s,%(o)s,%(n)s,%(g)s,%(b)s)"
        query_args = { 'u': before.id, 'o': before_nick, 'n': after_nick, 'g': guild, 'b': self.bot.beta }
        try:
            async with self.bot.db_query(query, query_args):
                pass
        except mysql.connector.errors.IntegrityError as err:
            self.bot.log.warning(err)
            await self.updade_memberslogs_name(before, after, tries+1)

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

    async def send_guild_log(self, guild: discord.Guild, log_type: str):
        """Send a log to the logging channel when the bot joins/leave a guild"""
        try:
            if log_type == "join":
                self.bot.log.info("Bot joined the server {}".format(guild.id))
                desc = "Bot **joined the server** {} ({}) - {} users".format(guild.name,guild.id,len(guild.members))
            else:
                self.bot.log.info("Bot left the server {}".format(guild.id))
                if guild.name is None and guild.unavailable:
                    desc = "Bot **may have left** the server {} (guild unavailable)".format(guild.id)
                else:
                    desc = "Bot **left the server** {} ({}) - {} users".format(guild.name,guild.id,len(guild.members))
            emb = discord.Embed(description=desc, color=self.embed_colors['welcome'], timestamp=self.bot.utcnow())
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed([emb])
            if self.bot.database_online:
                await self.send_sql_statslogs()
        except Exception as err:
            await self.bot.get_cog("Errors").on_error(err,None)


    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Called for each new message because it's cool"""
        if self.bot.zombie_mode:
            return
        if msg.guild is None and not msg.flags.ephemeral:
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
            except discord.HTTPException:
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
        "Send DM logs to the super secret internal channel"
        await self.check_mp_adv(msg)
        recipient = await self.bot.get_recipient(msg.channel)
        if recipient is None:
            return
        if recipient.id in {392766377078816789,279568324260528128,552273019020771358,281404141841022976}:
            return
        channel = self.bot.get_channel(625320165621497886)
        if channel is None:
            return self.bot.log.warning("[send_mp] Salon de MP introuvable")
        emb = msg.embeds[0] if len(msg.embeds) > 0 else None
        arrow = ":inbox_tray:" if msg.author == recipient else ":outbox_tray:"
        date_ = f"<t:{msg.created_at.timestamp():.0f}>"
        text = "{} **{}** ({} - {})\n{}".format(arrow, recipient, recipient.id, date_, msg.content)
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


    async def send_logs_per_server(self, guild: discord.Guild, log_type:str, message: str, author: discord.User=None, fields: list[dict]=None):
        """Send a log in a server. `log_type` is used to define the color of the embed"""
        if self.bot.zombie_mode:
            return
        if not self.bot.database_online:
            return
        color = self.embed_colors[log_type.lower()]
        try:
            config = str(await self.bot.get_config(guild.id,"modlogs_channel")).split(';', maxsplit=1)[0]
            if config == "" or not config.isnumeric():
                return
            channel = guild.get_channel(int(config))
        except Exception as err:
            await self.bot.get_cog("Errors").on_error(err,None)
            return
        if channel is None:
            return
        emb = discord.Embed(description=message, color=color, timestamp=self.bot.utcnow())
        for field in fields:
            emb.add_field(**field)
        if author is not None:
            emb.set_author(name=author, icon_url=author.display_avatar)
        try:
            await channel.send(embed=emb)
        except discord.Forbidden:
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

    @tasks.loop(seconds=1.0)
    async def loop(self):
        if not self.bot.internal_loop_enabled:
            return
        try:
            now = datetime.datetime.now()
            # Timed tasks - every 20s
            if now.second%20 == 0 and self.bot.database_online:
                await self.bot.task_handler.check_tasks()
            # Latency usage - every 30s
            if now.second%30 == 0:
                await self.status_loop(now)
            # Clear old rank cards - every 20min
            elif now.minute%20 == 0 and self.bot.database_online:
                await self.bot.get_cog('Xp').clear_cards()
            # Partners reload - every 7h (start from 1am)
            elif now.hour%7 == 1 and now.hour != self.partner_last_check.hour and self.bot.database_online:
                await self.partners_loop()
            # Bots lists updates - every day
            elif now.hour == 0 and now.day != self.dbl_last_sending.day:
                await self.dbl_send_data()
            # Translation backup - every 12h (start from 1am)
            elif now.hour%12 == 1 and (now.hour != self.last_tr_backup.hour or now.day != self.last_tr_backup.day):
                await self.translations_backup()
            # Check current event - every 12h (start from 0:02 am)
            elif int(now.hour)%12 == 0 and int(now.minute)%2 == 0 and (now.hour != self.last_eventDay_check.hour or now.day != self.last_eventDay_check.day):
                await self.botEventLoop()
            # Send stats logs - every 1h (start from 0:05 am)
            elif now.minute > 5 and (now.day != self.statslogs_last_push.day or now.hour != self.statslogs_last_push.hour) and self.bot.database_online:
                await self.send_sql_statslogs()
            # Refresh needed membercounter channels - every 1min
            elif abs((self.last_membercounter - now).total_seconds()) > 60 and self.bot.database_online:
                await self.bot.get_cog('Servers').update_everyMembercounter()
                self.last_membercounter = now
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
        emb = discord.Embed(description=f'**Bot event** updated (current event is {e})', color=1406147, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed([emb], url="loop")
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
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,None)
            guildCount = len(self.bot.guilds)
        session = aiohttp.ClientSession(loop=self.bot.loop)
        try:# https://top.gg/bot/486896267788812288
            payload = {'server_count': guildCount}
            async with session.post('https://top.gg/api/bots/486896267788812288/stats',data=payload,headers={'Authorization':str(self.bot.dbl_token)}) as resp:
                self.bot.log.debug('top.gg returned {} for {}'.format(resp.status, payload))
                answers[0] = resp.status
        except Exception as err:
            answers[0] = "0"
            await self.bot.get_cog("Errors").on_error(err,None)
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
        except Exception as err:
            answers[1] = "0"
            await self.bot.get_cog("Errors").on_error(err,None)
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
        except Exception as err:
            answers[2] = "0"
            await self.bot.get_cog("Errors").on_error(err,None)
        try: # https://discord.boats/bot/486896267788812288
            headers = {
                'Authorization': self.bot.others['discordboats'],
                'Content-Type': 'application/json'
            }
            async with session.post('https://discord.boats/api/bot/{}'.format(self.bot.user.id), data=payload, headers=headers) as resp:
                self.bot.log.debug('discord.boats returned {} for {}'.format(resp.status, payload))
                answers[3] = resp.status
        except Exception as err:
            answers[3] = "0"
            await self.bot.get_cog("Errors").on_error(err,None)
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
        except Exception as err:
            answers[4] = "0"
            await self.bot.get_cog("Errors").on_error(err,None)
        await session.close()
        answers = '-'.join(str(x) for x in answers)
        delta_time = round(time.time()-t,3)
        emb = discord.Embed(description=f'**Guilds count updated** in {delta_time}s ({answers})', color=7229109, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed([emb], url="loop")
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
            except Exception as err:
                await self.bot.get_cog('Errors').on_error(err,None)
        delta_time = round(time.time()-t,3)
        emb = discord.Embed(
            description=f'**Partners channels updated** in {delta_time}s ({count[0]} channels - {count[1]} partners)',
            color=10949630,
            timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed([emb], url="loop")

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
        delta_time = round(time.time()-t,3)
        emb = discord.Embed(description=f'**Translations files backup** completed in {delta_time}s', color=10197915, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed([emb], url="loop")

    async def send_sql_statslogs(self):
        "Send some stats about the current bot stats"
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
            async with self.bot.db_query(query, data):
                pass
        except Exception as err:
            await self.bot.get_cog("Errors").senf_err_msg(query)
            raise err
        emb = discord.Embed(description='**Stats logs** updated', color=5293283, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed([emb], url="loop")
        self.statslogs_last_push = datetime.datetime.now()


def setup(bot):
    bot.add_cog(Events(bot))
