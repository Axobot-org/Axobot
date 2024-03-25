from math import ceil
from typing import Any, Optional, Union

from discord import (ButtonStyle, Interaction, Message, NotFound, SelectOption,
                     User, ui)

from libs.bot_classes import Axobot, MyContext


def cut_text(lines: list[str], max_length: int = 1024, max_size=100) -> list[str]:
    "Cut some text into multiple paragraphs"
    result: list[str] = []
    paragraph: list[str] = []
    for line in lines:
        if len(paragraph)+1 > max_size or len("\n".join(paragraph+[line])) > max_length:
            result.append("\n".join(paragraph))
            paragraph = [line]
        else:
            paragraph.append(line)
    if len(paragraph) > 0:
        result.append("\n".join(paragraph))
    return result


class Paginator(ui.View):
    "Base class to paginate something"

    def __init__(self, client: Axobot, user: User, stop_label: str="Quit", timeout: int=180):
        super().__init__(timeout=timeout)
        self.client = client
        self.user = user
        self.page = 1
        self.children[2].label = stop_label

    async def send_init(self, ctx: Union[MyContext, Interaction]):
        "Build the first page, before anyone actually click"
        contents = await self.get_page_content(None, self.page)
        await self._update_buttons()
        if isinstance(ctx, MyContext):
            return await ctx.send(**contents, view=self)
        if ctx.response.is_done():
            return await ctx.followup.send(**contents, view=self)
        return await ctx.response.send_message(**contents, view=self)

    async def get_page_content(self, interaction: Interaction, page: int) -> dict[str, Any]:
        "Build the page content given the page number and source interaction"
        raise NotImplementedError("get_page_content must be implemented!")

    async def get_page_count(self) -> int:
        "Get total number of available pages"
        raise NotImplementedError("get_page_count must be implemented!")


    async def interaction_check(self, interaction: Interaction, /) -> bool:
        "Check if the user is actually allowed to press that"
        result = True
        if user := interaction.user:
            result = user == self.user
        if not result:
            err = await self.client._(interaction.user.id, "errors.interaction-forbidden")
            await interaction.response.send_message(err, ephemeral=True)
        return result

    async def on_error(self, interaction, error, item):
        await self.client.dispatch("error", error, interaction)

    async def disable(self, interaction: Union[Message, Interaction]):
        "Called when the timeout has expired"
        try:
            await self._update_contents(interaction, stopped=True)
        except NotFound:
            pass
        self.stop()

    async def _set_page(self, interaction: Interaction, page: int):
        "Set the page number starting from 1"
        count = await self.get_page_count()
        self.page = min(max(page, 1), count)

    async def _update_contents(self, interaction: Union[Message, Interaction], stopped: bool=None):
        "Update the page content"
        if isinstance(interaction, Interaction):
            await interaction.response.defer()
        await self._update_buttons()
        if isinstance(interaction, Interaction):
            contents = await self.get_page_content(interaction, self.page)
            await interaction.followup.edit_message(
                interaction.message.id,
                view=self,
                **contents
            )
        else:
            await interaction.edit(view=self)

    async def _update_buttons(self, stopped: bool=None):
        "Mark buttons as enabled/disabled according to current page and view status"
        stopped = self.is_finished() if stopped is None else stopped
        count = await self.get_page_count()
        # remove buttons if not required
        if count == 1:
            for child in self.children:
                self.remove_item(child)
            return
        self.children[0].disabled = (self.page == 1) or stopped
        self.children[1].disabled = (self.page == 1) or stopped
        self.children[2].disabled = stopped
        self.children[3].disabled = (self.page == count) or stopped
        self.children[4].disabled = (self.page == count) or stopped

    @ui.button(label='\U000025c0 \U000025c0', style=ButtonStyle.secondary)
    async def _first_element(self, interaction: Interaction, _: ui.Button):
        "Jump to the 1st page"
        await self._set_page(interaction, 1)
        await self._update_contents(interaction)

    @ui.button(label='\U000025c0', style=ButtonStyle.blurple)
    async def _previous_element(self, interaction: Interaction, _: ui.Button):
        "Go to the previous page"
        await self._set_page(interaction, self.page-1)
        await self._update_contents(interaction)

    @ui.button(label='...', style=ButtonStyle.red)
    async def _stop(self, interaction: Interaction, _: ui.Button):
        "Stop the view"
        self.stop()
        await self._update_contents(interaction)

    @ui.button(label='\U000025b6', style=ButtonStyle.blurple)
    async def _next_element(self, interaction: Interaction, _: ui.Button):
        "Go to the next page"
        await self._set_page(interaction, self.page+1)
        await self._update_contents(interaction)

    @ui.button(label='\U000025b6 \U000025b6', style=ButtonStyle.secondary)
    async def _last_element(self, interaction: Interaction, _: ui.Button):
        "Jump to the last page"
        await self._set_page(interaction, await self.get_page_count())
        await self._update_contents(interaction)


