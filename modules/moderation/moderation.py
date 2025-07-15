import datetime
import importlib
import random
from math import ceil
from typing import Literal, overload

import discord
from discord import app_commands
from discord.ext import commands

from core.arguments import args
from core.bot_classes import Axobot
from core.checks import checks
from core.formatutils import FormatUtils
from core.paginator import Paginator
from core.text_cleanup import sync_check_any_link, sync_check_discord_invite
from core.type_utils import UserOrMember, assert_interaction_channel_is_guild_messageable
from core.views import ConfirmView
from modules.cases.cases import Case

importlib.reload(checks)
importlib.reload(args)

CLEAR_MAX_MESSAGES = 10_000

async def target_is_higher(target: discord.Member, moderator: discord.Member):
    "Check if the target highest role is at the same position or higher than the moderator"
    if target == target.guild.owner:
        return True
    if moderator == target.guild.owner:
        return False
    return target.top_role.position >= moderator.top_role.position

class Moderation(commands.Cog):
    """Here you will find everything you need to moderate your server.
    Please note that most of the commands are reserved for certain members only."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "moderation"

    @app_commands.command(name="slowmode")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_channels=True)
    @app_commands.checks.cooldown(1, 3)
    async def slowmode(self, interaction: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        """Keep your chat cool
Slowmode works up to one message every 6h (21600s)

..Example slowmode 10

..Example slowmode 0

..Doc moderator.html#slowmode"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if not interaction.channel.permissions_for(interaction.guild.me).manage_channels:
            await interaction.response.send_message(await self.bot._(interaction, "moderation.slowmode.no-perm"), ephemeral=True)
            return
        await interaction.response.defer()
        if seconds == 0:
            await interaction.channel.edit(slowmode_delay=0)
            message = await self.bot._(interaction, "moderation.slowmode.disabled")
        elif seconds > 21600:
            message = await self.bot._(interaction, "moderation.slowmode.too-long")
        else:
            await interaction.channel.edit(slowmode_delay=seconds)
            duration = await FormatUtils.time_delta(seconds, lang=await self.bot._(interaction, "_used_locale"))
            message = await self.bot._(
                interaction, "moderation.slowmode.enabled",
                channel=interaction.channel.mention,
                s=duration
            )
        await interaction.followup.send(message)
        self.bot.dispatch("moderation_slowmode", interaction.channel, interaction.user, seconds)


    @app_commands.command(name="clear")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(
        number="The max amount of messages to delete",
        users="list of user IDs or mentions to delete messages from, separated by spaces",
        contains_file="Clear only messages that contains (or does not) files",
        contains_url="Clear only messages that contains (or does not) links",
        contains_invite="Clear only messages that contains (or does not) Discord invites",
        is_pinned="Clear only messages that are (or are not) pinned"
    )
    @app_commands.checks.cooldown(4, 30)
    async def clear(self, interaction: discord.Interaction,
                    number: app_commands.Range[int, 1, CLEAR_MAX_MESSAGES],
                    users: args.GreedyUsersArgument | None = None,
                    contains_file: bool | None = None,
                    contains_url: bool | None = None,
                    contains_invite: bool | None = None,
                    is_pinned: bool | None = None):
        """Keep your chat clean
        <number>: number of messages to check
        [users]: list of user IDs or mentions to delete messages from
        [contains_file]: delete if the message does (or does not) contain any file
        [contains_url]: delete if the message does (or does not) contain any link
        [contains_invite] : delete if the message does (or does not) contain a Discord invite
        [is_pinned]: delete if the message is (or is not) pinned
        By default, the bot will NOT delete pinned messages

..Example clear 120

..Example clear 10 @someone

..Example clear 50 False False True

..Doc moderator.html#clear"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            await interaction.response.send_message(await self.bot._(interaction, "moderation.need-manage-messages"))
            return
        if not interaction.channel.permissions_for(interaction.guild.me).read_message_history:
            await interaction.response.send_message(await self.bot._(interaction, "moderation.need-read-history"))
            return
        if number < 1:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.clear.too-few") + " " + self.bot.emojis_manager.customs["owo"]
            )
            return
        await interaction.response.defer(ephemeral=True)
        if users is None and contains_file is None and contains_url is None and contains_invite is None and is_pinned is None:
            await self._clear_simple(interaction, number)
            return
        user_ids = None if users is None else {u.id for u in users}

        def check(msg: discord.Message):
            # do not delete invocation message
            if msg.interaction_metadata is not None and interaction.id == msg.interaction_metadata.id:
                return False
            if is_pinned is not None and msg.pinned != is_pinned:
                return False
            if is_pinned is None and msg.pinned:
                return False
            if contains_file is not None and bool(msg.attachments) != contains_file:
                return False
            url_match = sync_check_any_link(msg.content)
            if contains_url is not None and (url_match is not None) != contains_url:
                return False
            invite_match = sync_check_discord_invite(msg.content)
            if contains_invite is not None and (invite_match is not None) != contains_invite:
                return False
            if user_ids:
                return msg.author.id in user_ids
            return True

        deleted = await interaction.channel.purge(limit=number, check=check)
        await interaction.followup.send(await self.bot._(interaction, "moderation.clear.done", count=len(deleted)))
        if len(deleted) > 0:
            self.bot.dispatch("moderation_clear", interaction.channel, interaction.user, len(deleted))

    async def _clear_simple(self, interaction: discord.Interaction, number: int):
        def check(msg: discord.Message):
            if msg.pinned or (interaction.message and msg.id == interaction.message.id):
                return False
            if msg.interaction_metadata is None:
                return True
            return interaction.id != msg.interaction_metadata.id

        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        try:
            deleted = await interaction.channel.purge(limit=number, check=check)
            await interaction.followup.send(
                await self.bot._(interaction, "moderation.clear.done", count=len(deleted)),
            )
            self.bot.dispatch("moderation_clear", interaction.channel, interaction.user, len(deleted))
        except discord.errors.NotFound:
            await interaction.followup.send(await self.bot._(interaction, "moderation.clear.not-found"))


    @app_commands.command(name="kick")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.checks.cooldown(5, 20)
    async def kick(self, interaction: discord.Interaction, user: discord.Member, reason: str | None = None):
        """Kick a member from this server

