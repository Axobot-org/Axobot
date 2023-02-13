import datetime
import importlib
import json
import typing
from random import randint

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Cog
from libs import halloween
from libs.errors import NotDuringEventError
from libs.halloween import ColorVariation, TargetConverterType, VariationFlagType, check_image, convert_image

importlib.reload(halloween)
from libs.bot_classes import PRIVATE_GUILD_ID, SUPPORT_GUILD_ID, MyContext, Axobot


async def is_halloween(ctx: MyContext):
    """Check if we are in Halloween period"""
    if ctx.bot.current_event == "halloween":
        return True
    raise NotDuringEventError()

async def get_url_from_ctx(ctx: MyContext, who: typing.Optional[TargetConverterType]):
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


class Halloween(Cog):
    "Class used for halloween events, mainly to hallowin-ify images"
    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "halloween"
        self.hourly_reward = [4, 17]
        try:
            with open("halloween-cache.json", "r", encoding="utf-8") as file:
                self.cache = json.load(file)
        except FileNotFoundError:
            with open("halloween-cache.json", "w", encoding="utf-8") as file:
                file.write('[]')
            self.cache = []

    @commands.hybrid_group(name="halloween", brief="Happy Halloween!")
    @discord.app_commands.guilds(PRIVATE_GUILD_ID, SUPPORT_GUILD_ID)
    @commands.check(is_halloween)
    async def hallow_main(self, ctx: MyContext):
        """Hallowify and be happy for the spooky month! Change your avatar color, check if an image is orange enough, and collect event points to unlock a collector Halloween card!

A BIG thanks to the Project Blurple and their original code for the colorization part.

..Example halloween lightfy

..Example halloween lightfy ++more-dark-halloween ++more-dark-halloween ++more-white ++less-halloween

..Example halloween darkfy @Axobot

..Example halloween check light Axobot

..Example halloween check dark

..Example halloween collect"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)


    async def edit_img_color(self, fmodifier: typing.Literal["light", "dark"], ctx: MyContext,
                             method: VariationFlagType = "hallowify",
                             variations: commands.Greedy[ColorVariation] = None, *,
                             who: typing.Optional[TargetConverterType] = None):
        "Method called under the hood of each modifier command"
        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).attach_files):
            return await ctx.send(await ctx.bot._(ctx.channel, "blurple", "missing-attachment-perm"))

        url = await get_url_from_ctx(ctx, who)

        old_msg = await ctx.send(f"Starting {fmodifier} hallowifying for {ctx.author.mention}...")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(url)) as image:
                    result = await ctx.bot.loop.run_in_executor(
                        None, convert_image,
                        await image.read(),
                        fmodifier,
                        method,
                        variations or []
                    )
        except RuntimeError as err:
            await ctx.reply(f"Oops, something went wrong: {err}")
            return
        await ctx.reply("Here's your image!", file=result)
        if not isinstance(old_msg, discord.InteractionMessage):
            await old_msg.delete()
        await ctx.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 3)

    @hallow_main.command()
    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @commands.check(is_halloween)
    async def lightfy(self, ctx: MyContext, method: VariationFlagType = "hallowify",
                      variations: commands.Greedy[ColorVariation] = None,
                      who: typing.Optional[TargetConverterType] = None):
        "Lightfy an image"
        await self.edit_img_color("light", ctx, method, variations, who=who)

    @hallow_main.command()
    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @commands.check(is_halloween)
    async def darkfy(self, ctx: MyContext, method: VariationFlagType = "hallowify",
                      variations: commands.Greedy[ColorVariation] = None,
                      who: typing.Optional[TargetConverterType] = None):
        "Darkfy an image"
        await self.edit_img_color("dark", ctx, method, variations, who=who)

    @hallow_main.command()
    @commands.cooldown(2, 60, commands.BucketType.member)
    @commands.cooldown(30, 40, commands.BucketType.guild)
    @commands.check(is_halloween)
    async def check(self, ctx: MyContext,
                    who: typing.Optional[TargetConverterType] = None
                    ):
        """Check an image to know if you're cool enough.

        ..Example halloween check

        ..Example halloween check Axobot"""

        url = await get_url_from_ctx(ctx, who)

        old_msg = await ctx.send(f"Starting check for {ctx.author.mention}...")
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as image:
                result = await check_image(await image.read())
        answer = "\n".join(f"> {color['name']}: {color['ratio']}%" for color in result['colors'])
        await ctx.reply(f"Results:\n{answer}")
        if result["passed"] and ctx.author.id not in self.cache:
            await ctx.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, 40)
            self.cache.append(ctx.author.id)
            with open("halloween-cache.json", "w", encoding="utf-8") as file:
                json.dump(self.cache, file)
            await ctx.send(f"{ctx.author.mention} you just won 40 event xp thanks to your hallow-iful picture!")
        if not isinstance(old_msg, discord.InteractionMessage):
            await old_msg.delete()

    @hallow_main.command()
    @commands.check(is_halloween)
    async def help(self, ctx: MyContext):
        "Get some help about hallowify and all of this"
        desc = """Hey! We're currently in October, which is the month of bats, skeletons and most importantly pumpkins! For a limited time, you can use this command to make your images more halloween-ish, and add some atmosphere to your server!