class PaginatedSelectView(ui.View):
    "View used to represent a discord Select with potentially more than 25 options"

    def __init__(self, client: Axobot, message: Optional[str], options: list[SelectOption], user: User, placeholder: str,
                 stop_label: str = "Quit", min_values: int = 1, max_values: int = 25, timeout: int = 180):
        super().__init__(timeout=timeout)
        if any(not isinstance(opt.value, str) for opt in options):
            raise ValueError("All options must have a string value")
        self.client = client
        self.message = message
        self.options = options
        self.user = user
        self.placeholder = placeholder
        self.stop_label = stop_label
        self.min_values = min_values
        self.max_values = min(len(self.options), max_values)
        self.page = 1
        # init selector
        self._selector.placeholder = self.placeholder
        self._selector.options = self.options[:25]
        self._selector.min_values = self.min_values
        self._selector.max_values = min(25, self.max_values)
        # remove buttons if not required
        if len(self.options) <= 25:
            for child in self.children[1:]:
                self.remove_item(child)
        # init stop label
        self._stop.label = stop_label

        self._values: set[str] = set()

    @property
    def values(self) -> Union[str, list[str], None]:
        "Return the selected values"
        if len(self._values) == 0:
            return None
        if self.max_values == 1:
            return list(self._values)[0]
        return sorted(self._values)

    async def send_init(self, ctx: MyContext):
        "Build the first page, before anyone actually click"
        await self._update_buttons()
        return await ctx.send(view=self)

    async def interaction_check(self, interaction) -> bool:
        result = True
        if user := interaction.user:
            result = user == self.user
        if not result:
            err = await self.client._(interaction.user.id, "errors.interaction-forbidden")
            await interaction.response.send_message(err, ephemeral=True)
        return result

    async def on_error(self, interaction, error, item):
        await self.client.dispatch("error", error, interaction)

    async def on_timeout(self):
        self._values.clear()

    async def disable(self, interaction: Union[Message, Interaction]):
        "Called when the timeout has expired"
        await self._update_contents(interaction, stopped=True)
        self.stop()

    async def _update_selector(self):
        "Update the selector component"
        options = self.options[(self.page-1)*25:self.page*25]
        for opt in options:
            opt.default = opt.value in self._values
        self._selector.options = options
        if self.max_values > 1:
            options_values = {opt.value for opt in options}
            outside_values = sum(1 for value in self._values if value not in options_values)
            self._selector.max_values = min(len(options), self.max_values - outside_values)

    async def _set_page(self, page: int):
        "Set the page number starting from 1"
        pages_count = ceil(len(self.options) / 25)
        self.page = min(max(page, 1), pages_count)

    async def _update_contents(self, interaction: Union[Message, Interaction], stopped: bool=None):
        "Update the page content"
        if isinstance(interaction, Interaction):
            await interaction.response.defer()
        await self._update_buttons(stopped=stopped)
        await self._update_selector()
        if isinstance(interaction, Interaction):
            await interaction.followup.edit_message(
                interaction.message.id,
                content=self.message,
                view=self
            )
        else:
            await interaction.edit(content=self.message, view=self)

    async def _update_buttons(self, stopped: bool=None):
        "Mark buttons as enabled/disabled according to current page and view status"
        stopped = self.is_finished() if stopped is None else stopped
        pages_count = ceil(len(self.options) / 25)
        self._selector.disabled = stopped
        self._first_element.disabled = (self.page == 1) or pages_count == 1 or stopped
        self._previous_element.disabled = (self.page == 1) or pages_count == 1 or stopped
        self._stop.disabled = stopped
        self._next_element.disabled = (self.page == pages_count) or pages_count == 1 or stopped
        self._last_element.disabled = (self.page == pages_count) or pages_count == 1 or stopped

    @ui.select(placeholder='...', row=0)
    async def _selector(self, interaction: Interaction, selector: ui.Select):
        "The actual selector"
        # remove values that have been unselected
        selector_all_values = {opt.value for opt in selector.options}
        self._values = {value
                        for value in self._values
                        if value in selector_all_values and value not in selector.values}
        # add values that have been selected
        self._values |= set(selector.values)
        # disable the selector if the max number of values has been reached
        #  or if buttons are not required
        if self.max_values == 1 or len(self.options) <= 25:
            await self.disable(interaction)
        else:
            await self._update_contents(interaction)

    @ui.button(label='\U000025c0 \U000025c0', style=ButtonStyle.secondary, row=1)
    async def _first_element(self, interaction: Interaction, _: ui.Button):
        "Jump to the 1st page"
        await self._set_page(1)
        await self._update_contents(interaction)

    @ui.button(label='\U000025c0', style=ButtonStyle.blurple, row=1)
    async def _previous_element(self, interaction: Interaction, _: ui.Button):
        "Go to the previous page"
        await self._set_page(self.page-1)
        await self._update_contents(interaction)

    @ui.button(label='...', style=ButtonStyle.red, row=1)
    async def _stop(self, interaction: Interaction, _: ui.Button):
        "Stop the view"
        await self.disable(interaction)

    @ui.button(label='\U000025b6', style=ButtonStyle.blurple, row=1)
    async def _next_element(self, interaction: Interaction, _: ui.Button):
        "Go to the next page"
        await self._set_page(self.page+1)
        await self._update_contents(interaction)

    @ui.button(label='\U000025b6 \U000025b6', style=ButtonStyle.secondary, row=1)
    async def _last_element(self, interaction: Interaction, _: ui.Button):
        "Jump to the last page"
        await self._set_page(ceil(len(self.options) / 25))
        await self._update_contents(interaction)
