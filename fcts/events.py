import asyncio
import datetime
import json
import random
import re
import time

import aiohttp
import discord
from discord.ext import commands, tasks

from libs.bot_classes import SUPPORT_GUILD_ID, Axobot


class Events(commands.Cog):
    """Cog for the management of major events that do not belong elsewhere. Like when a new server invites the bot."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "events"
        self.dbl_last_sending = datetime.datetime.utcfromtimestamp(0)
        self.statslogs_last_push = datetime.datetime.utcfromtimestamp(0)
        self.loop_errors = [0,datetime.datetime.utcfromtimestamp(0)]
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
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a guild"""
        await self.send_guild_log(guild,"join")
        await self.send_guild_count_milestone()
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

    async def send_guild_count_milestone(self):
        "Check the number of guilds and send a message if it's a milestone"
        guilds_count = len(self.bot.guilds)
        if guilds_count % 100 != 0:
            return
        if channel := self.bot.get_channel(625318973164093457):
            await channel.send(f"Nous venons d'atteindre les **{guilds_count} serveurs** ! :tada:")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        """Called for each new message because it's cool"""
        if self.bot.zombie_mode:
            return
        if msg.guild is None and not msg.flags.ephemeral:
            await self.send_mp(msg)
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
        msg_content = msg.content if len(msg.content) < 1900 else msg.content[:1900] + "…"
        text = "{} **{}** ({} - {})\n{}".format(arrow, recipient, recipient.id, date_, msg_content)
        if len(msg.attachments) > 0:
            text += "".join(["\n{}".format(x.url) for x in msg.attachments])
        await channel.send(text, embed=emb)

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
        guild = self.bot.get_guild(SUPPORT_GUILD_ID.id)
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
        except Exception as err:
            if member.guild.id != 264445053596991498:
                self.bot.log.warning("[check_user_left] %s (user %s/server %s)", err, member.id, member.guild.id)

    @tasks.loop(seconds=1.0)
    async def loop(self):
        """Main loop of the bot"""
        if not self.bot.internal_loop_enabled:
            return
        try:
            now = datetime.datetime.now()
            # Timed tasks - every 20s
            if now.second%20 == 0 and self.bot.database_online:
                await self.bot.task_handler.check_tasks()
            # Clear old rank cards - every 20min
            elif now.minute%20 == 0 and self.bot.database_online:
                await self.bot.get_cog('Xp').clear_cards()
            # Bots lists updates - every day
            elif now.hour == 0 and now.day != self.dbl_last_sending.day:
                await self.dbl_send_data()
            # Send stats logs - every 1h (start from 0:05 am)
            elif now.minute > 5 and (now.day != self.statslogs_last_push.day or now.hour != self.statslogs_last_push.hour) and self.bot.database_online:
                await self.send_sql_statslogs()
        except Exception as err:
            self.bot.dispatch("error", err)
            self.loop_errors[0] += 1
            if (datetime.datetime.now() - self.loop_errors[1]).total_seconds() > 120:
                self.loop_errors[0] = 0
                self.loop_errors[1] = datetime.datetime.now()
            if self.loop_errors[0] > 10:
                await self.bot.get_cog('Errors').senf_err_msg(":warning: **Too many errors: STOPPING THE MAIN LOOP** <@279568324260528128> :warning:")
                self.loop.cancel() # pylint: disable=no-member

    @loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        self.bot.log.info("[tasks_loop] Starting one loop iteration")

    async def dbl_send_data(self):
        """Send guilds count to Discord Bots Lists"""
        if self.bot.beta:
            return
        start_time = time.time()
        answers: list[str] = []
        self.bot.log.info("Sending server count to bots lists APIs...")
        try:
            guild_count = await self.bot.get_cog("BotInfo").get_guilds_count()
        except Exception as err:
            self.bot.dispatch("error", err, "Fetching guild count")
            guild_count = len(self.bot.guilds)
        session = aiohttp.ClientSession(loop=self.bot.loop)
        try:# https://top.gg/bot/1048011651145797673
            payload = {"server_count": guild_count}
            headers={
                "Authorization": self.bot.dbl_token
            }
            async with session.post(f"https://top.gg/api/bots/{self.bot.user.id}/stats", json=payload, headers=headers) as resp:
                self.bot.log.debug(f"top.gg returned {resp.status} for {payload}")
                answers.append(f"top.gg: {resp.status}")
        except Exception as err:
            answers.append("top.gg: 0")
            self.bot.dispatch("error", err, "Sending server count to top.gg")
        if self.bot.entity_id == 2:
            try: # https://discordbotlist.com/api/v1/bots/1048011651145797673/stats
                payload = {
                    "guilds": guild_count
                }
                headers = {
                    "Authorization": self.bot.others["discordbotlist_axobot"],
                }
                async with session.post(f"https://discordbotlist.com/api/v1/bots/{self.bot.user.id}/stats",
                                        json=payload, headers=headers) as resp:
                    self.bot.log.debug(f"discordbotlist returned {resp.status} for {payload}")
                    answers.append(f"discordbotlist: {resp.status}")
            except Exception as err:
                answers.append("discordbotlist: 0")
                self.bot.dispatch("error", err, "Sending server count to discordbotlist")
        await session.close()
        answers = ' - '.join(answers)
        delta_time = round(time.time()-start_time, 3)
        emb = discord.Embed(description=f"**Guilds count updated** in {delta_time}s\n{answers}", color=7229109, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")
        self.dbl_last_sending = datetime.datetime.now()

    async def send_sql_statslogs(self):
        "Send some stats about the current bot stats"
        await self.bot.wait_until_ready()
        if self.bot.get_cog("Rss") is None:
            return
        rss_feeds = await self.bot.get_cog("Rss").db_get_raws_count(get_disabled=True)
        active_rss_feeds = await self.bot.get_cog("Rss").db_get_raws_count()
        if infoCog := self.bot.get_cog("BotInfo"):
            member_count, bot_count = infoCog.get_users_nber([])
            codelines: int = infoCog.codelines
        else:
            member_count = len(self.bot.users)
            bot_count = len([1 for x in self.bot.users if x.bot])
            codelines = 0
        lang_stats = await self.bot.get_cog('ServerConfig').get_languages([])
        rankcards_stats = await self.bot.get_cog('Users').get_rankcards_stats()
        xptypes_stats = await self.bot.get_cog('ServerConfig').get_xp_types([])
        supportserver_members = self.bot.get_guild(SUPPORT_GUILD_ID.id).member_count
        query = "INSERT INTO `log_stats` (`servers_count`, `members_count`, `bots_count`, `dapi_heartbeat`, `codelines_count`, `earned_xp_total`, `rss_feeds`, `active_rss_feeds`, `supportserver_members`, `languages_json`, `used_rankcards_json`, `xp_types_json`, `entity_id`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        data = (
            len(self.bot.guilds),
            member_count,
            bot_count,
            10e6 if self.bot.latency == float("inf") else round(self.bot.latency, 3),
            codelines,
            await self.bot.get_cog('Xp').db_get_total_xp(),
            rss_feeds,
            active_rss_feeds,
            supportserver_members,
            json.dumps(lang_stats),
            json.dumps(rankcards_stats),
            json.dumps(xptypes_stats),
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


async def setup(bot):
    await bot.add_cog(Events(bot))
