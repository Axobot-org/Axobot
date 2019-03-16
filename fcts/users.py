import discord, importlib, typing
from discord.ext import commands

from fcts import args
importlib.reload(args)

class UsersCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = 'users'
        self.table = 'timed'
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr

    @commands.group(name='profile')
    async def profile_main(self,ctx):
        """Get and change info about yourself"""
        pass
    
    @profile_main.command(name='card')
    async def profile_card(self,ctx,style:typing.Optional[args.cardStyle]=None):
        """Change your xp card style"""
        if style==None and len(ctx.view.buffer.split(' '))>2:
            return await ctx.send(str(await self.translate(ctx.guild,'users','invalid-card')).format(', '.join(await ctx.bot.cogs['UtilitiesCog'].allowed_card_styles(ctx.author))))
        elif style==None:
            txts = [await self.translate(ctx.guild,'xp','card-level'), await self.translate(ctx.guild,'xp','card-rank')]
            await ctx.send(file=await self.bot.cogs['XPCog'].create_card(ctx.author,'admin',0,[1,0],txts,force_static=True))
        else:
            await ctx.send(style)



def setup(bot):
    bot.add_cog(UsersCog(bot))