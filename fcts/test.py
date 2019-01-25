import discord, datetime, inspect, random, logging
from discord.ext import commands

from docs import conf

class TestCog:
    """Hey, I'm a test cog! Happy to meet you :wave:"""

    def __init__(self, bot):
        self.bot = bot

    
    @commands.command(name="test")
    #@commands.is_owner()
    async def test(self,ctx):
        await ctx.send("heya")
        log = logging.getLogger("runner")
        log.info("hey")
    

def setup(bot):
    bot.add_cog(TestCog(bot))
