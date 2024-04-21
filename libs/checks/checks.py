import typing

import discord
from discord.ext import commands

from libs.bot_classes import SUPPORT_GUILD_ID, MyContext
from libs.checks.errors import NotAVoiceMessageError

admins_id = {279568324260528128,281404141841022976,552273019020771358}

async def is_bot_admin(ctx: typing.Union[MyContext, discord.Interaction, discord.User]):
    "Check if the user is one of the bot administrators"
    if isinstance(ctx, commands.Context):
        user = ctx.author
    elif isinstance(ctx, discord.Interaction):
        user = ctx.user
    else:
        user = ctx
    if isinstance(user, str) and user.isnumeric():
        user = int(user)
    elif isinstance(user, (discord.User, discord.Member)):
        user = user.id
    return user in admins_id

async def is_support_staff(ctx: typing.Union[MyContext, discord.Interaction]) -> bool:
    "Check if the user is one of the bot staff, either by flag or by role"
    user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    if user.id in admins_id:
        return True
    bot = ctx.bot if isinstance(ctx, commands.Context) else ctx.client
    if UsersCog := bot.get_cog('Users'):
        return await UsersCog.has_userflag(user, 'support')
    server = bot.get_guild(SUPPORT_GUILD_ID.id)
    if server is not None:
        member = server.get_member(user.id)
        role = server.get_role(412340503229497361)
        if member is not None and role is not None:
            return role in member.roles
    return False

async def can_mute(ctx: MyContext) -> bool:
    """Check if someone can mute"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "mute_allowed_roles")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles


async def can_warn(ctx: MyContext) -> bool:
    """Check if someone can warn"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "warn_allowed_roles")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles


async def can_kick(ctx: MyContext) -> bool:
    """Check if someone can kick"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "kick_allowed_roles")
    else:
        return ctx.channel.permissions_for(ctx.author).kick_members


async def can_ban(ctx: MyContext) -> bool:
    """Check if someone can ban"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "ban_allowed_roles")
    else:
        return ctx.channel.permissions_for(ctx.author).ban_members


async def can_slowmode(ctx: MyContext) -> bool:
    """Check if someone can use slowmode"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "slowmode_allowed_roles")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_channels


async def can_clear(ctx: MyContext) -> bool:
    """Check if someone can use clear"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "clear_allowed_roles")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_messages


async def has_admin(ctx: MyContext) -> bool:
    """Check if someone can see the banlist"""
    return ctx.channel.permissions_for(ctx.author).administrator or await ctx.bot.get_cog("Admin").check_if_god(ctx)


async def has_manage_msg(ctx: MyContext) -> bool:
    """... if someone can pin a message"""
    return ctx.channel.permissions_for(ctx.author).manage_messages or await ctx.bot.get_cog("Admin").check_if_god(ctx)


async def has_manage_guild(ctx: MyContext) -> bool:
    """... if someone can manage the server"""
    return ctx.channel.permissions_for(ctx.author).manage_guild or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_audit_logs(ctx: MyContext) -> bool:
    """... if someone can see server audit logs"""
    return ctx.channel.permissions_for(ctx.author).view_audit_log or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_manage_roles(ctx: MyContext) -> bool:
    """... if someone can manage the roles"""
    return ctx.channel.permissions_for(ctx.author).manage_roles or await ctx.bot.get_cog('Admin').check_if_god(ctx)


async def has_manage_nicknames(ctx: MyContext) -> bool:
    """... if someone can change nicknames"""
    return ctx.channel.permissions_for(ctx.author).manage_nicknames or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_manage_channels(ctx: MyContext) -> bool:
    """... if someone can manage the guild channels"""
    return ctx.channel.permissions_for(ctx.author).manage_channels or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_manage_expressions(ctx: MyContext) -> bool:
    """... if someone can change nicknames"""
    return ctx.channel.permissions_for(ctx.author).manage_expressions or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_embed_links(ctx: MyContext) -> bool:
    """... if someone can send embeds"""
    if not isinstance(ctx.author, discord.Member):
        return True
    return ctx.channel.permissions_for(ctx.author).embed_links or await ctx.bot.get_cog('Admin').check_if_god(ctx)


class CannotSendEmbed(commands.CommandError):
    "Raised when the bot needs the embed links permission to work"
    def __init__(self):
        super().__init__("The bot must have the 'embed links' permission")

async def bot_can_embed(ctx: typing.Union[MyContext, discord.Interaction]) -> bool:
    "Check if the bot can send embeds"
    if isinstance(ctx, commands.Context) and ctx.can_send_embed:
        return True
    elif isinstance(ctx, discord.Interaction):
        if ctx.guild is None:
            return True
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return True
    raise CannotSendEmbed()

async def is_translator(ctx: MyContext) -> bool:
    "Check if the user is an agreeded translator"
    if cog := ctx.bot.get_cog('Users'):
        return await cog.has_userflag(ctx.author, 'translator')
    return False


async def database_connected(ctx: MyContext) -> bool:
    "Check if the database is online and accessible"
    if ctx.bot.database_online:
        return True
    raise commands.CommandError("Database offline")


async def is_fun_enabled(ctx: MyContext) -> bool:
    "Check if fun is enabled in a given context"
    if ctx.guild is None:
        return True
    if not ctx.bot.database_online and not ctx.author.guild_permissions.manage_guild:
        return False
    return await ctx.bot.get_config(ctx.guild.id, "enable_fun")



async def is_a_cmd(msg: discord.Message, bot: commands.Bot) -> bool:
    "Check if a message is a command"
    pr = await bot.get_prefix(msg)
    is_cmd = False
    for p in pr:
        is_cmd = is_cmd or msg.content.startswith(p)
    return is_cmd

async def is_ttt_enabled(interaction: discord.Interaction) -> bool:
    "Check if the tic-tac-toe game is enabled in a given context"
    if interaction.guild is None:
        return True
    return await interaction.client.get_config(interaction.guild_id, "enable_ttt")


async def is_voice_message(interaction: discord.Interaction):
    "Check if the message is a voice message"
    if "resolved" not in interaction.data or "messages" not in interaction.data["resolved"]:
        raise NotAVoiceMessageError()
    messages: dict[str, dict] = interaction.data["resolved"]["messages"]
    if len(messages) != 1:
        raise NotAVoiceMessageError()
    message = list(messages.values())[0]
    flags = discord.MessageFlags()
    flags.value = message.get('flags', 0)
    if not flags.voice:
        raise NotAVoiceMessageError()
    return True
