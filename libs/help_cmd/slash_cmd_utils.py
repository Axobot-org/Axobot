from typing import Optional, Union

from discord import Locale
from discord.app_commands import Argument as AppArgument
from discord.app_commands import Command, Group
from discord.app_commands.translator import (TranslationContext,
                                             TranslationContextLocation,
                                             locale_str)

from libs.bot_classes import MyContext

from .utils import extract_info, get_discord_locale

AppCommandOrGroup = Union[Command, Group]


async def get_command_inline_desc(ctx: MyContext, cmd: AppCommandOrGroup):
    "Generate a 1-line description with the command name and short desc"
    name = await get_command_name_translation(ctx, cmd)
    short = await get_command_desc_translation(ctx, cmd) or cmd.description.split('\n')[0].strip()
    return f"• **{name}**" + (f"  *{short}*" if short else "")


async def get_command_description(ctx: MyContext, command: AppCommandOrGroup):
    "Get the parsed description of a command"
    if isinstance(command, Group):
        raw_desc = command.description.strip()
    else:
        raw_desc = command.callback.__doc__ or ""
    desc = Optional[str]
    desc, examples, doc = await extract_info(raw_desc)
    # check for translated description
    if short_desc := await get_command_desc_translation(ctx, command):
        if len(desc.split('\n')) > 1:
            long_desc = '\n'.join(desc.split('\n')[1:]).strip()
            desc = f"{short_desc}\n\n{long_desc}"
    if desc is None:
        desc = await ctx.bot._(ctx.channel, "help.no-desc-cmd")
    return desc, examples, doc

async def get_command_signature(ctx: MyContext, command: AppCommandOrGroup):
    "Get the signature of a command"
    # name
    translated_name = await get_command_full_name_translation(ctx, command)
    # parameters
    signature = await _get_command_params_signature(ctx, command)
    return f"/{translated_name} {signature}".strip()


async def get_command_full_name_translation(ctx: MyContext, command: AppCommandOrGroup):
    "Get the translated command or group name (with parent name if exists)"
    locale = await get_discord_locale(ctx)
    full_name = await get_command_name_translation(ctx, command, locale)
    while command.parent is not None:
        full_name = await get_command_name_translation(ctx, command.parent, locale) + " " + full_name
        command = command.parent
    return full_name

async def get_command_name_translation(ctx: MyContext, command: AppCommandOrGroup, locale: Optional[Locale]=None):
    "Get the translated command or group name (without parent name)"
    locale = locale or await get_discord_locale(ctx)
    if isinstance(command, Group):
        context = TranslationContext(
            TranslationContextLocation.group_name,
            command
        )
    else:
        context = TranslationContext(
            TranslationContextLocation.command_name,
            command
        )
    if translation := await ctx.bot.tree.translator.translate(locale_str(""), locale, context):
        return translation
    return command.qualified_name

async def get_command_desc_translation(ctx: MyContext, command: AppCommandOrGroup):
    "Get the translated command or group description"
    locale = await get_discord_locale(ctx)
    if isinstance(command, Group):
        context = TranslationContext(
            TranslationContextLocation.group_description,
            command
        )
    else:
        context = TranslationContext(
            TranslationContextLocation.command_description,
            command
        )
    return await ctx.bot.tree.translator.translate(locale_str(""), locale, context)


async def _get_command_param_translation(ctx: MyContext, param: AppArgument):
    "Get the translated command parameter name"
    locale = await get_discord_locale(ctx)
    context = TranslationContext(
        TranslationContextLocation.parameter_name,
        param
    )
    return await ctx.bot.tree.translator.translate(locale_str(param.name), locale, context) or param.name

async def _get_command_params_signature(ctx: MyContext, command: AppCommandOrGroup):
    "Returns a POSIX-like signature useful for help command output."
    if isinstance(command, Group) or not command.parameters:
        return ''
    result = []
    for param in command.parameters:
        name = await _get_command_param_translation(ctx, param)
        if param.required:
            result.append(f'<{name}>')
        else:
            result.append(f'[{name}]')

    return ' '.join(result)
