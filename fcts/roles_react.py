import discord, time
from discord.ext import commands

class RolesReact(commands.Cog):
    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self.file = 'roles_react'
        self.table = 'roles_react_beta' if bot.beta else 'roles_react'
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
        self.table = 'roles_react_beta' if self.bot.beta else 'roles_react'
    
    async def gen_id(self):
        return round(time.time()/2)

    async def rr_add_role(self,guild:int,role:int,emoji:str):
        """Add a role reaction in the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        ID = await self.gen_id()
        query = ("INSERT INTO `{}` (`ID`,`guild`,`role`,`emoji`) VALUES ('{i}','{g}','{r}','{e}');".format(self.table,i=ID,g=guild,r=role,e=emoji))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True
    
    async def rr_list_role(self,guild:int):
        """List role reaction in the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query ="SELECT * FROM `{}` WHERE guild={} ORDER BY level;".format(self.table,guild)
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste
    
    async def rr_remove_role(self,ID:int):
        """Remove a role reaction from the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("DELETE FROM `{}` WHERE `ID`={};".format(self.table,ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    @commands.group(name="roles_react")
    @commands.guild_only()
    async def rr_main(self,ctx):
        """Manage your roles reactions"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['roles_react'])




def setup(bot):
    bot.add_cog(RolesReact(bot))