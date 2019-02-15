import discord
from discord.ext import commands

async def can_mute(ctx):
    """Check if someone can mute"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"mute")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles

async def can_warn(ctx):
    """Check if someone can warn"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"warn")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles

async def can_kick(ctx):
    """Check if someone can kick"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"kick")
    else:
        return ctx.channel.permissions_for(ctx.author).kick_members

async def can_ban(ctx):
    """Check if someone can ban"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"ban")
    else:
        return ctx.channel.permissions_for(ctx.author).ban_members

async def can_slowmode(ctx):
    """Check if someone can use slowmode"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"slowmode")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_channels

async def can_clear(ctx):
    """Check if someone can use clear"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"clear")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_messages

async def can_see_banlist(ctx):
    """Check if someone can see the banlist"""
    return ctx.channel.permissions_for(ctx.author).administrator or await ctx.bot.cogs["AdminCog"].check_if_admin(ctx)

async def can_pin_msg(ctx):
    """... if someone can pin a message"""
    return ctx.channel.permissions_for(ctx.author).manage_messages or await ctx.bot.cogs["AdminCog"].check_if_admin(ctx)