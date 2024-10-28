import datetime
from abc import ABC, abstractmethod
from typing import Any, Literal, TypedDict

import discord

from core.bot_classes import Axobot
from core.formatutils import FormatUtils

from ..data.dict_types import (EventData, EventItem, EventItemWithCount,
                               EventType)
from ..data.get_translations import get_events_translations


class DBUserRank(TypedDict):
    "Type for the result of db_get_event_rank"
    user_id: int
    points: int
    rank: int


class AbstractSubcog(ABC):
    "Abstract class for the subcogs used by BotEvents"

    def __init__(self, bot: Axobot,
                 current_event: EventType | None, current_event_data: EventData, current_event_id: str | None):
        self.bot = bot
        self.current_event = current_event
        self.current_event_data = current_event_data
        self.current_event_id = current_event_id
        self.translations_data = get_events_translations()

    @abstractmethod
    async def on_message(self, msg: discord.Message):
        "Called when a message is sent"

    @abstractmethod
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        "Called when a reaction is added"

    @abstractmethod
    async def profile_cmd(self, interaction: discord.Interaction, user: discord.User):
        "Displays the profile of the user"

    @abstractmethod
    async def collect_cmd(self, interaction: discord.Interaction):
        "Collects the daily/hourly reward"

    async def get_event_language(self, translation_source) -> Literal["fr", "en"]:
        "Find which language to use for the event translations"
        lang = await self.bot._(translation_source, "_used_locale")
        if lang in ("fr", "fr2"):
            return "fr"
        return "en"

    async def generate_user_profile_rank_fields(self, interaction: discord.Interaction, lang: Literal["fr", "en"],
                                                user: discord.User):
        "Compute the texts to display in the /event profile command"
        user_rank_query = await self.db_get_event_rank(user.id)
        if user_rank_query is None:
            user_rank = await self.bot._(interaction, "bot_events.unclassed")
            points = 0
        else:
            total_ranked = await self.db_get_participants_count()
            if user_rank_query["rank"] <= total_ranked:
                user_rank = f"{user_rank_query['rank']}/{total_ranked}"
            else:
                user_rank = await self.bot._(interaction, "bot_events.unclassed")
            points: int = user_rank_query["points"]

        _points_total = await self.bot._(interaction, "bot_events.points-total")
        _position_global = await self.bot._(interaction, "bot_events.position-global")
        _rank_global = await self.bot._(interaction, "bot_events.leaderboard-global", count=5)

        fields: list[dict[str, Any]] = []
        if prices_field := await self.generate_prices_field(interaction, lang, points):
            fields.append(prices_field)
        fields += [
            {"name": _points_total, "value": str(points)},
            {"name": _position_global, "value": user_rank},
        ]
        if top_5 := await self.get_top_5():
            fields.append({"name": _rank_global, "value": top_5, "inline": False})
        return fields

    async def generate_prices_field(self, interaction: discord.Interaction, lang: Literal["fr", "en"], user_points: int):
        "Generate an embed field to display the current event prices for the user"
        prices_translations: dict[str, dict[str, str]] = self.translations_data[lang]["events_prices"]
        if self.current_event_id not in prices_translations:
            return None
        prices = []
        for required_points, desc in prices_translations[self.current_event_id].items():
            # check for a min_date
            related_objective = [
                objective
                for objective in self.current_event_data["objectives"]
                if str(objective["points"]) == required_points
            ]
            parsed_date = None
            if related_objective and (min_date := related_objective[0].get("min_date")):
                parsed_date = datetime.datetime.strptime(min_date, "%Y-%m-%d").replace(tzinfo=datetime.UTC)
                format_date = await FormatUtils.date(parsed_date, hour=False, seconds=False)
                desc += " (**" + await self.bot._(interaction, "bot_events.available-starting", date=format_date) + "**)"
            # assign correct emoji
            if parsed_date and parsed_date > self.bot.utcnow():
                emoji = self.bot.emojis_manager.customs["gray_check"]
            elif int(required_points) > user_points:
                emoji =self.bot.emojis_manager.customs["red_cross"]
            else:
                emoji = self.bot.emojis_manager.customs["green_check"]
            prices.append(f"{emoji}{min(user_points, int(required_points))}/{required_points}: {desc}")
        return {
            "name": await self.bot._(interaction, "bot_events.objectives"),
            "value": "\n".join(prices),
            "inline": False
        }

    async def generate_user_profile_collection_field(self, interaction: discord.Interaction, user: discord.User):
        "Compute the texts to display in the /event profile command"
        if interaction.user == user:
            title = await self.bot._(interaction, "bot_events.collection-title.user")
        else:
            title = await self.bot._(interaction, "bot_events.collection-title.other", user=user.display_name)
        items = await self.db_get_user_collected_items(user.id, self.current_event)
        if len(items) == 0:
            if interaction.user == user:
                _empty_collection = await self.bot._(interaction, "bot_events.collection-empty.user")
            else:
                _empty_collection = await self.bot._(interaction, "bot_events.collection-empty.other", user=user.display_name)
            return {"name": title, "value": _empty_collection, "inline": True}
        lang = await self.bot._(interaction, "_used_locale")
        name_key = "french_name" if lang in ("fr", "fr2") else "english_name"
        items.sort(key=lambda item: item["frequency"], reverse=True)
        items_list: list[str] = []
        more_count = 0
        for item in items:
            if len(items_list) >= 32:
                more_count += item["count"]
                continue
            item_name = item["emoji"] + " " + item[name_key]
            items_list.append(f"{item_name} x{item['count']}")
        if more_count:
            items_list.append(await self.bot._(interaction, "bot_events.collection-more", count=more_count))
        return {"name": title, "value": "\n".join(items_list), "inline": True}

    async def get_top_5(self) -> str:
        "Get the list of the 5 users with the most event points"
        top_5 = await self.db_get_event_top(number=5)
        if top_5 is None:
            return await self.bot._(self.bot.get_channel(0), "bot_events.nothing-desc")
        top_5_f: list[str] = []
        for i, row in enumerate(top_5):
            if user := self.bot.get_user(row["user_id"]):
                username = user.display_name
            elif user := await self.bot.fetch_user(row["user_id"]):
                username = user.display_name
            else:
                username = f"user {row['user_id']}"
            top_5_f.append(f"{i+1}. {username} ({row['points']} points)")
        return "\n".join(top_5_f)

    async def is_fun_enabled(self, message: discord.Message):
        "Check if fun is enabled in a given context"
        if message.guild is None:
            return True
        if not self.bot.database_online and not message.author.guild_permissions.manage_guild:
            return False
        return await self.bot.get_config(message.guild.id, "enable_events")

    async def get_random_tip_field(self, interaction: discord.Interaction):
        return {
            "name": await self.bot._(interaction, "bot_events.tip-title"),
            "value": await self.bot.tips_manager.generate_random_tip(interaction),
            "inline": False
        }

    async def get_seconds_since_last_collect(self, user_id: int):
        "Get the seconds since the last collect from a user"
        last_collect = await self.db_get_last_user_collect(user_id)
        if last_collect is None:
            return 1e9
        return (self.bot.utcnow() - last_collect).total_seconds()

    async def add_collect(self, user_id: int, points: int,
                          send_notif_to_interaction: discord.Interaction | discord.TextChannel | None = None):
        "Add collect points to a user"
        if not self.bot.database_online or self.bot.current_event is None:
            return
        await self.db_add_collect(user_id, points, with_strike=False)
        if cog := self.bot.get_cog("BotEvents"):
            try:
                if send_notif_to_interaction:
                    await cog.check_and_send_card_unlocked_notif(send_notif_to_interaction, user_id)
                await cog.reload_event_rankcard(user_id)
                await cog.reload_event_special_role(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)

    async def add_collect_and_strike(self, user_id: int, points: int,
                                     send_notif_to_interaction: discord.Interaction | discord.TextChannel | None = None):
        """Add collect points to a user and increase the strike level by 1"""
        if not self.bot.database_online or self.bot.current_event is None:
            return True
        await self.db_add_collect(user_id, points, with_strike=True)
        if cog := self.bot.get_cog("BotEvents"):
            try:
                if send_notif_to_interaction:
                    await cog.check_and_send_card_unlocked_notif(send_notif_to_interaction, user_id)
                await cog.reload_event_rankcard(user_id)
                await cog.reload_event_special_role(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
        return True

    async def db_get_event_top(self, number: int):
        "Get the event points leaderboard containing at max the given number of users"
        if not self.bot.database_online:
            return None
        query = "SELECT `user_id`, `points` FROM `event_points` WHERE `points` != 0 AND `beta` = %s \
            ORDER BY `points` DESC LIMIT %s"
        async with self.bot.db_main.read(query, (self.bot.beta, number)) as query_results:
            return query_results

    async def db_get_participants_count(self) -> int:
        "Get the number of users who have at least 1 event point"
        if not self.bot.database_online:
            return 0
        query = "SELECT COUNT(*) as count FROM `event_points` WHERE `points` > 0 AND `beta` = %s;"
        async with self.bot.db_main.read(query, (self.bot.beta,), fetchone=True) as query_results:
            return query_results["count"]

    async def db_get_event_rank(self, user_id: int) -> DBUserRank | None:
        "Get the ranking of a user"
        if not self.bot.database_online:
            return None
        query = "SELECT `user_id`, `points`, FIND_IN_SET( `points`, \
            ( SELECT GROUP_CONCAT( `points` ORDER BY `points` DESC ) FROM `event_points` WHERE `beta` = %(beta)s ) ) AS rank \
                FROM `event_points` WHERE `user_id` = %(user)s AND `beta` = %(beta)s"
        async with self.bot.db_main.read(query, {"user": user_id, "beta": self.bot.beta}, fetchone=True) as query_results:
            return query_results or None

    async def db_get_user_collected_items(self, user_id: int, event_type: EventType) -> list[EventItemWithCount]:
        "Get the items collected by a user"
        if not self.bot.database_online:
            return []
        query = """SELECT COUNT(*) AS 'count', a.*
        FROM `event_collected_items` c LEFT JOIN `event_available_items` a ON c.`item_id` = a.`item_id`
        WHERE c.`user_id` = %s
            AND c.`beta` = %s
            AND a.`event_type` = %s
        GROUP BY c.`item_id`"""
        async with self.bot.db_main.read(query, (user_id, self.bot.beta, event_type)) as query_results:
            return query_results

    async def db_get_last_user_collect(self, user_id: int) -> datetime.datetime:
        "Get the last collect datetime from a user"
        if not self.bot.database_online:
            return None
        query = "SELECT `last_collect` FROM `event_points` WHERE `user_id` = %s AND `beta` = %s;"
        async with self.bot.db_main.read(query, (user_id, self.bot.beta), fetchone=True, astuple=True) as query_result:
            if not query_result:
                return None
            query_result: tuple[datetime.datetime]
            if query_result[0] is None:
                return None
            # apply utc offset
            last_collect = query_result[0].replace(tzinfo=datetime.UTC)
        return last_collect

    async def db_add_user_items(self, user_id: int, items_ids: list[int]):
        "Add some items to a user's collection"
        if not self.bot.database_online:
            return
        query = "INSERT INTO `event_collected_items` (`user_id`, `item_id`, `beta`) VALUES " + \
            ", ".join(["(%s, %s, %s)"] * len(items_ids)) + ';'
        async with self.bot.db_main.write(query, [arg for item_id in items_ids for arg in (user_id, item_id, self.bot.beta)]):
            pass

    async def db_add_collect(self, user_id: int, points: int, with_strike: bool):
        """Add collect points to a user, and maybe increase the strike level by 1"""
        if not self.bot.database_online or self.bot.current_event is None:
            return
        if with_strike:
            query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `strike_level`, `beta`) VALUES (%s, %s, 1, %s) \
                ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                    strike_level = strike_level + 1, \
                    last_collect = CURRENT_TIMESTAMP();"
        elif points:
            query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `last_collect`, `beta`) \
                VALUES (%s, %s, CURRENT_TIMESTAMP(), %s) \
                ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                    strike_level = 0, \
                    last_collect = CURRENT_TIMESTAMP();"
        else:
            return
        async with self.bot.db_main.write(query, (user_id, points, self.bot.beta)):
            pass

    async def db_get_event_items(self, event_type: EventType) -> list[EventItem]:
        "Get the items to win during a specific event"
        if not self.bot.database_online:
            return []
        query = "SELECT * FROM `event_available_items` WHERE `event_type` = %s;"
        async with self.bot.db_main.read(query, (event_type, )) as query_results:
            return query_results
