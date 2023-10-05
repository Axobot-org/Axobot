import datetime
import json
import random
from random import randint
from typing import Literal, Optional, Union

import discord
from discord.ext import commands

from libs.bot_classes import SUPPORT_GUILD_ID, Axobot, MyContext
from libs.bot_events import (EventData, EventRewardRole, EventType,
                             get_events_translations)
from libs.checks.checks import database_connected, is_fun_enabled
from libs.formatutils import FormatUtils
from utils import OUTAGE_REASON


class BotEvents(commands.Cog):
    "Cog related to special bot events (like Halloween and Christmas)"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_events"
        self.collect_reward = [-5, 25]
        self.collect_cooldown = 3600
        self.collect_max_strike_period = 3600 * 2
        self.collect_bonus_per_strike = 1.1
        self.translations_data = get_events_translations()

        self.current_event: Optional[EventType] = None
        self.current_event_data: EventData = {}
        self.current_event_id: Optional[str] = None

        self.coming_event: Optional[EventType] = None
        self.coming_event_data: EventData = {}
        self.coming_event_id: Optional[str] = None
        self.update_current_event()

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
        with open("events-list.json", 'r', encoding='utf-8') as file:
            events = json.load(file)
        self.reset()
        for ev_id, ev_data in events.items():
            ev_data["begin"] = datetime.datetime.strptime(
                ev_data["begin"], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
            ev_data["end"] = datetime.datetime.strptime(
                ev_data["end"], "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)

            if ev_data["begin"] <= now < ev_data["end"]:
                self.current_event = ev_data["type"]
                self.current_event_data = ev_data
                self.current_event_id = ev_id
                break
            if ev_data["begin"] - datetime.timedelta(days=5) <= now < ev_data["begin"]:
                self.coming_event = ev_data["type"]
                self.coming_event_data = ev_data
                self.coming_event_id = ev_id

    async def get_specific_objectives(self, reward_type: Literal["rankcard", "role", "custom"]):
        "Get all objectives matching a certain reward type"
        if self.current_event_id is None:
            return []
        return [
            objective
            for objective in self.current_event_data["objectives"]
            if objective["reward_type"] == reward_type
            ]

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        "Add a random reaction to specific messages if an event is active"
        if self.bot.zombie_mode or msg.author.bot:
            # don't react if zombie mode is enabled or of it's a bot
            return
        if msg.guild is not None and not msg.channel.permissions_for(msg.guild.me).add_reactions:
            # don't react if we don't have the required permission
            return
        if msg.guild and await self.bot.check_axobot_presence(guild=msg.guild):
            # If axobot is already there, don't do anything
            return
        if self.current_event and (data := self.current_event_data.get("emojis")):
            if not await is_fun_enabled(msg):
                # don't react if fun is disabled for this guild
                return
            if random.random() < data["probability"] and any(trigger in msg.content for trigger in data["triggers"]):
                react = random.choice(data["reactions_list"])
                await msg.add_reaction(react)

    @commands.group(name="events", aliases=["botevents", "botevent", "event"])
    @commands.check(database_connected)
    async def events_main(self, ctx: MyContext):
        """When I'm organizing some events"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @events_main.command(name="info")
    @commands.check(database_connected)
    async def event_info(self, ctx: MyContext):
        """Get info about the current event"""
        current_event = self.current_event_id
        lang = await self.bot._(ctx.channel, '_used_locale')
        lang = 'en' if lang not in ('en', 'fr') else lang
        events_desc = self.translations_data[lang]["events_desc"]

        if current_event in events_desc:
            event_desc = events_desc[current_event]
            # Title
            try:
                title = self.translations_data[lang]["events_title"][current_event]
            except KeyError:
                title = self.current_event
            # Begin/End dates
            begin = f"<t:{self.current_event_data['begin'].timestamp():.0f}>"
            end = f"<t:{self.current_event_data['end'].timestamp():.0f}>"
            if ctx.can_send_embed:
                emb = discord.Embed(title=title, description=event_desc, color=self.current_event_data["color"])
                if self.current_event_data["icon"]:
                    emb.set_image(url=self.current_event_data["icon"])
                emb.add_field(
                    name=(await self.bot._(ctx.channel, "misc.beginning")).capitalize(),
                    value=begin
                )
                emb.add_field(
                    name=(await self.bot._(ctx.channel, "misc.end")).capitalize(),
                    value=end
                )
                # Prices to win
                prices = self.translations_data[lang]["events_prices"]
                if current_event in prices:
                    points = await self.bot._(ctx.channel, "bot_events.points")
                    prices = [f"**{k} {points}:** {v}" for k,
                              v in prices[current_event].items()]
                    emb.add_field(
                        name=await self.bot._(ctx.channel, "bot_events.events-price-title"),
                        value="\n".join(prices),
                        inline=False
                    )
                await ctx.send(embed=emb)
            else:
                txt = f"""**{title}**\n\n{event_desc}

                __{(await self.bot._(ctx.channel, "misc.beginning")).capitalize()}:__ {begin}
                __{(await self.bot._(ctx.channel, "misc.end")).capitalize()}:__ {end}
                """
                await ctx.send(txt)
        elif self.coming_event_data:
            date = f"<t:{self.coming_event_data['begin'].timestamp():.0f}>"
            await ctx.send(await self.bot._(ctx.channel, "bot_events.soon", date=date))
        else:
            await ctx.send(await self.bot._(ctx.channel, "bot_events.nothing-desc"))
            if current_event:
                self.bot.dispatch("error", ValueError(f"'{current_event}' has no event description"), ctx)

    @events_main.command(name="rank")
    @commands.check(database_connected)
    async def events_rank(self, ctx: MyContext, user: discord.User = None):
        """Watch how many xp you already have
        Events points are reset after each event"""
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

        if user is None:
            user = ctx.author

        if self.bot.database_online:
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
            if current_event in prices:
                emojis = self.bot.emojis_manager.customs["green_check"], self.bot.emojis_manager.customs["red_cross"]
                prices_list = []
                for price, desc in prices[current_event].items():
                    emoji = emojis[0] if int(price) <= points else emojis[1]
                    prices_list.append(f"{emoji}{min(points, int(price))}/{price}: {desc}")
                prices = "\n".join(prices_list)
                objectives_title = await self.bot._(ctx.channel, "bot_events.objectives")
            else:
                prices = ""
                objectives_title = ""
            _rank_total = await self.bot._(ctx.channel, "bot_events.rank-total")
            _position_global = await self.bot._(ctx.channel, "bot_events.position-global")
            _rank_global = await self.bot._(ctx.channel, "bot_events.leaderboard-global", count=5)

        title = await self.bot._(ctx.channel, "bot_events.rank-title")
        if ctx.can_send_embed:
            desc = await self.bot._(ctx.channel, "bot_events.xp-howto")
            emb = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
            user: discord.User
            emb.set_author(name=user, icon_url=user.display_avatar.replace(static_format="png", size=32))
            if self.bot.database_online:
                if objectives_title != "":
                    emb.add_field(name=objectives_title, value=prices, inline=False)
                emb.add_field(name=_rank_total, value=str(points))
                emb.add_field(name=_position_global, value=user_rank)
                if top_5 := await self.get_top_5():
                    emb.add_field(name=_rank_global, value=top_5, inline=False)
            else:
                lang = await self.bot._(ctx.channel, '_used_locale')
                reason = OUTAGE_REASON.get(lang, OUTAGE_REASON['en'])
                emb.add_field(name="OUTAGE", value=reason)
            await ctx.send(embed=emb)
        else:
            msg = f"**{title}** ({user})"
            if self.bot.database_online:
                if objectives_title != "":
                    msg += f"\n\n__{objectives_title}:__\n{prices}"
                msg += f"\n\n__{_rank_total}:__ {points}\n__{_rank_global}:__ {user_rank}"
            await ctx.send(msg)

    @events_main.command(name="collect")
    @commands.check(database_connected)
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def event_collect(self, ctx: MyContext):
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
        # check last collect from this user
        seconds_since_last_collect = await self.db_get_seconds_since_last_collect(ctx.author.id)
        can_collect, is_strike = await self.check_user_collect_availability(ctx.author.id, seconds_since_last_collect)
        if can_collect:
            # grant points
            strike_level = await self.db_get_user_strike_level(ctx.author.id)
            points = await self.get_random_points(strike_level)
            await self.db_add_collect(ctx.author.id, points, increase_strike=is_strike)
            if points > 0:
                txt = await self.bot._(ctx.channel, "bot_events.collect.got-points", pts=points)
            else:
                txt = await self.bot._(ctx.channel, "bot_events.collect.lost-points", pts=-points)
            if is_strike:
                txt += '\n' + await self.bot._(ctx.channel, "bot_events.collect.strike", level=strike_level+1)
        else:
            # cooldown error
            time_remaining = self.collect_cooldown - seconds_since_last_collect
            lang = await self.bot._(ctx.channel, '_used_locale')
            remaining = await FormatUtils.time_delta(time_remaining, lang=lang)
            txt = await self.bot._(ctx.channel, "bot_events.collect.too-quick", time=remaining)
        # send result
        if ctx.can_send_embed:
            title = self.translations_data[lang]["events_title"][current_event]
            emb = discord.Embed(title=title, description=txt, color=self.current_event_data["color"])
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)

    async def get_random_points(self, strike_level: int):
        "Get a random amount of points for the /collect command, depending on the strike level"
        strike_coef = self.collect_bonus_per_strike ** strike_level
        min_points = int(self.collect_reward[0] * strike_coef)
        max_points = int(self.collect_reward[1] * strike_coef)
        return randint(min_points, max_points)

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

    async def reload_event_rankcard(self, user: Union[discord.User, int], points: int = None):
        """Grant the current event rank card to the provided user, if they have enough points
        'points' argument can be provided to avoid re-fetching the database"""
        if (users_cog := self.bot.get_cog("Users")) is None:
            return
        if self.current_event is None or len(rewards := await self.get_specific_objectives("rankcard")) == 0:
            return
        if isinstance(user, int):
            user = self.bot.get_user(user)
            if user is None:
                return
        cards = await users_cog.get_rankcards(user)
        if points is None:
            points = await self.db_get_event_rank(user.id)
            points = 0 if (points is None) else points["points"]
        for reward in rewards:
            if reward["rank_card"] not in cards and points >= reward["points"]:
                await users_cog.set_rankcard(user, reward["rank_card"], True)
                # send internal log
                embed = discord.Embed(
                    description=f"{user} ({user.id}) has been granted the rank card **{reward['rank_card']}**",
                    color=discord.Color.brand_green()
                )
                await self.bot.send_embed(embed)

    async def reload_event_special_role(self, user: Union[discord.User, int], points: int = None):
        """Grant the current event special role to the provided user, if they have enough points
        'points' argument can be provided to avoid re-fetching the database"""
        if self.current_event is None or len(rewards := await self.get_specific_objectives("role")) == 0:
            return
        rewards: list[EventRewardRole]
        if (support_guild := self.bot.get_guild(SUPPORT_GUILD_ID.id)) is None:
            return
        if (member := support_guild.get_member(user.id)) is None:
            return
        if points is None:
            points = await self.db_get_event_rank(user.id)
            points = 0 if (points is None) else points["points"]
        for reward in rewards:
            if points >= reward["points"]:
                await member.add_roles(discord.Object(reward["role_id"]))


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

    async def db_add_collect(self, user_id: int, points: int, increase_strike: bool):
        """Add collect points to a user
        if increase_strike is True, the strike level will be increased by 1, else it will be reset to 0"""
        try:
            if not self.bot.database_online or self.bot.current_event is None:
                return True
            if increase_strike:
                query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `strike_level`, `beta`) VALUES (%s, %s, 1, %s) \
                    ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                        strike_level = strike_level + 1;"
            else:
                query = "INSERT INTO `event_points` (`user_id`, `collect_points`, `beta`) VALUES (%s, %s, %s) \
                    ON DUPLICATE KEY UPDATE collect_points = collect_points + VALUE(`collect_points`), \
                        strike_level = 0;"
            async with self.bot.db_query(query, (user_id, points, self.bot.beta)):
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

    async def db_get_seconds_since_last_collect(self, user_id: int):
        "Get the last collect datetime from a user"
        if not self.bot.database_online:
            return None
        query = "SELECT `last_update` FROM `event_points` WHERE `user_id` = %s AND `beta` = %s;"
        async with self.bot.db_query(query, (user_id, self.bot.beta), fetchone=True, astuple=True) as query_result:
            if not query_result:
                return None
            query_result: tuple[datetime.datetime]
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
            ( SELECT GROUP_CONCAT( `points` ORDER BY `points` DESC ) FROM `event_points` ) ) AS rank \
                FROM `event_points` WHERE `user_id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (user_id, self.bot.beta), fetchone=True) as query_results:
            return query_results or None

    async def db_get_event_top(self, number: int):
        "Get the event points leaderboard containing at max the given number of users"
        if not self.bot.database_online:
            return None
        query = "SELECT `user_id`, `points` FROM `event_points` WHERE `points` != 0 AND `beta` = %s ORDER BY `points` DESC LIMIT %s"
        async with self.bot.db_query(query, (self.bot.beta, number)) as query_results:
            return query_results

    async def db_get_participants_count(self) -> int:
        "Get the number of users who have at least 1 event point"
        if not self.bot.database_online:
            return 0
        query = "SELECT COUNT(*) as count FROM `event_points` WHERE `points` > 0 AND `beta` = %s;"
        async with self.bot.db_query(query, (self.bot.beta,), fetchone=True) as query_results:
            return query_results['count']

    async def db_add_user_points(self, user_id: int, points: int):
        "Add some 'other' events points to a user"
        try:
            if not self.bot.database_online or self.bot.current_event is None:
                return True
            query = "INSERT INTO `event_points` (`user_id`, `other_points`, `beta`) VALUES (%s, %s, %s) \
                ON DUPLICATE KEY UPDATE other_points = other_points + VALUE(`other_points`);"
            async with self.bot.db_query(query, (user_id, points, self.bot.beta)):
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
