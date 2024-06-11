from math import ceil

import discord
from discord import app_commands
from discord.ext import commands

from core.arguments import args
from core.bot_classes import Axobot
from core.paginator import Paginator


class EmojisManagement(commands.Cog):
    "Manage the guild's emojis"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "emojis_management"

    emojis_main = app_commands.Group(
        name="emojis",
        description="Manage your emojis",
        default_permissions=discord.Permissions(manage_expressions=True),
        guild_only=True,
    )

    @emojis_main.command(name="rename")
    @app_commands.describe(emoji="The emoji to rename", name="The new name")
    async def emoji_rename(self, interaction: discord.Interaction, emoji: args.EmojiArgument, name: str):
        """Rename an emoji

        ..Example emoji rename :cool: supercool

        ..Doc moderator.html#emoji-manager"""
        if emoji.guild != interaction.guild:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.emoji.wrong-guild"), ephemeral=True
            )
            return
        if not interaction.guild.me.guild_permissions.manage_expressions:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.emoji.cant-emoji"), ephemeral=True
            )
            return
        await interaction.response.defer()
        await emoji.edit(name=name)
        await interaction.followup.send(await self.bot._(interaction, "moderation.emoji.renamed", emoji=emoji))

    @emojis_main.command(name="restrict")
    @app_commands.describe(
        emoji="The emoji to restrict",
        roles="The roles allowed to use this emoji (separated by spaces), or 'everyone'"
    )
    @app_commands.checks.cooldown(2, 10)
    async def emoji_restrict(self, interaction: discord.Interaction, emoji: args.EmojiArgument,
                             roles: args.GreedyRolesArgument):
        """Restrict the use of an emoji to certain roles

        ..Example emoji restrict :vip: @VIP @Admins

        ..Example emoji restrict :vip: everyone

        ..Doc moderator.html#emoji-manager"""
        if emoji.guild != interaction.guild:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.emoji.wrong-guild"), ephemeral=True
            )
            return
        if not interaction.guild.me.guild_permissions.manage_expressions:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.emoji.cant-emoji"), ephemeral=True
            )
            return
        await interaction.response.defer()
        # everyone role
        if interaction.guild.default_role in roles:
            await emoji.edit(roles=[interaction.guild.default_role])
            await interaction.followup.send(await self.bot._(interaction, "moderation.emoji.unrestricted", name=emoji))
            return
        # remove duplicates
        roles = list(set(roles))
        await emoji.edit(roles=roles)
        # send success message
        roles_mentions = " ".join([x.mention for x in roles])
        await interaction.followup.send(
            await self.bot._(interaction, "moderation.emoji.emoji-valid", name=emoji, roles=roles_mentions, count=len(roles))
        )

    @emojis_main.command(name="clear")
    @app_commands.checks.cooldown(2, 10)
    async def emoji_clear(self, interaction: discord.Interaction, message: args.MessageArgument,
                          emoji: args.EmojiArgument | None = None):
        """Remove all reactions under a message
        If you specify an emoji, only reactions with that emoji will be deleted

        ..Example emoji clear

        ..Example emoji clear :axoblob:

        ..Doc moderator.html#emoji-manager"""
        if not interaction.channel.permissions_for(interaction.guild.me).manage_messages:
            return await interaction.followup.send(
                await self.bot._(interaction, "moderation.need-manage-messages"), ephemeral=True
            )
        await interaction.response.defer()
        if emoji:
            await message.clear_reaction(emoji)
        else:
            await message.clear_reactions()
        await interaction.followup.send(await self.bot._(interaction, "moderation.emoji.cleared"))

    @emojis_main.command(name="list")
    @app_commands.checks.cooldown(2, 20)
    async def emoji_list(self, interaction: discord.Interaction):
        """List every emoji of your server

        ..Example emojis list

        ..Doc moderator.html#emoji-manager"""
        structure = await self.bot._(interaction, "moderation.emoji.list")
        priv = "**"+await self.bot._(interaction, "moderation.emoji.private")+"**"
        title = await self.bot._(interaction, "moderation.emoji.list-title", guild=interaction.guild.name)
        # static emojis
        emotes = [
            structure.format(x, x.name, f"<t:{x.created_at.timestamp():.0f}>", priv if len(x.roles) > 0 else '')
            for x in interaction.guild.emojis
            if not x.animated
        ]
        # animated emojis
        emotes += [
            structure.format(x, x.name, f"<t:{x.created_at.timestamp():.0f}>", priv if len(x.roles) > 0 else '')
            for x in interaction.guild.emojis
            if x.animated
        ]

        class EmojisPaginator(Paginator):
            "Paginator for the emojis list"
            async def get_page_count(self) -> int:
                length = len(emotes)
                if length == 0:
                    return 1
                return ceil(length / 50)

            async def get_page_content(self, _: discord.Interaction, page: int):
                "Create one page"
                first_index = (page - 1) * 50
                last_index = min(first_index + 50, len(emotes))
                embed = discord.Embed(title=title, color=self.client.get_cog("ServerConfig").embed_color)
                for i in range(first_index, last_index, 10):
                    emotes_list: list[str] = []
                    for emote in emotes[i:i+10]:
                        emotes_list.append(emote)
                    field_name = f"{i+1}-{i + len(emotes_list)}"
                    embed.add_field(name=field_name, value="\n".join(emotes_list), inline=False)
                return {
                    "embed": embed
                }

        _quit = await self.bot._(interaction, "misc.quit")
        view = EmojisPaginator(self.bot, interaction.user, stop_label=_quit.capitalize())
        await view.send_init(interaction)


async def setup(bot):
    await bot.add_cog(EmojisManagement(bot))
