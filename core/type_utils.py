from typing import TYPE_CHECKING, Any, TypeGuard

import discord

if TYPE_CHECKING:
    from core.bot_classes.axobot import Axobot


AnyTuple = tuple[Any, ...]
AnyList = list[Any]
AnyDict = dict[Any, Any]
AnyStrDict = dict[str, Any]
UserOrMember = discord.User | discord.Member


def channel_is_guild_messageable(channel: Any) -> TypeGuard[
    discord.TextChannel
    | discord.VoiceChannel
    | discord.StageChannel
    | discord.Thread
]:
    """Ensure that a channel is a guild messageable channel."""
    return isinstance(channel, (
        discord.TextChannel,
        discord.VoiceChannel,
        discord.StageChannel,
        discord.Thread,
    ))

def channel_is_messageable(channel: Any) -> TypeGuard[
    discord.TextChannel
    | discord.VoiceChannel
    | discord.StageChannel
    | discord.Thread
    | discord.DMChannel
    | discord.GroupChannel
    | discord.PartialMessageable
]:
    """Ensure that a channel is a guild messageable channel."""
    return isinstance(channel, (
        discord.TextChannel,
        discord.VoiceChannel,
        discord.StageChannel,
        discord.Thread,
        discord.DMChannel,
        discord.GroupChannel,
        discord.PartialMessageable
    ))

def assert_interaction_channel_is_guild_messageable(
        interaction: discord.Interaction
    ) -> TypeGuard["GuildInteraction"]:
    """Ensure that the interaction channel is a guild messageable channel."""
    if (
        interaction.guild is None
        or not channel_is_guild_messageable(interaction.channel)
    ):
        raise RuntimeError("This command can only be used in a guild channel")
    return True

def assert_message_channel_is_guild_messageable(
        message: discord.Message
    ) -> TypeGuard["GuildMessage"]:
    """Ensure that the message channel is a guild messageable channel."""
    if (
        message.guild is None
        or not channel_is_guild_messageable(message.channel)
    ):
        raise RuntimeError("This command can only be used in a guild channel")
    return True

class GuildInteraction(discord.Interaction["Axobot"]):
    "A specific type for interactions that are guaranteed to be in a writable channel of a guild."
    guild: discord.Guild # pyright: ignore[reportIncompatibleMethodOverride]
    guild_id: int # pyright: ignore[reportIncompatibleVariableOverride]
    channel: ( # pyright: ignore[reportIncompatibleVariableOverride]
        discord.VoiceChannel
        | discord.StageChannel
        | discord.TextChannel
        | discord.Thread
    )
    user: discord.Member # pyright: ignore[reportIncompatibleVariableOverride]

class GuildMessage(discord.Message):
    "A specific type for messages that are guaranteed to be in a writable channel of a guild."
    guild: discord.Guild # pyright: ignore[reportIncompatibleVariableOverride]
    channel: ( # pyright: ignore[reportIncompatibleVariableOverride]
        discord.VoiceChannel
        | discord.StageChannel
        | discord.TextChannel
        | discord.Thread
    )
    author: discord.Member # pyright: ignore[reportIncompatibleVariableOverride]

__all__ = (
    "AnyTuple",
    "AnyList",
    "AnyDict",
    "AnyStrDict",
    "UserOrMember",
)
