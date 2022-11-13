from typing import Optional
from dateutil.parser import isoparse

import discord
from discord import app_commands
from discord.ext import commands

from libs.bot_classes import PRIVATE_GUILD_ID, MyContext, Zbot
from libs.twitch.api_agent import TwitchApiAgent
from libs.twitch.types import PlatformId, StreamersDBObject

class Twitch(commands.Cog):
    "Handle twitch streams"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "twitch"
        self.agent = TwitchApiAgent()

    async def cog_load(self):
        await self.agent.api_login(
            self.bot.others["twitch_client_id"],
            self.bot.others["twitch_client_secret"]
        )
        self.bot.log.info("[twitch] connected to API")

    async def cog_unload(self):
        "Close the Twitch session"
        await self.agent.close_session()
        self.bot.log.info("[twitch] connection closed")

    async def db_add_streamer(self, guild_id: int, platform: PlatformId, user_id: str, user_name: str):
        "Add a streamer to the database"
        query = "INSERT INTO `streamers` (`guild_id`, `platform`, `user_id`, `user_name`, `beta`) VALUES (%s, %s, %s, %s, %s)"
        async with self.bot.db_query(query, (guild_id, platform, user_id, user_name, self.bot.beta), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_get_guild_streamers(self, guild_id: int, platform: Optional[PlatformId]=None) -> list[StreamersDBObject]:
        "Get the streamers for a guild"
        query = "SELECT * FROM `streamers` WHERE `guild_id` = %s AND `beta` = %s"
        args = [guild_id, self.bot.beta]
        if platform is not None:
            query += " AND `platform` = %s"
            args.append(platform)
        async with self.bot.db_query(query, args) as query_result:
            return query_result

    async def db_get_streamers(self, platform: Optional[PlatformId]=None) -> list[StreamersDBObject]:
        "Get all streamers objects"
        query = "SELECT * FROM `streamers` WHERE `beta` = %s"
        args = [self.bot.beta]
        if platform is not None:
            query += " AND `platform` = %s"
            args.append(platform)
        async with self.bot.db_query(query, args) as query_result:
            return query_result

    async def db_remove_streamer(self, guild_id: int, platform: PlatformId, user_id: str):
        "Remove a streamer from the database"
        query = "DELETE FROM `streamers` WHERE `guild_id` = %s AND `platform` = %s AND `user_id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, platform, user_id, self.bot.beta), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_set_streamer_status(self, platform: PlatformId, user_id: str, is_streaming: bool):
        "Set the streaming status of a streamer"
        query = "UPDATE `streamers` SET `is_streaming` = %s WHERE `platform` = %s AND `user_id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (is_streaming, platform, user_id, self.bot.beta), returnrowcount=True) as query_result:
            return query_result > 0

    @commands.hybrid_group(name="twitch")
    @app_commands.default_permissions(manage_guild=True)
    @commands.guild_only()
    async def twitch(self, ctx: MyContext):
        "Twitch commands"
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @twitch.command(name="subscribe")
    async def twitch_sub(self, ctx: MyContext, streamer: str):
        "Subscribe to a Twitch streamer"
        user = await self.agent.get_user_by_name(streamer)
        if user is None:
            await ctx.send("User not found")
            return
        if await self.db_add_streamer(ctx.guild.id, "twitch", user["id"], user["display_name"]):
            await ctx.send(f"Subscribed to channel {user['display_name']}")
        else:
            await ctx.send("Channel already subscribed!")

    @twitch.command(name="unsubscribe")
    async def twitch_unsub(self, ctx: MyContext, streamer: str):
        "Unsubscribe from a Twitch streamer"
        if streamer.isnumeric():
            user_id = streamer
        else:
            if user := await self.agent.get_user_by_name(streamer):
                user_id = user["id"]
            else:
                await ctx.send("User not found")
                return
        if await self.db_remove_streamer(ctx.guild.id, "twitch", user_id):
            await ctx.send(f"Unsubscribed to channel")
        else:
            await ctx.send("User not subscribed!")

    @twitch_unsub.autocomplete("streamer")
    async def twitch_unsub_autocomplete(self, ctx: MyContext, current: str):
        "Autocomplete for twitch_unsub"
        current = current.lower()
        streamers = await self.db_get_guild_streamers(ctx.guild.id, "twitch")
        filtered = [
            (not streamer["user_name"].lower().startswith(current), streamer["user_name"], streamer["user_id"])
            for streamer in streamers
            if current in streamer["user_name"].lower() or current == streamer["user_id"]
        ]
        filtered.sort()
        return [
            app_commands.Choice(name=name, value=value)
            for _, name, value in filtered
        ]

    @twitch.command(name="list-subscriptions")
    async def twitch_list(self, ctx: MyContext):
        "List all subscribed Twitch streamers"
        streamers = await self.db_get_guild_streamers(ctx.guild.id, "twitch")
        if streamers:
            await ctx.send("Subscribed to:\n• " + "\n• ".join(streamer["user_name"] for streamer in streamers))

    @twitch.command(name="check-stream")
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def test_twitch(self, ctx: MyContext, streamer: str):
        "Check if a streamer is currently streaming"
        if streamer.isnumeric():
            user_id = streamer
        else:
            user_id = (await self.agent.get_user_by_name(streamer))["id"]
        resp = await self.agent.get_user_stream_by_id(user_id)
        if len(resp) > 0:
            stream = resp[0]
            if stream["is_mature"] and not ctx.channel.is_nsfw():
                await ctx.send("This stream is marked as mature, and this channel is not NSFW")
                return
            started_at = isoparse(stream["started_at"])
            embed = discord.Embed(
                title=f"{stream['user_name']} is streaming!",
                url=f"https://twitch.tv/{stream['user_name']}",
                color=0x6441A4,
                timestamp=started_at,
                description=stream["title"],
            )
            embed.set_image(url=stream["thumbnail_url"].format(width=1280, height=720))
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"User {streamer} is not streaming")


async def setup(bot: Zbot):
    await bot.add_cog(Twitch(bot))