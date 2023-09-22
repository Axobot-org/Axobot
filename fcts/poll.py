from typing import Optional, Union

import discord
from discord import app_commands
from discord.ext import commands

from libs.bot_classes import Axobot


class PollCog(commands.Cog):
    """Allow server managers to create polls in their servers"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "poll"

    async def add_vote(self, msg: discord.Message):
        "Add votes emojis as reactions under a message"
        if self.bot.database_online and msg.guild is not None:
            emojis_list: list[Union[str, discord.Emoji]] = await self.bot.get_config(msg.guild.id, "vote_emojis")
        else:
            await msg.add_reaction('👍')
            await msg.add_reaction('👎')
            return
        for emoji in emojis_list:
            await msg.add_reaction(emoji)

    @commands.Cog.listener(name="on_message")
    async def check_suggestion(self, message: discord.Message):
        "Check for any message sent in a poll channel, in order to add proper reactions"
        if message.guild is None or not self.bot.is_ready() or not self.bot.database_online or message.content.startswith('.'):
            return
        try:
            channels: Optional[list[discord.TextChannel]] = await self.bot.get_config(message.guild.id, "poll_channels")
            if channels is None:
                return
            if message.channel in channels and not message.author.bot:
                try:
                    await self.add_vote(message)
                except discord.DiscordException:
                    pass
        except Exception as err: # pylint: disable=broad-except
            self.bot.dispatch("error", err, message)


    @app_commands.command(name="poll")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.cooldown(4, 30)
    async def poll(self, interaction: discord.Interaction,
                   options_count: app_commands.Range[int, 1, 20],
                   channel: Union[None, discord.TextChannel, discord.VoiceChannel, discord.StageChannel] = None
                   ):
        """Create a poll in the current channel"""
        destination_channel = channel or interaction.channel
        if destination_channel is None:
            await interaction.response.send_message(await self.bot._(interaction.channel,"poll.no-channel"), ephemeral=True)
            return
        bot_perms = destination_channel.permissions_for(interaction.guild.me)
        if not (bot_perms.read_message_history and bot_perms.add_reactions):
            await interaction.response.send_message(await self.bot._(interaction.channel,"poll.cant-react"), ephemeral=True)
            return
        if options_count > 10 and not bot_perms.external_emojis:
            await interaction.response.send_message(await self.bot._(interaction.channel,"poll.too-many-options"), ephemeral=True)
            return
        await interaction.response.defer()
        text = "TO BE IMPLEMENTED"
        if options_count == 1:
            msg = await destination_channel.send(text)
            await self.add_vote(msg)
        else:
            if bot_perms.external_emojis:
                emojis = self.bot.emojis_manager.numbers_names
            else:
                emojis = [chr(48+i)+chr(8419) for i in range(10)]
            msg = await destination_channel.send(text)
            for i in range(1, options_count + 1):
                await msg.add_reaction(emojis[i])
        await interaction.edit_original_response(content=await self.bot._(interaction.channel, "poll.created", url=msg.jump_url))


async def setup(bot: Axobot):
    await bot.add_cog(PollCog(bot))
