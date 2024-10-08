import logging
import os
import random
import re
import sys
import traceback

import discord
from discord.ext import commands, tasks

from core.arguments import errors as arguments_errors
from core.bot_classes import Axobot, MyContext
from core.checks import checks
from core.checks.errors import (NotAVoiceMessageError, NotDuringEventError,
                                VerboseCommandError)
from modules.perms.arguments.perms_args import InvalidPermissionTargetError

AllowedCtx = MyContext | discord.Message | discord.Interaction | str

class Errors(commands.Cog):
    """General cog for error management."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "errors"
        self.log = logging.getLogger("bot.errors")
        # map of user ID and number of cooldowns recently hit
        self.cooldown_pool: dict[int, int] = {}

    async def cog_load(self):
        # pylint: disable=no-member
        self.reduce_cooldown_pool.start()

    async def cog_unload(self):
        # pylint: disable=no-member
        if self.reduce_cooldown_pool.is_running():
            self.reduce_cooldown_pool.cancel()

    async def can_send_cooldown_error(self, user_id: int):
        "Check if we can send a cooldown error message for a given user, to avoid spam"
        spam_score = self.cooldown_pool.get(user_id, 0)
        self.cooldown_pool[user_id] = spam_score + 1
        return spam_score < 4

    @tasks.loop(seconds=5)
    async def reduce_cooldown_pool(self):
        "Reduce the cooldown score by 1 every 5s"
        to_delete: set[int] = set()
        for user_id in self.cooldown_pool:
            self.cooldown_pool[user_id] -= 1
            if self.cooldown_pool[user_id] <= 0:
                to_delete.add(user_id)
        for user_id in to_delete:
            del self.cooldown_pool[user_id]

    @reduce_cooldown_pool.error
    async def on_reduce_cooldown_pool_error(self, error):
        "Log errors from reduce_cooldown_pool"
        self.bot.dispatch("error", error)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: MyContext, error: Exception):
        """The event triggered when an error is raised while invoking a command."""
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, "on_error"):
            return

        ignored = (
            commands.errors.CommandNotFound,
            commands.errors.CheckFailure,
            commands.errors.ConversionError,
            discord.errors.Forbidden
        )
        actually_not_ignored = (commands.errors.NoPrivateMessage, VerboseCommandError)

        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, "original", error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored) and not isinstance(error, actually_not_ignored):
            if isinstance(error, commands.CheckFailure) and ctx.interaction:
                help_cmd = await self.bot.get_command_mention("help")
                await ctx.send(await self.bot._(ctx.channel, "errors.checkfailure", help_cmd=help_cmd), ephemeral=True)
            if self.bot.beta and ctx.guild:
                await ctx.send(f"`Ignored error:` [{error.__class__.__module__}.{error.__class__.__name__}] {error}")
            return
        elif isinstance(error, commands.CommandError) and str(error) == "User doesn't have required roles":
            await ctx.send(await self.bot._(ctx.channel, "errors.notrightroles"), ephemeral=True)
            return
        elif isinstance(error, commands.CommandError) and str(error) == "Database offline":
            await ctx.send(await self.bot._(ctx.channel, "errors.nodb-1"))
            return
        elif isinstance(error, commands.ExpectedClosingQuoteError):
            await ctx.send(await self.bot._(ctx.channel, "errors.quoteserror"), ephemeral=True)
            return
        elif isinstance(error, NotDuringEventError):
            cmd = await self.bot.get_command_mention("event info")
            await ctx.send(await self.bot._(ctx.channel, "errors.notduringevent", cmd=cmd), ephemeral=True)
            return
        elif isinstance(error, commands.errors.CommandOnCooldown):
            if await checks.is_bot_admin(ctx) and not ctx.interaction:
                await ctx.reinvoke()
                return
            if await self.can_send_cooldown_error(ctx.author.id):
                delay = round(error.retry_after, 2 if error.retry_after < 60 else None)
                await ctx.send(await self.bot._(ctx.channel, "errors.cooldown", d=delay), ephemeral=True)
            return
        elif isinstance(error, commands.BadLiteralArgument):
            await ctx.send(await self.bot._(ctx.channel, "errors.badlitteral"), ephemeral=True)
            return
        elif isinstance(error, commands.BadArgument | commands.BadUnionArgument):
            allowed_mentions = discord.AllowedMentions(everyone=False, users=False, roles=False)
            async def send_err(tr_key: str, **kwargs):
                await ctx.send(await self.bot._(ctx.channel, tr_key, **kwargs),
                               allowed_mentions=allowed_mentions, ephemeral=True)

            raw_error = str(error)
            # value must be less than 1 but received -1
            if isinstance(error, commands.RangeError):
                return await send_err("errors.rangeerror", min=error.minimum, value=error.value)

            # Could not convert "limit" into int. OR Converting to "int" failed for parameter "number".
            reason = re.search(r"Could not convert \"(?P<arg>[^\"]+)\" into (?P<type>[^.\n]+)", raw_error)
            if reason is None:
                reason = re.search(r"Converting to \"(?P<type>[^\"]+)\" failed for parameter \"(?P<arg>[^.\n]+)\"", raw_error)
            if reason is not None:
                return await send_err("errors.badarguments", p=reason.group("arg"), t=reason.group("type"))
            # zzz is not a recognised boolean option
            if isinstance(error, commands.BadBoolArgument):
                return await send_err("errors.badboolean", p=error.argument)
            # Member "Z_runner" not found
            if isinstance(error, commands.MemberNotFound):
                return await send_err("errors.membernotfound", m=error.argument)
            # User "Z_runner" not found
            if isinstance(error, commands.UserNotFound):
                return await send_err("errors.usernotfound", u=error.argument)
            # Role "Admin" not found
            if isinstance(error, commands.RoleNotFound):
                return await send_err("errors.rolenotfound", r=error.argument)
            # Emoji ":shock:" not found
            if isinstance(error, commands.EmojiNotFound):
                return await send_err("errors.emojinotfound", e=error.argument)
             # Colour "blue" is invalid
            if isinstance(error, commands.BadColourArgument):
                return await send_err("errors.invalidcolor", c=error.argument)
            # Channel "twitter" not found.
            if isinstance(error, commands.ChannelNotFound):
                return await send_err("errors.channotfound", c=error.argument)
            # Message "1243" not found.
            if isinstance(error, commands.MessageNotFound):
                return await send_err("errors.msgnotfound", msg=error.argument)
            # Guild "1243" not found.
            if isinstance(error, commands.GuildNotFound):
                return await send_err("errors.guildnotfound", guild=error.argument)
            # abc does not follow a valid ID or mention format
            if isinstance(error, commands.ObjectNotFound):
                return await send_err("errors.invalidsnowflake")
            # Invalid duration: 2d
            if isinstance(error, arguments_errors.InvalidDurationError):
                return await send_err("errors.duration", d=error.argument)
            # Invalid invite: nope
            if isinstance(error, arguments_errors.InvalidBotOrGuildInviteError):
                return await send_err("errors.invalidinvite", i=error.argument)
            # Invalid url: nou
            if isinstance(error, arguments_errors.InvalidUrlError):
                return await send_err("errors.invalidurl", u=error.argument)
            # Invalid unicode emoji: lol
            if isinstance(error, arguments_errors.InvalidUnicodeEmojiError):
                return await send_err("errors.invalidunicode", u=error.argument)
            # Invalid card style: aqua
            if isinstance(error, arguments_errors.InvalidCardStyleError):
                return await send_err("errors.invalidcardstyle", s=error.argument)
            # Invalid server log type
            if isinstance(error, arguments_errors.InvalidServerLogError):
                return await send_err("errors.invalidserverlog")
            # Invalid member, role or permission
            if isinstance(error, InvalidPermissionTargetError):
                return await send_err("errors.invalidpermissiontarget")
            self.log.warning("Unknown BadArgument error type: %s", error)
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send(await self.bot._(
                ctx.channel,"errors.missingargument",
                a=error.param.name,
                e=random.choice([":eyes:",'',":confused:",":thinking:",''])
            ))
            return
        elif isinstance(error, commands.errors.DisabledCommand):
            await ctx.send(await self.bot._(ctx.channel,"errors.disabled", c=ctx.invoked_with), ephemeral=True)
            return
        elif isinstance(error, commands.errors.NoPrivateMessage):
            await ctx.send(await self.bot._(ctx.channel,"errors.DM"))
            return
        else:
            cmd = await self.bot.get_command_mention("about")
            try:
                await ctx.send(await self.bot._(ctx.channel, "errors.unknown", about=cmd), ephemeral=True)
            except Exception as newerror:
                self.log.info("[on_cmd_error] Can't send error on channel %s: %s", ctx.channel.id, newerror)
        # All other Errors not returned come here... And we can just print the default TraceBack.
        self.log.warning("Ignoring exception in command %s:", ctx.message.content)
        await self.on_error(error, ctx)

    @commands.Cog.listener()
    async def on_interaction_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        "Called when an error is raised during an interaction"
        if isinstance(error, discord.app_commands.CommandOnCooldown):
            delay = round(error.retry_after, 2 if error.retry_after < 60 else None)
            await interaction.response.send_message(
                await self.bot._(interaction, "errors.cooldown", d=delay),
                ephemeral=True)
            return
        if isinstance(error, NotAVoiceMessageError):
            await interaction.response.send_message(
                await self.bot._(interaction, "errors.notavoicemessage"),
                ephemeral=True)
            return
        if isinstance(error, discord.app_commands.CheckFailure):
            help_cmd = await self.bot.get_command_mention("help")
            await interaction.response.send_message(
                await self.bot._(interaction, "errors.checkfailure", help_cmd=help_cmd),
                ephemeral=True)
            return
        if isinstance(error, discord.app_commands.TransformerError):
            await interaction.response.send_message(error.args[0], ephemeral=True)
            return
        if interaction.guild:
            guild = f"{interaction.guild.name} | {interaction.channel.name}"
        elif interaction.guild_id:
            guild = f"guild {interaction.guild_id}"
        else:
            guild = f"DM with {interaction.user}"
        if interaction.type == discord.InteractionType.application_command:
            await self.on_error(error, interaction)
        elif interaction.type == discord.InteractionType.ping:
            await self.on_error(error, f"Ping interaction | {guild}")
        elif interaction.type == discord.InteractionType.modal_submit:
            await self.on_error(error, f"Modal submission interaction | {guild}")
        elif interaction.type == discord.InteractionType.component:
            await self.on_error(error, f"Component interaction | {guild}")
        elif interaction.type == discord.InteractionType.autocomplete:
            await self.on_error(error, f"Command autocompletion | {guild}")
        else:
            self.log.warning("Unhandled interaction error type: %s", interaction.type)
            await self.on_error(error, None)

    @commands.Cog.listener()
    async def on_error(self, error: Exception, ctx: AllowedCtx | None = None):
        """Called when an error is raised

        Its only purpose is to log the error, ctx param is only useful for traceability"""
        if sys.exc_info()[0] is None:
            exc_info = (type(error), error, error.__traceback__)
        else:
            exc_info = sys.exc_info()
        try:
            # if this is only an interaction too slow, don't report in bug channel
            if isinstance(error, discord.NotFound) and error.code == 10062:
                self.log.warning("Ignored NotFound error: %s", error, exc_info=exc_info)
                return
            # get traceback info
            if isinstance(ctx, discord.Message):
                ctx = await self.bot.get_context(ctx)
            trace = " ".join(traceback.format_exception(*exc_info))
            trace = trace.replace(os.getcwd(), ".")
            # get context clue
            if ctx is None:
                context = "Internal Error"
            elif isinstance(ctx, str):
                context = ctx
            elif ctx.guild is None:
                recipient = await self.bot.get_recipient(ctx.channel)
                context = f"DM | {recipient}"
            elif isinstance(ctx, discord.Interaction):
                cmd_name = ctx.command.qualified_name if ctx.command else None
                context = f"Slash command `{cmd_name}` | {ctx.guild.name} | {ctx.channel.name}"
            else:
                context = f"{ctx.guild.name} | {ctx.channel.name}"
            # if channel is the private beta channel, send it there
            if isinstance(ctx, MyContext | discord.Interaction) and ctx.channel.id == 625319425465384960:
                await ctx.channel.send(f"{context}\n```py\n{trace[:1920]}\n```")
            else:
                await self.send_error_msg_autoformat(context, trace)
            self.log.warning("Error: %s", error, exc_info=exc_info)
        except Exception as err: # pylint: disable=broad-except
            self.log.error("Error while sending logs for another error: %s", err, exc_info=exc_info)

    async def send_error_msg_autoformat(self, context: str, python_message: str):
        """Envoie un message dans le salon d'erreur"""
        success = True
        for i in range(0, len(python_message), 1920):
            if i == 0:
                msg = context + f"\n```py\n{python_message[i:i+1920]}\n```"
            else:
                msg = f"```py\n{python_message[i:i+1920]}\n```"
            success = success and await self.senf_err_msg(msg)
        return success

    async def senf_err_msg(self, msg: str):
        """Envoie un message dans le salon d'erreur"""
        errors_channel = self.bot.get_channel(626039503714254858)
        if errors_channel is None:
            return False
        if len(msg) > 2000:
            if msg.endswith("```"):
                msg = msg[:1997]+"```"
            else:
                msg = msg[:2000]
        await errors_channel.send(msg)
        return True


async def setup(bot):
    await bot.add_cog(Errors(bot))
