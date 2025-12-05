import re
from collections import defaultdict
from datetime import timedelta
from typing import Literal

import discord
from cachetools import TTLCache
from discord.ext import commands, tasks

from core.bot_classes import DISCORD_INVITE_REGEX, Axobot
from core.text_cleanup import sync_check_discord_invite

AutoActionType = Literal["timeout", "kick", "ban"]
CheckType = Literal["mentions", "invites", "attachments", "account_creation"]


RE_ATTACHMENT_URL = re.compile(r"https?://\S+\.(?:png|jpg|jpeg|gif|webp|mp4|mov|wmv|flv|avi|mkv)")
def _count_attachments(message: discord.Message) -> int:
    "Count the number of attachments in a message"
    files_count = len(message.attachments)
    if message.content:
        files_count += len(re.findall(RE_ATTACHMENT_URL, message.content))
    return files_count


class AntiRaid(commands.Cog):
    "Handle raid protection in guilds"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "antiraid"
        # Cache of raider status for (guild_id, user_id) - True if raider detected
        self.check_cache = TTLCache[tuple[int, int], bool](maxsize=10_000, ttl=60)
        # Cache of mentions sent by users - decreased every minute
        self.mentions_score: defaultdict[int, int] = defaultdict(int)
        # Cache of discord invites sent by users - decreased every minute
        self.invites_score: defaultdict[int, int] = defaultdict(int)
        # Cache of attachments sent by users - decreased every minute
        self.attachments_score: defaultdict[int, int] = defaultdict(int)

    async def cog_load(self):
        # pylint: disable=no-member
        self.decrease_users_scores.start()

    async def cog_unload(self):
         # pylint: disable=no-member
        self.decrease_users_scores.cancel()

    @commands.Cog.listener(name="on_message")
    async def on_message_anticaps(self, msg: discord.Message):
        "Check for capslock messages"
        if (
            msg.guild is None
            or msg.author.bot
            or not isinstance(msg.author, discord.Member)
            or not self.bot.database_online
            or len(msg.content) < 8
        ):
            return
        if msg.channel.permissions_for(msg.author).administrator: # type: ignore
            return
        if not await self.bot.get_config(msg.guild, "anti_caps_lock"):
            return
        clean_content = msg.content
        for rgx_match in (r'\|', r'\*', r'_', r"<a?:\w+:\d+>", r"<(#|@&?!?)\d+>", r"https?://\w+\.\S+"):
            clean_content = re.sub(rgx_match, '', clean_content)
        clean_content = clean_content.replace(' ', '')
        if len(clean_content) < 8:
            return
        if sum(1 for c in clean_content if c.isupper())/len(clean_content) > 0.8:
            try:
                await msg.channel.send(
                    await self.bot._(msg.guild, "moderation.caps-lock", user=msg.author.mention),
                    delete_after=4.0
                )
            except discord.HTTPException:
                pass

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        "Check if a new member is a potential raider, and takes actions"
        if self.bot.database_online and self.check_cache.get((member.guild.id, member.id), True):
            is_raider = await self.on_join_raid_check(member)
            self.check_cache[(member.guild.id, member.id)] = is_raider

    async def is_raider(self, member: discord.Member):
        "Check if a member is a potential raider"
        return self.check_cache.get((member.guild.id, member.id), False)


    async def _get_raid_level(self, guild: discord.Guild) -> int:
        "Get the raid protection level of a guild, between 0 and 5"
        level_name: str = await self.bot.get_config(guild.id, "anti_raid") # type: ignore
        return (await self.bot.get_options_list())["anti_raid"]["values"].index(level_name) # type: ignore

    async def on_join_raid_check(self, member: discord.Member):
        """Check if a member should trigger the raid protection, and if so, kick or ban them

        Returns True if the member was kicked or banned, False otherwise"""
        # if guild is unavailable, or Axobot left the guild, or member is a bot
        if member.bot:
            return False
        level = await self._get_raid_level(member.guild)
        # if antiraid is disabled or bot can't kick
        if level == 0 or not member.guild.me.guild_permissions.kick_members:
            return False
        can_ban = member.guild.me.guild_permissions.ban_members
        account_created_since = int((self.bot.utcnow() - member.created_at).total_seconds())
        # Level 4
        if level >= 4:
            # kick accounts created less than 1d before
            if await self._check_max_score(member, account_created_since, 86400, "kick", "account_creation"):
                return True
            # ban (2w) members created less than 1h before
            if can_ban and await self._check_max_score(member, account_created_since, 3600, "ban", "account_creation",
                                                   timedelta(weeks=2)):
                return True
            # ban (1w) members created less than 3h before
            if can_ban and await self._check_max_score(member, account_created_since, 3600*3, "ban", "account_creation",
                                                   timedelta(weeks=1)):
                return True
        # Level 3 or more
        if level >= 3 and can_ban:
            # ban (1w) members with invitations in their nickname
            if sync_check_discord_invite(member.display_name) is not None:
                duration = timedelta(days=7)
                if await self._ban(member, await self.bot._(member.guild.id,"logs.reason.invite"), duration):
                    self.bot.dispatch("antiraid_ban", member, {
                        "discord_invite": True,
                        "duration": duration.total_seconds()
                    })
                    return True
            # ban (1w) accounts created less than 1h before
            if can_ban and await self._check_max_score(member, account_created_since, 3600, "ban", "account_creation",
                                                    timedelta(weeks=1)):
                return True
            # kick accounts created less than 12h before
            if await self._check_max_score(member, account_created_since, 3600*12, "kick", "account_creation"):
                return True
        # Level 2 or more
        if level >= 2:
            # kick accounts created less than 2h before
            if await self._check_max_score(member, account_created_since, 3600*2, "kick", "account_creation"):
                return True
        # Level 1 or more
        if level >= 1: # kick members with invitations in their nickname
            if sync_check_discord_invite(member.display_name) is not None:
                if await self._kick(member, await self.bot._(member.guild.id,"logs.reason.invite")):
                    self.bot.dispatch("antiraid_kick", member, {"discord_invite": True})
                    return True
        # Nothing got triggered
        return False

    async def _kick(self, member: discord.Member, reason: str):
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

    async def _ban(self, member: discord.Member, reason: str, duration: timedelta | None = None):
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
            await self.bot.task_handler.add_task("ban", int(duration.total_seconds()), member.id, member.guild.id)
        return True

    async def _timeout(self, member: discord.Member, reason: str, duration: timedelta):
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

    async def _check_min_score(self, member: discord.Member, score: int, treshold: int, action: AutoActionType,
                           check_id: CheckType, duration: timedelta | None = None):
        "Check if a score is higher than a treshold, and take actions"
        if score < treshold:
            return False
        return await self._check_score_action(member, treshold, action, check_id, duration)

    async def _check_max_score(self, member: discord.Member, score: int, treshold: int, action: AutoActionType,
                            check_id: CheckType, duration: timedelta | None = None):
        "Check if a score is lower than a treshold, and take actions"
        if score > treshold:
            return False
        return await self._check_score_action(member, treshold, action, check_id, duration)

    async def _check_score_action(self, member: discord.Member, treshold: int, action: AutoActionType,
                           check_id: CheckType, duration: timedelta | None = None):
        translation_key = f"logs.reason.{check_id}"
        if action == "timeout":
            if duration is None:
                raise ValueError("Duration must be provided for timeout action")
            await self._timeout(member, await self.bot._(member.guild.id, translation_key), duration)
        if action == "kick":
            await self._kick(member, await self.bot._(member.guild.id, translation_key))
        if action == "ban":
            await self._ban(member, await self.bot._(member.guild.id, translation_key), duration)
        dispatch_data = {
            f"{check_id}_treshold": treshold
        }
        if duration:
            dispatch_data["duration"] = int(duration.total_seconds())
        self.bot.dispatch(f"antiraid_{action}", member, dispatch_data)
        return True


    async def _should_ignore_member(self, member: discord.Member):
        "Check whether this member should be verified (False) or is immune (True)"
        if member.bot or member.guild_permissions.administrator:
            return True
        immune_roles: list[discord.Role] | None = await self.bot.get_config(
            member.guild.id, "anti_raid_ignored_roles") # type: ignore
        if not immune_roles:
            return member.guild_permissions.moderate_members
        return any(
            role in member.roles
            for role in immune_roles
        )

    @commands.Cog.listener("on_message")
    async def on_message_antiraid(self, message: discord.Message):
        "Check mentions/invites count when a message is sent"
        # if the message is not in a guild or the bot can't see the guild
        if message.guild is None or not isinstance(message.author, discord.Member) or message.guild.me is None: # type: ignore
            return
        # if the author is a bot or should be immune
        if await self._should_ignore_member(message.author):
            return
        # if the antiraid is disabled
        if await self._get_raid_level(message.guild) == 0:
            return
        # 1. Check mentions
        raw_mentions = [mention for mention in message.raw_mentions if mention != message.author.id]
        if mentions_count := len(raw_mentions):
            # add users mentions count to the user score
            self.mentions_score[message.author.id] += mentions_count
        # if mentions score is higher than 0, apply sanctions
        if mentions_count != 0 and self.mentions_score[message.author.id] > 0:
            await self.check_mentions_score(message.author)
        # 2. Check invites
        if invites_count := len(DISCORD_INVITE_REGEX.findall(message.content)):
            self.invites_score[message.author.id] += invites_count
        # if invites score is higher than 0, apply sanctions
        if invites_count != 0 and self.invites_score[message.author.id] > 0:
            await self.check_invites_score(message.author)
        # 3. Check attachments
        if attachments_count := _count_attachments(message):
            self.attachments_score[message.author.id] += attachments_count
        # if attachments score is higher than 0, apply sanctions
        if attachments_count != 0 and self.attachments_score[message.author.id] > 0:
            await self.check_attachments_score(message.author)

    async def check_mentions_score(self, member: discord.Member):
        "Check if a member has a mentions score higher than the treshold set by the antiraid config, and take actions"
        score = self.mentions_score[member.id]
        if score == 0:
            return
        level = await self._get_raid_level(member.guild)
        # if antiraid is disabled, or bot can't moderate members
        if level == 0 or not member.guild.me.guild_permissions.moderate_members:
            return False
        # Level 4
        if level >= 4:
            # ban (2w) members with more than 20 mentions
            if await self._check_min_score(member, score, 20, "ban", "mentions", timedelta(weeks=2)):
                return True
            # kick members with more than 12 mentions
            if await self._check_min_score(member, score, 12, "kick", "mentions"):
                return True
            # timeout (1h) members with more than 5 mentions
            if await self._check_min_score(member, score, 5, "timeout", "mentions", timedelta(hours=1)):
                return True
        # Level 3 or more
        if level >= 3:
            # kick members with more than 20 mentions
            if await self._check_min_score(member, score, 20, "kick", "mentions"):
                return True
            # timeout (30min) members with more than 8 mentions
            if await self._check_min_score(member, score, 8, "timeout", "mentions", timedelta(minutes=30)):
                return True
        # Level 2 or more
        if level >= 2:
            # timeout (30min) members with more than 20 mentions
            if await self._check_min_score(member, score, 20, "timeout", "mentions", timedelta(minutes=30)):
                return True
            # timeout (15min) members with more than 10 mentions
            if await self._check_min_score(member, score, 10, "timeout", "mentions", timedelta(minutes=15)):
                return True
        # Level 1 or more
        if level >= 1:
            # timeout (30min) members with more than 30 mentions
            if await self._check_min_score(member, score, 30, "timeout", "mentions", timedelta(minutes=30)):
                return True
        return False


    async def check_invites_score(self, member: discord.Member):
        "Check if a member has a invites score higher than the treshold set by the antiraid config, and take actions"
        score = self.invites_score[member.id]
        if score == 0:
            return
        level = await self._get_raid_level(member.guild)
        # if antiraid is disabled, or bot can't moderate members
        if level == 0 or not member.guild.me.guild_permissions.moderate_members:
            return False
        # Level 4
        if level >= 4:
            # ban (4w) members with more than 5 invites
            if await self._check_min_score(member, score, 5, "ban", "invites", timedelta(weeks=4)):
                return True
            # kick members with more than 3 invites
            if await self._check_min_score(member, score, 3, "kick", "invites"):
                return True
            # timeout (3h) members with more than 2 invites
            if await self._check_min_score(member, score, 2, "timeout", "invites", timedelta(hours=3)):
                return True
        # Level 3 or more
        if level >= 3:
            # kick members with more than 5 invites
            if await self._check_min_score(member, score, 5, "kick", "invites"):
                return True
            # timeout (3h) members with more than 3 invites
            if await self._check_min_score(member, score, 3, "timeout", "invites", timedelta(hours=3)):
                return True
        # Level 2 or more
        if level >= 2:
            # timeout (6h) members with more than 6 invites
            if await self._check_min_score(member, score, 6, "timeout", "invites", timedelta(hours=6)):
                return True
            # timeout (1h) members with more than 3 invites
            if await self._check_min_score(member, score, 3, "timeout", "invites", timedelta(hours=1)):
                return True
        # Level 1 or more
        if level >= 1:
            # timeout (1h) members with more than 5 invites
            if await self._check_min_score(member, score, 5, "timeout", "invites", timedelta(hours=1)):
                return True
        return False

    async def check_attachments_score(self, member: discord.Member):
        "Check if a member has a attachments score higher than the treshold set by the antiraid config, and take actions"
        score = self.attachments_score[member.id]
        if score == 0:
            return
        level = await self._get_raid_level(member.guild)
        # if antiraid is disabled, or bot can't moderate members
        if level == 0 or not member.guild.me.guild_permissions.moderate_members:
            return False
        # Level 4
        if level >= 4:
            # ban (1w) members with more than 8 attachments
            if await self._check_min_score(member, score, 8, "ban", "attachments", timedelta(weeks=1)):
                return True
        # Level 3 or more
        if level >= 3:
            # kick members with more than 8 attachments
            if await self._check_min_score(member, score, 8, "kick", "attachments"):
                return True
        # Level 2 or more
        if level >= 2:
            # timeout (1h) members with more than 8 attachments
            if await self._check_min_score(member, score, 8, "timeout", "attachments", timedelta(hours=1)):
                return True
            # timeout (10min) members with more than 6 attachments
            if await self._check_min_score(member, score, 6, "timeout", "attachments", timedelta(minutes=10)):
                return True
        # Level 1 or more
        if level >= 1:
            # timeout (30min) members with more than 10 attachments
            if await self._check_min_score(member, score, 10, "timeout", "attachments", timedelta(minutes=30)):
                return True

    @tasks.loop(seconds=30)
    async def decrease_users_scores(self):
        """Decrease mentions and invites count every 30 seconds"""
        # Decrease mentions count by 2
        mentions_users_to_remove: list[int] = []
        for member_id in self.mentions_score:
            self.mentions_score[member_id] -= 2
            if self.mentions_score[member_id] <= 0:
                mentions_users_to_remove.append(member_id)
        for member_id in mentions_users_to_remove:
            del self.mentions_score[member_id]
        # Decrease invites count by 1
        invites_users_to_remove: list[int] = []
        for member_id in self.invites_score:
            self.invites_score[member_id] -= 1
            if self.invites_score[member_id] <= 0:
                invites_users_to_remove.append(member_id)
        for member_id in invites_users_to_remove:
            del self.invites_score[member_id]
        # Decrease attachments count by 2
        attachments_users_to_remove: list[int] = []
        for member_id in self.attachments_score:
            self.attachments_score[member_id] -= 2
            if self.attachments_score[member_id] <= 0:
                attachments_users_to_remove.append(member_id)
        for member_id in attachments_users_to_remove:
            del self.attachments_score[member_id]

    @decrease_users_scores.error
    async def on_decrease_mentions_count_error(self, error: BaseException):
        self.bot.dispatch("error", error, "When calling `decrease_mentions_count` (<@279568324260528128>)")


async def setup(bot: Axobot):
    await bot.add_cog(AntiRaid(bot))
