import asyncio
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from core.arguments.args import GuildInviteArgument
from core.bot_classes import Axobot

from .src.types import TrackedInvite
from .src.views import TrackedInvitesPaginator


class InvitesTracker(commands.Cog):
    "Track the invitations usage of your server"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "invites_tracker"

    async def db_get_invites(self, guild_id: int) -> list[TrackedInvite]:
        "Get a list of tracked invites associated to a guild"
        query = "SELECT * FROM `invites_tracker` WHERE `guild_id` = %s AND `beta` = %s"
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta)) as query_result:
            return query_result

    async def db_add_invite(self, guild_id: int, invite_id: str, user_id: int | None, creation_date: datetime, usage_count: int):
        "Insert a tracked invite in the database, or update it if it already exists"
        query = (
            "INSERT INTO `invites_tracker` "\
            "(`guild_id`, `invite_id`, `user_id`, `creation_date`,`last_count`,`beta`) "\
            "VALUES (%s, %s, %s, %s, %s, %s) "\
            "ON DUPLICATE KEY UPDATE `user_id` = VALUES(`user_id`), `last_count` = VALUES(`last_count`)"
        )
        async with self.bot.db_main.write(query, (guild_id, invite_id, user_id, creation_date, usage_count, self.bot.beta)):
            pass

    async def db_update_invite_count(self, guild_id: int, invite_id: str, usage_count: int):
        "Update the usage count of a tracked invite"
        query = "UPDATE `invites_tracker` SET `last_count` = %s WHERE `guild_id` = %s AND `invite_id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (usage_count, guild_id, invite_id, self.bot.beta)):
            pass

    async def db_update_invite_name(self, guild_id: int, invite_id: str, name: str | None):
        "Update the name of a tracked invite"
        query = "UPDATE `invites_tracker` SET `name` = %s WHERE `guild_id` = %s AND `invite_id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (name, guild_id, invite_id, self.bot.beta)):
            pass

    async def db_delete_invite(self, guild_id: int, invite_id: str):
        "Delete a tracked invite from the database"
        query = "DELETE FROM `invites_tracker` WHERE `guild_id` = %s AND `invite_id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (guild_id, invite_id, self.bot.beta)):
            pass


    async def sync_guild_invites(self, guild: discord.Guild):
        "Sync the tracked invites with the current invites of a guild"
        count = 0
        guild_invites = await guild.invites()
        # add/update existing invitations
        for invite in guild_invites:
            user_id = invite.inviter.id if invite.inviter else None
            await self.db_add_invite(guild.id, invite.code, user_id, invite.created_at, invite.uses)
            count += 1
        # delete removed invitations
        for tracked_invite in await self.db_get_invites(guild.id):
            if not next((i for i in guild_invites if i.code == tracked_invite["invite_id"]), None):
                await self.db_delete_invite(guild.id, tracked_invite["invite_id"])
                count += 1
        return count

    async def check_invites_usage(self, guild: discord.Guild):
        "Detect which invite was just used, by comparing the stored usage with the current usage"
        tracked_invites = await self.db_get_invites(guild.id)
        guild_invites = await guild.invites()
        # first, check if an invite was used exactly once
        for tracked_invite in tracked_invites:
            invite = next((i for i in guild_invites if i.code == tracked_invite["invite_id"]), None)
            if invite is None:
                continue
            if invite.uses == tracked_invite["last_count"] + 1:
                await self.db_update_invite_count(guild.id, invite.code, invite.uses)
                return (invite, tracked_invite)
        # if not, check if an invite was used more than once
        for tracked_invite in tracked_invites:
            invite = next((i for i in guild_invites if i.code == tracked_invite["invite_id"]), None)
            if invite is None:
                continue
            if invite.uses > tracked_invite["last_count"]:
                await self.db_update_invite_count(guild.id, invite.code, invite.uses)
                return (invite, tracked_invite)


    async def is_tracker_enabled(self, guild_id: int) -> bool:
        return await self.bot.get_config(guild_id, "enable_invites_tracking")


    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        "Update the tracked invite when a new invite is created"
        if invite.guild is None or not await self.is_tracker_enabled(invite.guild.id):
            return
        inviter_id = invite.inviter.id if invite.inviter else None
        await self.db_add_invite(invite.guild.id, invite.code, inviter_id, invite.created_at, invite.uses or 0)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite: discord.Invite):
        "Remove the tracked invite when an invite is deleted"
        if invite.guild is None or not await self.is_tracker_enabled(invite.guild.id):
            return
        await self.db_delete_invite(invite.guild.id, invite.code)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        "Detect which invite was used when a member joins the server"
        if not member.guild.me.guild_permissions.manage_guild:
            return
        await asyncio.sleep(1) # Wait for the invite to be updated
        used_invite = await self.check_invites_usage(member.guild)
        if used_invite:
            discord_invite, tracked_invite = used_invite
            tracked_invite["last_count"] = discord_invite.uses
            self.bot.dispatch("invite_used", member, tracked_invite)
            await self.db_update_invite_count(member.guild.id, discord_invite.code, discord_invite.uses)
        else:
            self.bot.log.warn(f"Could not detect the invite used in guild {member.guild.id}")


    invites_main = app_commands.Group(
        name="invites-tracker",
        description="Track your invitations usage",
        default_permissions=discord.Permissions(manage_guild=True),
        guild_only=True
    )

    @invites_main.command(name="enable")
    @app_commands.checks.cooldown(1, 60)
    async def enable_tracking(self, interaction: discord.Interaction):
        "Start tracking the invitations usage of your server"
        await interaction.response.defer()
        await self.bot.get_cog("ServerConfig").config_set_cmd(interaction, "enable_invites_tracking", str(True))
        if interaction.guild.me.guild_permissions.manage_guild:
            await self.sync_guild_invites(interaction.guild)

    @invites_main.command(name="disable")
    @app_commands.checks.cooldown(1, 60)
    async def disable_tracking(self, interaction: discord.Interaction):
        "Stop tracking the invitations usage of your server"
        await interaction.response.defer()
        await self.bot.get_cog("ServerConfig").config_set_cmd(interaction, "enable_invites_tracking", str(False))

    @invites_main.command(name="resync")
    @app_commands.checks.cooldown(1, 60)
    async def resync_invites(self, interaction: discord.Interaction):
        "Ensure the stored invites are up-to-date with the current invites of the server"
        if not await self.is_tracker_enabled(interaction.guild_id):
            await interaction.response.send_message(
                await self.bot._(interaction, "invites_tracker.tracking-disabled"),
                ephemeral=True)
            return
        if not interaction.guild.me.guild_permissions.manage_guild:
            await interaction.response.send_message(
                await self.bot._(interaction, "invites_tracker.missing-permission"),
                ephemeral=True)
            return
        await interaction.response.defer()
        count = await self.sync_guild_invites(interaction.guild)
        await interaction.followup.send(f"Synced {count} invites")

    @invites_main.command(name="set-name")
    @app_commands.checks.cooldown(4, 30)
    @app_commands.describe(
        invite="The invite URL to rename",
        name="The custom name to give to the invite, or 'none' to reset it"
    )
    async def name_invite(self, interaction: discord.Interaction, invite: GuildInviteArgument, name: str):
        "Specify a custom name to give to an invite URL"
        if not await self.is_tracker_enabled(interaction.guild_id):
            await interaction.response.send_message(
                await self.bot._(interaction, "invites_tracker.tracking-disabled"),
                ephemeral=True)
            return
        await interaction.response.defer()
        new_name = None if name.lower() == "none" else name
        await self.db_update_invite_name(interaction.guild_id, invite.code, new_name)
        link = f"discord.gg/{invite.code}"
        if new_name is None:
            await interaction.followup.send(
                await self.bot._(interaction, "invites_tracker.rename.reset-success", link=link)
            )
        else:
            await interaction.followup.send(
                await self.bot._(interaction, "invites_tracker.rename.set-success", link=link, name=new_name)
            )

    @invites_main.command(name="list-invites")
    @app_commands.checks.cooldown(4, 60)
    async def list_tracked_invites(self, interaction: discord.Interaction):
        "List the tracked invites and their usage"
        if not await self.is_tracker_enabled(interaction.guild_id):
            await interaction.response.send_message(
                await self.bot._(interaction, "invites_tracker.tracking-disabled"),
                ephemeral=True)
            return
        await interaction.response.defer()
        invites = await self.db_get_invites(interaction.guild_id)
        _quit = await self.bot._(interaction, "misc.quit")
        view = TrackedInvitesPaginator(
            self.bot,
            interaction.user,
            invites,
            stop_label=_quit.capitalize()
        )
        await view.send_init(interaction)


async def setup(bot):
    await bot.add_cog(InvitesTracker(bot))
