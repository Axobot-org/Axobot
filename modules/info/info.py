import importlib
import locale
from typing import Literal, get_args

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from core.arguments import args
from core.bot_classes import PRIVATE_GUILD_ID, Axobot
from core.checks import checks
from core.formatutils import FormatUtils
from modules.rss.src.rss_general import FeedObject

default_color = discord.Color(0x50e3c2)

importlib.reload(args)
importlib.reload(checks)

QueryTypesTyping = Literal[
    "member",
    "role",
    "emoji",
    "text-channel",
    "voice-channel",
    "forum",
    "stage-channel",
    "category",
    "user",
    "invite",
    "id",
]
QUERY_TYPES: tuple[str] = get_args(QueryTypesTyping)


class Info(commands.Cog):
    "Here you will find various useful commands to get information about anything"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "info"

    async def display_critical(self, interaction: discord.Interaction):
        return interaction.user.guild_permissions.manage_guild

    @app_commands.command(name="info")
    @app_commands.describe(
        query="A name, mention or ID",
        query_type="The type of the item to look for"
    )
    async def info_main(self, interaction: discord.Interaction, *, query: app_commands.Range[str, 1, 100], \
                        query_type: QueryTypesTyping | None = None):
        """Find informations about someone/something

        ..Example info role The VIP

        ..Example info 436835675304755200

        ..Example info :owo:

        ..Example info server

        ..Doc infos.html#info"""
        await interaction.response.defer()
        if query_type is None:
            if (guess_result := await self._guess_query_type(query, interaction)) is None:
                await interaction.followup.send(await self.bot._(interaction, "info.not-found", N=query))
                return
            query_type, resolved_query = guess_result
        else:
            ctx = await commands.Context.from_interaction(interaction)
            try:
                resolved_query = await self._convert_query(query, query_type, ctx)
            except (commands.BadArgument, ValueError):
                await interaction.followup.send(await self.bot._(interaction, "info.not-found", N=query))
                return

        if query_type == "member":
            await self.member_info(interaction, resolved_query)
        elif query_type == "role":
            await self.role_info(interaction, resolved_query)
        elif query_type == "user":
            await self.user_info(interaction, resolved_query)
        elif query_type == "emoji":
            await self.emoji_info(interaction, resolved_query)
        elif query_type == "text-channel":
            await self.textchannel_info(interaction, resolved_query)
        elif query_type == "voice-channel":
            await self.voicechannel_info(interaction, resolved_query)
        elif query_type == "forum":
            await self.forum_info(interaction, resolved_query)
        elif query_type == "stage-channel":
            await self.stagechannel_info(interaction, resolved_query)
        elif query_type == "category":
            await self.category_info(interaction, resolved_query)
        elif query_type == "invite":
            await self.invite_info(interaction, resolved_query)
        elif query_type == "server":
            await self.guild_info(interaction, resolved_query)
        elif query_type == "id":
            await self.snowflake_info(interaction, resolved_query)
        else:
            await interaction.followup.send(await self.bot._(interaction, "info.not-found", N=query))

    async def _guess_query_type(self, query: str, interaction: discord.Interaction):
        "Guess the query type from the given query"
        if query == "server":
            return "server", interaction.guild
        ctx = await commands.Context.from_interaction(interaction)
        for query_type in QUERY_TYPES:
            try:
                result = await self._convert_query(query, query_type, ctx)
            except commands.BadArgument:
                continue
            else:
                return query_type, result
        if await checks.is_bot_admin(interaction):
            try:
                return "server", await commands.GuildConverter().convert(ctx, query)
            except commands.BadArgument:
                pass

    async def _convert_query(self, query: str, query_type: QueryTypesTyping, ctx: commands.Context):
        "Try to convert the query to the given type"
        if query_type == "member":
            return await commands.MemberConverter().convert(ctx, query)
        if query_type == "role":
            return await commands.RoleConverter().convert(ctx, query)
        if query_type == "user":
            return await commands.UserConverter().convert(ctx, query)
        if query_type == "emoji":
            try:
                return await commands.EmojiConverter().convert(ctx, query)
            except commands.BadArgument:
                return await commands.PartialEmojiConverter().convert(ctx, query)
        if ctx.guild and query_type == "text-channel":
            return await commands.TextChannelConverter().convert(ctx, query)
        if ctx.guild and query_type == "voice-channel":
            return await commands.VoiceChannelConverter().convert(ctx, query)
        if ctx.guild and query_type == "forum":
            return await commands.ForumChannelConverter().convert(ctx, query)
        if ctx.guild and query_type == "stage-channel":
            return await commands.StageChannelConverter().convert(ctx, query)
        if ctx.guild and query_type == "category":
            return await commands.CategoryChannelConverter().convert(ctx, query)
        if query_type == "invite":
            return await commands.InviteConverter().convert(ctx, query)
        if query_type == "id":
            return await args.Snowflake.convert(ctx, query)
        raise ValueError(f"Unknown query type {query_type}")

    async def member_info(self, interaction: discord.Interaction, member: discord.Member):
        "Get info about a server member"
        lang = await self.bot._(interaction, "_used_locale")
        critical_info = await self.display_critical(interaction)
        since = await self.bot._(interaction, "misc.since")
        embed = discord.Embed(colour=member.color)
        embed.set_thumbnail(url=member.display_avatar.with_static_format("png"))
        embed.set_author(name=member.global_name or member.name, icon_url=member.display_avatar.with_format("png").url)
        # Name
        embed.add_field(name=(await self.bot._(interaction, "misc.name")).capitalize(),
                        value=f"{member.global_name or member.name} ({member.name})",
                        inline=True)
        # Nickname
        embed.add_field(name=await self.bot._(interaction, "info.info.member-0"),
                        value=member.nick if member.nick else str(await self.bot._(interaction.channel,"misc.none")).capitalize(),
                        inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=str(member.id))
        # Roles
        list_role = []
        for role in member.roles:
            if str(role) != "@everyone":
                list_role.append(role.mention)
        # Created at
        now = self.bot.utcnow()
        delta = abs(member.created_at - now)
        created_date = f"<t:{member.created_at.timestamp():.0f}>"
        created_since = await FormatUtils.time_delta(
            delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400
        )
        if member.created_at.day == now.day and member.created_at.month == now.month and member.created_at.year != now.year:
            created_date = "🎂 " + created_date
        embed.add_field(name=await self.bot._(interaction, "info.info.member-1"),
                        value=f"{created_date} ({since} {created_since})", inline=False)
        # Joined at
        if member.joined_at is not None:
            delta = abs(member.joined_at - now)
            join_date = f"<t:{member.joined_at.timestamp():.0f}>"
            since_date = await FormatUtils.time_delta(
                delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400
            )
            embed.add_field(name=await self.bot._(interaction, "info.info.member-2"),
                            value=f"{join_date} ({since} {since_date})", inline=False)
        if member.guild.member_count < 1e4:
            # Join position
            if len([x for x in interaction.guild.members if not x.joined_at]) > 0 and interaction.guild.large:
                await interaction.guild.chunk()
            position = str(
                sorted(interaction.guild.members, key=lambda m: m.joined_at).index(member) + 1
                ) + "/" + str(len(interaction.guild.members))
            embed.add_field(name=await self.bot._(interaction, "info.info.member-3"), value=position, inline=True)
        if self.bot.intents.presences:
            # Status
            status_value=(await self.bot._(interaction, f"misc.{member.status}")).capitalize()
            embed.add_field(name=await self.bot._(interaction, "info.info.member-4"), value=status_value, inline=True)
            # Activity
            if member.activity is not None and (member.activity.type == discord.ActivityType.custom and
                    member.activity.emoji is None and member.activity.name is None):
                # that's just a bug from discord apparently
                member.activity = None
            if member.activity is None:
                m_activity = str(
                    await self.bot._(interaction, "misc.activity.nothing")).capitalize()
            elif member.activity.type == discord.ActivityType.playing:
                m_activity = str(
                    await self.bot._(interaction, "misc.activity.play")).capitalize() + " " + member.activity.name
            elif member.activity.type == discord.ActivityType.streaming:
                m_activity = str(
                    await self.bot._(interaction, "misc.activity.stream")).capitalize() + " " + member.activity.name
            elif member.activity.type == discord.ActivityType.listening:
                m_activity = str(
                    await self.bot._(interaction, "misc.activity.listen")).capitalize() + " " + member.activity.name
            elif member.activity.type == discord.ActivityType.watching:
                m_activity = str(
                    await self.bot._(interaction, "misc.activity.watch")).capitalize() + " " + member.activity.name
            elif member.activity.type == discord.ActivityType.custom:
                emoji = str(member.activity.emoji if member.activity.emoji else '')
                m_activity = emoji + " " + (member.activity.name if member.activity.name else '')
                m_activity = m_activity.strip()
            else:
                m_activity="Error"
            if member.activity is None or member.activity.type != 4:
                embed.add_field(name=await self.bot._(interaction, "info.info.member-5"), value=m_activity,
                                inline=True)
            else:
                embed.add_field(name=await self.bot._(interaction, "info.info.member-8"), value=member.activity.state,
                                inline=True)
        # Bot
        if member.bot:
            botb = await self.bot._(interaction, "misc.yes")
            if member.public_flags.verified_bot:
                botb += " (" + await self.bot._(interaction, "misc.verified") + ")"
        else:
            botb = await self.bot._(interaction, "misc.no")
        embed.add_field(name="Bot", value=botb.capitalize())
        # Administrator
        if interaction.channel.permissions_for(member).administrator:
            admin = await self.bot._(interaction, "misc.yes")
        else:
            admin = await self.bot._(interaction, "misc.no")
        embed.add_field(name=await self.bot._(interaction, "info.info.member-6"), value=admin.capitalize(), inline=True)
        # Infractions count
        if critical_info and not member.bot and self.bot.database_online:
            embed.add_field(
                name=await self.bot._(interaction, "info.info.member-7"),
                value=await self.bot.get_cog("Cases").db_get_user_cases_count_from_guild(member.id, interaction.guild.id),
                inline=True)
        # Guilds count
        if member.bot:
            async with aiohttp.ClientSession(loop=self.bot.loop) as session:
                guilds_count = await self.bot.get_cog("Partners").get_bot_guilds(member.id, session)
                bot_owners = await self.bot.get_cog("Partners").get_bot_owners(member.id, session)
            if guilds_count is not None:
                guilds_count = await FormatUtils.format_nbr(guilds_count, lang)
                embed.add_field(name=str(await self.bot._(interaction,"misc.servers")).capitalize(), value=guilds_count)
            if bot_owners:
                embed.add_field(
                    name=(await self.bot._(interaction, "info.info.guild-1")).capitalize(),
                    value=", ".join([str(u) for u in bot_owners])
                )
        # Roles
        _roles = await self.bot._(interaction, "info.info.member-9") + f" [{len(list_role)}]"
        if len(list_role) > 0:
            list_role = list_role[:40]
            embed.add_field(name=_roles, value=", ".join(list_role), inline=False)
        else:
            embed.add_field(name=_roles, value=(await self.bot._(interaction, "misc.none")).capitalize(), inline=False)
        # member verification gate
        if member.pending:
            _waiting = await self.bot._(interaction, "info.info.member-10")
            embed.add_field(name=_waiting, value="\u200b", inline=False)
        await interaction.followup.send(embed=embed)

    async def role_info(self, interaction: discord.Interaction, role: discord.Role):
        "Get info about a server role"
        lang = await self.bot._(interaction, "_used_locale")
        embed = discord.Embed(colour=role.color)
        icon_url = role.guild.icon.with_static_format("png") if role.guild.icon else None
        embed.set_author(name=f"{await self.bot._(interaction, 'info.info.role-title')} '{role.name}'", icon_url=icon_url)
        since = await self.bot._(interaction, "misc.since")
        # Name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(),
                        value=role.mention, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"),
                        value=str(role.id), inline=True)
        # Color
        color_url = f"https://www.color-hex.com/color/{role.color.value:x}"
        embed.add_field(name=await self.bot._(interaction, "info.info.role-1"),
                        value=f"[{role.color}]({color_url})", inline=True)
        # Mentionnable
        if role.mentionable:
            mentionable = await self.bot._(interaction, "misc.yes")
        else:
            mentionable = await self.bot._(interaction, "misc.no")
        embed.add_field(name=await self.bot._(interaction, "info.info.role-2"),
                        value=mentionable.capitalize(), inline=True)
        # Members count
        embed.add_field(name=await self.bot._(interaction, "info.info.role-3"),
                        value=len(role.members), inline=True)
        # Specificities
        if role.tags:
            specificities = []
            if role.tags.is_available_for_purchase():
                specificities.append(await self.bot._(interaction, "info.info.role-specificities.purchaseable"))
            if role.tags.is_bot_managed() and role.tags.bot_id:
                specificities.append(await self.bot._(interaction, "info.info.role-specificities.bot_managed",
                                                      bot=f"<@{role.tags.bot_id}>"))
            if role.tags.is_guild_connection():
                specificities.append(await self.bot._(interaction, "info.info.role-specificities.guild_connection"))
            if role.tags.is_premium_subscriber():
                specificities.append(await self.bot._(interaction, "info.info.role-specificities.premium_sub"))
            if role.hoist:
                specificities.append(await self.bot._(interaction, "info.info.role-specificities.hoist"))
            if specificities:
                embed.add_field(name=await self.bot._(interaction, "info.info.role-specificities.field-name"),
                                value=" - ".join(specificities))
        # Created at
        delta = abs(role.created_at - self.bot.utcnow())
        created_date = f"<t:{role.created_at.timestamp():.0f}>"
        created_since = await FormatUtils.time_delta(delta.total_seconds(), lang=lang, year=True,
                                                     hour=delta.total_seconds() < 86400)
        embed.add_field(name=await self.bot._(interaction, "info.info.member-1"),
                        value=f"{created_date} ({since} {created_since})",
                        inline=False)
        # Hierarchy position
        embed.add_field(name=await self.bot._(interaction, "info.info.role-5"),
                        value=str(len(interaction.guild.roles) - role.position),
                        inline=True)
        # Unique member
        if len(role.members) == 1:
            embed.add_field(name=await self.bot._(interaction, "info.info.role-6"), value=role.members[0].mention, inline=True)
        await interaction.followup.send(embed=embed)

    async def user_info(self, interaction: discord.Interaction, user: discord.User):
        "Get info about any Discord user"
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        # is bot
        if user.bot:
            botb = await self.bot._(interaction, "misc.yes")
            if user.public_flags:
                botb += " (" + await self.bot._(interaction, "misc.verified") + ")"
        else:
            botb = await self.bot._(interaction, "misc.no")
        if interaction.guild:
            if user in interaction.guild.members:
                on_server = await self.bot._(interaction, "misc.yes")
            else:
                on_server = await self.bot._(interaction, "misc.no")
        embed = discord.Embed(colour=default_color)
        embed.set_thumbnail(url=user.display_avatar.with_static_format("png"))
        embed.set_author(name=user.display_name, icon_url=user.display_avatar.with_format("png"))
        # name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(),
                        value=f"{user.display_name} ({user.name})", inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=str(user.id))
        # created at
        now = self.bot.utcnow()
        delta = abs(user.created_at - now)
        created_date = f"<t:{user.created_at.timestamp():.0f}>"
        created_since = await FormatUtils.time_delta(
            delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400
        )
        if user.created_at.day == now.day and user.created_at.month == now.month and user.created_at.year != now.year:
            created_date = "🎂 " + created_date
        embed.add_field(name=await self.bot._(interaction, "info.info.member-1"),
                        value=f"{created_date} ({since} {created_since})", inline=False)
        # is bot
        embed.add_field(name="Bot", value=botb.capitalize())
        # is in server
        embed.add_field(name=await self.bot._(interaction, "info.info.user-0"), value=on_server.capitalize())
        if user.bot:
            async with aiohttp.ClientSession(loop=self.bot.loop) as session:
                guilds_count = await self.bot.get_cog("Partners").get_bot_guilds(user.id, session)
                bot_owners = await self.bot.get_cog("Partners").get_bot_owners(user.id, session)
            if guilds_count is not None:
                guilds_count = await FormatUtils.format_nbr(guilds_count, lang)
                embed.add_field(
                    name=str(await self.bot._(interaction, "misc.servers")).capitalize(),
                    value=guilds_count
                )
            if bot_owners:
                embed.add_field(
                    name=(await self.bot._(interaction, "info.info.guild-1")).capitalize(),
                    value=", ".join([str(u) for u in bot_owners])
                )
        await interaction.followup.send(embed=embed)

    async def emoji_info(self, interaction: discord.Interaction, emoji: discord.Emoji | discord.PartialEmoji):
        "Get info about any Discord emoji"
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        is_partial = isinstance(emoji, discord.PartialEmoji)
        embed = discord.Embed(colour=default_color)
        embed.set_thumbnail(url=emoji.url)
        embed.set_author(name=f"Emoji '{emoji.name}'", icon_url=emoji.url)
        # name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(), value=emoji.name, inline=True)
        # id
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=str(emoji.id))
        # animated
        if emoji.animated:
            animate = await self.bot._(interaction, "misc.yes")
        else:
            animate = await self.bot._(interaction, "misc.no")
        embed.add_field(name=await self.bot._(interaction, "info.info.emoji-0"), value=animate.capitalize())
        # guild name
        if not is_partial and emoji.guild != interaction.guild:
            embed.add_field(name=await self.bot._(interaction, "info.info.emoji-3"), value=emoji.guild.name)
        # string
        string = f"<a:{emoji.name}:{emoji.id}>" if emoji.animated else f"<:{emoji.name}:{emoji.id}>"
        embed.add_field(name=await self.bot._(interaction, "info.info.emoji-2"), value=f"`{string}`")
        # managed
        if not is_partial:
            if emoji.managed:
                manage = await self.bot._(interaction, "misc.yes")
            else:
                manage = await self.bot._(interaction, "misc.no")
            embed.add_field(name=await self.bot._(interaction, "info.info.emoji-1"), value=manage.capitalize())
        # created at
        if not is_partial:
            delta = abs(emoji.created_at - self.bot.utcnow())
            created_date = f"<t:{emoji.created_at.timestamp():.0f}>"
            created_since = await FormatUtils.time_delta(
                delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400
            )
            embed.add_field(
                name=await self.bot._(interaction, "info.info.member-1"),
                value=f"{created_date} ({since} {created_since})",
                inline=False
            )
        # allowed roles
        if not is_partial and len(emoji.roles) > 0:
            embed.add_field(
                name=await self.bot._(interaction, "info.info.emoji-4"),
                value=" ".join([x.mention for x in emoji.roles])
            )
        # uses
        infos_uses = await self.bot.get_cog("BotStats").db_get_emojis_info(emoji.id)
        if len(infos_uses) > 0:
            infos_uses = infos_uses[0]
            date = f"<t:{infos_uses['added_at'].timestamp():.0f}:D>"
            embed.add_field(
                name=await self.bot._(interaction, "info.info.emoji-5"),
                value=await self.bot._(interaction, "info.info.emoji-5v", nbr=infos_uses["count"], date=date)
            )
        await interaction.followup.send(embed=embed)

    async def textchannel_info(self, interaction: discord.Interaction, channel: discord.TextChannel):
        "Get informations about a text channel"
        if not channel.permissions_for(interaction.user).view_channel:
            await interaction.followup.send(await self.bot._(interaction, "info.cant-see-channel"))
            return
        lang = await self.bot._(interaction, "_used_locale")
        embed = discord.Embed(colour=default_color)
        icon_url = channel.guild.icon.with_format("png") if channel.guild.icon else None
        embed.set_author(
            name=await self.bot._(interaction, "info.info.textchan-5") + " '" + channel.name + "'",
            icon_url=icon_url)
        since = await self.bot._(interaction, "misc.since")
        # Name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(), value=channel.name, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=str(channel.id))
        # Category
        embed.add_field(name=await self.bot._(interaction, "info.info.textchan-0"), value=str(channel.category))
        # NSFW
        if channel.nsfw:
            nsfw = await self.bot._(interaction, "misc.yes")
        else:
            nsfw = await self.bot._(interaction, "misc.no")
        embed.add_field(name=await self.bot._(interaction, "info.info.textchan-2"), value=nsfw.capitalize())
        # Webhooks count
        try:
            web = len(await channel.webhooks())
        except discord.Forbidden:
            web = await self.bot._(interaction, "info.info.textchan-4")
        embed.add_field(name=await self.bot._(interaction, "info.info.textchan-3"), value=str(web))
        # Members nber
        embed.add_field(
            name=await self.bot._(interaction, "info.info.role-3"),
            value=str(len(channel.members)) + "/" + str(interaction.guild.member_count),
            inline=True
        )
        # Created at
        delta = abs(channel.created_at - self.bot.utcnow())
        created_date = f"<t:{channel.created_at.timestamp():.0f}>"
        created_since = await FormatUtils.time_delta(
            delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400)
        embed.add_field(
            name=await self.bot._(interaction, "info.info.member-1"),
            value=f"{created_date} ({since} {created_since})",
            inline=False
        )
        # Channel topic
        embed.add_field(
            name=await self.bot._(interaction, "info.info.textchan-1"),
            value=channel.topic if channel.topic else (await self.bot._(interaction, "misc.none")).capitalize(),
            inline=False
        )
        await interaction.followup.send(embed=embed)

    async def voicechannel_info(self, interaction: discord.Interaction, channel: discord.VoiceChannel):
        "Get informations about a voice channel"
        if not channel.permissions_for(interaction.user).view_channel:
            await interaction.followup.send(await self.bot._(interaction, "info.cant-see-channel"))
            return
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        embed = discord.Embed(colour=default_color)
        icon_url = channel.guild.icon.with_static_format("png") if channel.guild.icon else None
        embed.set_author(name=f"{await self.bot._(interaction, 'info.info.voicechan-0')} '{channel.name}'", icon_url=icon_url)
        # Name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(), value=channel.name, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=str(channel.id))
        # Category
        embed.add_field(name=await self.bot._(interaction, "info.info.textchan-0"), value=str(channel.category))
        # Created at
        delta = abs(channel.created_at - self.bot.utcnow())
        created_date = f"<t:{channel.created_at.timestamp():.0f}>"
        created_since = await FormatUtils.time_delta(
            delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400)
        embed.add_field(
            name=await self.bot._(interaction, "info.info.member-1"),
            value=f"{created_date} ({since} {created_since})",
            inline=False
        )
        # Bitrate
        embed.add_field(name="Bitrate", value=str(channel.bitrate/1000)+" kbps")
        # Members count
        users_limit = channel.user_limit if channel.user_limit > 0 else "∞"
        embed.add_field(
            name=await self.bot._(interaction, "info.info.role-3"),
            value=f"{len(channel.members)}/{users_limit}"
        )
        # Region
        if channel.rtc_region is not None:
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-2"), value=str(channel.rtc_region).capitalize())
        await interaction.followup.send(embed=embed)

    async def guild_info(self, interaction: discord.Interaction, guild: discord.Guild):
        "Get informations about the server"
        lang = await self.bot._(interaction, "_used_locale")
        critical_info = await self.display_critical(interaction)
        since = await self.bot._(interaction, "misc.since")
        _, bots, online, _ = await self.get_members_repartition(guild.members)

        desc = await self.bot.get_config(guild.id, "description")
        if (desc is None or len(desc) == 0) and guild.description is not None:
            desc = guild.description
        embed = discord.Embed(colour=default_color, description=desc)
        # Guild icon
        icon_url = guild.icon.with_static_format("png") if guild.icon else None
        embed.set_author(name=f"{await self.bot._(interaction, 'info.info.guild-0')} '{guild.name}'", icon_url=icon_url)
        embed.set_thumbnail(url=icon_url)
        # Guild banner
        if guild.banner is not None:
            embed.set_image(url=guild.banner)
        # Name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(), value=guild.name, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=str(guild.id))
        # Owner
        if guild.owner:
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-1"),
                            value=guild.owner.global_name or guild.owner.display_name)
        # Created at
        delta = abs(guild.created_at - self.bot.utcnow())
        created_date = f"<t:{guild.created_at.timestamp():.0f}>"
        created_since = await FormatUtils.time_delta(
            delta.total_seconds(), lang=lang, year=True, hour=delta.total_seconds() < 86400)
        embed.add_field(
            name=await self.bot._(interaction, "info.info.member-1"),
            value=f"{created_date} ({since} {created_since})",
            inline=False
        )
        # Member count
        if not self.bot.intents.presences:
            online = "?"
        embed.add_field(
            name=await self.bot._(interaction, "info.info.role-3"),
            value=await self.bot._(interaction, "info.info.guild-7", c=guild.member_count, b=bots, o=online)
        )
        # Channel count
        text_count = sum(1 for channel in guild.channels if isinstance(channel, discord.TextChannel | discord.ForumChannel))
        voice_count = sum(1 for channel in guild.channels if isinstance(channel, discord.VoiceChannel | discord.StageChannel))
        embed.add_field(
            name=await self.bot._(interaction, "info.info.guild-6"),
            value=await self.bot._(interaction, "info.info.guild-3", txt=text_count, voc=voice_count, cat=len(guild.categories))
        )
        # Invite count
        if guild.me.guild_permissions.manage_guild:
            len_invites = str(len(await guild.invites()))
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-12"), value=len_invites)
        # Emojis count
        c = {True: 0, False: 0}
        for x in guild.emojis:
            c[x.animated] += 1
        emojis_txt = await self.bot._(interaction, "info.info.guild-16", l=guild.emoji_limit, s=c[False], a=c[True])
        embed.add_field(name=await self.bot._(interaction, "info.info.guild-5"), value=emojis_txt)
        # AFK timeout
        embed.add_field(
            name=await self.bot._(interaction, "info.info.guild-10"),
            value=str(int(guild.afk_timeout/60))+" minutes"
        )
        # Splash url
        try:
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-15"), value=str(await guild.vanity_invite()))
        except (discord.errors.Forbidden, discord.errors.HTTPException):
            pass
        except Exception as err:
            self.bot.dispatch("error", err, interaction)
        # Premium subscriptions count
        if isinstance(guild.premium_subscription_count, int) and guild.premium_subscription_count > 0:
            subs_count = await self.bot._(interaction, "info.info.guild-13v",
                                          b=guild.premium_subscription_count, p=guild.premium_tier)
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-13"), value=subs_count)
        # Roles list
        try:
            if interaction.guild == guild:
                roles = [x.mention for x in guild.roles if len(x.members) > 1][1:]
            else:
                roles = [x.name for x in guild.roles if len(x.members) > 1][1:]
        except Exception as err:
            self.bot.dispatch("error", err, interaction)
            roles = guild.roles
        roles.reverse()
        if len(roles) == 0:
            temp = (await self.bot._(interaction, "misc.none")).capitalize()
            embed.add_field(
                name=await self.bot._(interaction, "info.info.guild-11.2", c=len(guild.roles)-1),
                value=temp)
        elif len(roles) > 20:
            embed.add_field(
                name=await self.bot._(interaction, "info.info.guild-11.1", c=len(guild.roles)-1),
                value=", ".join(roles[:20]))
        else:
            embed.add_field(
                name=await self.bot._(interaction, "info.info.guild-11.2", c=len(guild.roles)-1),
                value=", ".join(roles))
        # Limitations
        embed.add_field(name=await self.bot._(interaction, "info.info.guild-14"),
                        value=await self.bot._(interaction, "info.info.guild-14v",
                                               bit=round(guild.bitrate_limit/1000),
                                               fil=round(guild.filesize_limit/1.049e+6),
                                               emo=guild.emoji_limit,
                                               mem=guild.max_presences
                                               )
        )
        # Features
        if len(guild.features) > 0:
            async def tr(x: str):
                return await self.bot._(interaction, "info.info.guild-features." + x)
            features: list[str] = [await tr(x) for x in guild.features]
            features = [f.split('.')[-1] if '.' in f else f for f in features]
            embed.add_field(name=await self.bot._(interaction, "info.info.inv-9"), value=" - ".join(features))
        if critical_info:
            # A2F activation
            if guild.mfa_level:
                a2f = await self.bot._(interaction, "misc.yes")
            else:
                a2f = await self.bot._(interaction, "misc.no")
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-8"), value=a2f.capitalize())
            # Verification level
            embed.add_field(
                name=await self.bot._(interaction, "info.info.guild-9"),
                value=(await self.bot._(interaction, f"misc.{guild.verification_level}")).capitalize())
        await interaction.followup.send(embed=embed)

    async def invite_info(self, interaction: discord.Interaction, invite: discord.Invite):
        "Get informations about a Discord invite"
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        embed = discord.Embed(colour=default_color)
        icon_url = invite.guild.icon.with_static_format("png") if invite.guild.icon else None
        embed.set_author(name=f"{await self.bot._(interaction, 'info.info.inv-4')} '{invite.code}'", icon_url=icon_url)
        # Try to get the complete invite
        if invite.guild in self.bot.guilds:
            try:
                temp = [x for x in await invite.guild.invites() if x.id == invite.id]
                if len(temp) > 0:
                    invite = temp[0]
            except discord.errors.Forbidden:
                pass
            except Exception as err:
                self.bot.dispatch("error", err, interaction)
        # Invite URL
        embed.add_field(name=await self.bot._(interaction, "info.info.inv-0"), value=invite.url, inline=True)
        # Inviter
        embed.add_field(name=await self.bot._(interaction, "info.info.inv-1"),
                        value=(invite.inviter.global_name or invite.inviter.name)
                        if invite.inviter is not None else await self.bot._(interaction, "misc.unknown"))
        # Invite uses
        if invite.max_uses is not None and invite.uses is not None:
            if invite.max_uses == 0:
                uses = f"{invite.uses}/∞"
            else:
                uses = f"{invite.uses}/{invite.max_uses}"
            embed.add_field(name=await self.bot._(interaction, "info.info.inv-2"), value=uses)
        # Duration
        if invite.max_age is not None:
            max_age = str(invite.max_age) if invite.max_age != 0 else "∞"
            embed.add_field(name=await self.bot._(interaction, "info.info.inv-3"), value=max_age)
        if isinstance(invite.channel, discord.PartialInviteChannel | discord.abc.GuildChannel):
            # Guild name
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-0"), value=invite.guild.name)
            # Channel name
            embed.add_field(name=await self.bot._(interaction, "info.info.textchan-5"), value="#"+invite.channel.name)
            # Guild icon
            if invite.guild.icon:
                embed.set_thumbnail(url=icon_url)
            # Guild ID
            embed.add_field(name=await self.bot._(interaction, "info.info.inv-6"), value=invite.guild.id)
            # Members count
            if invite.approximate_member_count:
                embed.add_field(name=await self.bot._(interaction, "info.info.inv-7"), value=invite.approximate_member_count)
        # Guild banner
        if invite.guild.banner is not None:
            embed.set_image(url=invite.guild.banner)
        # Guild description
        if invite.guild.description is not None and len(invite.guild.description) > 0:
            embed.add_field(name=await self.bot._(interaction, "info.info.inv-8"), value=invite.guild.description)
        # Guild features
        if len(invite.guild.features) > 0:
            async def tr(x: str):
                return await self.bot._(interaction, "info.info.guild-features." + x)
            features: list[str] = [await tr(x) for x in invite.guild.features]
            features = [f.split('.')[-1] if '.' in f else f for f in features]
            embed.add_field(name=await self.bot._(interaction, "info.info.inv-9"), value=" - ".join(features))
        # Creation date
        if invite.created_at is not None:
            created_at = f"<t:{invite.created_at.timestamp():.0f}>"
            show_hour = (self.bot.utcnow() - invite.created_at).days < 1
            delta = await FormatUtils.time_delta(invite.created_at, self.bot.utcnow(), lang=lang, year=True, hour=show_hour)
            embed.add_field(
                name=await self.bot._(interaction, "info.info.member-1"),
                value=f"{created_at} ({since} {delta})",
                inline=False
            )
        await interaction.followup.send(embed=embed)

    async def category_info(self, interaction: discord.Interaction, category: discord.CategoryChannel):
        "Get informations about a category"
        if not category.permissions_for(interaction.user).view_channel:
            await interaction.followup.send(await self.bot._(interaction, "info.cant-see-channel"))
            return
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        tchan = 0
        vchan = 0
        for channel in category.channels:
            if isinstance(channel, discord.TextChannel):
                tchan += 1
            elif isinstance(channel, discord.VoiceChannel):
                vchan +=1
        embed = discord.Embed(colour=default_color)
        icon_url = category.guild.icon.with_static_format("png") if category.guild.icon else None
        embed.set_author(name=f"{await self.bot._(interaction,'info.info.categ-0')} '{category.name}'", icon_url=icon_url)
        # Category name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(), value=category.name, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=category.id)
        # Position
        embed.add_field(
            name=await self.bot._(interaction, "info.info.categ-1"),
            value=f"{category.position+1}/{len(category.guild.categories)}"
        )
        # Channels count
        embed.add_field(
            name=await self.bot._(interaction, "info.info.guild-6"),
            value=await self.bot._(interaction, "info.info.categ-2", txt=tchan, voc=vchan)
        )
        # Created at
        created_at = f"<t:{category.created_at.timestamp():.0f}>"
        show_hour = (self.bot.utcnow() - category.created_at).days < 1
        delta = await FormatUtils.time_delta(category.created_at, self.bot.utcnow(), lang=lang, year=True, hour=show_hour)
        embed.add_field(
            name=await self.bot._(interaction, "info.info.member-1"),
            value=f"{created_at} ({since} {delta})",
            inline=False
        )
        await interaction.followup.send(embed=embed)

    async def forum_info(self, interaction: discord.Interaction, forum: discord.ForumChannel):
        "Get informations about a forum channel"
        if not forum.permissions_for(interaction.user).view_channel:
            await interaction.followup.send(await self.bot._(interaction, "info.cant-see-channel"))
            return
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        embed = discord.Embed(colour=default_color)
        icon_url = forum.guild.icon.with_static_format("png") if forum.guild.icon else None
        title = await self.bot._(interaction, "info.info.forum.title", name=forum.name)
        embed.set_author(name=title, icon_url=icon_url)
        # Name
        embed.add_field(name=str(await self.bot._(interaction, "misc.name")).capitalize(), value=forum.name, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=forum.id)
        # Category
        if forum.category:
            embed.add_field(name=await self.bot._(interaction, "info.info.textchan-0"), value=forum.category.name)
        # NSFW
        if forum.nsfw:
            nsfw = await self.bot._(interaction, "misc.yes")
        else:
            nsfw = await self.bot._(interaction, "misc.no")
        embed.add_field(name=await self.bot._(interaction, "info.info.textchan-2"), value=nsfw.capitalize())
        # Created at
        created_at = f"<t:{forum.created_at.timestamp():.0f}>"
        show_hour = (self.bot.utcnow() - forum.created_at).days < 1
        delta = await FormatUtils.time_delta(forum.created_at, self.bot.utcnow(), lang=lang, year=True, hour=show_hour)
        embed.add_field(
            name=await self.bot._(interaction, "info.info.member-1"),
            value=f"{created_at} ({since} {delta})")
        if forum.permissions_for(interaction.user).read_messages:
            # Tags
            if forum.available_tags:
                tags_list = []
                for tag in forum.available_tags:
                    if tag.emoji and tag.emoji.is_unicode_emoji():
                        tags_list.append(f"`{tag.emoji} {tag.name}`")
                    else:
                        tags_list.append(f"`{tag.name}`")
                tags = ", ".join(tags_list)
                embed.add_field(name=await self.bot._(interaction, "info.info.forum.tags"), value=tags)
            # Default sort order
            if forum.default_sort_order == discord.ForumOrderType.latest_activity:
                sort_order = await self.bot._(interaction, "info.info.forum.sort-order-latest")
            elif forum.default_sort_order == discord.ForumOrderType.creation_date:
                sort_order = await self.bot._(interaction, "info.info.forum.sort-order-creation")
            elif forum.default_sort_order is None:
                sort_order = await self.bot._(interaction, "info.info.forum.sort-order-none")
            else:
                sort_order = None
                self.bot.dispatch("error", ValueError(f"Unknown forum sort order type: {forum.default_sort_order}"))
            if sort_order:
                sort_order_title = await self.bot._(interaction, "info.info.forum.sort-order")
                embed.add_field(name=sort_order_title, value=sort_order)
            # Default emoji
            if forum.default_reaction_emoji:
                embed.add_field(name=await self.bot._(interaction, "info.info.forum.default-emoji"),
                                value=forum.default_reaction_emoji)
            # Post slowmode
            if forum.slowmode_delay:
                slowmode = await FormatUtils.time_delta(forum.slowmode_delay, lang=lang, year=True, hour=True)
            else:
                slowmode = (await self.bot._(interaction, "misc.none")).capitalize()
            embed.add_field(name=await self.bot._(interaction, "info.info.forum.slowmode"), value=slowmode)
            # Guidelines
            if forum.topic:
                if len(forum.topic) > 400:
                    guidelines = forum.topic[:400] + "..."
                else:
                    guidelines = forum.topic
            else:
                guidelines = (await self.bot._(interaction, "misc.none")).capitalize()
            embed.add_field(name=await self.bot._(interaction, "info.info.forum.guidelines"), value=guidelines, inline=False)
        await interaction.followup.send(embed=embed)

    async def stagechannel_info(self, interaction: discord.Interaction, stage: discord.StageChannel):
        "Get information about a stage channel"
        if not stage.permissions_for(interaction.user).view_channel:
            await interaction.followup.send(await self.bot._(interaction, "info.cant-see-channel"))
            return
        lang = await self.bot._(interaction, "_used_locale")
        since = await self.bot._(interaction, "misc.since")
        embed = discord.Embed(colour=default_color)
        icon_url = stage.guild.icon.with_static_format("png") if stage.guild.icon else None
        title = await self.bot._(interaction, "info.info.stage.title", name=stage.name)
        embed.set_author(name=title, icon_url=icon_url)
        # Name
        embed.add_field(name=(await self.bot._(interaction, "misc.name")).capitalize(), value=stage.name, inline=True)
        # ID
        embed.add_field(name=await self.bot._(interaction, "info.info.role-0"), value=stage.id)
        # Category
        if stage.category:
            embed.add_field(name=await self.bot._(interaction, "info.info.textchan-0"), value=stage.category.name)
        # NSFW
        if stage.nsfw:
            nsfw = await self.bot._(interaction, "misc.yes")
        else:
            nsfw = await self.bot._(interaction, "misc.no")
        embed.add_field(name=await self.bot._(interaction, "info.info.textchan-2"), value=nsfw.capitalize())
        # Created at
        created_at = f"<t:{stage.created_at.timestamp():.0f}>"
        show_hour = (self.bot.utcnow() - stage.created_at).days < 1
        delta = await FormatUtils.time_delta(stage.created_at, self.bot.utcnow(), lang=lang, year=True, hour=show_hour)
        embed.add_field(
            name=await self.bot._(interaction, "info.info.member-1"),
            value=f"{created_at} ({since} {delta})")
        # Bitrate
        embed.add_field(name="Bitrate", value=str(stage.bitrate/1000)+" kbps")
        # Members count
        users_limit = stage.user_limit if stage.user_limit > 0 else "∞"
        embed.add_field(
            name=await self.bot._(interaction, "info.info.role-3"),
            value=f"{len(stage.members)}/{users_limit}"
        )
        # Region
        if stage.rtc_region is not None:
            embed.add_field(name=await self.bot._(interaction, "info.info.guild-2"), value=str(stage.rtc_region).capitalize())
        # Moderators
        if stage.moderators:
            embed.add_field(name=await self.bot._(interaction, "info.info.stage.moderators"),
                            value=", ".join(m.display_name for m in stage.moderators))
        await interaction.followup.send(embed=embed)

    async def snowflake_info(self, interaction: discord.Interaction, snowflake: args.Snowflake):
        "Get information about any Discord-generated ID"
        date = f"<t:{snowflake.date.timestamp():.0f}>"
        embed = discord.Embed(color=default_color)
        embed.add_field(name=await self.bot._(interaction, "info.info.snowflake-0"), value=date)
        embed.add_field(name=await self.bot._(interaction, "info.info.snowflake-2"), value=round(snowflake.date.timestamp()))
        embed.add_field(name=await self.bot._(interaction, "info.info.snowflake-6"), value=len(str(snowflake.id)))
        embed.add_field(name=await self.bot._(interaction, "info.info.snowflake-1"), value=snowflake.binary, inline=False)
        embed.add_field(name=await self.bot._(interaction, "info.info.snowflake-3"), value=snowflake.worker_id)
        embed.add_field(name=await self.bot._(interaction, "info.info.snowflake-4"), value=snowflake.process_id)
        await interaction.followup.send(embed=embed)


    async def get_members_repartition(self, members: list[discord.Member]):
        """Get number of total/online/bots members in a selection"""
        bots = online = total = unverified = 0
        for u in members:
            if u.bot:
                bots += 1
            if u.status != discord.Status.offline:
                online += 1
            if u.pending:
                unverified += 1
            total += 1
        return total, bots, online, unverified


    find_main = discord.app_commands.Group(
        name="find",
        description="Help the bot staff to find things",
        guild_ids=[PRIVATE_GUILD_ID.id]
    )

    @find_main.command(name="user")
    @discord.app_commands.check(checks.is_support_staff)
    async def find_user(self, interaction: discord.Interaction, user: discord.User):
        "Find any user visible by the bot"
        # Servers list
        servers_in: list[str] = []
        owned, membered = 0, 0
        await interaction.response.defer()
        if hasattr(user, "mutual_guilds"):
            for s in user.mutual_guilds:
                if s.owner==user:
                    servers_in.append(f":crown: {s.name} ({s.id})")
                    owned += 1
                else:
                    servers_in.append(f"- {s.name} ({s.id})")
                    membered += 1
            if len("\n".join(servers_in)) > 1020:
                servers_in = [f"{owned} owned servers, member of {membered} others"]
        else:
            servers_in = []
        # XP card
        xp_card = await self.bot.get_cog("Utilities").get_xp_style(user)
        # Flags
        userflags = await self.bot.get_cog("Users").get_userflags(user)
        if await self.bot.get_cog("Admin").check_if_admin(user):
            userflags.append("admin")
        if len(userflags) == 0:
            userflags = ["None"]
        # Votes
        votes = await self.bot.get_cog("Utilities").check_votes(user.id)
        votes = " - ".join([f"[{x[0]}]({x[1]})" for x in votes])
        if len(votes) == 0:
            votes = "Nowhere"
        # Languages
        disp_lang = list()
        if hasattr(user, "mutual_guilds"):
            for lang in await self.bot.get_cog("Utilities").get_languages(user):
                disp_lang.append(f"{lang[0]} ({lang[1]*100:.0f}%)")
        if len(disp_lang) == 0:
            disp_lang = ["Unknown"]
        # User name
        if user.bot and discord.PublicUserFlags.verified_bot in user.public_flags:
            user_name = user.name + "<:botverified:1093225375963811920>"
        elif user.bot:
            user_name = user.name + "<:bot:1093225377377308692>"
        else:
            user_name = user.name
        # XP sus
        xp_sus = "Unknown"
        if xp_cog := self.bot.get_cog("Xp"):
            if xp_cog.sus is not None:
                xp_sus = str(user.id in xp_cog.sus)
        # ----
        if interaction.guild is None:
            color = None
        else:
            color = None if interaction.guild.me.color.value == 0 else interaction.guild.me.color

        embed = discord.Embed(title=user_name, color=color)
        embed.set_thumbnail(url=user.display_avatar.replace(static_format="png", size=1024))
        embed.add_field(name="ID", value=user.id)
        if user.global_name:
            embed.add_field(name="Display name", value=user.global_name)
        embed.add_field(name="Flags", value=" - ".join(userflags), inline=False)
        embed.add_field(name=f"Servers ({len(servers_in)})", value="\n".join(servers_in) if servers_in else "No server")
        embed.add_field(name="Language", value="\n".join(disp_lang))
        embed.add_field(name="XP card", value=xp_card)
        embed.add_field(name="Upvoted the bot?", value=votes)
        embed.add_field(name="XP sus?", value=xp_sus)

        await interaction.followup.send(embed=embed)

    @find_main.command(name="guild")
    @discord.app_commands.check(checks.is_support_staff)
    @discord.app_commands.describe(guild="The server name or ID")
    async def find_guild(self, interaction: discord.Interaction, guild: str):
        "Find any guild where the bot is"
        await interaction.response.defer()
        if guild.isnumeric():
            guild: discord.Guild = self.bot.get_guild(int(guild))
        else:
            for x in self.bot.guilds:
                if x.name == guild:
                    guild = x
                    break
        if isinstance(guild, str) or guild is None:
            await interaction.followup.send("Unknown server")
            return
        # Bots
        bots = len([x for x in guild.members if x.bot])
        # Lang
        lang: str = await self.bot.get_config(guild.id, "language")
        # Roles rewards
        rr_len: int = await self.bot.get_config(guild.id, "rr_max_number")
        rr_len: str = "{}/{}".format(len(await self.bot.get_cog("Xp").rr_list_role(guild.id)), rr_len)
        # Streamers
        if twitch_cog := self.bot.get_cog("Twitch"):
            streamers_len: int =  await self.bot.get_config(guild.id, "streamers_max_number")
            streamers_len: str = "{}/{}".format(await twitch_cog.db_get_guild_subscriptions_count(guild.id), streamers_len)
        else:
            streamers_len = "Not available"
        # Rss
        rss_len: int = await self.bot.get_config(guild.id, "rss_max_number")
        if rss_cog := self.bot.get_cog("Rss"):
            rss_numb = "{}/{}".format(len(await rss_cog.db_get_guild_feeds(guild.id)), rss_len)
        else:
            rss_numb = "Not available"
        # Join date
        joined_at = f"<t:{guild.me.joined_at.timestamp():.0f}>"
        # ----
        if interaction.guild is None:
            color = None
        else:
            color = None if interaction.guild.me.color.value == 0 else interaction.guild.me.color
        emb = discord.Embed(title=guild.name, color=color)
        if guild.icon:
            emb.set_thumbnail(url=guild.icon.with_static_format("png"))
        emb.add_field(name="ID", value=guild.id)
        if guild.owner:
            emb.add_field(name="Owner", value=f"{guild.owner} ({guild.owner_id})", inline=False)
        else:
            emb.add_field(name="Owner", value="Unknown", inline=False)
        emb.add_field(name="Joined at", value=joined_at, inline=False)
        emb.add_field(name="Members", value=f"{guild.member_count} (including {bots} bots)")
        emb.add_field(name="Language", value=lang)
        emb.add_field(name="RSS feeds count", value=rss_numb)
        emb.add_field(name="Roles rewards count", value=rr_len)
        emb.add_field(name="Streamers count", value=streamers_len)
        await interaction.followup.send(embed=emb)

    @find_main.command(name="channel")
    @discord.app_commands.check(checks.is_support_staff)
    @discord.app_commands.describe(channel="The ID/name of the channel to look for")
    async def find_channel(self, interaction: discord.Interaction, channel: str):
        "Find any channel from any server where the bot is"
        await interaction.response.defer()
        ctx = await commands.Context.from_interaction(interaction)
        try:
            resolved_channel = await commands.GuildChannelConverter().convert(ctx, channel)
        except commands.ChannelNotFound:
            await interaction.followup.send("Unknonwn channel")
            return
        if interaction.guild is None:
            color = None
        else:
            color = None if interaction.guild.me.color.value == 0 else interaction.guild.me.color
        emb = discord.Embed(title="#"+resolved_channel.name, color=color)
        emb.add_field(name="ID", value=resolved_channel.id)
        emb.add_field(name="Server", value=f"{resolved_channel.guild.name} ({resolved_channel.guild.id})", inline=False)
        emb.add_field(name="Type", value=resolved_channel.type.name.capitalize())
        await interaction.followup.send(embed=emb)

    @find_main.command(name="role")
    @discord.app_commands.check(checks.is_support_staff)
    @discord.app_commands.describe(role_name="The ID/name of the role to look for")
    async def find_role(self, interaction: discord.Interaction, role_name: str):
        "Find any role from any server where the bot is"
        await interaction.response.defer()
        every_roles: list[discord.Role] = []
        for serv in self.bot.guilds:
            every_roles += serv.roles
        role = discord.utils.find(lambda item: role_name in {str(item.id), item.name, item.mention}, every_roles)
        if role is None:
            await interaction.followup.send("Unknown role")
            return
        if interaction.guild is None:
            color = None
        else:
            color = None if interaction.guild.me.color.value == 0 else interaction.guild.me.color
        emb = discord.Embed(title="@"+role.name, color=color)
        emb.add_field(name="ID", value=role.id)
        emb.add_field(name="Server", value=f"{role.guild.name} ({role.guild.id})", inline=False)
        emb.add_field(name="Members", value=len(role.members))
        emb.add_field(name="Colour", value=str(role.colour))
        await interaction.followup.send(embed=emb)

    @find_main.command(name="rss")
    @discord.app_commands.check(checks.is_support_staff)
    async def find_rss(self, interaction: discord.Interaction, feed_id: int):
        "Find any active or inactive RSS feed"
        await interaction.response.defer()
        feed: FeedObject = await self.bot.get_cog("Rss").db_get_feed(feed_id)
        if feed is None:
            await interaction.followup.send("Unknown RSS feed")
            return
        guild = self.bot.get_guild(feed.guild_id)
        if guild is None:
            g = f"Unknown ({feed.guild_id})"
        else:
            g = f"`{guild.name}`\n{guild.id}"
        channel = self.bot.get_channel(feed.channel_id)
        if channel is None:
            c = f"Unknown ({feed.channel_id})"
        else:
            c = f"`{channel.name}`\n{channel.id}"
        if feed.date is None:
            d = "never"
        else:
            d = f"<t:{feed.date.timestamp():.0f}>"
        if interaction.guild is None:
            color = None
        else:
            color = None if interaction.guild.me.color.value == 0 else interaction.guild.me.color
        specificities = []
        if not feed.enabled:
            specificities.append("Disabled")
        if feed.use_embed:
            specificities.append("Use embed")
        if feed.silent_mention:
            specificities.append("Silent mention")
        if feed.role_ids:
            specificities.append(f"{len(feed.role_ids)} role mention")
        emb = discord.Embed(title=f"RSS #{feed_id}", color=color)
        emb.add_field(name="Server", value=g)
        if isinstance(channel, discord.Thread):
            emb.add_field(name="Thread", value=c)
        else:
            emb.add_field(name="Channel", value=c)
        emb.add_field(name="URL", value=feed.link, inline=False)
        emb.add_field(name="Type", value=feed.type)
        emb.add_field(name="Last post", value=d)
        if specificities:
            emb.add_field(name="Specificities", value=" - ".join(specificities))
        emb.add_field(name="Recent errors", value=str(feed.recent_errors))
        await interaction.followup.send(embed=emb)

    @app_commands.command(name="membercount")
    @app_commands.guild_only()
    async def membercount(self, interaction: discord.Interaction):
        """Get some stats on the number of server members

        ..Doc infos.html#membercount"""
        await interaction.response.defer()
        total, bots_count, online_count, unverified = await self.get_members_repartition(interaction.guild.members)
        humans_count = total - bots_count
        def get_count(nbr: int):
            if 0 < nbr / total < 0.01:
                return "< 1"
            if 1 > nbr/total > 0.99:
                return "> 99"
            return round(nbr*100/total)
        humans_percent = get_count(humans_count)
        bots_percent = get_count(bots_count)
        online_percent = get_count(online_count)
        unverified_percent = get_count(unverified)
        fields = [
            (await self.bot._(interaction, "info.membercount-0"), total),
            (await self.bot._(interaction, "info.membercount-2"), f"{humans_count} ({humans_percent}%)"),
            (await self.bot._(interaction, "info.membercount-1"), f"{bots_count} ({bots_percent}%)"),
        ]
        if self.bot.intents.presences:
            fields.append((await self.bot._(interaction, "info.membercount-3"), f"{online_count} ({online_percent}%)"))
        if "MEMBER_VERIFICATION_GATE_ENABLED" in interaction.guild.features:
            fields.append((await self.bot._(interaction, "info.membercount-4"), f"{unverified} ({unverified_percent}%)"))
        embed = discord.Embed(colour=interaction.guild.me.color)
        for field in fields:
            embed.add_field(name=field[0], value=field[1], inline=True)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    locale.setlocale(locale.LC_ALL, '')
    await bot.add_cog(Info(bot))
