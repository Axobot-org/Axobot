import datetime as dt
from collections import defaultdict
from random import choice, random
from typing import Optional

import discord

from libs.bot_classes import Axobot
from libs.bot_events.dict_types import EventData, EventItem, EventType
from libs.bot_events.subcogs.abstract_subcog import AbstractSubcog

# list of the advent calendar items IDs per day between 1 and 24
#  on december 25th the card will be unlocked
ADVENT_CALENDAR: dict[int, list[int]] = {
    1:  [41, 61],
    2:  [46, 49],
    3:  [42, 61],
    4:  [46, 52],
    5:  [36, 47, 49],
    6:  [32, 47, 57, 39],
    7:  [42, 53, 61, 61],
    8:  [32, 32, 49, 59, 61],
    9:  [45, 47, 48, 51, 55],
    10: [39, 39, 44, 51],
    11: [36, 41, 43, 49],
    12: [32, 33, 35, 46, 53, 55],
    13: [36, 40, 42, 58],
    14: [38],
    15: [42, 50],
    16: [39, 60, 62],
    17: [45, 25, 25, 53],
    18: [33, 48, 56, 58],
    19: [36, 45, 45, 50],
    20: [35, 39, 42, 43, 57],
    21: [37, 43, 55, 57],
    22: [40, 48, 49],
    23: [33, 46, 58],
    24: [54],
}


