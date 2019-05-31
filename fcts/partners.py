import discord, time, typing, importlib, asyncio
from discord.ext import commands
from fcts import args
importlib.reload(args)

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
    
    async def generate_id(self):
        return round(time.time()/2)

    async def bdd_get_partner(self,partnerID:int,guildID:int):
        """Return a partner based on its ID"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT * FROM `{}` WHERE `ID`={} AND `guild`={}".format(self.table,partnerID,guildID))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
    
    async def bdd_get_guild(self,guildID:int):
        """Return every partners of a guild"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT * FROM `{}` WHERE `guild`={}".format(self.table,guildID))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
    
    async def bdd_set_partner(self,guildID:int,partnerID:str,partnerType:str):
        """Ajoute un partenaire à un serveur"""
        try:
            ID = await self.generate_id()
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("INSERT INTO `{table}` (`ID`,`guild`,`target`,`type`) VALUES ('{id}','{guild}','{target}','{type}');".format(table=self.table,id=ID,guild=guildID,target=partnerID,type=partnerType))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def bdd_del_partner(self,ID:int):
        """Ajoute un partenaire à un serveur"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("DELETE FROM `{}` WHERE `ID` = {}".format(self.table,ID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False


    @commands.group(name="partner",aliases=['partners'])
    @commands.guild_only()
    async def partner_main(self,ctx):
        """Manage the partners of your server"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['partner'])

    @partner_main.command(name='add')
    async def partner_add(self,ctx,invite:args.Invite):
        """Add a partner in your llist"""
        if isinstance(invite,int):
            try:
                item = await self.bot.fetch_user(invite)
                if item.bot==False:
                    raise Exception
            except:
                return await ctx.send('Impossible de trouver ce bot')
            Type = 'bot'
        elif isinstance(invite,str):
            try:
                item = await self.bot.fetch_invite(invite)
            except discord.errors.NotFound:
                return await ctx.send("Invitation invalide")
            Type = 'guild'
        else:
            return
        await self.bdd_set_partner(guildID=ctx.guild.id,partnerID=item.id,partnerType=Type)
        await ctx.send("done")
    
    @partner_main.command(name='remove')
    async def partner_remove(self,ctx,ID:int):
        """Remove a partner from the partners list"""
        if not ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            return await ctx.send("Permission 'Ajouter des réactions' manquante")
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l)==0:
            return await ctx.send("Partenaire introuvable")
        l = l[0]
        if l['type']=='bot':
            try:
                bot = await self.bot.fetch_user(l['target'])
            except:
                bot = l['target']
            msg = await ctx.send(("Voulez-vous vraiment supprimer le bot {} de vos partenaires ?").format(bot))
        elif l['type']=='guild':
            try:
                server = (await self.bot.fetch_invite(l['target'])).name
            except:
                server = l['target']
            msg = await ctx.send(("Voulez-vous vraiment supprimer le serveur {} de vos partenaires ?").format(server))
        else:
            return
        await msg.add_reaction('✅')
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'
        try:
            await ctx.bot.wait_for('reaction_add', timeout=10.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send('Suppression annulée')
        if await self.bdd_del_partner(l['ID']):
            await ctx.send("Ce partenaire a bien été supprimé de votre liste")
        else:
            await ctx.send("Une erreur inconnue est survenue. Veuillez contacter le support pour plus d'informations")



def setup(bot:commands.Bot):
    bot.add_cog(PartnerCog(bot))