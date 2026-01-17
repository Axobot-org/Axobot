import discord
from discord import ui
from typing_extensions import Self

from core.bot_classes import Axobot
from modules.cases.cases import Case


class AddCaseView(ui.View):
    """View to add an audit log entry to the user cases"""

    def __init__(self, *, log_entry: discord.AuditLogEntry, bot: Axobot, timeout: float = 3600):
        super().__init__(timeout=timeout)
        self.log_entry = log_entry
        self.bot = bot
        self.message: discord.Message | None = None
        if self.log_entry.target is None or not isinstance(self.log_entry.target, discord.User):
            raise ValueError("Log entry target must be a User")
        self.target_id = self.log_entry.target.id
        if self.log_entry.action == discord.AuditLogAction.ban:
            self.case_type = "ban"
        elif self.log_entry.action == discord.AuditLogAction.unban:
            self.case_type = "unban"
        elif self.log_entry.action == discord.AuditLogAction.kick:
            self.case_type = "kick"
        else:
            raise ValueError("Log entry action must be ban, unban, or kick")

    @ui.button(label="Add to the user cases", style=discord.ButtonStyle.blurple)
    async def _add_case_btn(self, interaction: discord.Interaction, _button: ui.Button[Self]):
        """Add the audit log entry to the user cases on click"""
        # Only members with Moderate Members permission can use it
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("You need the 'Moderate Members' permission to do that.", ephemeral=True)
            return

        mod_id = self.log_entry.user.id if self.log_entry.user else interaction.user.id
        reason = self.log_entry.reason if self.log_entry.reason else ""

        # Insert case via Cases cog
        cases_cog = self.bot.get_cog("Cases")
        if cases_cog is None:
            await interaction.response.send_message("Cases system is unavailable.", ephemeral=True)
            return
        try:
              # type: ignore
            case = Case(
                bot=self.bot,
                guild_id=self.log_entry.guild.id,
                user_id=self.target_id,
                case_type=self.case_type,
                mod_id=mod_id,
                reason=reason,
                date=self.bot.utcnow(),
            )
            if await cases_cog.db_add_case(case):
                await interaction.response.send_message(f"{self.case_type.capitalize()} recorded in user cases.", ephemeral=True)
            if self.message:
                await self.disable(self.message)
            self.stop()
        except Exception as err:  # pylint: disable=broad-except
            self.bot.dispatch("error", err, f"Adding {self.case_type} case from serverlogs")
            if not interaction.response.is_done():
                await interaction.response.send_message("An error occurred while adding the case.", ephemeral=True)

    async def disable(self, message: discord.Message):
        """Called when the timeout has expired"""
        self._add_case_btn.disabled = True
        await message.edit(view=self)

    async def on_timeout(self):
        try:
            if self.message:
                await self.message.edit(view=None)
        except Exception as err:  # pylint: disable=broad-except
            self.bot.dispatch("error", err, "AddCaseView timeout edit")
