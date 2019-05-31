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
    
    async def bdd_get_partnered(self,invites:list):
        """Return every guilds which has this one as partner"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ("SELECT * FROM `{}` WHERE `type`='guild' AND ({})".format(self.table," OR ".join([f"`target`='{x.code}'" for x in invites])))
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            return liste
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
    
    async def bdd_set_partner(self,guildID:int,partnerID:str,partnerType:str):
        """Add a partner into a server"""
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
    
    async def bdd_edit_partner(self,partnerID:str,target:str=None,desc:str=None):
        """Modify a partner"""
        try:
            cnx = self.bot.cnx
            cursor = cnx.cursor(dictionary = True)
            query = ""
            if target!=None:
                query += ("UPDATE `{table}` SET `target` = \"{target}\" WHERE `ID` = {id};".format(table=self.table,target=target,id=partnerID))
            if desc!=None:
                query += ("UPDATE `{table}` SET `description` = \"{desc}\" WHERE `ID` = {id};".format(table=self.table,desc=desc.replace('"','\"'),id=partnerID))
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
    
    @partner_main.command(name='description',aliases=['desc'])
    async def partner_desc(self,ctx,ID:int,*,description:str):
        """Add or modify a description for a partner"""
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l)==0:
            return await ctx.send("Partenaire introuvable")
        l = l[0]
        if await self.bdd_edit_partner(l['ID'],desc=description):
            await ctx.send("La description a bien été modifiée !")
        else:
            await ctx.send("Une erreur inconnue est survenue. Veuillez contacter le support pour plus d'informations")

    @partner_main.command(name='invite')
    async def partner_invite(self,ctx,ID:int,new_invite:discord.Invite=None):
        """Get the invite of a guild partner. 
        If you specify an invite, the partner will be updated with this new invite"""
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l)==0 or l[0]['type']!='guild':
            return await ctx.send("Serveur partenaire introuvable")
        l = l[0]
        if new_invite==None:
            return await ctx.send('discord.gg/'+l['target'])
        if await self.bdd_edit_partner(l['ID'],target=new_invite.code):
            await ctx.send("L'invitation a bien été modifiée !")
        else:
            await ctx.send("Une erreur inconnue est survenue. Veuillez contacter le support pour plus d'informations")

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
        
    @partner_main.command(name='list')
    async def partner_list(self,ctx):
        """Get the list of every partners"""
        f = ['','']
        lang = 'fr'
        for l in await self.bdd_get_guild(ctx.guild.id):
            date = await ctx.bot.cogs['TimeCog'].date(l['added_at'],lang=lang)
            if l['type']=='bot':
                try:
                    bot = await self.bot.fetch_user(l['target'])
                except:
                    bot = l['target']
                f[0] += "[{}] **Bot** `{}` (Ajouté le {})\n".format(l['ID'],bot,date)
            elif l['type']=='guild':
                try:
                    server = (await self.bot.fetch_invite(l['target'])).name
                except:
                    server = 'discord.gg/'+l['target']
                f[0] += "[{}] **Serveur** `{}` (Ajouté le {})\n".format(l['ID'],server,date)
        for l in await self.bdd_get_partnered(await ctx.guild.invites()):
            server = ctx.bot.get_guild(l['guild'])
            if server==None:
                server = l['guild']
                f[1] += f"[{l['ID']}] Inconnu (ID: {server})"
            else:
                f[1] += f"[{l['ID']}] {server.name} (Propriétaire : {server.owner})"
        if len(f[0])==0:
            f[0] = ctx.send("Vous n'avez aucun partenaire")
        if len(f[1])==0:
            f[1] = ctx.send("Aucun serveur n'a de partenariat avec vous")
        if isinstance(ctx.channel,discord.DMChannel) or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            color = await ctx.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'partner_color')
            emb = ctx.bot.cogs['EmbedCog'].Embed(fields=[{'name':'Liste de vos partenaires','value':f[0]},{'name':'Liste des serveurs vous ayant comme partenaire','value':f[1]}],color=color).create_footer(ctx.author).update_timestamp()
            await ctx.send(embed=emb.discord_embed())
        else:
            await ctx.send(f[0]+'\n'+f[1])




def setup(bot:commands.Bot):
    bot.add_cog(PartnerCog(bot))