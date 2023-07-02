import re
from typing import TYPE_CHECKING, Callable, Optional, Union

import discord

from libs.formatutils import FormatUtils

from .types import DbTask

if TYPE_CHECKING:
    from libs.bot_classes import Axobot

class RecreateReminderView(discord.ui.View):
    "A simple view allowing users to recreate a sent reminder"

    def __init__(self, bot: "Axobot", task: DbTask):
        self.bot = bot
        self.task = task
        self.message: Optional[discord.Message] = None
        super().__init__(timeout=60*60) # 1h

    async def init(self):
        "Create the button with the correct label"
        def on_pressed_decorator(duration: int):
            async def on_pressed(interaction: discord.Interaction):
                await self.on_pressed(interaction, duration)
            return on_pressed
        identic_duration = await FormatUtils.time_delta(
            self.task['duration'],
            lang=await self.bot._(self._get_translator_context(), '_used_locale'),
            form='developed'
        )
        identic_btn = discord.ui.Button(label="+ " + identic_duration, style=discord.ButtonStyle.blurple, emoji='⏰')
        identic_btn.callback = on_pressed_decorator(self.task['duration'])
        self.add_item(identic_btn)
        # 10min button
        if self.task['duration'] != 60 * 10:
            ten_min_duration = await FormatUtils.time_delta(
                60 * 10,
                lang=await self.bot._(self._get_translator_context(), '_used_locale'),
                form='developed'
            )
            ten_min_btn = discord.ui.Button(label="+ " + ten_min_duration, style=discord.ButtonStyle.blurple, emoji='⏰')
            ten_min_btn.callback = on_pressed_decorator(60 * 10)
            self.add_item(ten_min_btn)
        # custom duration button
        custom_duration_label = await self.bot._(self._get_translator_context(), "timers.rmd.custom-duration.button")
        custom_duration_btn = discord.ui.Button(label=custom_duration_label, style=discord.ButtonStyle.gray, emoji='⏰')
        custom_duration_btn.callback = self.on_custom_duration_pressed
        self.add_item(custom_duration_btn)

    def _get_translator_context(self):
        return self.task["guild"] or self.bot.get_user(self.task["user"])

    async def on_pressed(self, interaction: discord.Interaction, duration):
        "Called when the button is pressed"
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        self.bot.dispatch("reminder_snooze", self.task["duration"], duration)
        # remove the last hyperlink markdown from the message
        clean_msg = re.sub(r'\s+\[.+?\]\(.+?\)$', '', self.task['message'])
        await self.bot.task_handler.add_task(
                "timer",
                duration,
                self.task["user"],
                self.task["guild"],
                self.task["channel"],
                clean_msg,
                self.task["data"]
            )
        f_duration = await FormatUtils.time_delta(
            duration,
            lang=await self.bot._(interaction.user, '_used_locale'),
            form='developed'
        )
        await interaction.followup.send(
            await self.bot._(interaction.user, "timers.rmd.recreated", duration=f_duration),
            ephemeral=True
        )
        await self.disable(interaction)

    async def on_custom_duration_pressed(self, interaction: discord.Interaction):
        "Called when the custom duration button is pressed"
        await interaction.response.send_modal(AskDurationModal(
            title=await self.bot._(interaction.user, "timers.rmd.custom-duration.title"),
            input_label=await self.bot._(interaction.user, "timers.rmd.custom-duration.input"),
            callback=self.on_pressed
        ))

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.task['user']

    async def disable(self, interaction: Union[discord.Interaction, discord.Message]):
        "Called when the timeout has expired"
        for child in self.children:
            child.disabled = True
        if isinstance(interaction, discord.Interaction):
            await interaction.followup.edit_message(
                interaction.message.id,
                content=interaction.message.content,
                view=self
            )
        else:
            await interaction.edit(content=interaction.content, view=self)
        self.stop()

    async def on_timeout(self):
        "Called when the timeout has expired"
        if self.message:
            self.clear_items()
            await self.message.edit(content=self.message.content, view=self)


class AskDurationModal(discord.ui.Modal):
    "Ask a user to enter a duration for a reminder snooze"
    raw_duration = discord.ui.TextInput(label="", placeholder="1h 30m", style=discord.TextStyle.short, max_length=20)

    def __init__(self, title: str, input_label: str, callback: Callable[[discord.Interaction, int], None]):
        super().__init__(title=title)
        self.callback = callback
        self.raw_duration.label = input_label

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            duration = await FormatUtils.parse_duration(self.raw_duration.value)
            await self.callback(interaction, duration)
        except ValueError:
            await interaction.edit_original_response(
                content="The duration you entered is invalid. Please try again."
            )
        except Exception as err: # pylint: disable=broad-except
            interaction.client.dispatch("error", err, "When asking for a duration for a reminder snooze")
            await interaction.edit_original_response(
                content="An error occured while registering your answer. Please try again later."
            )
