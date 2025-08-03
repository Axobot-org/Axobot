import re

import discord

PRIVATE_GUILD_ID = discord.Object(625316773771608074)
SUPPORT_GUILD_ID = discord.Object(356067272730607628)

DISCORD_INVITE_REGEX = re.compile(
    r'(?:https?://)?(?:www[.\s])?((?:discord[.\s](?:gg|io|li(?:nk)?)|discord\.me|discordapp\.com/invite'
    r'|discord\.com/invite|dsc\.gg)[/\s]{1,3}[\w-]{2,27}(?!\w))'
)

IGNORED_GUILDS = [
    471361000126414848, # Zbot emojis 1
    513087032331993090, # Zbot emojis 2
    500648624204808193, # Emergency server
    446425626988249089, # Bots on Discord
    568567800910839811, # Delly
]