class ChristmasSubcog(AbstractSubcog):
    "Utility class for the BotEvents cog when the event is Christmas"

    def __init__(self, bot: Axobot,
                 current_event: Optional[EventType], current_event_data: EventData, current_event_id: Optional[str]):
        super().__init__(bot, current_event, current_event_data, current_event_id)
        self.pending_reactions: dict[int, EventItem] = {} # map of MessageID => EventItem

    async def on_message(self, msg):
        "Add random reaction to some messages"
        if self.current_event and (data := self.current_event_data.get("emojis")):
            if not await self.is_fun_enabled(msg):
                # don't react if fun is disabled for this guild
                return
            if random() < data["probability"] and any(trigger in msg.content for trigger in data["triggers"]):
                react = choice(data["reactions_list"])
                await msg.add_reaction(react)

    async def profile_cmd(self, ctx, user):
        "Displays the profile of the user"
        lang = await self.bot._(ctx.channel, '_used_locale')
        lang = 'en' if lang not in ('en', 'fr') else lang
        events_desc = self.translations_data[lang]["events_desc"]

        # if no event
        if not self.current_event_id in events_desc:
            await ctx.send(await self.bot._(ctx.channel, "bot_events.nothing-desc"))
            if self.current_event_id:
                self.bot.dispatch("error", ValueError(f"'{self.current_event_id}' has no event description"), ctx)
            return
        # if current event has no objectives
        if not self.current_event_data["objectives"]:
            cmd_mention = await self.bot.get_command_mention("event info")
            await ctx.send(await self.bot._(ctx.channel, "bot_events.no-objectives", cmd=cmd_mention))
            return

        await ctx.defer()

        title = await self.bot._(ctx.channel, "bot_events.rank-title")
        desc = await self.bot._(ctx.channel, "bot_events.xp-howto")

        emb = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
        emb.set_author(name=user, icon_url=user.display_avatar.replace(static_format="png", size=32))

        await ctx.send(embed=emb)

    async def collect_cmd(self, ctx):
        "Collect your daily reward"
        current_event = self.current_event_id
        lang = await self.bot._(ctx.channel, '_used_locale')
        lang = 'en' if lang not in ('en', 'fr') else lang
        events_desc = self.translations_data[lang]["events_desc"]
        # if no event
        if not current_event in events_desc:
            await ctx.send(await self.bot._(ctx.channel, "bot_events.nothing-desc"))
            if current_event:
                self.bot.dispatch("error", ValueError(f"'{current_event}' has no event description"), ctx)
            return
        # if current event has no objectives
        if not self.current_event_data["objectives"]:
            cmd_mention = await self.bot.get_command_mention("event info")
            await ctx.send(await self.bot._(ctx.channel, "bot_events.no-objectives", cmd=cmd_mention))
            return
        await ctx.defer()

        # check last collect from this user
        last_collect_day = await self.get_last_user_collect(ctx.author.id)
        gifts = await self.get_calendar_gifts_from_date(last_collect_day)
        await self.db_add_user_items(ctx.author.id, [item["item_id"] for item in gifts])
        await self.db_add_collect(ctx.author.id, sum(item["points"] for item in gifts))
        txt = await self.generate_collect_message(ctx.channel, gifts, last_collect_day)
        # send result
        if ctx.can_send_embed:
            title = self.translations_data[lang]["events_title"][current_event]
            emb = discord.Embed(title="✨ "+title, description=txt, color=self.current_event_data["color"])
            emb.add_field(**await self.get_random_tip_field(ctx.channel))
            emb.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/4213/4213958.png")
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)

    async def today(self):
        return dt.datetime.now(dt.timezone.utc).date()
        # return dt.date(2023, 12, 1)

    async def get_calendar_gifts_from_date(self, last_collect_day: dt.date) -> list[EventItem]:
        "Get the list of the gifts from the advent calendar from a given date"
        today = await self.today()
        if today.month != 12:
            return []
        gifts_ids = []
        # make sure user can't get more than 3 gifts in the past
        min_past_day = max(today.day - 3, last_collect_day.day)
        for day in range(min_past_day, today.day + 1):
            gifts_ids += ADVENT_CALENDAR[day]
        if not gifts_ids:
            return []
        items = await self.db_get_event_items("christmas")
        gifts: list[EventItem] = []
        for item in items:
            if item["item_id"] in gifts_ids:
                gifts.append(item)
        return gifts

    async def is_past_christmas(self):
        today = await self.today()
        return today.month == 12 and today.day >= 25

    async def generate_collect_message(self, channel, items: list[EventItem], last_collect_day: dt.date):
        "Generate the message to send after a /collect command"
        past_christmas = await self.is_past_christmas()
        if not items:
            if past_christmas:
                return "You collected all the gifts from the advent calendar!"
            return "No gift for you today, come back tomorrow!"
        # 1 item collected
        language = await self.bot._(channel, "_used_locale")
        name_key = "french_name" if language in ("fr", "fr2") else "english_name"
        today = await self.today()
        total_points = sum(item["points"] for item in items)
        if today == last_collect_day:
            text = f"### Here is today's gift (**{total_points} points**):"
        else:
            missed_days = min(today.day - last_collect_day.day, 3)
            text = f"### Here are today's gifts, as well as {missed_days} missed days (**{total_points} points**):"
        items_group: dict[int, int] = defaultdict(int)
        for item in items:
            items_group[item["item_id"]] += 1
        for item_id, count in items_group.items():
            item = next(item for item in items if item["item_id"] == item_id)
            item_name = item["emoji"] + " " + item[name_key]
            item_points = ('+' if item["points"] >= 0 else '') + str(item["points"] * count)
            text += f"\n**{item_name}** x{count} ({item_points} points)"
        return text

    async def get_last_user_collect(self, user_id: int):
        "Get the UTC date of the last collect from a user, or December 1st if never collected"
        last_collect_date = await self.db_get_last_user_collect(user_id)
        if last_collect_date is None:
            return dt.date(2023, 12, 1)
        today = await self.today()
        last_collect_day = last_collect_date.date()
        if last_collect_day.year != today.year or last_collect_day.month != today.month:
            return dt.date(2023, 12, 1)
        return last_collect_day

    async def db_add_collect(self, user_id: int, points: int):
        """Add collect points to a user"""
        if not self.bot.database_online or self.bot.current_event is None:
            return
        query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `beta`) VALUES (%s, %s, %s) \
            ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                last_collect = CURRENT_TIMESTAMP();"
        async with self.bot.db_query(query, (user_id, points, self.bot.beta)):
            pass
        if cog := self.bot.get_cog("BotEvents"):
            try:
                await cog.reload_event_rankcard(user_id)
                await cog.reload_event_special_role(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