For that, you have here some commands to hallowify you. Notably the `lightfy` command, which allows you to modify an image (by default your avatar or that of a friend) by changing its colors. Or why not `darkfy`, for a darker version. As well as `check`, to check that your image is up to Halloween:tm: standards.

The modification commands (darkfy/lightfy) take into account several methods and variations.
"""
        methods_title = "3 methods"
        methods_desc = """`hallowify` applies a basic hallowify to your image
`edge-detect` applies an algorithm to detect the edges of your image to make it easier to see (slower)
`filter` applies a Halloween filter to your image (very good for images with many colors, also faster, but doesn't support variations)"""
        variations_title = "29 variations"
        variations_desc = """`++more-dark-halloween` adds more Dark Halloween to your image
`++more-halloween` adds more Halloween to your image
`++more-white` adds more White to your image
`++less-dark-halloween` removes some Dark Halloween
`++less-halloween` removes some Halloween
`++less-white` removes some White
`++no-white` removes all White
`++no-halloween` removes all Orange
`++no-dark-halloween` removes all Dark Halloween
`++classic` uses the classic transformation from Blurplefier 2018
`++less-gradient` removes some smoothness of colors from your image
`++more-gradient` adds smoothness of colors to your image
`++invert` swaps the darkest color and lightest color
`++shift` shifts the colors over by one
`++white-bg` replaces the transparency of your image with a white background
`++halloween-bg` replaces the transparency of your image with a Halloween background
`++dark-halloween-bg` replaces the transparency of your image with a Dark Halloween background"""
        if ctx.can_send_embed:
            embed = discord.Embed(title="Hallowify help", description=desc, color=discord.Color.orange())
            embed.add_field(name=variations_title, value=variations_desc)
            embed.add_field(name=methods_title, value=methods_desc)
            await ctx.send(embed=embed)
        else:
            await ctx.send(desc + f"\n\n__{methods_title}:__\n{methods_desc}\n\n__{variations_title}:__\n{variations_desc}")


    @hallow_main.command(name="collect")
    @commands.check(is_halloween)
    async def hw_collect(self, ctx: MyContext):
        """Get some events points every hour"""
        events_cog = self.bot.get_cog("BotEvents")
        if events_cog is None:
            return
        last_data: typing.Optional[dict] = await events_cog.db_get_dailies(ctx.author.id)
        if last_data is None or (datetime.datetime.now() - last_data['last_update']).total_seconds() > 3600:
            points = randint(*self.hourly_reward)
            await self.bot.get_cog("Utilities").add_user_eventPoint(ctx.author.id, points)
            await events_cog.db_add_dailies(ctx.author.id, points)
            txt = await self.bot._(ctx.channel, "halloween.daily.got-points", pts=points)
        else:
            txt = await self.bot._(ctx.channel, "halloween.daily.too-quick")
        if ctx.can_send_embed:
            title = "Halloween event"
            emb = discord.Embed(title=title, description=txt, color=discord.Color.orange())
            await ctx.send(embed=emb)
        else:
            await ctx.send(txt)


async def setup(bot):
    await bot.add_cog(Halloween(bot))
