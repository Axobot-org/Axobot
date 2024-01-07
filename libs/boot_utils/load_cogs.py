import sys
from typing import TYPE_CHECKING

import discord
from LRFutils import progress

if TYPE_CHECKING:
    from libs.bot_classes import Axobot


async def load_cogs(bot: "Axobot"):
    "Load the bot modules"
    initial_extensions = [
        'fcts.languages',
        'fcts.admin',
        'fcts.help_cmd',
        'fcts.antiraid',
        'fcts.antiscam',
        'fcts.bitly',
        'fcts.bot_events',
        'fcts.bot_info',
        'fcts.bot_stats',
        'fcts.cases',
        'fcts.embeds',
        'fcts.errors',
        'fcts.events',
        'fcts.fun',
        # 'fcts.halloween',
        'fcts.info',
        'fcts.library',
        'fcts.minecraft',
        'fcts.moderation',
        'fcts.partners',
        'fcts.perms',
        'fcts.poll',
        'fcts.reloads',
        'fcts.roles_management',
        'fcts.roles_react',
        'fcts.rss',
        'fcts.s_backups',
        'fcts.serverlogs',
        'fcts.serverconfig',
        'fcts.tickets',
        'fcts.tictactoe',
        'fcts.timers',
        'fcts.twitch',
        'fcts.users_cache',
        'fcts.users',
        'fcts.utilities',
        'fcts.voice_channels',
        'fcts.voice_msg',
        'fcts.welcomer',
        'fcts.xp'
    ]
    progress_bar = progress.Bar(
        max=len(initial_extensions),
        width=60,
        prefix="Loading extensions",
        eta=False,
        show_duration=False
    )

    # Here we load our extensions (cogs) listed above in [initial_extensions]
    count = 0
    for i, extension in enumerate(initial_extensions):
        progress_bar(i)
        try:
            await bot.load_extension(extension)
        except discord.DiscordException:
            bot.log.critical("Failed to load extension %s", extension, exc_info=True)
            count += 1
        if count  > 0:
            bot.log.critical("%s modules not loaded\nEnd of program", count)
            sys.exit()
    progress_bar(len(initial_extensions), stop=True)
