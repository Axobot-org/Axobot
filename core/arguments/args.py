import inspect
import re
from typing import TYPE_CHECKING, Type

import discord
from discord.ext import commands

from core.arguments import errors as arguments_errors
from core.formatutils import FormatUtils

if TYPE_CHECKING:
    from core.bot_classes import Axobot, MyContext

def UnionTransformer(*types) -> Type[discord.app_commands.Transformer]: # pylint: disable=invalid-name
    "Convert arguments to one of the provided types"

    for type_ in types:
        if not (
            isinstance(type_, str)
            or type_ is None
            or inspect.isclass(type_) and issubclass(type_, discord.app_commands.Transformer)
        ):
            raise TypeError(f"unsupported type annotation: {type_!r}")

    class UnionTransformerClass(discord.app_commands.Transformer): # pylint: disable=abstract-method
        "Convert arguments to one of the provided types"

        async def transform(self, interaction, value, /):
            for type_ in types:
                if isinstance(type_, str) and type_ == value:
                    return value
                if type_ is None and value is None:
                    return None
                if inspect.isclass(type_) and issubclass(type_, discord.app_commands.Transformer):
                    try:
                        return await type_().transform(interaction, value)
                    except commands.errors.BadArgument:
                        continue
            raise commands.errors.BadArgument(value)
    return UnionTransformerClass


class CardStyleTransformer(discord.app_commands.Transformer):
    "Converts a string to a valid XP card style"

    async def transform(self, interaction: discord.Interaction["Axobot"], value, /):
        "Do the conversion"
        if value in await interaction.client.get_cog("Utilities").allowed_card_styles(interaction.user):
            return value
        raise arguments_errors.InvalidCardStyleError(value)

    async def autocomplete(self, interaction, value, /):
        raise NotImplementedError()

CardStyleArgument = discord.app_commands.Transform[str, CardStyleTransformer]


class BotOrGuildInviteTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    """Converts a string to a bot invite or a guild invite"""

    async def transform(self, interaction: discord.Interaction["Axobot"], value, /):
        "Do the conversion"
        answer = None
        r_invite = re.search(
            r"^https://discord(?:app)?\.com/(?:api/)?oauth2/authorize\?(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+)(?:&(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+))*$",
            value
        )
        if r_invite is None:
            r_invite = re.search(r"(?:discord\.gg|discordapp\.com/invite)/([^\s/]+)", value)
            if r_invite is not None:
                try:
                    invite = await interaction.client.fetch_invite(r_invite.group(1))
                except discord.NotFound:
                    pass
                else:
                    if invite.type == discord.enums.InviteType.guild:
                        answer = invite
        else:
            if (r_invite.group(2) or r_invite.group(4)) and (r_invite.group(1) or r_invite.group(3)):
                scopes = r_invite.group(2).split('+') if r_invite.group(2) else r_invite.group(4).split('+')
                if "bot" in scopes:
                    answer = int(r_invite.group(1) or r_invite.group(3))
        if r_invite is None or answer is None:
            raise arguments_errors.InvalidBotOrGuildInviteError(value)
        return answer

BotOrGuildInviteArgument = discord.app_commands.Transform[str | int, BotOrGuildInviteTransformer]

class GuildInviteTransformer(discord.app_commands.Transformer):
    """Convert a string to a guild invite"""

    async def transform(self, interaction, value, /):
        "Do the conversion"
        try:
            invite = await interaction.client.fetch_invite(value)
        except discord.NotFound as err:
            raise arguments_errors.InvalidGuildInviteError(value) from err
        if invite.type != discord.enums.InviteType.guild:
            raise arguments_errors.InvalidGuildInviteError(value)
        return invite

    async def autocomplete(self, interaction, value, /):
        if interaction.guild is None or not interaction.guild.me.guild_permissions.manage_guild:
            return []
        value = value.lower()
        options: list[tuple[bool, str]] = []
        for invite in await interaction.guild.invites():
            if value in invite.code.lower():
                options.append((invite.code.lower().startswith(value), invite.code))
        options.sort()
        return [
            discord.app_commands.Choice(name="discord.gg/"+invite_code, value=invite_code)
            for _, invite_code in options
        ][:25]

