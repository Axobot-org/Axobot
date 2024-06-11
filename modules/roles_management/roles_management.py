import discord
from discord import app_commands
from discord.ext import commands

from core.arguments import args
from core.bot_classes import Axobot
from core.formatutils import FormatUtils

from .view.roles_members_pagination import RoleMembersPaginator


class RolesManagement(commands.Cog):
    "A few commands to manage roles"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "roles_management"
        # maximum of roles granted/revoked by query
        self.max_roles_modifications = 300

    role_main = app_commands.Group(
        name="role",
        description="A few commands to manage roles",
        default_permissions=discord.Permissions(manage_roles=True),
        guild_only=True
    )

    @role_main.command(name="set-color")
    @app_commands.describe(color="The new color role, preferably in hex format (#ff6699)")
    @app_commands.checks.cooldown(5, 15)
    async def role_color(self, interaction: discord.Interaction, role: discord.Role, color: args.ColorArgument):
        """Change a color of a role

        ..Example role set-color "Admin team" red

        ..Doc moderator.html#role-manager"""
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.mute.cant-mute"), ephemeral=True
            )
            return
        if role.position >= interaction.guild.me.roles[-1].position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.too-high", r=role.name), ephemeral=True
            )
            return
        await interaction.response.defer()
        await role.edit(colour=color,reason=f"Asked by {interaction.user}")
        await interaction.followup.send(await self.bot._(interaction, "moderation.role.color-success", role=role.name))

    @role_main.command(name="members-list")
    @app_commands.checks.cooldown(3, 15)
    async def role_list(self, interaction: discord.Interaction, *, role: discord.Role):
        """Send the list of members in a role

        ..Example role members-list "Technical team"

        ..Doc moderator.html#role-manager"""
        _quit = await self.bot._(interaction, "misc.quit")
        view = RoleMembersPaginator(self.bot, interaction.user, role, stop_label=_quit)
        await view.send_init(interaction)

    @role_main.command(name="temporary-grant")
    @app_commands.checks.cooldown(3, 15)
    @app_commands.rename(duration="time")
    @app_commands.describe(
        role="The role to grant",
        user="The user to grant the role to",
        duration="The duration for which the role will be granted, example 3d 7h 12min"
    )
    async def roles_temp_grant(self, interaction: discord.Interaction, role: discord.Role, user: discord.Member,
                               duration: args.GreedyDurationArgument):
        """Temporary give a role to a member

        ..Example role temporary-grant Slime Theo 1h

        ..Doc moderator.html#role-manager"""
        if duration > 60*60*24*31: # max 31 days
            await interaction.response.send_message(
                await self.bot._(interaction, "timers.rmd.too-long"), ephemeral=True
            )
            return
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.mute.cant-mute"), ephemeral=True
            )
            return
        my_position = interaction.guild.me.roles[-1].position
        if role.position >= my_position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.give-too-high", r=role.name), ephemeral=True
            )
            return
        if role.position >= interaction.user.roles[-1].position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.give-roles-higher"), ephemeral=True
            )
            return
        await interaction.response.defer()
        await user.add_roles(role, reason=f"Asked by {interaction.user}")
        await self.bot.task_handler.add_task("role-grant", duration, user.id, interaction.guild_id, data={"role": role.id})
        f_duration = await FormatUtils.time_delta(duration, lang=await self.bot._(interaction, "_used_locale"))
        await interaction.followup.send(
            await self.bot._(interaction, "moderation.role.temp-grant-success",
                             role=role.name, user=user.mention, time=f_duration),
            allowed_mentions=discord.AllowedMentions.none()
        )


    @role_main.command(name="grant")
    @app_commands.describe(
        role="The role to grant",
        users="A list of users or roles to assign this role to."
    )
    @app_commands.checks.cooldown(3, 15)
    async def roles_grant(self, interaction: discord.Interaction, role: discord.Role, users: args.GreedyUsersOrRolesArgument):
        """Give a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role grant Elders everyone

        ..Example role grant Slime Theo AsiliS

        ..Doc moderator.html#role-manager"""
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.mute.cant-mute"), ephemeral=True
            )
            return
        my_position = interaction.guild.me.roles[-1].position
        if role.position >= my_position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.give-too-high", r=role.name), ephemeral=True
            )
            return
        if role.position >= interaction.user.roles[-1].position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.give-roles-higher"), ephemeral=True
            )
            return
        await interaction.response.defer()

        n_users: set[discord.Member] = set()
        for item in users:
            if isinstance(item, discord.Member):
                if role not in item.roles:
                    n_users.add(item)
            else:
                for member in item.members:
                    if role not in member.roles:
                        n_users.add(member)
        await interaction.followup.send(await self.bot._(interaction, "moderation.role.give-pending", n=len(n_users)))

        count = 0
        for user in n_users:
            if count >= self.max_roles_modifications:
                break
            await user.add_roles(role, reason=f"Asked by {interaction.user}")
            count += 1
        answer = await self.bot._(interaction, "moderation.role.give-success", count=count, m=len(n_users))
        if count == self.max_roles_modifications and len(n_users) > count:
            answer += f'\n⚠️ *{await self.bot._(interaction, "moderation.role.limit-hit", limit=self.max_roles_modifications)}*'
        await interaction.edit_original_response(content=answer)

    @role_main.command(name="revoke")
    @app_commands.describe(
        role="The role to revoke",
        users="A list of users or roles to remove this role from."
    )
    @app_commands.checks.cooldown(3, 15)
    async def roles_revoke(self, interaction: discord.Interaction, role: discord.Role, users: args.GreedyUsersOrRolesArgument):
        """Remove a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role revoke VIP @muted

        ..Doc moderator.html#role-manager"""
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.mute.cant-mute"), ephemeral=True
            )
            return
        my_position = interaction.guild.me.roles[-1].position
        if role.position >= my_position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.give-too-high",r=role.name), ephemeral=True
            )
            return
        if role.position >= interaction.user.roles[-1].position:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.role.give-roles-higher"), ephemeral=True
            )
            return
        await interaction.response.defer()

        n_users: set[discord.Member] = set()
        for item in users:
            if isinstance(item, discord.Member):
                if role in item.roles:
                    n_users.add(item)
            else:
                for member in item.members:
                    if role in member.roles:
                        n_users.add(member)
        await interaction.followup.send(await self.bot._(interaction, "moderation.role.remove-pending", n=len(n_users)))

        count = 0
        for user in n_users:
            if count >= self.max_roles_modifications:
                break
            await user.remove_roles(role, reason=f"Asked by {interaction.user}")
            count += 1
        answer = await self.bot._(interaction, "moderation.role.remove-success", count=count, m=len(n_users))
        if count == self.max_roles_modifications and len(n_users) > count:
            answer += f'\n⚠️ *{await self.bot._(interaction, "moderation.role.limit-hit", limit=self.max_roles_modifications)}*'
        await interaction.edit_original_response(content=answer)


async def setup(bot: Axobot):
    await bot.add_cog(RolesManagement(bot))
