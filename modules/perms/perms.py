import typing
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot
from core.type_utils import assert_interaction_channel_is_guild_messageable

from .arguments.perms_args import (AcceptableChannelTypes, TargetArgument,
                                   TextChannelTypes, VoiceChannelTypes)


@dataclass(frozen=True, kw_only=True)
class PermissionRow:
    name: str
    emoji: str

@dataclass(frozen=True, kw_only=True)
class PermissionSection:
    title: str
    perms: list[PermissionRow]


class Perms(commands.Cog):
    """Cog with a single command, allowing you to see the permissions of a member or a role in a channel."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "perms"
        self.general_permissions = [key for key, value in discord.Permissions().general() if value]
        self.text_permissions = [key for key, value in discord.Permissions().text() if value]
        self.voice_permissions = [key for key, value in (discord.Permissions().voice()) if value]

    async def _get_permissions_sections(
            self,
            interaction: discord.Interaction,
            permissions: discord.Permissions,
            channel: AcceptableChannelTypes
        ) -> list[PermissionSection]:
        """Get the sections of permissions for display."""
        emoji = {
            True: self.bot.emojis_manager.customs["green_check"],
            False: self.bot.emojis_manager.customs["red_cross"]
        }

        # if target is admin, only display that
        if permissions.administrator:
            return [PermissionSection(
                title=self.bot.zws,
                perms=[PermissionRow(
                    name=await self._build_permission_translation(interaction, "administrator"),
                    emoji=emoji[True]
                )]
            )]

        result: list[PermissionSection] = []

        result.append(PermissionSection(
            title=await self.bot._(interaction, "permissions.channel.general"),
            perms=[PermissionRow(
                name=await self._build_permission_translation(interaction, perm_id),
                emoji=emoji[getattr(permissions, perm_id)]
            ) for perm_id in self.general_permissions]
        ))

        is_category_or_none = channel is None or isinstance(channel, discord.CategoryChannel)

        if is_category_or_none or isinstance(channel, typing.get_args(TextChannelTypes)):
            result.append(PermissionSection(
                title=await self.bot._(interaction, "permissions.channel.text_channels"),
                perms=[PermissionRow(
                    name=await self._build_permission_translation(interaction, perm_id),
                    emoji=emoji[getattr(permissions, perm_id)]
                ) for perm_id in self.text_permissions]
            ))

        if is_category_or_none or isinstance(channel, typing.get_args(VoiceChannelTypes)):
            result.append(PermissionSection(
                title=await self.bot._(interaction, "permissions.channel.voice_channels"),
                perms=[PermissionRow(
                    name=await self._build_permission_translation(interaction, perm_id),
                    emoji=emoji[getattr(permissions, perm_id)]
                ) for perm_id in self.voice_permissions]
            ))

        return result

    async def _build_permission_translation(self, interaction: discord.Interaction, perm_id: str) -> str:
        perm_tr = await self.bot._(interaction, "permissions.list."+perm_id)
        if "permissions.list." in perm_tr:  # unsuccessful translation
            perm_tr = perm_id.replace('_', ' ').title()
        return perm_tr

    @app_commands.command(name="permissions")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(
        channel="The channel to check the permissions in",
        target="The member or role to check the permissions of, or an integer/binary value"
    )
    async def check_permissions(self, interaction: discord.Interaction, channel: AcceptableChannelTypes = None,
                                target: TargetArgument = None):
        """Check the permissions assigned to a member/role
        By default, it will calculate the author's permissions at the server level.
        You can also choose to view the permissions associated to a raw integer/binary value (if so, 'channel' will be ignored)

        ..Example permissions #announcements everyone

        ..Example permissions Axobot

        ..Example permissions 0b1001

        ..Doc infos.html#permissions"""
        if not assert_interaction_channel_is_guild_messageable(interaction):
            return
        if target is None:
            target = interaction.user
        await interaction.response.defer()

        if isinstance(target, discord.Member):
            if channel is None:
                perms = target.guild_permissions
            else:
                perms = channel.permissions_for(target)
            col = target.color
            avatar = target.display_avatar.replace(static_format="png", size=256)
            name = await self.bot._(interaction, "permissions.target.member", name=target.display_name)
        elif isinstance(target, discord.Role):
            if channel is None:
                perms = target.permissions
            else:
                perms = channel.permissions_for(target)
            col = target.color
            avatar = interaction.guild.icon.replace(format="png", size=256) if interaction.guild.icon else None
            name = await self.bot._(interaction, "permissions.target.role", name=str(target))
        else:
            perms = discord.Permissions(target)
            col = discord.Color.blurple()
            avatar = None
            name = await self.bot._(interaction, "permissions.target.value", value=f"{target} | {bin(target)}")

        if isinstance(target, int) or channel is None:
            desc = None
        elif isinstance(channel, discord.CategoryChannel):
            desc = await self.bot._(interaction, "permissions.channel.category", name=channel.name)
        else:
            desc = await self.bot._(interaction, "permissions.channel.channel", mention=channel.mention)

        embed = discord.Embed(color=col, description=desc)
        for perm_section in await self._get_permissions_sections(interaction, perms, channel):
            paragraph = "\n".join([
                f"{perm.emoji}{perm.name}"
                for perm in sorted(perm_section.perms, key=lambda x: x.name)
            ])
            embed.add_field(name=perm_section.title, value=paragraph)

        _whatisthat = await self.bot._(interaction, "permissions.whatisthat")
        embed.add_field(name=self.bot.zws, value=f"[{_whatisthat}]({self.bot.doc_url}perms.html)",
                        inline=False)
        embed.set_author(name=name, icon_url=avatar)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Perms(bot))
