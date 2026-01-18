import datetime
import json
import logging
import time
from collections import defaultdict
from typing import AsyncGenerator, Literal

import discord
from discord import app_commands
from discord.ext import commands, tasks

from core.bot_classes import SUPPORT_GUILD_ID, Axobot
from core.checks.checks import database_connected
from core.formatutils import FormatUtils

from .data import EventData, EventRewardRole, EventType
from .subcogs import AbstractSubcog, ChristmasSubcog


class BotEvents(commands.Cog):
    "Cog related to special bot events (like Halloween and Christmas)"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_events"
        self.log = logging.getLogger("bot.event")

        self.current_event: EventType | None = None
        self.current_event_data: EventData = {}
        self.current_event_id: str | None = None

        self.coming_event: EventType | None = None
        self.coming_event_data: EventData = {}
        self.coming_event_id: str | None = None
        self.update_current_event()

        self._subcog: AbstractSubcog = ChristmasSubcog(
            self.bot, self.current_event, self.current_event_data, self.current_event_id)
        self.min_delay_between_ttt_wins = 30 # seconds between 2 tictactoe wins
        self.last_ttt_win: dict[int, int] = defaultdict(int) # map of user_id -> timestamp

    @property
    def subcog(self) -> AbstractSubcog:
        "Return the subcog populated with the current event data"
        if self._subcog.current_event != self.current_event or self._subcog.current_event_data != self.current_event_data:
            self.log.debug("Updating subcog with new data")
            self._subcog = ChristmasSubcog(self.bot, self.current_event, self.current_event_data, self.current_event_id)
        return self._subcog

    async def cog_load(self):
        if self.bot.internal_loop_enabled:
            self._update_event_loop.start() # pylint: disable=no-member

    async def cog_unload(self):
        # pylint: disable=no-member
        if self._update_event_loop.is_running():
            self._update_event_loop.cancel()

    def reset(self):
        "Reset current and coming events"
        self.current_event = None
        self.current_event_data = {}
        self.current_event_id = None
        self.coming_event = None
        self.coming_event_data = {}
        self.coming_event_id = None

    def update_current_event(self):
        "Update class attributes with the new/incoming bot events if needed"
        now = self.bot.utcnow()
        with open("events-list.json", 'r', encoding="utf-8") as file:
            events = json.load(file)
        self.reset()
        for ev_id, ev_data in events.items():
            ev_data["begin"] = datetime.datetime.strptime(
                ev_data["begin"], "%Y-%m-%d").replace(tzinfo=datetime.UTC)
            ev_data["end"] = datetime.datetime.strptime(
                ev_data["end"], "%Y-%m-%d").replace(tzinfo=datetime.UTC)

            if ev_data["begin"] <= now < ev_data["end"]:
                self.current_event = ev_data["type"]
                self.current_event_data = ev_data
                self.current_event_id = ev_id
                self.log.info("Current bot event: %s", ev_id)
                break
            if ev_data["begin"] - datetime.timedelta(days=6) <= now < ev_data["begin"]:
                self.coming_event = ev_data["type"]
                self.coming_event_data = ev_data
                self.coming_event_id = ev_id
                self.log.info("Incoming bot event: %s", ev_id)

    async def get_specific_objectives(self, reward_type: Literal["rankcard", "role", "custom"]):
        "Get all objectives matching a certain reward type"
        if self.current_event_id is None:
            return []
        return [
            objective
            for objective in self.current_event_data["objectives"]
            if objective["reward_type"] == reward_type
        ]

    @tasks.loop(time=[
        datetime.time(hour=0,  tzinfo=datetime.UTC),
        datetime.time(hour=12, tzinfo=datetime.UTC),
    ])
    async def _update_event_loop(self):
        "Refresh the current bot event every 12h"
        self.update_current_event()
        event = self.bot.get_cog("BotEvents").current_event
        emb = discord.Embed(
            description=f"**Bot event** updated (current event is {event})",
            color=1406147, timestamp=self.bot.utcnow()
        )
        emb.set_author(name=self.bot.user, icon_url=self.bot.display_avatar)
        await self.bot.send_embed(emb, url="loop")

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        "Add a random reaction to specific messages if an event is active"
        if self.bot.zombie_mode or msg.author.bot:
            # don't react if zombie mode is enabled or of it's a bot
            return
        if msg.guild is not None and not msg.channel.permissions_for(msg.guild.me).add_reactions:
            # don't react if we don't have the required permission
            return
        if self.current_event:
            await self.subcog.on_message(msg)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        "Give points to the user if they reacted to a message with the right emoji"
        if self.bot.zombie_mode:
            return
        if self.current_event:
            await self.subcog.on_raw_reaction_add(payload)

    @commands.Cog.listener()
    async def on_tictactoe_win(self, interaction: discord.Interaction):
        "Grant points to the user if they won a game of tictactoe"
        if not self.current_event:
            return
        now = time.time()
        # limit to 1 win per minute
        if self.last_ttt_win[interaction.user.id] + self.min_delay_between_ttt_wins > now:
            return
        self.last_ttt_win[interaction.user.id] = now
        points = 3
        user = interaction.user
        # send win reward embed
        emb = discord.Embed(
            title=await self.bot._(interaction, "bot_events.tictactoe.won.title"),
            description=await self.bot._(interaction, "bot_events.tictactoe.won.desc", points=points),
            color=self.current_event_data["color"],
        )
        emb.set_author(name=user.global_name, icon_url=user.display_avatar)
        await interaction.followup.send(embed=emb)
        # send card unlocked notif
        await self.check_and_send_card_unlocked_notif(interaction, user)
        # give points
        await self.db_add_user_points(user.id, points)

    @commands.Cog.listener()
    async def on_tictactoe_lose(self, interaction: discord.Interaction):
        "Grant points to the user if they lost a game of tictactoe"
        if not self.current_event:
            return
        user = interaction.user
        # check if user points is high enough to add some difficulty (ie. remove points on loss)
        if not self.current_event_data["objectives"]:
            return
        user_points = await self.db_get_user_points(user.id)
        first_cap = self.current_event_data["objectives"][0]["points"]
        last_cap = self.current_event_data["objectives"][-1]["points"]
        if user_points is None or user_points < first_cap * 1.1:
            return
        if first_cap == last_cap or user_points < last_cap * 1.1:
            # remove 3 points if user has more than 110% of the first objective
            points = -3
        else:
            # remove 5 points if user has more than 110% of the last objective
            points = -5
        # send loss reward embed
        emb = discord.Embed(
            title=await self.bot._(interaction, "bot_events.tictactoe.lost.title"),
            description=await self.bot._(interaction, "bot_events.tictactoe.lost.desc", points=-points),
            color=self.current_event_data["color"],
        )
        emb.set_author(name=user.global_name, icon_url=user.display_avatar)
        await interaction.followup.send(embed=emb)
        # remove points
        await self.db_add_user_points(user.id, points)

    events_main = app_commands.Group(
        name="event",
        description="Participate in bot special events!",
    )

    @events_main.command(name="info")
    @app_commands.check(database_connected)
    async def event_info(self, interaction: discord.Interaction):
        """Get info about the current event"""
        await interaction.response.defer()
        current_event = self.current_event_id
        lang = await self.subcog.get_event_language(interaction)
        events_desc = self.subcog.translations_data[lang]["events_desc"]

        if current_event in events_desc:
            event_desc = events_desc[current_event]
            # Title
            try:
                title = self.subcog.translations_data[lang]["events_title"][current_event]
            except KeyError:
                title = self.current_event
            # Begin/End dates
            begin = f"<t:{self.current_event_data['begin'].timestamp():.0f}>"
            end = f"<t:{self.current_event_data['end'].timestamp():.0f}>"
            emb = discord.Embed(title=title, description=event_desc, color=self.current_event_data["color"])
            if self.current_event_data["icon"]:
                emb.set_image(url=self.current_event_data["icon"])
            emb.add_field(
                name=(await self.bot._(interaction, "misc.beginning")).capitalize(),
                value=begin
            )
            emb.add_field(
                name=(await self.bot._(interaction, "misc.end")).capitalize(),
                value=end
            )
            # Prices to win
            prices_translations = self.subcog.translations_data[lang]["events_prices"]
            if current_event in prices_translations:
                emb.add_field(
                    name=await self.bot._(interaction, "bot_events.events-price-title"),
                    value=await self.get_info_prices_field(interaction),
                    inline=False
                )
            await interaction.followup.send(embed=emb)
        elif self.coming_event_data:
            date = f"<t:{self.coming_event_data['begin'].timestamp():.0f}>"
            await interaction.followup.send(await self.bot._(interaction, "bot_events.soon", date=date))
        else:
            await interaction.followup.send(await self.bot._(interaction, "bot_events.nothing-desc"))
            if current_event:
                self.bot.dispatch("error", ValueError(f"'{current_event}' has no event description"), interaction)

    async def get_info_prices_field(self, interaction: discord.Interaction):
        "Get the prices field text for the current event"
        lang = await self.subcog.get_event_language(interaction)
        prices_translations = self.subcog.translations_data[lang]["events_prices"]
        if self.current_event_id not in prices_translations:
            return await self.bot._(interaction, "bot_events.nothing-desc")
        points = await self.bot._(interaction, "bot_events.points")
        if lang == "fr":
            points += " "
        prices: list[str] = []
        for required_points, description in prices_translations[self.current_event_id].items():
            related_objective = [
                objective
                for objective in self.current_event_data["objectives"]
                if str(objective["points"]) == required_points
            ]
            if related_objective and (min_date := related_objective[0].get("min_date")):
                parsed_date = datetime.datetime.strptime(min_date, "%Y-%m-%d").replace(tzinfo=datetime.UTC)
                format_date = await FormatUtils.date(parsed_date, hour=False, seconds=False)
                description += " (" + await self.bot._(interaction, "bot_events.available-starting", date=format_date) + ")"
            prices.append(f"- **{required_points} {points}:** {description}")
        return "\n".join(prices)

    @events_main.command(name="profile")
    @app_commands.checks.cooldown(4, 10)
    @app_commands.check(database_connected)
    async def event_profile(self, interaction: discord.Interaction, user: discord.User | None = None):
        """Take a look at your progress in the event and your global ranking
        Event points are reset after each event"""
        if self.current_event is None and self.coming_event_data:
            date = f"<t:{self.coming_event_data['begin'].timestamp():.0f}>"
            await interaction.response.send_message(await self.bot._(interaction, "bot_events.soon", date=date))
            return
        resolved_user = user or interaction.user
        await interaction.response.defer()
        await self.subcog.profile_cmd(interaction, resolved_user)

    @events_main.command(name="collect")
    @app_commands.checks.cooldown(2, 60)
    @app_commands.check(database_connected)
    async def event_collect(self, interaction: discord.Interaction):
        "Get some event points every hour"
        if self.current_event is None and self.coming_event_data:
            date = f"<t:{self.coming_event_data['begin'].timestamp():.0f}>"
            await interaction.response.send_message(await self.bot._(interaction, "bot_events.soon", date=date))
            return
        await interaction.response.defer()
        await self.subcog.collect_cmd(interaction)

    async def get_user_unlockable_rankcards(self, user: discord.User, points: int | None=None) -> AsyncGenerator[str, None]:
        "Get a list of event rank cards that the user can unlock"
        if (users_cog := self.bot.get_cog("Users")) is None:
            return
        if self.current_event is None or len(rewards := await self.get_specific_objectives("rankcard")) == 0:
            return
        cards = await users_cog.get_rankcards(user)
        if points is None:
            points = await self.subcog.db_get_event_rank(user.id)
            points = 0 if (points is None) else points["points"]
        for reward in rewards:
            if reward["rank_card"] not in cards and points >= reward["points"]:
                if self._check_reward_date(reward.get("min_date")):
                    continue
                yield reward["rank_card"]

    async def check_and_send_card_unlocked_notif(
            self,
            interaction: discord.Interaction | discord.TextChannel,
            user: discord.User | int
        ):
        "Check if the user meets the requirements to unlock the event rank card, and send a notification if so"
        if isinstance(user, int):
            user = self.bot.get_user(user)
            if user is None:
                return
        cards = [card async for card in self.get_user_unlockable_rankcards(user)]
        if cards:
            title = await self.bot._(interaction, "bot_events.rankcard-unlocked.title")
            profile_card_cmd = await self.bot.get_command_mention("profile card")
            desc = await self.bot._(interaction, "bot_events.rankcard-unlocked.desc",
                                    cards=", ".join(cards),
                                    profile_card_cmd=profile_card_cmd,
                                    count=len(cards)
                                    )
            emb = discord.Embed(title=title, description=desc, color=discord.Color.brand_green())
            emb.set_author(name=user.global_name, icon_url=user.display_avatar)
            if isinstance(interaction, discord.Interaction):
                await interaction.followup.send(embed=emb)
            else:
                try:
                    await interaction.send(embed=emb)
                except discord.Forbidden:
                    pass

    async def reload_event_rankcard(self, user: discord.User | int, points: int | None = None):
        """Grant the current event rank card to the provided user, if they have enough points
        'points' argument can be provided to avoid re-fetching the database"""
        if (users_cog := self.bot.get_cog("Users")) is None:
            return
        if self.current_event is None:
            return
        if isinstance(user, int):
            user = self.bot.get_user(user)
            if user is None:
                return
        async for card in self.get_user_unlockable_rankcards(user, points):
            await users_cog.set_rankcard(user, card, True)
            # send internal log
            embed = discord.Embed(
                description=f"{user} ({user.id}) has been granted the rank card **{card}**",
                color=discord.Color.brand_green()
            )
            await self.bot.send_embed(embed)

    async def reload_event_special_role(self, user: discord.User | int, points: int | None = None):
        """Grant the current event special role to the provided user, if they have enough points
        'points' argument can be provided to avoid re-fetching the database"""
        if self.current_event is None or len(rewards := await self.get_specific_objectives("role")) == 0:
            return
        rewards: list[EventRewardRole]
        if (support_guild := self.bot.get_guild(SUPPORT_GUILD_ID.id)) is None:
            return
        user_id = user if isinstance(user, int) else user.id
        if (member := support_guild.get_member(user_id)) is None:
            return
        if points is None:
            points = await self.subcog.db_get_event_rank(user_id)
            points = 0 if (points is None) else points["points"]
        for reward in rewards:
            if points >= reward["points"]:
                if self._check_reward_date(reward.get("min_date")):
                    continue
                await member.add_roles(discord.Object(reward["role_id"]))

    def _check_reward_date(self, reward_date: str | None):
        "Check if the minimal reward date is in the future"
        if reward_date is None:
            return False
        parsed_date = datetime.datetime.strptime(reward_date, "%Y-%m-%d").replace(tzinfo=datetime.UTC)
        return self.bot.utcnow() < parsed_date

    async def db_get_user_points(self, user_id: int) -> int | None:
        "Get the user's event points"
        if not self.bot.database_online or self.bot.current_event is None:
            return None
        query = "SELECT `points` FROM `event_points` WHERE `user_id` = %s AND `beta` = %s;"
        async with self.bot.db_main.read(query, (user_id, self.bot.beta), fetchone=True) as query_result:
            if query_result:
                return query_result["points"]
        return None

    async def db_add_user_points(self, user_id: int, points: int):
        "Add some 'other' events points to a user"
        try:
            if not self.bot.database_online or self.bot.current_event is None:
                return True
            query = "INSERT INTO `event_points` (`user_id`, `other_points`, `beta`) VALUES (%s, %s, %s) \
                ON DUPLICATE KEY UPDATE other_points = other_points + VALUE(`other_points`);"
            async with self.bot.db_main.write(query, (user_id, points, self.bot.beta)):
                pass
            try:
                await self.reload_event_rankcard(user_id)
                await self.reload_event_special_role(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False


async def setup(bot):
    await bot.add_cog(BotEvents(bot))
