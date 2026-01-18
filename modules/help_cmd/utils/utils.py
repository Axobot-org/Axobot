import inspect
from typing import Any, Callable, TypedDict, Union, get_type_hints

import discord
from discord import app_commands
from discord.ext import commands

from core.bot_classes import MyContext
from core.bot_classes.axobot import Axobot
from core.translator import LOCALES_MAP
from core.type_utils import channel_is_messageable

AnyAppCommand = discord.app_commands.Command
AppCommandsGroup = discord.app_commands.Group
AppCommandOrGroup = AnyAppCommand | AppCommandsGroup
AnyCtxCommand = commands.Command
AnyCtxGroup = commands.Group


class FieldData(TypedDict):
    "Represents an embed field"
    name: str
    value: str
    inline: bool

_IGNORED_CHECK_NAMES = {
    "_create_cooldown_decorator",
}

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

async def get_discord_locale(ctx: MyContext | discord.Interaction[Axobot]):
    "Get the Discord locale to use for a given context"
    bot = ctx.bot if isinstance(ctx, MyContext) else ctx.client
    bot_locale = await bot._(ctx.channel, "_used_locale")
    for locale, lang in LOCALES_MAP.items():
        if lang == bot_locale:
            return locale
    return discord.Locale.british_english

async def extract_info(raw_description: str) -> tuple[str | None, list[str], str | None]:
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
    return tuple(
        x if len(x) > 0 else None
        for x in ("\n\n".join(description), examples, doc)
    ) # pyright: ignore[reportReturnType]

async def generate_warnings_field(
        ctx: MyContext,
        command: AnyAppCommand | AppCommandsGroup | AnyCtxCommand | AnyCtxGroup
    ) -> FieldData | None:
    "Generate an embed field to list warnings and checks about a command usage"
    if isinstance(command, app_commands.Group | commands.Group):
        return None
    warnings: list[str] = []
    if isinstance(command, commands.Command) and not command.enabled:
        warnings.append(await ctx.bot._(ctx.channel, "help.not-enabled"))
    if len(command.checks) > 0:
        for check in command.checks:
            try:
                check_name = await _extract_check_name(check)
                if check_name in _IGNORED_CHECK_NAMES:
                    continue
                check_msg_tr = await ctx.bot._(ctx.channel, f"help.check-desc.{check_name}")
                if "help.check-desc" in check_msg_tr: # translation was not found
                    ctx.bot.dispatch("error", ValueError(f"No description for help check {check_name} ({check})"))
                    continue
                if await _run_check_function(ctx, check):
                    warnings.append("✅ " + check_msg_tr[0])
                else:
                    warnings.append("❌ " + check_msg_tr[1])
            except Exception as err:
                ctx.bot.dispatch("error", err)
    if len(warnings) > 0:
        return {
            "name": await ctx.bot._(ctx.channel, "help.warning"),
            "value": "\n".join(warnings),
            "inline": False
        }

async def _extract_check_name(check: Callable[..., Any]) -> str:
    "Get the name of a check"
    if "guild_only.<locals>.predicate" in str(check):
        return "guild_only"
    if "is_owner.<locals>.predicate" in str(check):
        return "is_owner"
    if "bot_has_permissions.<locals>.predicate" in str(check):
        return "bot_has_permissions"
    if "_has_permissions.<locals>.predicate" in str(check):
        return "has_permissions"
    return check.__qualname__.split('.')[0]

async def _run_check_function(ctx: MyContext, check: Callable[..., Any]) -> bool:
    # get type of expected argument
    sig = inspect.signature(check)
    first_param_name = list(sig.parameters.keys())[0]
    try:
        original_param_type = get_type_hints(check).get(first_param_name)
    except NameError:
        original_param_type = sig.parameters[first_param_name].annotation
    # if the type couldn't be parsed by the inspect module, map it from its name
    if isinstance(original_param_type, str):
        if "Context" in original_param_type:
            original_param_type = commands.Context
        elif "Interaction" in original_param_type:
            original_param_type = discord.Interaction
    # check if parameter is Union
    if getattr(original_param_type, "__origin__", None) == Union:
        param_types = original_param_type.__args__
    else:
        # else, use the original type
        param_types = [original_param_type]
    # check against each possible type
    for param_type in param_types:
        try:
            if ctx.interaction and issubclass(param_type, discord.Interaction):
                return await discord.utils.maybe_coroutine(check, ctx.interaction)
            if issubclass(param_type, commands.Context):
                return await discord.utils.maybe_coroutine(check, ctx)
        except TypeError as err:
            ctx.bot.dispatch("error", err, f"Type error when checking {check} ({param_types})")
    # if no type matched, dispatch an error
    ctx.bot.dispatch("error", ValueError(f"Unknown type for check {check} ({param_types})"))
    return False


async def get_send_callback(ctx: MyContext):
    "Get a function to call to send the command result"
    async def _send_interaction(content: str | None=None, *, embed: discord.Embed | None = None):
        if ctx.interaction is None:
            raise ValueError("Cannot send interaction response: no interaction found in context")
        await ctx.interaction.followup.send(content, embed=embed)

    async def _send_default(content: str | None=None, *, embed: discord.Embed | None = None):
        if not channel_is_messageable(destination):
            raise ValueError("Cannot send message: no destination channel found")
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
    return await ctx.bot.get_config(ctx.guild.id, "help_in_private") # pyright: ignore[reportReturnType]
