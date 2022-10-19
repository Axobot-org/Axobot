from datetime import datetime
import math
import typing
import aiohttp

import mysql
import psutil
import discord
from discord.ext import commands, tasks
from fcts.tickets import TicketCreationEvent
from libs.bot_classes import MyContext, Zbot
from libs.enums import ServerWarningType, UsernameChangeRecord

try:
    import orjson  # type: ignore
except ModuleNotFoundError:
    import json
    json_loads = json.loads
else:
    json_loads = orjson.loads


class BotStats(commands.Cog):
    """Hey, I'm a test cog! Happy to meet you :wave:"""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = 'bot_stats'
        self.received_events = {'CMD_USE': 0}
        self.commands_uses = {}
        self.rss_stats = {'checked': 0, 'messages': 0, 'errors': 0, 'warnings': 0}
        self.xp_cards = {'generated': 0, 'sent': 0}
        self.process = psutil.Process()
        self.cpu_records: list[float] = []
        self.latency_records: list[int] = []
        self.statuspage_header = {"Content-Type": "application/json", "Authorization": "OAuth " + self.bot.others["statuspage"]}
        self.antiscam = {"warning": 0, "deletion": 0}
        self.ticket_events = {"creation": 0}
        self.usernames = {"guild": 0, "user": 0, "deleted": 0}

    async def cog_load(self):
         # pylint: disable=no-member
        self.sql_loop.start()
        self.record_cpu_usage.start()
        self.record_ws_latency.start()
        self.status_loop.start()

    async def cog_unload(self):
         # pylint: disable=no-member
        self.sql_loop.cancel()
        self.record_cpu_usage.cancel()
        self.record_ws_latency.cancel()
        self.status_loop.stop()

    @tasks.loop(seconds=10)
    async def record_cpu_usage(self):
        "Record the CPU usage for later use"
        self.cpu_records.append(self.process.cpu_percent())
        if len(self.cpu_records) > 6:
            # if the list becomes too long (over 1min), cut it
            self.cpu_records = self.cpu_records[-6:]

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
        if event.is_guild:
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
        nbr = self.commands_uses.get(name, 0)
        self.commands_uses[name] = nbr + 1
        nbr = self.received_events.get('CMD_USE', 0)
        self.received_events['CMD_USE'] = nbr + 1

    async def db_get_disabled_rss(self) -> int:
        "Count the number of disabled RSS feeds in any guild"
        table = 'rss_flow_beta' if self.bot.beta else 'rss_flow'
        query = f"SELECT COUNT(*) FROM {table} WHERE enabled = 0"
        async with self.bot.db_query(query, fetchone=True, astuple=True) as query_result:
            return query_result[0]

    async def db_record_dailies_values(self, now: datetime):
        "Record into the stats table the total, min, max and median dailies values, as well as the number of dailies rows"
        args = ("points", False, self.bot.beta)
        # Total
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, SUM(points) AS value, 0, %s, %s, %s FROM `frm`.`dailies`"
        async with self.bot.db_query(query, (now, "dailies.total", *args)) as _:
            pass
        # Min
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MIN(points) AS value, 0, %s, %s, %s FROM `frm`.`dailies`"
        async with self.bot.db_query(query, (now, "dailies.min", *args)) as _:
            pass
        # Max
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MAX(points) AS value, 0, %s, %s, %s FROM `frm`.`dailies`"
        async with self.bot.db_query(query, (now, "dailies.max", *args)) as _:
            pass
        # Median
        query = """SET @row_index := -1;
        INSERT INTO `statsbot`.`zbot`
            SELECT %s, %s, ROUND(AVG(subq.points)) as value, 0, %s, %s, %s
            FROM (
                SELECT @row_index:=@row_index + 1 AS row_index, points
                FROM `frm`.`dailies`
                ORDER BY points
            ) AS subq
            WHERE subq.row_index 
            IN (FLOOR(@row_index / 2) , CEIL(@row_index / 2))"""
        async with self.bot.db_query(query, (now, "dailies.median", *args), multi=True) as _:
            pass
        # Number of rows
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, COUNT(*) AS value, 0, %s, %s, %s FROM `frm`.`dailies`"
        async with self.bot.db_query(query, (now, "dailies.rows", *args)) as _:
            pass

    async def db_record_eventpoints_values(self, now: datetime):
        """Record into the stats table the total, min, max and median event points values,
        as well as the number of users having at least 1 point"""
        args = ("points", False, self.bot.beta)
        # Total
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, SUM(`events_points`) AS value, 0, %s, %s, %s FROM `frm`.`users`"
        async with self.bot.db_query(query, (now, "eventpoints.total", *args)) as _:
            pass
        # Min
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MIN(`events_points`) AS value, 0, %s, %s, %s FROM `frm`.`users`"
        async with self.bot.db_query(query, (now, "eventpoints.min", *args)) as _:
            pass
        # Max
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, MAX(`events_points`) AS value, 0, %s, %s, %s FROM `frm`.`users`"
        async with self.bot.db_query(query, (now, "eventpoints.max", *args)) as _:
            pass
        # Median
        query = """SET @row_index := -1;
        INSERT INTO `statsbot`.`zbot`
            SELECT %s, %s, ROUND(AVG(subq.`events_points`)) as value, 0, %s, %s, %s
            FROM (
                SELECT @row_index:=@row_index + 1 AS row_index, `events_points`
                FROM `frm`.`users`
                WHERE `events_points` != 0
                ORDER BY events_points
            ) AS subq
            WHERE subq.row_index 
            IN (FLOOR(@row_index / 2) , CEIL(@row_index / 2))"""
        async with self.bot.db_query(query, (now, "eventpoints.median", *args), multi=True) as _:
            pass
        # Number of rows
        query = "INSERT INTO `statsbot`.`zbot` SELECT %s, %s, COUNT(*) AS value, 0, %s, %s, %s FROM `frm`.`users` WHERE `events_points` != 0"
        async with self.bot.db_query(query, (now, "eventpoints.rows", *args)) as _:
            pass

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
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        try:
            # WS events stats
            for k, v in self.received_events.items():
                cursor.execute(query, (now, 'wsevent.'+k, v, 0, 'event/min', True, self.bot.beta))
                self.received_events[k] = 0
            # Commands usages stats
            for k, v in self.commands_uses.items():
                cursor.execute(query, (now, 'cmd.'+k, v, 0, 'cmd/min', True, self.bot.beta))
            self.commands_uses.clear()
            # RSS stats
            for k, v in self.rss_stats.items():
                cursor.execute(query, (now, 'rss.'+k, v, 0, k, k == "messages", self.bot.beta))
            cursor.execute(query, (now, 'rss.disabled', await self.db_get_disabled_rss(), 0, 'disabled', True, self.bot.beta))
            # XP cards
            cursor.execute(query, (now, 'xp.generated_cards', self.xp_cards["generated"], 0, 'cards/min', True, self.bot.beta))
            cursor.execute(query, (now, 'xp.sent_cards', self.xp_cards["sent"], 0, 'cards/min', True, self.bot.beta))
            self.xp_cards["generated"] = 0
            self.xp_cards["sent"] = 0
            # Latency - RAM usage - CPU usage
            ram = round(self.process.memory_info()[0]/2.**30, 3)
            if latency := await self.get_list_usage(self.latency_records):
                cursor.execute(query, (now, 'perf.latency', latency, 1, 'ms', False, self.bot.beta))
            cursor.execute(query, (now, 'perf.ram', ram, 1, 'Gb', False, self.bot.beta))
            cpu = await self.get_list_usage(self.cpu_records)
            if cpu is not None:
                cursor.execute(query, (now, 'perf.cpu', cpu, 1, '%', False, self.bot.beta))
            # Unavailable guilds
            unav, total = 0, 0
            for guild in self.bot.guilds:
                unav += guild.unavailable
                total += 1
            cursor.execute(query, (now, 'guilds.unavailable', round(unav/total, 3)*100, 1, '%', False, self.bot.beta))
            cursor.execute(query, (now, 'guilds.total', total, 0, 'guilds', True, self.bot.beta))
            del unav, total
            # antiscam warn/deletions
            cursor.execute(query, (now, 'antiscam.warning', self.antiscam["warning"], 0, 'warning/min', True, self.bot.beta))
            cursor.execute(query, (now, 'antiscam.deletion', self.antiscam["deletion"], 0, 'deletion/min', True, self.bot.beta))
            self.antiscam["warning"] = self.antiscam["deletion"] = 0
            # tickets creation
            cursor.execute(query, (now, 'tickets.creation', self.ticket_events["creation"], 0, 'tickets/min', True, self.bot.beta))
            self.ticket_events["creation"] = 0
            # username changes
            cursor.execute(query, (now, 'usernames.guild', self.usernames["guild"], 0, 'nicknames/min', True, self.bot.beta))
            self.usernames["guild"] = 0
            cursor.execute(query, (now, 'usernames.user', self.usernames["user"], 0, 'usernames/min', True, self.bot.beta))
            self.usernames["user"] = 0
            cursor.execute(query, (now, 'usernames.deleted', self.usernames["deleted"], 0, 'usernames/min', True, self.bot.beta))
            self.usernames["deleted"] = 0
            # Dailies points
            await self.db_record_dailies_values(now)
            # Events points
            await self.db_record_eventpoints_values(now)
            # Push everything
            cnx.commit()
        except mysql.connector.errors.IntegrityError as err: # duplicate primary key
            self.bot.log.warning(f"Stats loop iteration cancelled: {err}")
        # if something goes wrong, we still have to close the cursor
        cursor.close()

    @sql_loop.before_loop
    async def before_sql_loop(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()

    @sql_loop.error
    async def on_sql_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "When sending SQL stats")

    async def get_stats(self, variable: str, minutes: int) -> typing.Union[int, float, str, None]:
        """Get the sum of a certain variable in the last X minutes"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        cursor.execute('SELECT variable, SUM(value) as value, type FROM `statsbot`.`zbot` WHERE variable = %s AND date BETWEEN (DATE_SUB(UTC_TIMESTAMP(),INTERVAL %s MINUTE)) AND UTC_TIMESTAMP() AND beta=%s', (variable, minutes, self.bot.beta))
        result: list[dict] = list(cursor)
        cursor.close()
        if len(result) == 0:
            return None
        result = result[0]
        if result['type'] == 0:
            return int(result['value'])
        elif result['type'] == 1:
            return float(result['value'])
        else:
            return result['value']

    @tasks.loop(minutes=4)
    async def status_loop(self):
        "Send average latency to zbot.statuspage.io every 4min"
        if self.bot.beta or not self.bot.internal_loop_enabled:
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
            params["data"]["value"] = psutil.virtual_memory().available
            async with session.post(
                "https://api.statuspage.io/v1/pages/g9cnphg3mhm9/metrics/72bmf4nnqbwb/data",
                    json=params) as response:
                response.raise_for_status()
                self.bot.log.debug(
                    f"StatusPage API returned {response.status} for {params} (available RAM)")

    @status_loop.before_loop
    async def before_status_loop(self):
        await self.bot.wait_until_ready()

    @status_loop.error
    async def on_status_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "When sending stats to statuspage.io")


async def setup(bot):
    await bot.add_cog(BotStats(bot))
