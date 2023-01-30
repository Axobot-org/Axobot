import datetime
import json
from random import randint
import random
from typing import Optional

import discord
from discord.ext import commands
from libs.bot_classes import MyContext, Axobot
from libs.bot_events import EventData, EventType
from libs.formatutils import FormatUtils

from fcts.checks import is_fun_enabled

translations_data = {
    "fr": {
        "events-desc": {
            "april-2021": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, un avatar unique ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`",
            "april-2022": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, des commandes uniques ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`",
            "halloween-2022": "Le mois d'octobre est là ! Profitez jusqu'au 1er novembre d'une atmosphère ténébreuse, remplie de chauve-souris, de squelettes et de citrouilles.\nProfitez-en pour redécorer votre serveur aux couleurs d'Halloween avec la commande `halloween lightfy` et ses dérivées, vérifiez que votre avatar soit bien conforme avec la commande `halloween check`, et récupérez des points d'événements toutes les heures avec la commande `halloween collect`.\n\nLes plus courageux d'entre vous réussirons peut-être à débloquer la carte d'xp spécial Halloween 2022, que vous pourrez utiliser via la commande profile card !",
            "christmas-2022": "La période des fêtes de fin d'année est là ! C'est l'occasion rêvée de retrouver ses amis et sa famille, de partager de bons moments ensemble, et de s'offrir tout plein de somptueux cadeaux !\n\nPour cet événement de rassemblement, nulle compétition, il vous suffit d'utiliser la commande `event collect` pour récupérer votre carte d'XP spécial Noël 2022 !\nVous pourrez ensuite utiliser cette carte d'XP via la commande `profile card`.\n\nBonne fêtes de fin d'année à tous !",
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
            }
        },
        "events-title": {
            "april-2021": "Joyeux 1er avril !",
            "april-2022": "Joyeux 1er avril !",
            "halloween-2022": "Le temps des citrouilles est arrivé !",
            "christmas-2022": "Joyeuses fêtes de fin d'année !",
            "test-2022": "Test event!"
        }
    },
    "en": {
        "events-desc": {
            "april-2021": "Today is International Fish Day! All day long, Zbot will be celebrating April 1st with special tic-tac-toe emojis, a unique avatar and other cool stuff. \nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command",
            "april-2022": "Today is International Fish Day! Throughout the day, Zbot will be celebrating April 1 with special tic-tac-toe emojis, unique commands and other cool stuff. \n\nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command",
            "halloween-2022": "October is here! Enjoy a dark atmosphere full of bats, skeletons and pumpkins until November 1st.\nTake the opportunity to redecorate your server in Halloween colors with the `halloween lightfy` command and its derivatives, check your avatar with the `halloween check` command, and collect event points every hour with the `halloween collect` command.\n\nThe most courageous among you may succeed in unlocking the special Halloween 2022 xp card, which you can use via the profile card command!",
            "christmas-2022": "The holiday season is here! It's the perfect opportunity to get together with friends and family, share good times together, and get all sorts of wonderful gifts!\n\nFor this gathering event, no competition, just use the `event collect` command to get your Christmas 2022 XP card!\nYou can then use this XP card via the `profile card` command.\n\nMerry Christmas to all!",
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
            }
        },
        "events-title": {
            "april-2021": "Happy April 1st!",
            "april-2022": "Happy April 1st!",
            "halloween-2022": "It's pumpkin time!",
            "christmas-2022": "Merry Christmas!",
            "test-2022": "Test event!"
        }
    }
}

