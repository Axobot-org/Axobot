import asyncio
import datetime
from random import randint
import aiohttp
import json
import typing
import json
import importlib

import discord
from discord.ext import commands
from discord.ext.commands import Cog

from libs import blurple
from libs.blurple import convert_image, check_image
importlib.reload(blurple)
from utils import zbot, MyContext


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

class ThemeConverter(commands.Converter):
    async def convert(self, ctx: MyContext, argument: str):
        if not argument in ["light", "dark"]:
            raise commands.errors.BadArgument(f'Could not convert "{argument}" into Blurple Theme')
        return argument


def _make_check_command(name, parent, **kwargs):
    @commands.cooldown(2, 60, commands.BucketType.member)
    @commands.cooldown(30, 40, commands.BucketType.guild)
    @parent.command(name, help=f"{name.title()} an image to know if you're cool enough.", **kwargs)
    async def command(self, ctx: MyContext, theme: ThemeConverter="light", *, who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):

        if ctx.message.attachments:
            url = ctx.message.attachments[0].proxy_url
        elif who is None:
            url = ctx.author.avatar_url
        else:
            if isinstance(who, str):  # LinkConverter
                url = who
            elif isinstance(who, discord.PartialEmoji):
                url = who.url
            else:
                url = who.avatar_url

        old_msg = await ctx.send("Starting check for {}...".format(ctx.author.mention))
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as image:
                r = await check_image(await image.read(), theme, name)
        answer = "\n".join(["> {}: {}%".format(color["name"],color["ratio"]) for color in r['colors']])
        await ctx.send(f"Results for {ctx.author.mention}:\n"+answer)
        if r["passed"] and ctx.author.id not in self.cache:
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 40)
            self.cache.append(ctx.author.id)
            with open("blurple-cache.json", "w") as f:
                json.dump(self.cache, f)
            await ctx.send(f"{ctx.author.mention} you just won 40 event xp thanks to your blurple-liful picture!")
        await old_msg.delete()

    return command


def _make_color_command(name, fmodifier, parent, **kwargs):
    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @parent.command(name, help=f"{name.title()} an image.", **kwargs)
    async def command(self, ctx: MyContext, method: typing.Optional[FlagConverter] = None,
                      variations: commands.Greedy[FlagConverter2] = [None], *,
                      who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):

        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).attach_files):
            return await ctx.send(await self.bot._(ctx.channel,"blurple","missing-attachment-perm"))

        if method is None:
            method = await self.get_default_blurplefier(ctx)

            if method is None:
                return
        if ctx.message.attachments:
            url = ctx.message.attachments[0].proxy_url
        elif who is None:
            url = ctx.author.avatar_url
        else:
            if isinstance(who, str):  # LinkConverter
                url = who
            elif isinstance(who, discord.PartialEmoji):
                url = who.url
            else:
                url = who.avatar_url

        if fmodifier == 'blurplefy':
            final_modifier = "light"

            if final_modifier is None:
                return
        else:
            final_modifier = fmodifier

        old_msg = await ctx.send("Starting {} for {}...".format(name,ctx.author.mention))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(url)) as image:
                    r = await convert_image(await image.read(), final_modifier, method,variations)
        except RuntimeError as e:
            await ctx.send(f"Oops, something went wrong: {e}")
            return
        await ctx.send(f"{ctx.author.mention}, here's your image!", file=r)
        await old_msg.delete()
        await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 3)

    return command


class Blurplefy(Cog):
    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "blurple"
        self.hourly_reward = [4, 20]
        try:
            with open("blurple-cache.json", "r") as f:
                self.cache: list[int] = json.load(f)
        except FileNotFoundError:
            with open("blurple-cache.json", "w") as f:
                json.dump(list(), f)
    
    async def get_default_blurplefier(self, ctx):
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

..Example b darkfy @Zbot

..Example blurple check light Zbot

..Example b check dark"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['blurple'])
    
    lightfy = _make_color_command('lightfy', 'light', blurple_main)
    darkfy = _make_color_command('darkfy', 'dark', blurple_main)
    blurplefy = _make_color_command('blurplefy', 'blurplefy', blurple_main)
    check = _make_check_command('check', blurple_main)

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

    def db_add_points(self, userid: int, points: int):
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        query = "INSERT INTO `dailies` (`userID`,`points`) VALUES (%(u)s,%(p)s) ON DUPLICATE KEY UPDATE points = points + %(p)s;"
        cursor.execute(query, {'u': userid, 'p': points})
        cnx.commit()
        cursor.close()

    def db_get_points(self, userid: int) -> dict:
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        query = "SELECT * FROM `dailies` WHERE userid = %(u)s;"
        cursor.execute(query, {'u': userid})
        result = list(cursor)
        cursor.close()
        return result[0] if len(result) > 0 else None

    @blurple_main.command(name="collect")
    async def bp_collect(self, ctx: MyContext):
        """Get some events points every 3 hours"""
        last_data = self.db_get_points(ctx.author.id)
        cooldown = 3600*3
        remaining_time: int = -cooldown if last_data is None else (datetime.datetime.now() - last_data['last_update']).total_seconds() - cooldown
        if remaining_time > 0:
            points = randint(*self.hourly_reward)
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, points)
            self.db_add_points(ctx.author.id, points)
            txt = await self.bot._(ctx.channel, "halloween", "got-points", pts=points)
        else:
            lang = await self.bot._(ctx.channel, "current_lang", "current")
            remaining = await self.bot.get_cog("TimeUtils").time_delta(-remaining_time, lang=lang)
            txt = await self.bot._(ctx.channel, "blurple", "too-quick", time=remaining)
        if ctx.can_send_embed:
            title = "Blurple event"
            emb = discord.Embed(title=title, description=txt, color=discord.Color(int("7289DA",16)))
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)

    

def setup(bot):
    bot.add_cog(Blurplefy(bot))