"""Payloads of the "server_warning" event, dispatched when the bot fails to do its job in a guild.

Usage: bot.dispatch("server_warning", MembercounterMissingPermissions(guild=guild, channel=channel))
"""

from dataclasses import dataclass

import discord


@dataclass(frozen=True, slots=True, kw_only=True)
class ServerWarning:
    "Base class of every server warning"
    guild: discord.Guild


# ---- Welcomer ----

@dataclass(frozen=True, slots=True, kw_only=True)
class WelcomeMissingTxtPermissions(ServerWarning):
    channel: discord.TextChannel
    is_join: bool

@dataclass(frozen=True, slots=True, kw_only=True)
class WelcomeRoleMissingPermissions(ServerWarning):
    role: discord.Role
    user: discord.Member


# ---- Server config ----

@dataclass(frozen=True, slots=True, kw_only=True)
class MembercounterMissingPermissions(ServerWarning):
    channel: discord.VoiceChannel | discord.StageChannel


# ---- XP ----

@dataclass(frozen=True, slots=True, kw_only=True)
class XpRoleRewardMissingPermissions(ServerWarning):
    member: discord.Member


# ---- RSS ----

@dataclass(frozen=True, slots=True, kw_only=True)
class RssWarning(ServerWarning):
    "Base class of RSS-related warnings"
    feed_id: int

@dataclass(frozen=True, slots=True, kw_only=True)
class RssMissingTxtPermission(RssWarning):
    channel: discord.TextChannel | discord.Thread

@dataclass(frozen=True, slots=True, kw_only=True)
class RssMissingEmbedPermission(RssWarning):
    channel: discord.TextChannel | discord.Thread

@dataclass(frozen=True, slots=True, kw_only=True)
class RssInvalidFormat(RssWarning):
    channel: discord.TextChannel | discord.Thread

@dataclass(frozen=True, slots=True, kw_only=True)
class RssUnknownChannel(RssWarning):
    channel_id: int

@dataclass(frozen=True, slots=True, kw_only=True)
class RssDisabledFeed(RssWarning):
    channel_id: int

@dataclass(frozen=True, slots=True, kw_only=True)
class RssTwitterDisabled(RssWarning):
    channel_id: int


# ---- Tickets ----

@dataclass(frozen=True, slots=True, kw_only=True)
class TicketCreationUnknownTarget(ServerWarning):
    channel_id: int | None
    topic_name: str | None

@dataclass(frozen=True, slots=True, kw_only=True)
class TicketCreationFailed(ServerWarning):
    channel: discord.CategoryChannel | discord.TextChannel
    topic_name: str | None

@dataclass(frozen=True, slots=True, kw_only=True)
class TicketInitFailed(ServerWarning):
    channel: discord.CategoryChannel | discord.TextChannel
    topic_name: str | None


# ---- Tasks ----

@dataclass(frozen=True, slots=True, kw_only=True)
class TempRoleRemoveForbidden(ServerWarning):
    role: discord.Role
    user: discord.Member


# ---- Twitch ----

@dataclass(frozen=True, slots=True, kw_only=True)
class StreamNotificationMissingPermissions(ServerWarning):
    channel_id: int
    username: str

@dataclass(frozen=True, slots=True, kw_only=True)
class StreamRoleMissingPermissions(ServerWarning):
    role_id: int
    member: discord.Member
    username: str
