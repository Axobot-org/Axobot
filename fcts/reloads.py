import importlib

from discord.ext import commands

from libs.bot_classes import Axobot, MyContext
from libs.checks.checks import is_bot_admin


class Reloads(commands.Cog):
    """Cog to manage the other cogs. Even if all are disabled, this is the last one left."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "reloads"
        self.ignored_guilds = [
            471361000126414848, # Zbot emojis 1
            513087032331993090, # Zbot emojis 2
            500648624204808193, # Emergency server
            446425626988249089, # Bots on Discord
            707248438391078978, # ?
            568567800910839811, # Delly
        ]

    async def reload_cogs(self, ctx: MyContext, cogs: list[str]):
        "Reload a list of cogs and python modules"
        if len(cogs)==1 and cogs[0]=='all':
            cogs = sorted([x.file for x in self.bot.cogs.values()])
        reloaded_cogs = []
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
                self.bot.dispatch("error", err, ctx)
                await ctx.send(f'**`ERROR:`** {type(err).__name__} - {err}')
            else:
                self.bot.log.info(f"Module {cog} rechargé")
                reloaded_cogs.append(cog)
            if cog == 'utilities':
                await self.bot.get_cog('Utilities').on_ready()
        if len(reloaded_cogs) > 0:
            await ctx.send(f"These cogs has successfully reloaded: {', '.join(reloaded_cogs)}")
            if info_cog := self.bot.get_cog("BotInfo"):
                await info_cog.refresh_code_lines_count()

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