..Example kick @someone Not nice enough to stay here

..Doc moderator.html#kick"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if not interaction.channel.permissions_for(interaction.guild.me).kick_members:
            await interaction.response.send_message(await self.bot._(interaction.guild.id, "moderation.kick.no-perm"))
            return
        await interaction.response.defer(ephemeral=True)

        if user == interaction.guild.me or await target_is_higher(user, interaction.user):
            await interaction.followup.send(await self.bot._(interaction, "moderation.kick.cant-staff"))
            return
        if user.roles[-1].position >= interaction.guild.me.roles[-1].position:
            await interaction.followup.send(await self.bot._(interaction, "moderation.kick.too-high"))
            return
        # send DM
        await self.dm_user(user, "kick", interaction, reason=reason)
        f_reason = reason or "Unspecified"
        try:
            await interaction.guild.kick(user, reason=f_reason[:512] + self.bot.zws)
        except discord.errors.Forbidden:
            await interaction.followup.send(await self.bot._(interaction, "moderation.kick.too-high"))
            return
        case_id = None
        if self.bot.database_online and (cases_cog := self.bot.get_cog("Cases")):
            case = Case(bot=self.bot, guild_id=interaction.guild.id, user_id=user.id, case_type="kick",
                        mod_id=interaction.user.id, reason=f_reason, date=self.bot.utcnow())
            await cases_cog.db_add_case(case)
            case_id = case.id
            await interaction.followup.send(await self.bot._(interaction,"moderation.kick.success"))
        # send in chat
        await self.send_chat_answer("kick", user, interaction, case_id)
        # send in modlogs
        self.bot.dispatch("moderation_kick", interaction.guild, interaction.user, user, case_id, reason)
        await self.bot.get_cog("Events").add_event("kick") # type: ignore


    @app_commands.command(name="warn")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(message="The reason of the warn")
    @app_commands.checks.cooldown(5, 20)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, message: str):
        """Send a warning to a member

..Example warn @someone Please just stop, next one is a mute duh

..Doc moderator.html#warn"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        if user == interaction.guild.me or await target_is_higher(user, interaction.user):
            await interaction.followup.send(await self.bot._(interaction, "moderation.warn.cant-staff"))
            return
        if user.bot and not user.id==423928230840500254:
            await interaction.followup.send(await self.bot._(interaction, "moderation.warn.cant-bot"))
            return
        # send DM
        await self.dm_user(user, "warn", interaction, reason=message)
        case_id = None
        if self.bot.database_online and (cases_cog := self.bot.get_cog("Cases")):
            case = Case(bot=self.bot, guild_id=interaction.guild.id, user_id=user.id, case_type="warn",
                        mod_id=interaction.user.id, reason=message, date=self.bot.utcnow())
            await cases_cog.db_add_case(case)
            case_id = case.id
            await interaction.followup.send(await self.bot._(interaction,"moderation.warn.success"))
        else:
            await interaction.followup.send(await self.bot._(interaction,"moderation.warn.warn-but-db"))
        # send in chat
        await self.send_chat_answer("warn", user, interaction, case_id)
        # send in modlogs
        self.bot.dispatch("moderation_warn", interaction.guild, interaction.user, user, case_id, message)


    async def get_muted_role(self, guild: discord.Guild) -> discord.Role | None:
        "Find the muted role from the guild config option"
        return await self.bot.get_config(guild.id, "muted_role") # pyright: ignore[reportReturnType]

    async def mute_member(self, member: discord.Member, reason: str | None, duration: datetime.timedelta | None=None):
        """Call when someone should be muted in a guild"""
        # add the muted role
        role = await self.get_muted_role(member.guild)
        f_reason = reason if reason is not None else "Unspecified"
        if role is None:
            duration = duration or datetime.timedelta(days=28)
            await member.timeout(duration, reason=f_reason[:512]+self.bot.zws)
        else:
            await member.add_roles(role, reason=f_reason[:512])
        # save in database that the user is muted
        if not self.bot.database_online:
            return
        query = "INSERT IGNORE INTO `mutes` VALUES (%s, %s, CURRENT_TIMESTAMP)"
        async with self.bot.db_main.write(query, (member.id, member.guild.id)):
            pass

    async def check_mute_context(self, interaction: discord.Interaction, role: discord.Role | None, member: discord.Member):
        "Return True if the user can be muted in the given context"
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if await self.is_muted(interaction.guild, member, role):
            await interaction.followup.send(await self.bot._(interaction, "moderation.mute.already-mute"))
            return False
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.followup.send(await self.bot._(interaction, "moderation.mute.cant-mute"))
            return False
        if role is None:
            if not interaction.guild.me.guild_permissions.moderate_members:
                await interaction.followup.send(await self.bot._(interaction, "moderation.mute.cant-timeout"))
                return False
            if member.top_role.position >= interaction.guild.me.roles[-1].position:
                await interaction.followup.send(await self.bot._(interaction, "moderation.mute.too-high"))
                return False
            return True
        if role.position > interaction.guild.me.roles[-1].position:
            await interaction.followup.send(await self.bot._(interaction, "moderation.mute.mute-high"))
            return False
        return True

    @app_commands.command(name="mute")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.rename(duration="time")
    @app_commands.describe(
        duration="The duration of the mute, example 3d 7h 12min",
        reason="The reason of the mute"
    )
    @app_commands.checks.cooldown(5,20)
    async def mute(self, interaction: discord.Interaction, user: discord.Member, duration: args.GreedyDurationArgument,
                   reason: str | None=None):
        """Timeout someone.
