import random
from typing import Any, Callable

import discord


class SelectView(discord.ui.View):
    "Used to ask what kind of ticket a user wants to open"
    def __init__(self, guild_id: int, topics: list[dict[str, Any]]):
        super().__init__(timeout=None)
        options = self.build_options(topics)
        custom_id = f"{guild_id}-tickets-{random.randint(1, 100):03}"
        self.select = discord.ui.Select(placeholder="Chose a topic", options=options, custom_id=custom_id)
        self.add_item(self.select)

    def build_options(self, topics: list[dict[str, Any]]):
        "Compute Select options from topics list"
        res = []
        for topic in topics:
            res.append(discord.SelectOption(label=topic['topic'], value=topic['id'], emoji=topic['topic_emoji']))
        return res

class SendHintText(discord.ui.View):
    "Used to send a hint and make sure the user actually needs help"
    def __init__(self, user_id: int, label_confirm: str, label_cancel: str, text_cancel: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.confirmed: bool | None = None
        self.interaction: discord.Interaction | None = None
        confirm_btn = discord.ui.Button(label=label_confirm, style=discord.ButtonStyle.green)
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        self.text_cancel = text_cancel
        cancel_btn = discord.ui.Button(label=label_cancel, style=discord.ButtonStyle.red)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    # pylint: disable=arguments-differ
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id

    async def confirm(self, interaction: discord.Interaction):
        "When user clicks on the confirm button"
        self.confirmed = True
        self.interaction = interaction
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        "When user clicks on the cancel button"
        await interaction.response.defer()
        self.confirmed = False
        self.stop()
        await self.disable(interaction)
        await interaction.followup.send(self.text_cancel, ephemeral=True)

    async def disable(self, src: discord.Interaction | discord.Message):
        "When the view timeouts or is disabled"
        for child in self.children:
            child.disabled = True
        if isinstance(src, discord.Interaction):
            await src.edit_original_response(view=self)
        else:
            await src.edit(content=src.content, embeds=src.embeds, view=self)
        self.stop()

class AskTitleModal(discord.ui.Modal):
    "Ask a user the name of their ticket"
    name = discord.ui.TextInput(label="", placeholder=None, style=discord.TextStyle.short, max_length=100)

    def __init__(self, guild_id: int, topic: dict, title: str, input_label: str, input_placeholder: str,
                 callback: Callable[[discord.Interaction, dict, str], Any]):
        super().__init__(title=title, timeout=600)
        self.guild_id = guild_id
        self.topic = topic
        self.callback = callback
        self.name.label = input_label
        self.name.placeholder = input_placeholder

    # pylint: disable=arguments-differ
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await self.callback(interaction, self.topic, self.name.value.strip())
        except Exception as err: # pylint: disable=broad-except
            interaction.client.dispatch("error", err, f"When opening a ticket in guild {self.guild_id}")
            await interaction.edit_original_response(content="An error occured while opening your ticket. Please try again later.")

class AskTopicSelect(discord.ui.View):
    "Ask a user what topic they want to edit/delete"
    def __init__(self, user_id: int, topics: list[dict[str, Any]], placeholder: str, max_values: int):
        super().__init__(timeout=90)
        self.user_id = user_id
        options = self.build_options(topics)
        self.select = discord.ui.Select(
            placeholder=placeholder, min_values=1, max_values=min(max_values, len(options)), options=options
        )
        self.select.callback = self.callback
        self.add_item(self.select)
        self.topics: list[str] | None = None

    # pylint: disable=arguments-differ
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id

    def build_options(self, topics: list[dict[str, Any]]) -> list[discord.SelectOption]:
        "Build the options list for Discord"
        res = []
        for topic in topics:
            res.append(discord.SelectOption(label=topic['topic'], value=topic['id'], emoji=topic['topic_emoji']))
        return res

    async def callback(self, interaction: discord.Interaction):
        "Called when the dropdown menu has been validated by the user"
        self.topics = self.select.values
        await interaction.response.defer()
        self.select.disabled = True
        await interaction.edit_original_response(view=self)
        self.stop()

    async def disable(self, src: discord.Interaction | discord.Message):
        "When the view timeouts or is disabled"
        for child in self.children:
            child.disabled = True
        if isinstance(src, discord.Interaction):
            await src.edit_original_response(view=self)
        else:
            await src.edit(content=src.content, embeds=src.embeds, view=self)
        self.stop()
