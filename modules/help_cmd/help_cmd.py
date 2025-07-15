import json
import os
from typing import Any, Callable, Coroutine, TypedDict

import discord
from discord.app_commands import Group
from discord.ext import commands

from core.bot_classes import Axobot, MyContext

from .utils import (AppCommandOrGroup, get_send_callback, help_all_command,
                    help_category_command, help_slash_cmd_command,
                    help_text_cmd_command)


class CommandsCategoryData(TypedDict):
    emoji: str
    commands: list[str]

class Help(commands.Cog):
    "Help commands"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "help_cmd"
        if (old_cmd := bot.remove_command("help")) is None:
            raise RuntimeError("The 'help' command is already removed, cannot load the help cog.")
        self.old_cmd = old_cmd
        self.help_color = 0x7ED321
        self.help_color_dm = 0xD6FFA9
        json_path = os.path.dirname(__file__) + "/help.json"
        with open(json_path, 'r', encoding="utf-8") as file:
            self.commands_data: dict[str, CommandsCategoryData] = json.load(file)

    async def cog_unload(self):
        self.bot.remove_command("help")
        self.bot.add_command(self.old_cmd)

    @commands.hybrid_command(name="help")
    @commands.cooldown(2, 8, commands.BucketType.user)
    @commands.cooldown(10, 30, commands.BucketType.guild)
    async def help_cmd(self, ctx: MyContext, *, args: str | None = None):
        """Shows this message
Enable "Embed Links" permission for better rendering

..Example help

..Example help info

..Example help rss embed

..Doc infos.html#help"""
        try:
            if not args:
                await help_all_command(self, ctx)
            else:
                await self.help_command(ctx, args.split(" "))
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, ctx)
            await ctx.send_super_help(args or None)

    async def help_command(self, ctx: MyContext, command_arg: list[str]):
        """Main command for the creation of the help message
If the bot can't send the new command format, it will try to send the old one."""
        # if user entered a category name
        if category_id := await self._detect_category_from_args(ctx, command_arg):
            await help_category_command(self, ctx, category_id)
            return
        # if user entered a textual or hybrid command / subcommand name
        if command := self.bot.get_command(" ".join(command_arg)):
            await help_text_cmd_command(self, ctx, command)
            return
        # if user entered a slash command / subcommand name
        if command := await self._find_command_from_name(command_arg, None):
            await help_slash_cmd_command(self, ctx, command)
            return
        send = await get_send_callback(ctx)
        await self._send_error_unknown_command(ctx, send, command_arg)

    async def _detect_category_from_args(self, ctx: MyContext, args: list[str]) -> str | None:
        """Detect the category from the arguments passed to the help command"""
        arg_input = " ".join(args).lower()
        if arg_input in self.commands_data:
            return arg_input
        for category_id in self.commands_data:
            category_name = await self.bot._(ctx.channel, f"help.categories.{category_id}")
            if category_name.lower() == arg_input:
                return category_id
        return None

    async def _send_error_unknown_command(self, ctx: MyContext, send: Callable[..., Coroutine[Any, Any, None]], args: list[str]):
        """Send a meaningful error message if the (sub)command is not found"""
        if len(args) == 0:
            return # should not happen
        if len(args) == 1:
            await send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=args[0]))
            return
        parent, last_arg = args[:-1], args[-1]
        if cmd := self.bot.get_command(" ".join(parent)):
            if isinstance(cmd, commands.Group):
                await send(await self.bot._(ctx.channel, "help.subcmd-not-found", name=last_arg))
                return
            cmd_mention = await self.bot.get_command_mention(cmd.qualified_name)
            await send(await self.bot._(ctx.channel, "help.no-subcmd", cmd=cmd_mention))
            return
        elif cmd := self.bot.tree.get_command(args[0]):
            if isinstance(cmd, Group):
                await send(await self.bot._(ctx.channel, "help.subcmd-not-found", name=last_arg))
                return
            cmd_mention = await self.bot.get_command_mention(cmd.qualified_name)
            await send(await self.bot._(ctx.channel, "help.no-subcmd", cmd=cmd_mention))
            return
        await self._send_error_unknown_command(ctx, send, parent)

    async def _find_command_from_name(
            self, args: list[str], parent_command: AppCommandOrGroup | None) -> AppCommandOrGroup | None:
        if parent_command and not args:
            return parent_command
        if not args:
            return None
        current_arg, args = args[0], args[1:]
        if not parent_command:
            if cmd := self.bot.tree.get_command(current_arg):
                return await self._find_command_from_name(args, cmd)
        elif isinstance(parent_command, Group):
            for subcommand in parent_command.commands:
                if subcommand.name == current_arg:
                    return await self._find_command_from_name(args, subcommand)


async def setup(bot: Axobot):
    await bot.add_cog(Help(bot))
