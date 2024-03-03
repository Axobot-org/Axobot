import datetime
import re
from typing import TYPE_CHECKING, Annotated, Optional, Union

import discord
from dateutil.relativedelta import relativedelta
from discord.ext import commands

from libs.arguments import errors as arguments_errors

if TYPE_CHECKING:
    from libs.bot_classes import MyContext


class Duration(float):
    "Argument converter for durations input"

    @classmethod
    async def convert(cls, _ctx: Optional["MyContext"], argument: str) -> int:
        "Converts a string to a duration in seconds."
        duration: int = 0
        found = False
        for symbol, coef in [('w', 604800), ('d', 86400), ('h', 3600), ('m', 60), ('min', 60)]:
            r = re.search(r'^(\d+)'+symbol+'$', argument)
            if r is not None:
                duration += int(r.group(1))*coef
                found = True
        r = re.search(r'^(\d+)h(\d+)m?$', argument)
        if r is not None:
            duration += int(r.group(1))*3600 + int(r.group(2))*60
            found = True
        r = re.search(r'^(\d+) ?mo(?:nths?)?$', argument)
        if r is not None:
            now = then = datetime.datetime.now(datetime.timezone.utc)
            then += relativedelta(months=int(r.group(1)))
            duration += (then - now).total_seconds()
            found = True
        r = re.search(r'^(\d+) ?y(?:ears?)?$', argument)
        if r is not None:
            now = then = datetime.datetime.now(datetime.timezone.utc)
            then += relativedelta(years=int(r.group(1)))
            duration += (then - now).total_seconds()
            found = True
        if not found:
            raise arguments_errors.InvalidDurationError(argument)
        return duration


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


class CardStyle(str):
    "Converts a string to a valid XP card style"
    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str):
        "Do the conversion"
        if argument in await ctx.bot.get_cog('Utilities').allowed_card_styles(ctx.author):
            return argument
        raise arguments_errors.InvalidCardStyleError(argument)


class BotOrGuildInviteConverter:
    """Converts a string to a bot invite or a guild invite"""
    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str) -> Union[str, int]:
        "Do the conversion"
        answer = None
        r_invite = re.search(
            r'^https://discord(?:app)?\.com/(?:api/)?oauth2/authorize\?(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+)(?:&(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+))*$',
            argument
        )
        if r_invite is None:
            r_invite = re.search(r'(?:discord\.gg|discordapp\.com/invite)/([^\s/]+)', argument)
            if r_invite is not None:
                answer = r_invite.group(1)
        else:
            if (r_invite.group(2) or r_invite.group(4)) and (r_invite.group(1) or r_invite.group(3)):
                scopes = r_invite.group(2).split('+') if r_invite.group(2) else r_invite.group(4).split('+')
                if 'bot' in scopes:
                    answer = int(r_invite.group(1) or r_invite.group(3))
        if r_invite is None or answer is None:
            raise arguments_errors.InvalidBotOrGuildInviteError(argument)
        return answer

BotOrGuildInvite = Annotated[Union[str, int], BotOrGuildInviteConverter]

class URL:
    "Convert argument to a valid URL"

    def __init__(self, regex_exp: re.Match):
        self.domain: str = regex_exp.group('domain')
        self.path: str = regex_exp.group('path')
        self.is_https: bool = regex_exp.group('https') == 'https'
        self.url: str = regex_exp.group(0)

    def __str__(self):
        return f"Url(url='{self.url}', domain='{self.domain}', path='{self.path}', is_https={self.is_https})"

    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str) -> "URL":
        "Convert a string to a proper URL instance, else raise BadArgument"
        r = re.search(
            r'(?P<https>https?)://(?:www\.)?(?P<domain>[^/\s]+)(?:/(?P<path>[\S]+))?', argument)
        if r is None:
            raise arguments_errors.InvalidUrlError(argument)
        return cls(r)

class UnicodeEmojiConverter(str):
    "Represents any Unicode emoji"

    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str):
        "Check if a string is a unicod emoji, else raise BadArgument"
        unicodes = ctx.bot.emojis_manager.unicode_set
        if all(char in unicodes for char in argument):
            return argument
        raise arguments_errors.InvalidUnicodeEmojiError(argument)

class PartialOrUnicodeEmojiConverter:
    "Represents any unicode or Discord emoji"

    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str):
        "Convert an argument into a PartialEmoji or Unicode emoji"
        try:
            return await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.errors.BadArgument:
            return await UnicodeEmojiConverter().convert(ctx, argument)

PartialorUnicodeEmoji = Annotated[Union[discord.PartialEmoji, str], PartialOrUnicodeEmojiConverter]

class DiscordOrUnicodeEmojiConverter:
    "Represents any unicode or Discord emoji"

    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str):
        "Convert an argument into a PartialEmoji or Unicode emoji"
        try:
            return await commands.EmojiConverter().convert(ctx, argument)
        except commands.errors.BadArgument:
            return await UnicodeEmojiConverter().convert(ctx, argument)

DiscordOrUnicodeEmoji = Annotated[Union[discord.Emoji, str], DiscordOrUnicodeEmojiConverter]


class arguments(commands.Converter):
    "Convert arguments to a foo=bar dictionary"
    async def convert(self, _ctx: "MyContext", argument: str) -> dict[str, str]:
        answer = {}
        for result in re.finditer(r'(\w+) ?= ?\"((?:[^\"\\]|\\\"|\\)+)\"', argument):
            answer[result.group(1)] = result.group(2).replace('\\"', '"')
        return answer


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


class ServerLog(str):
    "Convert arguments to a server log type"
    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str) -> str:
        "Do the conversion"
        from fcts.serverlogs import \
            ServerLogs  # pylint: disable=import-outside-toplevel

        if argument in ServerLogs.available_logs() or argument == 'all':
            return argument
        raise arguments_errors.InvalidServerLogError(argument)

class RawPermissionValue(int):
    "Represents a raw permission value, as an integer"
    @classmethod
    async def convert(cls, _ctx: "MyContext", argument: str):
        "Do the conversion"
        if re.match(r'0b[0,1]+', argument):
            return int(argument[2:], 2)
        if not argument.isnumeric():
            raise arguments_errors.InvalidRawPermissionError(argument)
        try:
            value = int(argument, 2 if len(argument) > 13 else 10)
        except ValueError:
            value = int(argument)
        if value > discord.Permissions.all().value:
            raise arguments_errors.InvalidRawPermissionError(argument)
        return value

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
