import discord, datetime, json
from discord.ext import commands


class BotEventsCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = "bot_events"
        self.current_event = None
        self.current_event_data = {}
        self.updateCurrentEvent()
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass

    def updateCurrentEvent(self):
        today = datetime.date.today()
        with open("events-list.json",'r') as f:
            events = json.load(f)
        for ev_data in events.values():
            ev_data["begin"] = datetime.datetime.strptime(ev_data["begin"], "%Y-%m-%d")
            ev_data["end"] = datetime.datetime.strptime(ev_data["end"], "%Y-%m-%d")
            if ev_data["begin"].date() <= today and ev_data["end"].date() >= today:
                self.current_event = ev_data["type"]
                self.current_event_data = ev_data
                break

    @commands.group(name="events",aliases=["botevents","botevent"])
    async def events_main(self,ctx:commands.Context):
        """When I'm organizing some events"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['events'])
    
    @events_main.command(name="info")
    async def event_info(self,ctx:commands.Context):
        """Get info about the current event"""
        events_desc = await self.translate(ctx.channel,"users","events-desc")
        current_event = str(self.bot.current_event) + "-" + str(datetime.datetime.today().year)
        if current_event in events_desc.keys():
            if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
                nice_date = self.bot.cogs["TimeCog"].date
                try:
                    title = (await self.translate(ctx.channel,"users","events-title"))[current_event]
                except:
                    title = self.current_event
                # Begin/End dates
                lang = await self.translate(ctx.channel,"current_lang","current")
                begin = await nice_date(self.current_event_data["begin"],lang,year=True,digital=True,hour=False)
                end = await nice_date(self.current_event_data["end"],lang,year=True,digital=True,hour=False)
                fields = [
                    {"name": (await self.translate(ctx.channel,"keywords","beginning")).capitalize(), 
                    "value": begin,
                    "inline": True
                    },
                    {"name": (await self.translate(ctx.channel,"keywords","end")).capitalize(), 
                    "value": end,
                    "inline": True
                    }]
                # Prices to win
                prices = await self.translate(ctx.channel,"users","events-prices")
                if current_event in prices.keys():
                    fields.append({"name":await self.translate(ctx.channel,"users","events-price-title"), "value":prices[current_event]})
                emb = self.bot.cogs["EmbedCog"].Embed(title=title, desc=events_desc[current_event], fields=fields, image=self.current_event_data["icon"], color=self.current_event_data["color"])
                #e = discord.Embed().from_dict(emb.to_dict())
                await ctx.send(embed=emb)
            else:
                await ctx.send(events_desc[current_event])
        else:
            await ctx.send(events_desc["nothing"])


def setup(bot):
    bot.add_cog(BotEventsCog(bot))