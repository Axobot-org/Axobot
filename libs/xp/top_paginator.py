
from math import ceil
from typing import Literal, Optional, TypedDict

import discord
from asyncache import cached
from cachetools import Cache

from libs.bot_classes import Axobot
from libs.paginator import Paginator

LeaderboardScope = Literal["global", "server"]

class TopPaginator(Paginator):
    "Paginator used to display the leaderboard"

    def __init__(self, client: Axobot, user: discord.User, guild: discord.Guild, scope: LeaderboardScope,
                    start_page: int, stop_label: str = "Quit", timeout: int = 180):
        super().__init__(client, user, stop_label, timeout)
        class Position(TypedDict):
            "A position in the leaderboard"
            username: str
            user_id: int
            level: int
            xp: int
            xp_label: str
        class RawData(TypedDict):
            "Raw data for the leaderboard"
            xp: int
            user_id: int

        self.guild = guild
        self.scope = scope
        self.page = start_page
        self.raw_data: list[Optional[RawData]] = []
        self.positions: list[Position] = []
        self.cog = client.get_cog("Xp")
        self.used_system: str = None
        self.max_page: int = 1

    def convert_average(self, nbr: int) -> str:
        "Convert a large number to its short version (ex: 1000000 -> 1M)"
        res = str(nbr)
        for power, symb in ((9,'G'), (6,'M'), (3,'k')):
            if nbr >= 10**power:
                res = str(round(nbr/10**power, 1)) + symb
                break
        return res

    async def get_page_count(self):
        return self.max_page

    @cached(Cache(maxsize=1)) # cache as long as possible, as it should never change for one same Paginator
    async def get_user_rank(self):
        "Get the embed field content corresponding to the user's rank"
        pos = [(i+1, pos) for i, pos in enumerate(self.positions) if pos is not None and pos["user_id"] == self.user.id]
        field_name = "__" + await self.client._(self.guild, "xp.top-your") + "__"
        if len(pos) == 0:
            # fetch from raw data
            pos = [(i+1, pos) for i, pos in enumerate(self.raw_data) if pos is not None and pos["user_id"] == self.user.id]
            if len(pos) == 0:
                value = await self.client._(self.guild, "xp.1-no-xp")
            else:
                rank = pos[0][0]
                level = await self.cog.calc_level(pos[0][1]["xp"], self.used_system)
                xp_label = self.convert_average(pos[0][1]["xp"])
                value = f"**#{rank} |** `lvl {level[0]}` **|** `xp {xp_label}`"
        else:
            rank, data = pos[0]
            value = f"**#{rank} |** `lvl {data['level']}` **|** `xp {data['xp_label']}`"
        return {
            "name": field_name,
            "value": value,
        }

    async def fetch_data(self):
        "Fetch the required data to display the leaderboard"
        self.used_system = await self.client.get_config(self.guild.id, 'xp_type')
        if self.used_system == "global":
            if self.scope == 'global':
                if len(self.cog.cache["global"]) == 0:
                    await self.cog.db_load_cache(None)
                self.raw_data = [
                    {"user_id": user_id, "xp": data[1]}
                    for user_id, data in self.cog.cache['global'].items()
                ]
            else:
                self.raw_data = [
                    {"user_id": int(row["userID"]), "xp": row["xp"]}
                    for row in await self.cog.db_get_top(10000, guild=self.guild)
                ]
        else:
            if not self.guild.id in self.cog.cache.keys():
                await self.cog.db_load_cache(self.guild.id)
            self.raw_data = [
                    {"user_id": user_id, "xp": data[1]}
                    for user_id, data in self.cog.cache[self.guild.id].items()
                ]
        self.raw_data.sort(key=lambda x: x["xp"], reverse=True)
        self.max_page = ceil(len(self.raw_data)/20)
        self.positions = [None for _ in range(len(self.raw_data))]

    async def _load_page(self):
        "Load the user data for the current page"
        i = (self.page-1)*20
        for data in self.raw_data[(self.page-1)*20:self.page*20]:
            if self.positions[i] is not None:
                i += 1
                continue
            user = self.client.get_user(data["user_id"])
            if user is None:
                try:
                    user = await self.client.fetch_user(data["user_id"])
                except discord.NotFound:
                    user = await self.client._(self.guild, "xp.del-user")
            if isinstance(user, discord.User):
                user_name = discord.utils.escape_markdown(user.display_name)
                if len(user_name) > 18:
                    user_name = user_name[:15]+'...'
                if user == self.user:
                    user_name = "__" + user_name + "__"
            else:
                user_name = user
            level = await self.cog.calc_level(data["xp"], self.used_system)
            xp = self.convert_average(data["xp"])
            self.positions[i] = {
                "username": user_name,
                "user_id": data["user_id"],
                "level": level[0],
                "xp": data["xp"],
                "xp_label": xp
            }
            i += 1

    async def get_page_content(self, _interaction, page: int):
        "Get the content of a page"
        if page > self.max_page:
            page = self.page = self.max_page
        await self._load_page()
        txt = []
        i = (page-1)*20
        for row in self.positions[(page-1)*20:page*20]:
            i += 1
            username = row['username']
            lvl = row['level']
            xp = row['xp_label']
            txt.append(f"{i} • **{username} |** `lvl {lvl}` **|** `xp {xp}`")
        # title
        if self.scope == "server" or self.used_system != "global":
            embed_title = await self.client._(self.guild, "xp.top-title-2")
        else:
            embed_title = await self.client._(self.guild, "xp.top-title-1")
        # field name
        field_title = await self.client._(self.guild, "xp.top-name", min=(page-1)*20+1, max=i, page=page, total=self.max_page)
        emb = discord.Embed(title=embed_title, color=self.cog.embed_color)
        emb.add_field(name=field_title, value="\n".join(txt), inline=False)
        # user rank
        emb.add_field(**await self.get_user_rank())
        # embed footer with user info
        emb.set_footer(text=self.user, icon_url=self.user.display_avatar)
        return {
            "embed": emb
        }
