from typing import TYPE_CHECKING, Optional

import discord
from discord.ext import commands

from libs.bot_classes import MyContext

from .txt_cmd_utils import (get_command_desc_translation,
                            get_command_description,
                            get_command_name_translation,
                            get_command_signature)
from .utils import (FieldData, get_embed_color, get_embed_footer,
                    get_send_callback)

if TYPE_CHECKING:
    from fcts.help_cmd import Help as HelpCog


def sort_by_name(cmd: commands.Command):
    return cmd.name


async def help_text_cmd_command(cog: "HelpCog", ctx: MyContext, command: commands.Command):
    "Generate embed fields to describe usage of one command or commands group"
    send = await get_send_callback(ctx)
    syntax, fields = await _generate_command_fields(cog, ctx, command)
    embed_color = get_embed_color(ctx)
    embed = discord.Embed(title=syntax, color=embed_color)
    embed.set_footer(text=await get_embed_footer(ctx))
    for field in fields:
        embed.add_field(**field)
    await send(embed=embed)


async def _generate_command_fields(cog: "HelpCog", ctx: MyContext, command: commands.Command):
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
    if isinstance(command, commands.Group):
        syntax += " ..."
        if subcommands_field := await _generate_subcommands_field(ctx, command):
            fields.append(subcommands_field)
    # Aliases
    if aliases_field := await _generate_aliases_field(ctx, command):
        fields.append(aliases_field)
    # Disabled and checks
    if warnings_field := await _generate_warnings_field(ctx, command):
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

async def _generate_aliases_field(ctx: MyContext, command: commands.Command) -> Optional[FieldData]:
    "Generate an embed field to list aliases of a command"
    if not command.aliases:
        return None
    title = await ctx.bot._(ctx.channel, "help.aliases")
    if command.full_parent_name:
        text = command.full_parent_name + " " + " - ".join(command.aliases)
    else:
        text = " - ".join(command.aliases)
    return {
        "name": title,
        "value": text,
        "inline": False
    }

async def _generate_subcommands_field(ctx: MyContext, cmd: commands.Group) -> Optional[FieldData]:
    "Generate an embed field to describe the subcommands of a commands group"
    subcmds = ""
    subs_cant_show = 0
    explored_subcommands = []
    for subcommand in sorted(cmd.all_commands.values(), key=sort_by_name):
        try:
            if (not subcommand.hidden) and subcommand.enabled and \
                subcommand.name not in explored_subcommands and await subcommand.can_run(ctx):
                if len(subcmds) > 950:
                    subs_cant_show += 1
                else:
                    name = await get_command_name_translation(ctx, subcommand)
                    if (description := await get_command_desc_translation(ctx, subcommand)) is None:
                        description = subcommand.short_doc
                    desc = f"*({description})*" if len(description) > 0 else ""
                    subcmds += f"\n• {name} {desc}"
                    explored_subcommands.append(subcommand.name)
        except commands.CommandError:
            pass
    if subs_cant_show > 0:
        subcmds += "\n" + await ctx.bot._(ctx.channel, 'help.more-subcmds', count=subs_cant_show)
    if len(subcmds) > 0:
        return {
            "name": await ctx.bot._(ctx.channel, "help.subcmds"),
            "value": subcmds,
            "inline": False
        }

async def _generate_warnings_field(ctx: MyContext, command: commands.Command) -> Optional[FieldData]:
    "Generate an embed field to list warnings and checks about a command usage"
    # Is enabled
    warnings: list[str] = []
    if not command.enabled:
        warnings.append(await ctx.bot._(ctx.channel, "help.not-enabled"))
    if len(command.checks) > 0:
        maybe_coro = discord.utils.maybe_coroutine
        for check in command.checks:
            try:
                if 'guild_only.<locals>.predicate' in str(check):
                    check_name = 'guild_only'
                elif 'is_owner.<locals>.predicate' in str(check):
                    check_name = 'is_owner'
                elif 'bot_has_permissions.<locals>.predicate' in str(check):
                    check_name = 'bot_has_permissions'
                elif '_has_permissions.<locals>.predicate' in str(check):
                    check_name = 'has_permissions'
                else:
                    check_name = check.__name__
                check_msg_tr = await ctx.bot._(ctx.channel, f'help.check-desc.{check_name}')
                if 'help.check-desc' not in check_msg_tr:
                    try:
                        pass_check = await maybe_coro(check, ctx)
                    except Exception:
                        pass_check = False
                    if pass_check:
                        warnings.append(
                            "✅ "+check_msg_tr[0])
                    else:
                        warnings.append('❌ '+check_msg_tr[1])
                else:
                    ctx.bot.dispatch("error", ValueError(f"No description for help check {check_name} ({check})"))
            except Exception as err:
                ctx.bot.dispatch("error", err, f"While checking {check} in help")
    if warnings:
        return {
            "name": await ctx.bot._(ctx.channel, "help.warning"),
            "value": "\n".join(warnings),
            "inline": False
        }

async def _generate_command_category_field(cog: "HelpCog", ctx: MyContext, command: commands.Command) -> FieldData:
    "Generate an embed field to describe the category of a command"
    category = "unclassed"
    for key, data in cog.commands_data.items():
        categ_commands = data['commands']
        if command.name in categ_commands or (
                command.full_parent_name and command.full_parent_name.split(" ")[0] in categ_commands):
            category = key
            break
    emoji = cog.commands_data[category]['emoji']
    category = emoji + "  " + (await cog.bot._(ctx.channel, f"help.categories.{category}")).capitalize()
    return {
        "name": (await ctx.bot._(ctx.channel, "misc.category")).capitalize(),
        "value": category,
        "inline": False
    }
