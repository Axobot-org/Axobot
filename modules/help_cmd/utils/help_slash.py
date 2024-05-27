from typing import TYPE_CHECKING

import discord
from discord.app_commands import Command, Group

from core.bot_classes import MyContext

from .slash_cmd_utils import (get_command_desc_translation,
                              get_command_description,
                              get_command_name_translation,
                              get_command_signature)
from .utils import (FieldData, generate_warnings_field, get_embed_color,
                    get_embed_footer, get_send_callback)

if TYPE_CHECKING:
    from ..help_cmd import Help as HelpCog

AppCommandOrGroup = Command | Group

def sort_by_name(cmd: AppCommandOrGroup):
    return cmd.name


async def help_slash_cmd_command(cog: "HelpCog", ctx: MyContext, command: AppCommandOrGroup):
    "Generate embed fields to describe usage of one command or commands group"
    send = await get_send_callback(ctx)
    syntax, fields = await _generate_command_fields(cog, ctx, command)
    embed_color = get_embed_color(ctx)
    embed = discord.Embed(title=syntax, color=embed_color)
    embed.set_footer(text=await get_embed_footer(ctx))
    for field in fields:
        embed.add_field(**field)
    await send(embed=embed)


async def _generate_command_fields(cog: "HelpCog", ctx: MyContext, command: AppCommandOrGroup):
    "Generate embed fields to describe usage of one command or commands group"
    fields: list[FieldData] = []
    desc, examples, doc = await get_command_description(ctx, command)
    # Syntax
    syntax = await get_command_signature(ctx, command)
    # Description
    fields.append({
        "name": await ctx.bot._(ctx.channel, "help.description"),
        "value": desc,
        "inline": False
    })
    # Examples
    if examples:
        fields.append({
            "name": (await ctx.bot._(ctx.channel, "misc.example", count=len(examples))).capitalize(),
            "value": "\n".join(examples),
            "inline": False
        })
    # Subcommands
    if isinstance(command, Group):
        syntax += " ..."
        if subcommands_field := await _generate_subcommands_field(ctx, command):
            fields.append(subcommands_field)
    # Disabled and checks
    if warnings_field := await generate_warnings_field(ctx, command):
        fields.append(warnings_field)
    # Documentation URL
    if doc is not None:
        doc_url = cog.doc_url + doc
        fields.append({
            "name": (await ctx.bot._(ctx.channel, "misc.doc")).capitalize(),
            "value": doc_url,
            "inline": False
        })
    # Category
    fields.append(await _generate_command_category_field(cog, ctx, command))
    return syntax, fields

async def _generate_subcommands_field(ctx: MyContext, cmd: Group) -> FieldData | None:
    "Generate an embed field to describe the subcommands of a commands group"
    subcmds = ""
    subs_cant_show = 0
    explored_subcommands = []
    for subcommand in sorted(cmd.commands, key=sort_by_name):
        if subcommand.name not in explored_subcommands:
            if len(subcmds) > 950:
                subs_cant_show += 1
            else:
                name = await get_command_name_translation(ctx, subcommand)
                if (description := await get_command_desc_translation(ctx, subcommand)) is None:
                    description = subcommand.description.split('\n')[0].strip()
                desc = f"*({description})*" if len(description) > 0 else ""
                subcmds += f"\n• {name} {desc}"
                explored_subcommands.append(subcommand.name)
    if subs_cant_show > 0:
        subcmds += "\n" + await ctx.bot._(ctx.channel, 'help.more-subcmds', count=subs_cant_show)
    if len(subcmds) > 0:
        return {
            "name": await ctx.bot._(ctx.channel, "help.subcmds"),
            "value": subcmds,
            "inline": False
        }

async def _generate_command_category_field(cog: "HelpCog", ctx: MyContext, command: AppCommandOrGroup) -> FieldData:
    "Generate an embed field to describe the category of a command"
    category = "unclassed"
    for key, data in cog.commands_data.items():
        categ_commands = data['commands']
        root_name = command.root_parent.name if command.root_parent else command.name
        if root_name in categ_commands:
            category = key
            break
    emoji = cog.commands_data[category]['emoji']
    category = emoji + "  " + (await cog.bot._(ctx.channel, f"help.categories.{category}")).capitalize()
    return {
        "name": (await ctx.bot._(ctx.channel, "misc.category")).capitalize(),
        "value": category,
        "inline": False
    }