You can also mute this member for a defined duration, then use the following format:
`XXm` : XX minutes
`XXh` : XX hours
`XXd` : XX days
`XXw` : XX weeks

..Example mute @someone 1d 3h Reason is becuz he's a bad guy

..Example mute @someone Plz respect me

..Doc articles/mute"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if duration <= 0:
            await interaction.response.send_message(await self.bot._(interaction, "timers.rmd.too-short"), ephemeral=True)
            return
        if duration > 60*60*24*365*3: # max 3 years
            await interaction.response.send_message(await self.bot._(interaction, "timers.rmd.too-long"), ephemeral=True)
            return
        f_duration = await FormatUtils.time_delta(duration, lang=await self.bot._(interaction, "_used_locale"), form="short")
        await interaction.response.defer(ephemeral=True)

        if user == interaction.guild.me or await target_is_higher(user, interaction.user):
            emoji = random.choice([
                ":confused:",
                ":no_mouth:",
                ":thinking:",
                ":upside_down:",
                self.bot.emojis_manager.customs["wat"],
                self.bot.emojis_manager.customs["owo"],
            ])
            await interaction.followup.send((await self.bot._(interaction, "moderation.mute.staff-mute")) + " " + emoji)
            return
        role = await self.get_muted_role(interaction.guild)
        if not await self.check_mute_context(interaction, role, user):
            return
        case_id = None
        if duration:
            await self.bot.task_handler.add_task("mute", duration, user.id, interaction.guild.id)
        if self.bot.database_online and (cases_cog := self.bot.get_cog("Cases")):
            f_reason = reason or "Unspecified"
            case = Case(bot=self.bot, guild_id=interaction.guild.id, user_id=user.id, case_type="tempmute",
                        mod_id=interaction.user.id, reason=f_reason, date=self.bot.utcnow(), duration=duration)
            await cases_cog.db_add_case(case)
            case_id = case.id
            await interaction.followup.send(await self.bot._(interaction,"moderation.mute.mute-success"))
        # actually mute
        await self.mute_member(user, reason, datetime.timedelta(seconds=duration) if duration else None)
        # send log
        self.bot.dispatch("moderation_mute", interaction.guild, interaction.user, user, case_id, reason, duration)
        # send DM
        await self.dm_user(user, "mute", interaction, reason=reason, duration=f_duration)
        # send in chat
        await self.send_chat_answer("mute", user, interaction, case_id)


    async def unmute_member(self, guild: discord.Guild, user: discord.Member, author: discord.Member):
        """Call this to unmute someone"""
        # remove the role
        role = await self.get_muted_role(guild)
        if author == guild.me:
            reason = await self.bot._(guild.id,"logs.reason.autounmute")
        else:
            reason = await self.bot._(guild.id, "logs.reason.unmute", user=author)
        if role is None:
            await user.timeout(None, reason=reason+self.bot.zws)
        elif role in user.roles:
            await user.remove_roles(role, reason=reason)
        # remove the muted record in the database
        if not self.bot.database_online:
            return
        query = "DELETE IGNORE FROM mutes WHERE userid=%s AND guildid=%s"
        async with self.bot.db_main.write(query, (user.id, guild.id)):
            pass

    async def is_muted(self, guild: discord.Guild, member: discord.Member, role: discord.Role | None) -> bool:
        """Check if a user is currently muted"""
        if member.is_timed_out():
            return True
        if not self.bot.database_online:
            if role is None:
                return False
            return role in member.roles
        query = "SELECT COUNT(*) AS count FROM `mutes` WHERE guildid=%s AND userid=%s"
        async with self.bot.db_main.read(query, (guild.id, member.id)) as query_results:
            result: int = query_results[0]["count"]
        return result > 0

    @overload
    async def db_get_muted_list(self, guild_id: int, reasons: Literal[True]) -> dict[int, str]:
        ...

    @overload
    async def db_get_muted_list(self, guild_id: int, reasons: Literal[False]) -> list[int]:
        ...

    async def db_get_muted_list(self, guild_id: int, reasons: bool = False) -> dict[int, str] | list[int]:
        """List muted users for a specific guild
        Set 'reasons' to True if you want the attached reason"""
        if reasons:
            cases_table = "cases_beta" if self.bot.beta else "cases"
            query = f"""SELECT userid, (
                        SELECT reason FROM {cases_table}
                        WHERE {cases_table}.user=userid AND {cases_table}.guild=guildid AND {cases_table}.type LIKE "%mute"
                        ORDER BY `{cases_table}`.`created_at` DESC LIMIT 1
                    ) as reason FROM `mutes` WHERE guildid=%s"""
            async with self.bot.db_main.read(query, (guild_id,)) as query_results:
                result = {row["userid"]: row["reason"] for row in query_results}
        else:
            query = "SELECT userid FROM `mutes` WHERE guildid=%s"
            async with self.bot.db_main.read(query, (guild_id,)) as query_results:
                result = [row["userid"] for row in query_results]
        return result

    @app_commands.command(name="unmute")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.checks.cooldown(5, 20)
    async def unmute(self, interaction: discord.Interaction, user: discord.Member):
        """Unmute someone
This will remove the role 'muted' for the targeted member

..Example unmute @someone

..Doc articles/mute"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        role = await self.get_muted_role(interaction.guild)
        # if role not in user.roles:
        if not await self.is_muted(interaction.guild, user, role):
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.mute.already-unmute"), ephemeral=True)
            return
        if role is not None:
            if not interaction.guild.me.guild_permissions.manage_roles:
                await interaction.response.send_message(
                    await self.bot._(interaction, "moderation.mute.cant-mute"), ephemeral=True)
                return
            if role.position >= interaction.guild.me.roles[-1].position:
                await interaction.response.send_message(
                    await self.bot._(interaction, "moderation.mute.mute-high"), ephemeral=True)
                return
        elif user.is_timed_out():
            if not interaction.guild.me.guild_permissions.moderate_members:
                await interaction.response.send_message(
                    await self.bot._(interaction, "moderation.mute.cant-timeout"), ephemeral=True)
                return
            if user.top_role.position >= interaction.guild.me.roles[-1].position:
                await interaction.response.send_message(
                    await self.bot._(interaction, "moderation.mute.too-high"), ephemeral=True)
                return
        await interaction.response.defer(ephemeral=True)
        # actually unmute
        await self.unmute_member(interaction.guild, user, interaction.user)
        # send log
        self.bot.dispatch("moderation_unmute", interaction.guild, interaction.user, user)
        # send in chat
        await self.send_chat_answer("unmute", user, interaction)
        # remove planned automatic unmutes
        await self.bot.task_handler.cancel_unmute(user.id, interaction.guild.id)
        await interaction.followup.send(await self.bot._(interaction,"moderation.mute.unmute-success"))

    @app_commands.command(name="mute-config")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.cooldown(1, 15)
    async def mute_config(self, interaction: discord.Interaction):
        """Auto configure the muted role for you, if you do not want to use the official timeout
        Useful if you want to have a base for a properly working muted role
        Warning: the process may break some things in your server, depending on how you configured your channel permissions.

        ..Doc moderator.html#mute-unmute
        """
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        await interaction.response.defer()
        confirm_view = ConfirmView(
            self.bot, interaction,
            validation=lambda inter: inter.user == interaction.user,
            ephemeral=False
        )
        await confirm_view.init()
        confirm_txt = await self.bot._(interaction, "moderation.mute-config.confirm")
        confirm_txt += "\n\n"
        confirm_txt += await self.bot._(interaction, "moderation.mute-config.tip",
                                        mute=await self.bot.get_command_mention("mute"))
        confirm_msg = await interaction.followup.send(confirm_txt, view=confirm_view, wait=True)

        await confirm_view.wait()
        await confirm_view.disable(confirm_msg)
        if not confirm_view.value:
            return

        role = await self.get_muted_role(interaction.guild)
        create = role is None
        role, errors_count = await self.configure_muted_role(interaction.guild, role)
        if role is None or errors_count >= len(interaction.guild.channels):
            await interaction.followup.send(await self.bot._(interaction, "moderation.mute-config.err"))
        elif create:
            await interaction.followup.send(await self.bot._(interaction, "moderation.mute-config.success", count=errors_count))
            self.bot.dispatch("config_edit", interaction.guild_id, interaction.user.id, "sconfig_option_set",
                              {"option": "muted_role", "value": str(role.id)})
        else:
            await interaction.followup.send(await self.bot._(interaction, "moderation.mute-config.success2", count=errors_count))


    @app_commands.command(name="ban")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.rename(duration="time")
    @app_commands.describe(
        duration="The duration of the ban, example 3d 7h 12min",
        days_to_delete="How many days of messages to delete, max 7",
        reason="The reason of the ban"
    )
    @app_commands.checks.cooldown(5, 20)
    async def ban(self, interaction: discord.Interaction, user: discord.User, duration: args.GreedyDurationArgument | None = None,
                  days_to_delete: app_commands.Range[int, 0, 7]=0, reason: str | None = None):
        """Ban someone
