from random import choices, random
from typing import Optional

import discord
import emoji
from asyncache import cached
from cachetools import TTLCache

from libs.bot_classes import Axobot
from libs.bot_events.dict_types import EventData, EventItem, EventType
from libs.bot_events.subcogs.abstract_subcog import AbstractSubcog


class SingleReactionSubcog(AbstractSubcog):
    """Utility class for the BotEvents cog when the event is about
    collecting the xp card at the first reaction."""

    def __init__(self, bot: Axobot,
                 current_event: Optional[EventType], current_event_data: EventData, current_event_id: Optional[str]):
        super().__init__(bot, current_event, current_event_data, current_event_id)
        self.pending_reactions: dict[int, EventItem] = {} # map of MessageID => EventItem

        self.collect_cooldown = 60*30 # (30min) time in seconds between 2 collects

    async def on_message(self, msg):
        "Add random reaction to some message"
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
        "Called when a reaction is added"
        if payload.message_id not in self.pending_reactions:
            return
        item = self.pending_reactions[payload.message_id]
        if payload.emoji.name != item["emoji"]:
            return
        del self.pending_reactions[payload.message_id]
        # add item to user collection
        await self.db_add_user_items(payload.user_id, [item["item_id"]])
        # prepare the notification embed
        translation_source = payload.guild_id or payload.user_id
        lang = await self.get_event_language(translation_source)
        title = self.translations_data[lang]["events_title"][self.current_event_id]
        desc_key = "bot_events.reaction.neutral"
        name_key = "french_name" if lang in ("fr", "fr2") else "english_name"
        item_name = item["emoji"] + " " + item[name_key]
        user_mention = f"<@{payload.user_id}>"
        desc = await self.bot._(translation_source, desc_key, user=user_mention, item=item_name)
        embed = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
        if self.current_event_data["icon"]:
            embed.set_image(url=self.current_event_data["icon"])
        # get the destination channel
        if (
            (channel := self.bot.get_channel(payload.channel_id))
            and channel.permissions_for(channel.guild.me).send_messages
            and channel.permissions_for(channel.guild.me).embed_links
        ):
            await channel.send(embed=embed, delete_after=12)
            # send the rank card notification if needed
            await self.bot.get_cog("BotEvents").check_and_send_card_unlocked_notif(channel, payload.user_id)
        elif (user := self.bot.get_user(payload.user_id)) and user.dm_channel is not None:
            await user.dm_channel.send(embed=embed)
            # send the rank card notification if needed
            await self.bot.get_cog("BotEvents").check_and_send_card_unlocked_notif(user.dm_channel, payload.user_id)
        # add points (and potentially grant reward rank card)
        await self.db_add_collect(payload.user_id, item["points"])

    async def profile_cmd(self, ctx, user):
        "Displays the profile of the user"
        print("profile_cmd")

    async def collect_cmd(self, ctx):
        "Collects the daily/hourly reward"
        cmd_mention = await self.bot.get_command_mention("event info")
        await ctx.send(await self.bot._(ctx.channel, "bot_events.no-objectives", cmd=cmd_mention))


    async def check_trigger_words(self, message: str):
        "Check if a word in the message triggers the event"
        if self.current_event and (data := self.current_event_data.get("emojis")):
            message = message.lower()
            return any(trigger in message for trigger in data["triggers"])
        return False

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

    async def db_add_collect(self, user_id: int, points: int):
        "Add collect points to a user"
        if not self.bot.database_online or self.bot.current_event is None:
            return
        if points:
            query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `last_collect`, `beta`) \
                VALUES (%s, %s, CURRENT_TIMESTAMP(), %s) \
                ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                    last_collect = CURRENT_TIMESTAMP();"
            async with self.bot.db_query(query, (user_id, points,  self.bot.beta)):
                pass
        if cog := self.bot.get_cog("BotEvents"):
            try:
                await cog.reload_event_rankcard(user_id)
                await cog.reload_event_special_role(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
