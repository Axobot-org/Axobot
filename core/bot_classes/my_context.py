from io import BytesIO
from json import dumps
from typing import TYPE_CHECKING, Any

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from . import Axobot


class MyContext(commands.Context["Axobot"]):
    """Replacement for the official commands.Context class
    It allows us to add more methods and properties in the whole bot code"""

    @property
    def can_send_embed(self) -> bool:
        """If the bot has the right permissions to send an embed in the current context"""
        return self.interaction is not None or self.bot_permissions.embed_links

    async def send(self, *args, json: dict | list | None = None, **kwargs) -> discord.Message | None: # type: ignore
        if self.bot.zombie_mode and (self.command is None or self.command.name not in self.bot.allowed_commands):
            return
        if self.message.type == discord.MessageType.reply and self.message.reference:
            kwargs["allowed_mentions"] = kwargs.get("allowed_mentions", self.bot.allowed_mentions)
            kwargs["allowed_mentions"].replied_user = False
            kwargs["reference"] = self.message.reference
        if json is not None:
            file = discord.File(BytesIO(dumps(json, indent=2).encode()), filename="message.json")
            if "file" in kwargs:
                kwargs["files"] = [kwargs["file"], file]
                kwargs.pop("file")
            elif "files" in kwargs:
                kwargs["files"].append(file)
            else:
                kwargs["file"] = file
        return await super().send(*args, **kwargs)

    async def send_help(self, *args: Any):
        """Send the help message of the given command"""
        if len(args) == 1 and isinstance(args[0], commands.Command):
            cmd_arg = args[0].qualified_name
        elif len(args) == 1 and isinstance(args[0], str):
            cmd_arg = args[0]
        elif all(isinstance(arg, str) for arg in args):
            cmd_arg = args
        else:
            raise ValueError(args)
        if (help_cmd := self.bot.get_command("help")):
            await help_cmd(self, args=cmd_arg)

    async def send_super_help(self, entity: str | commands.Command | commands.Cog | None = None): # type: ignore
        "Use the default help command"
        if entity:
            return await super().send_help(entity)
        return await super().send_help()
