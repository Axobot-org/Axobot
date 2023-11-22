import copy
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
                await self.help_command(ctx)
            else:
                await self.help_command(ctx, args)
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, ctx)
            if len(args) == 0:
                await self._default_help_command(ctx)
            else:
                await self._default_help_command(ctx, args)

    async def should_dm(self, context: MyContext) -> bool:
        "Check if the answer should be sent in DM or in current channel"
        if context.guild is None or not self.bot.database_online:
            return False
        return await self.bot.get_config(context.guild.id, 'help_in_dm')

    async def help_command(self, ctx: MyContext, commands_arg: Optional[list[str]] = None):
        """Main command for the creation of the help message
If the bot can't send the new command format, it will try to send the old one."""
        async with ctx.channel.typing():
            destination: discord.abc.Messageable = None
            if ctx.guild is not None:
                if await self.should_dm(ctx):
                    destination = ctx.message.author.dm_channel
                    if ctx.guild:
                        await ctx.message.delete(delay=0)
                else:
                    destination = ctx.message.channel
            if destination is None:
                await ctx.message.author.create_dm()
                destination = ctx.message.author.dm_channel

            if commands_arg is not None and " ".join(commands_arg).lower() in self.commands_data:
                categ_name = [" ".join(commands_arg).lower()]
            elif commands_arg is None:
                categ_name = []
            else:
                translated_categories = {
                    k: await self.bot._(ctx.channel, f"help.categories.{k}")
                    for k in self.commands_data.keys()
                }
                categ_name = [k for k, v in translated_categories.items() if v.lower() == " ".join(commands_arg).lower()]

            if len(categ_name) == 1: # category name
                await help_category_command(self, ctx, categ_name[0])
                return
            if not commands_arg:  # no command
                await help_all_command(self, ctx)
                return
            if len(commands_arg) == 1:  # Unique command name?
                name = commands_arg[0]
                command = self.bot.all_commands.get(name)
                if command is None:
                    ctx2 = copy.copy(ctx)
                    ctx2.message.content = name
                    name = await commands.clean_content().convert(ctx2, name)
                    await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                    return
                await help_text_cmd_command(self, ctx, command)
                return
            # sub-command name?
            name = commands_arg[0]
            command = self.bot.all_commands.get(name)
            if command is None:
                await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                return
            for key in commands_arg[1:]:
                try:
                    command = command.all_commands.get(key)
                    if command is None:
                        await ctx.send(await self.bot._(ctx.channel, "help.subcmd-not-found", name=key))
                        return
                except AttributeError:
                    await ctx.send(await self.bot._(ctx.channel, "help.no-subcmd", cmd=command.name))
                    return
            await help_text_cmd_command(self, ctx, command)


    async def _default_help_command(self, ctx: MyContext, command: str = None):
        default_help = commands.DefaultHelpCommand()
        default_help.context = ctx
        default_help._command_impl = self.help_cmd
        # General help
        if command is None:
            mapping = default_help.get_bot_mapping()
            return await default_help.send_bot_help(mapping)
        # Check if it's a cog
        cog = self.bot.get_cog(" ".join(command))
        if cog is not None:
            return await default_help.send_cog_help(cog)
        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        maybe_coro = discord.utils.maybe_coroutine
        keys = command
        cmd = self.bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(default_help.command_not_found, default_help.remove_mentions(keys[0]))
            return await default_help.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(default_help.subcommand_not_found, cmd, default_help.remove_mentions(key))
                return await default_help.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(default_help.subcommand_not_found, cmd, default_help.remove_mentions(key))
                    return await default_help.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await default_help.send_group_help(cmd)
        else:
            return await default_help.send_command_help(cmd)


async def setup(bot):
    await bot.add_cog(Help(bot))
