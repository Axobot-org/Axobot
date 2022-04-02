import asyncio
from typing import Any

import discord
from cachingutils import LRUCache
from discord.ext import commands, tasks
from libs.antiscam.classes import PredictionResult
from libs.classes import MyContext, Zbot
from libs.formatutils import FormatUtils

from fcts.args import serverlog


class ServerLogs(commands.Cog):
    """Handle any kind of server log"""

    available_logs = {
        "antiraid",
        "antiscam",
        "member_roles",
        "member_nick",
        "member_avatar",
        "member_join",
        "member_leave",
        "member_ban",
        "member_unban",
        "message_update",
        "message_delete",
        "role_creation"
    }

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "serverlogs"
        self.cache: LRUCache[int, dict[int, list[str]]] = LRUCache(max_size=10000, timeout=3600*4)
        self.to_send: dict[discord.TextChannel, list[discord.Embed]] = {}
        self.auditlogs_timeout = 3 # seconds
        self.send_logs_task.start() # pylint: disable=no-member


    async def is_log_enabled(self, guild: int, log: str) -> list[int]:
        "Check if a log kind is enabled for a guild, and return the corresponding logs channel ID"
        guild_logs = await self.db_get_from_guild(guild)
        res: list[int] = []
        for channel, event in guild_logs.items():
            if log in event:
                res.append(channel)
        return res

    async def validate_logs(self, guild: discord.Guild, channel_ids: list[int], embed: discord.Embed):
        "Send a log embed to the corresponding modlogs channels"
        for channel_id in channel_ids:
            if channel := guild.get_channel(channel_id):
                if channel in self.to_send:
                    self.to_send[channel].append(embed)
                else:
                    self.to_send[channel] = [embed]

    async def db_get_from_channel(self, guild: int, channel: int) -> list[str]:
        "Get enabled logs for a channel"
        if (cached := self.cache.get(guild)) and channel in cached:
            return cached[channel]
        query = "SELECT kind FROM serverlogs WHERE guild = %s AND channel = %s"
        async with self.bot.db_query(query, (guild, channel)) as query_results:
            self.cache[guild] = [row['kind'] for row in query_results]
            return [row['kind'] for row in query_results]

    async def db_get_from_guild(self, guild: int) -> dict[int, list[str]]:
        "Get enabled logs for a guild"
        if cached := self.cache.get(guild):
            return cached
        query = "SELECT channel, kind FROM serverlogs WHERE guild = %s"
        async with self.bot.db_query(query, (guild,)) as query_results:
            res = dict()
            for row in query_results:
                res[row['channel']] = res.get(row['channel'], []) + [row['kind']]
            self.cache[guild] = res
            return res

    async def db_add(self, guild: int, channel: int, kind: str) -> bool:
        "Add logs to a channel"
        query = "INSERT INTO serverlogs (guild, channel, kind) VALUES (%(g)s, %(c)s, %(k)s) ON DUPLICATE KEY UPDATE guild=%(g)s"
        async with self.bot.db_query(query, {'g': guild, 'c': channel, 'k': kind}) as query_result:
            if query_result > 0 and guild in self.cache:
                if channel in self.cache[guild]:
                    self.cache[guild][channel].append(kind)
            return query_result > 0

    async def db_remove(self, guild: int, channel: int, kind: str) -> bool:
        "Remove logs from a channel"
        query = "DELETE FROM serverlogs WHERE guild = %s AND channel = %s AND kind = %s"
        async with self.bot.db_query(query, (guild, channel, kind), returnrowcount=True) as query_result:
            if query_result > 0 and guild in self.cache and channel in self.cache[guild]:
                self.cache[guild][channel] = [x for x in self.cache[guild][channel] if x != kind]
            return query_result > 0


    @tasks.loop(seconds=30)
    async def send_logs_task(self):
        "Send ready logs every 1min to avoid rate limits"
        for channel, embeds in dict(self.to_send).items():
            perms = channel.permissions_for(channel.guild.me)
            if perms.send_messages and perms.embed_links:
                await channel.send(embeds=embeds)
                self.to_send.pop(channel)

    @send_logs_task.before_loop
    async def before_logs_task(self):
        await self.bot.wait_until_ready()


    @commands.group(name="modlogs")
    @commands.guild_only()
    @commands.cooldown(2, 6, commands.BucketType.guild)
    async def modlogs_main(self, ctx: MyContext):
        """Enable or disable server logs in specific channels"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['modlogs'])

    @modlogs_main.command(name="list")
    @commands.cooldown(1, 10, commands.BucketType.channel)
    async def modlogs_list(self, ctx: MyContext, channel: discord.TextChannel=None):
        """Show the full list of server logs type, or the list of enabled logs for a channel"""
        if channel:
            # display logs enabled for this channel only
            title = await self.bot._(ctx.guild.id, "serverlogs.list.channel", channel='#'+channel.name)
            if channel_logs := await self.db_get_from_channel(ctx.guild.id, ctx.channel.id):
                actual_logs = ('- '+l for l in sorted(channel_logs) if l in self.available_logs)
                embed = discord.Embed(title=title, description='\n'.join(actual_logs))
            else: # error msg
                cmd = await self.bot.prefix_manager.get_prefix(ctx.guild) + "modlogs enable"
                embed = discord.Embed(title=title, description=await self.bot._(ctx.guild.id, "serverlogs.list.none", cmd=cmd))
        else:
            # display available logs and logs enabled for the whole server
            global_title = await self.bot._(ctx.guild.id, "serverlogs.list.all")
            guild_title = await self.bot._(ctx.guild.id, "serverlogs.list.guild")
            embed = discord.Embed()
            embed.add_field(name=global_title, value='\n'.join('- '+l for l in sorted(self.available_logs)))
            if (guild_logs := await self.db_get_from_guild(ctx.guild.id)) and \
                    sum(len(values) for values in guild_logs.values()) > 0:
                # flatten and sort enabled logs
                guild_logs = sorted(set(x for v in guild_logs.values() for x in v if x in self.available_logs))
                embed.add_field(name=guild_title, value='\n'.join('- '+l for l in sorted(guild_logs)))
            else: # error msg
                cmd = await self.bot.prefix_manager.get_prefix(ctx.guild) + "modlogs enable"
                embed.add_field(name=guild_title, value=await self.bot._(ctx.guild.id, "serverlogs.list.none", cmd=cmd))
        embed.color = discord.Color.blue()
        await ctx.send(embed=embed)

    @modlogs_main.command(name="enable", aliases=['add'])
    async def modlogs_enable(self, ctx: MyContext, logs: commands.Greedy[serverlog]):
        """Enable one or more logs in the current channel"""
        logs: list[str]
        if len(logs) == 0:
            raise commands.BadArgument('Invalid server log type')
        if 'all' in logs:
            logs = list(self.available_logs)
        actually_added: list[str] = []
        for log in logs:
            if await self.db_add(ctx.guild.id, ctx.channel.id, log):
                actually_added.append(log)
        if actually_added:
            msg = await self.bot._(ctx.guild.id, "serverlogs.enabled", kind=', '.join(actually_added))
            if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
                msg += "\n:warning: " + await self.bot._(ctx.guild.id, "serverlogs.embed-warning")
        else:
            msg = await self.bot._(ctx.guild.id, "serverlogs.none-added")
        await ctx.send(msg)

    @modlogs_main.command(name="disable", aliases=['remove'])
    async def modlogs_disable(self, ctx: MyContext, logs: commands.Greedy[serverlog]):
        """Disable one or more logs in the current channel"""
        logs: list[str]
        if len(logs) == 0:
            raise commands.BadArgument('Invalid server log type')
        if 'all' in logs:
            logs = list(self.available_logs)
        actually_removed: list[str] = []
        for log in logs:
            if await self.db_remove(ctx.guild.id, ctx.channel.id, log):
                actually_removed.append(log)
        if actually_removed:
            msg = await self.bot._(ctx.guild.id, "serverlogs.disabled", kind=', '.join(actually_removed))
        else:
            msg = await self.bot._(ctx.guild.id, "serverlogs.none-removed")
        await ctx.send(msg)


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
            if new_content is None and msg.data.get('flags', 0) & 32:
                return
            emb = discord.Embed(
                description=f"**[Message]({link}) updated in <#{msg.channel_id}>**",
                colour=discord.Color.light_gray())
            if old_content:
                emb.add_field(name="Old content", value=old_content, inline=False)
            if new_content:
                emb.add_field(name="New content", value=new_content, inline=False)
            if author:
                emb.set_author(name=str(author), icon_url=author.display_avatar)
                emb.add_field(name="Message Author", value=f"{author} ({author.id})")
            await self.validate_logs(guild, channel_ids, emb)

    @commands.Cog.listener()
    async def on_message_delete(self, msg: discord.Message):
        """Triggered when a message is deleted
        Corresponding log: message_delete"""
        if not msg.guild or msg.author == self.bot.user:
            return
        if channel_ids := await self.is_log_enabled(msg.guild.id, "message_delete"):
            emb = discord.Embed(
                description=f"**Message deleted in <#{msg.channel.id}>**\n{msg.content}",
                colour=discord.Color.red()
            )
            emb.set_author(name=str(msg.author), icon_url=msg.author.display_avatar)
            emb.add_field(name="Created at", value=f"<t:{msg.created_at.timestamp():.0f}>")
            emb.add_field(name="Message Author", value=f"{msg.author} ({msg.author.id})")
            await self.validate_logs(msg.guild, channel_ids, emb)

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
            await self.validate_logs(guild, channel_ids, emb)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Triggered when a member is updated
        Corresponding logs: member_roles, member_nick, member_avatar"""
        # member roles
        if before.roles != after.roles and (channel_ids := await self.is_log_enabled(before.guild.id, "member_roles")):
            added_roles = [role for role in after.roles if role not in before.roles]
            removed_roles = [role for role in before.roles if role not in after.roles]
            emb = discord.Embed(
                description=f"**Member {before.mention} updated**",
                color=discord.Color.blurple()
            )
            if removed_roles:
                emb.add_field(name="Roles revoked", value=' '.join(r.mention for r in removed_roles), inline=False)
            if added_roles:
                emb.add_field(name="Roles granted", value=' '.join(r.mention for r in added_roles), inline=False)
            emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
            # if we have access to audit logs, just wait a bit to make sure the ban is logged
            if before.guild.me.guild_permissions.view_audit_log:
                now = self.bot.utcnow()
                await asyncio.sleep(self.auditlogs_timeout)
                async for entry in before.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update,
                                                           oldest_first=False):
                    if entry.target.id == before.id and (entry.created_at - now).total_seconds() < 5:
                        emb.add_field(name="Roles edited by", value=f"**{entry.user.mention}** ({entry.user.id})")
                        break
            await self.validate_logs(after.guild, channel_ids, emb)
        # member nick
        if before.nick != after.nick and (channel_ids := await self.is_log_enabled(before.guild.id, "member_nick")):
            emb = discord.Embed(
                description=f"**Member {before.mention} ({before.id}) updated**",
                color=discord.Color.blurple()
            )
            before_txt = "None" if before.nick is None else discord.utils.escape_markdown(before.nick)
            after_txt = "None" if after.nick is None else discord.utils.escape_markdown(after.nick)
            emb.add_field(name="Nickname edited", value=f"{before_txt} -> {after_txt}")
            emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
            await self.validate_logs(after.guild, channel_ids, emb)
        # member avatar
        if before.guild_avatar != after.guild_avatar and (
                channel_ids := await self.is_log_enabled(before.guild.id, "member_avatar")
        ):
            emb = discord.Embed(
                description=f"**Member {before.mention} ({before.id}) updated**",
                color=discord.Color.blurple()
            )
            before_txt = "None" if before.guild_avatar is None else f"[Before]({before.guild_avatar})"
            after_txt = "None" if after.guild_avatar is None else f"[After]{after.guild_avatar}"
            emb.add_field(name="Server avatar edited", value=f"{before_txt} -> {after_txt}")
            emb.set_author(name=str(after), icon_url=after.avatar or after.default_avatar)
            await self.validate_logs(after.guild, channel_ids, emb)

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
            await self.validate_logs(member.guild, channel_ids, emb)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Triggered when a member leaves a guild
        Corresponding log: member_leave"""
        if channel_ids := await self.is_log_enabled(member.guild.id, "member_remove"):
            emb = discord.Embed(
                description=f"**{member.mention} ({member.id}) left your server**",
                colour=discord.Color.orange()
            )
            emb.set_author(name=str(member), icon_url=member.display_avatar)
            emb.add_field(name="Account created at", value=f"<t:{member.created_at.timestamp():.0f}>", inline=False)
            if member.joined_at:
                emb.add_field(name="Joined your server at",
                              value=f"<t:{member.joined_at.timestamp():.0f}> (<t:{member.joined_at.timestamp():.0f}:R>)",
                              inline=False)
            if specs := await self.get_member_specs(member):
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            emb.add_field(name=f"Roles ({len(member.roles)})", value=" ".join(r.mention for r in member.roles[::-1][:20]))
            await self.validate_logs(member.guild, channel_ids, emb)

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
            # if we have access to audit logs, just wait a bit to make sure the ban is logged
            if guild.me.guild_permissions.view_audit_log:
                now = self.bot.utcnow()
                await asyncio.sleep(self.auditlogs_timeout)
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban, oldest_first=False):
                    if entry.target.id == user.id and (entry.created_at - now).total_seconds() < 5:
                        emb.add_field(name="Banned by", value=f"**{entry.user.mention}** ({entry.user.id})")
                        emb.add_field(name="With reason", value=entry.reason or "No reason specified")
                        break
            await self.validate_logs(guild, channel_ids, emb)

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
            # if we have access to audit logs, just wait a bit to make sure the unban is logged
            if guild.me.guild_permissions.view_audit_log:
                now = self.bot.utcnow()
                await asyncio.sleep(self.auditlogs_timeout)
                async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.unban, oldest_first=False):
                    if entry.target.id == user.id and (entry.created_at - now).total_seconds() < 5:
                        emb.add_field(name="Unbanned by", value=f"**{entry.user.mention}** ({entry.user.id})")
                        emb.add_field(name="With reason", value=entry.reason or "No reason specified")
                        break
            await self.validate_logs(guild, channel_ids, emb)


    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Triggered when a role is created in a guild
        Corresponding log: role_creation"""
        if channel_ids := await self.is_log_enabled(role.guild.id, "role_creation"):
            emb = discord.Embed(
                description="**New role created**",
                colour=discord.Color.green()
            )
            emb.add_field(name="Name", value=role.name, inline=False)
            emb.add_field(name="Color", value=str(role.color))
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
            if specs:
                emb.add_field(name="Specificities", value=", ".join(specs), inline=False)
            await self.validate_logs(role.guild, channel_ids, emb)

    @commands.Cog.listener()
    async def on_antiscam_warn(self, message: discord.Message, prediction: PredictionResult):
        """Triggered when the antiscam system find a potentially dangerous message
        Corresponding log: antiscam"""
        if channel_ids := await self.is_log_enabled(message.guild.id, "antiscam"):
            emb = discord.Embed(
                description=f"**Potentially dangerous [message]({message.jump_url})**",
                colour=discord.Color.orange()
            )
            # probabilities
            categories: dict = self.bot.get_cog("AntiScam").agent.categories
            emb.add_field(name="AI detection result", value=prediction.to_string(categories), inline=False)
            # message content
            content = message.content if len(message.content) < 1020 else message.content[:1020]+'…'
            emb.add_field(name="Message content", value=content)
            # author
            emb.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar)
            await self.validate_logs(message.guild, channel_ids, emb)

    @commands.Cog.listener()
    async def on_antiscam_delete(self, message: discord.Message, prediction: PredictionResult):
        """Triggered when the antiscam system delete a dangerous message
        Corresponding log: antiscam"""
        if channel_ids := await self.is_log_enabled(message.guild.id, "antiscam"):
            emb = discord.Embed(
                description=f"**Dangerous [message]({message.jump_url}) deleted**",
                colour=discord.Color.red()
            )
            # probabilities
            categories: dict = self.bot.get_cog("AntiScam").agent.categories
            emb.add_field(name="AI detection result", value=prediction.to_string(categories), inline=False)
            # message content
            content = message.content if len(message.content) < 1020 else message.content[:1020]+'…'
            emb.add_field(name="Message content", value=content)
            # author
            emb.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.display_avatar)
            await self.validate_logs(message.guild, channel_ids, emb)

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
            await self.validate_logs(member.guild, channel_ids, emb)

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
            await self.validate_logs(member.guild, channel_ids, emb)


def setup(bot):
    bot.add_cog(ServerLogs(bot))
