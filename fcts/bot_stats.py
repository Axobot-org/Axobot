import os
import typing
from math import isinf

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

    async def cog_load(self):
        self.loop.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.loop.cancel() # pylint: disable=no-member

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
    async def loop(self):
        """Send our stats every minute"""
        if not (self.bot.alerts_enabled and self.bot.database_online):
            return
        self.bot.log.debug("Stats loop triggered")
        # get current process for performances logs
        py = psutil.Process(os.getpid())
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
            # Latency - RAM usage - CPU usage
            latency = round(self.bot.latency*1000, 3)
            ram = round(py.memory_info()[0]/2.**30, 3)
            cpu = py.cpu_percent(interval=1)
            if not isinf(latency):
                cursor.execute(query, (now, 'perf.latency', latency, 1, 'ms', False, self.bot.beta))
            cursor.execute(query, (now, 'perf.ram', ram, 1, 'Gb', False, self.bot.beta))
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
        except Exception as err:
            await self.bot.get_cog("Errors").on_error(err)
        # if something goes wrong, we still have to close the cursor
        cursor.close()

    @loop.before_loop
    async def before_printer(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()


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


async def setup(bot):
    await bot.add_cog(BotStats(bot))
