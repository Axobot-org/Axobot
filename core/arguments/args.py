import re
from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from core.arguments import errors as arguments_errors
from core.formatutils import FormatUtils

if TYPE_CHECKING:
    from core.bot_classes import Axobot, MyContext


class AnyUser(discord.User):
    "Argument converter for any user or member"

    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str) -> discord.User:
        "Converts a string to a user or member"
        res = None
        if argument.isnumeric():
            if ctx.guild is not None:
                res = ctx.guild.get_member(int(argument))
            if res is None:
                res = ctx.bot.get_user(int(argument))
            if res is None:
                try:
                    res = await ctx.bot.fetch_user(int(argument))
                except discord.NotFound:
                    pass
            if res is not None:
                return res
        else:
            try:
                return await commands.MemberConverter().convert(ctx, argument)
            except commands.BadArgument:
                return await commands.UserConverter().convert(ctx, argument)
        if res is None:
            raise commands.errors.UserNotFound(argument)


class CardStyleTransformer(discord.app_commands.Transformer):
    "Converts a string to a valid XP card style"

    async def transform(self, interaction: discord.Interaction["Axobot"], value, /):
        "Do the conversion"
        if value in await interaction.client.get_cog('Utilities').allowed_card_styles(interaction.user):
            return value
        raise arguments_errors.InvalidCardStyleError(value)

    async def autocomplete(self, interaction, value, /):
        raise NotImplementedError()

CardStyleArgument = discord.app_commands.Transform[str, CardStyleTransformer]


class BotOrGuildInviteTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    """Converts a string to a bot invite or a guild invite"""

    async def transform(self, _interaction: discord.Interaction["Axobot"], value, /):
        "Do the conversion"
        answer = None
        r_invite = re.search(
            r'^https://discord(?:app)?\.com/(?:api/)?oauth2/authorize\?(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+)(?:&(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+))*$',
            value
        )
        if r_invite is None:
            r_invite = re.search(r'(?:discord\.gg|discordapp\.com/invite)/([^\s/]+)', value)
            if r_invite is not None:
                answer = r_invite.group(1)
        else:
            if (r_invite.group(2) or r_invite.group(4)) and (r_invite.group(1) or r_invite.group(3)):
                scopes = r_invite.group(2).split('+') if r_invite.group(2) else r_invite.group(4).split('+')
                if 'bot' in scopes:
                    answer = int(r_invite.group(1) or r_invite.group(3))
        if r_invite is None or answer is None:
            raise arguments_errors.InvalidBotOrGuildInviteError(value)
        return answer

BotOrGuildInviteArgument = discord.app_commands.Transform[str | int, BotOrGuildInviteTransformer]

class URL(str):
    "Represents a decomposed URL"
    def __init__(self, regex_exp: re.Match):
        self.domain: str = regex_exp.group('domain')
        self.path: str = regex_exp.group('path')
        self.is_https: bool = regex_exp.group('https') == 'https'
        self.url: str = regex_exp.group(0)

    def __str__(self):
        return f"Url(url='{self.url}', domain='{self.domain}', path='{self.path}', is_https={self.is_https})"

class URLTransformer(discord.app_commands.Transformer): # pylint: disable=abstract-method
    "Convert argument to a valid URL"

    async def transform(self, _interaction, value, /) -> URL:
        "Convert a string to a proper URL instance, else raise BadArgument"
        r = re.search(
            r'(?P<https>https?)://(?:www\.)?(?P<domain>[^/\s]+)(?:/(?P<path>[\S]+))?', value)
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
        unicodes = interaction.client.emojis_manager.unicode_set
        if all(char in unicodes for char in value):
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

class ISBN(int):
    "Convert argument to a valid ISBN"
    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str) -> int:
        "Convert a string to a proper ISBN, else raise BadArgument"
        import isbnlib  # pylint: disable=import-outside-toplevel
        if isbnlib.notisbn(argument):
            raise arguments_errors.InvalidISBNError(argument)
        return isbnlib.get_canonical_isbn(argument)


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
