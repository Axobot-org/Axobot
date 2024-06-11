import re

import discord
from discord import app_commands
from discord.ext import commands

from core.arguments.errors import VerboseBadArgumentError
from core.bot_classes import MyContext


class InvalidRawPermissionError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid raw permission"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid raw permission: {argument}")

class InvalidPermissionTargetError(VerboseBadArgumentError):
    "Raised when the 'target' argument of the permissions command is not valid"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid member, role or permission: {argument}")

class RawPermissionValue(int):
    "Represents a raw permission value, as an integer"
    @classmethod
    async def convert(cls, _ctx: MyContext, argument: str):
        "Do the conversion"
        if re.match(r'0b[0,1]+', argument):
            return int(argument[2:], 2)
        if not argument.isnumeric():
            raise InvalidRawPermissionError(argument)
        try:
            value = int(argument, 2 if len(argument) > 13 else 10)
        except ValueError:
            value = int(argument)
        if value > discord.Permissions.all().value:
            raise InvalidRawPermissionError(argument)
        return value

VoiceChannelTypes = (
    discord.VoiceChannel
    | discord.StageChannel
)

TextChannelTypes = (
    discord.TextChannel
    | discord.CategoryChannel
    | discord.ForumChannel
    | discord.Thread
)

AcceptableChannelTypes = (
    None
    | VoiceChannelTypes
    | TextChannelTypes
)

AcceptableTargetTypes = (
    None
    | discord.Member
    | discord.Role
    | RawPermissionValue
)

class TargetTransformer(app_commands.Transformer): # pylint: disable=abstract-method
    "Convert a string argument into a Discord Member, Role or Permission object"
    async def transform(self, interaction, value, /):
        ctx = await MyContext.from_interaction(interaction)
        try:
            return await commands.MemberConverter().convert(ctx, value)
        except commands.MemberNotFound:
            pass

        try:
            return await commands.RoleConverter().convert(ctx, value)
        except commands.RoleNotFound:
            pass

        try:
            return await RawPermissionValue().convert(ctx, value)
        except commands.BadArgument:
            pass

        if value == "everyone":
            return ctx.guild.default_role

        raise InvalidPermissionTargetError(value)

TargetArgument = app_commands.Transform[AcceptableTargetTypes, TargetTransformer]
