import datetime
import re
from collections import defaultdict
from typing import TypedDict

import discord
from discord import app_commands
from discord.ext import commands

from libs.arguments import DiscordOrUnicodeEmoji
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks
from libs.getch_methods import getch_member


class RoleReactionRow(TypedDict):
    "A role reaction row in the database"
    ID: int
    guild: int
    role: int
    emoji: str
    description: str
    added_at: datetime.datetime
    emoji_display: str | None

RoleDescription = app_commands.Range[str, 1, 150]


class RolesReact(commands.Cog):
    "Allow members to get new roles by clicking on reactions"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'roles_react'
        self.table = 'roles_react_beta' if bot.beta else 'roles_react'
        self.cache: dict[int, dict[int, RoleReactionRow]] = defaultdict(dict)
        self.cache_initialized = False
        self.embed_color = 12118406
        self.footer_texts = ("Axobot roles reactions", "ZBot roles reactions")

    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'roles_react_beta' if self.bot.beta else 'roles_react'

    async def prepare_react(self, payload: discord.RawReactionActionEvent) -> tuple[discord.Message, discord.Role] | None:
        "Handle new added/removed reactions and check if they are roles reactions"
        if payload.guild_id is None or payload.user_id == self.bot.user.id:
            return None
        if not self.cache_initialized:
            await self.db_init_cache()
        if payload.guild_id not in self.cache:
            return None
        chan = self.bot.get_channel(payload.channel_id)
        if chan is None or isinstance(chan, discord.abc.PrivateChannel):
            return None
        try:
            msg = await chan.fetch_message(payload.message_id)
        except discord.NotFound: # we don't care about those
            return None
        except Exception as err:
            self.bot.log.warning(
                f"Could not fetch roles-reactions message {payload.message_id} in guild {payload.guild_id}: {err}"
            )
            return None
        if len(msg.embeds) == 0 or msg.embeds[0].footer.text not in self.footer_texts:
            return None
        temp = await self.db_get_role_from_emoji(
            payload.guild_id,
            payload.emoji.id if payload.emoji.is_custom_emoji() else payload.emoji.name
        )
        if not temp:
            return None
        role = self.bot.get_guild(payload.guild_id).get_role(temp["role"])
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
        try:
            if data := await self.prepare_react(payload):
                msg, role = data
                member = await getch_member(msg.guild, payload.user_id)
                if member is None:
                    return
                await self.give_remove_role(member, role, msg.guild, msg.channel, is_adding)
        except discord.DiscordException as err:
            self.bot.dispatch("error", err)

    async def _add_rr_to_cache(self, rr: RoleReactionRow):
        """Add a role reaction to the cache"""
        if guild := self.bot.get_guild(rr['guild']):
            rr["emoji_display"] = await self.get_emoji_display_form(guild, rr['emoji'])
        else:
            rr["emoji_display"] = rr['emoji']
        self.cache[rr['guild']][rr['ID']] = rr

    async def db_init_cache(self):
        """Get the list of guilds which have roles reactions"""
        self.cache_initialized = False
        self.cache.clear()
        query = f"SELECT * FROM `{self.table}`;"
        async with self.bot.db_query(query) as query_results:
            for row in query_results:
                await self._add_rr_to_cache(row)
        self.cache_initialized = True

    async def db_add_role(self, guild: int, role: int, emoji: str, desc: str):
        """Add a role reaction in the database"""
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id
        query = f"INSERT INTO `{self.table}` (`guild`,`role`,`emoji`,`description`) VALUES (%(g)s,%(r)s,%(e)s,%(d)s);"
        async with self.bot.db_query(query, {'g': guild, 'r': role, 'e': emoji, 'd': desc}):
            pass
        return True

    async def db_get_roles(self, guild_id: int):
        """List role reaction in the database"""
        query = f"SELECT * FROM `{self.table}` WHERE guild=%s ORDER BY added_at;"
        rr_list: list[RoleReactionRow] = []
        async with self.bot.db_query(query, (guild_id,)) as query_results:
            for row in query_results:
                rr_list.append(row)
        return rr_list

    async def db_get_role_from_emoji(self, guild_id: int, emoji: discord.Emoji | int | str) -> RoleReactionRow | None:
        """Get a role reaction from the database corresponding to an emoji"""
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id
        query = f"SELECT * FROM `{self.table}` WHERE guild=%(g)s AND emoji=%(e)s ORDER BY added_at;"
        async with self.bot.db_query(query, {"g": guild_id, "e": str(emoji)}, fetchone=True) as query_results:
            return query_results or None

    async def db_remove_role(self, rr_id: int):
        """Remove a role reaction from the database"""
        query = f"DELETE FROM `{self.table}` WHERE `ID`=%s;"
        async with self.bot.db_query(query, (rr_id,)):
            pass
        return True

    async def db_edit_description(self, rr_id: int, new_description: str):
        """Edit the description of a role reaction"""
        query = f"UPDATE `{self.table}` SET `description`=%s WHERE `ID`=%s;"
        async with self.bot.db_query(query, (new_description, rr_id)):
            pass
        return True

    async def give_remove_role(self, user: discord.Member, role: discord.Role, guild: discord.Guild,
                               channel: discord.TextChannel | discord.Thread, give: bool = True,
                               ignore_failure: bool = False):
        """Add or remove a role to a user if possible"""
        if self.bot.zombie_mode:
            return
        if not ignore_failure:
            if (role in user.roles and give) or (role not in user.roles and not give):
                return
            try:
                if not guild.me.guild_permissions.manage_roles:
                    return await channel.send(await self.bot._(guild.id, 'moderation.mute.cant-mute'))
                if role.position >= guild.me.top_role.position:
                    return await channel.send(await self.bot._(guild.id, 'moderation.role.too-high', r=role.name))
            except discord.Forbidden:
                return
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

    async def get_emoji_display_form(self, guild: discord.Guild, raw_emoji: str):
        """Returns the emoji in a displayable form"""
        if len(raw_emoji) > 15 and raw_emoji.isnumeric():
            if not (emoji := self.bot.get_emoji(int(raw_emoji))):
                # if we couldn't get the emoji from cache, try to load from the guild
                try:
                    emoji = await guild.fetch_emoji(int(raw_emoji))
                except discord.errors.NotFound:
                    return raw_emoji
            return str(emoji)
        return raw_emoji

    @commands.hybrid_group(name="roles-react")
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.guild)
    @app_commands.default_permissions(manage_guild=True)
    async def rr_main(self, ctx: MyContext):
        """Manage your roles reactions

        ..Doc roles-reactions.html"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @rr_main.command(name="add")
    @commands.check(checks.has_manage_guild)
    @commands.check(checks.database_connected)
    async def rr_add(self, ctx: MyContext, emoji: DiscordOrUnicodeEmoji, role: discord.Role, *,
                     description: RoleDescription = ''):
        """Add a role reaction
        This role will be given when a membre click on a specific reaction
        Your description can only be a maximum of 150 characters

        ..Example roles_react add :upside_down: "weird users" role for weird members

        ..Example roles_react add :uwu: lolcats

        ..Doc roles-reactions.html#add-and-remove-a-reaction"""
        try:
            if role.name == '@everyone':
                raise commands.BadArgument(f'Role "{role.name}" not found')
            await ctx.defer()
            if await self.db_get_role_from_emoji(ctx.guild.id, emoji):
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.already-1-rr"))
            max_rr: int = await self.bot.get_config(ctx.guild.id, 'roles_react_max_number')
            existing_list = await self.db_get_roles(ctx.guild.id)
            if len(existing_list) >= max_rr:
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.too-many-rr", l=max_rr))
            await self.db_add_role(ctx.guild.id, role.id, emoji, description)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.rr-added", r=role.name, e=emoji))
            if rr := await self.db_get_role_from_emoji(ctx.guild.id, emoji):
                await self._add_rr_to_cache(rr)
            else:
                self.bot.log.warning(f"Could not add role reaction {emoji} in cache")

    @rr_main.command(name="remove")
    @commands.check(checks.database_connected)
    @commands.check(checks.has_manage_guild)
    async def rr_remove(self, ctx: MyContext, emoji: str):
        """Remove a role react

        ..Example roles_react remove :uwu:

        ..Doc roles-reactions.html#add-and-remove-a-reaction"""
        await ctx.defer()
        try:
            # if emoji is a custom one: extract the id
            old_emoji = emoji
            r = re.search(r'<a?:[^:]+:(\d+)>', emoji)
            if r is not None:
                emoji = r.group(1)
            role_react = await self.db_get_role_from_emoji(ctx.guild.id, emoji)
            if role_react is None:
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.no-rr"))
            await self.db_remove_role(role_react['ID'])
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        role = ctx.guild.get_role(role_react['role'])
        if role is None:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.rr-removed-2", e=old_emoji))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "roles_react.rr-removed", r=role, e=old_emoji))
        try:
            if ctx.guild.id in self.cache:
                del self.cache[ctx.guild.id][role_react["ID"]]
        except KeyError:
            self.bot.log.debug(f"Emoji {emoji} not found in cache")

    async def create_list_embed(self, rr_list: list[RoleReactionRow], guild: discord.Guild):
        """Create a text with the roles list"""
        emojis: list[str | discord.Emoji] = []
        for k in rr_list:
            emojis.append(await self.get_emoji_display_form(guild, k['emoji']))
        result = [
            (
                f"{emoji}   <@&{rr['role']}> - *{rr['description']}*"
                if len(rr['description']) > 0
                else f"{emoji}   <@&{rr['role']}>"
            )
            for rr, emoji in zip(rr_list, emojis, strict=True)
        ]
        return '\n'.join(result), emojis

    @rr_main.command(name="list")
    @commands.check(checks.database_connected)
    @commands.check(checks.bot_can_embed)
    async def rr_list(self, ctx: MyContext):
        """List every roles reactions of your server

        ..Doc roles-reactions.html#list-every-roles-reactions"""
        await ctx.defer()
        if self.cache_initialized and ctx.guild.id in self.cache:
            roles_list = list(self.cache[ctx.guild.id].values())
        else:
            roles_list = await self.db_get_roles(ctx.guild.id)
        des, _ = await self.create_list_embed(roles_list, ctx.guild)
        max_rr: int = await self.bot.get_config(ctx.guild.id, 'roles_react_max_number')
        title = await self.bot._(ctx.guild.id, "roles_react.rr-list", n=len(roles_list), m=max_rr)
        emb = discord.Embed(title=title, description=des, color=self.embed_color, timestamp=ctx.message.created_at)
        emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        await ctx.send(embed=emb)

    @rr_main.command(name="send")
    @commands.check(checks.database_connected)
    @commands.check(checks.bot_can_embed)
    async def rr_get(self, ctx: MyContext):
        """Send the roles embed
It will only display the whole message with reactions. Still very cool tho

..Doc roles-reactions.html#get-or-leave-a-role"""
        await ctx.defer()
        try:
            roles_list = await self.db_get_roles(ctx.guild.id)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
            return
        des, emojis = await self.create_list_embed(roles_list, ctx.guild)
        title = await self.bot._(ctx.guild.id, "roles_react.rr-embed")
        emb = discord.Embed(title=title, description=des, color=self.embed_color, timestamp=ctx.message.created_at)
        emb.set_footer(text=self.footer_texts[0])
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

    @rr_main.command(name="set-description")
    @commands.check(checks.database_connected)
    @commands.check(checks.has_manage_guild)
    async def rr_set_description(self, ctx: MyContext, emoji: DiscordOrUnicodeEmoji, *, description: RoleDescription):
        """Set the description of a role reaction
        Use the 'none' keyword to remove the description

        ..Example roles_react set-description :uwu: lolcats

        ..Example roles_react set-description :bell: none

        ..Doc roles-reactions.html#edit-a-reaction-description"""
        await ctx.defer()
        if description.lower() == "none":
            description = ""
        try:
            role_react = await self.db_get_role_from_emoji(ctx.guild.id, emoji)
            if role_react is None:
                return await ctx.send(await self.bot._(ctx.guild.id, "roles_react.no-rr"))
            await self.db_edit_description(role_react['ID'], description[:150])
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            if role := ctx.guild.get_role(role_react['role']):
                role_mention = f"<@&{role.id}>"
            else:
                role_mention = str(role_react['role'])
            await ctx.send(await self.bot._(
                ctx.guild.id,
                "roles_react.rr-description-set" if description else "roles_react.rr-description-reset",
                role=role_mention))

    @rr_main.command(name='update')
    @app_commands.describe(
        embed="A link to the message you want to update",
        change_description="Update the embed content (default: True)",
        emojis="A list of emojis to include (default: all)")
    @commands.check(checks.database_connected)
    async def rr_update(self, ctx: MyContext, embed: discord.Message, change_description: bool = True,
                        emojis: commands.Greedy[DiscordOrUnicodeEmoji] = None):
        """Update an Axobot message to refresh roles/reactions
        If you don't want to update the embed content (for example if it's a custom embed) then you can use 'False' as a second argument, and I will only check the reactions
        Specifying a list of emojis will update the embed only for those emojis, and ignore other roles reactions

        ..Example roles_react update https://discord.com/channels/356067272730607628/625320847296430120/707726569430319164 False

        ..Example roles_react update 707726569430319164 True :cool: :vip:

        ..Doc roles-reactions.html#update-your-embed"""
        if embed.author != ctx.guild.me:
            return await ctx.send(await self.bot._(ctx.guild, "roles_react.not-zbot-msg"))
        if len(embed.embeds) != 1 or embed.embeds[0].footer.text not in self.footer_texts:
            return await ctx.send(await self.bot._(ctx.guild, "roles_react.not-zbot-embed"))
        if not embed.channel.permissions_for(embed.guild.me).add_reactions:
            return await ctx.send(await self.bot._(ctx.guild, "poll.cant-react"))
        await ctx.defer()
        emb = embed.embeds[0]
        try:
            full_list = {x['emoji']: x for x in await self.db_get_roles(ctx.guild.id)}
        except Exception as err:
            return self.bot.dispatch("command_error", ctx, err)
        if emojis is not None:
            emojis_ids = [str(x.id) if isinstance(x, discord.Emoji)
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


    @rr_remove.autocomplete("emoji")
    @rr_set_description.autocomplete("emoji")
    async def emoji_autocompletion(self, interaction: discord.Interaction, current: str):
        """Autocompletion for the role-reaction emoji in slash commands"""
        if interaction.guild_id is None:
            return []
        if not self.cache_initialized:
            await self.db_init_cache()
        if interaction.guild_id not in self.cache:
            return []
        options: list[tuple[bool, str, str]] = []
        for rr in self.cache[interaction.guild_id].values():
            if ':' in rr["emoji_display"]:
                emoji_display = ':' + rr["emoji_display"].split(':')[1] + ':'
            else:
                emoji_display = rr["emoji_display"]
            role = interaction.guild.get_role(rr["role"])
            role_name = role.name if role else str(rr["role"])
            if current in rr["emoji_display"] or current in role_name:
                options.append((not True, f"{emoji_display} {role_name}", rr['emoji']))
        options.sort()
        return [
            app_commands.Choice(name=emoji, value=emoji_id)
            for _, emoji, emoji_id in options
        ]


async def setup(bot):
    await bot.add_cog(RolesReact(bot))
