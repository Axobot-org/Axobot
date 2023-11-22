from typing import TypedDict

import discord

from libs.bot_classes import MyContext


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
    ft = await ctx.bot._(ctx.channel, "help.footer")
    prefix = await ctx.bot.prefix_manager.get_prefix(ctx.guild)
    return ft.format(prefix)

async def get_destination(ctx: MyContext):
    "Get the destination where to send the help message, based on context and guild settings"
    if ctx.guild is not None:
        if not await _should_dm(ctx):
            return ctx.message.channel
        # if in guild but should DM: delete the invocation message
        await ctx.message.delete(delay=0)
    # if DM: make sure DM channel exists
    await ctx.message.author.create_dm()
    return ctx.message.author.dm_channel


async def _should_dm(ctx: MyContext) -> bool:
    "Check if the answer should be sent in DM or in current channel"
    if ctx.guild is None or not ctx.bot.database_online:
        return False
    return await ctx.bot.get_config(ctx.guild.id, 'help_in_dm')
