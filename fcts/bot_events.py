import datetime
import json
from random import randint
from typing import Optional

import discord
from discord.ext import commands
from libs.classes import MyContext, Zbot
from libs.formatutils import FormatUtils

data = {
    "fr": {
        "events-desc": {
            "april-2021": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, un avatar unique ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`",
            "april-2022": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, des commandes uniques ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`"
        },
        "events-prices": {
            "april-2021": {
                "120": "Débloquez la carte d'xp multicolore, obtenable qu'un seul jour par an !"
            },
            "april-2022": {
                "200": "Débloquez la carte d'xp sous-marine, obtenable pendant seulement 24h !"
            }
        },
        "events-title": {
            "april-2021": "Joyeux 1er avril !",
            "april-2022": "Joyeux 1er avril !"
        }
    },
    "en": {
        "events-desc": {
            "april-2021": "Today is International Fish Day! All day long, Zbot will be celebrating April 1st with special tic-tac-toe emojis, a unique avatar and other cool stuff. \nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command",
            "april-2022": "Today is International Fish Day! Throughout the day, Zbot will be celebrating April 1 with special tic-tac-toe emojis, unique commands and other cool stuff. \n\nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command"
        },
        "events-prices": {
            "april-2021": {
                "120": "Unlock the rainbow xp card, obtainable only one day a year!"
            },
            "april-2022": {
                "200": "Unlock the submarine xp card, obtainable only for 24h!"
            }
        },
        "events-title": {
            "april-2021": "Happy April 1st!",
            "april-2022": "Happy April 1st!"
        }
    }
}

class BotEvents(commands.Cog):
    "Cog related to special bot events (like Halloween and Christmas)"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "bot_events"
        self.hourly_reward = [-10, 60]
        self.current_event: str = None
        self.current_event_data: dict = {}
        self.current_event_id: str = None

        self.coming_event: str = None
        self.coming_event_data: dict = {}
        self.coming_event_id: str = None
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
            if ev_data["begin"] - datetime.timedelta(days=1) <= now < ev_data["begin"]:
                self.coming_event = ev_data["type"]
                self.coming_event_data = ev_data
                self.coming_event_id = ev_id

    @commands.group(name="events", aliases=["botevents", "botevent", "event"])
    async def events_main(self, ctx: MyContext):
        """When I'm organizing some events"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['events'])

    @events_main.command(name="info")
    async def event_info(self, ctx: MyContext):
        """Get info about the current event"""
        current_event = self.current_event_id
        lang = await self.bot._(ctx.channel, '_used_locale')
        lang = 'en' if lang not in ('en', 'fr') else lang
        events_desc = data[lang]['events-desc']

        if current_event in events_desc:
            event_desc = events_desc[current_event]
            # Title
            try:
                title = data[lang]['events-title'][current_event]
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
                prices = data[lang]['events-prices']
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

    @events_main.command(name="rank")
    async def events_rank(self, ctx: MyContext, user: discord.User = None):
        """Watch how many xp you already have
        Events points are reset after each event"""
        current_event = self.current_event_id
        lang = await self.bot._(ctx.channel, '_used_locale')
        lang = 'en' if lang not in ('en', 'fr') else lang
        events_desc = data[lang]['events-desc']

        if not current_event in events_desc:
            await ctx.send(await self.bot._(ctx.channel, "bot_events.nothing-desc"))
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
                user_rank = "{}/{}".format(
                    user_rank_query['rank'], total_ranked)
            else:
                user_rank = await self.bot._(ctx.channel, "bot_events.unclassed")
            points = user_rank_query["events_points"]
        title = await self.bot._(ctx.channel, "bot_events.rank-title")
        prices: dict = data[lang]['events-prices']
        if current_event in prices:
            emojis = self.bot.get_cog("Emojis").customs["green_check"], self.bot.get_cog("Emojis").customs["red_cross"]
            p = []
            for k, v in prices[current_event].items():
                emoji = emojis[0] if int(k) <= points else emojis[1]
                p.append(f"{emoji}{min(points,int(k))}/{k}: {v}")
            prices = "\n".join(p)
            objectives_title = await self.bot._(ctx.channel, "bot_events.objectives")
        else:
            prices = ""
            objectives_title = ""
        rank_total = await self.bot._(ctx.channel, "bot_events.rank-total")
        rank_global = await self.bot._(ctx.channel, "bot_events.rank-global")

        if ctx.can_send_embed:
            desc = await self.bot._(ctx.channel, "bot_events.xp-howto")
            emb = discord.Embed(title=title, description=desc, color=4254055)
            user: discord.User
            emb.set_author(name=user, icon_url=user.display_avatar.replace(static_format="png", size=32))
            if objectives_title != "":
                emb.add_field(name=objectives_title, value=prices, inline=False)
            emb.add_field(name=rank_total, value=str(points))
            emb.add_field(name=rank_global, value=user_rank)
            await ctx.send(embed=emb)
        else:
            msg = f"**{title}** ({user})"
            if objectives_title != "":
                msg += f"\n\n__{objectives_title}:__\n{prices}"
            msg += f"\n\n__{rank_total}:__ {points}\n__{rank_global}:__ {user_rank}"
            await ctx.send(msg)


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


def setup(bot):
    bot.add_cog(BotEvents(bot))
