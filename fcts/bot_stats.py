import math
import typing
import aiohttp

import mysql
import psutil
from discord.ext import commands, tasks
from libs.classes import MyContext, Zbot

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
        self.rss_stats = {'checked': 0, 'messages': 0, 'errors': 0}
        self.xp_cards = 0
        self.process = psutil.Process()
        self.cpu_records: list[float] = []
        self.latency_records: list[int] = []
        self.statuspage_header = {"Content-Type": "application/json", "Authorization": "OAuth " + self.bot.others["statuspage"]}

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

    @tasks.loop(seconds=30)
    async def record_ws_latency(self):
        "Record the websocket latency for later use"
        if self.bot.latency is None or math.isnan(self.bot.latency):
            return
        try:
            self.latency_records.append(round(self.bot.latency*1000))
        except OverflowError: # Usually because latency is infinite
            self.latency_records.append(10e6)
        if len(self.latency_records) > 2:
            # if the list becomes too long (over 1min), cut it
            self.latency_records = self.latency_records[-2:]

    @record_ws_latency.error
    async def on_record_latency_error(self, error: Exception):
        self.bot.dispatch("error", error, "When collecting WS latency")

    async def get_list_usage(self, origin: list):
        "Calculate the average list value"
        if len(origin) > 0:
            avg = round(sum(origin)/len(origin), 1)
            return avg

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
        query = "INSERT INTO zbot VALUES (%s, %s, %s, %s, %s, %s, %s);"
        cnx = self.bot.cnx_stats
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
                cursor.execute(query, (now, 'rss.'+k, v, 0, k, True, self.bot.beta))
            # XP cards
            cursor.execute(query, (now, 'xp.generated_cards', self.xp_cards, 0, 'cards/min', True, self.bot.beta))
            self.xp_cards = 0
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
            del unav, total
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
        cnx = self.bot.cnx_stats
        cursor = cnx.cursor(dictionary=True)
        cursor.execute('SELECT variable, SUM(value) as value, type FROM `zbot` WHERE variable = %s AND date BETWEEN (DATE_SUB(UTC_TIMESTAMP(),INTERVAL %s MINUTE)) AND UTC_TIMESTAMP() AND beta=%s', (variable, minutes, self.bot.beta))
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

    @status_loop.error
    async def on_status_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "When sending stats to statuspage.io")


async def setup(bot):
    await bot.add_cog(BotStats(bot))
