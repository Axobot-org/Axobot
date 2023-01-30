from math import ceil
from typing import TYPE_CHECKING, Union

import discord

from libs.bot_classes import MyContext, Axobot
from libs.paginator import Paginator

from . import options_list as opt_list

if TYPE_CHECKING:
    from fcts.servers import Servers

class ServerConfigPaginator(Paginator):
    "Allow user to see a server config and navigate into its pages"

    def __init__(self, client: Axobot, user: discord.User, stop_label: str, guild: discord.Guild, cog: "Servers"):
        super().__init__(client, user, stop_label, timeout=120)
        self.guild = guild
        self.cog = cog
        self.server_config: dict[str, Union[str, int, float]] = {}
        self.items_per_page = 21

    async def send_init(self, ctx: MyContext):
        "Create and send 1st page"
        if config := await self.cog.get_server([], criters=["ID="+str(self.guild.id)]):
            full_config = config[0]
        else:
            full_config = opt_list.default_values
        for option, value in full_config.items():
            if option in self.cog.options_list:
                self.server_config[option] = value
        contents = await self.get_page_content(ctx, 1)
        await self._update_buttons(None)
        await ctx.send(**contents, view=self)

    async def get_page_count(self, _: discord.Interaction) -> int:
        length = len(self.server_config)
        if length == 0:
            return 1
        return ceil(length / self.items_per_page)

    async def get_page_content(self, interaction: discord.Interaction, page: int):
        "Create one page"
        page_config_map: dict[str, Union[str, int, float]] = {}
        for option in self.cog.options_list[(page - 1) * self.items_per_page : page * self.items_per_page]:
            page_config_map[option] = self.server_config[option]
        max_pages = await self.get_page_count(interaction)
        title = await self.client._(interaction, "server.see-title", guild=self.guild.name) + f" ({page}/{max_pages})"
        embed = discord.Embed(
            title=title,
            color=self.cog.embed_color,
        )
        if self.guild.icon:
            embed.set_thumbnail(url=self.guild.icon.with_static_format('png'))
        replace_mentions = interaction.guild.id != self.guild.id
        for option, value in page_config_map.items():
            #if i not in self.optionsList:
            #    continue
            if option == "nicknames_history" and value is None:
                r = len(self.guild.members) < self.cog.max_members_for_nicknames
            elif option in opt_list.roles_options:
                r = await self.cog.form_roles(self.guild, value, replace_mentions)
                r = ", ".join(r)
            elif option in opt_list.bool_options:
                r = str(await self.cog.form_bool(value))
            elif option in opt_list.textchannels_options:
                r = await self.cog.form_textchan(self.guild, value, replace_mentions)
                r = ", ".join(r)
            elif option in opt_list.category_options:
                r = await self.cog.form_category(self.guild, value, replace_mentions)
                r = ', '.join(r)
            elif option in opt_list.text_options:
                r = value if len(value) < 500 else value[:500]+"..."
            elif option in opt_list.numb_options:
                r = str(value)
            elif option in opt_list.voicechannels_options:
                r = await self.cog.form_vocal(self.guild, value)
                r = ", ".join(r)
            elif option == "language":
                r = await self.cog.form_lang(value)
            elif option in opt_list.prefix_options:
                r = await self.cog.form_prefix(value)
            elif option in opt_list.raid_options:
                r = await self.cog.form_raid(value)
            elif option in opt_list.emoji_option:
                r = ", ".join(await self.cog.form_emoji(value, option))
            elif option in opt_list.xp_type_options:
                r = await self.cog.form_xp_type(value)
            elif option in opt_list.color_options:
                r = await self.cog.form_color(option, value)
            elif option in opt_list.xp_rate_option:
                r = await self.cog.form_xp_rate(option, value)
            elif option in opt_list.levelup_channel_option:
                r = await self.cog.form_levelup_chan(self.guild, value, replace_mentions)
            elif option in opt_list.ttt_display_option:
                r = await self.cog.form_tttdisplay(value)
            else:
                continue
            if len(str(r)) == 0:
                r = "Ø"
            embed.add_field(name=option, value=r)
        return {
            "embed": embed,
        }