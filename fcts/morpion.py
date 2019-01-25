import random, asyncio

class MorpionCog:

    def __init__(self,bot):
        self.bot = bot
        self.file = "morpion"
        try:
            self.translate = bot.cogs["LanguageCog"].tr
        except:
            pass

    async def on_ready(self):
        self.translate = self.bot.cogs["LanguageCog"].tr

    class MorpionGame:
        def __init__(self,ctx):
            self.ctx = ctx
            self.translate = ctx.bot.cogs["LanguageCog"].tr
            self.player= ctx.author

        async def launch(self):
            return

            
def setup(bot):
    bot.add_cog(MorpionCog(bot))