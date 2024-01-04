from io import BytesIO
from json import dumps
from typing import TYPE_CHECKING, Any, Optional, Union

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from . import Axobot


class MyContext(commands.Context):
    """Replacement for the official commands.Context class
    It allows us to add more methods and properties in the whole bot code"""

    bot: "Axobot"

    @property
    def bot_permissions(self) -> discord.Permissions:
        """Permissions of the bot in the current context"""
        if self.guild:
            # message in a guild
            return self.channel.permissions_for(self.guild.me)
        else:
            # message in DM
            return self.channel.permissions_for(self.bot)

    @property
    def user_permissions(self) -> discord.Permissions:
        """Permissions of the message author in the current context"""
        return self.channel.permissions_for(self.author)

    @property
    def can_send_embed(self) -> bool:
        """If the bot has the right permissions to send an embed in the current context"""
        return self.bot_permissions.embed_links

    async def send(self, *args, json: Union[dict, list, None]=None, **kwargs) -> Optional[discord.Message]:
        if self.bot.zombie_mode and self.command.name not in self.bot.allowed_commands:
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
        # command: Union[str, commands.Command]
        if len(args) == 1 and isinstance(args[0], commands.Command):
            cmd_arg = args[0].qualified_name
        elif len(args) == 1 and isinstance(args[0], str):
            cmd_arg = args[0]
        elif all(isinstance(arg, str) for arg in args):
            cmd_arg = args
        else:
            raise ValueError(args)
        await self.bot.get_command("help")(self, args=cmd_arg)

    async def send_super_help(self, entity: Union[str, commands.Command, commands.Cog, None]=None):
        "Use the default help command"
        if entity:
            return await super().send_help(entity)
        return await super().send_help()
