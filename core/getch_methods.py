import discord


async def getch_channel_or_thread(guild: discord.Guild, channel_id: int):
    """Get a channel from its ID, or None if not found

    This method will first look in the guild's cache before attempting to fetch the channel from the API.
    """
    if channel := guild.get_channel_or_thread(channel_id):
        return channel
    try:
        return await guild.fetch_channel(channel_id)
    except (discord.NotFound, discord.Forbidden):
        return None

async def getch_member(guild: discord.Guild, member_id: int):
    """Get a member from its ID, or None if not found

    This method will first look in the guild's cache before attempting to fetch the member from the API.
    """
    if member := guild.get_member(member_id):
        return member
    try:
        return await guild.fetch_member(member_id)
    except discord.NotFound:
        return None
