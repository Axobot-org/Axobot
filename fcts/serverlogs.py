import asyncio
import datetime
import re
from typing import Any, Callable, Optional

import discord
from cachingutils import LRUCache
from discord import app_commands
from discord.ext import commands, tasks

from fcts import checks
from fcts.args import serverlog
from fcts.tickets import TicketCreationEvent
from libs.antiscam.classes import PredictionResult
from libs.bot_classes import Axobot, MyContext
from libs.enums import ServerWarningType
from libs.formatutils import FormatUtils

DISCORD_INVITE = re.compile(r'(?:https?://)?(?:www[.\s])?((?:discord[.\s](?:gg|io|me|li(?:nk)?)|discordapp\.com/invite|discord\.com/invite|dsc\.gg)[/ ]{,3}[\w-]{1,25}(?!\w))')


class ServerLogs(commands.Cog):
    """Handle any kind of server log"""

    logs_categories = {
        "automod": {"antiraid", "antiscam"},
        "bot": {"bot_warnings"},
        "members": {"member_roles", "member_nick", "member_avatar", "member_join", "member_leave", "member_verification", "user_update"},
        "moderation": {"member_ban", "member_unban", "member_timeout", "member_kick"},
        "messages": {"message_update", "message_delete", "discord_invite", "ghost_ping"},
        "roles": {"role_creation", "role_update", "role_deletion"},
        "tickets": {"ticket_creation"},
    }

    @classmethod
    def available_logs(cls):
        return {log for category in cls.logs_categories.values() for log in category}


    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "serverlogs"
        self.cache: LRUCache[int, dict[int, list[str]]] = LRUCache(max_size=10000, timeout=3600*4)
        self.to_send: dict[discord.TextChannel, list[discord.Embed]] = {}
        self.auditlogs_timeout = 3 # seconds

    async def cog_load(self):
        self.send_logs_task.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.send_logs_task.cancel() # pylint: disable=no-member


    async def is_log_enabled(self, guild_id: int, log: str) -> list[int]:
        "Check if a log kind is enabled for a guild, and return the corresponding logs channel ID"
        guild_logs = await self.db_get_from_guild(guild_id)
        # if axobot is also there, don't send anything
        if await self.bot.check_axobot_presence(guild_id=guild_id):
            return []
        res: list[int] = []
        for channel, event in guild_logs.items():
            if log in event:
                res.append(channel)
        return res

    async def validate_logs(self, guild: discord.Guild, channel_ids: list[int], embed: discord.Embed, log_type: str):
        "Send a log embed to the corresponding modlogs channels"
        for channel_id in channel_ids:
            if channel := guild.get_channel_or_thread(channel_id):
                if channel in self.to_send:
                    self.to_send[channel].append(embed)
                else:
                    self.to_send[channel] = [embed]
                self.bot.dispatch("serverlog", guild.id, channel.id, log_type)

    async def db_get_from_channel(self, guild: int, channel: int, use_cache: bool=True) -> list[str]:
        "Get enabled logs for a channel"
        if use_cache and (cached := self.cache.get(guild)) and channel in cached:
            return cached[channel]
        query = "SELECT kind FROM serverlogs WHERE guild = %s AND channel = %s AND beta = %s"
        async with self.bot.db_query(query, (guild, channel, self.bot.beta)) as query_results:
            return [row['kind'] for row in query_results]

    async def db_get_from_guild(self, guild: int, use_cache: bool=True) -> dict[int, list[str]]:
        """Get enabled logs for a guild
        Returns a map of ChannelID -> list of enabled logs"""
        if use_cache and (cached := self.cache.get(guild)):
            return cached
        query = "SELECT channel, kind FROM serverlogs WHERE guild = %s AND beta = %s"
        async with self.bot.db_query(query, (guild, self.bot.beta)) as query_results:
            res = {}
            for row in query_results:
                res[row['channel']] = res.get(row['channel'], []) + [row['kind']]
            self.cache[guild] = res
            return res

    async def db_add(self, guild: int, channel: int, kind: str) -> bool:
        "Add logs to a channel"
        query = "INSERT INTO serverlogs (guild, channel, kind, beta) VALUES (%(g)s, %(c)s, %(k)s, %(b)s) ON DUPLICATE KEY UPDATE guild=%(g)s"
        async with self.bot.db_query(query, {'g': guild, 'c': channel, 'k': kind, 'b': self.bot.beta}) as query_result:
            if query_result > 0 and guild in self.cache:
                if channel in self.cache[guild]:
                    self.cache[guild][channel].append(kind)
                else:
                    self.cache[guild][channel] = await self.db_get_from_channel(guild, channel, False)
            return query_result > 0

    async def db_remove(self, guild: int, channel: int, kind: str) -> bool:
        "Remove logs from a channel"
        query = "DELETE FROM serverlogs WHERE guild = %s AND channel = %s AND kind = %s AND beta = %s"
        async with self.bot.db_query(query, (guild, channel, kind, self.bot.beta), returnrowcount=True) as query_result:
            if query_result > 0 and guild in self.cache:
                if channel in self.cache[guild]:
                    self.cache[guild][channel] = [x for x in self.cache[guild][channel] if x != kind]
                else:
                    self.cache[guild] = await self.db_get_from_guild(guild, use_cache=False)
            return query_result > 0


    @tasks.loop(seconds=30)
    async def send_logs_task(self):
        "Send ready logs every 30s to avoid rate limits"
        try:
            for channel, embeds in dict(self.to_send).items():
                if not embeds or channel.guild.me is None:
                    self.to_send.pop(channel)
                    continue
                try:
                    perms = channel.permissions_for(channel.guild.me)
                    if perms.send_messages and perms.embed_links:
                        await channel.send(embeds=embeds[:10])
                        if len(embeds) > 10:
                            self.to_send[channel] = self.to_send[channel][10:]
                        else:
                            self.to_send.pop(channel)
                except discord.HTTPException as err:
                    self.bot.dispatch('error', err, None)
        except Exception as err: # pylint: disable=broad-except
            self.bot.dispatch('error', err, None)

    @send_logs_task.before_loop
    async def before_logs_task(self):
        await self.bot.wait_until_ready()


    @commands.hybrid_group(name="modlogs")
    @app_commands.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    @commands.cooldown(2, 6, commands.BucketType.guild)
    async def modlogs_main(self, ctx: MyContext):
        """Enable or disable server logs in specific channels

        ..Doc moderator.html#server-logs"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @modlogs_main.command(name="list")
    @app_commands.describe(channel="The channel to list logs for. Leave empty to list all logs for the server")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def modlogs_list(self, ctx: MyContext, channel: Optional[discord.TextChannel]=None):
        """Show the full list of server logs type, or the list of enabled logs for a channel

        ..Example modlogs list

        ..Doc moderator.html#how-to-setup-logs"""
        if channel:  # display logs enabled for this channel only
            title = await self.bot._(ctx.guild.id, "serverlogs.list.channel", channel='#'+channel.name)
            if channel_logs := await self.db_get_from_channel(ctx.guild.id, channel.id):
                embed = discord.Embed(title=title)
                for category, logs in sorted(self.logs_categories.items()):
                    name = await self.bot._(ctx.guild.id, 'serverlogs.categories.'+category)
                    actual_logs = ['- '+l for l in sorted(logs) if l in channel_logs]
                    if actual_logs:
                        embed.add_field(name=name, value='\n'.join(actual_logs))
            else: # error msg
                cmd = await self.bot.prefix_manager.get_prefix(ctx.guild) + "modlogs enable"
                embed = discord.Embed(title=title, description=await self.bot._(ctx.guild.id, "serverlogs.list.none", cmd=cmd))
        else:  # display available logs and logs enabled for the whole server
            global_title = await self.bot._(ctx.guild.id, "serverlogs.list.all")
            # fetch logs enabled in the guild
            guild_logs = await self.db_get_from_guild(ctx.guild.id)
            guild_logs = sorted(set(x for v in guild_logs.values() for x in v if x in self.available_logs()))
            # build embed
            if ctx.bot_permissions.external_emojis and (cog := self.bot.emojis_manager):
                enabled_emoji, disabled_emoji = cog.customs["green_check"], cog.customs["gray_check"]
            else:
                enabled_emoji, disabled_emoji = '🔹', '◾'
            desc = await self.bot._(ctx.guild.id, "serverlogs.list.emojis", enabled=enabled_emoji, disabled=disabled_emoji)
            embed = discord.Embed(title=global_title, description=desc)
            for category, logs in sorted(self.logs_categories.items()):
                name = await self.bot._(ctx.guild.id, 'serverlogs.categories.'+category)
                embed.add_field(name=name, value='\n'.join([
                    (enabled_emoji if l in guild_logs else disabled_emoji) + l for l in sorted(logs)
                    ]))

        embed.color = discord.Color.blue()
        await ctx.send(embed=embed)

    @modlogs_main.command(name="enable", aliases=['add'])
    @app_commands.describe(channel="The channel to add logs to. Leave empty to select the current channel")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def modlogs_enable(self, ctx: MyContext, logs: commands.Greedy[serverlog], channel: Optional[discord.TextChannel]=None):
        """Enable one or more logs in the current channel

        ..Example modlogs enable ban bot_warnings

        ..Example modlogs enable role_creation bot_warnings #mod-logs

        ..Doc moderator.html#how-to-setup-logs"""
        if len(logs) == 0:
            raise commands.BadArgument('Invalid server log type')
        dest_channel = channel or ctx.channel
        if 'all' in logs:
            logs = list(self.available_logs())
        actually_added: list[str] = []
        for log in logs:
            if await self.db_add(ctx.guild.id, dest_channel.id, log):
                actually_added.append(log)
        if actually_added:
            if dest_channel == ctx.channel:
                msg = await self.bot._(ctx.guild.id, "serverlogs.enabled.current", kind=', '.join(actually_added))
            else:
                msg = await self.bot._(ctx.guild.id, "serverlogs.enabled.other", kind=', '.join(actually_added), channel=dest_channel.mention)
            if not dest_channel.permissions_for(ctx.guild.me).embed_links:
                msg += "\n:warning: " + await self.bot._(ctx.guild.id, "serverlogs.embed-warning")
        else:
            msg = await self.bot._(ctx.guild.id, "serverlogs.none-added")
        await ctx.send(msg)

    @modlogs_enable.autocomplete("logs")
    async def _modlogs_enable_autocomplete(self, interaction: discord.Interaction, current: str):
        if channel := interaction.namespace.channel:
            channel_id: int = channel.id
        else:
            channel_id = interaction.channel_id
        actived_logs = await self.db_get_from_channel(interaction.guild_id, channel_id)
        available_logs = self.available_logs() - set(actived_logs)
        return await self.log_name_autocomplete(current, available_logs)

    @modlogs_main.command(name="disable", aliases=['remove'])
    @app_commands.describe(channel="The channel to remove logs from. Leave empty to select the current channel")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def modlogs_disable(self, ctx: MyContext, logs: commands.Greedy[serverlog], channel: Optional[discord.TextChannel]=None):
        """Disable one or more logs in the current channel

        ..Example modlogs disable ban message_delete

        ..Example modlogs disable ghost_ping #mod-logs

        ..Doc moderator.html#how-to-setup-logs"""
        if len(logs) == 0:
            raise commands.BadArgument('Invalid server log type')
        if 'all' in logs:
            logs = list(self.available_logs())
        dest_channel = channel or ctx.channel
        actually_removed: list[str] = []
        for log in logs:
            if await self.db_remove(ctx.guild.id, dest_channel.id, log):
                actually_removed.append(log)
        if actually_removed:
            if dest_channel == ctx.channel:
                msg = await self.bot._(ctx.guild.id, "serverlogs.disabled.current", kind=', '.join(actually_removed))
            else:
                msg = await self.bot._(ctx.guild.id, "serverlogs.disabled.other", kind=', '.join(actually_removed), channel=dest_channel.mention)
        else:
            msg = await self.bot._(ctx.guild.id, "serverlogs.none-removed")
        await ctx.send(msg)

    @modlogs_disable.autocomplete("logs")
    async def _modlogs_disable_autocomplete(self, interaction: discord.Interaction, current: str):
        if channel := interaction.namespace.channel:
            channel_id: int = channel.id
        else:
            channel_id = interaction.channel_id
        actived_logs = await self.db_get_from_channel(interaction.guild_id, channel_id)
        return await self.log_name_autocomplete(current, actived_logs)

    async def log_name_autocomplete(self, current: str, available_logs: Optional[list[str]]=None):
        "Autocompletion for log names"
        all_logs = list(self.available_logs()) if available_logs is None else  available_logs
        filtered = sorted(
            (not option.startswith(current), option)
            for option in all_logs
            if current in option
        )
        return [
            app_commands.Choice(name=value[1], value=value[1])
            for value in filtered
        ][:25]

    async def search_audit_logs(self, guild: discord.Guild, action: discord.AuditLogAction, check: Callable[[discord.AuditLogEntry], bool]=None):
        """Search for a specific audit log entry in a given guild"""
        if not guild.me.guild_permissions.view_audit_log:
            return None
        now = self.bot.utcnow()
        stats_cog = self.bot.get_cog("BotStats")
        await asyncio.sleep(self.auditlogs_timeout)
        async for entry in guild.audit_logs(action=action, limit=5, oldest_first=False):
            if (now - entry.created_at).total_seconds() > 5:
                continue
            if check is None or check(entry):
                if stats_cog:
                    await stats_cog.on_serverlogs_audit_search(True)
                return entry
        if stats_cog:
            await stats_cog.on_serverlogs_audit_search(False)


    @commands.Cog.listener()
    async def on_raw_message_edit(self, msg: discord.RawMessageUpdateEvent):
        """Triggered when a message is sent
        Corresponding log: message_update"""
        if not msg.guild_id:
            return
        if channel_ids := await self.is_log_enabled(msg.guild_id, "message_update"):
            old_content: str = None
            author: discord.User = None
            guild: discord.Guild = None
            link: str = None
            if msg.cached_message:
                if msg.cached_message.author.bot:
                    return
                if "pinned" in msg.data and msg.cached_message.pinned != msg.data['pinned']:
                    return
                old_content = msg.cached_message.content
                author = msg.cached_message.author
                guild = msg.cached_message.guild
                link = msg.cached_message.jump_url
            else:
                if 'author' in msg.data and (author_id := msg.data.get('author').get('id')):
                    author = self.bot.get_user(int(author_id))
                guild = self.bot.get_guild(msg.guild_id)
                link = f"https://discord.com/channels/{msg.guild_id}/{msg.channel_id}/{msg.message_id}"
            new_content = msg.data.get('content')
            if new_content is None: # and msg.data.get('flags', 0) & 32:
                return
            emb = discord.Embed(
                description=f"**[Message]({link}) updated in <#{msg.channel_id}>**",
                colour=discord.Color.light_gray())
            if old_content:
                if len(old_content) > 1024:
                    old_content = old_content[:1020] + '…'
                emb.add_field(name="Old content", value=old_content, inline=False)
            if new_content:
                if len(new_content) > 1024:
                    new_content = new_content[:1020] + '…'
                emb.add_field(name="New content", value=new_content, inline=False)
            if author:
                emb.set_author(name=str(author), icon_url=author.display_avatar)
                emb.add_field(name="Message Author", value=f"{author} ({author.id})")
            await self.validate_logs(guild, channel_ids, emb, "message_update")

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        """Triggered when a message is deleted
        Corresponding logs: message_delete, ghost_ping"""
        if not payload.guild_id or (payload.cached_message and payload.cached_message.author == self.bot.user):
            return
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        # message delete
        if channel_ids := await self.is_log_enabled(payload.guild_id, "message_delete"):
            msg = payload.cached_message
            emb = discord.Embed(
                description=f"**Message deleted in <#{payload.channel_id}>**\n{msg.content if msg else ''}",
                colour=discord.Color.red()
            )
            if msg is not None:
                emb.set_author(name=str(msg.author), icon_url=msg.author.display_avatar)
                emb.add_field(name="Message Author", value=f"{msg.author} ({msg.author.id})")
            created_at = discord.utils.snowflake_time(payload.message_id)
            emb.add_field(name="Created at", value=f"<t:{created_at.timestamp():.0f}>")
            await self.validate_logs(guild, channel_ids, emb, "message_delete")
        # ghost_ping
        if payload.cached_message is not None and (channel_ids := await self.is_log_enabled(payload.guild_id, "ghost_ping")):
            msg = payload.cached_message
            if len(msg.raw_mentions) == 0 or (self.bot.utcnow() - msg.created_at).total_seconds() > 20:
                return
            emb = discord.Embed(
                description=f"**Ghost ping in <#{payload.channel_id}>**",
                colour=discord.Color.orange()
            )
            emb.add_field(name="Created at", value=f"<t:{msg.created_at.timestamp():.0f}>")
            emb.add_field(name="Message Author", value=f"{msg.author} ({msg.author.id})")
            emb.add_field(name="Mentionning", value=" ".join(f"<@{mention}>" for mention in set(msg.raw_mentions)), inline=False)
            await self.validate_logs(guild, channel_ids, emb, "ghost_ping")

    @commands.Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: discord.RawBulkMessageDeleteEvent):
        """Triggered when a bunch of  messages are deleted
        Corresponding log: message_delete"""
        if not payload.guild_id:
            return
        if channel_ids := await self.is_log_enabled(payload.guild_id, "message_delete"):
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return
            emb = discord.Embed(
                description=f"**{len(payload.message_ids)} messages deleted in <#{payload.channel_id}>**",
                colour=discord.Color.red()
            )
            await self.validate_logs(guild, channel_ids, emb, "message_delete")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Triggered when a message is sent by someone
        Corresponding log: discord_invite"""
        if message.guild is None or message.author == self.bot.user:
            return
        if (invites := DISCORD_INVITE.findall(message.content)) and (channel_ids := await self.is_log_enabled(message.guild.id, "discord_invite")):
            emb = discord.Embed(
                description=f"**[Discord invite]({message.jump_url}) detected in {message.channel.mention}**",
                colour=discord.Color.orange()
            )
            emb.set_author(name=str(message.author), icon_url=message.author.display_avatar)
            if len(invites) == 1 and (invite := await self.bot.fetch_invite(invites[0])):
                if invite.created_at:
                    emb.add_field(name="Invite created at", value=f"<t:{invite.created_at.timestamp():.0f}>")
            emb.add_field(name="Message Author", value=f"{message.author} ({message.author.id})")
            emb.add_field(name="Message sent at", value=f"<t:{message.created_at.timestamp():.0f}>")
            invites_formatted: set[str] = set(invite.replace(' ', '') for invite in invites)
            try:
                emb.add_field(name="Invite" if len(invites) == 1 else "Invites", value="\n".join(invites_formatted), inline=False)
            except Exception as err:
                print(err)
            await self.validate_logs(message.guild, channel_ids, emb, "discord_invite")

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Triggered when a member is updated
        Corresponding logs: member_roles, member_nick, member_avatar, member_verification"""
        now = self.bot.utcnow()
        # member roles
        if before.roles != after.roles and (channel_ids := await self.is_log_enabled(before.guild.id, "member_roles")):
            await self.handle_member_roles(before, after, channel_ids)
        # member nick
        if before.nick != after.nick and (channel_ids := await self.is_log_enabled(before.guild.id, "member_nick")):
            await self.handle_member_nick(before, after, channel_ids)
        # member avatar
        if before.guild_avatar != after.guild_avatar and (
                channel_ids := await self.is_log_enabled(before.guild.id, "member_avatar")
        ):
            await self.handle_member_avatar(before, after, channel_ids)
        # member timeout
        if ((before.timed_out_until is None or before.timed_out_until < now)
            and after.timed_out_until is not None and after.timed_out_until > now
            and (channel_ids := await self.is_log_enabled(before.guild.id, "member_timeout"))
            ):
            await self.handle_member_timeout(before, after, channel_ids)
        # member un-timeout
        if (before.timed_out_until is not None and before.timed_out_until > now
            and after.timed_out_until is None
            and (channel_ids := await self.is_log_enabled(before.guild.id, "member_timeout"))
            ):
            await self.handle_member_untimeout(before, after, channel_ids)
        # member verification
        if (before.pending and not after.pending) and (channel_ids := await self.is_log_enabled(before.guild.id, "member_verification")):
            await self.handle_member_verification(before, after, channel_ids)
        # public flags
        if before.public_flags != after.public_flags and (channel_ids := await self.is_log_enabled(before.guild.id, "user_update")):
            await self.handle_member_flags(before, after, channel_ids)

    async def handle_member_roles(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_roles log"
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) updated**",
            color=discord.Color.blurple()
        )
        if removed_roles:
            emb.add_field(name="Roles revoked", value=' '.join(r.mention for r in removed_roles), inline=False)
        if added_roles:
            emb.add_field(name="Roles granted", value=' '.join(r.mention for r in added_roles), inline=False)
        emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
        # if we have access to audit logs and no role come from an integration, try to get the user who edited the roles
        if any(not role.managed for role in added_roles+removed_roles):
            if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_role_update,
                                                     check=lambda entry: entry.target.id == before.id):
                emb.add_field(name="Roles edited by", value=f"**{entry.user.mention}** ({entry.user.id})")
        await self.validate_logs(after.guild, channel_ids, emb, "member_roles")

    async def handle_member_nick(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_nick log"
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) updated**",
            color=discord.Color.blurple()
        )
        if before.nick is None:
            escaped = discord.utils.escape_markdown(after.nick)
            emb.add_field(name="Nickname set", value=f"Set to '{escaped}'")
        elif after.nick is None:
            escaped = discord.utils.escape_markdown(before.nick)
            emb.add_field(name="Nickname removed", value=f"Previously '{escaped}'")
        else:
            escaped_before = discord.utils.escape_markdown(before.nick)
            escaped_after = discord.utils.escape_markdown(after.nick)
            emb.add_field(name="Nickname changed", value=f"From '{escaped_before}' to '{escaped_after}'")
        emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
        after_nick = after.nick
        if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_update,
                                                 check=lambda entry: (
                                                     entry.target.id == before.id
                                                     and hasattr(entry.after, "nick")
                                                     and entry.after.nick == after_nick
                                                 )):
            emb.add_field(name="Edited by",value=f"**{entry.user.mention}** ({entry.user.id})")
        await self.validate_logs(after.guild, channel_ids, emb, "member_nick")

    async def handle_member_avatar(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_avatar log"
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) updated**",
            color=discord.Color.blurple()
        )
        before_txt = "None" if before.guild_avatar is None else f"[Before]({before.guild_avatar})"
        after_txt = "None" if after.guild_avatar is None else f"[After]{after.guild_avatar}"
        emb.add_field(name="Server avatar edited", value=f"{before_txt} -> {after_txt}")
        emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
        await self.validate_logs(after.guild, channel_ids, emb, "member_avatar")

    async def handle_member_timeout(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_timeout log at start"
        now = self.bot.utcnow() - datetime.timedelta(seconds=1)
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) set in timeout**",
            color=discord.Color.orange()
        )
        duration = await FormatUtils.time_delta(now, after.timed_out_until, lang='en')
        emb.add_field(name="Duration", value=f"{duration} (until <t:{after.timed_out_until.timestamp():.0f}>)", inline=False)
        emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
        # try to get who timeouted that member
        if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_update,
                                                 check=lambda entry: (entry.target.id == before.id
                                                                      and entry.after.timed_out_until
                                                                      and (now - entry.created_at).total_seconds() < 5
                                                                      )):
            emb.add_field(name="Timeout by", value=f"**{entry.user.mention}** ({entry.user.id})")
            emb.add_field(name="With reason", value=entry.reason or "No reason specified")
        await self.validate_logs(after.guild, channel_ids, emb, "member_timeout")

    async def handle_member_untimeout(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_timeout log at end"
        now = self.bot.utcnow() - datetime.timedelta(seconds=1)
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) no longer in timeout**",
            color=discord.Color.green()
        )
        duration = await FormatUtils.time_delta(now, before.timed_out_until, lang='en')
        emb.add_field(
            name="Planned timeout end",
            value=f"<t:{before.timed_out_until.timestamp():.0f}> (in {duration})",
            inline=False
        )
        emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
        # try to get who timeouted that member
        if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_update,
                                                 check=lambda entry: (entry.target.id == before.id
                                                                      and entry.before.timed_out_until
                                                                      and (now - entry.created_at).total_seconds() < 5
                                                                      )):
            emb.add_field(name="Revoked by", value=f"**{entry.user.mention}** ({entry.user.id})")
            if entry.reason:
                emb.add_field(name="With reason", value=entry.reason)
        await self.validate_logs(after.guild, channel_ids, emb, "member_timeout")

    async def handle_member_verification(self, _before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_verification log"
        emb = discord.Embed(
            description=f"**{after.mention} ({after.id}) has been verified** through your server rules screen",
            colour=discord.Color.green()
        )
        emb.set_author(name=str(after), icon_url=after.display_avatar)
        emb.add_field(name="Account created at", value=f"<t:{after.created_at.timestamp():.0f}>", inline=False)
        if after.joined_at:
            delta = await FormatUtils.time_delta(
                after.joined_at,
                self.bot.utcnow(),
                lang=await self.bot._(after.guild.id, "_used_locale"),
                year=True
            )
            emb.add_field(
                name="Joined at",
                value=f"<t:{after.joined_at.timestamp():.0f}> ({delta})",
                inline=False)
        await self.validate_logs(after.guild, channel_ids, emb, "member_verification")

    async def handle_member_flags(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle user public flags change ('user_update')"
        before_flags = before.public_flags
        after_flags = after.public_flags
        if not before_flags.verified_bot and after_flags.verified_bot:
            description = f"**Bot {before.mention} has been verified**"
        elif not before_flags.active_developer and after_flags.active_developer:
            description = f"User {before.mention} **got the active developer badge**"
        elif before_flags.active_developer and not after_flags.active_developer:
            description = f"User {before.mention} **lost their active developer badge**"
        elif not before_flags.discord_certified_moderator and after_flags.active_developer:
            description = f"User {before.mention} is now a **Discord certified moderator**"
        elif before_flags.discord_certified_moderator and not after_flags.discord_certified_moderator:
            description = f"User {before.mention} is **no longer a Discord certified moderator**"
        else:
            self.bot.dispatch("error", ValueError(f"Unknown flag change between {before_flags} and {after_flags}"))
            return
        emb = discord.Embed(
            description=description,
            color=discord.Color.blurple(),
        )
        emb.add_field(name="User ID", value=str(after.id))
        emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
        await self.validate_logs(after.guild, channel_ids, emb, "member_avatar")

    async def get_member_specs(self, member: discord.Member) -> list[str]:
        "Get specific things to note for a member"
        specs = []
        if member.pending:
            specs.append("pending verification")
        if member.public_flags.verified_bot:
            specs.append("verified bot")
        elif member.bot:
            specs.append("bot")
        if member.public_flags.staff:
            specs.append("Discord staff")
        return specs

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Triggered when a member joins a guild
        Corresponding log: member_join"""
        if channel_ids := await self.is_log_enabled(member.guild.id, "member_join"):
            emb = discord.Embed(
                description=f"**{member.mention} ({member.id}) joined your server**",
                colour=discord.Color.green()
            )
            emb.set_author(name=str(member), icon_url=member.display_avatar)
            emb.add_field(name="Account created at", value=f"<t:{member.created_at.timestamp():.0f}>", inline=False)
            if specs := await self.get_member_specs(member):
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            await self.validate_logs(member.guild, channel_ids, emb, "member_join")

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        """Triggered when a member leaves a guild
        Corresponding log: member_leave, member_kick"""
        if not payload.guild_id:
            return
        if channel_ids := await self.is_log_enabled(payload.guild_id, "member_leave"):
            await self.handle_member_leave(payload, channel_ids)
        if channel_ids := await self.is_log_enabled(payload.guild_id, "member_kick"):
            await self.handle_member_kick(payload, channel_ids)

    async def handle_member_leave(self, payload: discord.RawMemberRemoveEvent, channel_ids: list[int]):
        "Handle member_leave log"
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        emb = discord.Embed(
            description=f"**{payload.user.mention} ({payload.user.id}) left your server**",
            colour=discord.Color.orange()
        )
        emb.set_author(name=str(payload.user), icon_url=payload.user.display_avatar)
        emb.add_field(name="Account created at", value=f"<t:{payload.user.created_at.timestamp():.0f}>", inline=False)
        if isinstance(payload.user, discord.Member):
            if payload.user.joined_at:
                delta = await FormatUtils.time_delta(
                    payload.user.joined_at,
                    self.bot.utcnow(),
                    lang=await self.bot._(payload.guild_id, "_used_locale"),
                    year=True
                )
                emb.add_field(
                    name="Joined your server at",
                    value=f"<t:{payload.user.joined_at.timestamp():.0f}> ({delta})",
                    inline=False)
            if specs := await self.get_member_specs(payload.user):
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            member_roles = [role for role in payload.user.roles[::-1] if not role.is_default()]
            roles_value = " ".join(r.mention for r in member_roles[:20]) if member_roles else "None"
            emb.add_field(name=f"Roles ({len(member_roles)})", value=roles_value)
        await self.validate_logs(guild, channel_ids, emb, "member_leave")

    async def handle_member_kick(self, payload: discord.RawMemberRemoveEvent, channel_ids: list[int]):
        "Handle member_kick log"
        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return
        if guild.me is None or not guild.me.guild_permissions.view_audit_log:
            return
        if entry := await self.search_audit_logs(guild, discord.AuditLogAction.kick,
                                                 check=lambda entry: entry.target.id == payload.user.id):
            emb = discord.Embed(
                description=f"**{payload.user.mention} ({payload.user.id}) has been kicked**",
                colour=discord.Color.red()
            )
            emb.set_author(name=str(payload.user), icon_url=payload.user.display_avatar)
            emb.add_field(name="Kicked by", value=f"**{entry.user.mention}** ({entry.user.id})")
            emb.add_field(name="With reason", value=entry.reason or "No reason specified")
            await self.validate_logs(guild, channel_ids, emb, "member_kick")


    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Triggered when a member is banned from a server
        Corresponding log: member_ban"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_ban"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been banned**",
                colour=discord.Color.red()
            )
            emb.set_author(name=str(user), icon_url=user.display_avatar)
            # try to get more info from audit logs
            if entry := await self.search_audit_logs(guild, discord.AuditLogAction.ban,
                                                     check=lambda entry: entry.target.id == user.id):
                emb.add_field(name="Banned by", value=f"**{entry.user.mention}** ({entry.user.id})")
                emb.add_field(name="With reason", value=entry.reason or "No reason specified")
            await self.validate_logs(guild, channel_ids, emb, "member_ban")

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        """Triggered when a user is unbanned from a server
        Corresponding log: member_unban"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_unban"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been unbanned**",
                colour=discord.Color.green()
            )
            emb.set_author(name=str(user), icon_url=user.display_avatar)
            # try to get more info from audit logs
            if entry := await self.search_audit_logs(guild, discord.AuditLogAction.unban,
                                                     check=lambda entry: entry.target.id == user.id):
                emb.add_field(name="Unbanned by", value=f"**{entry.user.mention}** ({entry.user.id})")
                emb.add_field(name="With reason", value=entry.reason or "No reason specified")
            await self.validate_logs(guild, channel_ids, emb, "member_unban")


    async def get_role_specs(self, role: discord.Role) -> list[str]:
        "Get specific things to note for a role"
        specs = []
        if role.permissions.administrator:
            specs.append("Administrator permission")
        if role.is_bot_managed():
            specs.append("Managed by a bot")
        if role.is_integration():
            specs.append("Integrated by an app")
        if role.is_premium_subscriber():
            specs.append("Nitro boosts role")
        if role.hoist:
            specs.append("Hoisted")
        return specs

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Triggered when a role is created in a guild
        Corresponding log: role_creation"""
        if channel_ids := await self.is_log_enabled(role.guild.id, "role_creation"):
            emb = discord.Embed(
                description="**New role created**",
                colour=discord.Color.green()
            )
            emb.set_footer(text=f"Role ID: {role.id}")
            emb.add_field(name="Name", value=role.name, inline=False)
            emb.add_field(name="Color", value=str(role.color))
            if specs := await self.get_role_specs(role):
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            # if we have access to audit logs, try to find who created the role
            if entry := await self.search_audit_logs(role.guild, discord.AuditLogAction.role_create,
                                                     check=lambda entry: entry.target.id == role.id):
                emb.add_field(name="Created by", value=f"**{entry.user.mention}** ({entry.user.id})")
                if entry.reason:
                    emb.add_field(name="With reason", value=entry.reason)
            await self.validate_logs(role.guild, channel_ids, emb, "role_creation")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Triggered when a role is edited in a guild
        Corresponding log: role_update"""
        if channel_ids := await self.is_log_enabled(after.guild.id, "role_update"):
            emb = discord.Embed(
                description=f"**Role '{before.name}' updated**",
                colour=discord.Color.blurple()
            )
            emb.set_footer(text=f"Role ID: {after.id}")
            # role name
            if before.name != after.name:
                emb.add_field(name="Name", value=f"{before.name} -> {after.name}", inline=False)
            # role color
            if before.color != after.color:
                emb.add_field(name="Color", value=f"{before.color} -> {after.color}", inline=False)
            # mentionnable
            if before.mentionable != after.mentionable:
                emb.add_field(name="Mentionnable", value="Enabled" if after.mentionable else "Disabled")
            # hoisted
            if before.hoist != after.hoist:
                emb.add_field(name="Hoisted", value="Enabled" if after.hoist else "Disabled")
            # icon
            if before.icon != after.icon:
                if after.icon:
                    emb.add_field(name="Icon", value=f"Set to {after.icon.url}")
                else:
                    emb.add_field(name="Icon", value=f"Removed (previously {before.icon.url})")
            if before.unicode_emoji != after.unicode_emoji:
                if before.unicode_emoji is None:
                    emb.add_field(name="Emoji", value=f"Set to {after.unicode_emoji}")
                elif after.unicode_emoji is None:
                    emb.add_field(name="Emoji", value=f"Removed (previously {after.unicode_emoji})")
                else:
                    emb.add_field(name="Emoji", value=f"{before.unicode_emoji} -> {after.unicode_emoji}")
            # permissions
            if before.permissions != after.permissions:
                revoked_perms = []
                granted_perms = []
                for perm in after.permissions:
                    perm_id, perm_enabled = perm
                    if perm not in before.permissions:
                        if perm_enabled:
                            granted_perms.append(
                           await self.bot._(after.guild.id, "permissions.list."+perm_id)
                        )
                        else:
                            revoked_perms.append(
                            await self.bot._(after.guild.id, "permissions.list."+perm_id)
                            )
                if revoked_perms:
                    emb.add_field(name="Revoked permissions", value=", ".join(revoked_perms), inline=False)
                if granted_perms:
                    emb.add_field(name="Granted permissions", value=", ".join(granted_perms), inline=False)
            # try to find who edited the role
            if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.role_update,
                                                     check=lambda entry: entry.target.id == after.id):
                emb.add_field(name="Edited by", value=f"**{entry.user.mention}** ({entry.user.id})", inline=False)
                if entry.reason:
                    emb.add_field(name="With reason", value=entry.reason)
            await self.validate_logs(after.guild, channel_ids, emb, "role_update")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Triggered when a role is deleted in a guild
        Corresponding log: role_deletion"""
        if channel_ids := await self.is_log_enabled(role.guild.id, "role_deletion"):
            emb = discord.Embed(
                description="**Role deleted**",
                colour=discord.Color.red()
            )
            emb.set_footer(text=f"Role ID: {role.id}")
            emb.add_field(name="Name", value=role.name, inline=False)
            emb.add_field(name="Color", value=str(role.color))
            if specs := await self.get_role_specs(role):
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            # try to find who deleted the role
            if entry := await self.search_audit_logs(role.guild, discord.AuditLogAction.role_delete,
                                                     check=lambda entry: entry.target.id == role.id):
                emb.add_field(name="Deleted by", value=f"**{entry.user.mention}** ({entry.user.id})")
                if entry.reason:
                    emb.add_field(name="With reason", value=entry.reason)
            await self.validate_logs(role.guild, channel_ids, emb, "role_deletion")


    @commands.Cog.listener()
    async def on_antiscam_warn(self, message: discord.Message, prediction: PredictionResult):
        """Triggered when the antiscam system find a potentially dangerous message
        Corresponding log: antiscam"""
        if channel_ids := await self.is_log_enabled(message.guild.id, "antiscam"):
            emb = discord.Embed(
                description=f"**Potentially dangerous [message]({message.jump_url})**",
                colour=discord.Color.orange()
            )
            await self.prepare_antiscam_embed(message, prediction, emb)
            await self.validate_logs(message.guild, channel_ids, emb, "antiscam")

    @commands.Cog.listener()
    async def on_antiscam_delete(self, message: discord.Message, prediction: PredictionResult):
        """Triggered when the antiscam system delete a dangerous message
        Corresponding log: antiscam"""
        if channel_ids := await self.is_log_enabled(message.guild.id, "antiscam"):
            emb = discord.Embed(
                description=f"**Dangerous [message]({message.jump_url}) deleted**",
                colour=discord.Color.red()
            )
            await self.prepare_antiscam_embed(message, prediction, emb)
            await self.validate_logs(message.guild, channel_ids, emb, "antiscam")

    async def prepare_antiscam_embed(self, message: discord.Message, prediction: PredictionResult, emb: discord.Embed):
        "Prepare the embed for an antiscam alert"
        # probabilities
        categories: dict = self.bot.get_cog("AntiScam").agent.categories
        emb.add_field(name="AI detection result", value=prediction.to_string(categories), inline=False)
        # message content
        content = message.content if len(message.content) < 1020 else message.content[:1020]+'…'
        emb.add_field(name="Message content", value=content)
        # author
        emb.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar)

    @commands.Cog.listener()
    async def on_antiraid_kick(self, member: discord.Member, data: dict[str, Any]):
        """Triggered when the antiraid system kicks a member
        Corresponding log: antiraid"""
        if channel_ids := await self.is_log_enabled(member.guild.id, "antiraid"):
            emb = discord.Embed(
                description=f"**{member.mention} ({member.id}) kicked by anti-raid**",
                colour=discord.Color.orange()
            )
            doc = "https://zbot.rtfd.io/en/latest/moderator.html#anti-raid"
            emb.set_author(name=str(member), url=doc, icon_url=member.display_avatar)
            # reason
            if account_creation_treshold := data.get("account_creation_treshold"):
                min_age = await FormatUtils.time_delta(account_creation_treshold, hour=(account_creation_treshold<86400))
                delta = await FormatUtils.time_delta(member.created_at, self.bot.utcnow(), hour=True)
                value = f"Account created at <t:{member.created_at.timestamp():.0f}> ({delta})\n\
Minimum age required by anti-raid: {min_age}"
                emb.add_field(name="Account was too recent", value=value, inline=False)
            if "discord_invite" in data:
                emb.add_field(name="Contains a Discord invite in their username", value=self.bot.zws, inline=False)
            await self.validate_logs(member.guild, channel_ids, emb, "antiraid")

    @commands.Cog.listener()
    async def on_antiraid_ban(self, member: discord.Member, data: dict[str, Any]):
        """Triggered when the antiraid system kicks a member
        Corresponding log: antiraid"""
        if channel_ids := await self.is_log_enabled(member.guild.id, "antiraid"):
            emb = discord.Embed(
                description=f"**{member.mention} ({member.id}) banned by anti-raid**",
                colour=discord.Color.red()
            )
            doc = "https://zbot.rtfd.io/en/latest/moderator.html#anti-raid"
            emb.set_author(name=str(member), url=doc, icon_url=member.display_avatar)
            # reason
            if account_creation_treshold := data.get("account_creation_treshold"):
                min_age = await FormatUtils.time_delta(
                    account_creation_treshold, hour=(account_creation_treshold < 86400))
                delta = await FormatUtils.time_delta(member.created_at, self.bot.utcnow(), hour=True)
                value = f"Account created at <t:{member.created_at.timestamp():.0f}> ({delta})\n\
Minimum age required by anti-raid: {min_age}"
                emb.add_field(name="Account was too recent", value=value, inline=False)
            if "discord_invite" in data:
                emb.add_field(name="Contains a Discord invite in their username", value=self.bot.zws, inline=False)
            # duration
            duration = await FormatUtils.time_delta(data["duration"], hour=(data["duration"] < 86400))
            emb.add_field(name="Duration", value=duration)
            await self.validate_logs(member.guild, channel_ids, emb, "antiraid")

    @commands.Cog.listener()
    async def on_ticket_creation(self, event: TicketCreationEvent):
        """Triggered when a ticket is successfully created
        Corresponding log: ticket_creation"""
        if channel_ids := await self.is_log_enabled(event.guild.id, "ticket_creation"):
            emb = discord.Embed(
                description=f"**{event.user.mention} ({event.user.id}) has opened a ticket**",
                colour=discord.Color.dark_grey()
            )
            if raw_emoji := event.topic_emoji:
                name = str(discord.PartialEmoji.from_str(raw_emoji)) + " " + event.topic_name
            else:
                name = event.topic_name
            emb.add_field(name="Topic", value=name)
            emb.add_field(name="Ticket name", value=event.name)
            emb.add_field(name="Channel", value=event.channel.mention, inline=False)
            await self.validate_logs(event.guild, channel_ids, emb, "ticket_creation")

    @commands.Cog.listener()
    async def on_server_warning(self, warning_type: ServerWarningType, guild: discord.Guild, **kwargs):
        """Triggered when the bot fails to do its job in a guild
        Corresponding log: bot_warnings"""
        if channel_ids := await self.is_log_enabled(guild.id, "bot_warnings"):
            emb = discord.Embed(colour=discord.Color.red())
            if warning_type == ServerWarningType.WELCOME_MISSING_TXT_PERMISSIONS:
                if kwargs.get("is_join"):
                    emb.description = f"**Could not send welcome message** in channel {kwargs.get('channel').mention}"
                else:

                    emb.description = f"**Could not send leaving message** in channel {kwargs.get('channel').mention}"
                emb.add_field(
                    name="Missing permission",
                    value=await self.bot._(guild.id, "permissions.list.send_messages")
                )
            elif warning_type in {ServerWarningType.RSS_MISSING_TXT_PERMISSION, ServerWarningType.RSS_MISSING_EMBED_PERMISSION}:
                emb.description = f"**Could not send RSS message** in channel {kwargs.get('channel').mention}"
                emb.add_field(name="Feed ID", value=kwargs.get('feed_id'))
                if warning_type == ServerWarningType.RSS_MISSING_TXT_PERMISSION:
                    emb.add_field(
                        name="Missing permission",
                        value=await self.bot._(guild.id, "permissions.list.send_messages")
                    )
                else:
                    emb.add_field(
                        name="Missing permission",
                        value=await self.bot._(guild.id, "permissions.list.embed_links")
                    )
            elif warning_type == ServerWarningType.RSS_UNKNOWN_CHANNEL:
                emb.description = f"**Could not send RSS message** in channel {kwargs.get('channel_id')}"
                emb.add_field(name="Feed ID", value=kwargs.get('feed_id'))
                emb.add_field(name="Reason", value="Unknown or deleted channel")
            elif warning_type == ServerWarningType.RSS_DISABLED_FEED:
                emb.description = f"**Feed has been disabled** in channel <#{kwargs.get('channel_id')}>"
                emb.add_field(name="Feed ID", value=kwargs.get('feed_id'))
                emb.add_field(name="Reason", value="Too many recent errors")
            elif warning_type == ServerWarningType.TICKET_CREATION_UNKNOWN_TARGET:
                emb.description = f"**Could not create ticket** in channel or category {kwargs.get('channel_id')}"
                emb.add_field(name="Selected topic", value=kwargs.get('topic_name'))
                emb.add_field(name="Reason", value="Unknown or deleted channel or category")
            elif warning_type == ServerWarningType.TICKET_CREATION_FAILED:
                channel = kwargs.get('channel')
                if isinstance(channel, discord.CategoryChannel):
                    emb.description = f"**Could not create ticket** in category {channel.name}"
                else:
                    emb.description = f"**Could not create ticket** in channel {channel.mention}"
                emb.add_field(name="Selected topic", value=kwargs.get('topic_name'))
                emb.add_field(
                    name="Missing permission",
                    value=await self.bot._(guild.id, "permissions.list.manage_channels")
                )
            elif warning_type == ServerWarningType.TICKET_INIT_FAILED:
                channel = kwargs.get('channel')
                if isinstance(channel, discord.CategoryChannel):
                    emb.description = f"**Could not setup ticket permissions** in category {channel.name}"
                else:
                    emb.description = f"**Could not setup ticket permissions** in channel {channel.mention}"
                emb.add_field(name="Selected topic", value=kwargs.get('topic_name'))
                emb.add_field(
                    name="Missing permission",
                    value=await self.bot._(guild.id, "permissions.list.manage_permissions")
                )
            else:
                return
            await self.validate_logs(guild, channel_ids, emb, "bot_warnings")


async def setup(bot):
    await bot.add_cog(ServerLogs(bot))
