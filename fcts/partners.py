from typing import Optional, Union
import discord
import time
import importlib
import asyncio
import aiohttp
from discord.ext import commands
from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)
from libs.classes import Zbot, MyContext

class Partners(commands.Cog):

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = 'partners'
        self.table = 'partners_beta' if bot.beta else 'partners'
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'partners_beta' if self.bot.beta else 'partners'
    
    async def generate_id(self):
        return round(time.time()/2)

    async def bdd_get_partner(self, partnerID: int, guildID: int):
        """Return a partner based on its ID"""
        try:
            query = ("SELECT * FROM `{}` WHERE `ID`={} AND `guild`={}".format(self.table,partnerID,guildID))
            async with self.bot.db_query(query) as query_results:
                liste = list(query_results)
            return liste
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,None)
    
    async def bdd_get_guild(self, guildID: int):
        """Return every partners of a guild"""
        try:
            query = ("SELECT * FROM `{}` WHERE `guild`={}".format(self.table,guildID))
            async with self.bot.db_query(query) as query_results:
                liste = list(query_results)
            return liste
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,None)
    
    async def bdd_get_partnered(self, invites: list):
        """Return every guilds which has this one as partner"""
        try:
            if len(invites) == 0:
                return list()
            query = ("SELECT * FROM `{}` WHERE `type`='guild' AND ({})".format(self.table," OR ".join([f"`target`='{x.code}'" for x in invites])))
            async with self.bot.db_query(query) as query_results:
                liste = list(query_results)
            return liste
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,None)
    
    async def bdd_set_partner(self,guildID:int,partnerID:str,partnerType:str,desc:str):
        """Add a partner into a server"""
        try:
            ID = await self.generate_id()
            query = "INSERT INTO `{}` (`ID`,`guild`,`target`,`type`,`description`) VALUES (%(i)s,%(g)s,%(ta)s,%(ty)s,%(d)s);".format(self.table)
            async with self.bot.db_query(query, { 'i': ID, 'g': guildID, 'ta': partnerID, 'ty': partnerType, 'd': desc }):
                pass
            return True
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,None)
            return False
    
    async def bdd_edit_partner(self,partnerID:int,target:str=None,desc:str=None,msg:int=None):
        """Modify a partner"""
        try:
            query = ""
            if target is not None:
                query += ("UPDATE `{table}` SET `target` = \"{target}\" WHERE `ID` = {id};".format(table=self.table,target=target,id=partnerID))
            if desc is not None:
                query += ("UPDATE `{table}` SET `description` = \"{desc}\" WHERE `ID` = {id};".format(table=self.table,desc=desc.replace('"','\"'),id=partnerID))
            if msg is not None:
                query += ("UPDATE `{table}` SET `messageID` = \"{msg}\" WHERE `ID` = {id};".format(table=self.table,msg=msg,id=partnerID))
            async with self.bot.db_query(query):
                pass
            return True
        except Exception as err:
            await self.bot.get_cog('Errors').on_error(err,None)
            return False
    
    async def bdd_del_partner(self,ID:int):
        """Delete a partner from a guild list"""
        try:
            query = ("DELETE FROM `{}` WHERE `ID` = {}".format(self.table,ID))
            async with self.bot.db_query(query):
                pass
            return True
        except Exception as e:
            await self.bot.get_cog('Errors').on_error(e,None)
            return False
    
    async def get_bot_guilds(self, bot:int, session:aiohttp.ClientSession) -> Optional[int]:
        """Get the guilds count of a bot
        None if unknown bot/count not provided"""
        async with session.get('https://discordbots.org/api/bots/{}/stats'.format(bot), headers={'Authorization':str(self.bot.dbl_token)}) as resp:
            ans: dict = await resp.json()
        if 'server_count' in ans:
            return ans['server_count']
        return None
    
    async def get_bot_owners(self, bot:int, session:aiohttp.ClientSession) -> list[Union[discord.User, int]]:
        """Get the owners list of a bot
        Empty list if unknown bot/owners not provided"""
        async with session.get('https://discordbots.org/api/bots/{}'.format(bot), headers={'Authorization':str(self.bot.dbl_token)}) as resp:
            ans: dict = await resp.json()
        owners = list()
        if 'owners' in ans:
            for o in ans['owners']:
                try:
                    owners.append(await self.bot.fetch_user(o))
                except discord.NotFound:
                    owners.append(o)
        return owners

    async def update_partners(self, channel: discord.TextChannel, color: int =None) -> int:
        """Update every partners of a channel"""
        if not channel.permissions_for(channel.guild.me).embed_links:
            return 0
        partners = await self.bdd_get_guild(channel.guild.id)
        if len(partners) == 0:
            return 0
        tr_unknown = await self.bot._(channel.guild.id, "misc.unknown")
        tr_guild = await self.bot._(channel.guild.id, "misc.server")
        tr_bot = await self.bot._(channel.guild.id, "misc.bot")
        tr_members = await self.bot._(channel.guild.id, 'info.info.role-3')
        tr_guilds = await self.bot._(channel.guild.id, "misc.servers")
        tr_invite = await self.bot._(channel.guild.id, 'info.info.inv-4')
        tr_click = await self.bot._(channel.guild.id, "misc.click_here")
        tr_owner = await self.bot._(channel.guild.id, 'info.info.guild-1')
        count = 0
        if color is None:
            color = await self.bot.get_config(channel.guild.id,'partner_color')
        if color is None:
            color = self.bot.get_cog('Servers').default_opt['partner_color']
        session = aiohttp.ClientSession(loop=self.bot.loop)
        for partner in partners:
            target_desc = partner['description']
            if partner['type'] == 'bot':
                title, fields, image = await self.update_partner_bot(tr_bot, tr_guilds, tr_invite, tr_owner, session, partner)
            else:
                try:
                    title, fields, image, target_desc = await self.update_partner_guild(tr_guild, tr_members, tr_unknown, tr_invite, tr_click, channel, partner, target_desc)
                except discord.NotFound:
                    continue
            emb = discord.Embed(title=title, description=target_desc, color=color, timestamp=self.bot.utcnow())
            emb.set_footer(text=partner['ID'])
            emb.set_thumbnail(url=image)
            for field in fields:
                if field:
                    emb.add_field(**field)
            if self.bot.zombie_mode:
                return
            try:
                msg = await channel.fetch_message(partner['messageID'])
                await msg.edit(embed=emb)
            except discord.errors.NotFound:
                msg = await channel.send(embed=emb)
                await self.bdd_edit_partner(partnerID=partner['ID'],msg=msg.id)
            except Exception as e:
                msg = await channel.send(embed=emb)
                await self.bdd_edit_partner(partnerID=partner['ID'],msg=msg.id)
                await self.bot.get_cog('Errors').on_error(e,None)
            count += 1
        await session.close()
        return count

    async def update_partner_bot(self, tr_bot: str, tr_guilds: str, tr_invite: str, tr_owner: str, session: aiohttp.ClientSession, partner: dict):
        """Update a bot partner embed"""
        image = ""
        title = "**{}** ".format(tr_bot.capitalize())
        fields = list()
        try:
            title += str(await self.bot.fetch_user(int(partner['target'])))
            # guild count field
            guild_nbr = await self.get_bot_guilds(partner['target'], session)
            if guild_nbr is not None:
                fields.append({'name': tr_guilds.capitalize(),
                              'value': str(guild_nbr)})
            # owners field
            owners = await self.get_bot_owners(partner['target'], session)
            if owners:
                fields.append({'name': tr_owner.capitalize(),
                              'value': ", ".join([str(u) for u in owners])})
            usr = await self.bot.fetch_user(int(partner['target']))
            image = usr.display_avatar.with_static_format("png") if usr else ""
        except discord.NotFound:
            title += "ID: "+partner['target']
        except Exception as e:
            usr = await self.bot.fetch_user(int(partner['target']))
            image = usr.display_avatar.url if usr else ""
            await self.bot.get_cog("Errors").on_error(e, None)
        perm = discord.Permissions.all()
        perm.update(administrator=False)
        oauth_url = discord.utils.oauth_url(partner['target'], permissions=perm)
        fields.append({'name': tr_invite.capitalize(),
                      'value': f'[Click here]({oauth_url})'})
        return title, fields, image

    async def update_partner_guild(self, tr_guild: str, tr_members: str, tr_unknown: str, tr_invite: str, tr_click: str, channel: discord.TextChannel, partner: dict, target_desc: str):
        """Update a guild partner embed"""
        title = "**{}** ".format(tr_guild.capitalize())
        try:
            inv = await self.bot.fetch_invite(partner['target'])
        except discord.errors.NotFound as e:
            raise e
        image = str(inv.guild.icon)
        if isinstance(inv, discord.Invite) and not inv.revoked:
            title += inv.guild.name
            field1 = {'name': tr_members.capitalize(), 'value': str(
                inv.approximate_member_count)}
            await self.give_roles(inv, channel.guild)
        else:
            title += tr_unknown
            field1 = None
        field2 = {'name': tr_invite.capitalize(
        ), 'value': '[{}](https://discord.gg/{})'.format(tr_click.capitalize(), partner['target'])}
        if len(target_desc) == 0:
            target_desc = await self.bot.get_config(inv.guild.id, 'description')
        return title, (field1, field2), image, target_desc

    async def give_roles(self,invite:discord.Invite,guild:discord.Guild):
        """Give a role to admins of partners"""
        if not isinstance(invite.guild,discord.Guild):
            return
        if guild.id == 356067272730607628 and self.bot.beta:
            return
        roles = await self.bot.get_config(guild.id,'partner_role')
        roles = (guild.get_role(int(x)) for x in roles.split(';') if len(x) > 0 and x.isnumeric())
        roles = (x for x in roles if x is not None)
        admins = [x for x in invite.guild.members if not x.bot and x.guild_permissions.administrator]
        for admin in admins:
            if admin in guild.members:
                member = guild.get_member(admin.id)
                for role in roles:
                    if role not in member.roles:
                        try:
                            await member.add_roles(role)
                        except (discord.HTTPException, discord.Forbidden):
                            pass


    @commands.group(name="partner",aliases=['partners'])
    @commands.guild_only()
    @commands.check(checks.database_connected)
    async def partner_main(self, ctx: MyContext):
        """Manage the partners of your server
        
        ..Doc server.html#partners-system"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx,['partner'])

    @partner_main.command(name='add')
    @commands.check(checks.database_connected)
    async def partner_add(self, ctx: MyContext, invite:args.Invite, *, description=''):
        """Add a partner in your list

        ..Example partners add https://discord.com/oauth2/authorize?client_id=486896267788812288&scope=bot

        ..Example partners add discord.gg/mee6
        
        ..Doc server.html#add-a-partner"""
        if isinstance(invite,int):
            try:
                item = await self.bot.fetch_user(invite)
                if not item.bot:
                    raise Exception
            except discord.NotFound:
                return await ctx.send(await self.bot._(ctx.guild.id, "partners.invalid-bot"))
            partner_type = 'bot'
        elif isinstance(invite,str):
            try:
                item = await self.bot.fetch_invite(invite)
            except discord.errors.NotFound:
                return await ctx.send(await self.bot._(ctx.guild.id, "partners.invalid-invite"))
            partner_type = 'guild'
        else:
            return
        current_list = [x['target'] for x in await self.bdd_get_guild(ctx.guild.id)]
        if str(item.id) in current_list:
            return await ctx.send(await self.bot._(ctx.guild, "partners.already-added"))
        if len(description) > 0:
            description = await self.bot.get_cog('Emojis').anti_code(description)
        await self.bdd_set_partner(guildID=ctx.guild.id,partnerID=item.id,partnerType=partner_type,desc=description)
        await ctx.send(await self.bot._(ctx.guild.id, "partners.added-partner"))
        # logs
        emb = discord.Embed(description=f"New partner added: {partner_type} {item.id}", color=10949630, timestamp=self.bot.utcnow())
        emb.set_footer(text=ctx.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.avatar)
        await self.bot.send_embed([emb])

    @partner_main.command(name='description',aliases=['desc'])
    @commands.check(checks.database_connected)
    async def partner_desc(self, ctx: MyContext, ID:int, *, description:str):
        """Add or modify a description for a partner

        ..Example partner desc 779713982 Very cool bot with tons of features, costs a lot
        
        ..Doc server.html#add-a-partner"""
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l) == 0:
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.invalid-partner"))
        l = l[0]
        description = await self.bot.get_cog('Emojis').anti_code(description)
        if await self.bdd_edit_partner(l['ID'],desc=description):
            await ctx.send(await self.bot._(ctx.guild.id, "partners.changed-desc"))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-error"))

    @partner_main.command(name='invite')
    async def partner_invite(self, ctx: MyContext, ID:int, new_invite:discord.Invite=None):
        """Get the invite of a guild partner. 
        If you specify an invite, the partner will be updated with this new invite
        
        ..Example partner invite 795897339 discord.gg/ruyvNYQ
        
        ..Doc server.html#change-a-server-invite"""
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l) == 0 or l[0]['type']!='guild':
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-server"))
        l = l[0]
        if new_invite is None:
            return await ctx.send('{}: discord.gg/{}'.format(await self.bot._(ctx.guild.id,'info.info.inv-4'),l['target']))
        if not await checks.has_admin(ctx):
            return
        if await self.bdd_edit_partner(l['ID'],target=new_invite.code):
            await ctx.send(await self.bot._(ctx.guild.id, "partners.changed-invite"))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-error"))

    @partner_main.command(name='remove')
    @commands.check(checks.has_admin)
    async def partner_remove(self, ctx: MyContext, ID:int):
        """Remove a partner from the partners list

        ..Example partner remove 800697342
        
        ..Doc server.html#remove-a-partner"""
        if not ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.missing-reactions"))
        l = await self.bdd_get_partner(ID,ctx.guild.id)
        if len(l) == 0:
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.invalid-partner"))
        l = l[0]
        if l['type']=='bot':
            try:
                bot = await self.bot.fetch_user(l['target'])
            except discord.NotFound:
                bot = l['target']
            msg = await ctx.send(await self.bot._(ctx.guild.id, "partners.confirm-bot", bot=bot))
        elif l['type']=='guild':
            try:
                server = (await self.bot.fetch_invite(l['target'])).guild.name
            except discord.NotFound:
                server = l['target']
            msg = await ctx.send(await self.bot._(ctx.guild.id, "partners.confirm-server", server=server))
        else:
            return
        await msg.add_reaction('✅')
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) == '✅'
        try:
            await ctx.bot.wait_for('reaction_add', timeout=10.0, check=check)
        except asyncio.TimeoutError:
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.del-canceled"))
        if await self.bdd_del_partner(l['ID']):
            await ctx.send(await self.bot._(ctx.guild.id, "partners.deleted"))
            emb = discord.Embed(description=f"Partner removed: {l['type']} {l['ID']}", color=10949630, timestamp=self.bot.utcnow())
            emb.set_footer(text=ctx.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.avatar)
            await self.bot.send_embed([emb])
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-error"))

    @partner_main.command(name="list")
    @commands.check(checks.has_manage_guild)
    async def partner_list(self, ctx: MyContext):
        """Get the list of every partners
        
        ..Doc server.html#list-every-partners"""
        f = ['','']
        lang = await self.bot._(ctx.guild.id,'_used_locale')
        tr_bot = await self.bot._(ctx.guild.id, "misc.bot")
        tr_guild = await self.bot._(ctx.guild.id, "misc.server")
        tr_added = await self.bot._(ctx.guild.id, "misc.added_at")
        tr_unknown = await self.bot._(ctx.guild.id, "misc.unknown")
        tr_owner = await self.bot._(ctx.guild.id,'info.info.guild-1')
        for l in await self.bdd_get_guild(ctx.guild.id):
            date = str(await ctx.bot.get_cog('TimeUtils').date(l['added_at'],lang=lang,year=True,hour=False)).strip()
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
                if server is None:
                    server = l['guild']
                    f[1] += f"{tr_unknown} (ID: {server})\n"
                else:
                    f[1] += f"{server.name} ({tr_owner} : {server.owner})\n"
        else:
            f[1] = await self.bot._(ctx.guild.id, "partners.missing-manage-guild")
        if len(f[0]) == 0:
            f[0] = await self.bot._(ctx.guild.id, "partners.no-partner")
        if len(f[1]) == 0:
            f[1] = await self.bot._(ctx.guild.id, "partners.no-partner-2")
        fields_name = await self.bot._(ctx.guild.id, "partners.partners-list")
        if ctx.can_send_embed:
            color = await ctx.bot.get_config(ctx.guild.id,'partner_color')
            if color is None:
                color = self.bot.get_cog('Servers').default_opt['partner_color']
            emb = discord.Embed(title=fields_name[0], color=color, timestamp=self.bot.utcnow())
            emb.set_thumbnail(url=ctx.guild.icon)
            emb.add_field(name=fields_name[1], value=f[0], inline=False)
            emb.add_field(name=self.bot.zws, value=self.bot.zws, inline=False)
            emb.add_field(name=fields_name[2], value=f[1], inline=False)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)
        else:
            await ctx.send(f"__{fields_name[0]}:__\n{f[0]}\n\n__{fields_name[1]}:__\n{f[1]}")

    @partner_main.command(name="color",aliases=['colour'])
    @commands.check(checks.has_manage_guild)
    async def partner_color(self, ctx: MyContext, color):
        """Change the color of the partners embed
    It has the same result as `config change partner_color`

    ..Example partners color yellow

    ..Example partners color #FF00FF
    
    ..Doc server.html#change-the-embed-color"""
        await self.bot.get_cog('Servers').conf_color(ctx,'partner_color',str(color))
    
    @partner_main.command(name='reload')
    @commands.check(checks.has_admin)
    @commands.cooldown(1,60,commands.BucketType.guild)
    async def partner_reload(self, ctx: MyContext):
        """Reload your partners channel
        
        ..Doc server.html#reload-your-list"""
        msg = await ctx.send(await self.bot._(ctx.guild, "rss.guild-loading", emoji=self.bot.get_cog('Emojis').customEmojis['loading']))
        channel = await self.bot.get_cog('Servers').get_server(criters=[f"`ID`={ctx.guild.id}"],columns=['partner_channel','partner_color'])
        if len(channel) == 0:
            return await msg.edit(content=await self.bot._(ctx.guild, "partners.no-channel"))
        chan: str = channel[0]['partner_channel'].split(';')[0]
        if not chan.isnumeric():
            return await msg.edit(content=await self.bot._(ctx.guild, "partners.no-channel"))
        chan = ctx.guild.get_channel(int(chan))
        if chan is None:
            return await msg.edit(content=await self.bot._(ctx.guild, "partners.no-channel"))
        count = await self.update_partners(chan,channel[0]['partner_color'])
        await msg.edit(content=await self.bot._(ctx.guild, "partners.reloaded", count=count))




def setup(bot:commands.Bot):
    bot.add_cog(Partners(bot))
