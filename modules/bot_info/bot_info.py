import glob
import os
import sys
from typing import Literal

import discord
import psutil
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot
from core.bot_classes.consts import IGNORED_GUILDS
from core.checks import checks
from core.formatutils import FormatUtils
from docs import conf


class BotInfo(commands.Cog):
    "Commands to get information about the bot"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_info"
        self.bot_version = conf.release + ('a' if bot.beta else '')
        self.process = psutil.Process()
        self.process.cpu_percent()
        self.codelines: int | None = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self.refresh_code_lines_count()


    async def refresh_code_lines_count(self):
        """Count lines of Python code in the current folder

        Comments and empty lines are ignored."""
        count = 0
        path = os.getcwd() + "/**/*.py"
        for filename in glob.iglob(path, recursive=True):
            if "/env/" in filename or not filename.endswith(".py"):
                continue
            with open(filename, 'r', encoding="utf-8") as file:
                for line in file.read().split("\n"):
                    cleaned_line = line.strip()
                    if len(cleaned_line) > 2 and not (cleaned_line.startswith('#') or cleaned_line.startswith('"')):
                        count += 1
        self.codelines = count

    async def get_ignored_guilds(self) -> list[int]:
        "Get the list of ignored guild IDs"
        if self.bot.database_online:
            if (utils_cog := self.bot.get_cog("Utilities")) is None:
                raise RuntimeError("Utilities cog not loaded, cannot get ignored guilds")
            config = await utils_cog.get_bot_infos()
            if "banned_guilds" not in config.keys():
                await utils_cog.get_bot_infos()
            return [
                int(gid)
                for gid in config["banned_guilds"].split(";")
                if len(gid) > 0
            ] + IGNORED_GUILDS
        return []

    async def get_guilds_count(self, ignored_guilds: list[int] | None = None) -> int:
        "Get the number of guilds where the bot is"
        if ignored_guilds is None:
            if self.bot.database_online:
                ignored_guilds = await self.get_ignored_guilds()
            else:
                return len(self.bot.guilds)
        return len([x for x in self.bot.guilds if x.id not in ignored_guilds])

    @app_commands.command(name="stats")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(3, 60)
    async def stats_main(self, interaction: discord.Interaction, category: Literal["general", "commands"]="general"):
        """Display some statistics about the bot

        ..Doc infos.html#statistics"""
        if category == "general":
            await self.stats_general(interaction)
        elif category == "commands":
            await self.stats_commands(interaction)

    async def stats_general(self, interaction: discord.Interaction):
        "General statistics about the bot"
        await interaction.response.defer()
        # Bot version
        bot_version = f"[{self.bot_version}]({self.bot.doc_url}changelog.html#v{self.bot_version.replace('.', '-').rstrip('a')})"
        # Python version
        python_version = sys.version_info
        f_python_version = str(python_version.major)+"."+str(python_version.minor)
        # API ping
        latency = round(self.bot.latency*1000, 2)
        # RAM/CPU
        ram_usage = round(self.process.memory_info()[0]/2.**30,3)
        stats_cog = self.bot.get_cog("BotStats")
        cpu: float = await stats_cog.get_list_usage(stats_cog.bot_cpu_records) or 0.0 if stats_cog else 0
        # Guilds count
        ignored_guilds = await self.get_ignored_guilds()
        len_servers = await self.get_guilds_count(ignored_guilds)
        # Languages
        if (config_cog := self.bot.get_cog("ServerConfig")) is None:
            raise RuntimeError("ServerConfig cog not loaded, cannot get languages")
        langs_list = list((await config_cog.get_enum_usage_stats("language", ignored_guilds)).items())
        langs_list.sort(reverse=True, key=lambda x: x[1])
        lang_total = sum(x[1] for x in langs_list)
        langs_list = " | ".join([f"{x[0]}: {x[1]/lang_total*100:.0f}%" for x in langs_list if x[1] > 0])
        del lang_total
        # Users/bots
        users, bots = self.get_users_nber(ignored_guilds)
        # Total XP
        if self.bot.database_online and (xp_cog := self.bot.get_cog("Xp")):
            total_xp: int | None = await xp_cog.db_get_total_xp() or None
        else:
            total_xp = None
        # Commands within 24h
        cmds_24h: int = (
            await stats_cog.get_sum_stats("wsevent.CMD_USE", 60*24)
            if stats_cog
            else 0
        ) # pyright: ignore[reportAssignmentType]
        # RSS messages within 24h
        rss_msg_24h: int = (
            await stats_cog.get_sum_stats("rss.messages", 60*24)
            if stats_cog
            else 0
        ) # pyright: ignore[reportAssignmentType]
        # number formatter
        lang = await self.bot._(interaction, "_used_locale")
        async def n_format(nbr: int | float | None):
            return await FormatUtils.format_nbr(nbr, lang) if nbr is not None else "0"
        # Generating message
        desc = ""
        for key, var in [
            ("bot_version", bot_version),
            ("servers_count", await n_format(len_servers)),
            ("users_count", (await n_format(users), await n_format(bots))),
            ("codes_lines", await n_format(self.codelines)),
            ("languages", langs_list),
            ("python_version", f_python_version),
            ("lib_version", discord.__version__),
            ("ram_usage", await n_format(ram_usage)),
            ("cpu_usage", await n_format(cpu)),
            ("api_ping", await n_format(latency)),
            ("cmds_24h", await n_format(cmds_24h)),
            ("rss_msg_24h", await n_format(rss_msg_24h)),
            ("total_xp", await n_format(total_xp) + " ")]:
            str_args = {f"v{i}": var[i] for i in range(len(var))} if isinstance(var, tuple | list) else {'v': var}
            desc += await self.bot._(interaction, "info.stats."+key, **str_args) + "\n"
        title = await self.bot._(interaction,"info.stats.title")
        color = self.bot.get_cog("Help").help_color
        embed = discord.Embed(title=title, color=color, description=desc)
        if self.bot.display_avatar:
            embed.set_thumbnail(url=self.bot.display_avatar.with_static_format("png"))
        await interaction.followup.send(embed=embed)

    def get_users_nber(self, ignored_guilds: list[int]):
        "Return the amount of members and the amount of bots in every reachable guild, excepted in ignored guilds"
        members = [x.members for x in self.bot.guilds if x.id not in ignored_guilds]
        members = list(set(x for x in members for x in x)) # filter users
        return len(members), len([x for x in members if x.bot])

    async def stats_commands(self, interaction: discord.Interaction):
        """List the most used commands

        ..Doc infos.html#statistics"""
        await interaction.response.defer()
        forbidden = ["eval", "admin", "test", "bug", "idea", "send_msg"]
        forbidden_where = ", ".join(f"'cmd.{elem}'" for elem in forbidden)
        forbidden_where += ", " + ", ".join(f"'app_cmd.{elem}'" for elem in forbidden)
        commands_limit = 15
        lang = await self.bot._(interaction, "_used_locale")
        # SQL query
        async def do_query(minutes: int | None = None):
            if minutes:
                date_where_clause = "date BETWEEN (DATE_SUB(UTC_TIMESTAMP(), INTERVAL %(minutes)s MINUTE)) AND UTC_TIMESTAMP() AND"
            else:
                date_where_clause = ""
            query = f"""
SELECT
    `all`.`variable`,
    SUBSTRING_INDEX(`all`.`variable`, ".", -1) as cmd,
    SUM(`all`.`value`) as usages
FROM
(
    (
        SELECT
    		`variable`,
	    	`value`
    	FROM `statsbot`.`zbot`
    	WHERE
        	`variable` LIKE "cmd.%" AND
            {date_where_clause}
            `variable` NOT IN ({forbidden_where}) AND
        	`entity_id` = %(entity_id)s
	) UNION ALL (
    	SELECT
        	`variable`,
	    	`value`
    	FROM `statsbot`.`zbot-archives`
    	WHERE
        	`variable` LIKE "cmd.%" AND
            {date_where_clause}
            `variable` NOT IN ({forbidden_where}) AND
        	`entity_id` = %(entity_id)s
	)
) AS `all`
GROUP BY cmd
ORDER BY usages DESC LIMIT %(limit)s"""
            query_args = {"entity_id": self.bot.entity_id, "minutes": minutes, "limit": commands_limit}
            async with self.bot.db_main.read(query, query_args) as query_result:
                pass
            return [row for row in query_result if not any(row["cmd"].startswith(x) for x in forbidden)]

        # in the last 24h
        data_24h = await do_query(60*24)
        text_24h = "• " + "\n• ".join([
            data["cmd"] + ": " + await FormatUtils.format_nbr(data["usages"], lang)
            for data in data_24h
        ])
        title_24h = await self.bot._(interaction, "info.stats-cmds.day")
        # since the beginning
        data_total = await do_query()
        text_total = "• " + "\n• ".join([
            data["cmd"] + ": " + await FormatUtils.format_nbr(data["usages"], lang)
            for data in data_total
        ])
        title_total = await self.bot._(interaction, "info.stats-cmds.total")
        # message title and desc
        title = await self.bot._(interaction, "info.stats-cmds.title")
        desc = await self.bot._(interaction, "info.stats-cmds.description", number=commands_limit)
        # send everything
        emb = discord.Embed(
            title=title,
            description=desc,
            color=self.bot.get_cog("Help").help_color,
        )
        if self.bot.display_avatar:
            emb.set_thumbnail(url=self.bot.display_avatar.with_static_format("png"))
        emb.add_field(name=title_total, value=text_total)
        emb.add_field(name=title_24h, value=text_24h)
        await interaction.followup.send(embed=emb)

    @app_commands.command(name="ping")
    @app_commands.checks.cooldown(5, 45)
    async def rep(self, interaction: discord.Interaction):
        """Get the bot latency

        ..Example ping

        ..Doc infos.html#ping"""
        await interaction.response.send_message("Ping...")
        msg = await interaction.original_response()
        bot_delta = (msg.created_at - interaction.created_at).total_seconds()
        try:
            api_latency = round(self.bot.latency*1000)
        except OverflowError:
            api_latency = "∞"
        await msg.edit(content=await self.bot._(
            interaction, "info.ping.normal",
            bot=round(bot_delta*1000),
            api=api_latency)
        )


    @app_commands.command(name="documentation")
    async def display_doc(self, interaction: discord.Interaction):
        """Get the documentation url"""
        text = self.bot.emojis_manager.customs["readthedocs"] + await self.bot._(interaction,"info.docs") + \
            " https://axobot.rtfd.io"
        if self.bot.entity_id == 1:
            text += "/en/develop"
        await interaction.response.send_message(text)

    @app_commands.command(name="about")
    @app_commands.checks.cooldown(7, 30)
    async def about_cmd(self, interaction: discord.Interaction):
        """Information about the bot

..Doc infos.html#about"""
        if self.bot.user is None:
            raise RuntimeError("Bot user is not initialized, cannot display about information")
        urls = ""
        website = "https://axobeta.zrunner.me" if self.bot.beta else "https://axobot.xyz"
        links = {
            "server": "https://discord.gg/N55zY88",
            "website": website,
            "docs": "https://axobot.rtfd.io/",
            "privacy": website + "/privacy",
            "sponsor": "https://github.com/sponsors/ZRunner",
        }
        for key, url in links.items():
            urls += "\n:arrow_forward: " + await self.bot._(interaction, f"info.about.{key}") + " <" + url + ">"
        command_mentions = {
            f"{name.replace(' ', '_')}_cmd": await self.bot.get_command_mention(name)
            for name in ("help", "config see")
        }
        msg = await self.bot._(interaction, "info.about-main", mention=self.bot.user.mention, links=urls, **command_mentions)
        await interaction.response.send_message(embed=discord.Embed(description=msg, color=16298524))

    @app_commands.command(name="random-tip")
    @app_commands.checks.cooldown(10, 30)
    async def tip(self, interaction: discord.Interaction):
        """Send a random tip or trivia about the bot

        ..Doc fun.html#tip"""
        await interaction.response.send_message(await self.bot.tips_manager.generate_random_tip(interaction))


async def setup(bot: Axobot):
    await bot.add_cog(BotInfo(bot))
