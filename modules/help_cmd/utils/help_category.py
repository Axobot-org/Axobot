from typing import TYPE_CHECKING

import discord

from core.bot_classes import MyContext

from .help_all import all_commands
from .utils import get_embed_color, get_embed_footer, get_send_callback

if TYPE_CHECKING:
    from ..help_cmd import Help as HelpCog

async def help_category_command(cog: "HelpCog", ctx: MyContext, category_id: str):
    "Generate embed fields to describe all commands of a specific category"
    send = await get_send_callback(ctx)
    bot_commands = cog.bot.tree.get_commands(guild=None, type=discord.AppCommandType.chat_input)
    if category_id == "unclassed":
        referenced_commands = {x for v in cog.commands_data.values() for x in v["commands"]}
        commands_list = [c for c in bot_commands if c.name not in referenced_commands]
    else:
        commands_list = [c for c in bot_commands if c.name in cog.commands_data[category_id]["commands"]]
    fields = await all_commands(cog, ctx, commands_list, compress=False)
    embed_color = get_embed_color(ctx)
    embed = discord.Embed(color=embed_color)
    embed.set_footer(text=await get_embed_footer(ctx))
    for field in fields:
        embed.add_field(**field)
    await send(embed=embed)
