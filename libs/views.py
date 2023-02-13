from typing import Callable, Optional, Union

import discord

from libs.bot_classes import Axobot


class ConfirmView(discord.ui.View):
    "A simple view used to confirm an action"

    def __init__(self, bot: Axobot, ctx, validation: Callable[[discord.Interaction], bool], ephemeral: bool=True,
            timeout: int=60, send_confirmation: bool=True):
        super().__init__(timeout=timeout)
        self.value: Optional[bool] = None
        self.bot = bot
        self.ctx = ctx
        self.validation = validation
        self.ephemeral = ephemeral
        self.send_confirmation = send_confirmation

    async def init(self):
        "Initialize buttons with translations"
        confirm_label = await self.bot._(self.ctx, "misc.btn.confirm.label")
        confirm_btn = discord.ui.Button(label=confirm_label, style=discord.ButtonStyle.green)
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        cancel_label = await self.bot._(self.ctx, "misc.btn.cancel.label")
        cancel_btn = discord.ui.Button(label=cancel_label, style=discord.ButtonStyle.grey)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def confirm(self, interaction: discord.Interaction):
        "Confirm the action when clicking"
        if not self.validation(interaction):
            return
        if self.send_confirmation:
            await interaction.response.send_message(await self.bot._(self.ctx, "misc.btn.confirm.answer"), ephemeral=self.ephemeral)
        self.value = True
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        "Cancel the action when clicking"
        if not self.validation(interaction):
            return
        await interaction.response.send_message(await self.bot._(self.ctx, "misc.btn.cancel.answer"), ephemeral=self.ephemeral)
        self.value = False
        self.stop()

    async def disable(self, interaction: Union[discord.Message, discord.Interaction]):
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

class DeleteView(discord.ui.View):
    "A simple view used to delete a bot message after reading it"

    def __init__(self, delete_text: str, validation: Callable[[discord.Interaction], bool], \
            timeout: int=60):
        super().__init__(timeout=timeout)
        self.validation = validation
        delete_btn = discord.ui.Button(label=delete_text, style=discord.ButtonStyle.red, emoji='🗑')
        delete_btn.callback = self.delete
        self.add_item(delete_btn)

    async def delete(self, interaction: discord.Interaction):
        "Delete the message when clicking"
        if not self.validation(interaction):
            return
        await interaction.message.delete(delay=0)
        self.stop()
