from math import ceil

from discord import Color, Embed, User

from core.bot_classes.axobot import Axobot
from core.formatutils import FormatUtils
from core.paginator import Paginator

from .types import TrackedInvite

INVITES_PER_PAGE = 20

class TrackedInvitesPaginator(Paginator):
    "Paginator to list tracked invites for a guild"

    def __init__(self, client: Axobot, user: User, invites: list[TrackedInvite], stop_label: str):
        super().__init__(client, user, stop_label)
        self.invites = sorted(invites, key=lambda invite: invite["last_count"], reverse=True)

    async def get_page_count(self):
        length = len(self.invites)
        if length == 0:
            return 1
        return ceil(length / INVITES_PER_PAGE)

    async def get_page_content(self, interaction, page):
        embed = Embed(
            title=await self.client._(interaction, "invites_tracker.list.title"),
            color=Color.blurple()
        )
        lang = await self.client._(interaction, "_used_locale")
        for invite in self.invites[(page - 1) * INVITES_PER_PAGE : page * INVITES_PER_PAGE]:
            if invite["name"]:
                name = f"{invite['name']} ({invite['invite_id']})"
            else:
                name = invite["invite_id"]
            creation_user = None if not invite['user_id'] else f"<@{invite['user_id']}>"
            creation_date = None if not invite['creation_date'] else f"<t:{invite['creation_date'].timestamp():.0f}>"
            if creation_user and creation_date:
                value = await self.client._(
                    interaction, "invites_tracker.list.field-value.user-and-date", user=creation_user, date=creation_date
                )
            elif creation_user:
                value = await self.client._(
                    interaction, "invites_tracker.list.field-value.user", user=creation_user
                )
            elif creation_date:
                value = await self.client._(
                    interaction, "invites_tracker.list.field-value.date", date=creation_date
                )
            else:
                value = await self.client._(
                    interaction, "invites_tracker.list.field-value.none"
                )
            invites_count = await FormatUtils.format_nbr(invite["last_count"], lang)
            embed.add_field(
                name=await self.client._(interaction, "invites_tracker.list.field-title", name=name, count=invites_count),
                value=value,
                inline=False
            )
        if (pages_count := await self.get_page_count()) > 1:
            footer = f"{page}/{pages_count}"
            embed.set_footer(text=footer)
        return {
            "embed": embed
        }
