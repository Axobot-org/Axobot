from io import BytesIO
from typing import Optional

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image

from libs.arguments import args
from libs.bot_classes import Axobot
from libs.quote.generator import QuoteGeneration, QuoteStyle


class Quote(commands.Cog):
    "Handle features like quoting a message and Quote of the day"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "quote"
        self.max_characters = 600
        self.quote_ctx_menu = app_commands.ContextMenu(
            name="Quote",
            callback=self.quote_context_command,
        )
        self.bot.tree.add_command(self.quote_ctx_menu)

    async def cog_unload(self):
        "Disable the Quote context menu"
        self.bot.tree.remove_command(self.quote_ctx_menu.name, type=self.quote_ctx_menu.type)

    async def quote_context_command(self, interaction: discord.Interaction, message: discord.Message):
        await self.quote_command(interaction, message, style="classic")

    async def quote_command(self, interaction: discord.Interaction, message: discord.Message, style: QuoteStyle):
        "Quote a message using the context menu"
        # check if message exists
        if not message.content:
            await interaction.response.send_message(
                await self.bot._(interaction.user, "quote.error.empty-message"),
                ephemeral=True
            )
            return
        # check if message is not too long
        if len(message.content) > self.max_characters:
            await interaction.response.send_message(
                await self.bot._(interaction.user, "quote.error.too-long", max=self.max_characters),
                ephemeral=True
            )
            return
        # defer and try to generate the quote
        await interaction.response.defer(ephemeral=True)
        if msg := await self.quote_message(message, interaction.channel, style):
            await interaction.followup.send(
                f"Your quote has been posted to {msg.jump_url}"
            )
        else:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))

    @app_commands.command(name="quote")
    @app_commands.checks.cooldown(2, 30)
    @app_commands.describe(message="The URL of the message to quote")
    async def quote_slash_cmd(self, interaction: discord.Interaction, message: args.MessageArgument, style: QuoteStyle="classic"):
        "Quote a message using the slash command"
        await self.quote_command(interaction, message, style)


    async def quote_message(
            self, message: discord.Message, channel: discord.abc.Messageable, style: QuoteStyle
            ) -> Optional[discord.Message]:
        "Generate a Quote card from a message and post it to the channel"
        text = discord.utils.remove_markdown(message.clean_content)
        while '\n\n' in text:
            text = text.replace('\n\n', '\n')
        author_name = message.author.display_name
        author_avatar = await self.get_image_from_url(message.author.display_avatar.replace(format="png", size=256).url)
        generator = QuoteGeneration(
            text,
            author_name,
            author_avatar,
            message.created_at,
            style,
        )
        generated_card = generator.draw_card()

        img_byte_arr = BytesIO()
        generated_card.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        file = discord.File(img_byte_arr, filename="quote.png")
        return await channel.send(file=file)

    async def get_image_from_url(self, url: str):
        "Download an image from an url"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return Image.open(BytesIO(await response.read()))


async def setup(bot: Axobot):
    await bot.add_cog(Quote(bot))
