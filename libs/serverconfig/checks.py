from typing import Any, Optional, Union

import discord

from libs.bot_classes import Axobot
from libs.serverconfig.options_list import options as options_list


async def check_config(bot: Axobot, guild: discord.Guild, option: str, value: Any):
    "Check if the config option is correct, or return a custom warning message"
    if option not in options_list:
        return None
    if option == "anti_raid":
        return await antiraid_check(bot, guild, option, value)
    if option == "antiscam":
        return await antiscam_check(bot, guild, option, value)
    if option in {
        "ban_allowed_roles", "clear_allowed_roles", "kick_allowed_roles", "mute_allowed_roles", "slowmode_allowed_roles"
    }:
        if embed := await moderation_commands_check(bot, guild, option, value):
            return embed
    if option in {"bot_news", "modlogs_channel", "partner_channel", "streaming_channel", "welcome_channel"}:
        if embed := await can_write_in_channel_check(bot, guild, option, value):
            return embed
    if option == "xp_rate":
        if embed := await xp_is_local_check(bot, guild, option, value):
            return embed

async def antiraid_check(bot: Axobot, guild: discord.Guild, _option: str, value: str):
    "Check if bot has permissions to kick and ban, else warn to grant them"
    if value == "none":
        return None
    can_kick = guild.me.guild_permissions.kick_members
    can_ban = guild.me.guild_permissions.ban_members and value in {"high", "extreme"}
    if not can_kick and not can_ban:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.antiraid_kick_ban")
        )
    if not can_kick:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.antiraid_kick")
        )
    if not can_ban:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.antiraid_ban")
        )


async def antiscam_check(bot: Axobot, guild: discord.Guild, _option: str, value: bool):
    "Check if the antiscam logs are enabled, else suggest to enable them"
    if value is False or (logs_cog := bot.get_cog("ServerLogs")) is None:
        return None
    if not await logs_cog.is_log_enabled(guild, "antiscam"):
        return None
    return await _create_tip_embed(
        bot,
        guild,
        await bot._(guild, "server.tips.antiscam", modlogs_enable=await bot.get_command_mention("modlogs enable"))
    )

async def moderation_commands_check(bot: Axobot, guild: discord.Guild, option: str, value: Optional[list[discord.Role]]):
    "Check if bot has the required permissions to execute moderation commands, else warn to grant them"
    if not value:
        return
    if option == "ban_allowed_roles" and not guild.me.guild_permissions.ban_members:
        ban_perm = await bot._(guild, "permissions.list.ban_members")
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.moderation_commands", perm=ban_perm)
        )
    if option == "clear_allowed_roles" and not guild.me.guild_permissions.manage_messages:
        manage_msg_perms = await bot._(guild, "permissions.list.manage_messages")
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.moderation_commands", perm=manage_msg_perms)
        )
    if option == "kick_allowed_roles" and not guild.me.guild_permissions.kick_members:
        kick_perm = await bot._(guild, "permissions.list.kick_members")
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.moderation_commands", perm=kick_perm)
        )
    if option == "mute_allowed_roles" and not guild.me.guild_permissions.moderate_members:
        moderate_perm = await bot._(guild, "permissions.list.moderate_members")
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.moderation_commands", perm=moderate_perm)
        )
    if option == "slowmode_allowed_roles" and not guild.me.guild_permissions.manage_channels:
        manage_channel_perm = await bot._(guild, "permissions.list.manage_channels")
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.moderation_commands", perm=manage_channel_perm)
        )


async def can_write_in_channel_check(bot: Axobot, guild: discord.Guild, _option: str, value: Union[discord.TextChannel, list[discord.TextChannel]]):
    "Check if bot can write in the channel, else warn to grant permissions"
    if not isinstance(value, list):
        value = [value]
    for channel in value:
        if not channel.permissions_for(guild.me).send_messages:
            return await _create_warning_embed(
                bot,
                guild,
                await bot._(guild, "server.warnings.channel_write_permissions", channel=channel.mention)
            )


async def xp_is_local_check(bot: Axobot, guild: discord.Guild, _option: str, _value: Any):
    "Check if the xp system is local, else warn that it won't work"
    xp_type = await bot.get_config(guild.id, "xp_type")
    if xp_type != "global":
        return
    return await _create_warning_embed(
        bot,
        guild,
        await bot._(guild, "server.warnings.xp_should_be_local")
    )


async def _create_tip_embed(bot: Axobot, guild: discord.Guild, text: str):
    return discord.Embed(
        title=":information_source: " + await bot._(guild, "server.tips.title"),
        description=text,
        color=discord.Color.blurple()
    )

async def _create_warning_embed(bot: Axobot, guild: discord.Guild, text: str):
    return discord.Embed(
        title=":warning: " + await bot._(guild, "server.warnings.title"),
        description=text,
        color=discord.Color.orange()
    )
