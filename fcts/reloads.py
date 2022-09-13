import importlib
from discord.ext import commands
from fcts.checks import is_bot_admin
from libs.classes import MyContext, Zbot
from utils import count_code_lines

class Reloads(commands.Cog):
    """Cog to manage the other cogs. Even if all are disabled, this is the last one left."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "reloads"
        self.ignored_guilds = [471361000126414848,513087032331993090,500648624204808193,264445053596991498,446425626988249089,707248438391078978]
    
    async def reload_cogs(self, ctx: MyContext, cogs: list[str]):
        errors_cog = self.bot.get_cog("Errors")
        if len(cogs)==1 and cogs[0]=='all':
            cogs = sorted([x.file for x in self.bot.cogs.values()])
        reloaded_cogs = list()
        for cog in cogs:
            if not cog.startswith("fcts."):
                fcog = "fcts."+cog
            else:
                fcog = cog
            try:
                await self.bot.reload_extension(fcog)
            except ModuleNotFoundError:
                await ctx.send(f"Cog {cog} can't be found")
            except commands.errors.ExtensionNotLoaded :
                try:
                    flib = importlib.import_module(cog)
                    importlib.reload(flib)
                except ModuleNotFoundError:
                    await ctx.send(f"Cog {cog} was never loaded")
                else:
                    self.bot.log.info(f"Lib {cog} reloaded")
                    await ctx.send(f"Lib {cog} reloaded")
            except Exception as err:
                await errors_cog.on_error(err,ctx)
                await ctx.send(f'**`ERROR:`** {type(err).__name__} - {err}')
            else:
                self.bot.log.info(f"Module {cog} rechargé")
                reloaded_cogs.append(cog)
            if cog == 'utilities':
                await self.bot.get_cog('Utilities').on_ready()
        if len(reloaded_cogs) > 0:
            await ctx.send("These cogs has successfully reloaded: {}".format(", ".join(reloaded_cogs)))
            if info_cog := self.bot.get_cog("Info"):
                info_cog.codelines = await count_code_lines()

    @commands.command(name="add_cog",hidden=True)
    @commands.check(is_bot_admin)
    async def add_cog(self, ctx: MyContext, name: str):
        """Ajouter un cog au bot"""
        try:
            await self.bot.load_extension('fcts.'+name)
            await ctx.send(f"Module '{name}' ajouté !")
            self.bot.log.info(f"Module {name} ajouté")
        except Exception as err:
            await ctx.send(str(err))

    @commands.command(name="del_cog",aliases=['remove_cog'],hidden=True)
    @commands.check(is_bot_admin)
    async def rm_cog(self, ctx: MyContext, name: str):
        """Enlever un cog au bot"""
        try:
            await self.bot.unload_extension('fcts.'+name)
            await ctx.send(f"Module '{name}' désactivé !")
            self.bot.log.info(f"Module {name} ajouté")
        except Exception as err:
            await ctx.send(str(err))


async def setup(bot):
    await bot.add_cog(Reloads(bot))
