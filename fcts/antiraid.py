import discord
from cachingutils import Cache
from discord.ext import commands

from libs.bot_classes import Axobot
from libs.serverconfig.options_list import options


class AntiRaid(commands.Cog):
    "Handle raid protection in guilds"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "antiraid"
        # Cache of raider status for (guild_id, user_id) - True if raider detected
        self.check_cache = Cache[tuple[int, int], bool](timeout=60)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        "Check if a new member is a potential raider, and takes actions"
        if self.bot.database_online and self.check_cache.get((member.guild.id, member.id), True):
            is_raider = await self.raid_check(member)
            self.check_cache[(member.guild.id, member.id)] = is_raider

    async def is_raider(self, member: discord.Member) -> bool:
        "Check if a member is a potential raider"
        return self.check_cache.get((member.guild.id, member.id), False)


    async def raid_check(self, member: discord.Member):
        """Check if a member should trigger the raid protection, and if so, kick or ban them

        Returns True if the member was kicked or banned, False otherwise"""
        # if guild is unavailable or the bot left the guild
        if member.guild is None or member.guild.me is None:
            return False
        level_name: str = await self.bot.get_config(member.guild.id, "anti_raid")
        # if antiraid is disabled or bot can't kick
        if level_name == "none" or not member.guild.channels[0].permissions_for(member.guild.me).kick_members:
            return False
        level: int = options["anti_raid"]["values"].index(level_name)
        can_ban = member.guild.get_member(self.bot.user.id).guild_permissions.ban_members
        account_created_since = (self.bot.utcnow() - member.created_at).total_seconds()
        # Level 4
        if level >= 4:
            if account_created_since <= 86400: # kick accounts created less than 1d before
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 86400})
                    return True
            if account_created_since <= 3600 and can_ban: # ban (2w) members created less than 1h before
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), 86400*14):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600,
                        "duration": 86400*14
                    })
                    return True
            elif account_created_since <= 3600*3 and can_ban: # ban (1w) members created less than 3h before
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), 86400*7):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600*3,
                        "duration": 86400*7
                    })
                    return True
        # Level 3 or more
        if level >= 3 and can_ban:
            # ban (1w) members with invitations in their nickname
            if self.bot.get_cog('Utilities').sync_check_discord_invite(member.name) is not None:
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.invite"), 86400*7):
                    self.bot.dispatch("antiraid_ban", member, {
                        "discord_invite": True,
                        "duration": 86400*7
                    })
                    return True
            if account_created_since <= 3600*12: # kick accounts created less than 45min before
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 3600*12})
                    return True
        # Level 2 or more
        if level >= 2: # kick accounts created less than 15min before
            if account_created_since <= 3600*2:
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 3600*2})
                    return True
        # Level 1 or more
        if level >= 1: # kick members with invitations in their nickname
            if self.bot.get_cog('Utilities').sync_check_discord_invite(member.name) is not None:
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.invite")):
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
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await member.guild.kick(member, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            return False
        else:
            if mod_cog := self.bot.get_cog("Moderation"):
                await mod_cog.send_modlogs("kick", member, self.bot.user, member.guild, reason=reason)
            return True

    async def ban(self, member: discord.Member, reason: str, duration: int = None):
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
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await member.guild.ban(member, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            return False
        else:
            if duration:
                await self.bot.task_handler.add_task('ban', duration, member.id, member.guild.id)
            if mod_cog := self.bot.get_cog("Moderation"):
                await mod_cog.send_modlogs("ban", member, self.bot.user, member.guild, reason=reason)
            return True


async def setup(bot):
    await bot.add_cog(AntiRaid(bot))
