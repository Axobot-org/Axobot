import logging
import random

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot
from core.checks import checks
from core.safedict import SafeDict

RANDOM_NAMES_URL = "https://randommer.io/api/Name?nameType=surname&quantity=20"
MINECRAFT_ENTITIES_URL = "https://raw.githubusercontent.com/PixiGeko/Minecraft-generated-data/master/1.21/releases/1.21/"\
    "custom-generated/tags/universal_tags/entity_type.json"


class VoiceChannels(commands.Cog):
    "Create automated voice channels and give roles to voice members"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "voice_channels"
        self.log = logging.getLogger("bot.voice_channels")
        self.names: dict[str, list[str]] = {"random": [], "minecraft": []}
        self.channels: dict[int, list[int]] = {}
        self.table = "voices_chats"

    async def cog_load(self):
        await self.db_get_channels()

    @commands.Cog.listener()
    async def on_ready(self):
        "if the database is still offline when the bot is ready, remove that cog"
        if not self.bot.database_online:
            await self.bot.unload_module("voice_channels")

    async def db_get_channels(self):
        "Refresh the channels cache"
        if not self.bot.database_online:
            return
        beta_condition = '' if self.bot.beta else "NOT "
        async with self.bot.db_main.read(f"SELECT * FROM {self.table} WHERE {beta_condition}beta") as query_results:
            for row in query_results:
                guild = int(row["guild"])
                channel = int(row["channel"])
                self.channels[guild] = self.channels.get(guild, list()) + [channel]

    async def db_add_channel(self, channel: discord.VoiceChannel):
        "Add a newly created channel to the database and cache"
        arg = (channel.guild.id, channel.id, self.bot.beta)
        async with self.bot.db_main.write(f"INSERT INTO `{self.table}` (`guild`,`channel`,`beta`) VALUES (%s, %s, %s)", arg):
            pass
        prev = self.channels.get(channel.guild.id, [])
        self.channels[channel.guild.id] = prev + [channel.id]

    async def db_delete_channel(self, channel: discord.VoiceChannel):
        "Delete a voice channel from the database and cache"
        arg = (channel.guild.id, channel.id)
        async with self.bot.db_main.write(f"DELETE FROM {self.table} WHERE guild=%s AND channel=%s", arg):
            pass
        try:
            self.channels[channel.guild.id].remove(channel.id)
        except (KeyError, ValueError):
            return

    async def give_roles(self, member: discord.Member, remove: bool = False):
        "Give roles to a member joining/leaving a voice channel"
        if not self.bot.database_online:
            return
        if not member.guild.me.guild_permissions.manage_roles:
            self.log.info("Missing \"manage_roles\" permission on guild %s", member.guild.id)
            return
        roles: list[discord.Role] | None = await self.bot.get_config(
            member.guild.id, "voice_roles"
        ) # pyright: ignore[reportAssignmentType]
        if not roles:
            return
        pos = member.guild.me.top_role.position
        filtered_roles = filter(lambda x: x.position < pos, roles)
        if remove:
            await member.remove_roles(*filtered_roles, reason="Left the voice chat")
        else:
            await member.add_roles(*filtered_roles, reason="Joined a voice chat")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Deletes a voice channel in the database when deleted in Discord"""
        if isinstance(channel, discord.VoiceChannel):
            await self.db_delete_channel(channel)
        # other cases are not interesting

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Check if a member joined/left a voice channel"""
        try:
            if before.channel == after.channel:
                return
            if not self.bot.database_online:
                return
            voice_channel: discord.VoiceChannel | None = await self.bot.get_config(
                member.guild.id,
                "voice_channel"
            ) # pyright: ignore[reportAssignmentType]
            if voice_channel is None:  # if nothing was setup
                return
            if after.channel == voice_channel:
                if before.channel is not None and len(before.channel.members) == 0: # move from another channel which is now empty
                    if (member.guild.id in self.channels) and (before.channel.id in self.channels[member.guild.id]):
                        # if they come from an automated channel, we move them back if the channel is now empty
                        await member.move_to(before.channel)
                        return
                await self.create_channel(member)
            if (
                isinstance(before.channel, discord.VoiceChannel)
                and (member.guild.id in self.channels)
                and (before.channel.id in self.channels[member.guild.id])
            ):
                await self.delete_channel(before.channel)
            if after.channel is None:
                await self.give_roles(member, remove=True)
            if before.channel is None:
                await self.give_roles(member)
        except Exception as err: # pylint: disable=broad-except
            self.bot.dispatch("error", err, f"Member {member}")

    async def create_channel(self, member: discord.Member):
        """Create a new voice channel
        The member will get "Manage channel" permissions automatically"""
        category: discord.CategoryChannel | None = await self.bot.get_config(
            member.guild.id,
            "voice_category"
        ) # pyright: ignore[reportAssignmentType]
        if category is None:  # if nothing was setup
            return
        perms = category.permissions_for(member.guild.me)
        # if bot is missing perms: abort
        if not (perms.manage_channels and perms.move_members):
            self.log.info("Missing \"manage_channels, move_members\" permission on guild %s", member.guild.id)
            return
        if member.voice is None or member.voice.channel is None:
            raise RuntimeError("Member is not in a voice channel")
        if not (member.voice.channel.permissions_for(member.guild.me)).move_members:
            self.log.info("Missing \"move_members\" permission on channel %s", member.voice.channel.id)
            return
        p = len(category.channels)
        # try to calculate the correct permissions
        d = member.guild.me.guild_permissions
        d = {k: v for k, v in dict(d).items() if v}
        over = {
            member: discord.PermissionOverwrite(**d),
            member.guild.me: discord.PermissionOverwrite(**d)}
        # remove manage roles cuz DISCOOOOOOOOOOORD
        over[member].manage_roles = None
        over[member.guild.me].manage_roles = None
        # build channel name from config and random
        chan_name: str = await self.bot.get_config(
            member.guild.id,
            "voice_channel_format"
        ) # pyright: ignore[reportAssignmentType]
        args = {
            "user": member.global_name or member.name,
            "number": random.randint(0, 1000)
        }
        if "{random}" in chan_name:
            args["random"] = await self.get_random_name()
        if "{minecraft}" in chan_name:
            args["minecraft"] = await self.get_mc_name()
        chan_name = chan_name.format_map(SafeDict(args))
        # actually create the channel
        new_channel = await category.create_voice_channel(name=chan_name, position=p, overwrites=over)
        # move user
        await member.move_to(new_channel)
        # add to database
        await self.db_add_channel(new_channel)

    async def delete_channel(self, channel: discord.VoiceChannel):
        """Delete an unusued channel if no one is in"""
        if len(channel.members) == 0 and channel.permissions_for(channel.guild.me).manage_channels:
            await channel.delete(reason="Unusued")
            await self.db_delete_channel(channel)

    async def get_random_name(self):
        "Get a random name from the randommer API"
        if len(self.names["random"]) != 0:
            return self.names["random"].pop()
        async with aiohttp.ClientSession() as session:
            header = {"X-Api-Key": self.bot.secrets["random_api_token"]}
            try:
                async with session.get(RANDOM_NAMES_URL, headers=header) as resp:
                    json: list[str] = await resp.json()
                    self.names["random"] = json
            except aiohttp.ContentTypeError as err:
                self.bot.dispatch("error", err)
                return "hello"
        return self.names["random"].pop()

    async def get_mc_name(self):
        "Get a random Minecraft entity name from a JSON file"
        if len(self.names["minecraft"]) != 0:
            return self.names["minecraft"].pop()
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(MINECRAFT_ENTITIES_URL) as resp:
                    data: dict[str, list[str]] = await resp.json()
                    json: list[str] = [
                        name.replace("minecraft:", '').replace('_', ' ') for name in data["values"]
                    ]
                    self.names["minecraft"] = json
                    random.shuffle(self.names["minecraft"])
            except aiohttp.ContentTypeError as err:
                self.bot.dispatch("error", err)
                return "hello"
        return self.names["minecraft"].pop()


    @app_commands.command(name="voice-clean")
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.guild_only()
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(1, 10)
    async def voice_clean(self, interaction: discord.Interaction):
        """Delete every unusued voice channels previously generated by the bot

        ..Doc server.html#voice-channels-managment"""
        if not interaction.guild_id in self.channels or len(self.channels[interaction.guild_id]) == 0:
            await interaction.response.send_message(
                await self.bot._(interaction, "voice_channels.no-channel"), ephemeral=True
            )
            return
        if interaction.guild is None:
            raise RuntimeError("This command can only be used in a guild")
        await interaction.response.defer()
        i = 0
        temp = []
        for chan in self.channels[interaction.guild_id]:
            d_chan = interaction.guild.get_channel(chan)
            if d_chan is None:
                continue
            if not isinstance(d_chan, (discord.VoiceChannel, discord.StageChannel)):
                self.bot.dispatch("error", TypeError(
                    f"Channel {chan} is not a voice channel in guild {interaction.guild_id}"
                ))
                continue
            if len(d_chan.members) == 0:
                await d_chan.delete(reason="unusued")
                temp.append(d_chan)
                i += 1
        for chan in temp:
            await self.db_delete_channel(chan)
        await interaction.followup.send(await self.bot._(interaction, "voice_channels.deleted", count=i))


async def setup(bot: Axobot):
    if bot.database_online:
        await bot.add_cog(VoiceChannels(bot))
