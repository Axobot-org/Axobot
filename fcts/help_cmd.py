import json
from typing import Optional, TypedDict

import discord
from discord.ext import commands

from libs.bot_classes import Axobot, MyContext
from libs.help_cmd import (help_all_command, help_category_command,
                           help_text_cmd_command)


class CommandsCategoryData(TypedDict):
    emoji: str
    commands: list[str]

class Help(commands.Cog):
    "Help commands"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "help_cmd"
        self.old_cmd = bot.remove_command("help")
        self.help_color = 0x7ED321
        self.help_color_dm = 0xD6FFA9
        with open('fcts/help.json', 'r', encoding="utf-8") as file:
            self.commands_data: dict[str, CommandsCategoryData] = json.load(file)

    @property
    def doc_url(self):
        return (
            "https://axobot.readthedocs.io/en/main/",
            "https://axobot.readthedocs.io/en/develop/",
            "https://axobot.readthedocs.io/en/latest/",
        )[self.bot.entity_id]

    async def cog_unload(self):
        self.bot.remove_command("help")
        self.bot.add_command(self.old_cmd)

    @commands.command(name="help")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.cooldown(10, 30, commands.BucketType.guild)
    async def help_cmd(self, ctx: MyContext, *args: str):
        """Shows this message
Enable "Embed Links" permission for better rendering

..Example help

..Example help info

..Example help rss embed

..Doc infos.html#help"""
        try:
            if len(args) == 0:
                await help_all_command(self, ctx)
            else:
                await self.help_command(ctx, args)
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, ctx)
            await ctx.send_super_help(" ".join(args) if args else None)

    async def help_command(self, ctx: MyContext, command_arg: list[str]):
        """Main command for the creation of the help message
If the bot can't send the new command format, it will try to send the old one."""
        # if user entered a category name
        if category_id := await self._detect_category_from_args(ctx, command_arg):
            await help_category_command(self, ctx, category_id)
            return
        # if user entered a root command/group name
        if len(command_arg) == 1:
            name = command_arg[0]
            command = self.bot.all_commands.get(name)
            if command is None:
                await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                return
            await help_text_cmd_command(self, ctx, command)
            return
        # if user entered a subcommand name
        name = command_arg[0]
        command = self.bot.all_commands.get(name)
        if command is None:
            await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
            return
        for key in command_arg[1:]:
            if not isinstance(command, commands.Group):
                await ctx.send(await self.bot._(ctx.channel, "help.no-subcmd", cmd=command.name))
                return
            command = command.all_commands.get(key)
            if command is None:
                await ctx.send(await self.bot._(ctx.channel, "help.subcmd-not-found", name=key))
                return
        await help_text_cmd_command(self, ctx, command)

    async def _detect_category_from_args(self, ctx: MyContext, args: list[str]) -> Optional[str]:
        """Detect the category from the arguments passed to the help command"""
        arg_input = " ".join(args).lower()
        if arg_input in self.commands_data:
            return arg_input
        for category_id in self.commands_data:
            category_name = await self.bot._(ctx.channel, f"help.categories.{category_id}")
            if category_name.lower() == arg_input:
                return category_id
        return None


async def setup(bot):
    await bot.add_cog(Help(bot))
