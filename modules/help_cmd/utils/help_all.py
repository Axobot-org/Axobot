from typing import TYPE_CHECKING, Iterable

import discord

from core.bot_classes import MyContext

from .slash_cmd_utils import get_command_inline_desc
from .utils import (FieldData, get_embed_color, get_embed_footer,
                    get_send_callback)

if TYPE_CHECKING:
    from ..help_cmd import Help as HelpCog


def sort_by_name(cmd: discord.app_commands.Command):
    return cmd.name

async def help_all_command(cog: "HelpCog", ctx: MyContext):
    "Show all commands and groups"
    send = await get_send_callback(ctx)
    compress: bool = await cog.bot.get_config(ctx.guild.id, 'compress_help') if ctx.guild else False
    commands = cog.bot.tree.get_commands(guild=None, type=discord.AppCommandType.chat_input)
    fields = await all_commands(cog, ctx, commands, compress=compress)
    if ctx.guild is None:
        title = await cog.bot._(ctx.channel, "help.embed_title_dm")
    else:
        title = await cog.bot._(ctx.channel, "help.embed_title")
    embed_color = get_embed_color(ctx)
    embed = discord.Embed(title=title, color=embed_color)
    embed.set_footer(text=await get_embed_footer(ctx))
    for field in fields:
        embed.add_field(**field)
    await send(embed=embed)


async def all_commands(cog: "HelpCog", ctx: MyContext, commands_list: Iterable[discord.app_commands.Command],
                        compress: bool) -> list[FieldData]:
    "Generate embed fields to describe all commands, grouped by category"
    categories: dict[str, list[str]] = { x: [] for x in cog.commands_data.keys() }
    commands_list = sorted(list(commands_list), key=sort_by_name)
    # group commands by category
    for command in commands_list:
        if compress:
            cmd_desc = ""
        else:
            cmd_desc = await get_command_inline_desc(ctx, command)
        for category_id, category in cog.commands_data.items():
            if command.name in category["commands"]:
                categories[category_id].append(cmd_desc)
                break
        else:
            categories["unclassed"].append(cmd_desc)
    # generate "compressed" embed fields
    if compress:
        return await _generate_compressed_help(cog, ctx, categories)
    # generate "normal" embed fields
    return await _generate_normal_help(cog, ctx, categories)

async def _generate_compressed_help(cog: "HelpCog", ctx: MyContext, categories: dict[str, list[str]]):
    "Generate embed fields to list all command categories, with how many commands they contain"
    fields: list[FieldData] = []
    for category_id, category_commands in categories.items():
        if not category_commands:
            continue
        category_name = await cog.bot._(ctx.channel, f"help.categories.{category_id}")
        emoji = cog.commands_data[category_id]["emoji"]
        title = f"{emoji}  __**{category_name.capitalize()}**__"
        description = await cog.bot._(
            ctx.channel, "help.cmd-count", count=len(category_commands), p='/', cog=category_id
        )
        fields.append({"name": title, "value": description, "inline": False})
    return fields

async def _generate_normal_help(cog: "HelpCog", ctx: MyContext, categories: dict[str, list[str]]):
    "Generate embed fields to list all commands in each category"
    fields: list[FieldData] = []
    for category_id, category_commands in categories.items():
        if not category_commands:
            continue
        category_name = await cog.bot._(ctx.channel, f"help.categories.{category_id}")
        emoji = cog.commands_data[category_id]["emoji"]
        title = f"{emoji}  __**{category_name.capitalize()}**__"
        # make sure the commands list fits in one field
        field_commands: list[str] = []
        for command in category_commands:
            # if field is full, add it to the fields list and start a new one
            if len("\n".join(field_commands + [command])) > 1024:
                fields.append({"name": title, "value": "\n".join(field_commands), "inline": False})
                field_commands = []
            field_commands.append(command)
        # add remaining commands into a new field
        if field_commands:
            fields.append({"name": title, "value": "\n".join(field_commands), "inline": False})
    return fields