The 'days_to_delete' option represents the number of days worth of messages to delete from the user in the guild, bewteen 0 and 7

..Example ban @someone 3d You're bad

..Example ban someone#1234 7 Spam isn't tolerated here

..Example ban someone_else DM advertising is against Discord ToS!!!

..Doc moderator.html#ban-unban
        """
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if duration is not None:
            if duration <= 0:
                await interaction.response.send_message(await self.bot._(interaction, "timers.rmd.too-short"), ephemeral=True)
                return
            if duration > 60*60*24*365*20: # max 20 years
                await interaction.response.send_message(await self.bot._(interaction, "timers.rmd.too-long"), ephemeral=True)
                return
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.followup.send(await self.bot._(interaction, "moderation.ban.cant-ban"))
            return
        if member := interaction.guild.get_member(user.id):
            if member == interaction.guild.me or await target_is_higher(member, interaction.user):
                await interaction.followup.send(await self.bot._(interaction, "moderation.ban.staff-ban"))
                return
            if member.roles[-1].position >= interaction.guild.me.roles[-1].position:
                await interaction.followup.send(await self.bot._(interaction, "moderation.ban.too-high"))
                return
            # send DM only if the user is still in the server
            await self.dm_user(user, "ban", interaction, reason=reason)
        if days_to_delete not in range(8):
            days_to_delete = 0
        f_reason = reason or "Unspecified"
        try:
            await interaction.guild.ban(user, reason=f_reason[:512]+self.bot.zws, delete_message_seconds=days_to_delete * 86400)
        except discord.errors.Forbidden:
            await interaction.followup.send(await self.bot._(interaction, "moderation.ban.too-high"))
            return
        await self.bot.get_cog("Events").add_event("ban") # type: ignore
        if duration is not None:
            await self.bot.task_handler.add_task("ban", duration, user.id, interaction.guild_id)
        case_id = None
        if self.bot.database_online and (cases_cog := self.bot.get_cog("Cases")):
            case = Case(bot=self.bot, guild_id=interaction.guild_id, user_id=user.id, case_type="ban",
                        mod_id=interaction.user.id, reason=f_reason, date=self.bot.utcnow(), duration=duration)
            await cases_cog.db_add_case(case)
            case_id = case.id
        # send message in chat
        await self.send_chat_answer("ban", user, interaction, case_id)
        # send in modlogs
        self.bot.dispatch("moderation_ban", interaction.guild, interaction.user, user, case_id, reason, duration)
        await interaction.followup.send(await self.bot._(interaction, "moderation.ban.ban-success"))

    @app_commands.command(name="unban")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(reason="The reason of the unban")
    @app_commands.checks.cooldown(5, 20)
    async def unban(self, interaction: discord.Interaction, user: discord.User, reason: str | None=None):
        """Unban someone

