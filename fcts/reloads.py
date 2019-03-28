import importlib, sys
from discord.ext import commands

admins_id = [279568324260528128,281404141841022976,552273019020771358]

async def check_admin(ctx):
    if type(ctx) == commands.Context:
        user = ctx.author
    else:
        user = ctx
    if type(user) == str and user.isnumeric():
        user = int(user)
    elif type(user) != int:
        user = user.id
    return user in admins_id

async def is_support_staff(ctx):
    if ctx.author.id in admins_id:
        return True
    try:
        return await ctx.bot.cogs['UtilitiesCog'].is_support(ctx.author)
    except:
        pass
    server = ctx.bot.get_guild(356067272730607628)
    if server != None:
        member = server.get_member(ctx.author.id)
        role = server.get_role(412340503229497361)
        if member != None and role != None:
            return role in member.roles
    return False

class ReloadsCog(commands.Cog):
    """Cog to manage the other cogs. Even if all are disabled, this is the last one left."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "reloads"
        self.ignored_guilds = [471361000126414848,513087032331993090,500648624204808193,264445053596991498]
    
    async def reload_cogs(self,ctx,cogs):
        errors_cog = self.bot.cogs["ErrorsCog"]
        if len(cogs)==1 and cogs[0]=='all':
            cogs = sorted([x.file for x in self.bot.cogs.values()])
        reloaded_cogs = list()
        for cog in cogs:
            if not cog.startswith("fcts."):
                fcog = "fcts."+cog
            try:
                self.bot.unload_extension(fcog)
                self.bot.load_extension(fcog)
            except ModuleNotFoundError:
                await ctx.send("Cog {} can't be found".format(cog))
            except commands.errors.ExtensionNotLoaded :
                await ctx.send("Cog {} was never loaded".format(cog))
            except Exception as e:
                await errors_cog.on_error(e,ctx)
                await ctx.send(f'**`ERROR:`** {type(e).__name__} - {e}')
            else:
                await self.bot.cogs["UtilitiesCog"].print2("Module {} rechargé".format(cog))
                reloaded_cogs.append(cog)
        if len(reloaded_cogs)>0:
            await ctx.send("These cogs has successfully reloaded: {}".format(", ".join(reloaded_cogs)))
            ctx.bot.cogs['InfosCog'].codelines = await ctx.bot.cogs['InfosCog'].count_lines_code()

    @commands.command(name="add_cog",hidden=True)
    @commands.check(check_admin)
    async def add_cog(self,ctx,name):
        """Ajouter un cog au bot"""
        if not ctx.author.id in admins_id:
            return
        try:
            self.bot.load_extension('fcts.'+name)
            await ctx.send("Cog '{}' ajouté !".format(name))
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
            await ctx.send("Cog '{}' désactivé !".format(name))
        except Exception as e:
            await ctx.send(str(e))


def setup(bot):
    bot.add_cog(ReloadsCog(bot))
