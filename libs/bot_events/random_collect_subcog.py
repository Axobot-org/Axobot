import datetime
from collections import defaultdict
from random import choice, choices, lognormvariate, randint, random
from typing import Any, Literal, Optional

import discord

from libs.bot_classes import Axobot, MyContext
from libs.bot_events import get_events_translations
from libs.bot_events.dict_types import (EventData, EventItem,
                                        EventItemWithCount, EventType)
from libs.formatutils import FormatUtils
from libs.tips import generate_random_tip
from utils import OUTAGE_REASON


class RandomCollectSubcog:
    "Utility class for the BotEvents cog when the event is about collecting random items"

    def __init__(self, bot: Axobot,
                 current_event: Optional[EventType], current_event_data: EventData, current_event_id: Optional[str]):
        self.bot = bot
        self.current_event = current_event
        self.current_event_data = current_event_data
        self.current_event_id = current_event_id

        self.collect_reward = [-8, 25]
        self.collect_cooldown = 60*60 # (1h) time in seconds between 2 collects
        self.collect_max_strike_period = 3600 * 2 # (2h) time in seconds after which the strike level is reset to 0
        self.collect_bonus_per_strike = 1.05 # the amount of points is multiplied by this number for each strike level
        self.translations_data = get_events_translations()

    async def on_message(self, msg: discord.Message):
        "Add random reaction to some messages"
        if self.current_event and (data := self.current_event_data.get("emojis")):
            if not await self._is_fun_enabled(msg):
                # don't react if fun is disabled for this guild
                return
            if random() < data["probability"] and any(trigger in msg.content for trigger in data["triggers"]):
                react = choice(data["reactions_list"])
                await msg.add_reaction(react)


    async def profile_cmd(self, ctx: MyContext, user: discord.User):
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

        if not self.bot.database_online:
            lang = await self.bot._(ctx.channel, '_used_locale')
            reason = OUTAGE_REASON.get(lang, OUTAGE_REASON['en'])
            emb = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
            emb.add_field(name="OUTAGE", value=reason)
            await ctx.send(embed=emb)
            return

        emb = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
        user: discord.User
        emb.set_author(name=user, icon_url=user.display_avatar.replace(static_format="png", size=32))
        for field in await self.generate_user_profile_rank_fields(ctx, lang, user):
            emb.add_field(**field)
        emb.add_field(**await self.generate_user_profile_collection_field(ctx, user))
        await ctx.send(embed=emb)

    async def generate_user_profile_rank_fields(self, ctx: MyContext, lang: Literal["fr", "en"], user: discord.User):
        "Compute the texts to display in the /event profile command"
        user_rank_query = await self.db_get_event_rank(user.id)
        if user_rank_query is None:
            user_rank = await self.bot._(ctx.channel, "bot_events.unclassed")
            points = 0
        else:
            total_ranked = await self.db_get_participants_count()
            if user_rank_query['rank'] <= total_ranked:
                user_rank = f"{user_rank_query['rank']}/{total_ranked}"
            else:
                user_rank = await self.bot._(ctx.channel, "bot_events.unclassed")
            points: int = user_rank_query["points"]
        prices: dict[str, dict[str, str]] = self.translations_data[lang]["events_prices"]
        if self.current_event_id in prices:
            emojis = self.bot.emojis_manager.customs["green_check"], self.bot.emojis_manager.customs["red_cross"]
            prices_list = []
            for price, desc in prices[self.current_event_id].items():
                emoji = emojis[0] if int(price) <= points else emojis[1]
                prices_list.append(f"{emoji}{min(points, int(price))}/{price}: {desc}")
            prices = "\n".join(prices_list)
            objectives_title = await self.bot._(ctx.channel, "bot_events.objectives")
        else:
            prices = ""
            objectives_title = ""

        _points_total = await self.bot._(ctx.channel, "bot_events.points-total")
        _position_global = await self.bot._(ctx.channel, "bot_events.position-global")
        _rank_global = await self.bot._(ctx.channel, "bot_events.leaderboard-global", count=5)

        fields: list[dict[str, Any]] = [
            {"name": objectives_title, "value": prices, "inline": False},
            {"name": _points_total, "value": str(points)},
            {"name": _position_global, "value": user_rank},
        ]
        if top_5 := await self.get_top_5():
            fields.append({"name": _rank_global, "value": top_5, "inline": False})
        return fields

    async def generate_user_profile_collection_field(self, ctx: MyContext, user: discord.User):
        "Compute the texts to display in the /event profile command"
        if ctx.author == user:
            title = await self.bot._(ctx.channel, "bot_events.collection-title.user")
        else:
            title = await self.bot._(ctx.channel, "bot_events.collection-title.other", user=user.display_name)
        items = await self.db_get_user_collected_items(user.id)
        if len(items) == 0:
            if ctx.author == user:
                _empty_collection = await self.bot._(ctx.channel, "bot_events.collection-empty.user")
            else:
                _empty_collection = await self.bot._(ctx.channel, "bot_events.collection-empty.other", user=user.display_name)
            return {"name": title, "value": _empty_collection, "inline": True}
        lang = await self.bot._(ctx.channel, '_used_locale')
        name_key = "french_name" if lang in ("fr", "fr2") else "english_name"
        items.sort(key=lambda item: item["frequency"], reverse=True)
        items_list: list[str] = []
        more_count = 0
        for item in items:
            if len(items_list) >= 32:
                more_count += item['count']
                continue
            item_name = item["emoji"] + " " + item[name_key]
            items_list.append(f"{item_name} x{item['count']}")
        if more_count:
            items_list.append(await self.bot._(ctx.channel, "bot_events.collection-more", count=more_count))
        return {"name": title, "value": "\n".join(items_list), "inline": True}


    async def collect_cmd(self, ctx: MyContext):
        "Get some event points every hour"
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
        seconds_since_last_collect = await self.db_get_seconds_since_last_collect(ctx.author.id)
        can_collect, is_strike = await self.check_user_collect_availability(ctx.author.id, seconds_since_last_collect)
        if not can_collect:
            # cooldown error
            time_remaining = self.collect_cooldown - seconds_since_last_collect
            remaining = await FormatUtils.time_delta(time_remaining, lang=lang)
            txt = await self.bot._(ctx.channel, "bot_events.collect.too-quick", time=remaining)
        else:
            # grant points
            items = await self.get_random_items()
            strike_level = (await self.db_get_user_strike_level(ctx.author.id) + 1) if is_strike else 0
            if len(items) == 0:
                points = randint(*self.collect_reward)
                bonus = 0
            else:
                points = sum(item["points"] for item in items)
                bonus = max(0, await self.adjust_points_to_strike(points, strike_level) - points)
                await self.db_add_user_items(ctx.author.id, [item["item_id"] for item in items])
            txt = await self.generate_collect_message(ctx.channel, items, points + bonus)
            if strike_level and bonus != 0:
                txt += "\n\n" + \
                    await self.bot._(ctx.channel, 'bot_events.collect.strike-bonus', bonus=bonus, level=strike_level+1)
            await self.db_add_collect(ctx.author.id, points + bonus, increase_strike=is_strike)
        # send result
        if ctx.can_send_embed:
            title = self.translations_data[lang]["events_title"][current_event]
            emb = discord.Embed(title=title, description=txt, color=self.current_event_data["color"])
            emb.add_field(**await self.get_random_tip_field(ctx.channel))
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)

    async def generate_collect_message(self, channel, items: list[EventItem], points: int):
        "Generate the message to send after a /collect command"
        items_count = len(items)
        # no item collected
        if items_count == 0:
            if points < 0:
                return await self.bot._(channel, "bot_events.collect.lost-points", points=-points)
            if points == 0:
                return await self.bot._(channel, "bot_events.collect.nothing")
            return await self.bot._(channel, "bot_events.collect.got-points", points=points)
        language = await self.bot._(channel, "_used_locale")
        name_key = "french_name" if language in ("fr", "fr2") else "english_name"
        # 1 item collected
        if items_count == 1:
            item_name = items[0]["emoji"] + " " + items[0][name_key]
            return await self.bot._(channel, "bot_events.collect.got-items", count=1, item=item_name, points=points)
        # more than 1 item
        f_points = str(points) if points <= 0 else "+" + str(points)
        text = await self.bot._(channel, "bot_events.collect.got-items", count=items_count, points=f_points)
        items_group: dict[int, int] = defaultdict(int)
        for item in items:
            items_group[item["item_id"]] += 1
        for item_id, count in items_group.items():
            item = next(item for item in items if item["item_id"] == item_id)
            item_name = item["emoji"] + " " + item[name_key]
            item_points = ('+' if item["points"] >= 0 else '') + str(item["points"] * count)
            text += f"\n**{item_name}** x{count} ({item_points} points)"
        return text

    async def get_random_tip_field(self, channel):
        return {
            "name": await self.bot._(channel, "bot_events.tip-title"),
            "value": await generate_random_tip(self.bot, channel),
            "inline": False
        }

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

    async def check_user_collect_availability(self, user_id: int, seconds_since_last_collect: Optional[int] = None):
        "Check if a user can collect points, and if they are in a strike period"
        if not self.bot.database_online or self.bot.current_event is None:
            return False, False
        if not seconds_since_last_collect:
            seconds_since_last_collect = await self.db_get_seconds_since_last_collect(user_id)
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

    async def get_top_5(self) -> str:
        "Get the list of the 5 users with the most event points"
        top_5 = await self.db_get_event_top(number=5)
        if top_5 is None:
            return await self.bot._(self.bot.get_channel(0), "bot_events.nothing-desc")
        top_5_f: list[str] = []
        for i, row in enumerate(top_5):
            if user := self.bot.get_user(row['user_id']):
                username = user.display_name
            elif user := await self.bot.fetch_user(row['user_id']):
                username = user.display_name
            else:
                username = f"user {row['user_id']}"
            top_5_f.append(f"{i+1}. {username} ({row['points']} points)")
        return "\n".join(top_5_f)

    async def _is_fun_enabled(self, message: discord.Message):
        "Check if fun is enabled in a given context"
        if message.guild is None:
            return True
        if not self.bot.database_online and not message.author.guild_permissions.manage_guild:
            return False
        return await self.bot.get_config(message.guild.id, "enable_fun")

    async def db_get_seconds_since_last_collect(self, user_id: int):
        "Get the last collect datetime from a user"
        if not self.bot.database_online:
            return None
        query = "SELECT `last_collect` FROM `event_points` WHERE `user_id` = %s AND `beta` = %s;"
        async with self.bot.db_query(query, (user_id, self.bot.beta), fetchone=True, astuple=True) as query_result:
            if not query_result:
                return None
            query_result: tuple[datetime.datetime]
            # if no last collect, return a very high number
            if query_result[0] is None:
                return 1e9
            # apply utc offset
            last_collect = query_result[0].replace(tzinfo=datetime.timezone.utc)
        return (self.bot.utcnow() - last_collect).total_seconds()

    async def db_get_user_strike_level(self, user_id: int) -> int:
        "Get the strike level of a user"
        if not self.bot.database_online:
            return 0
        query = "SELECT `strike_level` FROM `event_points` WHERE `user_id` = %s AND `beta` = %s;"
        async with self.bot.db_query(query, (user_id, self.bot.beta), fetchone=True) as query_result:
            return query_result["strike_level"] if query_result else 0

    async def db_get_event_rank(self, user_id: int):
        "Get the ranking of a user"
        if not self.bot.database_online:
            return None
        query = "SELECT `user_id`, `points`, FIND_IN_SET( `points`, \
            ( SELECT GROUP_CONCAT( `points` ORDER BY `points` DESC ) FROM `event_points` WHERE `beta` = %(beta)s ) ) AS rank \
                FROM `event_points` WHERE `user_id` = %(user)s AND `beta` = %(beta)s"
        async with self.bot.db_query(query, {'user': user_id, 'beta': self.bot.beta}, fetchone=True) as query_results:
            return query_results or None

    async def db_get_participants_count(self) -> int:
        "Get the number of users who have at least 1 event point"
        if not self.bot.database_online:
            return 0
        query = "SELECT COUNT(*) as count FROM `event_points` WHERE `points` > 0 AND `beta` = %s;"
        async with self.bot.db_query(query, (self.bot.beta,), fetchone=True) as query_results:
            return query_results['count']

    async def db_get_event_top(self, number: int):
        "Get the event points leaderboard containing at max the given number of users"
        if not self.bot.database_online:
            return None
        query = "SELECT `user_id`, `points` FROM `event_points` WHERE `points` != 0 AND `beta` = %s \
            ORDER BY `points` DESC LIMIT %s"
        async with self.bot.db_query(query, (self.bot.beta, number)) as query_results:
            return query_results

    async def db_get_user_collected_items(self, user_id: int) -> list[EventItemWithCount]:
        "Get the items collected by a user"
        if not self.bot.database_online:
            return []
        query = """SELECT COUNT(*) AS 'count', a.*
        FROM `event_collected_items` c LEFT JOIN `event_available_items` a ON c.`item_id` = a.`item_id`
        WHERE c.`user_id` = %s AND c.`beta` = %s
        GROUP BY c.`item_id`"""
        async with self.bot.db_query(query, (user_id, self.bot.beta)) as query_results:
            return query_results

    async def db_add_user_items(self, user_id: int, items_ids: list[int]):
        "Add some items to a user's collection"
        if not self.bot.database_online:
            return
        query = "INSERT INTO `event_collected_items` (`user_id`, `item_id`, `beta`) VALUES " + \
            ", ".join(["(%s, %s, %s)"] * len(items_ids)) + ';'
        async with self.bot.db_query(query, [arg for item_id in items_ids for arg in (user_id, item_id, self.bot.beta)]):
            pass

    async def db_get_event_items(self, event_type: EventType) -> list[EventItem]:
        "Get the items to win during a specific event"
        if not self.bot.database_online:
            return []
        query = "SELECT * FROM `event_available_items` WHERE `event_type` = %s;"
        async with self.bot.db_query(query, (event_type, )) as query_results:
            return query_results

    async def db_add_collect(self, user_id: int, points: int, increase_strike: bool):
        """Add collect points to a user
        if increase_strike is True, the strike level will be increased by 1, else it will be reset to 0"""
        try:
            if not self.bot.database_online or self.bot.current_event is None:
                return True
            if increase_strike:
                query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `strike_level`, `beta`) VALUES (%s, %s, 1, %s) \
                    ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                        strike_level = strike_level + 1, \
                        last_collect = CURRENT_TIMESTAMP();"
            else:
                query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `beta`) VALUES (%s, %s, %s) \
                    ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                        strike_level = 0, \
                        last_collect = CURRENT_TIMESTAMP();"
            async with self.bot.db_query(query, (user_id, points, self.bot.beta)):
                pass
            if cog := self.bot.get_cog("BotEvents"):
                try:
                    await cog.reload_event_rankcard(user_id)
                    await cog.reload_event_special_role(user_id)
                except Exception as err:
                    self.bot.dispatch("error", err)
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False
