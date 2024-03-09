import datetime as dt
from collections import defaultdict
from random import choices, random
from typing import Optional

import discord
import emoji
from asyncache import cached
from cachetools import TTLCache

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
            if msg.guild is not None and not msg.channel.permissions_for(msg.guild.me).add_reactions:
                # don't react if we can't add reactions
                return
            if not await self.is_fun_enabled(msg):
                # don't react if fun is disabled for this guild
                return
            if random() < data["probability"] and await self.check_trigger_words(msg.content):
                if item := await self.get_random_item_for_reaction():
                    try:
                        await msg.add_reaction(item["emoji"])
                    except discord.HTTPException as err:
                        self.bot.dispatch("error", err, f"When trying to add event reaction {item['emoji']}")
                        return
                    self.pending_reactions[msg.id] = item

    async def on_raw_reaction_add(self, payload):
        if payload.message_id not in self.pending_reactions:
            return
        item = self.pending_reactions[payload.message_id]
        if payload.emoji.name != item["emoji"]:
            print("wrong emoji")
            return
        del self.pending_reactions[payload.message_id]
        # add item to user collection
        await self.db_add_user_items(payload.user_id, [item["item_id"]])
        # prepare the notification embed
        translation_source = payload.guild_id or payload.user_id
        lang = await self.bot._(translation_source, '_used_locale')
        title = self.translations_data[lang]["events_title"][self.current_event_id]
        desc_key = "bot_events.reaction.positive" if item["points"] >= 0 else "bot_events.reaction.negative"
        name_key = "french_name" if lang in ("fr", "fr2") else "english_name"
        item_name = item["emoji"] + " " + item[name_key]
        user_mention = f"<@{payload.user_id}>"
        desc = await self.bot._(translation_source, desc_key, user=user_mention, item=item_name, points=abs(item["points"]))
        embed = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
        if self.current_event_data["icon"]:
            embed.set_image(url=self.current_event_data["icon"])
        notif_channel = None
        # get the destination channel
        if (
            (channel := self.bot.get_channel(payload.channel_id))
            and channel.permissions_for(channel.guild.me).send_messages
            and channel.permissions_for(channel.guild.me).embed_links
        ):
            await channel.send(embed=embed, delete_after=12)
            notif_channel = channel
        elif (user := self.bot.get_user(payload.user_id)) and user.dm_channel is not None:
            await user.dm_channel.send(embed=embed)
            notif_channel = user.dm_channel
        # add points (and potentially grant reward rank card)
        await self.add_collect(payload.user_id, item["points"], send_notif_to_channel=notif_channel)

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
        emb.set_author(name=user.global_name, icon_url=user.display_avatar.replace(static_format="png", size=32))
        for field in await self.generate_user_profile_rank_fields(ctx, lang, user):
            emb.add_field(**field)
        if user == ctx.author:
            if field := await self._generate_user_profile_top_rank_field(user):
                emb.add_field(**field)
        emb.add_field(**await self.generate_user_profile_collection_field(ctx, user))
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
        if gifts:
            await self.db_add_user_items(ctx.author.id, [item["item_id"] for item in gifts])
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
        # add points (and potentially grant reward rank card)
        await self.add_collect(ctx.author.id, sum(item["points"] for item in gifts), send_notif_to_channel=ctx.channel)

    @cached(TTLCache(maxsize=1, ttl=60*2)) # cache for 2min
    async def today(self):
        return dt.datetime.now(dt.timezone.utc).date()

    async def check_trigger_words(self, message: str):
        "Check if a word in the message triggers the event"
        if self.current_event and (data := self.current_event_data.get("emojis")):
            message = message.lower()
            return any(trigger in message for trigger in data["triggers"])
        return False

    async def get_calendar_gifts_from_date(self, last_collect_day: dt.date) -> list[EventItem]:
        "Get the list of the gifts from the advent calendar from a given date"
        today = await self.today()
        if today.month != 12:
            return []
        if today.day >= 25:
            today = dt.date(today.year, 12, 24)
        gifts_ids = []
        # make sure user can't get more than 3 gifts in the past
        min_past_day = max(today.day - 3, last_collect_day.day if last_collect_day.month == 12 else 0)
        for day in range(min_past_day, today.day):
            gifts_ids += ADVENT_CALENDAR[day + 1]
        if not gifts_ids:
            return []
        items = await self.db_get_event_items(self.current_event)
        gifts: list[EventItem] = []
        for item in items:
            if item["item_id"] in gifts_ids:
                gifts.append(item)
        return gifts

    async def _generate_user_profile_top_rank_field(self, user: discord.User):
        "If user is in Top 3, returns an embed field indicating that they may win a Nitro prize"
        user_rank_query = await self.db_get_event_rank(user.id)
        if user_rank_query is None:
            return None
        rank = user_rank_query['rank']
        if rank > 3:
            return None
        return {
            "name": ":wave: Hey, congrats!",
            "value": "Hey, it looks like you're in the **top 3!**\nDid you know that the top 3 players will win a Nitro prize at \
the end of the event? Don't forget to join our [support server](https://discord.gg/N55zY88) to claim your prize if you win!\n\
<:_nothing:446782476375949323>",
            "inline": False,
        }

    async def is_past_christmas(self):
        today = await self.today()
        return today.month == 12 and today.day >= 25

    async def generate_collect_message(self, channel, items: list[EventItem], last_collect_day: dt.date):
        "Generate the message to send after a /collect command"
        past_christmas = await self.is_past_christmas()
        if not items:
            if past_christmas:
                return await self.bot._(channel, "bot_events.calendar.collected-all")
            return await self.bot._(channel, "bot_events.calendar.collected-day")
        # 1 item collected
        language = await self.bot._(channel, "_used_locale")
        name_key = "french_name" if language in ("fr", "fr2") else "english_name"
        today = await self.today()
        total_points = sum(item["points"] for item in items)
        text = "### "
        if (today - last_collect_day).days <= 1 or last_collect_day.month != 12:
            text += await self.bot._(channel, "bot_events.calendar.today-gifts", points=total_points)
        else:
            missed_days = min(today.day - last_collect_day.day - 1, 3)
            text = await self.bot._(channel, "bot_events.calendar.today-gifts-late", days=missed_days, points=total_points)
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
            return dt.date(2023, 11, 30)
        today = await self.today()
        last_collect_day = last_collect_date.date()
        if last_collect_day.year != today.year or last_collect_day.month != today.month:
            return dt.date(2023, 11, 30)
        return last_collect_day

    @cached(TTLCache(maxsize=1, ttl=60*60*24))
    async def _get_suitable_reaction_items(self):
        "Get the list of items usable in reactions"
        if self.current_event is None:
            return []
        items = await self.db_get_event_items(self.current_event)
        if len(items) == 0:
            return []
        return [item for item in items if emoji.emoji_count(item["emoji"]) == 1]

    async def get_random_item_for_reaction(self):
        "Get some random items to win during an event"
        items = await self._get_suitable_reaction_items()
        if not items:
            return None
        return choices(
            items,
            weights=[item["frequency"] for item in items],
        )[0]
