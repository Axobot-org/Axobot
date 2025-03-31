from typing import Any

import discord

from core.bot_classes import Axobot


async def check_config(bot: Axobot, guild: discord.Guild, option: str, value: Any):
    "Check if the config option is correct, or return a custom warning message"
    if option == "anti_raid":
        return await antiraid_check(bot, guild, option, value)
    if option == "antiscam":
        return await antiscam_check(bot, guild, option, value)
    if option == "enable_invites_tracking":
        return await manage_guild_check(bot, guild, option, value)
    if option in {"bot_news", "levelup_channel", "partner_channel", "streaming_channel", "welcome_channel"}:
        levelup_is_channel = option != "levelup_channel" or not isinstance(value, str)
        if levelup_is_channel and (embed := await can_write_in_channel_check(bot, guild, option, value)):
            return embed
    if option in {
        "levelup_channel", "levelup_msg", "noxp_channels", "noxp_roles", "voice_xp_per_min", "xp_decay", "xp_rate", "xp_type"
    }:
        if embed := await xp_is_enabled_check(bot, guild, option, value):
            return embed
    if option in {"voice_xp_per_min", "xp_decay", "xp_rate"}:
        if embed := await xp_is_local_check(bot, guild, option, value):
            return embed

async def antiraid_check(bot: Axobot, guild: discord.Guild, _option: str, value: str):
    "Check if bot has permissions to kick and ban, else warn to grant them"
    if value == "none":
        return None
    missing_perms: list[str] = []
    if not guild.me.guild_permissions.kick_members:
        missing_perms.append(await bot._(guild, "permissions.list.kick_members"))
    if not guild.me.guild_permissions.moderate_members:
        missing_perms.append(await bot._(guild, "permissions.list.moderate_members"))
    if value in {"high", "extreme"} and not guild.me.guild_permissions.ban_members:
        missing_perms.append(await bot._(guild, "permissions.list.ban_members"))
    if len(missing_perms) == 1:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.antiraid_perms_missing",
                        count=1,
                        perm=missing_perms[0]
                        )
        )
    if len(missing_perms) >= 2:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.antiraid_perms_missing",
                        count=3,
                        list=", ".join(missing_perms)
                        )
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


async def manage_guild_check(bot: Axobot, guild: discord.Guild, _option: str, value: bool):
    "Check if the bot can manage guild (for invites), else warn to grant permissions"
    if value and not guild.me.guild_permissions.manage_guild:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.manage_guild_permissions")
        )

async def guild_has_afk_channel(bot: Axobot, guild: discord.Guild, _option: str, value: Any):
    "Check if the guild has an AFK channel, else warn to create one"
    if not value:
        return None
    if not guild.afk_channel or guild.afk_timeout == 0:
        return await _create_warning_embed(
            bot,
            guild,
            await bot._(guild, "server.warnings.afk_channel")
        )

async def can_write_in_channel_check(bot: Axobot, guild: discord.Guild, _option: str,
                                     value: discord.TextChannel | list[discord.TextChannel]):
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

async def xp_is_enabled_check(bot: Axobot, guild: discord.Guild, _option: str, _value: Any):
    "Check if the xp is enabled in this server, else warn that it'll be useless"
    xp_enabled = await bot.get_config(guild.id, "enable_xp")
    if xp_enabled:
        return
    return await _create_warning_embed(
        bot,
        guild,
        await bot._(guild, "server.warnings.xp_should_be_enabled")
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
