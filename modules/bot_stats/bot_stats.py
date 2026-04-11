import logging
import math
import re
import subprocess
from collections import defaultdict
from datetime import datetime
from typing import Any, Literal

import aiohttp
import discord
import psutil
from discord.ext import commands, tasks
from mysql.connector.errors import IntegrityError as MysqlIntegrityError

from core.bot_classes import Axobot, MyContext
from core.enums import ServerWarningType
from core.type_utils import AnyStrDict
from core.utilities import avg

from .src.db_writer import StatRow, write_stats_batch

try:
    import orjson  # type: ignore
except ModuleNotFoundError:
    import json
    json_loads = json.loads
else:
    json_loads = orjson.loads

_LOGS_CHANNEL_ID = 625319946271850537

RssStats = dict[Literal["checked", "messages", "errors", "warnings", "time"], int]
XpCardsStats = dict[Literal["generated", "sent"], int]
TicketEventsStats = dict[Literal["creation"], int]


async def get_ram_data() -> tuple[float, int]:
    data = psutil.virtual_memory()
    return data.percent, (data.total - data.available)


class BotStats(commands.Cog):
    "Send internal stats to our database"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_stats"
        self.log = logging.getLogger("bot.stats")

        self.received_events: dict[str, int] = defaultdict(int)
        self.commands_uses: dict[str, int] = defaultdict(int)
        self.app_commands_uses: dict[str, int] = defaultdict(int)
        self.rss_stats: RssStats = {"checked": 0, "messages": 0, "errors": 0, "warnings": 0, "time": 0}
        self.rss_loop_finished = False
        self.xp_cards: XpCardsStats = {"generated": 0, "sent": 0}
        self.process: psutil.Process = psutil.Process()
        self.bot_cpu_records: list[float] = []
        self.total_cpu_records: list[float] = []
        self.latency_records: list[int] = []
        self.sql_performance_records: list[float] = []
        self.statuspage_header = {
            "Content-Type": "application/json",
            "Authorization": "OAuth " + self.bot.secrets["statuspage"],
        }
        self.antiscam: dict[str, int] = {"warning": 0, "deletion": 0}
        self.ticket_events: TicketEventsStats = {"creation": 0}
        self.emitted_serverlogs: dict[str, int] = defaultdict(int)
        self.emojis_usage: dict[int, int] = defaultdict(int)
        self.last_backup_size: float | None = None
        self.open_files: dict[str, int] = defaultdict(int)
        self.role_reactions: dict[str, int] = {"added": 0, "removed": 0}
        self.serverlogs_audit_search: tuple[int, int] | None = None
        self.invite_tracker_search: tuple[int, int] | None = None
        self.snooze_events: dict[tuple[int, int], int] = defaultdict(int)
        self.stream_events: dict[str, int] = defaultdict(int)
        self.voice_transcript_events: dict[tuple[float, float], int] = defaultdict(int)

    async def cog_load(self):
        # pylint: disable=no-member
        self.sql_loop.start()
        self.record_cpu_usage.start()
        self.record_ws_latency.start()
        self.record_open_files.start()
        self.status_loop.start()
        self.heartbeat_loop.start()
        self.emojis_loop.start()

    async def cog_unload(self):
        # pylint: disable=no-member
        self.sql_loop.cancel()
        self.record_cpu_usage.cancel()
        self.record_ws_latency.cancel()
        self.record_open_files.cancel()
        self.status_loop.stop()
        self.heartbeat_loop.stop()
        self.emojis_loop.stop()

    @property
    def emoji_table(self) -> str:
        return "emojis_beta" if self.bot.beta else "emojis"

    # ---- Performance sampling loops ----

    @tasks.loop(seconds=10)
    async def record_cpu_usage(self):
        "Record the CPU usage for later use"
        self.bot_cpu_records.append(self.process.cpu_percent())
        if len(self.bot_cpu_records) > 6:
            # if the list becomes too long (over 1min), cut it
            self.bot_cpu_records = self.bot_cpu_records[-6:]
        self.total_cpu_records.append(sum(psutil.cpu_percent(percpu=True)))
        if len(self.total_cpu_records) > 6:
            # if the list becomes too long (over 1min), cut it
            self.total_cpu_records = self.total_cpu_records[-6:]

    @record_cpu_usage.error
    async def on_record_cpu_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When collecting CPU usage")

    @tasks.loop(seconds=20)
    async def record_ws_latency(self):
        "Record the websocket latency for later use"
        if math.isnan(self.bot.latency):
            return
        try:
            self.latency_records.append(round(self.bot.latency * 1000))
        except OverflowError:  # Usually because latency is infinite
            self.latency_records.append(int(10e6))
        if len(self.latency_records) > 3:
            # if the list becomes too long (over 1min), cut it
            self.latency_records = self.latency_records[-3:]

    @record_ws_latency.error
    async def on_record_latency_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When collecting WS latency")

    @tasks.loop(minutes=2)
    async def record_open_files(self):
        "Record the number of open files from the bot process"
        if not self.bot.files_count_enabled:
            return
        result = subprocess.run(["lsof", "-p", str(self.process.pid)], stdout=subprocess.PIPE, check=True)
        self.open_files.clear()
        for line in result.stdout.split(b"\n"):
            if line.startswith(b"COMMAND"):
                continue # skip header
            row = line.decode("utf8")
            if not row:
                continue # skip empty lines
            while "  " in row:
                row = row.replace("  ", " ")
            fd = ''.join(c for c in row.split(" ")[3] if not c.isdigit())
            if not fd:
                self.log.info("Unknown file descriptor for open file: %s", row)
                continue
            self.open_files[fd] += 1
            if (file_type := row.split(" ")[4]) and file_type.startswith("IPv"):
                self.open_files[file_type] += 1

    @record_open_files.error
    async def record_open_files_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When checking process open files")

    # ---- Event listeners ----

    @commands.Cog.listener()
    async def on_antiscam_warn(self, *_args: Any, **_kwargs: Any):
        self.antiscam["warning"] += 1

    @commands.Cog.listener()
    async def on_antiscam_delete(self, *_args: Any, **_kwargs: Any):
        self.antiscam["deletion"] += 1

    @commands.Cog.listener()
    async def on_ticket_creation(self, *_args: Any, **_kwargs: Any):
        self.ticket_events["creation"] += 1

    @commands.Cog.listener()
    async def on_server_warning(self, warning_type: ServerWarningType, *_args: Any, **_kwargs: Any):
        "Called when a server warning is triggered"
        if warning_type in {
            ServerWarningType.RSS_UNKNOWN_CHANNEL,
            ServerWarningType.RSS_MISSING_TXT_PERMISSION,
            ServerWarningType.RSS_MISSING_EMBED_PERMISSION,
            ServerWarningType.RSS_TWITTER_DISABLED,
        }:
            self.rss_stats["warnings"] += 1

    @commands.Cog.listener()
    async def on_socket_raw_receive(self, raw: str):
        """Count when a websocket event is received"""
        msg: AnyStrDict = json_loads(raw)
        if msg['t'] is None:
            return
        self.received_events[msg['t']] += 1
        if self.bot.user is None:
            raise RuntimeError("Bot user is not initialized, cannot track events")
        if msg['t'] == "MESSAGE_CREATE" and msg["d"]["author"]["id"] == str(self.bot.user.id):
            self.received_events["message_sent"] += 1

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: MyContext):
        """Called when a prefix command is correctly used by someone"""
        if ctx.interaction or ctx.command is None:
            return # will be handled in on_app_command_completion
        name = ctx.command.qualified_name
        self.commands_uses[name] += 1
        self.received_events["CMD_USE"] += 1

    @commands.Cog.listener()
    async def on_app_command_completion(
        self,
        _interaction: discord.Interaction,
        command: discord.app_commands.Command[Any, ..., Any] | discord.app_commands.ContextMenu,
    ):
        """Called when an app command is correctly used by someone"""
        name = command.qualified_name.lower()
        self.commands_uses[name] += 1
        self.received_events["CMD_USE"] += 1
        self.app_commands_uses[name] += 1
        self.received_events["SLASH_CMD_USE"] += 1

    @commands.Cog.listener()
    async def on_serverlog(self, _guild_id: int, _channel_id: int, log_type: str):
        "Called when a serverlog is emitted"
        self.emitted_serverlogs[log_type] += 1

    @commands.Cog.listener()
    async def on_reminder_snooze(self, initial_duration: int, snooze_duration: int):
        "Called when a reminder is snoozed"
        self.snooze_events[(initial_duration, round(snooze_duration))] += 1

    @commands.Cog.listener()
    async def on_voice_transcript_completed(self, message_duration: float, generation_duration: float):
        "Called when a voice transcript is completed"
        self.voice_transcript_events[(message_duration, generation_duration)] += 1

    @commands.Cog.listener()
    async def on_stream_starts(self, *_args: Any, **_kwargs: Any):
        "Called when a stream starts"
        self.stream_events["starts"] += 1

    @commands.Cog.listener()
    async def on_stream_ends(self, *_args: Any, **_kwargs: Any):
        "Called when a stream ends"
        self.stream_events["ends"] += 1

    @commands.Cog.listener()
    async def on_serverlogs_audit_search(self, success: bool):
        "Called when a serverlog audit-log search completes"
        if prev := self.serverlogs_audit_search:
            self.serverlogs_audit_search = (prev[0] + 1, prev[1] + int(success))
        else:
            self.serverlogs_audit_search = (1, int(success))

    @commands.Cog.listener()
    async def on_invite_tracker_search(self, success: bool):
        "Called when an invite tracker search is done"
        if prev := self.invite_tracker_search:
            self.invite_tracker_search = (prev[0] + 1, prev[1] + int(success))
        else:
            self.invite_tracker_search = (1, int(success))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        "Collect a few stats from some specific messages"
        await self._check_backup_msg(message)
        await self._check_voice_msg(message)
        if message.author != self.bot.user:
            await self.emoji_analysis(message)

    async def _check_backup_msg(self, message: discord.Message):
        "Collect the last backup size from the logs channel"
        if message.channel.id != _LOGS_CHANNEL_ID or len(message.embeds) != 1:
            return
        embed = message.embeds[0]
        if embed.description is None:
            return
        if match := re.search(r"Database backup done! \((\d+(?:\.\d+)?)([GMK])\)", embed.description):
            unit = match.group(2)
            size = float(match.group(1))
            if unit == "G":
                self.last_backup_size = size
            elif unit == "M":
                self.last_backup_size = size / 1024
            elif unit == "K":
                self.last_backup_size = size / 1024 ** 2
            else:
                self.bot.dispatch(
                    "error", ValueError(f"Unknown backup size unit: {unit}"), "When checking last backup size"
                )
                return
            self.log.info("Last backup size detected: %sG", self.last_backup_size)

    async def _check_voice_msg(self, message: discord.Message):
        "Collect the amount of sent voice messages"
        if message.flags.voice:
            self.received_events["VOICE_MSG"] += 1

    # ---- Public helpers (used by other cogs) ----

    async def db_get_emojis_info(self, emoji_id: int | list[int]) -> list[dict[str, Any]]:
        "Get info about an emoji usage"
        if not self.bot.database_online:
            return []
        if isinstance(emoji_id, int):
            query = f"SELECT * from `{self.emoji_table}` WHERE `ID`=%s"
            query_args = (emoji_id,)
        else:
            where_cond = " OR ".join(["`ID` = %s" for _ in emoji_id])
            query = f"SELECT * from `{self.emoji_table}` WHERE {where_cond}"
            query_args = tuple(emoji_id)
        result: list[dict[str, Any]] = []
        async with self.bot.db_main.read(query, query_args) as rows:
            for x in rows:
                x["emoji"] = self.bot.get_emoji(x["ID"])
                result.append(x)
        return result

    # ---- Database helpers ----

    async def db_get_disabled_rss(self) -> int:
        "Count the number of disabled RSS feeds in any guild"
        table = "rss_feed_beta" if self.bot.beta else "rss_feed"
        query = f"SELECT COUNT(*) FROM {table} WHERE enabled = 0"
        async with self.bot.db_main.read(query, fetchone=True, astuple=True) as result:
            return int(result[0])

    async def db_get_antiscam_enabled_count(self) -> int:
        "Get the number of active guilds where antiscam is enabled"
        query = "SELECT `guild_id` FROM `serverconfig` WHERE `option_name` = 'anti_scam' AND `value` = %s"
        guild_ids = {guild.id for guild in self.bot.guilds}
        count = 0
        async with self.bot.db_main.read(query, ("True",)) as rows:
            for row in rows:
                if row["guild_id"] in guild_ids:
                    count += 1
        return count

    async def _collect_serverlogs_enabled_rows(self) -> list[StatRow]:
        "Collect per-kind count of enabled server logs as stat rows"
        guild_ids = {guild.id for guild in self.bot.guilds}
        query = "SELECT guild, kind FROM `serverlogs` WHERE `beta` = %s"
        enabled_kinds: dict[str, int] = defaultdict(int)
        async with self.bot.db_main.read(query, (self.bot.beta,)) as rows:
            for row in rows:
                if row["guild"] in guild_ids:
                    enabled_kinds[row["kind"]] += 1
        return [
            StatRow(f"logs.{kind}.enabled", count, 0, "logs", False)
            for kind, count in enabled_kinds.items()
        ]

    async def db_record_event_collect_values(self, now: datetime):
        "Record the collect-points distribution (total, min, max, median, row count)"
        query = "SELECT COUNT(*) FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_main.read(query, (self.bot.beta,), fetchone=True, astuple=True) as result:
            if result[0] == 0:
                return
        # (unit, is_sum, entity_id, beta) – appended after the per-query positional args
        tail = ("points", False, self.bot.entity_id, self.bot.beta)
        for label, agg in (("total", "SUM"), ("min", "MIN"), ("max", "MAX")):
            q = (
                f"INSERT INTO `zbot` SELECT %s, %s, {agg}(collect_points) AS value, 0, %s, %s, %s "
                "FROM `axobot`.`event_points` WHERE `beta` = %s"
            )
            async with self.bot.db_stats.write(q, (now, f"eventpoints_collect.{label}", *tail)):
                pass
        median_q = """SET @row_index := -1;
        INSERT INTO `zbot`
            SELECT %s, %s, ROUND(AVG(subq.collect_points)) as value, 0, %s, %s, %s
            FROM (
                SELECT @row_index:=@row_index + 1 AS row_index, collect_points
                FROM `axobot`.`event_points`
                WHERE `beta` = %s
                ORDER BY collect_points
            ) AS subq
            WHERE subq.row_index
            IN (FLOOR(@row_index / 2) , CEIL(@row_index / 2))"""
        async with self.bot.db_stats.write(median_q, (now, "eventpoints_collect.median", *tail), multi=True):
            pass
        rows_q = (
            "INSERT INTO `zbot` SELECT %s, %s, COUNT(*) AS value, 0, %s, %s, %s "
            "FROM `axobot`.`event_points` WHERE `collect_points` != 0 AND `beta` = %s"
        )
        async with self.bot.db_stats.write(rows_q, (now, "eventpoints_collect.rows", *tail)):
            pass

    async def db_record_event_points_values(self, now: datetime):
        "Record the event-points distribution (total, min, max, median, row count)"
        query = "SELECT COUNT(*) FROM `axobot`.`event_points` WHERE `beta` = %s"
        async with self.bot.db_main.read(query, (self.bot.beta,), fetchone=True, astuple=True) as result:
            if result[0] == 0:
                return
        tail = ("points", False, self.bot.entity_id, self.bot.beta)
        for label, agg in (("total", "SUM"), ("min", "MIN"), ("max", "MAX")):
            q = (
                f"INSERT INTO `zbot` SELECT %s, %s, {agg}(`points`) AS value, 0, %s, %s, %s "
                "FROM `axobot`.`event_points` WHERE `beta` = %s"
            )
            async with self.bot.db_stats.write(q, (now, f"eventpoints.{label}", *tail)):
                pass
        median_q = """SET @row_index := -1;
        INSERT INTO `zbot`
            SELECT %s, %s, ROUND(AVG(subq.`points`)) as value, 0, %s, %s, %s
            FROM (
                SELECT @row_index:=@row_index + 1 AS row_index, `points`
                FROM `axobot`.`event_points`
                WHERE `points` != 0 AND `beta` = %s
                ORDER BY points
            ) AS subq
            WHERE subq.row_index
            IN (FLOOR(@row_index / 2) , CEIL(@row_index / 2))"""
        async with self.bot.db_stats.write(median_q, (now, "eventpoints.median", *tail), multi=True):
            pass
        rows_q = (
            "INSERT INTO `zbot` SELECT %s, %s, COUNT(*) AS value, 0, %s, %s, %s "
            "FROM `axobot`.`event_points` WHERE `points` != 0 AND `beta` = %s"
        )
        async with self.bot.db_stats.write(rows_q, (now, "eventpoints.rows", *tail)):
            pass

    # ---- Stat collection ----

    def _flush_rows(self) -> list[StatRow]:
        "Collect all pending in-memory stats as StatRows and reset the counters."
        rows: list[StatRow] = []

        # WS events – always reset, emit only non-zero
        for k, v in self.received_events.items():
            if v:
                rows.append(StatRow("wsevent." + k, v, 0, "event/min", True))
        self.received_events.clear()

        # Commands
        for k, v in self.commands_uses.items():
            rows.append(StatRow("cmd." + k, v, 0, "cmd/min", True))
        self.commands_uses.clear()
        for k, v in self.app_commands_uses.items():
            rows.append(StatRow("app_cmd." + k, v, 0, "cmd/min", True))
        self.app_commands_uses.clear()

        # RSS – only flush when the loop has finished a full pass
        if self.rss_loop_finished:
            for k, v in self.rss_stats.items():
                rows.append(StatRow("rss." + k, v, 0, k, k == "messages"))
            self.rss_stats = {"checked": 0, "messages": 0, "errors": 0, "warnings": 0, "time": 0}
            self.rss_loop_finished = False

        # XP cards
        for key in ("generated", "sent"):
            if self.xp_cards[key]:
                rows.append(StatRow(f"xp.{key}_cards", self.xp_cards[key], 0, "cards/min", True))
                self.xp_cards[key] = 0

        # Performance: latency, SQL queries, CPU
        lat = avg(self.latency_records)
        if lat is not None:
            rows.append(StatRow("perf.latency", lat, 1, "ms", False))
            self.latency_records.clear()
        if self.sql_performance_records:
            rows.append(StatRow("perf.sql_count", len(self.sql_performance_records), 0, "queries/min", True))
            if (sql_avg := avg(self.sql_performance_records)) is not None:
                rows.append(StatRow("perf.sql", sql_avg, 1, "ms", False))
            self.sql_performance_records.clear()
        if (bot_cpu := avg(self.bot_cpu_records)) is not None:
            rows.append(StatRow("perf.bot_cpu", bot_cpu, 1, "%", False))
            self.bot_cpu_records.clear()
        if (total_cpu := avg(self.total_cpu_records)) is not None:
            rows.append(StatRow("perf.total_cpu", total_cpu, 1, "%", False))
            self.total_cpu_records.clear()

        # AntiScam warn / deletion counters
        for key, unit in (("warning", "warning/min"), ("deletion", "deletion/min")):
            if self.antiscam[key]:
                rows.append(StatRow(f"antiscam.{key}", self.antiscam[key], 0, unit, True))
                self.antiscam[key] = 0

        # Tickets
        if self.ticket_events["creation"]:
            rows.append(StatRow("tickets.creation", self.ticket_events["creation"], 0, "tickets/min", True))
            self.ticket_events["creation"] = 0

        # Serverlogs emitted
        for k, v in self.emitted_serverlogs.items():
            rows.append(StatRow(f"logs.{k}.emitted", v, 0, "event/min", True))
        self.emitted_serverlogs.clear()

        # Audit-log search success rate
        if self.serverlogs_audit_search is not None:
            total_s, success_s = self.serverlogs_audit_search
            rows.append(StatRow("logs.audit_search", round(success_s / total_s * 100, 1), 1, "%", False))
            self.serverlogs_audit_search = None

        # Invite-tracker search success rate
        if self.invite_tracker_search is not None:
            total_i, success_i = self.invite_tracker_search
            rows.append(StatRow("invite_search", round(success_i / total_i * 100, 1), 1, "%", False))
            self.invite_tracker_search = None

        # Backup size
        if self.last_backup_size is not None:
            rows.append(StatRow("backup.size", self.last_backup_size, 1, "Gb", False))
            self.last_backup_size = None

        # Role reactions
        for key in ("added", "removed"):
            if self.role_reactions[key]:
                rows.append(StatRow(f"role_reactions.{key}", self.role_reactions[key], 0, "reactions", True))
                self.role_reactions[key] = 0

        # Snoozed reminders
        for (initial, snooze), count in self.snooze_events.items():
            rows.append(StatRow(f"reminders.snoozed.{initial}.{snooze}", count, 0, "reminders", True))
        self.snooze_events.clear()

        # Stream events
        for event, count in self.stream_events.items():
            rows.append(StatRow(f"streams.{event}", count, 0, "streams", True))
        self.stream_events.clear()

        # Voice transcripts
        for (msg_dur, gen_dur), count in self.voice_transcript_events.items():
            rows.append(StatRow(f"voice_transcripts.{msg_dur:.0f}.{gen_dur:.0f}", count, 0, "transcripts", True))
        self.voice_transcript_events.clear()

        # Open file descriptors
        for fd, count in self.open_files.items():
            rows.append(StatRow(f"process.open_files.{fd}", count, 0, "files", False))
        self.open_files.clear()

        return rows

    # ---- Main stats loop ----

    @tasks.loop(minutes=1)
    async def sql_loop(self):
        """Send all collected stats to the database every minute"""
        if not (self.bot.stats_enabled and self.bot.database_online):
            return
        self.log.debug("Stats loop triggered")
        now = self.bot.utcnow().replace(second=0, microsecond=0)

        rows = self._flush_rows()

        # RSS: number of disabled feeds (DB query)
        rows.append(StatRow("rss.disabled", await self.db_get_disabled_rss(), 0, "disabled", False))

        # RAM usage
        bot_ram = round(self.process.memory_info()[0] / 2.0 ** 30, 3)
        rows.append(StatRow("perf.bot_ram", bot_ram, 1, "Gb", False))
        percent_ram, total_ram = await get_ram_data()
        rows.append(StatRow("perf.total_ram", round(total_ram / 1e9, 3), 1, "Gb", False))
        rows.append(StatRow("perf.percent_total_ram", percent_ram, 1, "%", False))

        # Guild availability
        guilds = self.bot.guilds
        total = len(guilds)
        if total:
            unav = sum(g.unavailable for g in guilds)
            rows.append(StatRow("guilds.unavailable", round(unav / total, 3) * 100, 1, "%", False))
        rows.append(StatRow("guilds.total", total, 0, "guilds", False))

        # AntiScam: messages scanned this minute
        if antiscam_cog := self.bot.get_cog("AntiScam"):
            rows.append(
                StatRow("antiscam.scanned", antiscam_cog.messages_scanned_in_last_minute, 0, "messages/min", True)
            )
            antiscam_cog.messages_scanned_in_last_minute = 0

        # AntiScam: activated guild count
        rows.append(StatRow("antiscam.activated", await self.db_get_antiscam_enabled_count(), 0, "guilds", False))

        # Serverlogs: enabled per kind
        rows.extend(await self._collect_serverlogs_enabled_rows())

        # Event points – use direct INSERT … SELECT queries, cannot be batched
        if self.bot.current_event:
            try:
                await self.db_record_event_collect_values(now)
                await self.db_record_event_points_values(now)
            except Exception as err:  # pylint: disable=broad-except
                self.bot.dispatch("error", err, "When recording event points")

        # Flush all in-memory rows in a single batch INSERT
        try:
            await write_stats_batch(self.bot.db_stats, self.bot.entity_id, now, rows)
        except MysqlIntegrityError as err:  # usually a duplicate primary key
            self.bot.dispatch("error", err, "Stats loop iteration cancelled")

    @sql_loop.before_loop
    async def before_sql_loop(self):
        await self.bot.wait_until_ready()

    @sql_loop.error
    async def on_sql_loop_error(self, error: BaseException):
        self.bot.dispatch("error", error, "SQL stats loop has stopped <@279568324260528128>")

    async def get_sum_stats(self, variable: str, minutes: int) -> int | float | str | None:
        """Get the sum of a stat variable over the last X minutes"""
        query = (
            "SELECT variable, SUM(value) as value, type FROM `zbot` "
            "WHERE variable = %s AND date BETWEEN (DATE_SUB(UTC_TIMESTAMP(), INTERVAL %s MINUTE)) "
            "AND UTC_TIMESTAMP() AND `entity_id` = %s"
        )
        async with self.bot.db_stats.read(query, (variable, minutes, self.bot.entity_id), fetchone=True) as result:
            sum_value = result.get("value")
            if sum_value is None:
                return 0
            if result["type"] == 0:
                return int(sum_value)
            if result["type"] == 1:
                return float(sum_value)
            return sum_value  # type: ignore[return-value]

    @tasks.loop(minutes=4)
    async def status_loop(self):
        """Send average latency to axobot.statuspage.io every 4 min"""
        if self.bot.entity_id != 2 or not self.bot.internal_loop_enabled:
            return
        now = self.bot.utcnow()
        average = avg(self.latency_records)
        if average is None:
            return
        async with aiohttp.ClientSession(headers=self.statuspage_header) as session:
            params = {"data": {"timestamp": round(now.timestamp()), "value": average}}
            async with session.post(
                "https://api.statuspage.io/v1/pages/g9cnphg3mhm9/metrics/x4xs4clhkmz0/data",
                json=params,
            ) as response:
                response.raise_for_status()
                self.log.debug("StatusPage API returned %s for %s (latency)", response.status, params)

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()

    @status_loop.error
    async def on_status_loop_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When sending stats to statuspage.io (<@279568324260528128>)")

    @tasks.loop(minutes=2)
    async def heartbeat_loop(self):
        """Register a heartbeat in the stats database every 2 min"""
        if not self.bot.stats_enabled:
            return
        query = "INSERT INTO `heartbeat` (`entity_id`) VALUES (%s)"
        async with self.bot.db_stats.write(query, (self.bot.entity_id,)):
            self.log.debug("Heartbeat sent to database")

    @heartbeat_loop.before_loop
    async def before_heartbeat_loop(self):
        await self.bot.wait_until_ready()

    @heartbeat_loop.error
    async def on_heartbeat_loop_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When sending heartbeat to statsbot")

    async def emoji_analysis(self, msg: discord.Message):
        "List the custom emojis used in a message and accumulate their usage counts"
        try:
            if not self.bot.database_online:
                return
            ctx = await self.bot.get_context(msg)
            if ctx.command is not None:
                return
            for emoji_id in set(re.findall(r"<a?:[\w-]+:(\d{17,19})>", msg.content)):
                self.emojis_usage[int(emoji_id)] += 1
        except Exception as err:  # pylint: disable=broad-except
            self.bot.dispatch("error", err)

    @tasks.loop(seconds=30)
    async def emojis_loop(self):
        "Flush accumulated emoji usage counts to the database every 30 s"
        if not self.bot.stats_enabled or not self.emojis_usage:
            return
        query = f"INSERT INTO `{self.emoji_table}` (`ID`, `count`, `last_update`) VALUES"
        args: list[int] = []
        for emoji_id, count in self.emojis_usage.items():
            query += " (%s, %s, UTC_TIMESTAMP()),"
            args.extend((emoji_id, count))
        query = (
            query[:-1]
            + " ON DUPLICATE KEY UPDATE count = count + VALUES(count), last_update = UTC_TIMESTAMP();"
        )
        async with self.bot.db_main.write(query, tuple(args)):
            self.emojis_usage.clear()

    @emojis_loop.before_loop
    async def before_emojis_loop(self):
        await self.bot.wait_until_ready()

    @emojis_loop.error
    async def on_emojis_loop_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When sending emojis usage to database")


async def setup(bot: Axobot):
    await bot.add_cog(BotStats(bot))
