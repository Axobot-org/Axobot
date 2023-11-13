import datetime
import json
from typing import Literal, Optional, Union

import discord
from discord.ext import commands, tasks

from libs.bot_classes import SUPPORT_GUILD_ID, Axobot, MyContext
from libs.bot_events import (AbstractSubcog, ChristmasSubcog, EventData,
                             EventRewardRole, EventType)
from libs.checks.checks import database_connected


class BotEvents(commands.Cog):
    "Cog related to special bot events (like Halloween and Christmas)"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_events"

        self.current_event: Optional[EventType] = None
        self.current_event_data: EventData = {}
        self.current_event_id: Optional[str] = None

        self.coming_event: Optional[EventType] = None
        self.coming_event_data: EventData = {}
        self.coming_event_id: Optional[str] = None
        self.update_current_event()

        self._subcog: AbstractSubcog = ChristmasSubcog(
            self.bot, self.current_event, self.current_event_data, self.current_event_id)

    @property
    def subcog(self) -> AbstractSubcog:
        "Return the subcog populated with the current event data"
        if self._subcog.current_event != self.current_event or self._subcog.current_event_data != self.current_event_data:
            self.bot.log.info("[BotEvents] Updating subcog with new data")
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
                self.bot.log.info("Current bot event: %s", ev_id)
                break
            if ev_data["begin"] - datetime.timedelta(days=5) <= now < ev_data["begin"]:
                self.coming_event = ev_data["type"]
                self.coming_event_data = ev_data
                self.coming_event_id = ev_id
                self.bot.log.info("Incoming bot event: %s", ev_id)

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
        datetime.time(hour=0,  tzinfo=datetime.timezone.utc),
        datetime.time(hour=12, tzinfo=datetime.timezone.utc),
    ])
    async def _update_event_loop(self):
        "Refresh the current bot event every 12h"
        self.update_current_event()
        event = self.bot.get_cog("BotEvents").current_event
        emb = discord.Embed(
            description=f'**Bot event** updated (current event is {event})',
            color=1406147, timestamp=self.bot.utcnow()
        )
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
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
        if msg.guild and await self.bot.check_axobot_presence(guild=msg.guild):
            # If axobot is already there, don't do anything
            return
        if self.current_event:
            await self.subcog.on_message(msg)

    @commands.hybrid_group("event", aliases=["botevents", "botevent", "events"])
    @commands.check(database_connected)
    async def events_main(self, ctx: MyContext):
        """Participate in bot special events!"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @events_main.command(name="info")
    @commands.check(database_connected)
    async def event_info(self, ctx: MyContext):
        """Get info about the current event"""
        current_event = self.current_event_id
        lang = await self.bot._(ctx.channel, '_used_locale')
        lang = 'en' if lang not in ('en', 'fr') else lang
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
                prices = self.subcog.translations_data[lang]["events_prices"]
                if current_event in prices:
                    points = await self.bot._(ctx.channel, "bot_events.points")
                    prices = [f"- **{k} {points}:** {v}" for k,
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

    @events_main.command(name="profile")
    @commands.check(database_connected)
    async def event_profile(self, ctx: MyContext, user: discord.User = None):
        """Take a look at your progress in the event and your global ranking
        Event points are reset after each event"""
        if user is None:
            user = ctx.author
        await self.subcog.profile_cmd(ctx, user)

    @events_main.command(name="collect")
    @commands.check(database_connected)
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def event_collect(self, ctx: MyContext):
        "Get some event points every hour"
        await self.subcog.collect_cmd(ctx)

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
            points = await self.subcog.db_get_event_rank(user.id)
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
        user_id = user if isinstance(user, int) else user.id
        if (member := support_guild.get_member(user_id)) is None:
            return
        if points is None:
            points = await self.subcog.db_get_event_rank(user_id)
            points = 0 if (points is None) else points["points"]
        for reward in rewards:
            if points >= reward["points"]:
                await member.add_roles(discord.Object(reward["role_id"]))

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
