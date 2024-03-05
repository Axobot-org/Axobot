import re

import discord

PRIVATE_GUILD_ID = discord.Object(625316773771608074)
SUPPORT_GUILD_ID = discord.Object(356067272730607628)

DISCORD_INVITE_REGEX = re.compile(
    r'(?:https?://)?(?:www[.\s])?((?:discord[.\s](?:gg|io|li(?:nk)?)|discord\.me|discordapp\.com/invite\
        |discord\.com/invite|dsc\.gg)[/\s]{1,3}[\w-]{2,27}(?!\w))'
)
