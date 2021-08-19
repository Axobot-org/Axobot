import discord
import datetime
import json
from discord.ext import commands
from utils import zbot, MyContext

data = {
    "fr": {
        "events-desc": {
            "april-2021": "Aujourd'hui, c'est la journée internationale des poissons ! Pendant toute la journée, Zbot fêtera le 1er avril avec des émojis spéciaux pour le jeu du morpion, un avatar unique ainsi que d'autres choses trop cool. \n\nProfitez-en pour récupérer des points d'événements et tentez de gagner la carte d'xp rainbow ! Pour rappel, les cartes d'xp sont accessibles via ma commande `profile card`"
        },
        "events-price": {
            "april-2021": {
                "120": "Débloquez la carte d'xp multicolore, obtenable qu'un seul jour par an !"
            }
        },
        "events-title": {
            "april-2021": "Joyeux 1er avril !"
        }
    },
    "en": {
        "events-desc": {
            "april-2021": "Today is International Fish Day! All day long, Zbot will be celebrating April 1st with special tic-tac-toe emojis, a unique avatar and other cool stuff. \nTake the opportunity to collect event points and try to win the rainbow xp card! As a reminder, the xp cards are accessible via my `profile card` command"
        },
        "events-price": {
            "april-2021": {
                "120": "Unlock the rainbow xp card, obtainable only one day a year!"
            }
        },
        "events-title": {
            "april-2021": "Happy April 1st!"
        }
    }
}


class BotEvents(commands.Cog):

    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "bot_events"
        self.current_event: str = None
        self.current_event_data: dict = {}
        self.current_event_id: str = None
        self.updateCurrentEvent()

    def updateCurrentEvent(self):
        today = datetime.date.today()
        with open("events-list.json", 'r') as f:
            events = json.load(f)
        self.current_event = None
        self.current_event_data = {}
        self.current_event_id = None
        for ev_id, ev_data in events.items():
            ev_data["begin"] = datetime.datetime.strptime(
                ev_data["begin"], "%Y-%m-%d")
            ev_data["end"] = datetime.datetime.strptime(
                ev_data["end"], "%Y-%m-%d")
            if ev_data["begin"].date() <= today and ev_data["end"].date() >= today:
                self.current_event = ev_data["type"]
                self.current_event_data = ev_data
                self.current_event_id = ev_id
                break

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
                title = data[lang]['events-title']
            except:
                title = self.current_event
            # Begin/End dates
            nice_date = self.bot.get_cog("TimeUtils").date
            begin = await nice_date(self.current_event_data["begin"], lang, year=True, digital=True, hour=False)
            end = await nice_date(self.current_event_data["end"], lang, year=True, digital=True, hour=False)
            if ctx.can_send_embed:
                fields = [
                    {"name": (await self.bot._(ctx.channel, "misc.beginning")).capitalize(),
                     "value": begin,
                     "inline": True
                     },
                    {"name": (await self.bot._(ctx.channel, "misc.end")).capitalize(),
                     "value": end,
                     "inline": True
                     }]
                # Prices to win
                prices = data[lang]['events-prices']
                if current_event in prices:
                    points = await self.bot._(ctx.channel, "bot_events.points")
                    prices = [f"**{k} {points}:** {v}" for k,
                              v in prices[current_event].items()]
                    fields.append({"name": await self.bot._(ctx.channel, "bot_events.events-price-title"), "value": "\n".join(prices)})
                emb = self.bot.get_cog("Embeds").Embed(title=title, desc=event_desc, fields=fields,
                                                      image=self.current_event_data["icon"], color=self.current_event_data["color"])
                #e = discord.Embed().from_dict(emb.to_dict())
                await ctx.send(embed=emb)
            else:
                txt = f"**{title}**\n\n{event_desc}"
                txt += "\n\n__{}:__ {}".format((await self.bot._(ctx.channel, "misc.beginning")).capitalize(), begin)
                txt += "\n__{}:__ {}".format((await self.bot._(ctx.channel, "misc.end")).capitalize(), end)
                await ctx.send(txt)
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

        if not current_event in events_desc.keys():
            await ctx.send(events_desc["nothing"])
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
        prices = await self.bot._(ctx.channel, "bot_events.events-prices")
        if current_event in prices.keys():
            emojis = self.bot.get_cog("Emojis").customEmojis["green_check"], self.bot.get_cog("Emojis").customEmojis["red_cross"]
            p = list()
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
            fields = list()
            if objectives_title != "":
                fields.append({"name": objectives_title, "value": prices})
            fields.append(
                {"name": rank_total, "value": str(points), "inline": True})
            fields.append(
                {"name": rank_global, "value": user_rank, "inline": True})
            desc = await self.bot._(ctx.channel, "bot_events.xp-howto")
            emb = self.bot.get_cog("Embeds").Embed(title=title, desc=desc, fields=fields, color=4254055, author_name=str(user), author_icon=str(await self.bot.user_avatar_as(user, 32)))
            await ctx.send(embed=emb)
        else:
            msg = f"**{title}** ({user})"
            if objectives_title != "":
                msg += "\n\n__{}:__\n{}".format(objectives_title, prices)
            msg += "\n\n__{}:__ {}\n__{}:__ {}".format(
                rank_total, str(points), rank_global, user_rank)
            await ctx.send(msg)


def setup(bot):
    bot.add_cog(BotEvents(bot))
