from typing import TypedDict

import discord

from libs.bot_classes import MyContext


class FieldData(TypedDict):
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
