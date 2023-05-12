import datetime
import json
import random
from random import randint
from typing import Optional, Union

import discord
from discord.ext import commands

from fcts.checks import is_fun_enabled, database_connected
from libs.bot_classes import Axobot, MyContext
from libs.bot_events import EventData, EventType
from libs.formatutils import FormatUtils
from utils import OUTAGE_REASON

translations_data = {
    "fr": {
        "events-desc": {
            "april-2021": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, un avatar unique ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`",
            "april-2022": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, des commandes uniques ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`",
            "halloween-2022": "Le mois d'octobre est là ! Profitez jusqu'au 1er novembre d'une atmosphère ténébreuse, remplie de chauve-souris, de squelettes et de citrouilles.\nProfitez-en pour redécorer votre serveur aux couleurs d'Halloween avec la commande `halloween lightfy` et ses dérivées, vérifiez que votre avatar soit bien conforme avec la commande `halloween check`, et récupérez des points d'événements toutes les heures avec la commande `halloween collect`.\n\nLes plus courageux d'entre vous réussirons peut-être à débloquer la carte d'xp spécial Halloween 2022, que vous pourrez utiliser via la commande profile card !",
            "christmas-2022": "La période des fêtes de fin d'année est là ! C'est l'occasion rêvée de retrouver ses amis et sa famille, de partager de bons moments ensemble, et de s'offrir tout plein de somptueux cadeaux !\n\nPour cet événement de rassemblement, nulle compétition, il vous suffit d'utiliser la commande `event collect` pour récupérer votre carte d'XP spécial Noël 2022 !\nVous pourrez ensuite utiliser cette carte d'XP via la commande `profile card`.\n\nBonne fêtes de fin d'année à tous !",
            "blurple-2023": "Nous célébrons en ce moment le 8e anniversaire de Discord ! Pour l'occasion, Axobot se met aux couleurs de Discord, le célèbre blurple, et vous propose de récupérer une carte d'XP spéciale anniversaire !\n\nPour cela, il vous suffit de récupérer des points d'événements, en utilisant la commande `event collect` régulièrement ou en redécorant votre serveur avec la commande `blurple`.\n\nJoyeux anniversaire Discord !",
            "test-2022": "Test event!"
        },
        "events-prices": {
            "april-2021": {
                "120": "Débloquez la carte d'xp multicolore, obtenable qu'un seul jour par an !"
            },
            "april-2022": {
                "200": "Débloquez la carte d'xp sous-marine, obtenable pendant seulement 24h !"
            },
            "halloween-2022": {
                "300": "Débloquez la carte d'xp halloween 2022, obtenable uniquement pendant cet événement !",
                "600": "Venez réclamer votre rôle spécial Halloween 2022 sur le serveur officiel de Zbot !"
            },
            "blurple-2023": {
                "300": "Débloquez la carte d'xp blurple 2023, obtenable uniquement pendant cet événement !",
                "600": "Venez réclamer votre rôle spécial blurple 2023 sur le serveur officiel d'Axobot !"
            }
        },
        "events-title": {
            "april-2021": "Joyeux 1er avril !",
            "april-2022": "Joyeux 1er avril !",
            "halloween-2022": "Le temps des citrouilles est arrivé !",
            "christmas-2022": "Joyeuses fêtes de fin d'année !",
            "blurple-2023": "Joyeux anniversaire Discord !",
            "test-2022": "Test event!"
        }
    },
    "en": {
        "events-desc": {
            "april-2021": "Today is International Fish Day! All day long, Zbot will be celebrating April 1st with special tic-tac-toe emojis, a unique avatar and other cool stuff. \nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command",
            "april-2022": "Today is International Fish Day! Throughout the day, Zbot will be celebrating April 1 with special tic-tac-toe emojis, unique commands and other cool stuff. \n\nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command",
            "halloween-2022": "October is here! Enjoy a dark atmosphere full of bats, skeletons and pumpkins until November 1st.\nTake the opportunity to redecorate your server in Halloween colors with the `halloween lightfy` command and its derivatives, check your avatar with the `halloween check` command, and collect event points every hour with the `halloween collect` command.\n\nThe most courageous among you may succeed in unlocking the special Halloween 2022 xp card, which you can use via the profile card command!",
            "christmas-2022": "The holiday season is here! It's the perfect opportunity to get together with friends and family, share good times together, and get all sorts of wonderful gifts!\n\nFor this gathering event, no competition, just use the `event collect` command to get your Christmas 2022 XP card!\nYou can then use this XP card via the `profile card` command.\n\nMerry Christmas to all!",
            "blurple-2023": "We are currently celebrating Discord's 8th anniversary! For the occasion, Axobot is turning Discord's famous blurple color, and offers you to get a special anniversary XP card!\n\nTo do so, all you have to do is collect event points, by using the `event collect` command regularly or by redecorating your server with the `blurple` command.\n\nHappy birthday Discord!",
            "test-2022": "Test event!"
        },
        "events-prices": {
            "april-2021": {
                "120": "Unlock the rainbow xp card, obtainable only one day a year!"
            },
            "april-2022": {
                "200": "Unlock the submarine xp card, obtainable only for 24h!"
            },
            "halloween-2022": {
                "300": "Unlock the Halloween 2022 xp card, obtainable only during this event!",
                "600": "Come claim your special Halloween 2022 role on the official Zbot server!"
            },
            "blurple-2023": {
                "300": "Unlock the blurple 2023 xp card, obtainable only during this event!",
                "600": "Come claim your special blurple 2023 role on the official Axobot server!"
            }
        },
        "events-title": {
            "april-2021": "Happy April 1st!",
            "april-2022": "Happy April 1st!",
            "halloween-2022": "It's pumpkin time!",
            "christmas-2022": "Merry Christmas!",
            "blurple-2023": "Happy birthday Discord!",
            "test-2022": "Test event!"
        }
    }
}

