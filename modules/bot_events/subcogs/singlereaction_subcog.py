from random import choices, random

import discord
import emoji
from asyncache import cached
from cachetools import TTLCache

from core.bot_classes import Axobot
from core.formatutils import FormatUtils

from ..data.dict_types import EventData, EventItem, EventType
from .abstract_subcog import AbstractSubcog


class SingleReactionSubcog(AbstractSubcog):
    """Utility class for the BotEvents cog when the event is about
    collecting the xp card at the first reaction."""

    def __init__(self, bot: Axobot,
                 current_event: EventType | None, current_event_data: EventData, current_event_id: str | None):
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
        if payload.member and payload.member.bot:
            return
        item = self.pending_reactions[payload.message_id]
        if payload.emoji.name != item["emoji"]:
            return
        # find which channel and language to use
        channel = await self.get_reaction_destination_channel(payload)
        if channel is None:
            return
        delete_after = 12 if isinstance(channel, discord.abc.PrivateChannel) else None
        translation_source = payload.guild_id or payload.user_id
        lang = await self.get_event_language(translation_source)
        # check last collect from this user
        seconds_since_last_collect = await self.get_seconds_since_last_collect(payload.user_id)
        if seconds_since_last_collect < self.collect_cooldown:
            # user is trying to collect too quickly
            time_remaining = self.collect_cooldown - seconds_since_last_collect
            remaining = await FormatUtils.time_delta(time_remaining, lang=lang, seconds=time_remaining < 60)
            await channel.send(
                await self.bot._(translation_source, "bot_events.ocean-cooldown", time=remaining),
                delete_after=delete_after
            )
            return
        del self.pending_reactions[payload.message_id]
        # add item to user collection
        await self.db_add_user_items(payload.user_id, [item["item_id"]])
        # prepare the notification embed
        title = self.translations_data[lang]["events_title"][self.current_event_id]
        desc_key = "bot_events.reaction.neutral"
        name_key = "french_name" if lang in ("fr", "fr2") else "english_name"
        item_name = item["emoji"] + " " + item[name_key]
        user_mention = f"<@{payload.user_id}>"
        desc = await self.bot._(translation_source, desc_key, user=user_mention, item=item_name)
        embed = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
        if self.current_event_data["icon"]:
            embed.set_image(url=self.current_event_data["icon"])
        # send the notification in the guild/DM channel
        await channel.send(embed=embed, delete_after=delete_after)
        # add points (and potentially grant reward rank card)
        await self.add_collect(payload.user_id, item["points"], send_notif_to_interaction=channel)

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
        emb.set_author(name=user.global_name, icon_url=user.display_avatar.replace(static_format="png", size=32))
        for field in await self.generate_user_profile_rank_fields(interaction, lang, user):
            emb.add_field(**field)
        emb.add_field(**await self.generate_user_profile_collection_field(interaction, user))
        await interaction.followup.send(embed=emb)

    async def collect_cmd(self, interaction):
        "Collects the daily/hourly reward"
        lang = await self.get_event_language(interaction)
        events_desc = self.translations_data[lang]["events_desc"]

        # if no event
        if not self.current_event_id in events_desc:
            await interaction.followup.send(await self.bot._(interaction, "bot_events.nothing-desc"))
            if self.current_event_id:
                self.bot.dispatch("error", ValueError(f"'{self.current_event_id}' has no event description"), interaction)
            return

        cmd_mention = await self.bot.get_command_mention("event info")
        await interaction.followup.send(await self.bot._(interaction, "bot_events.no-objectives", cmd=cmd_mention))


    async def check_trigger_words(self, message: str):
        "Check if a word in the message triggers the event"
        if self.current_event and (data := self.current_event_data.get("emojis")):
            message = message.lower()
            return any(trigger in message for trigger in data["triggers"])
        return False

    async def get_reaction_destination_channel(self, payload: discord.RawReactionActionEvent):
        "Find the correct channel to use when responding to a collect reaction"
        # get the destination channel
        if (
            (channel := self.bot.get_channel(payload.channel_id))
            and channel.permissions_for(channel.guild.me).send_messages
            and channel.permissions_for(channel.guild.me).embed_links
        ):
            return channel
        if (user := self.bot.get_user(payload.user_id)) and user.dm_channel is not None:
            return user.dm_channel
        return None

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
