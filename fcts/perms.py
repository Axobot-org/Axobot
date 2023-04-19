import typing

import discord
from discord import app_commands
from discord.ext import commands
from fcts.args import RawPermissionValue
from libs.bot_classes import MyContext, Axobot
from libs.paginator import cut_text


VoiceChannelTypes = typing.Union[
    discord.VoiceChannel,
    discord.StageChannel
]

TextChannelTypes = typing.Union[
    discord.TextChannel,
    discord.CategoryChannel,
    discord.ForumChannel,
    discord.Thread
]

AcceptableChannelTypes = typing.Optional[typing.Union[
    VoiceChannelTypes,
    TextChannelTypes,
]]
AcceptableTargetTypes = typing.Optional[typing.Union[
    discord.Member,
    discord.Role,
    RawPermissionValue
]]


class TargetConverter(commands.Converter):
    async def convert(self, ctx: MyContext, argument: str) -> AcceptableTargetTypes:
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.MemberNotFound:
            pass

        try:
            return await commands.RoleConverter().convert(ctx, argument)
        except commands.RoleNotFound:
            pass

        try:
            return await RawPermissionValue().convert(ctx, argument)
        except commands.BadArgument:
            pass

        raise commands.BadArgument(f"Could not find a member, role or permission value with the name {argument}")

class Perms(commands.Cog):
    """Cog with a single command, allowing you to see the permissions of a member or a role in a channel."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "perms"
        chan_perms = [key for key,value in discord.Permissions().all_channel() if value]
        self.perms_name = {'general':[key for key,value in discord.Permissions().general() if value],
            'text':[key for key,value in discord.Permissions().text() if value],
            'voice':[key for key,value in discord.Permissions().voice() if value]}
        self.perms_name['common_channel'] = [x for x in chan_perms if x in self.perms_name['general']]

    async def collect_permissions(self, ctx: MyContext, permissions: discord.Permissions, channel) -> list[tuple[str, str]]:
        "Iterate over the given permissions and return the needed ones, formatted"
        result = []
        emojis_cog = self.bot.emojis_manager
        # if target is admin, only display that
        if permissions.administrator:
            perm_tr = await self.bot._(ctx.guild.id, "permissions.list.administrator")
            if "permissions.list." in perm_tr: # unsuccessful translation
                perm_tr = "Administrator"
            return [(emojis_cog.customs['green_check'], perm_tr)]
        # else
        common_perms = self.perms_name['common_channel']
        text_perms = self.perms_name['text'] + common_perms
        voice_perms = self.perms_name['voice'] + common_perms
        for perm_id, value in permissions:
            if not (
                channel is None
                or
                (perm_id in text_perms and isinstance(channel, typing.get_args(TextChannelTypes)))
                or
                (perm_id in voice_perms and isinstance(channel, typing.get_args(VoiceChannelTypes)))
            ):
                continue
            perm_tr = await self.bot._(ctx.guild.id, "permissions.list."+perm_id)
            if "permissions.list." in perm_tr:  # unsuccessful translation
                perm_tr = perm_id.replace('_', ' ').title()
            if value:
                result.append((emojis_cog.customs['green_check'], perm_tr))
            else:
                result.append((emojis_cog.customs['red_cross'], perm_tr))
        return result

    @commands.hybrid_command(name='permissions', aliases=['perms'])
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(channel="The channel to check the permissions in", target="The member or role to check the permissions of, or an integer/binary value")
    @commands.guild_only()
    async def check_permissions(self, ctx: MyContext, channel:AcceptableChannelTypes=None, *, target: typing.Annotated[AcceptableTargetTypes, TargetConverter]=None):
        """Check the permissions assigned to a member/role
        By default, it will calculate the author's permissions at the server level.
        You can also choose to view the permissions associated to a raw integer/binary value (in which case channel will be ignored)

        ..Example permissions #announcements everyone

        ..Example permissions Axobot

        ..Example permissions 0b1001

        ..Doc infos.html#permissions"""
        if ctx.current_argument and target is None and channel is None:
            await ctx.send(await self.bot._(ctx.guild.id, "permissions.invalid_arg", arg=ctx.current_argument))
            return
        if target is None:
            target = ctx.author
        if isinstance(target, discord.Member):
            if channel is None:
                perms = target.guild_permissions
            else:
                perms = channel.permissions_for(target)
            col = target.color
            avatar = target.display_avatar.replace(static_format="png", size=256)
            name = await self.bot._(ctx, "permissions.target.member", name=str(target))
        elif isinstance(target, discord.Role):
            if channel is None:
                perms = target.permissions
            else:
                perms = channel.permissions_for(target)
            col = target.color
            avatar = ctx.guild.icon.replace(format='png', size=256) if ctx.guild.icon else None
            name = await self.bot._(ctx, "permissions.target.role", name=str(target))
        elif isinstance(target, int):
            perms = discord.Permissions(target)
            col = discord.Color.blurple()
            avatar = None
            name = await self.bot._(ctx, "permissions.target.value", value=f"{target} | {bin(target)}")
        else:
            self.bot.dispatch("error", TypeError(f"Unknown target type: {type(target)}"), ctx)
            return

        perms_list = await self.collect_permissions(ctx, perms, channel)
        perms_list.sort(key=lambda x: x[1])
        perms_list = [''.join(perm) for perm in perms_list]
        if ctx.can_send_embed:
            if isinstance(target, int):
                desc = None
            elif channel is None:
                desc = await self.bot._(ctx, "permissions.channel.general")
            elif isinstance(channel, discord.CategoryChannel):
                desc = await self.bot._(ctx, "permissions.channel.category", name=channel.name)
            else:
                desc = await self.bot._(ctx, "permissions.channel.channel", mention=channel.mention)

            embed = discord.Embed(color=col, description=desc)
            paragraphs = cut_text(perms_list, max_size=21)
            for paragraph in paragraphs:
                embed.add_field(name=self.bot.zws, value=paragraph)

            _whatisthat = await self.bot._(ctx, "permissions.whatisthat")
            embed.add_field(name=self.bot.zws, value=f'[{_whatisthat}](https://axobot.readthedocs.io/en/latest/perms.html)',
                            inline=False)
            embed.set_author(name=name, icon_url=avatar)
            embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=embed)
        else:
            txt = await self.bot._(ctx.guild.id,"permissions.title", name=name) + "\n".join(perms_list)
            allowed_mentions = discord.AllowedMentions.none()
            await ctx.send(txt, allowed_mentions=allowed_mentions)


async def setup(bot):
    await bot.add_cog(Perms(bot))
