import random, discord, asyncio, datetime
from discord.ext import commands

class PartnerCog(commands.Cog):

    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self.file = 'partners'
        self.table = 'partners_beta' if bot.beta else 'partners'
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
        self.table = 'partners_beta' if self.bot.beta else 'partners'
    


def setup(bot:commands.Bot):
    bot.add_cog(PartnerCog(bot))