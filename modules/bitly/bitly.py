import discord
from discord import app_commands
from discord.ext import commands

from core.arguments import args
from core.bot_classes import Axobot

from .api import bitly_api


class Bitly(commands.Cog):
    "Shorten or expand urls using Bitly services"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bitly"
        self.bitly_client = bitly_api.Bitly(api_key=self.bot.others['bitly'])

    bitly_main = app_commands.Group(
        name="bitly",
        description="Create shortened url and unpack them by using Bitly services",
    )

    @bitly_main.command(name="create")
    @app_commands.describe(url="The url you want to shorten")
    @app_commands.checks.cooldown(3, 15)
    async def bitly_create(self, interaction: discord.Interaction, url: args.URLArgument):
        """Create a shortened url

        ..Example bitly create https://fr-minecraft.net

        ..Doc miscellaneous.html#bitly-urls"""
        if url.domain == 'bit.ly':
            return await interaction.response.send_message(await self.bot._(interaction, "info.bitly_already_shortened"))
        await interaction.response.defer()
        shortened_url = self.bitly_client.shorten_url(url.url)
        await interaction.followup.send(await self.bot._(interaction, "info.bitly_short", url=shortened_url))

    @bitly_main.command(name="find")
    @app_commands.describe(url="The url to expand. Should starts with https://bit.ly/")
    @app_commands.checks.cooldown(3, 15)
    async def bitly_find(self, interaction: discord.Interaction, url: args.URLArgument):
        """Find the long url from a bitly link

        ..Example bitly find https://bit.ly/2JEHsUf

        ..Doc miscellaneous.html#bitly-urls"""
        if url.domain != 'bit.ly':
            return await interaction.response.send_message(await self.bot._(interaction, "info.bitly_nobit"))
        await interaction.response.defer()
        expanded_url = self.bitly_client.expand_url(url.url)
        await interaction.followup.send(await self.bot._(interaction, "info.bitly_long", url=expanded_url))


async def setup(bot):
    await bot.add_cog(Bitly(bot))
