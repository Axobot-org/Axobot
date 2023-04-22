import datetime
import re
import typing

import discord
from dateutil.relativedelta import relativedelta
from discord.ext import commands

if typing.TYPE_CHECKING:
    from libs.bot_classes import MyContext


class Duration(float):
    "Specific argument converter for durations input"

    @classmethod
    async def convert(cls, _ctx: typing.Optional["MyContext"], argument: str) -> int:
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
            raise commands.errors.BadArgument('Invalid duration: '+argument)
        return duration


class AnyUser(discord.User):
    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str) -> discord.User:
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


class cardStyle(str):
    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str) -> str:
        if argument in await ctx.bot.get_cog('Utilities').allowed_card_styles(ctx.author):
            return argument
        else:
            raise commands.errors.BadArgument('Invalid card style: '+argument)


class Invite(commands.Converter):
    def __init__(self):
        pass

    async def convert(self, _ctx: "MyContext", argument: str) -> typing.Union[str, int]:
        answer = None
        r_invite = re.search(
            r'^https://discord(?:app)?\.com/(?:api/)?oauth2/authorize\?(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+)(?:&(?:client_id=(\d{17,19})|scope=([a-z\.\+]+?)|(?:permissions|guild_id|disable_guild_select|redirect_uri)=[^&\s]+))*$',
            argument)
        if r_invite is None:
            r_invite = re.search(
                r'(?:discord\.gg|discordapp\.com/invite)/([^\s/]+)', argument)
            if r_invite is not None:
                answer = r_invite.group(1)
        else:
            if (r_invite.group(2) or r_invite.group(4)) and (r_invite.group(1) or r_invite.group(3)):
                scopes = r_invite.group(2).split('+') if r_invite.group(2) else r_invite.group(4).split('+')
                if 'bot' in scopes:
                    answer = int(r_invite.group(1) or r_invite.group(3))
        if r_invite is None or answer is None:
            raise commands.errors.BadArgument('Invalid invite: '+argument)
        return answer


class Guild(discord.Guild):
    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str) -> discord.Guild:
        if argument.isnumeric():
            res = ctx.bot.get_guild(int(argument))
            if res is not None:
                return res
        raise commands.errors.BadArgument('Invalid guild: '+argument)


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
            raise commands.errors.BadArgument('Invalid url: '+argument)
        return cls(r)

class UnicodeEmoji(str):
    "Represents any Unicode emoji"
    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str):
        "Check if a string is a unicod emoji, else raise BadArgument"
        unicodes = ctx.bot.emojis_manager.unicode_set
        if all(char in unicodes for char in argument):
            return argument
        raise commands.errors.BadArgument('Invalid Unicode emoji: '+argument)

class AnyEmoji(commands.Converter):
    "Convert argument to any emoji, either custom or unicode"
    async def convert(self, ctx: "MyContext", argument: str) -> typing.Union[str, discord.Emoji]:
        r = re.search(r'<a?:[^:]+:(\d+)>', argument)
        if r is None:
            try:
                return await UnicodeEmoji.convert(ctx, argument)
            except commands.errors.BadArgument:
                pass
        else:
            try:
                return await commands.EmojiConverter().convert(ctx, r.group(1))
            except discord.DiscordException:
                return r.group(1)
        raise commands.errors.BadArgument('Invalid emoji: '+argument)


class arguments(commands.Converter):
    "Convert arguments to a foo=bar dictionary"
    async def convert(self, ctx: "MyContext", argument: str) -> dict[str, str]:
        answer = dict()
        for result in re.finditer(r'(\w+) ?= ?\"((?:[^\"\\]|\\\"|\\)+)\"', argument):
            answer[result.group(1)] = result.group(2).replace('\\"', '"')
        return answer


class Color(commands.Converter):
    "Convert arguments to a valid color (hexa or decimal)"
    async def convert(self, ctx: "MyContext", argument: str) -> int:
        if argument.startswith('#') and len(argument) % 3 == 1:
            arg = argument[1:]
            rgb = [int(arg[i:i+2], 16)
                   for i in range(0, len(arg), len(arg)//3)]
            return discord.Colour(0).from_rgb(rgb[0], rgb[1], rgb[2]).value
        elif argument.isnumeric():
            return int(argument)
        else:
            return None


class Snowflake:
    "Convert arguments to a discord Snowflake"
    def __init__(self, ID: int):
        self.id = ID
        self.binary = bin(ID)
        self.date = discord.utils.snowflake_time(ID)
        self.increment = int(self.binary[-12:])
        self.process_id = int(self.binary[-17:-12])
        self.worker_id = int(self.binary[-22:-17])

    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str) -> int:
        if len(argument) < 17 or len(argument) > 20 or not argument.isnumeric():
            raise commands.BadArgument("Invalid snowflake")
        return cls(int(argument))


class serverlog(str):
    "Convert arguments to a server log type"
    @classmethod
    async def convert(cls, ctx: "MyContext", argument: str) -> str:
        from fcts.serverlogs import ServerLogs  # pylint: disable=import-outside-toplevel

        if argument in ServerLogs.available_logs() or argument == 'all':
            return argument
        raise commands.BadArgument(f'"{argument}" is not a valid server log type')

class RawPermissionValue(int):
    "Represents a raw permission value, as an integer"

    async def convert(self, ctx: "MyContext", argument: str):
        if re.match(r'0b[0,1]+', argument):
            return int(argument[2:], 2)
        if not argument.isnumeric():
            return None
        try:
            value = int(argument, 2 if len(argument) > 13 else 10)
        except ValueError:
            value = int(argument)
        if value > discord.Permissions.all().value:
            return None
        return value
