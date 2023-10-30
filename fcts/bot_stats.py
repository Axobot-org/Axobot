import math
import re
import time
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional, TypedDict, Union

import aiohttp
import discord
import mysql
import psutil
from discord.ext import commands, tasks

from fcts.tickets import TicketCreationEvent
from libs.bot_classes import Axobot, MyContext
from libs.enums import ServerWarningType, UsernameChangeRecord

try:
    import orjson  # type: ignore
except ModuleNotFoundError:
    import json
    json_loads = json.loads
else:
    json_loads = orjson.loads


async def get_ram_data():
    data = psutil.virtual_memory()
    return data.percent, (data.total - data.available)

class RssStats(TypedDict):
    "RSS-loop-related stats"
    checked: int
    messages: int
    errors: int
    warnings: int
    time: int


class BotStats(commands.Cog):
    "Send internal stats to our database"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'bot_stats'
        self.received_events = {'CMD_USE': 0}
        self.commands_uses: dict[str, int] = {}
        self.app_commands_uses: dict[str, int] = {}
        self.rss_stats: RssStats = {'checked': 0, 'messages': 0, 'errors': 0, 'warnings': 0, 'time': 0}
        self.rss_loop_finished = False
        self.xp_cards = {'generated': 0, 'sent': 0}
        self.process = psutil.Process()
        self.bot_cpu_records: list[float] = []
        self.total_cpu_records: list[float] = []
        self.latency_records: list[int] = []
        self.statuspage_header = {"Content-Type": "application/json", "Authorization": "OAuth " + self.bot.others["statuspage"]}
        self.antiscam = {"warning": 0, "deletion": 0}
        self.ticket_events = {"creation": 0}
        self.usernames = {"guild": 0, "user": 0, "deleted": 0}
        self.emitted_serverlogs: dict[str, int] = {}
        self.serverlogs_audit_search: Optional[tuple[int, int]] = None
        self.last_backup_size: Optional[int] = None
        self.role_reactions = {"added": 0, "removed": 0}
        self.snooze_events: dict[tuple[int, int], int] = defaultdict(int)
        self.stream_events: dict[str, int] = defaultdict(int)
        self.voice_transcript_events: dict[tuple[float, float], int] = defaultdict(int)

    async def cog_load(self):
         # pylint: disable=no-member
        self.sql_loop.start()
        self.record_cpu_usage.start()
        self.record_ws_latency.start()
        self.status_loop.start()
        self.heartbeat_loop.start()

    async def cog_unload(self):
         # pylint: disable=no-member
        self.sql_loop.cancel()
        self.record_cpu_usage.cancel()
        self.record_ws_latency.cancel()
        self.status_loop.stop()
        self.heartbeat_loop.stop()

    @property
    def emoji_table(self):
        return 'emojis_beta' if self.bot.beta else 'emojis'

    @tasks.loop(seconds=10)
    async def record_cpu_usage(self):
        "Record the CPU usage for later use"
        self.bot_cpu_records.append(self.process.cpu_percent())
        if len(self.bot_cpu_records) > 6:
            # if the list becomes too long (over 1min), cut it
            self.bot_cpu_records = self.bot_cpu_records[-6:]
        self.total_cpu_records.append(psutil.cpu_percent())
        if len(self.total_cpu_records) > 6:
            # if the list becomes too long (over 1min), cut it
            self.total_cpu_records = self.total_cpu_records[-6:]

    @record_cpu_usage.error
    async def on_record_cpu_error(self, error: Exception):
        self.bot.dispatch("error", error, "When collecting CPU usage")

    @tasks.loop(seconds=20)
    async def record_ws_latency(self):
        "Record the websocket latency for later use"
        if self.bot.latency is None or math.isnan(self.bot.latency):
            return
        try:
            self.latency_records.append(round(self.bot.latency*1000))
        except OverflowError: # Usually because latency is infinite
            self.latency_records.append(10e6)
        if len(self.latency_records) > 3:
            # if the list becomes too long (over 1min), cut it
            self.latency_records = self.latency_records[-3:]

    @record_ws_latency.error
    async def on_record_latency_error(self, error: Exception):
        self.bot.dispatch("error", error, "When collecting WS latency")

    async def get_list_usage(self, origin: list):
        "Calculate the average list value"
        if len(origin) > 0:
            avg = round(sum(origin)/len(origin), 1)
            return avg

    @commands.Cog.listener()
    async def on_antiscam_warn(self, *_args):
        self.antiscam["warning"] += 1

    @commands.Cog.listener()
    async def on_antiscam_delete(self, *_args):
        self.antiscam["deletion"] += 1

    @commands.Cog.listener()
    async def on_ticket_creation(self, _event: TicketCreationEvent):
        self.ticket_events["creation"] += 1

    @commands.Cog.listener()
    async def on_username_change_record(self, event: UsernameChangeRecord):
        "Called when a user change their username/nickname"
        if event.is_in_guild:
            self.usernames["guild"] += 1
        else:
            self.usernames["user"] += 1

    @commands.Cog.listener()
    async def on_server_warning(self, warning_type: ServerWarningType, _guild: discord.Guild, **_kwargs):
        "Called when a server warning is triggered"
        if warning_type in {
            ServerWarningType.RSS_UNKNOWN_CHANNEL,
            ServerWarningType.RSS_MISSING_TXT_PERMISSION,
            ServerWarningType.RSS_MISSING_EMBED_PERMISSION,
            ServerWarningType.RSS_TWITTER_DISABLED,
        }:
            self.rss_stats["warnings"] += 1

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, msg: str):
        """Count when a websocket event is received"""
        msg: dict = json_loads(msg)
        if msg['t'] is None:
            return
        nbr = self.received_events.get(msg['t'], 0)
        self.received_events[msg['t']] = nbr + 1
        if msg['t'] == "MESSAGE_CREATE" and msg['d']['author']['id'] == str(self.bot.user.id):
            nbr2 = self.received_events.get('message_sent', 0)
            self.received_events['message_sent'] = nbr2 + 1

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: MyContext):
        """Called when a command is correctly used by someone"""
        name = ctx.command.full_parent_name.split()[0] if ctx.command.parent is not None else ctx.command.name
        self.commands_uses[name] = self.commands_uses.get(name, 0) + 1
        self.received_events['CMD_USE'] = self.received_events.get('CMD_USE', 0) + 1
        if ctx.interaction:
            self.app_commands_uses[name] = self.app_commands_uses.get(name, 0) + 1
            self.received_events['SLASH_CMD_USE'] = self.received_events.get('SLASH_CMD_USE', 0) + 1

    @commands.Cog.listener()
    async def on_serverlog(self, _guild_id: int, _channel_id: int, log_type: str):
        "Called when a serverlog is emitted"
        self.emitted_serverlogs[log_type] = self.emitted_serverlogs.get(log_type, 0) + 1

    @commands.Cog.listener()
    async def on_reminder_snooze(self, initial_duration: int, snooze_duration: int):
        "Called when a reminder is snoozed"
        self.snooze_events[(initial_duration, round(snooze_duration))] += 1

    @commands.Cog.listener()
    async def on_voice_transcript_completed(self, message_duration: float, generation_duration: float):
        "Called when a voice transcript is completed"
        self.voice_transcript_events[(message_duration, generation_duration)] += 1

    @commands.Cog.listener()
    async def on_stream_starts(self, *_args):
        "Called when a stream starts"
        self.stream_events["starts"] += 1

    @commands.Cog.listener()
    async def on_stream_ends(self, *_args):
        "Called when a stream ends"
        self.stream_events["ends"] += 1

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        "Collect a few stats from some specific messages"
        await self._check_backup_msg(message)
        await self._check_voice_msg(message)
        if message.author != self.bot.user:
            await self.emoji_analysis(message)

    async def _check_backup_msg(self, message: discord.Message):
        "Collect the last backup size from the logs channel"
        if message.channel.id != 625319946271850537 or len(message.embeds) != 1:
            return
        embed = message.embeds[0]
        if match := re.search(r"Database backup done! \((\d+(?:\.\d+)?)([GMK])\)", embed.description):
            unit = match.group(2)
            self.last_backup_size = float(match.group(1))
            if unit == "M":
                self.last_backup_size /= 1024
            elif unit == "K":
                self.last_backup_size /= 1024**2
            self.bot.log.info(f"Last backup size detected: {self.last_backup_size}G")

    async def _check_voice_msg(self, message: discord.Message):
        "Collect the amount of sent voice messages"
        if message.flags.voice:
            self.received_events['VOICE_MSG'] = self.received_events.get('VOICE_MSG', 0) + 1

    async def on_serverlogs_audit_search(self, success: bool):
        "Called when a serverlog audit logs search is done"
        if prev := self.serverlogs_audit_search:
            self.serverlogs_audit_search = (prev[0]+1, prev[1]+success)
        else:
            self.serverlogs_audit_search = (1, success)

    async def db_get_disabled_rss(self) -> int:
        "Count the number of disabled RSS feeds in any guild"
        table = 'rss_feed_beta' if self.bot.beta else 'rss_flow'
        query = f"SELECT COUNT(*) FROM {table} WHERE enabled = 0"
        async with self.bot.db_query(query, fetchone=True, astuple=True) as query_result:
            return query_result[0]

    async def db_record_event_collect_values(self, now: datetime):
        "Record into the stats table the total, min, max and median dailies values, as well as the number of dailies rows"
        # check if any daily is present
        query = "SELECT COUNT(*) FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (self.bot.beta,), fetchone=True, astuple=True) as query_result:
            if query_result[0] == 0:
                return
        # unit, is_sum, entity_id
        args = ("points", False, self.bot.entity_id, self.bot.beta)
        # Total
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, SUM(collect_points) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints_collect.total", *args)) as _:
            pass
        # Min
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MIN(collect_points) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints_collect.min", *args)) as _:
            pass
        # Max
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MAX(collect_points) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints_collect.max", *args)) as _:
            pass
        # Median
        query = """SET @row_index := -1;
        INSERT INTO `statsbot`.`zbot`
            SELECT %s, %s, ROUND(AVG(subq.collect_points)) as value, 0, %s, %s, %s
            FROM (
                SELECT @row_index:=@row_index + 1 AS row_index, collect_points
                FROM `axobot`.`event_points`
                WHERE `beta` = %s
                ORDER BY collect_points
            ) AS subq
            WHERE subq.row_index
            IN (FLOOR(@row_index / 2) , CEIL(@row_index / 2))"""
        async with self.bot.db_query(query, (now, "eventpoints_collect.median", *args), multi=True) as _:
            pass
        # Number of rows
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, COUNT(*) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints_collect.rows", *args)) as _:
            pass

    async def db_record_event_points_values(self, now: datetime):
        """Record into the stats table the total, min, max and median event points values,
        as well as the number of users having at least 1 point"""
        args = ("points", False, self.bot.entity_id, self.bot.beta)
        # Total
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, SUM(`points`) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints.total", *args)) as _:
            pass
        # Min
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MIN(`points`) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints.min", *args)) as _:
            pass
        # Max
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MAX(`points`) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints.max", *args)) as _:
            pass
        # Median
        query = """SET @row_index := -1;
        INSERT INTO `statsbot`.`zbot`
            SELECT %s, %s, ROUND(AVG(subq.`points`)) as value, 0, %s, %s, %s
            FROM (
                SELECT @row_index:=@row_index + 1 AS row_index, `points`
                FROM `axobot`.`event_points`
                WHERE `points` != 0 AND `beta` = %s
                ORDER BY points
            ) AS subq
            WHERE subq.row_index
            IN (FLOOR(@row_index / 2) , CEIL(@row_index / 2))"""
        async with self.bot.db_query(query, (now, "eventpoints.median", *args), multi=True) as _:
            pass
        # Number of rows
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, COUNT(*) AS value, 0, %s, %s, %s FROM `axobot`.`event_points` WHERE `points` != 0 AND `beta` = %s"
        async with self.bot.db_query(query, (now, "eventpoints.rows", *args)) as _:
            pass

    async def db_record_serverlogs_enabled(self, now: datetime):
        "Record into the stats table the number of enabled serverlogs, grouped by kind"
        guild_ids = {guild.id for guild in self.bot.guilds}
        query = """SELECT guild, kind FROM `serverlogs` WHERE `beta` = %s"""
        async with self.bot.db_query(query, (self.bot.beta,)) as query_results:
            enabled_kinds = defaultdict(int)
            for row in query_results:
                if row["guild"] in guild_ids:
                    enabled_kinds[row["kind"]] += 1
        query = "INSERT INTO `statsbot`.`zbot` VALUES (%s, %s, %s,  0,\"logs\", 0, %s);"
        return ((query, (now, f"logs.{kind}.enabled", count, self.bot.entity_id))
            for kind, count in enabled_kinds.items()
        )


    async def db_get_antiscam_enabled_count(self):
        "Get the number of active guilds where antiscam is enabled"
        query = "SELECT `guild_id` FROM `serverconfig` WHERE `option_name` = 'anti_scam' AND `value` = %s"
        count = 0
        guild_ids = {guild.id for guild in self.bot.guilds}
        async with self.bot.db_query(query, ("True",)) as query_results:
            for row in query_results:
                if row["guild_id"] in guild_ids:
                    count += 1
        return count

    async def emoji_analysis(self, msg: discord.Message):
        """Lists the emojis used in a message"""
        try:
            if not self.bot.database_online:
                return
            ctx = await self.bot.get_context(msg)
            if ctx.command is not None:
                return
            liste = list(set(re.findall(r'<a?:[\w-]+:(\d{17,19})>',msg.content)))
            if len(liste) == 0:
                return
            current_timestamp = datetime.fromtimestamp(round(time.time()))
            query = f"INSERT INTO `{self.emoji_table}` (`ID`,`count`,`last_update`) VALUES (%(i)s, 1, %(l)s) ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = %(l)s;"
            for data in [{ 'i': x, 'l': current_timestamp } for x in liste]:
                async with self.bot.db_query(query, data):
                    pass
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_emojis_info(self, emoji_id: Union[int, list[int]]) -> list[dict[str, Any]]:
        """Get info about an emoji usage"""
        if not self.bot.database_online:
            return []
        if isinstance(emoji_id, int):
            query = f"SELECT * from `{self.emoji_table}` WHERE `ID`=%s"
            query_args = (emoji_id,)
        else:
            where_cond = "OR".join(['`ID` = %s' for _ in emoji_id])
            query = f"SELECT * from `{self.emoji_table}` WHERE {where_cond}"
            query_args = (tuple(emoji_id), )
        liste = []
        async with self.bot.db_query(query, query_args) as query_results:
            for x in query_results:
                x['emoji'] = self.bot.get_emoji(x['ID'])
                liste.append(x)
        return liste

    @tasks.loop(minutes=1)
    async def sql_loop(self):
        """Send our stats every minute"""
        if not (self.bot.alerts_enabled and self.bot.database_online):
            return
        self.bot.log.debug("Stats loop triggered")
        # get current time
        now = self.bot.utcnow()
        # remove seconds and less
        now = now.replace(second=0, microsecond=0)
        # prepare requests
        query = "INSERT INTO `statsbot`.`zbot` VALUES (%s, %s, %s, %s, %s, %s, %s);"
        cnx = self.bot.cnx_axobot
        cursor = cnx.cursor(dictionary=True)
        try:
            # WS events stats
            for k, v in self.received_events.items():
                if v:
                    cursor.execute(query, (now, 'wsevent.'+k, v, 0, 'event/min', True, self.bot.entity_id))
                self.received_events[k] = 0
            # Commands usages stats
            for k, v in self.commands_uses.items():
                cursor.execute(query, (now, 'cmd.'+k, v, 0, 'cmd/min', True, self.bot.entity_id))
            self.commands_uses.clear()
            for k, v in self.app_commands_uses.items():
                cursor.execute(query, (now, 'app_cmd.'+k, v, 0, 'cmd/min', True, self.bot.entity_id))
            self.app_commands_uses.clear()
            # RSS stats
            if self.rss_loop_finished:
                for k, v in self.rss_stats.items():
                    cursor.execute(query, (now, 'rss.'+k, v, 0, k, k == "messages", self.bot.entity_id))
                    self.rss_stats[k] = 0
                self.rss_loop_finished = False
            cursor.execute(query, (now, 'rss.disabled', await self.db_get_disabled_rss(), 0, 'disabled', False, self.bot.entity_id))
            # XP cards
            if self.xp_cards["generated"]:
                cursor.execute(query, (now, 'xp.generated_cards', self.xp_cards["generated"], 0, 'cards/min', True, self.bot.entity_id))
                self.xp_cards["generated"] = 0
            if self.xp_cards["sent"]:
                cursor.execute(query, (now, 'xp.sent_cards', self.xp_cards["sent"], 0, 'cards/min', True, self.bot.entity_id))
                self.xp_cards["sent"] = 0
            # Latency
            if latency := await self.get_list_usage(self.latency_records):
                cursor.execute(query, (now, 'perf.latency', latency, 1, 'ms', False, self.bot.entity_id))
            # CPU usage
            bot_cpu = await self.get_list_usage(self.bot_cpu_records)
            if bot_cpu is not None:
                cursor.execute(query, (now, 'perf.bot_cpu', bot_cpu, 1, '%', False, self.bot.entity_id))
            total_cpu = await self.get_list_usage(self.total_cpu_records)
            if total_cpu is not None:
                cursor.execute(query, (now, 'perf.total_cpu', total_cpu, 1, '%', False, self.bot.entity_id))
            # RAM usage
            bot_ram = round(self.process.memory_info()[0] / 2.**30, 3)
            cursor.execute(query, (now, 'perf.bot_ram', bot_ram, 1, 'Gb', False, self.bot.entity_id))
            percent_ram, total_ram = await get_ram_data()
            cursor.execute(query, (now, 'perf.total_ram', round(total_ram / 1e9, 3), 1, 'Gb', False, self.bot.entity_id))
            cursor.execute(query, (now, 'perf.percent_total_ram', percent_ram, 1, '%', False, self.bot.entity_id))
            # Unavailable guilds
            unav, total = 0, 0
            for guild in self.bot.guilds:
                unav += guild.unavailable
                total += 1
            cursor.execute(query, (now, 'guilds.unavailable', round(unav/total, 3)*100, 1, '%', False, self.bot.entity_id))
            cursor.execute(query, (now, 'guilds.total', total, 0, 'guilds', False, self.bot.entity_id))
            del unav, total
            # antiscam warn/deletions
            if self.antiscam["warning"]:
                cursor.execute(query, (now, 'antiscam.warning', self.antiscam["warning"], 0, 'warning/min', True, self.bot.entity_id))
            if self.antiscam["deletion"]:
                cursor.execute(query, (now, 'antiscam.deletion', self.antiscam["deletion"], 0, 'deletion/min', True, self.bot.entity_id))
            self.antiscam["warning"] = self.antiscam["deletion"] = 0
            # antiscam scanned messages
            if antiscam_cog := self.bot.get_cog("AntiScam"):
                cursor.execute(query, (now, 'antiscam.scanned', antiscam_cog.messages_scanned, 0, 'messages/min', True, self.bot.entity_id))
                antiscam_cog.messages_scanned = 0
            # antiscam activated count
            cursor.execute(query, (now, 'antiscam.activated', await self.db_get_antiscam_enabled_count(), 0, 'guilds', False, self.bot.entity_id))
            # tickets creation
            if self.ticket_events["creation"]:
                cursor.execute(query, (now, 'tickets.creation', self.ticket_events["creation"], 0, 'tickets/min', True, self.bot.entity_id))
                self.ticket_events["creation"] = 0
            if self.bot.current_event:
                # Dailies points
                await self.db_record_event_collect_values(now)
                # Events points
                await self.db_record_event_points_values(now)
            # serverlogs
            for serverlogs_query in await self.db_record_serverlogs_enabled(now):
                cursor.execute(*serverlogs_query)
            for k, v in self.emitted_serverlogs.items():
                cursor.execute(query, (now, f'logs.{k}.emitted', v, 0, 'event/min', True, self.bot.entity_id))
            self.emitted_serverlogs.clear()
            if self.serverlogs_audit_search is not None:
                audit_search_percent = round(self.serverlogs_audit_search[1] / self.serverlogs_audit_search[0] * 100, 1)
                cursor.execute(query, (now, 'logs.audit_search', audit_search_percent, 1, '%', False, self.bot.entity_id))
                self.serverlogs_audit_search = None
            # Last backup save
            if self.last_backup_size:
                cursor.execute(query, (now, 'backup.size', self.last_backup_size, 1, 'Gb', False, self.bot.entity_id))
                self.last_backup_size = None
            # role reactions
            if self.role_reactions["added"]:
                cursor.execute(query, (now, 'role_reactions.added', self.role_reactions["added"], 0,
                                       'reactions', True, self.bot.entity_id))
                self.role_reactions["added"] = 0
            if self.role_reactions["removed"]:
                cursor.execute(query, (now, 'role_reactions.removed', self.role_reactions["removed"], 0,
                                       'reactions', True, self.bot.entity_id))
                self.role_reactions["removed"] = 0
            # snoozed reminders
            for (initial_duration, snooze_duration), count in self.snooze_events.items():
                cursor.execute(query, (now, f'reminders.snoozed.{initial_duration}.{snooze_duration}', count, 0,
                                       'reminders',True, self.bot.entity_id))
            self.snooze_events.clear()
            # Twitch stream events
            for event, count in self.stream_events.items():
                cursor.execute(query, (now, f'streams.{event}', count, 0,
                                       'streams', True, self.bot.entity_id))
            self.stream_events.clear()
            # voice transcripts
            for (message_duration, generation_duration), count in self.voice_transcript_events.items():
                cursor.execute(query, (now, f'voice_transcripts.{message_duration:.0f}.{generation_duration:.0f}', count, 0,
                                       'transcripts', True, self.bot.entity_id))
            self.voice_transcript_events.clear()
            # Push everything
            cnx.commit()
        except mysql.connector.errors.IntegrityError as err: # usually duplicate primary key
            self.bot.log.warning(f"Stats loop iteration cancelled: {err}", exc_info=True)
            self.bot.dispatch("error", err, "Stats loop iteration cancelled")
        # if something goes wrong, we still have to close the cursor
        cursor.close()

    @sql_loop.before_loop
    async def before_sql_loop(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()

    @sql_loop.error
    async def on_sql_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "SQL stats loop has stopped <@279568324260528128>")

    async def get_stats(self, variable: str, minutes: int) -> Union[int, float, str, None]:
        """Get the sum of a certain variable in the last X minutes"""
        cnx = self.bot.cnx_axobot
        cursor = cnx.cursor(dictionary=True)
        cursor.execute('SELECT variable, SUM(value) as value, type FROM `statsbot`.`zbot` WHERE variable = %s \
                       AND date BETWEEN (DATE_SUB(UTC_TIMESTAMP(),INTERVAL %s MINUTE)) AND UTC_TIMESTAMP() AND `entity_id`=%s',
                       (variable, minutes, self.bot.entity_id))
        result: list[dict] = list(cursor)
        cursor.close()
        if len(result) == 0:
            return 0
        result = result[0]
        if result['type'] == 0:
            return int(result['value'])
        elif result['type'] == 1:
            return float(result['value'])
        else:
            return result['value']

    @tasks.loop(minutes=4)
    async def status_loop(self):
        "Send average latency to axobot.statuspage.io every 4min"
        if self.bot.user.id != 486896267788812288 or not self.bot.internal_loop_enabled:
            return
        now = self.bot.utcnow()
        average = await self.get_list_usage(self.latency_records)
        async with aiohttp.ClientSession(loop=self.bot.loop, headers=self.statuspage_header) as session:
            params = {"data": {"timestamp": round(
                now.timestamp()), "value": average}}
            async with session.post(
                "https://api.statuspage.io/v1/pages/g9cnphg3mhm9/metrics/x4xs4clhkmz0/data",
                    json=params) as response:
                response.raise_for_status()
                self.bot.log.debug(
                    f"StatusPage API returned {response.status} for {params} (latency)")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()

    @status_loop.error
    async def on_status_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "When sending stats to statuspage.io (<@279568324260528128>)")

    @tasks.loop(minutes=2)
    async def heartbeat_loop(self):
        "Register a hearbeat in our database every 2min"
        if not self.bot.internal_loop_enabled:
            return
        query = "INSERT INTO `statsbot`.`heartbeat` (`entity_id`) VALUES (%s)"
        async with self.bot.db_query(query, (self.bot.entity_id,)):
            self.bot.log.debug("Heartbeat sent to database")

    @heartbeat_loop.before_loop
    async def before_heartbeat_loop(self):
        await self.bot.wait_until_ready()

    @heartbeat_loop.error
    async def on_heartbeat_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "When sending heartbeat to statsbot (<@279568324260528128>)")


async def setup(bot):
    await bot.add_cog(BotStats(bot))