..Example unban 1048011651145797673 Nice enough

..Doc moderator.html#ban-unban"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.followup.send(await self.bot._(interaction, "moderation.ban.cant-ban"))
            return
        try:
            await interaction.guild.fetch_ban(user)
        except discord.NotFound:
            await interaction.followup.send(await self.bot._(interaction, "moderation.ban.user-not-banned"))
            return
        f_reason = reason or "Unspecified"
        await interaction.guild.unban(user, reason=f_reason[:512] + self.bot.zws)
        case_id = None
        if self.bot.database_online and (cases_cog := self.bot.get_cog("Cases")):
            case = Case(bot=self.bot, guild_id=interaction.guild_id, user_id=user.id, case_type="unban",
                        mod_id=interaction.user.id, reason=f_reason, date=self.bot.utcnow())
            await cases_cog.db_add_case(case)
            case_id = case.id
        # send in chat
        await self.send_chat_answer("unban", user, interaction, case_id)
        # send in modlogs
        self.bot.dispatch("moderation_unban", interaction.guild, interaction.user, user, case_id, reason)
        await interaction.followup.send(await self.bot._(interaction, "moderation.ban.unban-success"))

    @app_commands.command(name="softban")
    @app_commands.guild_only()
    @app_commands.default_permissions(kick_members=True)
    @app_commands.describe(reason="The reason of the kick")
    @app_commands.checks.cooldown(5, 20)
    async def softban(self, interaction: discord.Interaction, user: discord.Member, *, reason: str | None=None):
        """Kick a member and lets Discord delete all his messages up to 7 days old.
Permissions for using this command are the same as for the kick

..Example softban @someone No spam pls

..Doc moderator.html#softban"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(await self.bot._(interaction, "moderation.ban.cant-ban"), ephemeral=True)
            return

        if user == interaction.guild.me or await target_is_higher(user, interaction.user):
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.kick.cant-staff"), ephemeral=True
            )
            return
        if user.roles[-1].position >= interaction.guild.me.roles[-1].position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.kick.too-high"), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        # send DM
        await self.dm_user(user, "kick", interaction, reason)

        f_reason = reason or "Unspecified"
        try:
            await interaction.guild.ban(user, reason=f_reason[:512] + self.bot.zws, delete_message_days=7)
            await user.unban(reason=self.bot.zws)
        except discord.errors.Forbidden:
            await interaction.followup.send(await self.bot._(interaction, "moderation.kick.too-high"))
            return
        case_id = None
        if self.bot.database_online and (cases_cog := self.bot.get_cog("Cases")):
            case = Case(bot=self.bot, guild_id=interaction.guild_id, user_id=user.id, case_type="softban",
                        mod_id=interaction.user.id, reason=f_reason, date=self.bot.utcnow())
            await cases_cog.db_add_case(case)
            case_id = case.id
        # send in chat
        await self.send_chat_answer("kick", user, interaction, case_id)
        # send in modlogs
        self.bot.dispatch("moderation_softban", interaction.guild, interaction.user, user, case_id, reason)
        await interaction.followup.send(await self.bot._(interaction, "moderation.ban.softban-success"))

    async def dm_user(self, user: UserOrMember, action: str, interaction: discord.Interaction,
                      reason: str | None = None, duration: str | None = None):
        "DM a user about a moderation action taken against them"
        if interaction.guild is None:
            raise RuntimeError("This method is supposed to be used in a guild context")
        if user.id in self.bot.get_cog("Welcomer").no_message: # type: ignore
            return
        if action in ("warn", "mute", "kick", "ban"):
            message = await self.bot._(user, "moderation."+action+"-dm", guild=interaction.guild.name)
        else:
            return
        color: int | None = None
        if help_cog := self.bot.get_cog("Help"):
            color = help_cog.help_color
        emb = discord.Embed(description=message, colour=color)
        if duration:
            if len(duration) > 1020:
                duration = duration[:1020] + "..."
            _duration = await self.bot._(user, "misc.duration")
            emb.add_field(name=_duration.capitalize(), value=duration)
        if reason:
            if len(reason) > 1020:
                reason = reason[:1020] + "..."
            _reason = await self.bot._(user, "misc.reason")
            emb.add_field(name=_reason.capitalize(),
                          value=reason, inline=False)
        try:
            await user.send(embed=emb)
        except (discord.Forbidden, discord.NotFound):
            pass
        except discord.HTTPException as err:
            if err.code == 50007:
                # "Cannot send message to this user"
                return
            self.bot.dispatch("error", err, interaction)
        except Exception as err:
            self.bot.dispatch("error", err, interaction)

    async def send_chat_answer(self, action: str, user: UserOrMember, interaction: discord.Interaction, case: int | None = None):
        "Send a message in the chat about a moderation action taken"
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if action not in ("warn", "mute", "unmute", "kick", "ban", "unban"):
            raise ValueError("Invalid action: "+action)
        if not interaction.channel.permissions_for(interaction.guild.me).embed_links:
            return
        message = await self.bot._(interaction.guild_id, "moderation."+action+"-chat", user=user.mention, userid=user.id)
        _case = await self.bot._(interaction.guild_id, "misc.case")
        color = discord.Color.red()
        if action in ("unmute", "unban"):
            if help_cog := self.bot.get_cog("Help"):
                color = help_cog.help_color
        emb = discord.Embed(description=message, colour=color)
        if case:
            emb.add_field(name=_case.capitalize(), value=f"#{case}")
        await interaction.channel.send(embed=emb)

    @app_commands.command(name="banlist")
    @app_commands.guild_only()
    @app_commands.default_permissions(ban_members=True)
    @app_commands.describe(show_reasons="Show or not the bans reasons")
    @app_commands.checks.cooldown(2, 20)
    async def banlist(self, interaction: discord.Interaction, show_reasons: bool = True):
        """Check the list of currently banned members.
