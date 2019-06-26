import discord, time, typing, importlib, asyncio, aiohttp
from discord.ext import commands
from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)

class PartnersCog(commands.Cog):

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
            cnx = self.bot.cnx_frm
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
            cnx = self.bot.cnx_frm
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
            if len(invites)==0:
                return list()
            cnx = self.bot.cnx_frm
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
    
    async def bdd_set_partner(self,guildID:int,partnerID:str,partnerType:str,desc:str):
        """Add a partner into a server"""
        try:
            ID = await self.generate_id()
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            query = ("INSERT INTO `{table}` (`ID`,`guild`,`target`,`type`,`description`) VALUES ('{id}','{guild}','{target}','{type}','{desc}');".format(table=self.table,id=ID,guild=guildID,target=partnerID,type=partnerType,desc=desc.replace("'","\\'")))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def bdd_edit_partner(self,partnerID:int,target:str=None,desc:str=None,msg:int=None):
        """Modify a partner"""
        try:
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            query = ""
            if target!=None:
                query += ("UPDATE `{table}` SET `target` = \"{target}\" WHERE `ID` = {id};".format(table=self.table,target=target,id=partnerID))
            if desc!=None:
                query += ("UPDATE `{table}` SET `description` = \"{desc}\" WHERE `ID` = {id};".format(table=self.table,desc=desc.replace('"','\"'),id=partnerID))
            if msg!=None:
                query += ("UPDATE `{table}` SET `messageID` = \"{msg}\" WHERE `ID` = {id};".format(table=self.table,msg=msg,id=partnerID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    
    async def bdd_del_partner(self,ID:int):
        """Delete a partner from a guild list"""
        try:
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary = True)
            query = ("DELETE FROM `{}` WHERE `ID` = {}".format(self.table,ID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)
            return False
    

    async def get_uptimes(self,bot:int,session:aiohttp.ClientSession):
        """Get the uptime of a bot
        None if unknown"""
        async with session.get(f'https://api.discordbots.group/v1/bot/{bot}/uptime') as resp:
            ans = await resp.json()
            if ans['error']:
                return None
            return ans['percentage']
    
    async def get_guilds(self,bot:int,session:aiohttp.ClientSession):
        """Get the guilds count of a bot
        None if unknown"""
        async with session.get('https://discordbots.org/api/bots/{}/stats'.format(bot),headers={'Authorization':str(self.bot.dbl_token)}) as resp:
            ans = await resp.json()
            if 'server_count' in ans.keys():
                return ans['server_count']
            return None


    async def update_partners(self,channel:discord.TextChannel,color:int=None):
        """Update every partners of a channel"""
        partners = await self.bdd_get_guild(channel.guild.id)
        if not channel.permissions_for(channel.guild.me).embed_links:
            return 0
        tr_unknown = await self.translate(channel.guild.id,'keywords','unknown')
        tr_guild = await self.translate(channel.guild.id,'keywords','server')
        tr_bot = await self.translate(channel.guild.id,'keywords','bot')
        tr_members = await self.translate(channel.guild.id,'stats_infos','role-3')
        tr_guilds = await self.translate(channel.guild.id,'keywords','servers')
        tr_invite = await self.translate(channel.guild.id,'stats_infos','inv-4')
        tr_click = await self.translate(channel.guild.id,'keywords','click_here')
        count = 0
        if color==None:
            color = await self.bot.cogs['ServerCog'].find_staff(channel.guild.id,'partner_color')
        if color==None:
            color = self.bot.cogs['ServerCog'].default_opt['partner_color']
        session = aiohttp.ClientSession(loop=self.bot.loop)
        for partner in partners:
            image = ""
            if partner['type']=='bot':
                title = "**{}** ".format(tr_bot.capitalize())
                try:
                    title += str(await self.bot.fetch_user(int(partner['target'])))
                    guild_nbr = await self.get_guilds(partner['target'],session)
                    if guild_nbr!=None:
                        field1 = {'name':tr_guilds.capitalize(),'value':str(guild_nbr)}
                    else:
                        field1 = None
                    image = (await self.bot.fetch_user(int(partner['target']))).avatar_url.__str__()
                except discord.errors.NotFound:
                    title += "ID: "+partner['target']
                    field1 = None
                except Exception as e:
                    field1 = None
                    image = (await self.bot.fetch_user(int(partner['target']))).avatar_url
                    await self.bot.cogs["ErrorsCog"].on_error(e,None)
                field2 = {'name':tr_invite.capitalize(),'value':'[Click here](https://discordapp.com/oauth2/authorize?client_id={}&scope=bot&permissions=2113273087)'.format(partner['target'])}
                up = await self.get_uptimes(partner['target'],session)
                if up!=None:
                    field3 = {'name':await self.translate(channel.guild,'partners','bot-uptime'), 'value':f"{round(up,2)}%"}
                else:
                    field3 = None
            else:
                title = "**{}** ".format(tr_guild.capitalize())
                inv = await self.bot.fetch_invite(partner['target'])
                image = inv.guild.icon_url.__str__()
                if isinstance(inv,discord.Invite) and not inv.revoked:
                    title += inv.guild.name
                    field1 = {'name':tr_members.capitalize(),'value':str(inv.approximate_member_count)}
                    await self.give_roles(inv,channel.guild)
                else:
                    title += tr_unknown
                    field1 = None
                field2 = {'name':tr_invite.capitalize(),'value':'[{}](https://discord.gg/{})'.format(tr_click.capitalize(),partner['target'])}
                field3 = None
            emb = self.bot.cogs['EmbedCog'].Embed(title=title,desc=partner['description'],fields=[x for x in (field1,field2,field3) if not x==None],color=color,footer_text=str(partner['ID']),thumbnail=image).update_timestamp()
            try:
                msg = await channel.fetch_message(partner['messageID'])
                await msg.edit(embed=emb.discord_embed())
            except discord.errors.NotFound:
                msg = await channel.send(embed=emb.discord_embed())
                await self.bdd_edit_partner(partnerID=partner['ID'],msg=msg.id)
            except Exception as e:
                msg = await channel.send(embed=emb.discord_embed())
                await self.bdd_edit_partner(partnerID=partner['ID'],msg=msg.id)
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
            count += 1
        await session.close()
        return count

    async def give_roles(self,invite:discord.Invite,guild:discord.Guild):
        """Give a role to admins of partners"""
        if isinstance(invite.guild,discord.Guild):
            roles = await self.bot.cogs['ServerCog'].find_staff(guild.id,'partner_role')
            roles = [x for x in [guild.get_role(int(x)) for x in roles.split(';') if len(x)>0 and x.isnumeric()] if x!=None]
            admins = [x for x in invite.guild.members if x.guild_permissions.administrator]
            for admin in admins:
                if admin in guild.members:
                    member = guild.get_member(admin.id)
                    for role in roles:
                        if role not in member.roles:
                            try:
                                await member.add_roles(role)
                            except:
                                pass



    @commands.group(name="partner",aliases=['partners'])
    @commands.guild_only()
    async def partner_main(self,ctx):
        """Manage the partners of your server"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['partner'])

    @partner_main.command(name='add')
    @commands.check(checks.has_admin)
    async def partner_add(self,ctx,invite:args.Invite,*,description=''):
        """Add a partner in your llist"""
        if isinstance(invite,int):
            try:
                item = await self.bot.fetch_user(invite)
                if item.bot==False:
                    raise Exception
            except:
                return await ctx.send(await self.translate(ctx.guild.id,'partners','invalid-bot'))
            Type = 'bot'
        elif isinstance(invite,str):
            try:
                item = await self.bot.fetch_invite(invite)
            except discord.errors.NotFound:
                return await ctx.send(await self.translate(ctx.guild.id,'partners','invalid-invite'))
            Type = 'guild'
        else:
            return
        if len(description)>0:
            description = await self.bot.cogs['EmojiCog'].anti_code(description)
        await self.bdd_set_partner(guildID=ctx.guild.id,partnerID=item.id,partnerType=Type,desc=description)
        await ctx.send(await self.translate(ctx.guild.id,'partners','added-partner'))
    
    @partner_main.command(name='description',aliases=['desc'])
    @commands.check(checks.has_admin)
    async def partner_desc(self,ctx,ID:int,*,description:str):
        """Add or modify a description for a partner"""
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l)==0:
            return await ctx.send(await self.translate(ctx.guild.id,'partners','invalid-partner'))
        l = l[0]
        description = await self.bot.cogs['EmojiCog'].anti_code(description)
        if await self.bdd_edit_partner(l['ID'],desc=description):
            await ctx.send(await self.translate(ctx.guild.id,'partners','changed-desc'))
        else:
            await ctx.send(await self.translate(ctx.guild.id,'partners','unknown-error'))

    @partner_main.command(name='invite')
    async def partner_invite(self,ctx,ID:int,new_invite:discord.Invite=None):
        """Get the invite of a guild partner. 
        If you specify an invite, the partner will be updated with this new invite"""
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l)==0 or l[0]['type']!='guild':
            return await ctx.send(await self.translate(ctx.guild.id,'partners','unknown-server'))
        l = l[0]
        if new_invite==None:
            return await ctx.send('{}: discord.gg/{}'.format(await self.translate(ctx.guild.id,'stats_infos','inv-4'),l['target']))
        if not await checks.has_admin(ctx):
            return
        if await self.bdd_edit_partner(l['ID'],target=new_invite.code):
            await ctx.send(await self.translate(ctx.guild.id,'partners','changed-invite'))
        else:
            await ctx.send(await self.translate(ctx.guild.id,'partners','unknown-error'))

    @partner_main.command(name='remove')
    @commands.check(checks.has_admin)
    async def partner_remove(self,ctx,ID:int):
        """Remove a partner from the partners list"""
        if not ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            return await ctx.send(await self.translate(ctx.guild.id,'partners','missing-reactions'))
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l)==0:
            return await ctx.send(await self.translate(ctx.guild.id,'partners','invalid-partner'))
        l = l[0]
        if l['type']=='bot':
            try:
                bot = await self.bot.fetch_user(l['target'])
            except:
                bot = l['target']
            msg = await ctx.send((await self.translate(ctx.guild.id,'partners','confirm-bot')).format(bot))
        elif l['type']=='guild':
            try:
                server = (await self.bot.fetch_invite(l['target'])).guild.name
            except:
                server = l['target']
            msg = await ctx.send((await self.translate(ctx.guild.id,'partners','confirm-server')).format(server))
        else:
            return
        await msg.add_reaction('✅')
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'
        try:
            await ctx.bot.wait_for('reaction_add', timeout=10.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(await self.translate(ctx.guild.id,'partners','del-canceled'))
        if await self.bdd_del_partner(l['ID']):
            await ctx.send(await self.translate(ctx.guild.id,'partners','deleted'))
        else:
            await ctx.send(await self.translate(ctx.guild.id,'partners','unknown-error'))
        
    @partner_main.command(name='list')
    @commands.check(checks.has_manage_guild)
    async def partner_list(self,ctx):
        """Get the list of every partners"""
        f = ['','']
        lang = await self.translate(ctx.guild.id,'current_lang','current')
        tr_bot = await self.translate(ctx.guild.id,'keywords','bot')
        tr_guild = await self.translate(ctx.guild.id,'keywords','server')
        tr_added = await self.translate(ctx.guild.id,'keywords','added_at')
        tr_unknown = await self.translate(ctx.guild.id,'keywords','unknown')
        tr_owner = await self.translate(ctx.guild.id,'stats_infos','guild-1')
        for l in await self.bdd_get_guild(ctx.guild.id):
            date = str(await ctx.bot.cogs['TimeCog'].date(l['added_at'],lang=lang,year=True,hour=False)).strip()
            if l['type']=='bot':
                try:
                    bot = await self.bot.fetch_user(l['target'])
                except:
                    bot = l['target']
                f[0] += "[{}] **{}** `{}` ({} {})\n".format(l['ID'],tr_bot.capitalize(),bot,tr_added,date)
            elif l['type']=='guild':
                try:
                    server = (await self.bot.fetch_invite(l['target'])).guild.name
                except:
                    server = 'discord.gg/'+l['target']
                f[0] += "[{}] **{}** `{}` ({} {})\n".format(l['ID'],tr_guild.capitalize(),server,tr_added,date)
        if ctx.guild.me.guild_permissions.manage_guild:
            for l in await self.bdd_get_partnered(await ctx.guild.invites()):
                server = ctx.bot.get_guild(l['guild'])
                if server==None:
                    server = l['guild']
                    f[1] += f"{tr_unknown} (ID: {server})"
                else:
                    f[1] += f"{server.name} ({tr_owner} : {server.owner})"
        else:
            f[1] = await self.translate(ctx.guild.id,'partners','missing-manage-guild')
        if len(f[0])==0:
            f[0] = await self.translate(ctx.guild.id,'partners','no-partner')
        if len(f[1])==0:
            f[1] = await self.translate(ctx.guild.id,'partners','no-partner-2')
        fields_name = await self.translate(ctx.guild.id,'partners','partners-list')
        if isinstance(ctx.channel,discord.DMChannel) or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            color = await ctx.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'partner_color')
            if color==None:
                color = self.bot.cogs['ServerCog'].default_opt['partner_color']
            emb = ctx.bot.cogs['EmbedCog'].Embed(title=fields_name[0],fields=[{'name':fields_name[1],'value':f[0]},{'name':'​','value':'​'},{'name':fields_name[2],'value':f[1]}],color=color,thumbnail=ctx.guild.icon_url).create_footer(ctx.author).update_timestamp()
            await ctx.send(embed=emb.discord_embed())
        else:
            await ctx.send(f"__{fields_name[0]}:__\n{f[0]}\n\n__{fields_name[1]}:__\n{f[1]}")




def setup(bot:commands.Bot):
    bot.add_cog(PartnersCog(bot))