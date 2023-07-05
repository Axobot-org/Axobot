import datetime
import importlib
import time
from typing import Optional, Union

import aiohttp
import discord
from discord.ext import commands, tasks

from libs.arguments import args
from libs.bot_classes import SUPPORT_GUILD_ID, Axobot, MyContext
from libs.checks import checks
from libs.views import ConfirmView

importlib.reload(args)
importlib.reload(checks)

utc = datetime.timezone.utc


class Partners(commands.Cog):
    "Manage bots and server partners of your server"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'partners'
        self.table = 'partners_beta' if bot.beta else 'partners'

    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'partners_beta' if self.bot.beta else 'partners'

    async def cog_load(self):
        self.refresh_loop.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.refresh_loop.cancel() # pylint: disable=no-member

    @tasks.loop(time=[
        datetime.time(hour=7, tzinfo=utc),
        datetime.time(hour=14, tzinfo=utc),
        datetime.time(hour=21, tzinfo=utc)
    ], reconnect=True)
    async def refresh_loop(self):
        """Refresh partners channels every 7 hours"""
        await self.bot.wait_until_ready()
        start = time.time()
        channels = await self.get_partners_channels()
        self.bot.log.info(f"[Partners] Reloading channels ({len(channels)} planned guilds)...")
        count = [0,0]
        for channel in channels:
            try:
                count[0] += 1
                count[1] += await self.update_partners(channel)
            except Exception as err:
                self.bot.dispatch("error", err)
        delta_time = round(time.time()-start, 3)
        emb = discord.Embed(
            description=f'**Partners channels updated** in {delta_time}s ({count[0]} channels - {count[1]} partners)',
            color=10949630,
            timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")

    @refresh_loop.error
    async def on_refresh_loop_error(self, error):
        self.bot.dispatch("error", error, "When refreshing partners channels")

    async def generate_id(self):
        return round(time.time()/2)

    async def db_get_partner(self, partner_id: int, guild_id: int) -> Optional[dict]:
        """Return a partner based on its ID"""
        query = f"SELECT * FROM `{self.table}` WHERE `ID` = %s AND `guild` = %s"
        async with self.bot.db_query(query, (partner_id, guild_id), fetchone=True) as query_result:
            return query_result

    async def db_get_partners_of_guild(self, guild_id: int):
        """Return every partners of a guild"""
        query = f"SELECT * FROM `{self.table}` WHERE `guild` = %s"
        async with self.bot.db_query(query, (guild_id, )) as query_results:
            results = list(query_results)
        return results

    async def db_get_partnered(self, invites: list):
        """Return every guilds which has this one as partner"""
        if len(invites) == 0:
            return []
        condition = " OR ".join(["`target` = %s" for _ in invites])
        params = [invite.code for invite in invites]
        query = f"SELECT * FROM `{self.table}` WHERE `type`='guild' AND ({condition})"
        async with self.bot.db_query(query, params) as query_results:
            results = list(query_results)
        return results

    async def db_set_partner(self, guild_id: int, partner_id: str, partner_type: str, desc: str):
        """Add a partner into a server"""
        new_id = await self.generate_id()
        query = f"INSERT INTO `{self.table}` (`ID`, `guild`, `messageId`, `target`, `type`, `description`) \
            VALUES (%(i)s, %(g)s, %(m)s, %(ta)s, %(ty)s, %(d)s);"
        params = { 'i': new_id, 'g': guild_id, 'm': 0, 'ta': partner_id, 'ty': partner_type, 'd': desc }
        async with self.bot.db_query(query, params):
            pass
        return True

    async def db_edit_partner(self,partner_id: int, target: str=None, desc: str=None, msg: int=None):
        """Modify a partner"""
        try:
            values: list[str] = []
            params = { 'id': partner_id }
            if target is not None:
                values.append("`target` = %(target)s")
                params['target'] = target
            if desc is not None:
                values.append("`description` = %(desc)s")
                params['desc'] = desc
            if msg is not None:
                values.append("`messageID` = %(msg)s")
                params['msg'] = msg
            query = f"UPDATE `{self.table}` SET {', '.join(values)} WHERE `ID` = %(id)s;"
            async with self.bot.db_query(query, params):
                pass
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False

    async def db_del_partner(self, partner_id:int):
        """Delete a partner from a guild list"""
        query = f"DELETE FROM `{self.table}` WHERE `ID` = %s"
        async with self.bot.db_query(query, (partner_id,)):
            pass
        return True

    async def db_get_bot_guilds(self, bot_id: int) -> Optional[int]:
        "Try to fetch the bot guilds count from the internal database"
        if bot_id == 159985870458322944:
            bot_id = 159985415099514880
        elif bot_id == 155149108183695360:
            bot_id = 161660517914509312
        query = "SELECT server_count FROM `statsbot`.`biggest_bots` WHERE bot_id = %s ORDER BY `date` DESC LIMIT 1"
        async with self.bot.db_query(query, (bot_id,), fetchone=True) as query_results:
            if query_results:
                return query_results['server_count']
        return None

    async def get_bot_guilds(self, bot_id:int, session:aiohttp.ClientSession) -> Optional[int]:
        """Get the guilds count of a bot
        None if unknown bot/count not provided"""
        db_count = await self.db_get_bot_guilds(bot_id)
        async with session.get(f'https://top.gg/api/bots/{bot_id}/stats', headers={'Authorization': self.bot.dbl_token}) as resp:
            ans: dict = await resp.json()
        if 'server_count' in ans:
            api_count: int = ans['server_count']
            if db_count and api_count < db_count*0.95:
                return db_count
            return api_count
        return None

    async def get_bot_owners(self, bot_id:int, session:aiohttp.ClientSession) -> list[Union[discord.User, int]]:
        """Get the owners list of a bot
        Empty list if unknown bot/owners not provided"""
        async with session.get(f'https://top.gg/api/bots/{bot_id}', headers={'Authorization': self.bot.dbl_token}) as resp:
            ans: dict = await resp.json()
        owners = []
        if 'owners' in ans:
            for owner_id in ans['owners']:
                try:
                    owners.append(await self.bot.fetch_user(owner_id))
                except discord.NotFound:
                    owners.append(owner_id)
        return owners

    async def get_partners_channels(self):
        """Return every partners channels"""
        channels: list[discord.abc.GuildChannel] = []
        for guild in self.bot.guilds:
            if channel := await self.bot.get_config(guild.id, "partner_channel"):
                channels.append(channel)
        return channels

    async def update_partners(self, channel: discord.TextChannel, color: Optional[int] = None) -> int:
        """Update every partners of a channel"""
        if not channel.permissions_for(channel.guild.me).embed_links:
            return 0
        partners = await self.db_get_partners_of_guild(channel.guild.id)
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
            color = await self.bot.get_config(channel.guild.id, "partner_color")
        session = aiohttp.ClientSession(loop=self.bot.loop)
        for partner in partners:
            target_desc = partner['description']
            if partner['type'] == 'bot':
                title, fields, image = await self.update_partner_bot(
                    tr_bot, tr_guilds, tr_invite, tr_owner, tr_click, session, partner
                )
            else:
                try:
                    title, fields, image, target_desc = await self.update_partner_guild(
                        tr_guild, tr_members, tr_unknown, tr_invite, tr_click, channel, partner, target_desc
                    )
                except discord.NotFound:
                    continue
            emb = discord.Embed(title=title, description=target_desc, color=color, timestamp=self.bot.utcnow())
            emb.set_footer(text=partner['ID'])
            if image:
                emb.set_thumbnail(url=image)
            for field in fields:
                if field:
                    emb.add_field(**field)
            if self.bot.zombie_mode:
                return
            try:
                msg = await channel.fetch_message(partner['messageID'])
                await msg.edit(embed=emb)
            except (discord.errors.NotFound, discord.errors.Forbidden):
                msg = await channel.send(embed=emb)
                await self.db_edit_partner(partner_id=partner['ID'], msg=msg.id)
            except Exception as err:
                msg = await channel.send(embed=emb)
                await self.db_edit_partner(partner_id=partner['ID'], msg=msg.id)
                self.bot.dispatch("error", err)
            count += 1
        await session.close()
        return count

    async def update_partner_bot(self, tr_bot: str, tr_guilds: str, tr_invite: str, tr_owner: str, tr_click: str,
                                 session: aiohttp.ClientSession, partner: dict):
        """Update a bot partner embed"""
        image = ""
        title = "**" + tr_bot.capitalize() + "** "
        fields = []
        try:
            title += str(await self.bot.fetch_user(int(partner['target'])))
            # guild count field
            guild_nbr = await self.get_bot_guilds(partner['target'], session)
            if guild_nbr is not None:
                fields.append({
                    'name': tr_guilds.capitalize(),
                    'value': str(guild_nbr)
                })
            # owners field
            owners = await self.get_bot_owners(partner['target'], session)
            if owners:
                fields.append({
                    'name': tr_owner.capitalize(),
                    'value': ", ".join([str(u) for u in owners])
                })
            usr = await self.bot.fetch_user(int(partner['target']))
            image = usr.display_avatar.with_static_format("png") if usr else ""
        except discord.NotFound:
            title += "ID: " + partner['target']
        except Exception as err:
            usr = await self.bot.fetch_user(int(partner['target']))
            image = usr.display_avatar.url if usr else ""
            self.bot.dispatch("error", err)
        perm = discord.Permissions.all()
        perm.update(administrator=False)
        oauth_url = discord.utils.oauth_url(partner['target'], permissions=perm)
        fields.append({
            'name': tr_invite.capitalize(),
            'value': f"[{tr_click.capitalize()}]({oauth_url})"
        })
        return title, fields, image

    async def update_partner_guild(self, tr_guild: str, tr_members: str, tr_unknown: str, tr_invite: str, tr_click: str,
                                   channel: discord.TextChannel, partner: dict, target_desc: str):
        """Update a guild partner embed"""
        title = "**" + tr_guild.capitalize() + "** "
        try:
            inv = await self.bot.fetch_invite(partner['target'])
        except discord.NotFound as err:
            raise err
        image = str(inv.guild.icon) if inv.guild.icon else None
        if isinstance(inv, discord.Invite) and not inv.revoked and inv.guild:
            title += str(inv.guild.name)
            field1 = {
                'name': tr_members.capitalize(),
                'value': str(inv.approximate_member_count)
            }
            await self.give_roles(inv, channel.guild)
        else:
            title += tr_unknown
            field1 = None
        field2 = {
            'name': tr_invite.capitalize(),
            'value': f"[{tr_click.capitalize()}](https://discord.gg/{partner['target']})"
        }
        if len(target_desc) == 0:
            target_desc: Optional[str] = await self.bot.get_config(inv.guild.id, 'description')
        return title, (field1, field2), image, target_desc

    async def give_roles(self,invite:discord.Invite,guild:discord.Guild):
        """Give a role to admins of partners"""
        if not isinstance(invite.guild,discord.Guild):
            return
        if guild.id == SUPPORT_GUILD_ID.id and self.bot.beta:
            return
        role = await self.bot.get_config(guild.id, 'partner_role')
        if role is None:
            return
        admins = [x for x in invite.guild.members if not x.bot and x.guild_permissions.administrator]
        for admin in admins:
            if admin in guild.members:
                member = guild.get_member(admin.id)
                if role not in member.roles:
                    try:
                        await member.add_roles(role)
                    except discord.HTTPException:
                        pass


    @commands.group(name="partner",aliases=['partners'])
    @commands.guild_only()
    @commands.check(checks.database_connected)
    @commands.check(checks.has_manage_guild)
    async def partner_main(self, ctx: MyContext):
        """Manage the partners of your server

        ..Doc server.html#partners-system"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @partner_main.command(name='add')
    @commands.check(checks.database_connected)
    async def partner_add(self, ctx: MyContext, invite: args.Invite, *, description=''):
        """Add a partner in your list

        ..Example partners add https://discord.com/oauth2/authorize?client_id=486896267788812288&scope=bot

        ..Example partners add discord.gg/mee6

        ..Doc server.html#add-a-partner"""
        if isinstance(invite, int):
            try:
                item = await self.bot.fetch_user(invite)
                if not item.bot:
                    raise ValueError("Not a bot")
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
        current_list = [x['target'] for x in await self.db_get_partners_of_guild(ctx.guild.id)]
        if str(item.id) in current_list:
            return await ctx.send(await self.bot._(ctx.guild, "partners.already-added"))
        if len(description) > 0:
            description = await self.bot.emojis_manager.anti_code(description)
        await self.db_set_partner(guild_id=ctx.guild.id,partner_id=item.id,partner_type=partner_type,desc=description)
        await ctx.send(await self.bot._(ctx.guild.id, "partners.added-partner"))
        # logs
        emb = discord.Embed(description=f"New partner added: {partner_type} {item.id}", color=10949630,
                            timestamp=self.bot.utcnow())
        emb.set_footer(text=ctx.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)

    @partner_main.command(name='description', aliases=['desc'])
    @commands.check(checks.database_connected)
    async def partner_desc(self, ctx: MyContext, partner_id:int, *, description:str):
        """Add or modify a description for a partner

        ..Example partner desc 779713982 Very cool bot with tons of features, costs a lot

        ..Doc server.html#add-a-partner"""
        partner = await self.db_get_partner(partner_id,ctx.guild.id)
        if not partner:
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.invalid-partner"))
        description = await self.bot.emojis_manager.anti_code(description)
        if await self.db_edit_partner(partner['ID'], desc=description):
            await ctx.send(await self.bot._(ctx.guild.id, "partners.changed-desc"))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-error"))

    @partner_main.command(name='invite')
    async def partner_invite(self, ctx: MyContext, partner_id: int, new_invite: Optional[discord.Invite]=None):
        """Get the invite of a guild partner.
        If you specify an invite, the partner will be updated with this new invite

        ..Example partner invite 795897339 discord.gg/ruyvNYQ

        ..Doc server.html#change-a-server-invite"""
        partner = await self.db_get_partner(partner_id,ctx.guild.id)
        if not partner or partner['type']!='guild':
            return await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-server"))
        if new_invite is None:
            txt = await self.bot._(ctx.guild.id,'info.info.inv-4')
            return await ctx.send(f"{txt}: discord.gg/{partner['target']}")
        if not await checks.has_admin(ctx):
            return
        if await self.db_edit_partner(partner['ID'],target=new_invite.code):
            await ctx.send(await self.bot._(ctx.guild.id, "partners.changed-invite"))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-error"))

    @partner_main.command(name='remove')
    @commands.check(checks.has_admin)
    async def partner_remove(self, ctx: MyContext, partner_id: int):
        """Remove a partner from the partners list

        ..Example partner remove 800697342

        ..Doc server.html#remove-a-partner"""
        if not ctx.channel.permissions_for(ctx.guild.me).add_reactions:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.missing-reactions"))
            return
        partner = await self.db_get_partner(partner_id,ctx.guild.id)
        if not partner:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.invalid-partner"))
            return
        if partner['type']=='bot':
            try:
                bot = await self.bot.fetch_user(partner['target'])
            except discord.NotFound:
                bot = partner['target']
            confirm_txt = await self.bot._(ctx.guild.id, "partners.confirm-bot", bot=bot)
        elif partner['type']=='guild':
            try:
                server = (await self.bot.fetch_invite(partner['target'])).guild.name
            except discord.NotFound:
                server = partner['target']
            confirm_txt = await self.bot._(ctx.guild.id, "partners.confirm-server", server=server)
        else:
            return
        confirm_view = ConfirmView(
            self.bot, ctx.channel,
            validation=lambda inter: inter.user == ctx.author,
            ephemeral=False)
        await confirm_view.init()
        await ctx.send(confirm_txt, view=confirm_view)
        await confirm_view.wait()
        if confirm_view.value is None:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.del-canceled"))
            return
        if not confirm_view.value:
            return
        if await self.db_del_partner(partner['ID']):
            await ctx.send(await self.bot._(ctx.guild.id, "partners.deleted"))
            emb = discord.Embed(description=f"Partner removed: {partner['type']} {partner['ID']}", color=10949630,
                                timestamp=self.bot.utcnow())
            emb.set_footer(text=ctx.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "partners.unknown-error"))

    @partner_main.command(name="list")
    @commands.check(checks.has_manage_guild)
    async def partner_list(self, ctx: MyContext):
        """Get the list of every partners

        ..Doc server.html#list-every-partners"""
        lists = ['', '']
        tr_bot = await self.bot._(ctx.guild.id, "misc.bot")
        tr_guild = await self.bot._(ctx.guild.id, "misc.server")
        tr_added = await self.bot._(ctx.guild.id, "misc.added_at")
        tr_unknown = await self.bot._(ctx.guild.id, "misc.unknown")
        tr_owner = await self.bot._(ctx.guild.id,'info.info.guild-1')
        for partner in await self.db_get_partners_of_guild(ctx.guild.id):
            date = f"<t:{partner['added_at'].timestamp():.0f}:D>"
            if partner['type']=='bot':
                try:
                    bot = await self.bot.fetch_user(partner['target'])
                except discord.HTTPException:
                    bot = partner['target']
                lists[0] += f"[{partner['ID']}] **{tr_bot.capitalize()}** `{bot}` ({tr_added} {date})\n"
            elif partner['type']=='guild':
                try:
                    server = (await self.bot.fetch_invite(partner['target'])).guild.name
                except discord.HTTPException:
                    server = 'discord.gg/'+partner['target']
                lists[0] += f"[{partner['ID']}] **{tr_guild.capitalize()}** `{server}` ({tr_added} {date})\n"
        if ctx.guild.me.guild_permissions.manage_guild:
            for partner in await self.db_get_partnered(await ctx.guild.invites()):
                server = ctx.bot.get_guild(partner['guild'])
                if server is None:
                    server = partner['guild']
                    lists[1] += f"{tr_unknown} (ID: {server})\n"
                else:
                    lists[1] += f"{server.name} ({tr_owner} : {server.owner})\n"
        else:
            lists[1] = await self.bot._(ctx.guild.id, "partners.missing-manage-guild")
        if len(lists[0]) == 0:
            lists[0] = await self.bot._(ctx.guild.id, "partners.no-partner")
        if len(lists[1]) == 0:
            lists[1] = await self.bot._(ctx.guild.id, "partners.no-partner-2")
        fields_name = await self.bot._(ctx.guild.id, "partners.partners-list")
        if ctx.can_send_embed:
            color = await ctx.bot.get_config(ctx.guild.id, "partner_color")
            emb = discord.Embed(title=fields_name[0], color=color, timestamp=self.bot.utcnow())
            if ctx.guild.icon:
                emb.set_thumbnail(url=ctx.guild.icon)
            emb.add_field(name=fields_name[1], value=lists[0], inline=False)
            emb.add_field(name=self.bot.zws, value=self.bot.zws, inline=False)
            emb.add_field(name=fields_name[2], value=lists[1], inline=False)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)
        else:
            await ctx.send(f"__{fields_name[0]}:__\n{lists[0]}\n\n__{fields_name[1]}:__\n{lists[1]}")

    @partner_main.command(name="color", aliases=['colour'])
    @commands.check(checks.has_manage_guild)
    async def partner_color(self, ctx: MyContext, color: str):
        """Change the color of the partners embed
    It has the same result as `config set partner_color`

    ..Example partners color yellow

    ..Example partners color #FF00FF

    ..Doc server.html#change-the-embed-color"""
        await self.bot.get_cog('ServerConfig').config_set_cmd(ctx, "partner_color", color)

    @partner_main.command(name="reload")
    @commands.check(checks.has_manage_guild)
    @commands.cooldown(1,60,commands.BucketType.guild)
    async def partner_reload(self, ctx: MyContext):
        """Reload your partners channel

        ..Doc server.html#reload-your-list"""
        msg = await ctx.send(await self.bot._(ctx.guild, "rss.guild-loading", emoji=self.bot.emojis_manager.customs['loading']))
        channel: Optional[discord.abc.GuildChannel] = await self.bot.get_config(ctx.guild.id, "partner_channel")
        if channel is None:
            return await msg.edit(content=await self.bot._(ctx.guild, "partners.no-channel"))
        count = await self.update_partners(channel)
        await msg.edit(content=await self.bot._(ctx.guild, "partners.reloaded", count=count))


async def setup(bot):
    await bot.add_cog(Partners(bot))
