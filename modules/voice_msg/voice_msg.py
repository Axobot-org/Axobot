import logging
import time

import discord
from aiohttp import ClientSession
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot
from core.checks import checks
from core.formatutils import FormatUtils


class VoiceMessages(commands.Cog):
    "Allow to get voice messages transcript"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "voice_msg"
        self.log = logging.getLogger("bot.voice_msg")
        self.stt_ctx_menu = app_commands.ContextMenu(
            name='Voice to text',
            callback=self.handle_message_command,
        )
        self.bot.tree.add_command(self.stt_ctx_menu)
        self.max_duration = 2*60
        self.cache: dict[int, str] = {}
        self._session: ClientSession | None = None

    @property
    def session(self):
        "Get the aiohttp session"
        if self._session is None:
            self._session = ClientSession()
        return self._session

    async def cog_unload(self):
        "Close the aiohttp session"
        if self._session is not None:
            await self._session.close()

    @app_commands.checks.cooldown(2, 90)
    @app_commands.check(checks.is_voice_message)
    async def handle_message_command(self, interaction: discord.Interaction, message: discord.Message):
        "Create a transcript of the voice message"
        attachment = message.attachments[0]
        await interaction.response.defer(ephemeral=True)
        # if voice message is too long, abort
        if attachment.duration > self.max_duration:
            lang = await self.bot._(interaction, "_used_locale")
            f_max_duration = await FormatUtils.time_delta(self.max_duration, lang=lang)
            await interaction.followup.send(
                await self.bot._(interaction.user, "voice_msg.attachment-too-long", duration=f_max_duration),
                ephemeral=True)
            return
        if message.id in self.cache:
            # if message is in the cache, use it
            result = self.cache[message.id]
            duration = None
            self.log.debug("Transcript already available in cache: skipping API call")
        else:
            # else generate it
            start = time.time()
            result = await self._get_transcript(attachment)
            duration = time.time() - start
            self.log.info(
                "Transcript done in %ss (original duration: %ss)",
                round(duration, 1), round(attachment.duration, 1)
            )
            self.bot.dispatch("voice_transcript_completed", attachment.duration, duration)
            self.cache[message.id] = result
        # no transcript found, alert the user
        if not result:
            self.cache[message.id] = ""
            await interaction.followup.send(
                await self.bot._(interaction.user, "voice_msg.no-transcript"),
                ephemeral=True
            )
            self.log.info("Transcript is empty")
            return
        # if transcript is too long, truncate it
        if len(result) > 1900:
            result = result[:1900] + "…"
        result += "\n\n*" + await self.bot._(interaction.user, "voice_msg.openai-credits",
                                            url="https://github.com/openai/whisper") + '*'
        emb = discord.Embed(
            title=await self.bot._(interaction.user, "voice_msg.title"),
            description=result,
            color=discord.Color.blurple()
        )
        await interaction.followup.send(embed=emb, ephemeral=True)

    async def _get_transcript(self, attachment: discord.Attachment) -> str:
        "Call the external API to get the audio transcript"
        headers = {'Authorization': self.bot.others["awhikax_api"]}
        data = {'status': "default", 'audio': attachment.url}
        async with self.session.post("https://api.awhikax.com/stt", headers=headers, data=data) as resp:
            if resp.status != 200:
                return ""
            response = await resp.json()
        if response["success"]:
            return response["message"]
        return ""


async def setup(bot):
    await bot.add_cog(VoiceMessages(bot))