class BotEvents(commands.Cog):
    "Cog related to special bot events (like Halloween and Christmas)"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_events"
        self.hourly_reward = [-10, 50]
        self.hourly_cooldown = 3600
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

    async def get_specific_objectives(self, reward_type: str):
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
        events_desc = translations_data[lang]['events-desc']

        if current_event in events_desc:
            event_desc = events_desc[current_event]
            # Title
            try:
                title = translations_data[lang]['events-title'][current_event]
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
                prices = translations_data[lang]['events-prices']
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
        events_desc = translations_data[lang]['events-desc']

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
                points: int = user_rank_query["events_points"]
            prices: dict[str, dict[str, str]] = translations_data[lang]['events-prices']
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
        events_desc = translations_data[lang]['events-desc']
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
        last_data = await self.db_get_dailies(ctx.author.id)
        if last_data is None or (self.bot.utcnow() - last_data['last_update']).total_seconds() > self.hourly_cooldown:
            # grant points
            points = randint(*self.hourly_reward)
            await self.db_add_user_points(ctx.author.id, points)
            await self.db_add_dailies(ctx.author.id, points)
            if points > 0:
                txt = await self.bot._(ctx.channel, "bot_events.collect.got-points", pts=points)
            else:
                txt = await self.bot._(ctx.channel, "bot_events.collect.lost-points", pts=points)
        else:
            # cooldown error
            time_since_available = (self.bot.utcnow() - last_data['last_update']).total_seconds()
            time_remaining = self.hourly_cooldown - time_since_available
            lang = await self.bot._(ctx.channel, '_used_locale')
            remaining = await FormatUtils.time_delta(time_remaining, lang=lang)
            txt = await self.bot._(ctx.channel, "bot_events.collect.too-quick", time=remaining)
        # send result
        if ctx.can_send_embed:
            title = translations_data[lang]['events-title'][current_event]
            emb = discord.Embed(title=title, description=txt, color=self.current_event_data["color"])
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)

    async def get_top_5(self) -> str:
        "Get the list of the 5 users with the most event points"
        top_5 = await self.db_get_event_top(number=5)
        if top_5 is None:
            return await self.bot._(self.bot.get_channel(0), "bot_events.nothing-desc")
        top_5_f: list[str] = []
        for i, row in enumerate(top_5):
            if user := self.bot.get_user(row['userID']):
                username = user.name
            elif user := await self.bot.fetch_user(row['userID']):
                username = user.name
            else:
                username = f"user {row['userID']}"
            top_5_f.append(f"{i+1}. {username} ({row['events_points']} points)")
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
            points = 0 if (points is None) else points["events_points"]
        for reward in rewards:
            if reward["rank_card"] not in cards and points >= reward["points"]:
                await users_cog.set_rankcard(user, reward["rank_card"], True)

    async def db_add_dailies(self, userid: int, points: int):
        "Add dailies points to a user"
        query = "INSERT INTO `dailies` (`userID`,`points`) VALUES (%(u)s,%(p)s) ON DUPLICATE KEY UPDATE points = points + %(p)s;"
        async with self.bot.db_query(query, {'u': userid, 'p': points}):
            pass

    async def db_get_dailies(self, userid: int) -> Optional[dict]:
        "Get dailies info about a user"
        query = "SELECT * FROM `dailies` WHERE userid = %(u)s;"
        async with self.bot.db_query(query, {'u': userid}) as query_results:
            if not query_results:
                return None
            result = query_results[0]
            # apply utc offset
            result['first_update'] = result['first_update'].replace(tzinfo=datetime.timezone.utc)
            result['last_update'] = result['last_update'].replace(tzinfo=datetime.timezone.utc)
            return query_results[0] if len(query_results) > 0 else None

    async def db_get_event_rank(self, user_id: int):
        "Get the ranking of a user"
        if not self.bot.database_online:
            return None
        query = (
            "SELECT `userID`, `events_points`, FIND_IN_SET( `events_points`, ( SELECT GROUP_CONCAT( `events_points` ORDER BY `events_points` DESC ) FROM `users` ) ) AS rank FROM `users` WHERE `userID` = %s")
        async with self.bot.db_query(query, (user_id,), fetchone=True) as query_results:
            return query_results

    async def db_get_event_top(self, number: int):
        "Get the event points leaderboard containing at max the given number of users"
        if not self.bot.database_online:
            return None
        query = "SELECT `userID`, `events_points` FROM `users` WHERE `events_points` != 0 ORDER BY `events_points` DESC LIMIT %s"
        async with self.bot.db_query(query, (number,)) as query_results:
            return query_results

    async def db_get_participants_count(self) -> int:
        if not self.bot.database_online:
            return 0
        query = "SELECT COUNT(*) as count FROM `users` WHERE events_points > 0"
        async with self.bot.db_query(query, fetchone=True) as query_results:
            return query_results['count']

    async def db_add_user_points(self, user_id: int, points: int, check_event: bool = True):
        "Add some events points to a user"
        try:
            if not self.bot.database_online:
                return True
            if check_event and self.bot.current_event is None:
                return True
            query = "INSERT INTO `users` (`userID`,`events_points`) VALUES (%s, %s) ON DUPLICATE KEY UPDATE events_points = events_points + VALUE(`events_points`);"
            async with self.bot.db_query(query, (user_id, points)):
                pass
            try:
                await self.reload_event_rankcard(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False

    async def db_set_user_points(self, user_id: int, points: int, check_event: bool = True):
        "Set the events points of a user"
        try:
            if not self.bot.database_online:
                return True
            if check_event and self.bot.current_event is None:
                return True
            query = "INSERT INTO `users` (`userID`,`events_points`) VALUES (%s, %s) ON DUPLICATE KEY UPDATE events_points = VALUE(`event_points`);"
            async with self.bot.db_query(query, (user_id, points)):
                pass
            try:
                await self.reload_event_rankcard(user_id)
            except Exception as err:
                self.bot.dispatch("error", err)
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False


async def setup(bot):
    await bot.add_cog(BotEvents(bot))
