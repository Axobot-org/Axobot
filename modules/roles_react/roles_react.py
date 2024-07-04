import datetime
import re
from collections import defaultdict
from typing import TypedDict

import discord
from discord import app_commands
from discord.ext import commands

from core.arguments import (DiscordOrUnicodeEmojiArgument,
                            GreedyDiscordOrUnicodeEmojiArgument,
                            MessageArgument)
from core.bot_classes import Axobot
from core.checks import checks
from core.getch_methods import getch_member


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
        self.file = "roles_react"
        self.table = "roles_react_beta" if bot.beta else "roles_react"
        self.cache: dict[int, dict[int, RoleReactionRow]] = defaultdict(dict)
        self.cache_initialized = False
        self.embed_color = 12118406
        self.footer_texts = ("Axobot roles reactions", "ZBot roles reactions")

    @commands.Cog.listener()
    async def on_ready(self):
        self.table = "roles_react_beta" if self.bot.beta else "roles_react"

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

    @commands.Cog.listener("on_raw_reaction_add")
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.on_raw_reaction_event(payload, True)

    @commands.Cog.listener("on_raw_reaction_remove")
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
        if guild := self.bot.get_guild(rr["guild"]):
            rr["emoji_display"] = await self.get_emoji_display_form(guild, rr["emoji"])
        else:
            rr["emoji_display"] = rr["emoji"]
        self.cache[rr["guild"]][rr["ID"]] = rr

    async def db_init_cache(self):
        """Get the list of guilds which have roles reactions"""
        self.cache_initialized = False
        self.cache.clear()
        query = f"SELECT * FROM `{self.table}`;"
        async with self.bot.db_main.read(query) as query_results:
            for row in query_results:
                await self._add_rr_to_cache(row)
        self.cache_initialized = True

    async def db_add_role(self, guild: int, role: int, emoji: str, desc: str):
        """Add a role reaction in the database"""
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id
        query = f"INSERT INTO `{self.table}` (`guild`,`role`,`emoji`,`description`) VALUES (%(g)s,%(r)s,%(e)s,%(d)s);"
        async with self.bot.db_main.write(query, {'g': guild, 'r': role, 'e': emoji, 'd': desc}):
            pass
        return True

    async def db_get_roles(self, guild_id: int):
        """List role reaction in the database"""
        query = f"SELECT * FROM `{self.table}` WHERE guild=%s ORDER BY added_at;"
        rr_list: list[RoleReactionRow] = []
        async with self.bot.db_main.read(query, (guild_id,)) as query_results:
            for row in query_results:
                rr_list.append(row)
        return rr_list

    async def db_get_role_from_emoji(self, guild_id: int, emoji: discord.Emoji | int | str) -> RoleReactionRow | None:
        """Get a role reaction from the database corresponding to an emoji"""
        if isinstance(emoji, discord.Emoji):
            emoji = emoji.id
        query = f"SELECT * FROM `{self.table}` WHERE guild=%(g)s AND emoji=%(e)s ORDER BY added_at;"
        async with self.bot.db_main.read(query, {"g": guild_id, "e": str(emoji)}, fetchone=True) as query_results:
            return query_results or None

    async def db_remove_role(self, rr_id: int):
        """Remove a role reaction from the database"""
        query = f"DELETE FROM `{self.table}` WHERE `ID`=%s;"
        async with self.bot.db_main.write(query, (rr_id,)):
            pass
        return True

    async def db_edit_description(self, rr_id: int, new_description: str):
        """Edit the description of a role reaction"""
        query = f"UPDATE `{self.table}` SET `description`=%s WHERE `ID`=%s;"
        async with self.bot.db_main.write(query, (new_description, rr_id)):
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
                    await channel.send(await self.bot._(guild.id, "moderation.mute.cant-mute"))
                    return
                if role.position >= guild.me.top_role.position:
                    await channel.send(await self.bot._(guild.id, "moderation.role.too-high", r=role.name))
                    return
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

    rr_main = app_commands.Group(
        name="roles-react",
        description="Manage your roles reactions",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True
    )

    @rr_main.command(name="add")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(5, 20)
    async def rr_add(self, interaction: discord.Interaction, emoji: DiscordOrUnicodeEmojiArgument, role: discord.Role,
                     description: RoleDescription = ''):
        """Add a role reaction
        This role will be given when a membre click on a specific reaction
        Your description can only be a maximum of 150 characters

        ..Example roles_react add :upside_down: "weird users" role for weird members

        ..Example roles_react add :uwu: lolcats

        ..Doc roles-reactions.html#add-and-remove-a-reaction"""
        if role == interaction.guild.default_role:
            raise commands.BadArgument(f"Role \"{role.name}\" not found")
        await interaction.response.defer()
        if await self.db_get_role_from_emoji(interaction.guild_id, emoji):
            await interaction.followup.send(await self.bot._(interaction, "roles_react.already-1-rr"))
            return
        max_rr: int = await self.bot.get_config(interaction.guild_id, "roles_react_max_number")
        existing_list = await self.db_get_roles(interaction.guild_id)
        if len(existing_list) >= max_rr:
            await interaction.followup.send(await self.bot._(interaction, "roles_react.too-many-rr", l=max_rr))
            return
        await self.db_add_role(interaction.guild_id, role.id, emoji, description)
        await interaction.followup.send(await self.bot._(interaction, "roles_react.rr-added", r=role.name, e=emoji))
        if rr := await self.db_get_role_from_emoji(interaction.guild_id, emoji):
            await self._add_rr_to_cache(rr)
        else:
            self.bot.log.warning(f"Could not add role reaction {emoji} in cache")

    @rr_main.command(name="remove")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(5, 20)
    async def rr_remove(self, interaction: discord.Interaction, emoji: str):
        """Remove a role react

        ..Example roles_react remove :uwu:

        ..Doc roles-reactions.html#add-and-remove-a-reaction"""
        await interaction.response.defer()
        # if emoji is a custom one: extract the id
        old_emoji = emoji
        r = re.search(r"<a?:[^:]+:(\d+)>", emoji)
        if r is not None:
            emoji = r.group(1)
        role_react = await self.db_get_role_from_emoji(interaction.guild_id, emoji)
        if role_react is None:
            await interaction.followup.send(await self.bot._(interaction, "roles_react.no-rr"))
            return
        await self.db_remove_role(role_react["ID"])
        role = interaction.guild.get_role(role_react["role"])
        if role is None:
            await interaction.followup.send(await self.bot._(interaction, "roles_react.rr-removed-2", e=old_emoji))
        else:
            await interaction.followup.send(await self.bot._(interaction, "roles_react.rr-removed", r=role, e=old_emoji))
        try:
            if interaction.guild_id in self.cache:
                del self.cache[interaction.guild_id][role_react["ID"]]
        except KeyError:
            self.bot.log.debug(f"Emoji {emoji} not found in cache")

    async def create_list_embed(self, rr_list: list[RoleReactionRow], guild: discord.Guild):
        """Create a text with the roles list"""
        emojis: list[str | discord.Emoji] = []
        for k in rr_list:
            emojis.append(await self.get_emoji_display_form(guild, k["emoji"]))
        result = [
            (
                f"{emoji}   <@&{rr['role']}> - *{rr['description']}*"
                if len(rr["description"]) > 0
                else f"{emoji}   <@&{rr['role']}>"
            )
            for rr, emoji in zip(rr_list, emojis, strict=True)
        ]
        return "\n".join(result), emojis

    @rr_main.command(name="list")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(3, 30)
    async def rr_list(self, interaction: discord.Interaction):
        """List every roles reactions of your server

        ..Doc roles-reactions.html#list-every-roles-reactions"""
        await interaction.response.defer(ephemeral=True)
        if self.cache_initialized and interaction.guild_id in self.cache:
            roles_list = list(self.cache[interaction.guild_id].values())
        else:
            roles_list = await self.db_get_roles(interaction.guild_id)
        des, _ = await self.create_list_embed(roles_list, interaction.guild)
        max_rr: int = await self.bot.get_config(interaction.guild_id, "roles_react_max_number")
        title = await self.bot._(interaction, "roles_react.rr-list", n=len(roles_list), m=max_rr)
        emb = discord.Embed(title=title, description=des, color=self.embed_color)
        await interaction.followup.send(embed=emb)

    @rr_main.command(name="send")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(3, 30)
    async def rr_send(self, interaction: discord.Interaction, channel: discord.TextChannel | discord.Thread | None = None):
        """Send the roles embed
It will only display the whole message with reactions. Still very cool tho

..Doc roles-reactions.html#get-or-leave-a-role"""
        if channel is None:
            channel = interaction.channel
        bot_perms = channel.permissions_for(interaction.guild.me)
        if not (bot_perms.add_reactions and bot_perms.embed_links):
            await interaction.response.send_message(
                await self.bot._(interaction, "roles_react.cant-send-embed"), ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        roles_list = await self.db_get_roles(interaction.guild_id)
        des, emojis = await self.create_list_embed(roles_list, interaction.guild)
        title = await self.bot._(interaction, "roles_react.rr-embed")
        emb = discord.Embed(title=title, description=des, color=self.embed_color)
        emb.set_footer(text=self.footer_texts[0])
        msg = await interaction.channel.send(embed=emb)
        for emoji in emojis:
            try:
                await msg.add_reaction(emoji)
            except (discord.Forbidden, discord.NotFound):
                pass
            except discord.HTTPException as err:
                if err.status == 400:
                    continue
                self.bot.dispatch("interaction_error", interaction, err)
                break
        await interaction.followup.send(
            await self.bot._(interaction, "roles_react.success-sent", msg=f"<{msg.jump_url}>")
        )

    @rr_main.command(name="set-description")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(5, 20)
    async def rr_set_description(self, interaction: discord.Interaction, emoji: DiscordOrUnicodeEmojiArgument,
                                 description: RoleDescription):
        """Set the description of a role reaction
        Use the 'none' keyword to remove the description

        ..Example roles_react set-description :uwu: lolcats

        ..Example roles_react set-description :bell: none

        ..Doc roles-reactions.html#edit-a-reaction-description"""
        await interaction.response.defer(ephemeral=True)
        if description.lower() == "none":
            description = ""
        role_react = await self.db_get_role_from_emoji(interaction.guild_id, emoji)
        if role_react is None:
            await interaction.followup.send(await self.bot._(interaction, "roles_react.no-rr"))
            return
        await self.db_edit_description(role_react["ID"], description[:150])
        if role := interaction.guild.get_role(role_react["role"]):
            role_mention = f"<@&{role.id}>"
        else:
            role_mention = str(role_react["role"])
        if description:
            text_key = "roles_react.rr-description-set"
        else:
            text_key = "roles_react.rr-description-reset"
        await interaction.followup.send(await self.bot._(interaction, text_key, role=role_mention))

    @rr_main.command(name="update")
    @app_commands.describe(
        embed="A link to the message you want to update",
        change_description="Update the embed content (default: True)",
        emojis="A list of emojis to include (default: all)")
    @app_commands.check(checks.database_connected)
    @app_commands.checks.cooldown(5, 20)
    async def rr_update(self, interaction: discord.Interaction, embed: MessageArgument, change_description: bool = True,
                        emojis: GreedyDiscordOrUnicodeEmojiArgument | None = None):
        """Update an Axobot message to refresh roles/reactions
        If you don't want to update the embed content (for example if it's a custom embed) then you can use 'False' as a second argument, and I will only check the reactions
        Specifying a list of emojis will update the embed only for those emojis, and ignore other roles reactions

        ..Example roles_react update https://discord.com/channels/356067272730607628/625320847296430120/707726569430319164 False

        ..Example roles_react update 707726569430319164 True :cool: :vip:

        ..Doc roles-reactions.html#update-your-embed"""
        if embed.author != interaction.guild.me:
            await interaction.response.send_message(
                await self.bot._(interaction, "roles_react.not-zbot-msg"), ephemeral=True
            )
            return
        if len(embed.embeds) != 1 or embed.embeds[0].footer.text not in self.footer_texts:
            await interaction.response.send_message(
                await self.bot._(interaction, "roles_react.not-zbot-embed"), ephemeral=True
            )
            return
        if not embed.channel.permissions_for(embed.guild.me).add_reactions:
            await interaction.response.send_message(
                await self.bot._(interaction, "poll.cant-react"), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        emb = embed.embeds[0]
        full_list = {x["emoji"]: x for x in await self.db_get_roles(interaction.guild_id)}
        if emojis is not None:
            emojis_ids = [str(x.id) if isinstance(x, discord.Emoji)
                      else str(x) for x in emojis]
            full_list = [full_list[x] for x in emojis_ids if x in full_list]
        else:
            full_list = list(full_list.values())
        desc, proper_emojis = await self.create_list_embed(full_list, interaction.guild)
        reacts = [x.emoji for x in embed.reactions]
        for emoji in proper_emojis:
            if emoji not in reacts:
                await embed.add_reaction(emoji)
        if emb.description != desc and change_description:
            emb.description = desc
            await embed.edit(embed=emb)
            await interaction.followup.send(await self.bot._(interaction, "roles_react.embed-edited"))
        else:
            await interaction.followup.send(await self.bot._(interaction, "roles_react.reactions-edited"))


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
                options.append((not True, f"{emoji_display} {role_name}", rr["emoji"]))
        options.sort()
        return [
            app_commands.Choice(name=emoji, value=emoji_id)
            for _, emoji, emoji_id in options
        ]


async def setup(bot):
    await bot.add_cog(RolesReact(bot))
