from typing import TYPE_CHECKING, Any, Awaitable, Callable, Self

from discord import (ButtonStyle, Colour, Interaction, SeparatorSpacing,
                     TextStyle, ui)

if TYPE_CHECKING:
    from core.bot_classes import Axobot

_DEFAULT_FRENCH_TEXT = "🇫🇷 French text"
_DEFAULT_ENGLISH_TEXT = "🇬🇧 English text"


class ChangelogView(ui.LayoutView):
    """A view for editing and publishing changelogs."""

    def __init__(self, bot: "Axobot", user_id: int, version: str, on_send: Callable[[Interaction, Self], Awaitable[None]]):
        super().__init__(timeout=60*30)  # 30 minutes timeout
        self.bot = bot
        self.user_id = user_id
        self.on_send = on_send

        self.french_text: str | None = None
        self.english_text: str | None = None

        self.french_textdisplay = ui.TextDisplay(_DEFAULT_FRENCH_TEXT)
        self.english_textdisplay = ui.TextDisplay(_DEFAULT_ENGLISH_TEXT)

        self.edit_french_text = ui.Button(
            label="Edit text", emoji="✏️", style=ButtonStyle.secondary
        )
        self.edit_french_text.callback = self.edit_french_text_callback
        self.edit_english_text = ui.Button(
            label="Edit text", emoji="✏️", style=ButtonStyle.secondary
        )
        self.edit_english_text.callback = self.edit_english_text_callback

        self.send_to_servers = ui.Button(
            label="Send to servers", emoji="📨",
            style=ButtonStyle.success,
            disabled=True
        )
        self.send_to_servers.callback = self.send_callback

        self.add_item(ui.Container(
            ui.TextDisplay(f"# {version} Changelog"),
            ui.Separator(visible=False),
            ui.Section(
                self.french_textdisplay,
                accessory=self.edit_french_text
            ),
            ui.Separator(spacing=SeparatorSpacing.large),
            ui.Section(
                self.english_textdisplay,
                accessory=self.edit_english_text,
            ),
            ui.Separator(spacing=SeparatorSpacing.large, visible=False),
            ui.ActionRow(
                self.send_to_servers,
            ),
            accent_colour=Colour.blurple(),
        ))

    async def interaction_check(self, interaction: Interaction, /):
        return interaction.user.id == self.user_id

    async def on_error(self, interaction: Interaction, error: Exception, item: ui.Item[Any], /):
        self.bot.dispatch("interaction_error", interaction, error)
        return await super().on_error(interaction, error, item)

    async def edit_french_text_callback(self, interaction: Interaction):
        """Button to edit the French changelog text."""
        modal = _ChangelogTextModal(
            language="French", initial_text=self.french_text or "")
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.last_interaction:
            self.french_text = modal.text_input.value
            self.french_textdisplay.content = self.french_text or _DEFAULT_FRENCH_TEXT
            await self._refresh_buttons_states(modal.last_interaction)

    async def edit_english_text_callback(self, interaction: Interaction):
        """Button to edit the English changelog text."""
        modal = _ChangelogTextModal(
            language="English", initial_text=self.english_text or "")
        await interaction.response.send_modal(modal)
        await modal.wait()
        if modal.last_interaction:
            self.english_text = modal.text_input.value
            self.english_textdisplay.content = self.english_text or _DEFAULT_ENGLISH_TEXT
            await self._refresh_buttons_states(modal.last_interaction)

    async def send_callback(self, interaction: Interaction):
        """Button to send the changelog to all servers."""
        self.stop()
        await self._refresh_buttons_states(interaction)
        await self.on_send(interaction, self)

    async def _refresh_buttons_states(self, interaction: Interaction):
        """Refresh the send button's disabled state."""
        self.edit_french_text.disabled = self.is_finished()
        self.edit_english_text.disabled = self.is_finished()
        self.send_to_servers.disabled = self.is_finished() or not (self.french_text or self.english_text)
        await interaction.response.edit_message(view=self)


class _ChangelogTextModal(ui.Modal):
    """A modal for editing changelog text."""

    def __init__(self, language: str, initial_text: str):
        super().__init__(title=f"Edit {language} Changelog Text")
        self.text_input = ui.TextInput(
            label=f"{language} Changelog Text",
            style=TextStyle.paragraph,
            default=initial_text,
            required=False,
            max_length=1500,
        )
        self.add_item(self.text_input)
        self.last_interaction: Interaction | None = None

    async def on_submit(self, interaction: Interaction, /) -> None:
        self.last_interaction = interaction
        return await super().on_submit(interaction)
