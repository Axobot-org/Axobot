import asyncio
import datetime
from random import randint
import aiohttp
import json
import typing
import importlib

import discord
from discord.ext import commands
from discord.ext.commands import Cog

from libs import blurple
from libs.blurple import convert_image, check_image
from libs.formatutils import FormatUtils
importlib.reload(blurple)
from libs.bot_classes import Axobot, MyContext


class LinkConverter(commands.Converter):
    async def convert(self, ctx: MyContext, argument: str):
        if not argument.startswith(('http://', 'https://')):
            raise commands.errors.BadArgument('Could not convert "{}" into URL'.format(argument))

        for _ in range(10):
            if ctx.message.embeds and ctx.message.embeds[0].thumbnail:
                return ctx.message.embeds[0].thumbnail.proxy_url

            await asyncio.sleep(1)

        raise commands.errors.BadArgument('Discord proxy image did not load in time.')


class FlagConverter(commands.Converter):
    async def convert(self, ctx: MyContext, argument: str):
        if not argument.startswith('--'):
            raise commands.errors.BadArgument('Not a valid flag!')
        return argument


class FlagConverter2(commands.Converter):
    async def convert(self, ctx: MyContext, argument: str):
        if not argument.startswith('++'):
            raise commands.errors.BadArgument('Not a valid flag!')
        return argument

async def get_url_from_ctx(ctx: MyContext, who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter]):
    "Get the resource URL from either the who argument or the context"
    if ctx.message.attachments:
        url = ctx.message.attachments[0].proxy_url
    elif who is None:
        url = ctx.author.display_avatar.url
    else:
        if isinstance(who, str):  # LinkConverter
            url = who
        elif isinstance(who, discord.PartialEmoji):
            url = who.url
        else:
            url = who.display_avatar.url
    return url


class Blurplefy(Cog):
    "Class used to make things blurple, for the Discord birthday event"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "blurple"
        self.hourly_reward = [4, 20]
        try:
            with open("blurple-cache.json", "r", encoding="utf-8") as jsonfile:
                self.cache: list[int] = json.load(jsonfile)
        except FileNotFoundError:
            with open("blurple-cache.json", "w", encoding="utf-8") as jsonfile:
                json.dump(list(), jsonfile)
            self.cache = list()

    async def get_default_blurplefier(self, _):
        return "--blurplefy"

    @commands.group(name="blurple", aliases=["b"])
    async def blurple_main(self, ctx: MyContext):
        """Blurplefy and be happy for the 6th Discord birthday!
A BIG thanks to the Project Blurple and their help.

Original code: https://github.com/project-blurple/blurplefier
Their server: https://discord.gg/blurple
Online editor: https://projectblurple.com/paint

..Example b blurplefy

..Example b  blurplefy ++more-dark-blurple ++more-dark-blurple ++more-white ++less-blurple

..Example b darkfy @Axobot

..Example blurple check light Axobot

..Example b check dark"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @blurple_main.command()
    async def help(self, ctx: MyContext):
        "Get some help about blurplefy and all of this"
        await ctx.send("""Hey! We're currently celebrating 6 years of Discord! And for the third year in a row, we're taking part in the "Blurple" event, which consists in recoloring our avatars and servers with a maximum of blurple, that characteristic color of Discord between purple and blue.

For that, you have here some commands to blurplefy you. Notably the `blurplefy` command, which allows you to modify an image (by default your avatar or that of a friend) by changing its colors. Or why not `darkfy`, for a darker version. As well as `check`, to check that your image is up to Blurple:tm: standards.

