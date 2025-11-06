from typing import TYPE_CHECKING, TypedDict

import discord
from discord.ext import commands

from core.bot_classes import SUPPORT_GUILD_ID, MyContext
from core.bot_classes.axobot import Axobot
from core.checks.errors import NotAVoiceMessageError

if TYPE_CHECKING:
    from discord.types.message import Message as MessageDict
    from discord.types.message import MessageSnapshot

admins_id = {279568324260528128,281404141841022976,552273019020771358}

async def is_bot_admin(ctx: MyContext | discord.Interaction | discord.User):
    "Check if the user is one of the bot administrators"
    if isinstance(ctx, commands.Context):
        user = ctx.author.id
    elif isinstance(ctx, discord.Interaction):
        user = ctx.user.id
    else:
        user = ctx.id
    return user in admins_id

async def is_support_staff(interaction: discord.Interaction[Axobot]) -> bool:
    "Check if the user is one of the bot staff, either by flag or by role"
    if interaction.user.id in admins_id:
        return True
    if users_cog := interaction.client.get_cog("Users"):
        return await users_cog.has_userflag(interaction.user, "support")
    server = interaction.client.get_guild(SUPPORT_GUILD_ID.id)
    if server is not None:
        member = server.get_member(interaction.user.id)
        role = server.get_role(412340503229497361)
        if member is not None and role is not None:
            return role in member.roles
    return False

async def database_connected(interaction: discord.Interaction[Axobot]) -> bool:
    "Check if the database is online and accessible"
    if interaction.client.database_online:
        return True
    raise commands.CommandError("Database offline")

async def is_voice_message(interaction: discord.Interaction):
    "Check if the message is a voice message"
    if interaction.data is None or "resolved" not in interaction.data or "messages" not in interaction.data["resolved"]:
        raise NotAVoiceMessageError()
    messages = interaction.data["resolved"]["messages"]
    if len(messages) != 1:
        raise NotAVoiceMessageError()
    message = list(messages.values())[0]
    flags = discord.MessageFlags()
    flags.value = message.get("flags", 0)
    if not flags.voice:
        if flags.forwarded: # pylint: disable=using-constant-test
            return await _forwards_voice_message(message)
        raise NotAVoiceMessageError()
    return True

SnapshotRef = TypedDict("SnapshotRef", message="MessageSnapshot")
async def _forwards_voice_message(message: "MessageDict"):
    "Check if the interaction message forwards a voice message"
    snapshots: list[SnapshotRef] = message.get("message_snapshots", [])
    if len(snapshots) != 1:
        raise NotAVoiceMessageError()
    snapshot = snapshots[0]["message"]
    flags = discord.MessageFlags()
    flags.value = snapshot.get("flags", 0)
    if not flags.voice:
        raise NotAVoiceMessageError()
    return True
