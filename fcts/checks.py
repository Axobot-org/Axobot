import discord
from discord.ext import commands
from libs.classes import MyContext


async def can_mute(ctx: MyContext) -> bool:
    """Check if someone can mute"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "mute")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles


async def can_warn(ctx: MyContext) -> bool:
    """Check if someone can warn"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "warn")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles


async def can_kick(ctx: MyContext) -> bool:
    """Check if someone can kick"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "kick")
    else:
        return ctx.channel.permissions_for(ctx.author).kick_members


async def can_ban(ctx: MyContext) -> bool:
    """Check if someone can ban"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "ban")
    else:
        return ctx.channel.permissions_for(ctx.author).ban_members


async def can_slowmode(ctx: MyContext) -> bool:
    """Check if someone can use slowmode"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "slowmode")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_channels


async def can_clear(ctx: MyContext) -> bool:
    """Check if someone can use clear"""
    if ctx.bot.database_online:
        return await ctx.bot.get_cog("Servers").staff_finder(ctx.author, "clear")
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


async def has_manage_roles(ctx: MyContext) -> bool:
    """... if someone can manage the roles"""
    return ctx.channel.permissions_for(ctx.author).manage_roles or await ctx.bot.get_cog('Admin').check_if_god(ctx)


async def has_manage_nicknames(ctx: MyContext) -> bool:
    """... if someone can change nicknames"""
    return ctx.channel.permissions_for(ctx.author).manage_nicknames or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_manage_channels(ctx: MyContext) -> bool:
    """... if someone can manage the guild channels"""
    return ctx.channel.permissions_for(ctx.author).manage_channels or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_manage_emojis(ctx: MyContext) -> bool:
    """... if someone can change nicknames"""
    return ctx.channel.permissions_for(ctx.author).manage_emojis or await ctx.bot.get_cog('Admin').check_if_god(ctx)

async def has_embed_links(ctx: MyContext) -> bool:
    """... if someone can send embeds"""
    if not isinstance(ctx.author, discord.Member):
        return True
    return ctx.channel.permissions_for(ctx.author).embed_links or await ctx.bot.get_cog('Admin').check_if_god(ctx)


class CannotSendEmbed(commands.CommandError):
    "Raised when the bot needs the embed links permission to work"
    def __init__(self):
        super().__init__("The bot must have the 'embed links' permission")

async def bot_can_embed(ctx: MyContext) -> bool:
    "Check if the bot can send embeds"
    if ctx.can_send_embed:
        return True
    raise CannotSendEmbed()

async def verify_role_exists(ctx: MyContext) -> bool:
    """Check if the verify role exists"""
    if ctx.guild is None:
        return False
    roles_raw = await ctx.bot.get_config(ctx.guild.id, "verification_role")
    if roles_raw is None:
        return False
    roles = [r for r in [ctx.guild.get_role(int(x)) for x in roles_raw.split(';') if x.isnumeric() and len(x) > 0] if r is not None]
    return len(roles) > 0


async def database_connected(ctx: MyContext) -> bool:
    "Check if the database is online and accessible"
    if ctx.bot.database_online:
        return True
    raise commands.CommandError("Database offline")


async def is_fun_enabled(ctx: MyContext, self=None) -> bool:
    if self is None:
        if hasattr(ctx, 'bot'):
            self = ctx.bot.get_cog("Fun")
        else:
            return False
    if ctx.guild is None:
        return True
    if not self.bot.database_online and not ctx.guild.channels[0].permissions_for(ctx.author).manage_guild:
        return False
    ID = ctx.guild.id
    return bool(await self.bot.get_config(ID, "enable_fun"))



async def is_a_cmd(msg: discord.Message, bot: commands.Bot) -> bool:
    "Check if a message is a command"
    pr = await bot.get_prefix(msg)
    is_cmd = False
    for p in pr:
        is_cmd = is_cmd or msg.content.startswith(p)
    return is_cmd

async def is_ttt_enabled(ctx: MyContext, self=None) -> bool:
    if ctx.guild is None:
        return True
    mode = await ctx.bot.get_config(ctx.guild.id, "ttt_display")
    return mode != 0
