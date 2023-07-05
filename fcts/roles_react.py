import importlib
import re
from typing import Any, Optional, Tuple, Union

import discord
from discord.ext import commands

from libs.arguments import args
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks

importlib.reload(checks)
importlib.reload(args)


class RolesReact(commands.Cog):
    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'roles_react'
        self.table = 'roles_react_beta' if bot.beta else 'roles_react'
        self.guilds_which_have_roles = set()
        self.cache_initialized = False
        self.embed_color = 12118406
        self.footer_txt = 'ZBot roles reactions'

    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'roles_react_beta' if self.bot.beta else 'roles_react'

    async def prepare_react(self, payload: discord.RawReactionActionEvent) -> Tuple[discord.Message, discord.Role]:
        if payload.guild_id is None or payload.user_id == self.bot.user.id:
            return None, None
        if not self.cache_initialized:
            await self.rr_get_guilds()
        if payload.guild_id not in self.guilds_which_have_roles:
            return None, None
        chan: discord.TextChannel = self.bot.get_channel(payload.channel_id)
        if chan is None:
            return None, None
        try:
            msg = await chan.fetch_message(payload.message_id)
        except discord.NotFound: # we don't care about those
            return None, None
        except Exception as err:
            self.bot.log.warning(f"Could not fetch roles-reactions message {payload.message_id} in guild {payload.guild_id}: {err}")
            return None, None
        if len(msg.embeds) == 0 or msg.embeds[0].footer.text != self.footer_txt:
            return None, None
        temp = await self.rr_list_role(payload.guild_id, payload.emoji.id if payload.emoji.is_custom_emoji() else payload.emoji.name)
        if len(temp) == 0:
            return None, None
        role = self.bot.get_guild(payload.guild_id).get_role(temp[0]["role"])
        return msg, role

    @commands.Cog.listener('on_raw_reaction_add')
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.on_raw_reaction_event(payload, True)

    @commands.Cog.listener('on_raw_reaction_remove')
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.on_raw_reaction_event(payload, False)

    async def on_raw_reaction_event(self, payload: discord.RawReactionActionEvent, is_adding: bool):
        "handle reactions adding/removing events"
        if not self.bot.database_online:
            return
        # If axobot is already there, let it handle it
        if payload.guild_id and await self.bot.check_axobot_presence(guild_id=payload.guild_id):
            return
        try:
            msg, role = await self.prepare_react(payload)
            if msg is not None:
                user = msg.guild.get_member(payload.user_id)
                if user is None:
                    return
                await self.give_remove_role(user, role, msg.guild, msg.channel, is_adding, ignore_success=True)
        except discord.DiscordException as err:
            self.bot.dispatch("error", err)

    async def rr_get_guilds(self) -> set:
        """Get the list of guilds which have roles reactions"""
        query = "SELECT `guild` FROM `{}`;".format(self.table)
        async with self.bot.db_query(query) as query_results:
            self.guilds_which_have_roles = {x['guild'] for x in query_results}
        self.cache_initialized = True
        return self.guilds_which_have_roles

    async def rr_add_role(self, guild: int, role: int, emoji: str, desc: str):
        """Add a role reaction in the database"""
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id
        query = ("INSERT INTO `{}` (`guild`,`role`,`emoji`,`description`) VALUES (%(g)s,%(r)s,%(e)s,%(d)s);".format(self.table))
        async with self.bot.db_query(query, {'g': guild, 'r': role, 'e': emoji, 'd': desc}):
            pass
        return True

    async def rr_list_role(self, guild: int, emoji: str = None):
        """List role reaction in the database"""
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id
        if emoji is None:
            query = "SELECT * FROM `{}` WHERE guild={} ORDER BY added_at;".format(self.table, guild)
        else:
            query = "SELECT * FROM `{}` WHERE guild={} AND emoji='{}' ORDER BY added_at;".format(self.table, guild, emoji)
        liste: list[dict[str, Any]] = []
        async with self.bot.db_query(query) as query_results:
            for row in query_results:
                if emoji is None or row['emoji'] == str(emoji):
                    liste.append(row)
        return liste

    async def rr_remove_role(self, rr_id: int):
        """Remove a role reaction from the database"""
        query = ("DELETE FROM `{}` WHERE `ID`={};".format(self.table, rr_id))
        async with self.bot.db_query(query):
            pass
        return True

    @commands.group(name="roles_react", aliases=['role_react'])
    @commands.guild_only()
    async def rr_main(self, ctx: MyContext):
        """Manage your roles reactions

        ..Doc roles-reactions.html"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @rr_main.command(name="add")
    @commands.check(checks.has_manage_guild)
    @commands.check(checks.database_connected)
    async def rr_add(self, ctx: MyContext, emoji: args.AnyEmoji, role: discord.Role, *, description: str = ''):
        """Add a role reaction
        This role will be given when a membre click on a specific reaction
        Your description can only be a maximum of 150 characters

        ..Example roles_react add :upside_down: "weird users" role for weird members

        ..Example roles_react add :uwu: lolcats

        ..Doc roles-reactions.html#add-and-remove-a-reaction"""
        try:
            if role.name == '@everyone':
                raise commands.BadArgument(f'Role "{role.name}" not found')
            l = await self.rr_list_role(ctx.guild.id, emoji)
            if len(l) > 0:
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.already-1-rr"))
            max_rr: int = await self.bot.get_config(ctx.guild.id, 'roles_react_max_number')
            if len(l) >= max_rr:
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.too-many-rr", l=max_rr))
            await self.rr_add_role(ctx.guild.id, role.id, emoji, description[:150])
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.rr-added", r=role.name, e=emoji))
            self.guilds_which_have_roles.add(ctx.guild.id)

    @rr_main.command(name="remove")
    @commands.check(checks.database_connected)
    @commands.check(checks.has_manage_guild)
    async def rr_remove(self, ctx: MyContext, emoji):
        """Remove a role react

        ..Example roles_react remove :uwu:

        ..Doc roles-reactions.html#add-and-remove-a-reaction"""
        try:
            # if emoji is a custom one:
            old_emoji = emoji
            r = re.search(r'<a?:[^:]+:(\d+)>', emoji)
            if r is not None:
                emoji = r.group(1)
            l = await self.rr_list_role(ctx.guild.id, emoji)
            if len(l) == 0:
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.no-rr"))
            await self.rr_remove_role(l[0]['ID'])
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        role = ctx.guild.get_role(l[0]['role'])
        if role is None:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.rr-removed-2", e=old_emoji))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.rr-removed", r=role, e=old_emoji))
        if len(l) < 2:
            try:
                self.guilds_which_have_roles.remove(ctx.guild.id)
            except KeyError:
                pass

    async def create_list_embed(self, liste: list[dict], guild: discord.Guild):
        """Create a text with the roles list"""
        emojis: list[Union[str, discord.Emoji]] = []
        for k in liste:
            if len(k['emoji']) > 15 and k['emoji'].isnumeric():
                if not (temp := self.bot.get_emoji(int(k['emoji']))):
                    # if we couldn't get the emoji from cache, try to load from the guild
                    try:
                        temp = await guild.fetch_emoji(int(k['emoji']))
                    except discord.errors.NotFound:
                        emojis.append(k['emoji'])
                        continue
                emojis.append(temp)
                k['emoji'] = str(temp)
            else:
                emojis.append(k['emoji'])
        result = [
            f"{x['emoji']}   <@&{x['role']}> - *{x['description']}*" if len(
                x['description']) > 0 else f"{x['emoji']}   <@&{x['role']}>"
            for x in liste
        ]
        return '\n'.join(result), emojis

    @rr_main.command(name="list")
    @commands.check(checks.database_connected)
    @commands.check(checks.bot_can_embed)
    async def rr_list(self, ctx: MyContext):
        """List every roles reactions of your server

        ..Doc roles-reactions.html#list-every-roles-reactions"""
        try:
            roles_list = await self.rr_list_role(ctx.guild.id)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            des, _ = await self.create_list_embed(roles_list, ctx.guild)
            max_rr: int = await self.bot.get_config(ctx.guild.id, 'roles_react_max_number')
            title = await self.bot._(ctx.guild.id, "roles_react.rr-list", n=len(roles_list), m=max_rr)
            emb = discord.Embed(title=title, description=des, color=self.embed_color, timestamp=ctx.message.created_at)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)

    @rr_main.command(name="get", aliases=['display'])
    @commands.check(checks.database_connected)
    @commands.check(checks.bot_can_embed)
    async def rr_get(self, ctx: MyContext):
        """Send the roles embed
It will only display the whole message with reactions. Still very cool tho

..Doc roles-reactions.html#get-or-leave-a-role"""
        try:
            roles_list = await self.rr_list_role(ctx.guild.id)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        des, emojis = await self.create_list_embed(roles_list, ctx.guild)
        title = await self.bot._(ctx.guild.id, "roles_react.rr-embed")
        emb = discord.Embed(title=title, description=des, color=self.embed_color, timestamp=ctx.message.created_at)
        emb.set_footer(text=self.footer_txt)
        msg = await ctx.send(embed=emb)
        for emoji in emojis:
            try:
                await msg.add_reaction(emoji)
            except (discord.Forbidden, discord.NotFound):
                pass
            except discord.HTTPException as err:
                if err.status == 400:
                    continue
                self.bot.dispatch("command_error", ctx, err)
                break

    @rr_main.command(name="join")
    @commands.check(checks.database_connected)
    async def rr_join(self, ctx: MyContext, *, role: discord.Role):
        """Join a role without using reactions
Opposite is the subcommand 'leave'

..Example roles_react join Announcements

..Doc roles-reactions.html#get-or-leave-a-role"""
        if not role.id in [x['role'] for x in await self.rr_list_role(ctx.guild.id)]:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.role-not-in-list"))
            return
        await self.give_remove_role(ctx.author, role, ctx.guild, ctx.channel)

    @rr_main.command(name="leave")
    @commands.check(checks.database_connected)
    async def rr_leave(self, ctx: MyContext, *, role: discord.Role):
        """Leave a role without using reactions
Opposite is the subcommand 'join'

..Example roles_react leave Announcements

..Doc roles-reactions.html#get-or-leave-a-role"""
        if not role.id in [x['role'] for x in await self.rr_list_role(ctx.guild.id)]:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.role-not-in-list"))
            return
        await self.give_remove_role(ctx.author, role, ctx.guild, ctx.channel, give=False)

    async def give_remove_role(self, user: discord.Member, role: discord.Role, guild: discord.Guild,
                               channel: Union[discord.TextChannel, discord.Thread], give: bool = True,
                               ignore_success: bool = False, ignore_failure: bool = False):
        """Add or remove a role to a user if possible"""
        if self.bot.zombie_mode:
            return
        if not ignore_failure:
            if role in user.roles and give:
                if not ignore_success:
                    await channel.send(await self.bot._(guild.id, "roles_react.already-have"))
                return
            elif not (role in user.roles or give):
                if not ignore_success:
                    await channel.send(await self.bot._(guild.id, "roles_react.already-dont-have"))
                return
            if not guild.me.guild_permissions.manage_roles:
                return await channel.send(await self.bot._(guild.id, 'moderation.mute.cant-mute'))
            if role.position >= guild.me.top_role.position:
                return await channel.send(await self.bot._(guild.id, 'moderation.role.too-high', r=role.name))
        if stats_cog := self.bot.get_cog("BotStats"):
            stats_cog.role_reactions["added" if give else "removed"] += 1
        try:
            if give:
                await user.add_roles(role, reason="Roles reaction")
            else:
                await user.remove_roles(role, reason="Roles reaction")
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err)
        else:
            if not ignore_success:
                await channel.send(await self.bot._(guild.id, "roles_react.role-given" if give else "roles_react.role-lost", r=role.name))

    @rr_main.command(name='update')
    @commands.check(checks.database_connected)
    async def rr_update(self, ctx: MyContext, embed: discord.Message, change_description: Optional[bool] = True, emojis: commands.Greedy[args.AnyEmoji] = None):
        """Update an Axobot message to refresh roles/reactions
        If you don't want to update the embed content (for example if it's a custom embed) then you can use 'False' as a second argument, and I will only check the reactions
        Specifying a list of emojis will update the embed only for those emojis, and ignore other roles reactions

        ..Example roles_react update https://discord.com/channels/356067272730607628/625320847296430120/707726569430319164 False

        ..Example roles_react update 707726569430319164 True :cool: :vip:

        ..Doc roles-reactions.html#update-your-embed"""
        if embed.author != ctx.guild.me:
            return await ctx.send(await self.bot._(ctx.guild, "roles_react.not-zbot-msg"))
        if len(embed.embeds) != 1 or embed.embeds[0].footer.text != self.footer_txt:
            return await ctx.send(await self.bot._(ctx.guild, "roles_react.not-zbot-embed"))
        if not embed.channel.permissions_for(embed.guild.me).add_reactions:
            return await ctx.send(await self.bot._(ctx.guild, 'fun', "cant-react"))
        emb = embed.embeds[0]
        try:
            full_list: dict[str, dict[str, Any]] = {x['emoji']: x for x in await self.rr_list_role(ctx.guild.id)}
        except Exception as err:
            return self.bot.dispatch("command_error", ctx, err)
        if emojis is not None:
            emojis_ids: list[str] = [str(x.id) if isinstance(x, discord.Emoji)
                      else str(x) for x in emojis]
            full_list = [full_list[x] for x in emojis_ids if x in full_list]
        else:
            full_list = list(full_list.values())
        desc, proper_emojis = await self.create_list_embed(full_list, ctx.guild)
        reacts = [x.emoji for x in embed.reactions]
        for emoji in proper_emojis:
            if emoji not in reacts:
                await embed.add_reaction(emoji)
        if emb.description != desc and change_description:
            emb.description = desc
            await embed.edit(embed=emb)
            await ctx.send(await self.bot._(ctx.guild, "roles_react.embed-edited"))
        else:
            await ctx.send(await self.bot._(ctx.guild, "roles_react.reactions-edited"))


async def setup(bot):
    await bot.add_cog(RolesReact(bot))
