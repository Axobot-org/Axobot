import asyncio
import aiohttp
import json
import typing
import json
import importlib
import datetime
from random import randint

import discord
from discord.ext import commands
from discord.ext.commands import Cog

from libs import halloween
from libs.halloween import convert_image, check_image
importlib.reload(halloween)
from utils import zbot, MyContext


class LinkConverter(commands.Converter):
    async def convert(self, ctx: MyContext, argument: str):
        if not argument.startswith(('http://', 'https://')):
            raise commands.errors.BadArgument(
                'Could not convert "{}" into URL'.format(argument))

        for _ in range(10):
            if ctx.message.embeds and ctx.message.embeds[0].thumbnail:
                return ctx.message.embeds[0].thumbnail.proxy_url

            await asyncio.sleep(1)

        raise commands.errors.BadArgument(
            'Discord proxy image did not load in time.')


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
            raise commands.errors.BadArgument(
                f'Could not convert "{argument}" into Halloween Theme')
        return argument

async def is_halloween(ctx: MyContext):
    """Check if we are in Halloween period"""
    return ctx.bot.current_event == "halloween"

def _make_check_command(name: str, parent: commands.Group, **kwargs):
    @commands.cooldown(2, 60, commands.BucketType.member)
    @commands.cooldown(30, 40, commands.BucketType.guild)
    @parent.command(name, help=f"{name.title()} an image to know if you're cool enough.\n\nTheme is either 'light' or 'dark'", **kwargs)
    async def command(self, ctx: MyContext, theme: ThemeConverter = "light", *, who: typing.Union[discord.Member, discord.PartialEmoji, LinkConverter] = None):

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
        answer = "\n".join(
            ["> {}: {}%".format(color["name"], color["ratio"]) for color in r['colors']])
        await ctx.send(f"Results for {ctx.author.mention}:\n"+answer)
        if r["passed"] and ctx.author.id not in self.cache:
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 40)
            self.cache.append(ctx.author.id)
            with open("halloween-cache.json", "w") as f:
                json.dump(self.cache, f)
            await ctx.send(f"{ctx.author.mention} you just won 40 event xp thanks to your hallow-iful picture!")
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
            return await ctx.send(await self.bot._(ctx.channel, "blurple", "missing-attachment-perm"))

        if method is None:
            method = await self.get_default_halloweefier(ctx)

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

        if fmodifier == 'hallowify':
            final_modifier = "light"

            if final_modifier is None:
                return
        else:
            final_modifier = fmodifier

        old_msg = await ctx.send("Starting {} for {}...".format(name, ctx.author.mention))
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(url)) as image:
                    r = await self.bot.loop.run_in_executor(None, convert_image, await image.read(), final_modifier, method, variations)
        except RuntimeError as e:
            await ctx.send(f"Oops, something went wrong: {e}")
            return
        await ctx.send(f"{ctx.author.mention}, here's your image!", file=r)
        await old_msg.delete()
        await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 3)

    return command


class Halloween(Cog):
    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "halloween"
        self.hourly_reward = [4, 17]
        try:
            with open("halloween-cache.json", "r") as f:
                self.cache = json.load(f)
        except FileNotFoundError:
            with open("halloween-cache.json", "w") as f:
                f.write('[]')
            self.cache = list()

    async def get_default_halloweefier(self, ctx: MyContext):
        return "--hallowify"

    @commands.group(name="halloween", aliases=["hw"])
    @commands.check(is_halloween)
    async def hallow_main(self, ctx: MyContext):
        """Hallowify and be happy for the spooky month! Change your avatar color, check if an image is orange enough, and collect event points to unlock a collector Halloween 2020 card!
        
A BIG thanks to the Project Blurple and their original code for the colorization part.

..Example hw hallowify

..Example hw  hallowify ++more-dark-halloween ++more-dark-halloween ++more-white ++less-halloween

..Example hw darkfy @Zbot

..Example halloween check light Zbot

..Example hw check dark

..Example hw collect"""
        pass
    
    lightfy = _make_color_command('lightfy', 'light', hallow_main)
    darkfy = _make_color_command('darkfy', 'dark', hallow_main)
    hallowify = _make_color_command('hallowify', 'hallowify', hallow_main)
    check = _make_check_command('check', hallow_main)

    @hallow_main.command()
    async def help(self, ctx: MyContext):
        "Get some help about hallowify and all of this"
        await ctx.send("""Hey! We're currently in October, which is the month of bats, skeletons and most importantly pumpkins! For a limited time, you can use this command to make your images more halloween-ish, and add some atmosphere to your server!

For that, you have here some commands to hallowify you. Notably the `hallowify` command, which allows you to modify an image (by default your avatar or that of a friend) by changing its colors. Or why not `darkfy`, for a darker version. As well as `check`, to check that your image is up to Halloween:tm: standards.

The modification commands (hallowify/darkfy/lightfy) take into account several methods and variations.
__3 methods:__ 
`--hallowify` applies a basic hallowify to your image
`--edge-detect` applies an algorithm to detect the edges of your image to make it easier to see
`--filter` applies a Halloween filter to your image (very good for images with many colors)
__29 variations: __
`++more-dark-halloween` adds more Dark Halloween to your image
`++more-halloween` adds more Halloween to your image
`++more-white` adds more White to your image
`++less-dark-halloween` removes some Dark Halloween from your image
`++less-halloween` removes some Halloween from your image
`++less-white` removes some White from your image
`++no-white` removes White from your image
`++no-halloween` removes Halloween from your image
`++no-dark-halloween` removes Dark Halloween from your image
`++classic` uses the classic transformation from Blurplefier 2018
`++less-gradient` removes some smoothness of colors from your image
`++more-gradient` adds smoothness of colors to your image
`++invert` swaps the darkest color and lightest color
`++shift` shifts the colors over by one 
`++white-bg` replaces the transparency of your image with a white background
`++halloween-bg` replaces the transparency of your image with a Halloween background
`++dark-halloween-bg` replaces the transparency of your image with a Dark Halloween background""")

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

    @hallow_main.command(name="collect")
    async def hw_collect(self, ctx: MyContext):
        """Get some events points every hour"""
        last_data = self.db_get_points(ctx.author.id)
        if last_data is None or (datetime.datetime.now() - last_data['last_update']).total_seconds() > 3600:
            points = randint(*self.hourly_reward)
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, points)
            self.db_add_points(ctx.author.id, points)
            txt = await self.bot._(ctx.channel, "halloween", "got-points", pts=points)
        else:
            txt = await self.bot._(ctx.channel, "halloween", "too-quick")
        if ctx.can_send_embed:
            title = "Halloween event"
            emb = discord.Embed(title=title, description=txt, color=discord.Color.orange())
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)


def setup(bot):
    bot.add_cog(Halloween(bot))
