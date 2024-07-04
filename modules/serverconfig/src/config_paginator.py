from math import ceil
from typing import TYPE_CHECKING, Any

import discord

from core.bot_classes import Axobot
from core.paginator import Paginator
from core.serverconfig import options_list as opt_list

from .converters import to_display

if TYPE_CHECKING:
    from modules.serverconfig.serverconfig import ServerConfig

class ServerConfigPaginator(Paginator):
    "Allow user to see a server config and navigate into its pages"

    def __init__(self, client: Axobot, user: discord.User, stop_label: str, guild: discord.Guild, cog: "ServerConfig"):
        super().__init__(client, user, stop_label, timeout=10)
        self.guild = guild
        self.cog = cog
        self.options_list = [option for option, value in opt_list.options.items() if value["is_listed"]]
        self.server_config: dict[str, Any] = {}
        self.items_per_page = 21

    async def send_init(self, ctx: discord.Interaction):
        "Create and send 1st page"
        full_config = await self.client.get_cog("ServerConfig").get_guild_config(self.guild.id, with_defaults=True)
        for option, value in full_config.items():
            if option in opt_list.options and opt_list.options[option]["is_listed"]:
                self.server_config[option] = value
        contents = await self.get_page_content(ctx, 1)
        await self._update_buttons()
        if ctx.response.is_done():
            await ctx.followup.send(**contents, view=self)
        else:
            await ctx.response.send_message(**contents, view=self)

    async def get_page_count(self) -> int:
        length = len(self.server_config)
        if length == 0:
            return 1
        return ceil(length / self.items_per_page)

    async def get_page_content(self, interaction: discord.Interaction, page: int):
        "Create one page"
        page_config_map: dict[str, Any] = {}
        for option in self.options_list[(page - 1) * self.items_per_page : page * self.items_per_page]:
            page_config_map[option] = self.server_config[option]
        max_pages = await self.get_page_count()
        title = await self.client._(interaction, "server.see-title", guild=self.guild.name) + f" ({page}/{max_pages})"
        embed = discord.Embed(
            title=title,
            color=self.cog.embed_color,
        )
        if self.guild.icon:
            embed.set_thumbnail(url=self.guild.icon.with_static_format("png"))
        for option, value in page_config_map.items():
            if (display := await to_display(option, value, self.guild, self.client)) is None:
                display = "Ø"
            elif len(display) > 1024:
                display = display[:1023] + "…"
            embed.add_field(name=option, value=display)
        return {
            "embed": embed,
        }