The 'show_reasons' parameter is used to display the ban reasons.

You must be an administrator of this server to use this command.

..Doc moderator.html#banlist-mutelist"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if not interaction.guild.me.guild_permissions.ban_members:
            await interaction.response.send_message(await self.bot._(interaction, "moderation.ban.cant-ban"), ephemeral=True)
            return
        guild = interaction.guild

        class BansPaginator(Paginator):
            "Paginator used to display banned users"
            saved_bans: list[discord.guild.BanEntry] = []
            users: set[int] = set()

            async def get_page_count(self) -> int:
                length = len(self.saved_bans)
                if length == 0:
                    return 1
                if length%1000 == 0:
                    return self.page+1
                return ceil(length/30)

            async def get_page_content(self, interaction, page):
                "Create one page"
                if last_user := (None if len(self.saved_bans) == 0 else self.saved_bans[-1].user):
                    self.saved_bans += [
                        entry
                        async for entry in guild.bans(limit=1000, after=last_user)
                        if entry.user.id not in self.users
                    ]
                else:
                    self.saved_bans += [
                        entry
                        async for entry in guild.bans(limit=1000)
                        if entry.user.id not in self.users
                    ]
                self.users = {entry.user.id for entry in self.saved_bans}

                _title = await self.client._(interaction, "moderation.ban.list-title-0")
                emb = discord.Embed(
                    title=_title.format(guild.name),
                    color=7506394
                )
                if len(self.saved_bans) == 0:
                    emb.description = await self.client._(interaction, "moderation.ban.no-bans")
                else:
                    page_start, page_end = (page-1)*30, min(page*30, len(self.saved_bans))
                    for i in range(page_start, page_end, 10):
                        column_start, column_end = i+1, min(i+10, len(self.saved_bans))
                        if show_reasons:
                            values = [f"{entry.user}  *({entry.reason})*" for entry in self.saved_bans[i:i+10]]
                        else:
                            values = [str(entry.user) for entry in self.saved_bans[i:i+10]]
                        emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(values))
                if (pages_count := await self.get_page_count()) > 1:
                    footer = f"{page}/{pages_count}"
                    emb.set_footer(text=footer)
                return {
                    "embed": emb
                }

        _quit = await self.bot._(interaction, "misc.quit")
        view = BansPaginator(self.bot, interaction.user, stop_label=_quit.capitalize())
        await view.send_init(interaction)


    @app_commands.command(name="mutelist")
    @app_commands.guild_only()
    @app_commands.default_permissions(moderate_members=True)
    @app_commands.describe(show_reasons="Show or not the mute reasons")
    @app_commands.checks.cooldown(2, 20)
    async def mutelist(self, interaction: discord.Interaction, show_reasons: bool = True):
        """Check the list of members currently **muted by using this bot**.
The 'show_reasons' parameter is used to display the mute reasons.

..Doc moderator.html#banlist-mutelist"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            muted_list = await self.db_get_muted_list(interaction.guild_id, reasons=show_reasons)
        except Exception as err:
            await interaction.followup.send(await self.bot._(interaction, "moderation.error"))
            self.bot.dispatch("error", err, interaction)
            return
        guild = interaction.guild

        class MutesPaginator(Paginator):
            "Paginator used to display muted users"
            users_map: dict[int, discord.User | None] = {}

            async def get_page_count(self) -> int:
                length = len(muted_list)
                if length == 0:
                    return 1
                return ceil(length/30)

            async def _resolve_user(self, user_id: int):
                if user := self.users_map.get(user_id):
                    return user
                if user := self.client.get_user(user_id):
                    self.users_map[user_id] = user
                    return user
                if user := await self.client.fetch_user(user_id):
                    self.users_map[user_id] = user
                    return user
                return user_id

            async def get_page_content(self, interaction, page):
                "Create one page"
                title = await self.client._(interaction, "moderation.mute.list-title-0", guild=guild.name)
                if serverconfig_cog := self.client.get_cog("ServerConfig"):
                    emb_color = serverconfig_cog.embed_color
                else:
                    emb_color = None
                emb = discord.Embed(
                    title=title,
                    color=emb_color
                )
                if len(muted_list) == 0:
                    emb.description = await self.client._(interaction, "moderation.mute.no-mutes")
                else:
                    page_start, page_end = (page-1)*30, min(page*30, len(muted_list))
                    for i in range(page_start, page_end, 10):
                        column_start, column_end = i+1, min(i+10, len(muted_list))
                        values: list[str] = []
                        if isinstance(muted_list, dict):
                            for user_id, reason in list(muted_list.items())[i:i+10]:
                                user = await self._resolve_user(user_id)
                                values.append(f"{user}  *({reason})*")
                        else:
                            for user_id in muted_list[i:i+10]:
                                user = await self._resolve_user(user_id)
                                values.append(str(user))
                        emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(values))
                if (pages_count := await self.get_page_count()) > 1:
                    footer = f"{page}/{pages_count}"
                    emb.set_footer(text=footer)
                return {
                    "embed": emb
                }

        _quit = await self.bot._(interaction, "misc.quit")
        view = MutesPaginator(self.bot, interaction.user, stop_label=_quit.capitalize())
        await view.send_init(interaction)


    @app_commands.command(name="unhoist")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_nicknames=True)
    @app_commands.describe(characters="The list of characters that should be considered as hoisting")
    @app_commands.checks.cooldown(2, 120)
    async def unhoist(self, interaction: discord.Interaction, characters: str | None = None):
        """Remove the special characters from the beginning of usernames

        ..Example unhoist

        ..Example unhoist 0AZ^_

        ..Doc moderator.html#unhoist-members"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        count = 0
        if not interaction.guild.me.guild_permissions.manage_nicknames:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.missing-manage-nick"), ephemeral=True
            )
            return
        if len(interaction.guild.members) > 5000:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.unhoist-too-many-members"), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        if characters is None:
            def check(username: str):
                while username < '0' and len(username):
                    username = username[1:]
                if len(username) == 0:
                    username = "z unhoisted"
                return username
        else:
            characters = characters.lower()
            def check(username: str):
                while len(username) and username[0].lower() in characters+' ':
                    username = username[1:]
                if len(username) == 0:
                    username = "z unhoisted"
                return username

        for member in interaction.guild.members:
            new = check(member.display_name)
            if new != member.display_name:
                if not self.bot.beta:
                    try:
                        await member.edit(nick=new)
                        count += 1
                    except discord.Forbidden:
                        pass
        await interaction.followup.send(await self.bot._(interaction.guild_id, "moderation.unhoisted", count=count))

    @app_commands.command(name="destop")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.checks.cooldown(2, 30)
    async def destop(self, interaction: discord.Interaction, start_message: args.MessageArgument):
        """Clear every message between now and an older message
        Message can be either ID or url
        Limited to 1,000 messages

        ..Example destop https://discordapp.com/channels/356067272730607628/488769306524385301/740249890201796688

        ..Doc moderator.html#clear"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if start_message.guild != interaction.guild or start_message.guild is None:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.destop.no-guild"), ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        channel = start_message.channel
        if isinstance(channel, discord.PartialMessageable):
            channel = await start_message.guild.fetch_channel(channel.id)
        bot_perms = start_message.channel.permissions_for(interaction.guild.me)
        if not bot_perms.manage_messages:
            await interaction.followup.send(await self.bot._(interaction, "moderation.need-manage-messages"))
            return
        if not bot_perms.read_message_history:
            await interaction.followup.send(await self.bot._(interaction, "moderation.need-read-history"))
            return
        if start_message.created_at < self.bot.utcnow() - datetime.timedelta(days=21):
            await interaction.followup.send(await self.bot._(interaction, "moderation.destop.too-old", days=21))
            return
        min_date = start_message.created_at - datetime.timedelta(seconds=1)
        messages = await channel.purge( # pyright: ignore[reportAttributeAccessIssue]
            after=min_date, limit=CLEAR_MAX_MESSAGES, oldest_first=False
        )
        await interaction.followup.send(await self.bot._(interaction, "moderation.clear.done", count=len(messages)))
        self.bot.dispatch("moderation_clear", interaction.channel, interaction.user, len(messages))


    async def configure_muted_role(self, guild: discord.Guild, role: discord.Role | None = None):
        """Ajoute le rôle muted au serveur, avec les permissions nécessaires.
        Retourne le rôle et le nombre d'erreurs rencontrées"""
        if not guild.me.guild_permissions.manage_roles:
            return None, 0
        if role is None:
            role = await guild.create_role(name="muted")
        errors_count = 0
        if (serverconfig_cog := self.bot.get_cog("ServerConfig")) is None:
            raise RuntimeError("ServerConfig cog not found, cannot get muted role color")
        try:
            for (category, channelslist) in guild.by_category():
                for channel in channelslist:
                    if len(channel.changed_roles) == 0 or channel.permissions_synced:
                        continue
                    try:
                        await channel.set_permissions(role, send_messages=False)
                        for r in channel.changed_roles:
                            if r.managed and len(r.members) == 1 and r.members[0].bot:
                                # if it's an integrated bot role
                                continue
                            obj = channel.overwrites_for(r)
                            if obj.send_messages:
                                obj.send_messages = None
                                await channel.set_permissions(r, overwrite=obj)
                    except discord.errors.Forbidden:
                        errors_count += 1
                if category is not None and category.permissions_for(guild.me).manage_roles:
                    await category.set_permissions(role, send_messages=False)
        except Exception as err:
            self.bot.dispatch("error", err)
            errors_count = len(guild.channels)
        await serverconfig_cog.set_option(guild.id, "muted_role", role)
        return role, errors_count


async def setup(bot: Axobot):
    await bot.add_cog(Moderation(bot))
