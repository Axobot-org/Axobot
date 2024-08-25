import asyncio
import datetime
import time
from random import random
from typing import TYPE_CHECKING, Any, Callable

import discord
from cachetools import TTLCache
from discord import app_commands
from discord.ext import commands, tasks

from core.bot_classes import DISCORD_INVITE_REGEX, Axobot
from core.enums import ServerWarningType
from core.formatutils import FormatUtils
from core.tips import GuildTip
from modules.antiscam.model.classes import PredictionResult
from modules.tickets.src.types import TicketCreationEvent

from .arguments.serverlog_argument import (ALL_LOGS, LOGS_CATEGORIES,
                                           ServerLogArgument)

if TYPE_CHECKING:
    from modules.cases.cases import Case


class ServerLogs(commands.Cog):
    """Handle any kind of server log"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "serverlogs"
        self.cache = TTLCache[int, dict[int, list[str]]](maxsize=10_000, ttl=3600*4)
        self.to_send: dict[int, list[discord.Embed]] = {}
        self.auditlogs_timeout = 3 # seconds
        self.voice_join_timestamps: dict[tuple[int, int], float] = {}

    async def cog_load(self):
        self.send_logs_task.start() # pylint: disable=no-member

    async def cog_unload(self):
        self.send_logs_task.cancel() # pylint: disable=no-member


    async def is_log_enabled(self, guild_id: int, log: str) -> list[int]:
        "Check if a log kind is enabled for a guild, and return the corresponding logs channel ID"
        if not self.bot.database_online:
            return
        guild_logs = await self.db_get_from_guild(guild_id)
        res: list[int] = []
        for channel, event in guild_logs.items():
            if log in event:
                res.append(channel)
        return res

    async def validate_logs(self, guild_id: discord.Guild, channel_ids: list[int], embed: discord.Embed, log_type: str):
        "Send a log embed to the corresponding modlogs channels"
        for channel_id in channel_ids:
            if channel_id in self.to_send:
                self.to_send[channel_id].append(embed)
            else:
                self.to_send[channel_id] = [embed]
            self.bot.dispatch("serverlog", guild_id.id, channel_id, log_type)

    async def db_get_from_channel(self, guild_id: int, channel_id: int, use_cache: bool=True) -> list[str]:
        "Get enabled logs for a channel"
        if use_cache and (cached := self.cache.get(guild_id)) and channel_id in cached:
            return cached[channel_id]
        query = "SELECT kind FROM serverlogs WHERE guild = %s AND channel = %s AND beta = %s"
        async with self.bot.db_main.read(query, (guild_id, channel_id, self.bot.beta)) as query_results:
            return [row["kind"] for row in query_results]

    async def db_get_from_guild(self, guild_id: int, use_cache: bool=True) -> dict[int, list[str]]:
        """Get enabled logs for a guild
        Returns a map of ChannelID -> list of enabled logs"""
        if use_cache and (cached := self.cache.get(guild_id)):
            return cached
        query = "SELECT channel, kind FROM serverlogs WHERE guild = %s AND beta = %s"
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta)) as query_results:
            res = {}
            for row in query_results:
                res[row["channel"]] = res.get(row["channel"], []) + [row["kind"]]
            self.cache[guild_id] = res
            return res

    async def db_add(self, guild_id: int, channel_id: int, kind: str) -> bool:
        "Add logs to a channel"
        query = "INSERT INTO serverlogs (guild, channel, kind, beta) VALUES (%(g)s, %(c)s, %(k)s, %(b)s) "\
            "ON DUPLICATE KEY UPDATE guild=%(g)s"
        async with self.bot.db_main.write(query, {'g': guild_id, 'c': channel_id, 'k': kind, 'b': self.bot.beta}) as query_result:
            if query_result > 0 and guild_id in self.cache:
                if channel_id in self.cache[guild_id]:
                    self.cache[guild_id][channel_id].append(kind)
                else:
                    self.cache[guild_id][channel_id] = await self.db_get_from_channel(guild_id, channel_id, False)
            return query_result > 0

    async def db_remove(self, guild_id: int, channel_id: int, kind: str) -> bool:
        "Remove logs from a channel"
        query = "DELETE FROM serverlogs WHERE guild = %s AND channel = %s AND kind = %s AND beta = %s"
        async with self.bot.db_main.write(
            query, (guild_id, channel_id, kind, self.bot.beta), returnrowcount=True
        ) as query_result:
            if query_result > 0 and guild_id in self.cache:
                if channel_id in self.cache[guild_id]:
                    self.cache[guild_id][channel_id] = [x for x in self.cache[guild_id][channel_id] if x != kind]
                else:
                    self.cache[guild_id] = await self.db_get_from_guild(guild_id, use_cache=False)
            return query_result > 0


    @tasks.loop(seconds=15)
    async def send_logs_task(self):
        "Send ready logs every 15s to avoid rate limits"
        try:
            for channel_id, embeds in dict(self.to_send).items():
                channel = self.bot.get_channel(channel_id)
                if not embeds or channel is None or channel.guild.me is None:
                    self.to_send.pop(channel_id)
                    continue
                perms = channel.permissions_for(channel.guild.me)
                if not (perms.send_messages and perms.embed_links):
                    continue
                # send logs
                try:
                    embeds_to_send = await self._get_embeds_batch(embeds)
                    await channel.send(embeds=embeds_to_send)
                except discord.HTTPException as err:
                    self.bot.dispatch("error", err, f"Sending logs to guild {channel.guild.id} | Channel {channel.id}")
                    if not isinstance(err, discord.InvalidData):
                        # invalid data error is not recoverable, so we remove the logs
                        continue
                # remove sent embeds
                if len(embeds) > len(embeds_to_send):
                    self.to_send[channel_id] = self.to_send[channel_id][len(embeds_to_send):]
                else:
                    self.to_send.pop(channel_id)
        except Exception as err: # pylint: disable=broad-except
            self.bot.dispatch("error", err, None)

    @send_logs_task.before_loop
    async def before_logs_task(self):
        await self.bot.wait_until_ready()

    async def _get_embeds_batch(self, embeds: list[discord.Embed]):
        "Return a list of max. 10 embeds, such that the list do not exceed 6000 characters"
        batch: list[discord.Embed] = []
        current = 0
        for embed in embeds[:10]:
            if current + len(embed) > 6000:
                break
            batch.append(embed)
            current += len(embed)
        return batch

    modlogs_main = app_commands.Group(
        name="modlogs",
        description="Enable or disable server logs in specific channels",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True,
    )

    @modlogs_main.command(name="list")
    @app_commands.describe(channel="The channel to list logs for. Leave empty to list all logs for the server")
    @app_commands.checks.cooldown(1, 10)
    async def modlogs_list(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        """Show the full list of server logs type, or the list of enabled logs for a channel

        ..Example modlogs list

        ..Doc moderator.html#how-to-setup-logs"""
        await interaction.response.defer()
        if channel:  # display logs enabled for this channel only
            title = await self.bot._(interaction, "serverlogs.list.channel", channel='#'+channel.name)
            if channel_logs := await self.db_get_from_channel(interaction.guild_id, channel.id):
                embed = discord.Embed(title=title)
                for category, logs in sorted(LOGS_CATEGORIES.items()):
                    name = await self.bot._(interaction, "serverlogs.categories."+category)
                    actual_logs = ["- "+l for l in sorted(logs) if l in channel_logs]
                    if actual_logs:
                        embed.add_field(name=name, value='\n'.join(actual_logs))
            else: # error msg
                cmd = await self.bot.get_command_mention("modlogs enable")
                embed = discord.Embed(title=title, description=await self.bot._(interaction, "serverlogs.list.none", cmd=cmd))
        else:  # display available logs and logs enabled for the whole server
            global_title = await self.bot._(interaction, "serverlogs.list.all")
            # fetch logs enabled in the guild
            guild_logs = await self.db_get_from_guild(interaction.guild_id)
            guild_logs = sorted(set(x for v in guild_logs.values() for x in v if x in ALL_LOGS))
            # build embed
            if interaction.guild.me.guild_permissions.external_emojis and (cog := self.bot.emojis_manager):
                enabled_emoji, disabled_emoji = cog.customs["green_check"], cog.customs["gray_check"]
            else:
                enabled_emoji, disabled_emoji = '🔹', '◾'
            desc = await self.bot._(interaction, "serverlogs.list.emojis", enabled=enabled_emoji, disabled=disabled_emoji)
            embed = discord.Embed(title=global_title, description=desc)
            for category, logs in sorted(LOGS_CATEGORIES.items()):
                name = await self.bot._(interaction, "serverlogs.categories."+category)
                embed.add_field(name=name, value='\n'.join([
                    (enabled_emoji if l in guild_logs else disabled_emoji) + l for l in sorted(logs)
                    ]))

        embed.color = discord.Color.blue()
        await interaction.followup.send(embed=embed)

    @modlogs_main.command(name="enable")
    @app_commands.describe(channel="The channel to add logs to. Leave empty to select the current channel")
    async def modlogs_enable(self, interaction: discord.Interaction, logs: ServerLogArgument,
                             channel: discord.TextChannel | None = None):
        """Enable one or more logs in the current channel

        ..Example modlogs enable ban bot_warnings

        ..Example modlogs enable role_creation bot_warnings #mod-logs

        ..Doc moderator.html#how-to-setup-logs"""
        dest_channel = channel or interaction.channel
        currently_actived_logs = await self.db_get_from_channel(interaction.guild_id, dest_channel.id)
        actually_added: list[str] = []
        not_added: list[str] = []
        await interaction.response.defer()
        for log in logs:
            if log not in currently_actived_logs and await self.db_add(interaction.guild_id, dest_channel.id, log):
                actually_added.append(log)
            else:
                not_added.append(log)
        if actually_added:
            added = ", ".join(sorted(actually_added))
            if dest_channel == interaction.channel:
                msg = await self.bot._(interaction, "serverlogs.enabled.current", kind=added)
            else:
                msg = await self.bot._(interaction, "serverlogs.enabled.other", kind=added, channel=dest_channel.mention)
            if not_added:
                msg += "\n" + await self.bot._(
                    interaction, "serverlogs.enabled.already-enabled-list",
                    kinds=", ".join(not_added),
                    count=len(not_added)
                )
        else:
            msg = await self.bot._(interaction, "serverlogs.none-added")

        if not dest_channel.permissions_for(interaction.guild.me).embed_links:
            msg += "\n\n:warning: " + await self.bot._(interaction, "serverlogs.embed-warning")
        await interaction.followup.send(msg)
        if "member_kick" in actually_added:
            if await self.send_member_kick_warning(interaction):
                return
        if "antiscam" in actually_added:
            if await self.send_antiscam_tip(interaction):
                return
        if "antiraid" in actually_added:
            if await self.send_antiraid_tip(interaction):
                return
        if actually_added:
            if random() < 0.7 and await self.send_botwarning_tip(interaction):
                return

    @modlogs_enable.autocomplete("logs")
    async def _modlogs_enable_autocomplete(self, interaction: discord.Interaction, current: str):
        if channel := interaction.namespace.channel:
            channel_id: int = channel.id
        else:
            channel_id = interaction.channel_id
        actived_logs = await self.db_get_from_channel(interaction.guild_id, channel_id)
        available_logs = ALL_LOGS - set(actived_logs)
        if len(available_logs) == 0:
            return []
        return await self.log_name_autocomplete(
            current, available_logs,
            all_label=await self.bot._(interaction, "serverlogs.autocompletion-all")
        )


    @modlogs_main.command(name="disable")
    @app_commands.describe(channel="The channel to remove logs from. Leave empty to select the current channel")
    async def modlogs_disable(self, interaction: discord.Interaction, logs: ServerLogArgument,
                              channel: discord.TextChannel | None = None):
        """Disable one or more logs in the current channel

        ..Example modlogs disable ban message_delete

        ..Example modlogs disable ghost_ping #mod-logs

        ..Doc moderator.html#how-to-setup-logs"""
        dest_channel = channel or interaction.channel
        currently_actived_logs = await self.db_get_from_channel(interaction.guild_id, dest_channel.id)
        actually_removed: list[str] = []
        await interaction.response.defer()
        for log in logs:
            if log in currently_actived_logs and await self.db_remove(interaction.guild_id, dest_channel.id, log):
                actually_removed.append(log)
        if actually_removed:
            removed = ", ".join(sorted(actually_removed))
            if dest_channel == interaction.channel:
                msg = await self.bot._(interaction, "serverlogs.disabled.current", kind=removed)
            else:
                msg = await self.bot._(interaction, "serverlogs.disabled.other", kind=removed, channel=dest_channel.mention)
        else:
            msg = await self.bot._(interaction, "serverlogs.none-removed")
        await interaction.followup.send(msg)

    @modlogs_disable.autocomplete("logs")
    async def _modlogs_disable_autocomplete(self, interaction: discord.Interaction, current: str):
        if channel := interaction.namespace.channel:
            channel_id: int = channel.id
        else:
            channel_id = interaction.channel_id
        actived_logs = await self.db_get_from_channel(interaction.guild_id, channel_id)
        if len(actived_logs) == 0:
            return []
        return await self.log_name_autocomplete(
            current, actived_logs,
            all_label=await self.bot._(interaction, "serverlogs.autocompletion-all")
        )

    async def log_name_autocomplete(self, current: str, available_logs: list[str] | None=None, all_label: str="all"):
        "Autocompletion for log names"
        all_logs = list(ALL_LOGS) if available_logs is None else  available_logs
        filtered = sorted(
            (not option.startswith(current), option)
            for option in all_logs
            if current in option
        )
        choices = [
            app_commands.Choice(name=value[1], value=value[1])
            for value in filtered
        ][:24]
        choices.insert(0, app_commands.Choice(name=all_label, value="all"))
        return choices

    async def send_antiscam_tip(self, interaction: discord.Interaction):
        "Send a tip if antiscam log is enabled but not the antiscam system"
        antiscam_enabled: bool = await self.bot.get_config(interaction.guild_id, "anti_scam")
        if antiscam_enabled:
            return False
        if await self.bot.tips_manager.should_show_guild_tip(interaction.guild_id, GuildTip.SERVERLOG_ENABLE_ANTISCAM):
            antiscam_enable_cmd = await self.bot.get_command_mention("antiscam enable")
            await self.bot.tips_manager.send_guild_tip(
                interaction,
                GuildTip.SERVERLOG_ENABLE_ANTISCAM,
                antiscam_enable_cmd=antiscam_enable_cmd
            )
            return True
        return False

    async def send_antiraid_tip(self, interaction: discord.Interaction):
        "Send a tip if antiraid log is enabled but not the antiscam system"
        antiraid_level: str = await self.bot.get_config(interaction.guild_id, "anti_raid")
        if antiraid_level != "none":
            return False
        if await self.bot.tips_manager.should_show_guild_tip(interaction.guild_id, GuildTip.SERVERLOG_ENABLE_ANTIRAID):
            config_set_cmd = await self.bot.get_command_mention("config set")
            await self.bot.tips_manager.send_guild_tip(
                interaction,
                GuildTip.SERVERLOG_ENABLE_ANTIRAID,
                config_set_cmd=config_set_cmd
            )
            return True
        return False

    async def send_botwarning_tip(self, interaction: discord.Interaction):
        "Send a tip if bot_warnings log is not used in this guild"
        if interaction.guild is None or await self.is_log_enabled(interaction.guild_id, "bot_warnings"):
            return False
        if await self.bot.tips_manager.should_show_guild_tip(interaction.guild_id, GuildTip.SERVERLOG_ENABLE_BOTWARNING):
            log_add_cmd = await self.bot.get_command_mention("modlogs enable")
            await self.bot.tips_manager.send_guild_tip(
                interaction,
                GuildTip.SERVERLOG_ENABLE_BOTWARNING,
                log_add_cmd=log_add_cmd
            )
            return True
        return False

    async def send_member_kick_warning(self, interaction: discord.Interaction):
        "Warn the user if member kick log is enabled but bot has not access to guild audit logs"
        if interaction.guild.me.guild_permissions.view_audit_log:
            return
        await interaction.followup.send(await self.bot._(interaction.guild, "serverlogs.kick-warning"))

    async def search_audit_logs(self, guild: discord.Guild, action: discord.AuditLogAction,
                                check: Callable[[discord.AuditLogEntry], bool]=None):
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
                if stats_cog and action != discord.AuditLogAction.kick:
                    await stats_cog.on_serverlogs_audit_search(True)
                return entry
        if stats_cog and action != discord.AuditLogAction.kick:
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
                if "pinned" in msg.data and msg.cached_message.pinned != msg.data["pinned"]:
                    return
                old_content = msg.cached_message.content
                author = msg.cached_message.author
                guild = msg.cached_message.guild
                link = msg.cached_message.jump_url
            else:
                if "author" in msg.data and (author_id := msg.data.get("author").get("id")):
                    author = self.bot.get_user(int(author_id))
                guild = self.bot.get_guild(msg.guild_id)
                link = f"https://discord.com/channels/{msg.guild_id}/{msg.channel_id}/{msg.message_id}"
            new_content = msg.data.get("content")
            if new_content is None: # and msg.data.get("flags", 0) & 32:
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

    async def _format_attachments_list(self, attachments: list[discord.Attachment]) -> str:
        "Format a list of attachments into a string"
        count = 5
        def _format(attachments: list[discord.Attachment]):
            if len(attachments) > count:
                return " ".join(f"[{a.filename}]({a.url})" for a in attachments[:count]) + f" and {len(attachments)-count} more"
            return " ".join(f"[{a.filename}]({a.url})" for a in attachments[:count])
        while len(msg := _format(attachments)) > 1024:
            count -= 1
        return msg

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
                if msg.attachments:
                    field_title = "Attachment" if len(msg.attachments) == 1 else f"Attachments ({len(msg.attachments)})"
                    field_value = await self._format_attachments_list(msg.attachments)
                    emb.add_field(name=field_title, value=field_value)
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
        if (invites := DISCORD_INVITE_REGEX.findall(message.content)) and (
                channel_ids := await self.is_log_enabled(message.guild.id, "discord_invite")):
            emb = discord.Embed(
                description=f"**[Discord invite]({message.jump_url}) detected in {message.channel.mention}**",
                colour=discord.Color.orange()
            )
            emb.set_author(name=str(message.author), icon_url=message.author.display_avatar)
            if len(invites) == 1:
                try:
                    invite = await self.bot.fetch_invite(invites[0])
                except discord.HTTPException:
                    pass
                else:
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
        if (before.pending and not after.pending) and (
                channel_ids := await self.is_log_enabled(before.guild.id, "member_verification")):
            await self.handle_member_verification(before, after, channel_ids)
        # public flags
        if before.public_flags != after.public_flags and (
                channel_ids := await self.is_log_enabled(before.guild.id, "user_update")):
            await self.handle_member_flags(before, after, channel_ids)

    async def handle_member_roles(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_roles log"
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles and role in after.guild.roles]
        if len(added_roles) == 0 and len(removed_roles) == 0:
            return
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) updated**",
            color=discord.Color.blurple()
        )
        if removed_roles:
            emb.add_field(name="Roles revoked", value=' '.join(r.mention for r in removed_roles), inline=False)
        if added_roles:
            emb.add_field(name="Roles granted", value=' '.join(r.mention for r in added_roles), inline=False)
        emb.set_author(name=str(after), icon_url=after.display_avatar)
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
        emb.set_author(name=str(after), icon_url=after.display_avatar)
        after_nick = after.nick
        if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_update,
                                                 check=lambda entry: (
                                                     entry.target.id == before.id
                                                     and hasattr(entry.after, "nick")
                                                     and entry.after.nick == after_nick
                                                 )):
            emb.add_field(name="Edited by", value=f"**{entry.user.mention}** ({entry.user.id})")
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
        emb.set_author(name=str(after), icon_url=after.display_avatar)
        await self.validate_logs(after.guild, channel_ids, emb, "member_avatar")

    async def handle_member_timeout(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle member_timeout log at start"
        now = self.bot.utcnow() - datetime.timedelta(seconds=1)
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) set in timeout**",
            color=discord.Color.dark_gray()
        )
        duration = await FormatUtils.time_delta(now, after.timed_out_until, lang="en")
        emb.add_field(name="Duration", value=f"{duration} (until <t:{after.timed_out_until.timestamp():.0f}>)", inline=False)
        emb.set_author(name=str(after), icon_url=after.display_avatar)
        # try to get who timeouted that member
        if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_update,
                                                 check=lambda entry: (entry.target.id == before.id
                                                                      and entry.after.timed_out_until
                                                                      and (now - entry.created_at).total_seconds() < 5
                                                                      )):
            if entry.reason and entry.reason.endswith(self.bot.zws):
                # muted from the /mute command, so we ignore this event
                return
            emb.add_field(name="Timeout by", value=f"**{entry.user.mention}** ({entry.user.id})")
            if entry.reason:
                emb.add_field(name="With reason", value=entry.reason)
        await self.validate_logs(after.guild, channel_ids, emb, "member_timeout")

    async def handle_member_untimeout(self, before: discord.Member, after: discord.Member, channel_ids: list[int]):
        "Handle early un-timeout (member_timeout log)"
        now = self.bot.utcnow() - datetime.timedelta(seconds=1)
        emb = discord.Embed(
            description=f"**Member {before.mention} ({before.id}) no longer in timeout**",
            color=discord.Color.green()
        )
        duration = await FormatUtils.time_delta(now, before.timed_out_until, lang="en")
        emb.add_field(
            name="Planned timeout end",
            value=f"<t:{before.timed_out_until.timestamp():.0f}> (in {duration})",
            inline=False
        )
        emb.set_author(name=str(after), icon_url=after.display_avatar)
        # try to get who timeouted that member
        if entry := await self.search_audit_logs(before.guild, discord.AuditLogAction.member_update,
                                                 check=lambda entry: (entry.target.id == before.id
                                                                      and entry.before.timed_out_until
                                                                      and (now - entry.created_at).total_seconds() < 5
                                                                      )):
            if entry.reason and entry.reason.endswith(self.bot.zws):
                # muted from the /mute command, so we ignore this event
                return
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
        emb.set_author(name=str(after), icon_url=after.display_avatar)
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
            # try to wait for the invitation tracker event
            try:
                _, invite = await self.bot.wait_for("invite_used", timeout=2)
            except asyncio.TimeoutError:
                pass
            else:
                emb.add_field(
                    name="Invitation used",
                    value=await self._create_invite_field(invite)
                )
            emb.add_field(name="Account created at", value=f"<t:{member.created_at.timestamp():.0f}>", inline=False)
            if specs := await self.get_member_specs(member):
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            await self.validate_logs(member.guild, channel_ids, emb, "member_join")

    async def _create_invite_field(self, invite: dict[str, int | str | None]):
        "Create a field value for an invite used by a new member"
        text: list[str] = []
        if invite["name"]:
            invite_name = f"'{invite['name']}' ({invite['invite_id']})"
        else:
            invite_name = f"'{invite['invite_id']}'"
        if invite["max_uses"] == 1:
            text.append(f"Single use invite {invite_name}")
        elif invite["ephemeral"]:
            text.append(f"Ephemeral invite {invite_name}")
        else:
            text.append(f"Invite {invite_name}")
        if invite["user_id"]:
            text.append(f"Created by <@{invite['user_id']}> ({invite['user_id']})")
        if invite["last_count"]:
            text.append(f"Used {invite['last_count']} times now")
        return "\n".join(text)

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
            if entry.reason and entry.reason.endswith(self.bot.zws):
                # kicked from the /kick command, so we ignore this event
                return
            emb = discord.Embed(
                description=f"**{payload.user.mention} ({payload.user.id}) has been kicked**",
                colour=discord.Color.red()
            )
            emb.set_author(name=str(payload.user), icon_url=payload.user.display_avatar)
            emb.add_field(name="Kicked by", value=f"**{entry.user.mention}** ({entry.user.id})")
            if entry.reason:
                emb.add_field(name="With reason", value=entry.reason)
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
                if entry.reason and entry.reason.endswith(self.bot.zws):
                    # banned from the /ban command, so we ignore this event
                    return
                emb.add_field(name="Banned by", value=f"**{entry.user.mention}** ({entry.user.id})", inline=False)
                if entry.reason:
                    emb.add_field(name="With reason", value=entry.reason)
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
                if entry.reason and entry.reason.endswith(self.bot.zws):
                    # unbanned from the /unban command or after a tempban, so we ignore this event
                    return
                emb.add_field(name="Unbanned by", value=f"**{entry.user.mention}** ({entry.user.id})", inline=False)
                if entry.reason:
                    emb.add_field(name="With reason", value=entry.reason)
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
            color_url = f"https://www.color-hex.com/color/{role.color.value:06x}"
            emb.add_field(name="Color", value=f"[{role.color}]({color_url})")
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
                before_color_url = f"https://www.color-hex.com/color/{before.color.value:06x}"
                after_color_url = f"https://www.color-hex.com/color/{after.color.value:06x}"
                txt = f"[{before.color}]({before_color_url}) -> [{after.color}]({after_color_url})"
                emb.add_field(name="Color", value=txt, inline=False)
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
            if len(emb.fields) == 0:
                # nothing we care about was edited
                return
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
            color_url = f"https://www.color-hex.com/color/{role.color.value:06x}"
            emb.add_field(name="Color", value=f"[{role.color}]({color_url})")
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

    @commands.Cog.listener()
    async def on_antiscam_report(self, message: discord.Message, prediction: PredictionResult, user: discord.Member):
        """Triggered when someone reports a potential scam message
        Corresponding log: antiscam"""
        if channel_ids := await self.is_log_enabled(message.guild.id, "antiscam"):
            emb = discord.Embed(
                description=f"**Scam [message]({message.jump_url}) reported** by one of your members",
                colour=discord.Color.orange()
            )
            emb.set_footer(text=f"Reported by {user}", icon_url=user.display_avatar)
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
    async def on_antiraid_timeout(self, member: discord.Member, data: dict[str, Any]):
        """Triggered when the antiraid system timeouts a member
        Corresponding log: antiraid"""
        if channel_ids := await self.is_log_enabled(member.guild.id, "antiraid"):
            emb = discord.Embed(
                description=f"**{member.mention} ({member.id}) set in timeout by anti-raid**",
                colour=discord.Color.orange()
            )
            doc = f"{self.bot.doc_url}moderator.html#anti-raid"
            emb.set_author(name=str(member), url=doc, icon_url=member.display_avatar)
            # mentions treshold
            if mentions_treshold := data.get("mentions_treshold"):
                emb.add_field(name="Mentions treshold", value=mentions_treshold)
            # invites theshold
            if invites_treshold := data.get("invites_treshold"):
                emb.add_field(name="Invites treshold", value=invites_treshold)
            # duration
            if duration := data.get("duration"):
                lang = await self.bot._(member.guild.id, "_used_locale")
                f_duration = await FormatUtils.time_delta(duration, lang=lang)
                emb.add_field(name="Duration", value=f_duration)
            # account creation date
            emb.add_field(name="Account created at", value=f"<t:{member.created_at.timestamp():.0f}>")
            await self.validate_logs(member.guild, channel_ids, emb, "antiraid")

    @commands.Cog.listener()
    async def on_antiraid_kick(self, member: discord.Member, data: dict[str, Any]):
        """Triggered when the antiraid system kicks a member
        Corresponding log: antiraid"""
        if channel_ids := await self.is_log_enabled(member.guild.id, "antiraid"):
            emb = discord.Embed(
                description=f"**{member.mention} ({member.id}) kicked by anti-raid**",
                colour=discord.Color.orange()
            )
            doc = f"{self.bot.doc_url}moderator.html#anti-raid"
            emb.set_author(name=str(member), url=doc, icon_url=member.display_avatar)
            # reason
            if account_creation_treshold := data.get("account_creation_treshold"):
                show_hour = account_creation_treshold<86400
                min_age = await FormatUtils.time_delta(account_creation_treshold, hour=show_hour)
                delta = await FormatUtils.time_delta(member.created_at, self.bot.utcnow(), hour=True)
                value = f"Account created at <t:{member.created_at.timestamp():.0f}> ({delta})\n\
Minimum age required by anti-raid: {min_age}"
                emb.add_field(name="Account was too recent", value=value, inline=False)
            # mentions treshold
            if mentions_treshold := data.get("mentions_treshold"):
                emb.add_field(name="Mentions treshold", value=mentions_treshold)
            # invites theshold
            if invites_treshold := data.get("invites_treshold"):
                emb.add_field(name="Invites treshold", value=invites_treshold)
            # discord invite
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
            doc = f"{self.bot.doc_url}moderator.html#anti-raid"
            emb.set_author(name=str(member), url=doc, icon_url=member.display_avatar)
            # reason
            if account_creation_treshold := data.get("account_creation_treshold"):
                show_hour = account_creation_treshold < 86400
                min_age = await FormatUtils.time_delta(account_creation_treshold, hour=show_hour)
                delta = await FormatUtils.time_delta(member.created_at, self.bot.utcnow(), hour=True)
                value = f"Account created at <t:{member.created_at.timestamp():.0f}> ({delta})\n\
Minimum age required by anti-raid: {min_age}"
                emb.add_field(name="Account was too recent", value=value, inline=False)
            # mentions treshold
            if mentions_treshold := data.get("mentions_treshold"):
                emb.add_field(name="Mentions treshold", value=mentions_treshold)
            # invites theshold
            if invites_treshold := data.get("invites_treshold"):
                emb.add_field(name="Invites treshold", value=invites_treshold)
            # discord invite
            if "discord_invite" in data:
                emb.add_field(name="Contains a Discord invite in their username", value=self.bot.zws, inline=False)
            # duration
            show_hour = data["duration"] < 86400
            duration = await FormatUtils.time_delta(data["duration"], hour=show_hour)
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
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """Triggered when a guild is updated
        Corresponding log: server_update"""
        if channel_ids := await self.is_log_enabled(after.id, "server_update"):
            if before.features != after.features:
                await self.handle_guild_features(before, after, channel_ids)
            if before.icon != after.icon:
                await self.handle_guild_icon(before, after, channel_ids)
            if before.name != after.name:
                await self.handle_guild_name(before, after, channel_ids)
            if before.owner != after.owner:
                await self.handle_guild_owner(before, after, channel_ids)

    async def handle_guild_features(self, before: discord.Guild, after: discord.Guild, channel_ids: list[int]):
        """Handle when guild receives or loses perks"""
        emb = discord.Embed(
            description="**Server features updates**",
            colour=discord.Color.blurple()
        )
        async def _(key: str):
            res = await self.bot._(after.id, "info.info.guild-features."+key)
            return key if "." in res else res
        removed_features = [await _(f) for f in before.features if f not in after.features]
        added_features = [await _(f) for f in after.features if f not in before.features]
        if len(removed_features + added_features) == 0:
            return
        if removed_features:
            emb.add_field(name="Removed features", value="\n".join(removed_features))
        if added_features:
            emb.add_field(name="Added features", value="\n".join(added_features))
        await self.validate_logs(after, channel_ids, emb, "server_update")

    async def handle_guild_icon(self, before: discord.Guild, after: discord.Guild, channel_ids: list[int]):
        """Handle the guild icon update log"""
        if before.icon is None:
            emb = discord.Embed(
                description="**Server icon added**",
                colour=discord.Color.blurple(),
            )
            emb.set_image(url=after.icon)
        elif after.icon is None:
            emb = discord.Embed(
                description="**Server icon removed**",
                colour=discord.Color.blurple(),
            )
            emb.add_field(name="Previous icon", value=before.icon.url)
        else:
            emb = discord.Embed(
                description="**Server icon updated**",
                colour=discord.Color.blurple(),
            )
            emb.add_field(name="Previous icon", value=before.icon.url)
            emb.add_field(name="New icon", value=after.icon.url)
            emb.set_image(url=after.icon)
        await self.validate_logs(after, channel_ids, emb, "server_update")

    async def handle_guild_name(self, before: discord.Guild, after: discord.Guild, channel_ids: list[int]):
        """Handle the guild name update log"""
        if before.name != after.name:
            emb = discord.Embed(
                description="**Server name updated**",
                colour=discord.Color.blurple(),
            )
            emb.add_field(name="Previous name", value=before.name)
            emb.add_field(name="New name", value=after.name)
            await self.validate_logs(after, channel_ids, emb, "server_update")

    async def handle_guild_owner(self, before: discord.Guild, after: discord.Guild, channel_ids: list[int]):
        """Handle the guild owner update log"""
        if before.owner != after.owner:
            emb = discord.Embed(
                description="**Server owner updated**",
                colour=discord.Color.blurple(),
            )
            if before.owner is None:
                emb.add_field(name="Previous owner", value="Unknown")
            else:
                emb.add_field(name="Previous owner", value=f"{before.owner.mention} ({before.owner.id})")
            if after.owner is None:
                emb.add_field(name="New owner", value="Unknown")
            else:
                emb.add_field(name="New owner", value=f"{after.owner.mention} ({after.owner.id})")
            await self.validate_logs(after, channel_ids, emb, "server_update")

    @commands.Cog.listener()
    async def on_moderation_slowmode(self, channel: discord.abc.GuildChannel, author: discord.Member, duration: int):
        """Triggered when someone uses the slowmode command
        Corresponding log: slowmode"""
        if channel_ids := await self.is_log_enabled(channel.guild.id, "slowmode"):
            if duration == 0:
                emb = discord.Embed(
                    description=f"**Slowmode disabled** in {channel.mention}",
                    colour=discord.Color.greyple()
                )
            else:
                emb = discord.Embed(
                    description=f"**Slowmode activated** in {channel.mention}",
                    colour=discord.Color.orange()
                )
                lang = await self.bot._(channel.guild.id, "_used_locale")
                f_duration = await FormatUtils.time_delta(duration, lang=lang)
                emb.add_field(name="Duration", value=f_duration)
            emb.add_field(name="Moderator", value=author.mention)
            emb.set_author(name=author, icon_url=author.display_avatar)
            await self.validate_logs(channel.guild, channel_ids, emb, "slowmode")

    @commands.Cog.listener()
    async def on_moderation_clear(self, channel: discord.abc.GuildChannel, author: discord.Member, messages_count: int):
        """Triggered when someone uses the clear command
        Corresponding log: clear"""
        if channel_ids := await self.is_log_enabled(channel.guild.id, "clear"):
            emb = discord.Embed(
                description=f"**{messages_count} messages deleted** in {channel.mention}",
                colour=discord.Color.red()
            )
            emb.add_field(name="Moderator", value=author.mention)
            emb.set_author(name=author, icon_url=author.display_avatar)
            await self.validate_logs(channel.guild, channel_ids, emb, "clear")

    @commands.Cog.listener()
    async def on_moderation_ban(self, guild: discord.Guild, author: discord.Member, user: discord.User,
                                case_id: int | None, reason: str | None, duration: int | None):
        """Triggered when someone uses the ban command
        Corresponding log: member_ban"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_ban"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been banned**",
                colour=discord.Color.red()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Banned by", value=f"**{author.mention}** ({author.id})", inline=False)
            if reason:
                emb.add_field(name="With reason", value=reason)
            if case_id:
                emb.add_field(name="Case ID", value=f"#{case_id}")
            if duration:
                lang = await self.bot._(guild.id, "_used_locale")
                f_duration = await FormatUtils.time_delta(duration, lang=lang)
                planned_unban = time.time() + duration
                emb.add_field(name="Ban duration", value=f"{f_duration} (until <t:{planned_unban:.0f}>)")
            await self.validate_logs(guild, channel_ids, emb, "member_ban")

    @commands.Cog.listener()
    async def on_moderation_unban(self, guild: discord.Guild, author: discord.Member, user: discord.user,
                                  case_id: int | None, reason: str | None):
        """Triggered when someone uses the unban command
        Corresponding log: member_unban"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_unban"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been unbanned**",
                colour=discord.Color.green()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Unbanned by", value=f"**{author.mention}** ({author.id})", inline=False)
            if reason:
                emb.add_field(name="With reason", value=reason)
            if case_id:
                emb.add_field(name="Case ID", value=f"#{case_id}")
            await self.validate_logs(guild, channel_ids, emb, "member_unban")

    @commands.Cog.listener()
    async def on_tempban_expiration(self, guild: discord.Guild, user: discord.User, ban_date: datetime.datetime):
        """Triggered when a tempban expires
        Corresponding log: member_unban"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_unban"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been unbanned** after a tempban",
                colour=discord.Color.green()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            f_date = f"<t:{ban_date.timestamp():.0f}>"
            emb.add_field(name="Ban date", value=f_date)
            await self.validate_logs(guild, channel_ids, emb, "member_unban")

    @commands.Cog.listener()
    async def on_moderation_softban(self, guild: discord.Guild, author: discord.Member, user: discord.User,
                                    case_id: int | None, reason: str | None):
        """Triggered when someone uses the softban command
        Corresponding log: member_kick"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_kick"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been softbanned**",
                colour=discord.Color.orange()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Softbanned by", value=f"**{author.mention}** ({author.id})", inline=False)
            if reason:
                emb.add_field(name="With reason", value=reason)
            if case_id:
                emb.add_field(name="Case ID", value=f"#{case_id}")
            await self.validate_logs(guild, channel_ids, emb, "member_kick")

    @commands.Cog.listener()
    async def on_moderation_kick(self, guild: discord.Guild, author: discord.Member, user: discord.User,
                                 case_id: int | None, reason: str | None):
        """Triggered when someone uses the kick command
        Corresponding log: member_kick"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_kick"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been kicked**",
                colour=discord.Color.orange()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Kicked by", value=f"**{author.mention}** ({author.id})", inline=False)
            if reason:
                emb.add_field(name="With reason", value=reason)
            if case_id:
                emb.add_field(name="Case ID", value=f"#{case_id}")
            await self.validate_logs(guild, channel_ids, emb, "member_kick")

    @commands.Cog.listener()
    async def on_moderation_mute(self, guild: discord.Guild, author: discord.Member, user: discord.Member,
                                 case_id: int | None, reason: str | None, duration: int | None):
        """Triggered when someone uses the mute command
        Corresponding log: member_timeout"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_timeout"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been muted**",
                colour=discord.Color.dark_gray()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Muted by", value=f"**{author.mention}** ({author.id})", inline=False)
            if reason:
                emb.add_field(name="With reason", value=reason)
            if case_id:
                emb.add_field(name="Case ID", value=f"#{case_id}")
            if duration:
                lang = await self.bot._(guild.id, "_used_locale")
                f_duration = await FormatUtils.time_delta(duration, lang=lang)
                planned_unmute = time.time() + duration
                emb.add_field(name="Mute duration", value=f"{f_duration} (until <t:{planned_unmute:.0f}>)")
            await self.validate_logs(guild, channel_ids, emb, "member_timeout")

    @commands.Cog.listener()
    async def on_tempmute_expiration(self, guild: discord.Guild, user: discord.Member, mute_date: datetime.datetime):
        """Triggered when a tempmute expires
        Corresponding log: member_timeout"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_timeout"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been unmuted** after a tempmute",
                colour=discord.Color.green()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            f_date = f"<t:{mute_date.timestamp():.0f}>"
            emb.add_field(name="Mute date", value=f_date)
            await self.validate_logs(guild, channel_ids, emb, "member_timeout")

    @commands.Cog.listener()
    async def on_moderation_unmute(self, guild: discord.Guild, author: discord.Member, user: discord.Member):
        """Triggered when someone uses the unmute command
        Corresponding log: member_timeout"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_timeout"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been unmuted**",
                colour=discord.Color.green()
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Unmuted by", value=f"**{author.mention}** ({author.id})", inline=False)
            await self.validate_logs(guild, channel_ids, emb, "member_timeout")

    @commands.Cog.listener()
    async def on_moderation_warn(self, guild: discord.Guild, author: discord.Member, user: discord.Member,
                                 case_id: int | None, message: str):
        """Triggered when someone uses the warn command
        Corresponding log: member_warn"""
        if channel_ids := await self.is_log_enabled(guild.id, "member_warn"):
            emb = discord.Embed(
                description=f"**{user.mention} ({user.id}) has been warned**",
                colour=0x8B572A
            )
            emb.set_author(name=user, icon_url=user.display_avatar)
            emb.add_field(name="Warned by", value=f"**{author.mention}** ({author.id})", inline=False)
            emb.add_field(name="With reason", value=message)
            if case_id:
                emb.add_field(name="Case ID", value=f"#{case_id}")
            await self.validate_logs(guild, channel_ids, emb, "member_warn")

    @commands.Cog.listener()
    async def on_case_edit(self, guild: discord.Guild, before: "Case", after: "Case"):
        """Triggered when a case is edited
        Corresponding log: moderation_case"""
        if channel_ids := await self.is_log_enabled(guild.id, "moderation_case"):
            emb = discord.Embed(
                description=f"**Case #{after.id} edited**",
                colour=discord.Color.orange()
            )
            if moderator := self.bot.get_user(after.mod_id):
                emb.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})")
            else:
                emb.add_field(name="Moderator", value=f"Unknown ({after.mod_id})")
            emb.add_field(name="Old reason", value=before.reason)
            emb.add_field(name="New reason", value=after.reason)
            if moderator:
                emb.set_author(name=moderator, icon_url=moderator.display_avatar)
            await self.validate_logs(guild, channel_ids, emb, "case_edit")

    @commands.Cog.listener()
    async def on_case_delete(self, guild: discord.Guild, case: "Case"):
        """Triggered when a case is deleted
        Corresponding log: moderation_case"""
        if channel_ids := await self.is_log_enabled(guild.id, "moderation_case"):
            emb = discord.Embed(
                description=f"**Case #{case.id} deleted**",
                colour=discord.Color.red()
            )
            if moderator := self.bot.get_user(case.mod_id):
                emb.add_field(name="Moderator", value=f"{moderator.mention} ({moderator.id})")
            else:
                emb.add_field(name="Moderator", value=f"Unknown ({case.mod_id})")
            if user := self.bot.get_user(case.user_id):
                emb.add_field(name="User", value=f"{user.mention} ({user.id})")
            else:
                emb.add_field(name="User", value=f"Unknown ({case.user_id})")
            emb.add_field(name="Reason", value=case.reason)
            if moderator:
                emb.set_author(name=moderator, icon_url=moderator.display_avatar)
            await self.validate_logs(guild, channel_ids, emb, "case_delete")

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
            elif warning_type == ServerWarningType.WELCOME_ROLE_MISSING_PERMISSIONS:
                emb.description = f"**Could not give welcome role** to user {kwargs.get('user').mention}"
                emb.add_field(
                    name="Role to give",
                    value=kwargs.get("role").mention
                )
            elif warning_type in {ServerWarningType.RSS_MISSING_TXT_PERMISSION, ServerWarningType.RSS_MISSING_EMBED_PERMISSION}:
                emb.description = f"**Could not send RSS message** in channel {kwargs.get('channel').mention}"
                emb.add_field(name="Feed ID", value=kwargs.get("feed_id"))
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
                emb.add_field(name="Feed ID", value=kwargs.get("feed_id"))
                emb.add_field(name="Reason", value="Unknown or deleted channel")
            elif warning_type == ServerWarningType.RSS_DISABLED_FEED:
                emb.description = f"**Feed has been disabled** in channel <#{kwargs.get('channel_id')}>"
                emb.add_field(name="Feed ID", value=kwargs.get("feed_id"))
                emb.add_field(name="Reason", value="Too many recent errors")
            elif warning_type == ServerWarningType.RSS_TWITTER_DISABLED:
                emb.description = "Due to a recent Twitter API change, **Twitter feeds are not supported** anymore.\n"\
                    "You should consider deleting this RSS feed."
                emb.add_field(name="Feed ID", value=kwargs.get("feed_id"))
                emb.add_field(name="Reason", value="Withdrawal of the free Twitter API")
            elif warning_type == ServerWarningType.RSS_INVALID_FORMAT:
                emb.description = f"**Could not send RSS message** in channel {kwargs.get('channel').mention}"
                emb.add_field(name="Feed ID", value=kwargs.get("feed_id"))
                rss_text_cmd = await self.bot.get_command_mention("rss set-text")
                emb.add_field(name="Reason",
                              value=f"Invalid template format. Use the {rss_text_cmd} command to fix your template.")
            elif warning_type == ServerWarningType.TICKET_CREATION_UNKNOWN_TARGET:
                emb.description = f"**Could not create ticket** in channel or category {kwargs.get('channel_id')}"
                emb.add_field(name="Selected topic", value=kwargs.get("topic_name"))
                emb.add_field(name="Reason", value="Unknown or deleted channel or category")
            elif warning_type == ServerWarningType.TICKET_CREATION_FAILED:
                channel = kwargs.get("channel")
                if isinstance(channel, discord.CategoryChannel):
                    emb.description = f"**Could not create ticket** in category {channel.name}"
                else:
                    emb.description = f"**Could not create ticket** in channel {channel.mention}"
                emb.add_field(name="Selected topic", value=kwargs.get("topic_name"))
                emb.add_field(
                    name="Missing permission",
                    value=await self.bot._(guild.id, "permissions.list.manage_channels")
                )
            elif warning_type == ServerWarningType.TICKET_INIT_FAILED:
                channel = kwargs.get("channel")
                if isinstance(channel, discord.CategoryChannel):
                    emb.description = f"**Could not setup ticket permissions** in category {channel.name}"
                else:
                    emb.description = f"**Could not setup ticket permissions** in channel {channel.mention}"
                emb.add_field(name="Selected topic", value=kwargs.get("topic_name"))
                emb.add_field(
                    name="Missing permission",
                    value=await self.bot._(guild.id, "permissions.list.manage_permissions")
                )
            elif warning_type == ServerWarningType.TEMP_ROLE_REMOVE_FORBIDDEN:
                role = kwargs.get("role")
                user = kwargs.get("user")
                emb.description = f"**Could not remove temporary role** {role.mention} from user {user.mention}"
                emb.add_field(name="Reason", value="Missing permission")
            else:
                return
            await self.validate_logs(guild, channel_ids, emb, "bot_warnings")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Triggered when a member changes their voice state (changes channel, mutes, deafen, etc.)
        Corresponding log: voice_join, voice_leave, voice_move"""
        if before.channel == after.channel:
            return
        if before.channel is None and after.channel is not None:
            # voice_join
            self.voice_join_timestamps[(member.id, after.channel.id)] = time.time()
            if channel_ids := await self.is_log_enabled(member.guild.id, "voice_join"):
                emb = discord.Embed(
                    description=f"**{member.mention} ({member.id}) joined {after.channel.mention}**",
                    colour=discord.Color.light_grey()
                )
                emb.set_author(name=member, icon_url=member.display_avatar)
                await self.validate_logs(member.guild, channel_ids, emb, "voice_join")
        elif before.channel is not None and after.channel is None:
            # voice_leave
            if channel_ids := await self.is_log_enabled(member.guild.id, "voice_leave"):
                emb = discord.Embed(
                    description=f"**{member.mention} ({member.id}) left {before.channel.mention}**",
                    colour=discord.Color.light_grey()
                )
                emb.set_author(name=member, icon_url=member.display_avatar)
                if join_timestamp := self.voice_join_timestamps.get((member.id, before.channel.id)):
                    duration = await FormatUtils.time_delta(time.time() - join_timestamp)
                    emb.add_field(name="Time spent in the channel", value=duration)
                    del self.voice_join_timestamps[(member.id, before.channel.id)]
                await self.validate_logs(member.guild, channel_ids, emb, "voice_leave")
        else:
            # voice_move
            self.voice_join_timestamps[(member.id, after.channel.id)] = time.time()
            if channel_ids := await self.is_log_enabled(member.guild.id, "voice_move"):
                emb = discord.Embed(
                    description=
                    f"**{member.mention} ({member.id}) moved from {before.channel.mention} to {after.channel.mention}**",
                    colour=discord.Color.light_grey()
                )
                emb.set_author(name=member, icon_url=member.display_avatar)
                if join_timestamp := self.voice_join_timestamps.get((member.id, before.channel.id)):
                    duration = await FormatUtils.time_delta(time.time() - join_timestamp)
                    emb.add_field(name="Time spent in the channel", value=duration)
                    del self.voice_join_timestamps[(member.id, before.channel.id)]
                await self.validate_logs(member.guild, channel_ids, emb, "voice_move")


async def setup(bot):
    await bot.add_cog(ServerLogs(bot))
