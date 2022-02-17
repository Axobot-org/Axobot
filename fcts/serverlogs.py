from typing import Optional
import discord
from cachingutils import LRUCache
from discord.ext import commands
from libs.classes import MyContext, Zbot

from fcts.args import serverlog


class ServerLogs(commands.Cog):
    """Handle any kind of server log"""

    available_logs = {
        "member_roles",
        "member_nick",
        "member_avatar",
        "message_update",
        "message_delete",
        "role",
        "emoji"
    }

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "serverlogs"
        self.cache: LRUCache[int, dict[int, list[str]]] = LRUCache(max_size=10000, timeout=3600*4)


    async def is_log_enabled(self, guild: int, log: str) -> Optional[list[int]]:
        "Check if a log kind is enabled for a guild, and return the corresponding logs channel ID"
        guild_logs = await self.db_get_from_guild(guild)
        res = list()
        for channel, event in guild_logs.items():
            if log in event:
                res.append(channel)
        return res

    async def send_logs(self, guild: discord.Guild, channel_ids: list[int], embed: discord.Embed):
        "Send a log embed to the corresponding modlogs channels"
        for channel_id in channel_ids:
            if channel := guild.get_channel(channel_id):
                perms = channel.permissions_for(guild.me)
                if perms.send_messages and perms.embed_links:
                    await channel.send(embed=embed)

    async def db_get_from_channel(self, guild: int, channel: int) -> list[str]:
        "Get enabled logs for a channel"
        if cached := self.cache.get(guild) and channel in cached:
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

    async def db_add(self, guild: int, channel: int, kind: str):
        "Add logs to a channel"
        query = "INSERT INTO serverlogs (guild, channel, kind) VALUES (%(g)s, %(c)s, %(k)s) ON DUPLICATE KEY UPDATE guild=%(g)s"
        async with self.bot.db_query(query, {'g': guild, 'c': channel, 'k': kind}):
            if guild in self.cache:
                if channel in self.cache[guild]:
                    self.cache[guild][channel].append(kind)
                else:
                    self.cache[guild] = {channel: [kind]}

    async def db_remove(self, guild: int, channel: int, kind: str):
        "Remove logs from a channel"
        query = "DELETE FROM serverlogs WHERE guild = %s AND channel = %s AND kind = %s"
        async with self.bot.db_query(query, (guild, channel, kind)):
            if guild in self.cache and channel in self.cache[guild]:
                self.cache[guild][channel] = [x for x in self.cache[guild][channel] if x != kind]


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
            logs = await self.db_get_from_channel(ctx.guild.id, ctx.channel.id)
        else:
            logs = self.available_logs
        if logs:
            await ctx.send('\n'.join('- '+l for l in sorted(logs)))
        else:
            await ctx.send("NO LOG TO SHOW") # TODO: translation

    @modlogs_main.command(name="enable", aliases=['add'])
    async def modlogs_enable(self, ctx: MyContext, logs: commands.Greedy[serverlog]):
        """Enable one or more logs in the current channel"""
        logs: list[str]
        if len(logs) == 0:
            raise commands.BadArgument('Invalid server log type')
        for log in logs:
            await self.db_add(ctx.guild.id, ctx.channel.id, log)
        await ctx.send("HEY "+' '.join(logs)) # TODO: translation

    @modlogs_main.command(name="disable", aliases=['remove'])
    async def modlogs_disable(self, ctx: MyContext, logs: commands.Greedy[serverlog]):
        """Disable one or more logs in the current channel"""
        logs: list[str]
        if len(logs) == 0:
            raise commands.BadArgument('Invalid server log type')
        for log in logs:
            await self.db_remove(ctx.guild.id, ctx.channel.id, log)
        await ctx.send("BYE "+' '.join(logs)) # TODO: translation


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
            if msg.cached_message:
                if msg.cached_message.author.bot:
                    return
                old_content = msg.cached_message.content
                author = msg.cached_message.author
                guild = msg.cached_message.guild
            else:
                if 'author' in msg.data:
                    author = self.bot.get_user(msg.data.get('author'))
                guild = self.bot.get_guild(msg.guild_id)
            new_content = msg.data.get('content')
            emb = discord.Embed(description=f"**Message updated in <#{msg.channel_id}>**", colour=discord.Color.light_gray())
            if old_content:
                emb.add_field(name="Old content", value=old_content, inline=False)
            if new_content:
                emb.add_field(name="New content", value=new_content, inline=False)
            if author:
                emb.set_author(name=str(author), icon_url=author.display_avatar)
                emb.add_field(name="Author", value=f"{author} ({author.id})")
            await self.send_logs(guild, channel_ids, emb)


def setup(bot):
    bot.add_cog(ServerLogs(bot))
