from datetime import datetime, timezone
import os
from time import time
from discord.ext import commands, tasks
import psutil

from utils import MyContext, zbot


class BotStats(commands.Cog):
    """Hey, I'm a test cog! Happy to meet you :wave:"""

    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = 'bot_stats'
        self.received_events = {'CMD_USE': 0}
        self.commands_uses = dict()
        self.rss_stats = {'checked': 0, 'messages': 0, 'errors': 0}
        self.loop.start()

    def cog_unload(self):
        self.loop.cancel()

    @commands.Cog.listener()
    async def on_socket_response(self, msg: dict):
        """Count when a websocket event is received"""
        if msg['t'] is None:
            return
        nbr = self.received_events.get(msg['t'], 0)
        self.received_events[msg['t']] = nbr + 1

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
        now = time()
        # remove seconds and less
        now = datetime.fromtimestamp(now-now % 60, tz=timezone.utc)
        # prepare erquests
        query = "INSERT INTO zbot VALUES (%s, %s, %s, %s, %s, %s);"
        cnx = self.bot.cnx_stats
        cursor = cnx.cursor(dictionary=True)
        try:
            # WS events stats
            for k, v in self.received_events.items():
                cursor.execute(query, (now, 'wsevent.'+k, v, 0, 'event/min', self.bot.beta))
                self.received_events[k] = 0
            # Commands usages stats
            for k, v in self.commands_uses.items():
                cursor.execute(query, (now, 'cmd.'+k, v, 0, 'cmd/min', self.bot.beta))
            self.commands_uses.clear()
            # RSS stats
            for k, v in self.rss_stats.items():
                cursor.execute(query, (now, 'rss.'+k, v, 0, k, self.bot.beta))
            # Latency - RAM usage - CPU usage
            latency = round(self.bot.latency*1000, 3)
            ram = round(py.memory_info()[0]/2.**30, 3)
            cpu = py.cpu_percent(interval=1)
            cursor.execute(
                query, (now, 'perf.latency', latency, 1, 'ms', self.bot.beta))
            cursor.execute(query, (now, 'perf.ram', ram, 1, 'Gb', self.bot.beta))
            cursor.execute(query, (now, 'perf.cpu', cpu, 1, '%', self.bot.beta))
            # Unavailable guilds
            unav, total = 0, 0
            for g in self.bot.guilds:
                unav += g.unavailable
                total += 1
            cursor.execute(query, (now, 'guilds.unavailable', round(unav/total, 3)*100, 1, '%', self.bot.beta))
            del unav, total
            # Push everything
            cnx.commit()
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e)
        # if something goes wrong, we still have to close the cursor
        cursor.close()

    @loop.before_loop
    async def before_printer(self):
        """Wait until the bot is ready"""
        await self.bot.wait_until_ready()


def setup(bot):
    bot.add_cog(BotStats(bot))
