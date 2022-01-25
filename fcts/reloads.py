from discord.ext import commands
from libs.classes import MyContext, Zbot
from utils import count_code_lines

admins_id = {279568324260528128,281404141841022976,552273019020771358}

async def check_admin(ctx):
    if isinstance(ctx, commands.Context):
        user = ctx.author
    else:
        user = ctx
    if isinstance(user, str) and user.isnumeric():
        user = int(user)
    elif type(user) != int:
        user = user.id
    return user in admins_id

async def is_support_staff(ctx):
    if ctx.author.id in admins_id:
        return True
    if UsersCog := ctx.bot.get_cog('Users'):
        return await UsersCog.has_userflag(ctx.author, 'support')
    server = ctx.bot.get_guild(356067272730607628)
    if server is not None:
        member = server.get_member(ctx.author.id)
        role = server.get_role(412340503229497361)
        if member is not None and role is not None:
            return role in member.roles
    return False

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
                self.bot.reload_extension(fcog)
            except ModuleNotFoundError:
                await ctx.send("Cog {} can't be found".format(cog))
            except commands.errors.ExtensionNotLoaded :
                await ctx.send("Cog {} was never loaded".format(cog))
            except Exception as e:
                await errors_cog.on_error(e,ctx)
                await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
            else:
                self.bot.log.info("Module {} rechargé".format(cog))
                reloaded_cogs.append(cog)
            if cog == 'utilities':
                await self.bot.get_cog('Utilities').on_ready()
        if len(reloaded_cogs) > 0:
            await ctx.send("These cogs has successfully reloaded: {}".format(", ".join(reloaded_cogs)))
            if info_cog := self.bot.get_cog("Info"):
                info_cog.codelines = await count_code_lines()

    @commands.command(name="add_cog",hidden=True)
    @commands.check(check_admin)
    async def add_cog(self,ctx,name):
        """Ajouter un cog au bot"""
        if not ctx.author.id in admins_id:
            return
        try:
            self.bot.load_extension('fcts.'+name)
            await ctx.send("Module '{}' ajouté !".format(name))
            self.bot.log.info("Module {} ajouté".format(name))
        except Exception as e:
            await ctx.send(str(e))

    @commands.command(name="del_cog",aliases=['remove_cog'],hidden=True)
    @commands.check(check_admin)
    async def rm_cog(self,ctx,name):
        """Enlever un cog au bot"""
        if not ctx.author.id in admins_id:
            return
        try:
            self.bot.unload_extension('fcts.'+name)
            await ctx.send("Module '{}' désactivé !".format(name))
            self.bot.log.info("Module {} ajouté".format(name))
        except Exception as e:
            await ctx.send(str(e))


def setup(bot: Zbot):
    bot.add_cog(Reloads(bot))
