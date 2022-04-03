from typing import Any
from discord import ui, ButtonStyle, User, Interaction

from libs.classes import MyContext, Zbot

class Paginator(ui.View):
    "Base class to paginate something"

    def __init__(self, client: Zbot, user: User, stop_label: str="Quit", timeout: int=180):
        super().__init__(timeout=timeout)
        self.client = client
        self.user = user
        self.page = 1
        self.children[2].label = stop_label

    async def send_init(self, ctx: MyContext):
        "Build the first page, before anyone actually click"
        await ctx.send(view=self)

    async def get_page_content(self, interaction: Interaction, page: int) -> dict[str, Any]:
        "Build the page content given the page number and source interaction"
        raise NotImplementedError("get_page_content must be implemented!")

    async def get_page_count(self, interaction: Interaction) -> int:
        "Get total number of available pages"
        raise NotImplementedError("get_page_count must be implemented!")


    async def interaction_check(self, interaction: Interaction) -> bool:
        "Check if the user is actually allowed to press that"
        result = True
        if user := interaction.user:
            result = user == self.user
        if not result:
            err = await self.client._(interaction.user.id, "errors.interaction-forbidden")
            await interaction.response.send_message(err, ephemeral=True)
        return result

    async def _set_page(self, interaction: Interaction, page: int):
        "Set the page number starting from 1"
        count = await self.get_page_count(interaction)
        self.page = min(max(page, 1), count)

    async def _update_contents(self, interaction: Interaction):
        "Update the page content"
        await interaction.response.defer()
        contents = await self.get_page_content(interaction, self.page)
        await self._update_buttons(interaction)
        await interaction.followup.edit_message(
            (await interaction.original_message()).id,
            view=self,
            **contents
        )

    async def _update_buttons(self, interaction: Interaction):
        "Mark buttons as enabled/disabled according to current page and view status"
        count = await self.get_page_count(interaction)
        self.children[0].disabled = (self.page == 1) or self.is_finished()
        self.children[1].disabled = (self.page == 1) or self.is_finished()
        self.children[2].disabled = self.is_finished()
        self.children[3].disabled = (self.page == count) or self.is_finished()
        self.children[4].disabled = (self.page == count) or self.is_finished()

    @ui.button(label='\U000025c0 \U000025c0', style=ButtonStyle.secondary)
    async def _first_element(self, _: ui.Button, interaction: Interaction):
        "Jump to the 1st page"
        await self._set_page(interaction, 1)
        await self._update_contents(interaction)

    @ui.button(label='\U000025c0', style=ButtonStyle.blurple)
    async def _previous_element(self, _: ui.Button, interaction: Interaction):
        "Go to the previous page"
        await self._set_page(interaction, self.page-1)
        await self._update_contents(interaction)

    @ui.button(label='...', style=ButtonStyle.red)
    async def _stop(self, _: ui.Button, interaction: Interaction):
        "Jump to the last page"
        self.stop()
        await self._update_contents(interaction)

    @ui.button(label='\U000025b6', style=ButtonStyle.blurple)
    async def _next_element(self, _: ui.Button, interaction: Interaction):
        "Go to the next page"
        await self._set_page(interaction, self.page+1)
        await self._update_contents(interaction)

    @ui.button(label='\U000025b6 \U000025b6', style=ButtonStyle.secondary)
    async def _last_element(self, _: ui.Button, interaction: Interaction):
        "Jump to the last page"
        await self._set_page(interaction, await self.get_page_count(interaction))
        await self._update_contents(interaction)
