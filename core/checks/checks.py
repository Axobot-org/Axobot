import discord
from discord.ext import commands

from core.bot_classes import SUPPORT_GUILD_ID, MyContext
from core.bot_classes.axobot import Axobot
from core.checks.errors import NotAVoiceMessageError

admins_id = {279568324260528128,281404141841022976,552273019020771358}

async def is_bot_admin(ctx: MyContext | discord.Interaction | discord.User):
    "Check if the user is one of the bot administrators"
    if isinstance(ctx, commands.Context):
        user = ctx.author
    elif isinstance(ctx, discord.Interaction):
        user = ctx.user
    else:
        user = ctx
    if isinstance(user, str) and user.isnumeric():
        user = int(user)
    elif isinstance(user, discord.User | discord.Member):
        user = user.id
    return user in admins_id

async def is_support_staff(ctx: MyContext | discord.Interaction) -> bool:
    "Check if the user is one of the bot staff, either by flag or by role"
    user = ctx.author if isinstance(ctx, commands.Context) else ctx.user
    if user.id in admins_id:
        return True
    bot = ctx.bot if isinstance(ctx, commands.Context) else ctx.client
    if users_cog := bot.get_cog("Users"):
        return await users_cog.has_userflag(user, "support")
    server = bot.get_guild(SUPPORT_GUILD_ID.id)
    if server is not None:
        member = server.get_member(user.id)
        role = server.get_role(412340503229497361)
        if member is not None and role is not None:
            return role in member.roles
    return False

async def database_connected(ctx: MyContext | discord.Interaction[Axobot]) -> bool:
    "Check if the database is online and accessible"
    bot = ctx.client if isinstance(ctx, discord.Interaction) else ctx.bot
    if bot.database_online:
        return True
    raise commands.CommandError("Database offline")

async def is_voice_message(interaction: discord.Interaction):
    "Check if the message is a voice message"
    if "resolved" not in interaction.data or "messages" not in interaction.data["resolved"]:
        raise NotAVoiceMessageError()
    messages: dict[str, dict] = interaction.data["resolved"]["messages"]
    if len(messages) != 1:
        raise NotAVoiceMessageError()
    message = list(messages.values())[0]
    flags = discord.MessageFlags()
    flags.value = message.get("flags", 0)
    if not flags.voice:
        raise NotAVoiceMessageError()
    return True