class BotEvents(commands.Cog):
    "Cog related to special bot events (like Halloween and Christmas)"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bot_events"
        self.hourly_reward = [-10, 60]
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
            if not await is_fun_enabled(msg, self.bot.get_cog("Fun")):
                # don't react if fun is disabled for this guild
                return
            if random.random() < data["probability"] and any(trigger in msg.content for trigger in data["triggers"]):
                react = random.choice(data["reactions_list"])
                await msg.add_reaction(react)

    @commands.group(name="events", aliases=["botevents", "botevent", "event"])
    async def events_main(self, ctx: MyContext):
        """When I'm organizing some events"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @events_main.command(name="info")
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
        user_rank_query = await self.bot.get_cog("Utilities").get_eventsPoints_rank(user.id)
        if user_rank_query is None:
            user_rank = await self.bot._(ctx.channel, "bot_events.unclassed")
            points = 0
        else:
            total_ranked = await self.bot.get_cog("Utilities").get_eventsPoints_nbr()
            if user_rank_query['rank'] <= total_ranked:
                user_rank = f"{user_rank_query['rank']}/{total_ranked}"
            else:
                user_rank = await self.bot._(ctx.channel, "bot_events.unclassed")
            points: int = user_rank_query["events_points"]
        title = await self.bot._(ctx.channel, "bot_events.rank-title")
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

        if ctx.can_send_embed:
            desc = await self.bot._(ctx.channel, "bot_events.xp-howto")
            emb = discord.Embed(title=title, description=desc, color=self.current_event_data["color"])
            user: discord.User
            emb.set_author(name=user, icon_url=user.display_avatar.replace(static_format="png", size=32))
            if objectives_title != "":
                emb.add_field(name=objectives_title, value=prices, inline=False)
            emb.add_field(name=_rank_total, value=str(points))
            emb.add_field(name=_position_global, value=user_rank)
            emb.add_field(name=_rank_global, value=await self.get_top_5(), inline=False)
            await ctx.send(embed=emb)
        else:
            msg = f"**{title}** ({user})"
            if objectives_title != "":
                msg += f"\n\n__{objectives_title}:__\n{prices}"
            msg += f"\n\n__{_rank_total}:__ {points}\n__{_rank_global}:__ {user_rank}"
            await ctx.send(msg)

    @events_main.command(name="collect")
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def event_collect(self, ctx: MyContext):
        "Collect your Christmas present!"
        if self.current_event_id != "christmas-2022":
            await ctx.send(await self.bot._(ctx.channel, "bot_events.nothing-desc"))
            return
        if (users_cog := self.bot.get_cog("Users")) is None:
            raise RuntimeError("Users cog not found")
        if await users_cog.has_rankcard(ctx.author, "christmas22"):
            await ctx.send(await self.bot._(ctx.channel, "bot_events.christmas.already-collected"))
            return
        await users_cog.set_rankcard(ctx.author, "christmas22")
        profile_cmd = await self.bot.get_command_mention("profile card")
        await ctx.send(await self.bot._(ctx.channel, "bot_events.christmas.collected", cmd=profile_cmd))

    async def get_top_5(self) -> str:
        "Get the list of the 5 users with the most event points"
        top_5 = await self.bot.get_cog("Utilities").get_eventsPoints_top(number=5)
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

    async def db_add_dailies(self, userid: int, points: int):
        "Add dailies points to a user"
        query = "INSERT INTO `dailies` (`userID`,`points`) VALUES (%(u)s,%(p)s) ON DUPLICATE KEY UPDATE points = points + %(p)s;"
        async with self.bot.db_query(query, {'u': userid, 'p': points}):
            pass

    async def db_get_dailies(self, userid: int) -> Optional[dict]:
        "Get dailies info about a user"
        query = "SELECT * FROM `dailies` WHERE userid = %(u)s;"
        async with self.bot.db_query(query, {'u': userid}) as query_results:
            return query_results[0] if len(query_results) > 0 else None

    @commands.command(name="fish")
    async def fish(self, ctx: MyContext):
        "Try to catch a fish and get some event points!"
        if not self.current_event or self.current_event_data['type'] != "fish":
            await ctx.send(await self.bot._(ctx.channel, "bot_events.nothing-desc"))
            return
        last_data = await self.db_get_dailies(ctx.author.id)
        cooldown = 3600/2 # 30min
        time_since_available: int = 0 if last_data is None else (
            datetime.datetime.now() - last_data['last_update']).total_seconds() - cooldown
        if time_since_available >= 0:
            points = randint(*self.hourly_reward)
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, points)
            await self.db_add_dailies(ctx.author.id, points)
            if points >= 0:
                txt = await self.bot._(ctx.channel, "halloween.daily.got-points", pts=points)
            else:
                txt = await self.bot._(ctx.channel, "halloween.daily.lost-points", pts=points)
        else:
            lang = await self.bot._(ctx.channel, '_used_locale')
            remaining = await FormatUtils.time_delta(-time_since_available, lang=lang)
            txt = await self.bot._(ctx.channel, "blurple.collect.too-quick", time=remaining)
        if ctx.can_send_embed:
            title = "Fish event"
            emb = discord.Embed(title=title, description=txt, color=16733391)
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)


async def setup(bot):
    await bot.add_cog(BotEvents(bot))
