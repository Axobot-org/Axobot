import sys
from typing import TYPE_CHECKING

import discord
from LRFutils import progress

if TYPE_CHECKING:
    from core.bot_classes import Axobot


async def load_cogs(bot: "Axobot"):
    "Load the bot modules"
    initial_modules = [
        "languages",
        "admin",
        "help_cmd",
        "antiraid",
        "antiscam",
        "bitly",
        "bot_events",
        "bot_info",
        "bot_stats",
        "cases",
        "emojis_management",
        "errors",
        "events",
        "fun",
        # "halloween",
        "info",
        "minecraft",
        "moderation",
        "partners",
        "perms",
        "poll",
        "quote",
        "roles_management",
        "roles_react",
        "rss",
        "s_backups",
        "serverlogs",
        "serverconfig",
        "tickets",
        "tictactoe",
        "timers",
        "twitch",
        "users_cache",
        "users",
        "voice_channels",
        "voice_msg",
        "welcomer",
        "xp"
    ]
    progress_bar = progress.Bar(
        max=len(initial_modules),
        width=60,
        prefix="Loading extensions",
        eta=False,
        show_duration=False
    )

    # load utilities core cog
    await bot.load_extension("core.utilities")

    # Here we load our extensions (cogs) listed above in [initial_extensions]
    count = 0
    for i, module_name in enumerate(initial_modules):
        progress_bar(i)
        try:
            await bot.load_module(module_name)
        except discord.DiscordException:
            bot.log.critical("Failed to load extension %s", module_name, exc_info=True)
            count += 1
        if count > 0:
            bot.log.critical("%s modules not loaded\nEnd of program", count)
            sys.exit()
    progress_bar(len(initial_modules), stop=True)
