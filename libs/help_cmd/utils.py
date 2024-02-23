from typing import Optional, TypedDict, Union

import discord

from libs.bot_classes import MyContext
from libs.translator import LOCALES_MAP


class FieldData(TypedDict):
    "Represents an embed field"
    name: str
    value: str
    inline: bool

def get_embed_color(ctx: MyContext):
    "Get the color to use for help embeds"
    if ctx.guild is None:
        return discord.Colour(0xD6FFA9)
    if ctx.guild.me.color != discord.Colour.default():
        return ctx.guild.me.color
    return discord.Colour(0x7ED321)

async def get_embed_footer(ctx: MyContext):
    "Get the footer text to use for help embeds"
    return (await ctx.bot._(ctx.channel, "help.footer")).format('/')

async def get_discord_locale(ctx: Union[MyContext, discord.Interaction]):
    "Get the Discord locale to use for a given context"
    bot_locale = await ctx.bot._(ctx.channel, "_used_locale")
    for locale, lang in LOCALES_MAP.items():
        if lang == bot_locale:
            return locale
    return discord.Locale.british_english

async def extract_info(raw_description: str) -> tuple[Optional[str], list[str], Optional[str]]:
    "Split description, examples and documentation link from the given documentation"
    description, examples = [], []
    doc = ""
    for line in raw_description.split("\n\n"):
        line = line.strip()
        if line.startswith("..Example "):
            examples.append(line.replace("..Example ", ""))
        elif line.startswith("..Doc "):
            doc = line.replace("..Doc ", "")
        else:
            description.append(line)
    return (
        x if len(x) > 0 else None
        for x in ("\n\n".join(description), examples, doc)
    )

async def get_send_callback(ctx: MyContext):
    "Get a function to call to send the command result"
    async def _send_interaction(content: Optional[str]=None, *, embed: Optional[discord.Embed] = None):
        await ctx.interaction.followup.send(content, embed=embed)

    async def _send_default(content: Optional[str]=None, *, embed: Optional[discord.Embed] = None):
        await destination.send(content, embed=embed)

    destination = None
    if ctx.guild is not None:
        if await _should_dm(ctx):
            # if using interaction: return ephemeral message instead
            if ctx.interaction:
                if not ctx.interaction.response.is_done():
                    await ctx.interaction.response.defer(ephemeral=True)
                return _send_interaction
            # if in guild but should DM: delete the invocation message
            await ctx.message.delete(delay=0)
        # if slash in guild but not private
        elif ctx.interaction:
            if not ctx.interaction.response.is_done():
                await ctx.interaction.response.defer()
            return _send_interaction
        else:
            destination = ctx.channel
    # if slash in DM
    elif ctx.interaction:
        if not ctx.interaction.response.is_done():
            await ctx.interaction.response.defer()
        return _send_interaction

    if destination is None:
        # if DM: make sure DM channel exists
        await ctx.message.author.create_dm()
        destination = ctx.message.author.dm_channel

    return _send_default


async def _should_dm(ctx: MyContext) -> bool:
    "Check if the answer should be sent in DM or in current channel"
    if ctx.guild is None or not ctx.bot.database_online:
        return False
    return await ctx.bot.get_config(ctx.guild.id, 'help_in_dm')
