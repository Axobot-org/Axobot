from collections import defaultdict
from random import choice, choices, lognormvariate, randint, random

import discord

from core.bot_classes import Axobot
from core.formatutils import FormatUtils

from ..data.dict_types import EventData, EventItem, EventType
from .abstract_subcog import AbstractSubcog


class RandomCollectSubcog(AbstractSubcog):
    "Utility class for the BotEvents cog when the event is about collecting random items"

    def __init__(self, bot: Axobot,
                 current_event: EventType | None, current_event_data: EventData, current_event_id: str | None):
        super().__init__(bot, current_event, current_event_data, current_event_id)

        self.collect_reward = [-8, 25]
        self.collect_cooldown = 60*60 # (1h) time in seconds between 2 collects
        self.collect_max_strike_period = 3600 * 2 # (2h) time in seconds after which the strike level is reset to 0
        self.collect_bonus_per_strike = 1.05 # the amount of points is multiplied by this number for each strike level

    async def on_message(self, msg):
        "Add random reaction to some messages"
        if self.current_event and (data := self.current_event_data.get("emojis")):
            if msg.guild is not None and not msg.channel.permissions_for(msg.guild.me).add_reactions:
                # don't react if we can't add reactions
                return
            if not await self.is_fun_enabled(msg):
                # don't react if fun is disabled for this guild
                return
            if random() < data["probability"] and any(trigger in msg.content for trigger in data["triggers"]):
                react = choice(data["reactions_list"])
                await msg.add_reaction(react)

    async def on_raw_reaction_add(self, payload):
        pass

    async def profile_cmd(self, interaction, user):
        "Displays the profile of the user"
        lang = await self.get_event_language(interaction)
        events_desc = self.translations_data[lang]["events_desc"]

        # if no event
        if not self.current_event_id in events_desc:
            await interaction.followup.send(await self.bot._(interaction, "bot_events.nothing-desc"))
            if self.current_event_id:
                self.bot.dispatch("error", ValueError(f"'{self.current_event_id}' has no event description"), interaction)
            return
        # if current event has no objectives
        if not self.current_event_data["objectives"]:
            cmd_mention = await self.bot.get_command_mention("event info")
            await interaction.followup.send(await self.bot._(interaction, "bot_events.no-objectives", cmd=cmd_mention))
            return

        title = await self.bot._(interaction, "bot_events.rank-title")
        desc = await self.bot._(interaction, "bot_events.xp-howto")

        emb = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
        emb.set_author(name=user, icon_url=user.display_avatar.replace(static_format="png", size=32))
        for field in await self.generate_user_profile_rank_fields(interaction, lang, user):
            emb.add_field(**field)
        emb.add_field(**await self.generate_user_profile_collection_field(interaction, user))
        await interaction.followup.send(embed=emb)

    async def collect_cmd(self, interaction):
        "Get some event points every hour"
        lang = await self.get_event_language(interaction)
        events_desc = self.translations_data[lang]["events_desc"]
        # if no event
        if not self.current_event_id in events_desc:
            await interaction.followup.send(await self.bot._(interaction, "bot_events.nothing-desc"))
            if self.current_event_id:
                self.bot.dispatch("error", ValueError(f"'{self.current_event_id}' has no event description"), interaction)
            return
        # if current event has no objectives
        if not self.current_event_data["objectives"]:
            cmd_mention = await self.bot.get_command_mention("event info")
            await interaction.followup.send(await self.bot._(interaction, "bot_events.no-objectives", cmd=cmd_mention))
            return

        # check last collect from this user
        seconds_since_last_collect = await self.get_seconds_since_last_collect(interaction.user.id)
        can_collect, is_strike = await self.check_user_collect_availability(interaction.user.id, seconds_since_last_collect)
        if not can_collect:
            # cooldown error
            time_remaining = self.collect_cooldown - seconds_since_last_collect
            remaining = await FormatUtils.time_delta(time_remaining, lang=lang)
            txt = await self.bot._(interaction, "bot_events.collect.too-quick", time=remaining)
        else:
            # grant points
            items = await self.get_random_items()
            strike_level = (await self.db_get_user_strike_level(interaction.user.id) + 1) if is_strike else 0
            if len(items) == 0:
                points = randint(*self.collect_reward)
                bonus = 0
            else:
                points = sum(item["points"] for item in items)
                bonus = max(0, await self.adjust_points_to_strike(points, strike_level) - points)
                await self.db_add_user_items(interaction.user.id, [item["item_id"] for item in items])
            txt = await self.generate_collect_message(interaction, items, points + bonus)
            if strike_level and bonus != 0:
                txt += "\n\n" + \
                    await self.bot._(interaction, 'bot_events.collect.strike-bonus', bonus=bonus, level=strike_level+1)
            if is_strike:
                await self.add_collect_and_strike(interaction.user.id, points + bonus, send_notif_to_interaction=interaction)
            else:
                await self.add_collect(interaction.user.id, points + bonus, send_notif_to_interaction=interaction)
        # send result
        title = self.translations_data[lang]["events_title"][self.current_event_id]
        emb = discord.Embed(title=title, description=txt, color=self.current_event_data["color"])
        emb.add_field(**await self.get_random_tip_field(interaction))
        await interaction.followup.send(embed=emb)

    async def generate_collect_message(self, interaction: discord.Interaction, items: list[EventItem], points: int):
        "Generate the message to send after a /collect command"
        items_count = len(items)
        # no item collected
        if items_count == 0:
            if points < 0:
                return await self.bot._(interaction, "bot_events.collect.lost-points", points=-points)
            if points == 0:
                return await self.bot._(interaction, "bot_events.collect.nothing")
            return await self.bot._(interaction, "bot_events.collect.got-points", points=points)
        language = await self.bot._(interaction, "_used_locale")
        name_key = "french_name" if language in ("fr", "fr2") else "english_name"
        # 1 item collected
        if items_count == 1:
            item_name = items[0]["emoji"] + " " + items[0][name_key]
            return await self.bot._(interaction, "bot_events.collect.got-items", count=1, item=item_name, points=points)
        # more than 1 item
        f_points = str(points) if points <= 0 else "+" + str(points)
        text = await self.bot._(interaction, "bot_events.collect.got-items", count=items_count, points=f_points)
        items_group: dict[int, int] = defaultdict(int)
        for item in items:
            items_group[item["item_id"]] += 1
        for item_id, count in items_group.items():
            item = next(item for item in items if item["item_id"] == item_id)
            item_name = item["emoji"] + " " + item[name_key]
            item_points = ('+' if item["points"] >= 0 else '') + str(item["points"] * count)
            text += f"\n**{item_name}** x{count} ({item_points} points)"
        return text

    async def get_random_items(self) -> list[EventItem]:
        "Get some random items to win during an event"
        if self.current_event is None:
            return []
        items_count = min(round(lognormvariate(1.1, 0.9)), 8) # random number between 0 and 8
        if items_count <= 0:
            return []
        items = await self.db_get_event_items(self.current_event)
        if len(items) == 0:
            return []
        return choices(
            items,
            weights=[item["frequency"] for item in items],
            k=items_count
        )

    async def check_user_collect_availability(self, user_id: int, seconds_since_last_collect: int | None = None):
        "Check if a user can collect points, and if they are in a strike period"
        if not self.bot.database_online or self.bot.current_event is None:
            return False, False
        if not seconds_since_last_collect:
            seconds_since_last_collect = await self.get_seconds_since_last_collect(user_id)
        if seconds_since_last_collect is None:
            return True, False
        if seconds_since_last_collect < self.collect_cooldown:
            return False, False
        if seconds_since_last_collect < self.collect_max_strike_period:
            return True, True
        return True, False

    async def adjust_points_to_strike(self, points: int, strike_level: int):
        "Get a random amount of points for the /collect command, depending on the strike level"
        strike_coef = self.collect_bonus_per_strike ** strike_level
        return round(points * strike_coef)

    async def db_get_user_strike_level(self, user_id: int) -> int:
        "Get the strike level of a user"
        if not self.bot.database_online:
            return 0
        query = "SELECT `strike_level` FROM `event_points` WHERE `user_id` = %s AND `beta` = %s;"
        async with self.bot.db_query(query, (user_id, self.bot.beta), fetchone=True) as query_result:
            return query_result["strike_level"] if query_result else 0
