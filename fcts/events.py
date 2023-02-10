import asyncio
import datetime
import json
import marshal
import random
import re
import time
from typing import Optional

import aiohttp
import discord
import mysql
from discord.ext import commands, tasks

from libs.bot_classes import MyContext, Axobot
from libs.enums import UsernameChangeRecord


class Events(commands.Cog):
    """Cog for the management of major events that do not belong elsewhere. Like when a new server invites the bot."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "events"
        self.dbl_last_sending = datetime.datetime.utcfromtimestamp(0)
        self.last_eventDay_check = datetime.datetime.utcfromtimestamp(0)
        self.statslogs_last_push = datetime.datetime.utcfromtimestamp(0)
        self.loop_errors = [0,datetime.datetime.utcfromtimestamp(0)]
        self.last_membercounter = datetime.datetime.utcfromtimestamp(0)
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

    async def cog_load(self):
        if self.bot.internal_loop_enabled:
            self.loop.start() # pylint: disable=no-member


    async def cog_unload(self):
        # pylint: disable=no-member
        if self.loop.is_running():
            self.loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        "Send a first log on connect"
        if self.bot.database_online:
            await asyncio.sleep(0.1)
            await self.send_sql_statslogs()


    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Called when a member change something (status, activity, nickame, roles)"""
        if before.nick != after.nick and await self.can_register_memberlog(before.id, before.guild.id):
            await self.register_memberlog_name(before, after)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        """Called when a user change something (avatar, username, discrim)"""
        if before.name != after.name and await self.can_register_memberlog(before.id):
            await self.register_userlog_name(before, after)
    
    async def can_register_memberlog(self, user_id: int, guild_id: Optional[int]=None):
        "Check if we are allowed to register a memberlog (if database is online, if the user has allowed it, if the server hasn't disabled it)"
        if not self.bot.database_online:
            return False
        # If axobot is already there, let it handle it
        if guild_id and await self.bot.check_axobot_presence(guild_id=guild_id):
            return
        config_option = await self.bot.get_cog('Utilities').get_db_userinfo(['allow_usernames_logs'],["userID=" + str(user_id)])
        if config_option is not None and config_option['allow_usernames_logs'] is False:
            return False
        if guild_id:
            return await self.bot.get_config(guild_id, "nicknames_history")
        return True

    async def register_memberlog_name(self, before: discord.Member, after: discord.Member, tries:int=0):
        "Save in our database when a user change its nickname"
        if tries > 5:
            self.bot.dispatch("error", RuntimeError(f"Nickname change failed after 5 attempts for user {before.id}"))
            return
        before_nick = '' if before.nick is None else before.nick
        after_nick = '' if after.nick is None else after.nick
        try:
            await self.db_register_memberlog(before.id, before_nick, after_nick, before.guild.id)
        except mysql.connector.errors.IntegrityError as err:
            self.bot.log.warning(err)
            await self.register_memberlog_name(before, after, tries+1)

    async def register_userlog_name(self, before: discord.User, after: discord.User, tries:int=0):
        "Save in our database when a user change its username"
        if tries > 5:
            self.bot.dispatch("error", RuntimeError(f"Nickname change failed after 5 attempts for user {before.id}"))
            return
        before_nick = '' if before.name is None else before.name
        after_nick = '' if after.name is None else after.name
        try:
            await self.db_register_memberlog(before.id, before_nick, after_nick)
        except mysql.connector.errors.IntegrityError as err:
            self.bot.log.warning(err)
            await self.register_userlog_name(before, after, tries+1)

    async def db_register_memberlog(self, user_id: int, before: str, after: str, guild_id: int=0):
        query = "INSERT INTO `usernames_logs` (`user`,`old`,`new`,`guild`,`beta`) VALUES (%(u)s, %(o)s, %(n)s, %(g)s, %(b)s)"
        query_args = { 'u': user_id, 'o': before, 'n': after, 'g': guild_id, 'b': self.bot.beta }
        async with self.bot.db_query(query, query_args):
            self.bot.dispatch("username_change_record", UsernameChangeRecord(
                before or None,
                after or None,
                is_in_guild=guild_id != 0,
                user=self.bot.get_user(user_id)
            ))


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
        await self.bot.wait_until_ready()
        try:
            if log_type == "join":
                self.bot.log.info(f"Bot joined the server {guild.id}")
                desc = f"Bot **joined the server** {guild.name} ({guild.id}) - {len(guild.members)} users"
            else:
                self.bot.log.info(f"Bot left the server {guild.id}")
                if guild.name is None and guild.unavailable:
                    desc = f"Bot **may have left** the server {guild.id} (guild unavailable)"
                else:
                    desc = f"Bot **left the server** {guild.name} ({guild.id}) - {len(guild.members)} users"
                    if guild.me and guild.me.joined_at:
                        desc += f"\nJoined at <t:{guild.me.joined_at.timestamp():.0f}>"
            emb = discord.Embed(description=desc, color=self.embed_colors['welcome'], timestamp=self.bot.utcnow())
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)
            if self.bot.database_online:
                await self.send_sql_statslogs()
        except Exception as err:
            self.bot.dispatch('error', err, None)


    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Called for each new message because it's cool"""
        if self.bot.zombie_mode:
            return
        # If axobot is already there, don't do anything
        if msg.guild and await self.bot.check_axobot_presence(guild=msg.guild):
            return
        if msg.guild is None and not msg.flags.ephemeral:
            await self.send_mp(msg)
        if msg.author != self.bot.user:
            await self.bot.get_cog('Info').emoji_analysis(msg)
        if "send nudes" in msg.content.lower() and len(msg.content)<13 and random.random() > 0.0:
            try:
                nudes_reacts = [':eyes:',':innocent:',':rolling_eyes:',':confused:',':smirk:']
                if msg.guild is None or msg.channel.permissions_for(msg.guild.me).external_emojis:
                    nudes_reacts += ['<:whut:485924115199426600>','<:thinksmart:513105826530197514>','<:excusemewhat:418154673523130398>','<:blobthinking:499661417012527104>','<a:ano_U:568494122856611850>','<:catsmirk:523929843331498015>','<a:ablobno:537680872820965377>']
                await msg.channel.send(random.choice(nudes_reacts))
            except discord.HTTPException:
                pass
        if not msg.author.bot:
            cond = False
            if self.bot.database_online:
                cond: bool = await self.bot.get_config(msg.guild, "anti_caps_lock")
            if cond:
                clean_content = msg.content
                for rgx_match in (r'\|', r'\*', r'_', r'<a?:\w+:\d+>', r'<(#|@&?!?)\d+>', r'https?://\w+\.\S+'):
                    clean_content = re.sub(rgx_match, '', clean_content)
                clean_content = clean_content.replace(' ', '')
                if len(clean_content) > 0 and sum(1 for c in clean_content if c.isupper())/len(clean_content) > 0.8 and len(clean_content)>7 and not msg.channel.permissions_for(msg.author).administrator:
                    try:
                        await msg.channel.send(await self.bot._(msg.guild, "moderation.caps-lock", user=msg.author.mention), delete_after=4.0)
                    except discord.HTTPException:
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
            await self.bot.fetch_invite(msg.content)
        except discord.NotFound:
            return
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
            channel: Optional[discord.TextChannel] = await self.bot.get_config(guild.id, "modlogs_channel")
        except Exception as err:
            self.bot.dispatch("error", err)
            return
        if channel is None:
            return
        emb = discord.Embed(description=message, color=color, timestamp=self.bot.utcnow())
        if fields:
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
        "Check if someone has been kicked or banned by the bot"
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
            utcnow = self.bot.utcnow()
            # Timed tasks - every 20s
            if now.second%20 == 0 and self.bot.database_online:
                await self.bot.task_handler.check_tasks()
            # Clear old rank cards - every 20min
            elif now.minute%20 == 0 and self.bot.database_online:
                await self.bot.get_cog('Xp').clear_cards()
            # Bots lists updates - every day
            elif now.hour == 0 and now.day != self.dbl_last_sending.day:
                await self.dbl_send_data()
            # Check current event - every 12h UTC (start from 0:02 am)
            elif utcnow.hour%12 == 0 and utcnow.minute%2 == 0 and (now.hour != self.last_eventDay_check.hour or now.day != self.last_eventDay_check.day):
                await self.botEventLoop()
            # Send stats logs - every 1h (start from 0:05 am)
            elif now.minute > 5 and (now.day != self.statslogs_last_push.day or now.hour != self.statslogs_last_push.hour) and self.bot.database_online:
                await self.send_sql_statslogs()
            # Refresh needed membercounter channels - every 1min
            elif abs((self.last_membercounter - now).total_seconds()) > 60 and self.bot.database_online:
                await self.bot.get_cog('ServerConfig').update_everyMembercounter()
                self.last_membercounter = now
        except Exception as err:
            self.bot.dispatch("error", err)
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

    async def botEventLoop(self):
        "Refresh the current bot event every once in a while"
        self.bot.get_cog("BotEvents").update_current_event()
        event = self.bot.get_cog("BotEvents").current_event
        emb = discord.Embed(description=f'**Bot event** updated (current event is {event})', color=1406147, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")
        self.last_eventDay_check = datetime.datetime.today()

    async def dbl_send_data(self):
        """Send guilds count to Discord Bots Lists"""
        if self.bot.beta:
            return
        t = time.time()
        answers = ['None' for _ in range(3)]
        self.bot.log.info("Sending server count to bots lists APIs...")
        try:
            guild_count = await self.bot.get_cog('Info').get_guilds_count()
        except Exception as err:
            self.bot.dispatch("error", err, "Fetching guild count")
            guild_count = len(self.bot.guilds)
        session = aiohttp.ClientSession(loop=self.bot.loop)
        try:# https://top.gg/bot/486896267788812288
            payload = {'server_count': guild_count}
            headers={
                'Authorization': self.bot.dbl_token
            }
            async with session.post(f'https://top.gg/api/bots/{self.bot.user.id}/stats' ,data=payload, headers=headers) as resp:
                self.bot.log.debug(f'top.gg returned {resp.status} for {payload}')
                answers[0] = resp.status
        except Exception as err:
            answers[0] = "0"
            self.bot.dispatch("error", err, "Sending server count to top.gg")
        if self.bot.entity_id == 0:
            try: # https://bots.ondiscord.xyz/bots/486896267788812288
                payload = json.dumps({
                    'guildCount': guild_count
                })
                headers = {
                    'Authorization': self.bot.others['botsondiscord'],
                    'Content-Type': 'application/json'
                }
                async with session.post(f'https://bots.ondiscord.xyz/bot-api/bots/{self.bot.user.id}/guilds', data=payload, headers=headers) as resp:
                    self.bot.log.debug(f'BotsOnDiscord returned {resp.status} for {payload}')
                    answers[1] = resp.status
            except Exception as err:
                answers[1] = "0"
                self.bot.dispatch("error", err, "Sending server count to BotsOnDiscord")
            try: # https://api.discordextremelist.xyz/v2/bot/486896267788812288/stats
                payload = json.dumps({
                    'guildCount': guild_count
                })
                headers = {
                    'Authorization': self.bot.others['discordextremelist'],
                    'Content-Type': 'application/json'
                }
                async with session.post(f'https://api.discordextremelist.xyz/v2/bot/{self.bot.user.id}/stats', data=payload, headers=headers) as resp:
                    self.bot.log.debug(f'DiscordExtremeList returned {resp.status} for {payload}')
                    answers[2] = resp.status
            except Exception as err:
                answers[2] = "0"
                self.bot.dispatch("error", err, "Sending server count to DiscordExtremeList")
        await session.close()
        answers = '-'.join(str(x) for x in answers)
        delta_time = round(time.time()-t, 3)
        emb = discord.Embed(description=f'**Guilds count updated** in {delta_time}s ({answers})', color=7229109, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")
        self.dbl_last_sending = datetime.datetime.now()

    async def send_sql_statslogs(self):
        "Send some stats about the current bot stats"
        await self.bot.wait_until_ready()
        if self.bot.get_cog("Rss") is None:
            return
        rss_feeds = await self.bot.get_cog("Rss").db_get_raws_count(True)
        active_rss_feeds = await self.bot.get_cog("Rss").db_get_raws_count()
        if infoCog := self.bot.get_cog("Info"):
            member_count, bot_count = infoCog.get_users_nber(list())
        else:
            member_count = len(self.bot.users)
            bot_count = len([1 for x in self.bot.users if x.bot])
        lang_stats = await self.bot.get_cog('ServerConfig').get_languages([])
        rankcards_stats = await self.bot.get_cog('Users').get_rankcards_stats()
        xptypes_stats = await self.bot.get_cog('ServerConfig').get_xp_types([])
        supportserver_members = self.bot.get_guild(356067272730607628).member_count
        query = "INSERT INTO `log_stats` (`servers_count`, `members_count`, `bots_count`, `dapi_heartbeat`, `codelines_count`, `earned_xp_total`, `rss_feeds`, `active_rss_feeds`, `supportserver_members`, `languages`, `used_rankcards`, `xp_types`, `entity_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        data = (
            len(self.bot.guilds),
            member_count,
            bot_count,
            10e6 if self.bot.latency == float("inf") else round(self.bot.latency, 3),
            self.bot.get_cog("Info").codelines,
            await self.bot.get_cog('Xp').bdd_total_xp(),
            rss_feeds,
            active_rss_feeds,
            supportserver_members,
            marshal.dumps(lang_stats),
            marshal.dumps(rankcards_stats),
            marshal.dumps(xptypes_stats),
            self.bot.entity_id,
        )
        try:
            async with self.bot.db_query(query, data):
                pass
        except Exception as err:
            await self.bot.get_cog("Errors").senf_err_msg(query)
            raise err
        emb = discord.Embed(description='**Stats logs** updated', color=5293283, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")
        self.statslogs_last_push = datetime.datetime.now()


    @commands.Cog.listener()
    async def on_command_completion(self, ctx: MyContext):
        "If a command is executed with Zbot, remind the user to invite Axobot instead"
        class MigrationView(discord.ui.View):
            def __init__(self):
                super().__init__()
                self.add_item(discord.ui.Button(label='Invite Axobot', url="https://zrunner.me/invite-axobot", style=discord.ButtonStyle.blurple))
                self.add_item(discord.ui.Button(label='About the migration', url="https://zbot.readthedocs.io/en/release-candidate/v4.html#new-identity"))
                self.add_item(discord.ui.Button(label='Support server', url="https://discord.gg/N55zY88"))
        
        if self.bot.entity_id == 0 and random.random() < 0.1:
            txt = """Hey, Zbot is currently changing its identity to **Axobot**!

During the migration period, Zbot will continue to work, but will **receive updates later** than Axobot and may not work as well.
Luckily for you, **the migration is very quick**, just invite Axobot and give it the same roles as Zbot to avoid any service interruption!"""
            emb = discord.Embed(title="Zbot is becoming Axobot!", description=txt, color=0x00ff00)
            emb.set_thumbnail(url="https://zrunner.me/axolotl.png")
            await ctx.send(embed=emb, view=MigrationView())


async def setup(bot):
    await bot.add_cog(Events(bot))