The modification commands (blurplefy/darkfy/lightfy) take into account several methods and variations.
__3 methods:__
`--blurplefy` applies a basic blurplefy to your image
`--edge-detect` applies an algorithm to detect the edges of your image to make it easier to see
`--filter` applies a Blurple filter to your image (very good for images with many colors)
__29 variations: __
`++more-dark-blurple` adds more Dark Blurple to your image
`++more-blurple` adds more Blurple to your image
`++more-white` adds more White to your image
`++less-dark-blurple` removes some Dark Blurple from your image
`++less-blurple` removes some Blurple from your image
`++less-white` removes some White from your image
`++no-white` removes White from your image
`++no-blurple` removes Blurple from your image
`++no-dark-blurple` removes Dark Blurple from your image
`++classic` uses the same Blurplefier as 2018
`++less-gradient` removes some smoothness of colors from your image
`++more-gradient` adds smoothness of colors to your image
`++invert` swaps the darkest color and lightest color
`++shift` shifts the colors over by one
`++white-bg` replaces the transparency of your image with a white background
`++blurple-bg` replaces the transparency of your image with a Blurple background
`++dark-blurple-bg` replaces the transparency of your image with a Dark Blurple background""")

    async def db_add_points(self, userid: int, points: int):
        query = "INSERT INTO `dailies` (`userID`,`points`) VALUES (%(u)s,%(p)s) ON DUPLICATE KEY UPDATE points = points + %(p)s;"
        async with self.bot.db_query(query, {'u': userid, 'p': points}):
            pass

    async def db_get_points(self, userid: int) -> dict:
        query = "SELECT * FROM `dailies` WHERE userid = %(u)s;"
        async with self.bot.db_query(query, {'u': userid}, fetchone=True) as query_results:
            result = query_results or None
        return result

    @commands.cooldown(2, 60, commands.BucketType.member)
    @commands.cooldown(30, 40, commands.BucketType.guild)
    @blurple_main.command("check", help="Check an image to know if you're cool enough")
    async def bp_check(self, ctx: MyContext, theme: typing.Literal["light", "dark"] = "light", *, who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):

        url = await get_url_from_ctx(ctx, who)

        old_msg = await ctx.send(await ctx.bot._(ctx.channel, "blurple.check_intro", user=ctx.author.mention))
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as image:
                r = await check_image(await image.read(), theme, "check")
        answer = "\n".join([f"> {color['name']}: {color['ratio']}%" for color in r['colors']])
        await ctx.send(f"Results for {ctx.author.mention}:\n"+answer)
        if r["passed"] and ctx.author.id not in self.cache:
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 40)
            self.cache.append(ctx.author.id)
            with open("blurple-cache.json", "w", encoding="utf-8") as jsonfile:
                json.dump(self.cache, jsonfile)
            await ctx.send(f"{ctx.author.mention} you just won 40 event xp thanks to your blurple-liful picture!")
        await old_msg.delete()

    async def color_command(self, fmodifier: str, ctx: MyContext, method: typing.Optional[FlagConverter],
                      variations: commands.Greedy[FlagConverter2],
                      who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter]):
        "Change a given image with the given modifier, method and variations"
        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).attach_files):
            await ctx.send(await self.bot._(ctx.channel,"blurple.missing-attachment-perm"))
            return

        if method is None:
            method = await self.get_default_blurplefier(ctx)

            if method is None:
                return

        url = await get_url_from_ctx(ctx, who)

        if fmodifier == 'blurplefy':
            final_modifier = "light"

            if final_modifier is None:
                return
        else:
            final_modifier = fmodifier

        old_msg = await ctx.send(
            await ctx.bot._(ctx.channel, 'blurple.blurplefy.starting', name=fmodifier+'fy', user=ctx.author.mention)
            )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(url)) as image:
                    r = await convert_image(await image.read(), final_modifier, method,variations)
        except RuntimeError as err:
            await ctx.send(await ctx.bot._(ctx.channel, 'blurple.unknown-err', err=str(err)))
            return
        await ctx.send(await ctx.bot._(ctx.channel, 'blurple.blurplefy.success', user=ctx.author.mention), file=r)
        await old_msg.delete()
        await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 3)

    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @blurple_main.command("lightfy", help="Lightfy an image")
    async def bp_lightfy(self, ctx: MyContext, method: typing.Optional[FlagConverter] = None,
                      variations: commands.Greedy[FlagConverter2] = [None], *,
                      who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):
        await self.color_command("light", ctx, method, variations, who)

    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @blurple_main.command("darkfy", help="Darkfy an image")
    async def bp_darkfy(self, ctx: MyContext, method: typing.Optional[FlagConverter] = None,
                      variations: commands.Greedy[FlagConverter2] = [None], *,
                      who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):
        await self.color_command("dark", ctx, method, variations, who)

    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @blurple_main.command("blurplefy", help="Blurplefy an image")
    async def bp_blurplefy(self, ctx: MyContext, method: typing.Optional[FlagConverter] = None,
                      variations: commands.Greedy[FlagConverter2] = [None], *,
                      who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):
        await self.color_command("blurplefy", ctx, method, variations, who)

    @blurple_main.command(name="collect")
    async def bp_collect(self, ctx: MyContext):
        """Get some events points every 3 hours"""
        last_data = await self.db_get_points(ctx.author.id)
        cooldown = 3600*3
        time_since_available: int = 0 if last_data is None else (datetime.datetime.now() - last_data['last_update']).total_seconds() - cooldown
        if time_since_available >= 0:
            points = randint(*self.hourly_reward)
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, points)
            await self.db_add_points(ctx.author.id, points)
            txt = await self.bot._(ctx.channel, "halloween.daily.got-points", pts=points)
        else:
            lang = await self.bot._(ctx.channel, '_used_locale')
            remaining = await FormatUtils.time_delta(-time_since_available, lang=lang)
            txt = await self.bot._(ctx.channel, "blurple.collect.too-quick", time=remaining)
        if ctx.can_send_embed:
            title = await self.bot._(ctx.channel, 'blurple.collect.title')
            emb = discord.Embed(title=title, description=txt, color=discord.Color(int("7289DA",16)))
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)



async def setup(bot):
    await bot.add_cog(Blurplefy(bot))