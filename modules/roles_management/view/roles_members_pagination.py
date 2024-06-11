

import discord

from core.bot_classes import Axobot
from core.paginator import Paginator

_MEMBERS_PER_PAGE = 30

class RoleMembersPaginator(Paginator):
    "A paginator for the members of a role."

    def __init__(self, client: Axobot, user: discord.User, role: discord.Role, stop_label: str = "Quit"):
        super().__init__(client, user, stop_label)
        self.role = role

    async def get_page_count(self) -> int:
        if len(self.role.members) == 0:
            return 1
        return (len(self.role.members) + _MEMBERS_PER_PAGE - 1) // _MEMBERS_PER_PAGE

    async def get_page_content(self, interaction, page):
        "Create one page"
        tr_nbr = await self.client._(interaction, "info.info.role-3")
        tr_mbr = await self.client._(interaction, "misc.membres")
        emb = discord.Embed(title=self.role.name, color=self.role.color)
        emb.add_field(name=tr_nbr.capitalize(), value=len(self.role.members), inline=False)
        if len(self.role.members) != 0:
            page_start, page_end = (page - 1) * _MEMBERS_PER_PAGE, min(page * _MEMBERS_PER_PAGE, len(self.role.members))
            for i in range(page_start, page_end, 10):
                column_start, column_end = i, min(i + 10, page_end)
                if column_start == 0 and column_end < 10:
                    field_title = f"{tr_mbr.capitalize()}"
                else:
                    field_title = f"{tr_mbr.capitalize()} {column_start + 1} - {column_end}"
                emb.add_field(
                    name=field_title,
                    value="\n".join(
                        member.mention for member in self.role.members[column_start:column_end]
                    ),
                )
            if (pages_count := await self.get_page_count()) > 1:
                footer = f"{page}/{pages_count}"
                emb.set_footer(text=footer)
        return {
            "embed": emb
        }
