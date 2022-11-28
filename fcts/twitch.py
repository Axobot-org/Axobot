import json
from typing import Optional, TypedDict

import discord
from dateutil.parser import isoparse
from discord import app_commands
from discord.ext import commands, tasks
from mysql.connector.errors import IntegrityError

from libs.bot_classes import MyContext, Zbot
from libs.twitch.api_agent import TwitchApiAgent
from libs.twitch.types import (GroupedStreamerDBObject, PlatformId,
                               StreamersDBObject, StreamObject)


class _StreamersReadyForNotification(TypedDict):
    platform: PlatformId
    user_id: str
    user_name: str
    is_streaming: bool
    guilds: list[discord.Guild]

class Twitch(commands.Cog):
    "Handle twitch streams"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "twitch"
        self.agent = TwitchApiAgent()
        self.twitch_color = 0x6441A4

    async def cog_load(self):
        await self.agent.api_login(
            self.bot.others["twitch_client_id"],
            self.bot.others["twitch_client_secret"]
        )
        self.bot.log.info("[twitch] connected to API")
        self.stream_check_task.start()

    async def cog_unload(self):
        "Close the Twitch session"
        await self.agent.close_session()
        self.bot.log.info("[twitch] connection closed")
        self.stream_check_task.cancel()

    async def db_add_streamer(self, guild_id: int, platform: PlatformId, user_id: str, user_name: str):
        "Add a streamer to the database"
        query = "INSERT INTO `streamers` (`guild_id`, `platform`, `user_id`, `user_name`, `beta`) VALUES (%s, %s, %s, %s, %s)"
        try:
            async with self.bot.db_query(query, (guild_id, platform, user_id, user_name, self.bot.beta), returnrowcount=True) as query_result:
                return query_result > 0
        except IntegrityError:
            return False

    async def db_get_guild_subscriptions_count(self, guild_id: int) -> Optional[int]:
        "Get the number of subscriptions for a guild"
        query = "SELECT COUNT(*) FROM `streamers` WHERE `guild_id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta), astuple=True) as query_result:
            return query_result[0][0] if query_result else None

    async def db_get_guild_streamers(self, guild_id: int, platform: Optional[PlatformId]=None) -> list[StreamersDBObject]:
        "Get the streamers for a guild"
        query = "SELECT * FROM `streamers` WHERE `guild_id` = %s AND `beta` = %s"
        args = [guild_id, self.bot.beta]
        if platform is not None:
            query += " AND `platform` = %s"
            args.append(platform)
        async with self.bot.db_query(query, args) as query_result:
            return query_result

    async def db_get_guilds_per_streamers(self, platform: Optional[PlatformId]=None) -> list[GroupedStreamerDBObject]:
        "Get all streamers objects"
        where = "" if platform is None else f"AND `platform` = \"{platform}\""
        query = f"SELECT `platform`, `user_id`, `user_name`, `is_streaming`, JSON_ARRAYAGG(`guild_id`) as \"guild_ids\" FROM `streamers` WHERE `beta` = %s {where} GROUP BY `platform`, `user_id`; "
        async with self.bot.db_query(query, (self.bot.beta,)) as query_result:
            return [
                data | {"guild_ids": json.loads(data["guild_ids"])}
                for data in query_result
            ]

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

    async def db_get_streamer_status(self, platform: PlatformId, user_id: str) -> Optional[bool]:
        "Get the streaming status of a streamer"
        query = "SELECT `is_streaming` FROM `streamers` WHERE `platform` = %s AND `user_id` = %s AND `beta` = %s LIMIT 1"
        async with self.bot.db_query(query, (platform, user_id, self.bot.beta), astuple=True) as query_result:
            return query_result[0][0] if query_result else None

    async def db_get_streamer_name(self, platform: PlatformId, user_id: str) -> Optional[str]:
        "Get the last known name of a streamer from its ID and platform"
        query = "SELECT `user_name` FROM `streamers` WHERE `platform` = %s AND `user_id` = %s AND `beta` = %s LIMIT 1"
        async with self.bot.db_query(query, (platform, user_id, self.bot.beta), astuple=True) as query_result:
            return query_result[0][0] if query_result else None

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
        await ctx.defer()
        try:
            user = await self.agent.get_user_by_name(streamer)
        except ValueError:
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.invalid-streamer-name"))
            return
        if user is None:
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.unknown-streamer"))
            return
        streamers_count = await self.db_get_guild_subscriptions_count(ctx.guild.id)
        max_count = await self.bot.get_config(ctx.guild.id,'streamers_max_number')
        if streamers_count >= max_count:
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.subscribe.limit-reached", max_count))
            return
        if await self.db_add_streamer(ctx.guild.id, "twitch", user["id"], user["display_name"]):
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.subscribe.success", streamer=user["display_name"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.subscribe.already-subscribed", streamer=user["display_name"]))

    @twitch.command(name="unsubscribe")
    async def twitch_unsub(self, ctx: MyContext, streamer: str):
        "Unsubscribe from a Twitch streamer"
        if streamer.isnumeric():
            user_id = streamer
            user_name = await self.db_get_streamer_name("twitch", user_id)
        else:
            if user := await self.agent.get_user_by_name(streamer):
                user_id = user["id"]
                user_name = user["display_name"]
            else:
                await ctx.send(await self.bot._(ctx.guild.id, "twitch.unknown-streamer"))
                return
        if await self.db_remove_streamer(ctx.guild.id, "twitch", user_id):
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.unsubscribe.success", streamer=user_name))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.unsubscribe.not-subscribed", streamer=user_name))

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
        await ctx.defer()
        streamers = await self.db_get_guild_streamers(ctx.guild.id, "twitch")
        max_count = await self.bot.get_config(ctx.guild.id,'streamers_max_number')
        if streamers:
            title = await self.bot._(ctx.guild.id, "twitch.subs-list.title", current=len(streamers), max=max_count)
            on_live = await self.bot._(ctx.guild.id, "twitch.on-live-indication")
            streamers_name = [
                streamer["user_name"] + (f"  *({on_live})*" if streamer["is_streaming"] else "")
                for streamer in streamers
            ]
            streamers_name.sort(key=str.casefold)
            await ctx.send(title+"\n• " + "\n• ".join(streamers_name))
        else:
            txt = await self.bot._(ctx.guild.id, "twitch.subs-list.empty", max=max_count)
            cmd = await self.bot.get_command_mention("twitch subscribe")
            txt += "\n" + await self.bot._(ctx.guild.id, "twitch.subs-list.empty-tip", cmd=cmd, max=max_count)
            await ctx.send(txt)

    @twitch.command(name="check-stream")
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def test_twitch(self, ctx: MyContext, streamer: str):
        "Check if a streamer is currently streaming"
        if streamer.isnumeric():
            user_id = streamer
        else:
            try:
                user_id = (await self.agent.get_user_by_name(streamer))["id"]
            except ValueError:
                await ctx.send(await self.bot._(ctx.guild.id, "twitch.invalid-streamer-name"))
                return
        resp = await self.agent.get_user_stream_by_id(user_id)
        if len(resp) > 0:
            stream = resp[0]
            if stream["is_mature"] and not ctx.channel.is_nsfw():
                await ctx.send(await self.bot._(ctx.guild.id, "twitch.check-stream.no-nsfw"))
                return
            await ctx.send(embed=await self.create_stream_embed(stream, ctx.guild.id))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "twitch.check-stream.offline", streamer=streamer))

    async def create_stream_embed(self, stream: StreamObject, guild_id: int):
        started_at = isoparse(stream["started_at"])
        embed = discord.Embed(
            title=await self.bot._(guild_id, "twitch.check-stream.title", streamer=stream["user_name"]),
            url=f"https://twitch.tv/{stream['user_name']}",
            color=self.twitch_color,
            timestamp=started_at,
            description=stream["title"],
        )
        embed.set_image(url=stream["thumbnail_url"].format(width=1280, height=720))
        return embed

    async def find_streamer_in_guild(self, streamer_name: str, guild: discord.Guild):
        "Try to find a member currently streaming with this streamer name in the given guild"
        streamer_name = streamer_name.lower()
        for member in guild.members:
            if member.bot or not member.activities:
                continue
            for activity in member.activities:
                if activity.type != discord.ActivityType.streaming:
                    continue
                if activity.twitch_name and activity.twitch_name.lower() == streamer_name:
                    return member

    async def send_stream_alert(self, stream: StreamObject, channel: discord.abc.GuildChannel):
        "Send a stream alert to a guild when a streamer is live"
        msg = await self.bot._(channel.guild, "twitch.stream-alerts", streamer=stream["user_name"], game=stream["game_name"])
        allowed_mentions = discord.AllowedMentions.none()
        if role_id := await self.bot.get_config(channel.guild.id, "stream_mention"):
            if role := channel.guild.get_role(int(role_id)):
                msg = role.mention + " " + msg
                allowed_mentions = discord.AllowedMentions(roles=[role])
        if channel.permissions_for(channel.guild.me).embed_links:
            embed = await self.create_stream_embed(stream, channel.guild.id)
        else:
            embed = None
            msg += f"\nhttps://twitch.tv/{stream['user_name']}"
        await channel.send(
            msg,
            embed=embed,
            allowed_mentions=allowed_mentions
        )


    @commands.Cog.listener()
    async def on_stream_starts(self, stream: StreamObject, guild: discord.Guild):
        "When a stream starts, send a notification to the subscribed guild"
        # Send notification
        if (channel_id := await self.bot.get_config(guild.id, "streaming_channel")) and channel_id.isnumeric():
            if channel := guild.get_channel(int(channel_id)):
                await self.send_stream_alert(stream, channel)
            else:
                self.bot.log.warn("[twitch] Channel %s not found in guild %s", channel_id, guild.id)
        # Grant role
        if (role_id := await self.bot.get_config(guild.id, "streaming_role")) and role_id.isnumeric():
            if role := guild.get_role(int(role_id)):
                if member := await self.find_streamer_in_guild(stream["user_name"], guild):
                    try:
                        await member.add_roles(role, reason="Twitch streamer is live")
                    except discord.Forbidden:
                        self.bot.log.info("[twitch] Cannot add role %s to member %s in guild %s: Forbidden", role_id, member.id, guild.id)
            else:
                self.bot.log.warn("[twitch] Role %s not found in guild %s", role_id, guild.id)

    @tasks.loop(minutes=5)
    async def stream_check_task(self):
        "Check if any subscribed streamer is streaming and send notifications"
        await self.bot.wait_until_ready()
        count = 0
        streamer_ids: dict[str, _StreamersReadyForNotification] = {}
        for streamer in await self.db_get_guilds_per_streamers("twitch"):
            guilds = [self.bot.get_guild(guild_id) for guild_id in streamer["guild_ids"]]
            guilds = [guild for guild in guilds if guild]
            if not guilds:
                continue
            streamer_ids[streamer["user_id"]] = streamer | {"guilds": guilds}
            count += 1
            # make one request every 30 streamers
            if len(streamer_ids) > 30:
                await self._update_streams(streamer_ids)
                streamer_ids = {}
        if streamer_ids:
            await self._update_streams(streamer_ids)
        self.bot.log.info(f"[twitch] {count} streamers checked")

    async def _update_streams(self, streamer_ids: dict[str, _StreamersReadyForNotification]):
        streaming_user_ids: set[str] = set()
        # Check current streams
        for stream in await self.agent.get_user_stream_by_id(*streamer_ids.keys()):
            streamer_data = streamer_ids[stream["user_id"]]
            # mark that this streamer is streaming
            streaming_user_ids.add(stream["user_id"])
            # if it was already notified, skip
            if streamer_data["is_streaming"]:
                continue
            # dispatch event
            for guild in streamer_data["guilds"]:
                self.bot.dispatch("stream_starts", stream, guild)
            # mark streamers as streaming
            await self.db_set_streamer_status("twitch", stream["user_id"], True)
        # Check streamers that went offline
        for streamer_id, streamer_data in streamer_ids.items():
            if streamer_id not in streaming_user_ids and streamer_data["is_streaming"]:
                for guild in streamer_data["guilds"]:
                    self.bot.dispatch("stream_ends", streamer_data["user_name"], guild)
                # mark streamers as offline
                await self.db_set_streamer_status("twitch", streamer_id, False)


async def setup(bot: Zbot):
    await bot.add_cog(Twitch(bot))