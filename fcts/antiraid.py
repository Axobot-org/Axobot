from collections import defaultdict
from datetime import timedelta
from typing import Optional

import discord
from cachetools import TTLCache
from discord.ext import commands, tasks

from libs.bot_classes import Axobot
from libs.serverconfig.options_list import options


class AntiRaid(commands.Cog):
    "Handle raid protection in guilds"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "antiraid"
        # Cache of raider status for (guild_id, user_id) - True if raider detected
        self.check_cache = TTLCache[tuple[int, int], bool](maxsize=10_000, ttl=60)
        # Cache of mentions sent by users - count of recent mentions, decreased every minute
        self.mentions_score: defaultdict[int, int] = defaultdict(int)

    async def cog_load(self):
         # pylint: disable=no-member
        self.decrease_mentions_count.start()

    async def cog_unload(self):
         # pylint: disable=no-member
        self.decrease_mentions_count.cancel()

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        "Check if a new member is a potential raider, and takes actions"
        if self.bot.database_online and self.check_cache.get((member.guild.id, member.id), True):
            is_raider = await self.raid_check(member)
            self.check_cache[(member.guild.id, member.id)] = is_raider

    async def is_raider(self, member: discord.Member):
        "Check if a member is a potential raider"
        return self.check_cache.get((member.guild.id, member.id), False)


    async def _get_raid_level(self, guild: discord.Guild) -> int:
        "Get the raid protection level of a guild, between 0 and 5"
        level_name: str = await self.bot.get_config(guild.id, "anti_raid")
        return options["anti_raid"]["values"].index(level_name)

    async def raid_check(self, member: discord.Member):
        """Check if a member should trigger the raid protection, and if so, kick or ban them

        Returns True if the member was kicked or banned, False otherwise"""
        # if guild is unavailable, or Axobot left the guild, or member is a bot
        if member.guild is None or member.guild.me is None or member.bot:
            return False
        level = await self._get_raid_level(member.guild)
        # if antiraid is disabled or bot can't kick
        if level == 0 or not member.guild.me.guild_permissions.kick_members:
            return False
        can_ban = member.guild.get_member(self.bot.user.id).guild_permissions.ban_members
        account_created_since = (self.bot.utcnow() - member.created_at).total_seconds()
        # Level 4
        if level >= 4:
            if account_created_since <= 86400: # kick accounts created less than 1d before
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 86400})
                    return True
            if account_created_since <= 3600 and can_ban: # ban (2w) members created less than 1h before
                duration = timedelta(days=14)
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), duration):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600,
                        "duration": duration.total_seconds()
                    })
                    return True
            elif account_created_since <= 3600*3 and can_ban: # ban (1w) members created less than 3h before
                duration = timedelta(days=7)
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), duration):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600*3,
                        "duration": duration.total_seconds()
                    })
                    return True
        # Level 3 or more
        if level >= 3 and can_ban:
            # ban (1w) members with invitations in their nickname
            if self.bot.get_cog('Utilities').sync_check_discord_invite(member.display_name) is not None:
                duration = timedelta(days=7)
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.invite"), duration):
                    self.bot.dispatch("antiraid_ban", member, {
                        "discord_invite": True,
                        "duration": duration.total_seconds()
                    })
                    return True
            if account_created_since <= 3600*1: # ban (1w) accounts created less than 1h before
                duration = timedelta(days=7)
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), duration):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600,
                        "duration": duration.total_seconds()
                    })
                    return True
            if account_created_since <= 3600*12: # kick accounts created less than 45min before
                if await self.kick(member, await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 3600*12})
                    return True
        # Level 2 or more
        if level >= 2: # kick accounts created less than 15min before
            if account_created_since <= 3600*2:
                if await self.kick(member, await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 3600*2})
                    return True
        # Level 1 or more
        if level >= 1: # kick members with invitations in their nickname
            if self.bot.get_cog('Utilities').sync_check_discord_invite(member.display_name) is not None:
                if await self.kick(member, await self.bot._(member.guild.id,"logs.reason.invite")):
                    self.bot.dispatch("antiraid_kick", member, {"discord_invite": True})
                    return True
        # Nothing got triggered
        return False

    async def kick(self, member: discord.Member, reason: str):
        "Try to kick a member from a guild, by checking every needed permission and requirements"
        # if user is too high
        if member.roles[-1].position >= member.guild.me.roles[-1].position:
            return False
        # if bot can't kick
        if not member.guild.me.guild_permissions.kick_members:
            return False
        # try to send a DM but don't mind if we can't
        try:
            await member.send(await self.bot._(member, "moderation.raid-kicked", guild=member.guild.name))
        except discord.HTTPException:
            pass
        try:
            await member.guild.kick(member, reason=reason)
        except discord.HTTPException:
            return False
        return True

    async def ban(self, member: discord.Member, reason: str, duration: Optional[timedelta] = None):
        "Try to ban a member from a guild, by checking every needed permission and requirements"
        # if user is too high
        if member.roles[-1].position >= member.guild.me.roles[-1].position:
            return False
        # if bot doesn't have the ban perm
        if not member.guild.me.guild_permissions.ban_members:
            return False
        # try to send a DM but don't mind if we can't
        try:
            await member.send(await self.bot._(member, "moderation.raid-banned", guild=member.guild.name))
        except discord.HTTPException:
            pass
        try:
            await member.ban(reason=reason)
        except discord.HTTPException:
            return False
        if duration:
            await self.bot.task_handler.add_task('ban', duration.total_seconds(), member.id, member.guild.id)
        return True

    async def timeout(self, member: discord.Member, reason: str, duration: timedelta):
        "Try to time-out a member from a guild, by checking every needed permission and requirements"
        # if user is too high
        if member.roles[-1].position >= member.guild.me.roles[-1].position:
            return False
        # if bot doesn't have the ban perm
        if not member.guild.me.guild_permissions.moderate_members:
            return False
        try:
            await member.timeout(duration, reason=reason)
        except discord.HTTPException:
            return False
        return True


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        "Check mentions count when a message is sent"
        # if the message is not in a guild or the bot can't see the guild
        if not isinstance(message.author, discord.Member) or message.guild.me is None:
            return
        # if the author is a bot or has permission to moderate memebrs
        if message.author.bot or message.author.guild_permissions.moderate_members:
            return
        # if the antiraid is disabled
        if await self._get_raid_level(message.guild) == 0:
            return
        raw_mentions = [mention for mention in message.raw_mentions if mention != message.author.id]
        if count := len(raw_mentions):
            # add users mentions count to the user score
            self.mentions_score[message.author.id] += count
        # if score is higher than 0, apply sanctions
        if self.mentions_score[message.author.id] > 0:
            await self.check_mentions_score(message.author)

    async def check_mentions_score(self, member: discord.Member):
        "Check if a member has a mentions score higher than the treshold set by the antiraid config, and take actions"
        score = self.mentions_score[member.id]
        if score == 0:
            return
        level = await self._get_raid_level(member.guild)
        # if antiraid is disabled,  or bot can't moderate members
        if level == 0 or not member.guild.me.guild_permissions.moderate_members:
            return False
        # Level 4
        if level >= 4:
            if score >= 20: # ban (2w) members with more than 20 mentions
                duration = timedelta(weeks=2)
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.mentions"), duration=duration):
                    self.bot.dispatch("antiraid_ban", member, {
                        "mentions_treshold": 20, "duration": duration.total_seconds()
                    })
                    return True
            if score >= 15: # kick members with more than 15 mentions
                if await self.kick(member, await self.bot._(member.guild.id,"logs.reason.mentions")):
                    self.bot.dispatch("antiraid_kick", member, {
                        "mentions_treshold": 15
                    })
                    return True
            if score >= 10: # timeout (1h) members with more than 10 mentions
                duration = timedelta(hours=1)
                if await self.timeout(member, await self.bot._(member.guild.id,"logs.reason.mentions"), duration=duration):
                    self.bot.dispatch("antiraid_timeout", member, {
                        "mentions_treshold": 10, "duration": duration.total_seconds()
                    })
                    return True
        # Level 3 or more
        if level >= 3:
            if score >= 20: # kick members with more than 20 mentions
                if await self.kick(member, await self.bot._(member.guild.id,"logs.reason.mentions")):
                    self.bot.dispatch("antiraid_kick", member, {
                        "mentions_treshold": 20
                    })
                    return True
            if score >= 10: # timeout (30min) members with more than 10 mentions
                duration = timedelta(minutes=30)
                if await self.timeout(member, await self.bot._(member.guild.id,"logs.reason.mentions"), duration=duration):
                    self.bot.dispatch("antiraid_timeout", member, {
                        "mentions_treshold": 10, "duration": duration.total_seconds()
                    })
                    return True
        # Level 2 or more
        if level >= 2:
            if score >= 20: # timeout (30min) members with more than 20 mentions
                duration = timedelta(minutes=30)
                if await self.timeout(member, await self.bot._(member.guild.id,"logs.reason.mentions"), duration=duration):
                    self.bot.dispatch("antiraid_timeout", member, {
                        "mentions_treshold": 20, "duration": duration.total_seconds()
                    })
                    return True
            if score >= 10: # timeout (15min) members with more than 10 mentions
                duration = timedelta(minutes=15)
                if await self.timeout(member, await self.bot._(member.guild.id,"logs.reason.mentions"), duration=duration):
                    self.bot.dispatch("antiraid_timeout", member, {
                        "mentions_treshold": 10, "duration": duration.total_seconds()
                    })
                    return True
        # Level 1 or more
        if level >= 1:
            if score >= 30: # timeout (20min) members with more than 30 mentions
                duration = timedelta(minutes=20)
                if await self.timeout(member, await self.bot._(member.guild.id,"logs.reason.mentions"), duration=duration):
                    self.bot.dispatch("antiraid_timeout", member, {
                        "mentions_treshold": 30, "duration": duration.total_seconds()
                    })
                    return True
        return False


    @tasks.loop(seconds=30)
    async def decrease_mentions_count(self):
        "Decrease mentions count by 2every 30 seconds"
        to_remove: list[int] = []
        for member_id in self.mentions_score:
            self.mentions_score[member_id] -= 2
            if self.mentions_score[member_id] <= 0:
                to_remove.append(member_id)
        for member_id in to_remove:
            del self.mentions_score[member_id]

    @decrease_mentions_count.error
    async def on_decrease_mentions_count_error(self, error: Exception):
        self.bot.dispatch("error", error, "When calling `decrease_mentions_count` (<@279568324260528128>)")


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