GuildInviteArgument = discord.app_commands.Transform[discord.Invite, GuildInviteTransformer]

class URL(str):
    "Represents a decomposed URL"
    def __init__(self, regex_exp: re.Match):
        self.domain: str = regex_exp.group("domain")
        self.path: str = regex_exp.group("path")
        self.is_https: bool = regex_exp.group("https") == "https"
        self.url: str = regex_exp.group(0)

    def __str__(self):
        return f"Url(url='{self.url}', domain='{self.domain}', path='{self.path}', is_https={self.is_https})"

class URLTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a valid URL"

    async def transform(self, _interaction, value, /) -> URL:
        "Convert a string to a proper URL instance, else raise BadArgument"
        r = re.search(
            r"(?P<https>https?)://(?:www\.)?(?P<domain>[^/\s]+)(?:/(?P<path>[\S]+))?", value)
        if r is None:
            raise arguments_errors.InvalidUrlError(value)
        return URL(r)

URLArgument = discord.app_commands.Transform[URL, URLTransformer]

class GreedyUsersTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a list of users"

    async def transform(self, interaction, value: str, /):
        "Convert a string to a list of users, else raise BadArgument"
        ctx = await commands.Context.from_interaction(interaction)
        return [
            await commands.UserConverter().convert(ctx, word)
            for word in value.split(" ")
        ]

GreedyUsersArgument = discord.app_commands.Transform[list[discord.User], GreedyUsersTransformer]

class GreedyRolesTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a list of roles"

    async def transform(self, interaction, value: str, /):
        "Convert a string to a list of roles, else raise BadArgument"
        ctx = await commands.Context.from_interaction(interaction)
        return [
            await commands.RoleConverter().convert(ctx, word)
            for word in value.split(" ")
        ]

GreedyRolesArgument = discord.app_commands.Transform[list[discord.Role], GreedyRolesTransformer]

class GreedyUsersOrRolesTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a list of users or roles"

    async def transform(self, interaction, value: str, /):
        "Convert a string to a list of users or roles, else raise BadArgument"
        ctx = await commands.Context.from_interaction(interaction)
        result = []
        for word in value.split(" "):
            try:
                result.append(await commands.UserConverter().convert(ctx, word))
            except commands.BadArgument:
                result.append(await commands.RoleConverter().convert(ctx, word))
        return result

GreedyUsersOrRolesArgument = discord.app_commands.Transform[list[discord.User | discord.Role], GreedyUsersOrRolesTransformer]

class GreedyDurationTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a duration in seconds"

    async def transform(self, _interaction, value: str, /):
        "Convert a string to a duration in seconds, else raise BadArgument"
        return await FormatUtils.parse_duration(value)

GreedyDurationArgument = discord.app_commands.Transform[int, GreedyDurationTransformer]

class EmojiTransformer(discord.app_commands.Transformer):
    "Convert argument to a discord Emoji"

    async def transform(self, interaction, value: str, /):
        "Convert a string to a proper discord Emoji, else raise BadArgument"
        ctx = await commands.Context.from_interaction(interaction)
        return await commands.EmojiConverter().convert(ctx, value)

    async def autocomplete(self, interaction, value, /):
        if interaction.guild_id is None:
            return []
        value = value.lower()
        options: list[tuple[bool, str, str]] = []
        for emoji in interaction.guild.emojis:
            emoji_display = ':' + emoji.name + ':'
            lowercase_emoji_display = emoji_display.lower()
            if value in lowercase_emoji_display or value in str(emoji.id):
                options.append((lowercase_emoji_display.startswith(value), emoji_display, str(emoji.id)))
        options.sort()
        return [
            discord.app_commands.Choice(name=emoji, value=emoji_id)
            for _, emoji, emoji_id in options
        ][:25]

EmojiArgument = discord.app_commands.Transform[discord.Emoji, EmojiTransformer]

class UnicodeEmojiTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Represents any Unicode emoji"

    async def transform(self, interaction: discord.Interaction["Axobot"], value, /):
        "Check if a string is a unicod emoji, else raise BadArgument"
        if value in interaction.client.emojis_manager.unicode_set:
            return value
        raise arguments_errors.InvalidUnicodeEmojiError(value)

class PartialOrUnicodeEmojiTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Represents any unicode or Discord emoji"

    async def transform(self, interaction, value, /):
        "Convert an argument into a PartialEmoji or Unicode emoji"
        ctx = await commands.Context.from_interaction(interaction)
        try:
            return await commands.PartialEmojiConverter().convert(ctx, value)
        except commands.errors.BadArgument:
            return await UnicodeEmojiTransformer().transform(interaction, value)

PartialorUnicodeEmojiArgument = discord.app_commands.Transform[discord.PartialEmoji | str, PartialOrUnicodeEmojiTransformer]

class DiscordOrUnicodeEmojiTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Represents any unicode or Discord emoji"

    async def transform(self, interaction, value, /):
        "Convert an argument into a PartialEmoji or Unicode emoji"
        ctx = await commands.Context.from_interaction(interaction)
        try:
            return await commands.EmojiConverter().convert(ctx, value)
        except commands.errors.BadArgument:
            return await UnicodeEmojiTransformer().transform(interaction, value)

DiscordOrUnicodeEmojiArgument = discord.app_commands.Transform[discord.Emoji | str, DiscordOrUnicodeEmojiTransformer]

class GreedyDiscordOrUnicodeEmojiTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a list of discord or unicode emojis"

    async def transform(self, interaction, value: str, /):
        "Convert a string to a list of discord or unicode emojis, else raise BadArgument"
        return [
            await DiscordOrUnicodeEmojiTransformer().transform(interaction, word)
            for word in value.split(" ")
        ]

GreedyDiscordOrUnicodeEmojiArgument = discord.app_commands.Transform[
    list[discord.Emoji | str], GreedyDiscordOrUnicodeEmojiTransformer
]

class Snowflake:
    "Convert arguments to a discord Snowflake"
    def __init__(self, object_id: int):
        self.id = object_id
        self.binary = bin(object_id)
        self.date = discord.utils.snowflake_time(object_id)
        self.increment = int(self.binary[-12:])
        self.process_id = int(self.binary[-17:-12])
        self.worker_id = int(self.binary[-22:-17])

    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str) -> "Snowflake":
        "Do the conversion"
        if len(argument) < 17 or len(argument) > 20 or not argument.isnumeric():
            raise commands.ObjectNotFound(argument)
        return cls(int(argument))

class GuildTransformer(discord.app_commands.Transformer):
    "Convert a string argument in an interaction usage to a valid discord Guild"

    async def transform(self, interaction, value, /) -> discord.Guild:
        "Do the conversion"
        match = commands.IDConverter._get_id_match(value) # pylint: disable=protected-access
        result = None

        if match is not None:
            guild_id = int(match.group(1))
            result = interaction.client.get_guild(guild_id)

        if result is None:
            result = discord.utils.get(interaction.client.guilds, name=value)

            if result is None:
                raise commands.GuildNotFound(value)
        return result

    async def autocomplete(self, interaction, value, /):
        raise NotImplementedError()

GuildArgument = discord.app_commands.Transform[discord.Guild, GuildTransformer]

class MessageTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert a string argument in an interaction usage to a valid discord Message"

    async def transform(self, interaction, value, /):
        "Do the conversion"
        ctx = await commands.Context.from_interaction(interaction)
        return await commands.MessageConverter().convert(ctx, value) # pylint: disable=protected-access

MessageArgument = discord.app_commands.Transform[discord.Message, MessageTransformer]

class ColorTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert a string argument in an interaction usage to a valid discord Color"

    async def transform(self, interaction, value, /):
        "Do the conversion"
        ctx = await commands.Context.from_interaction(interaction)
        return await commands.ColourConverter().convert(ctx, value) # pylint: disable=protected-access

ColorArgument = discord.app_commands.Transform[discord.Colour, ColorTransformer]
