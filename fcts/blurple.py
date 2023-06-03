import json
import typing

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Cog

from libs.bot_classes import (PRIVATE_GUILD_ID, SUPPORT_GUILD_ID, Axobot,
                              MyContext)
from libs.colors_events import (BlurpleVariationFlagType, ColorVariation,
                                TargetConverterType, check_blurple,
                                convert_blurple, get_url_from_ctx)
from libs.errors import NotDuringEventError


async def is_blurple(ctx: MyContext):
    """Check if we are in a Blurple event period"""
    if ctx.bot.current_event == "blurple":
        return True
    raise NotDuringEventError()

class Blurplefy(Cog):
    "Class used to make things blurple, for the Discord birthday event"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "blurple"
        self.embed_color = 0x5865F2
        try:
            with open("blurple-cache.json", "r", encoding="utf-8") as jsonfile:
                self.cache: list[int] = json.load(jsonfile)
        except FileNotFoundError:
            with open("blurple-cache.json", "w", encoding="utf-8") as jsonfile:
                jsonfile.write('[]')
            self.cache = []

    @commands.hybrid_group(name="blurple", aliases=["b"], brief="Happy Discord birthday!")
    @discord.app_commands.guilds(PRIVATE_GUILD_ID, SUPPORT_GUILD_ID)
    @commands.check(is_blurple)
    async def blurple_main(self, ctx: MyContext):
        """Blurplefy and be happy for the 8th Discord birthday!
Change your avatar color, check if an image is blurple enough, and collect event points to unlock a collector Blurple card!

A BIG thanks to the Project Blurple and their original code for the colorization part.

Original code: https://github.com/project-blurple/blurplefier
Their server: https://discord.gg/qEmKyCf
Online editor: https://projectblurple.com/paint

..Example b lightfy

..Example b lightfy ++more-dark-blurple ++more-dark-blurple ++more-white ++less-blurple

..Example b darkfy @Axobot

..Example blurple check light Axobot

..Example b check dark"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @blurple_main.command()
    @commands.check(is_blurple)
    async def help(self, ctx: MyContext):
        "Get some help about blurplefy and all of this"
        desc = """Hey! We're currently celebrating 8 years of Discord! And for the third year in a row, we're taking part in the "Blurple" event, which consists in recoloring our avatars and servers with a maximum of blurple, that characteristic color of Discord between purple and blue.

        For that, you have here some commands to blurplefy you. Notably the `blurplefy` command, which allows you to modify an image (by default your avatar or that of a friend) by changing its colors. Or why not `darkfy`, for a darker version. As well as `check`, to check that your image is up to Blurple:tm: standards.

        The modification commands (darkfy/lightfy) take into account several methods and variations.
        """
        methods_title = "3 methods"
        methods_desc = """`blurplefy` applies a basic blurplefy to your image
        `edge-detect` applies an algorithm to detect the edges of your image to make it easier to see
        `filter` applies a Blurple filter to your image (very good for images with many colors, also faster, but doesn't support variations)"""
        variations_title = "29 variations"
        variations_desc = """`++more-dark-blurple` adds more Dark Blurple
        `++more-blurple` adds more Blurple
        `++more-white` adds more White
        `++less-dark-blurple` removes some Dark Blurple
        `++less-blurple` removes some Blurple
        `++less-white` removes some White
        `++no-white` removes White
        `++no-blurple` removes Blurple
        `++no-dark-blurple` removes Dark Blurple from your image
        `++classic` uses the same Blurplefier as 2018
        `++less-gradient` removes some colors smoothness
        `++more-gradient` adds colors smoothness
        `++invert` swaps the darkest color and lightest color
        `++shift` shifts the colors over by one
        `++white-bg` replaces the transparency of your image with a white background
        `++blurple-bg` replaces the transparency of your image with a Blurple background
        `++dark-blurple-bg` replaces the transparency of your image with a Dark Blurple background"""
        if ctx.can_send_embed:
            embed = discord.Embed(title="Blurplefy help", description=desc, color=self.embed_color)
            embed.add_field(name=variations_title, value=variations_desc)
            embed.add_field(name=methods_title, value=methods_desc)
            await ctx.send(embed=embed)
        else:
            await ctx.send(desc + f"\n\n__{methods_title}:__\n{methods_desc}\n\n__{variations_title}:__\n{variations_desc}")

    async def color_command(self, fmodifier: typing.Literal["light", "dark"], ctx: MyContext,
                            method: BlurpleVariationFlagType = "blurplefy",
                            variations: commands.Greedy[ColorVariation] = None,
                            who: typing.Optional[TargetConverterType] = None):
        "Change a given image with the given modifier, method and variations"
        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).attach_files):
            await ctx.send(await self.bot._(ctx.channel, "color-event.missing-attachment-perm"))
            return

        url = await get_url_from_ctx(ctx, who)

        old_msg = await ctx.send(
            await self.bot._(ctx.channel, 'color-event.colorify.starting', name=fmodifier+'fy', user=ctx.author.mention)
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(url)) as image:
                    result = await convert_blurple(await image.read(), fmodifier, method, variations or [])
        except RuntimeError as err:
            await ctx.send(await self.bot._(ctx.channel, 'color-event.unknown-err', err=str(err)))
            return
        await ctx.reply(await self.bot._(ctx.channel, 'color-event.colorify.success', user=ctx.author.mention), file=result)
        if not isinstance(old_msg, discord.InteractionMessage):
            await old_msg.delete()
        if self.bot.database_online:
            await self.bot.get_cog("BotEvents").db_add_user_points(ctx.author.id, 3)

    @blurple_main.command("lightfy")
    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @commands.check(is_blurple)
    async def lightfy(self, ctx: MyContext, method: BlurpleVariationFlagType = "blurplefy",
                      variations: commands.Greedy[ColorVariation] = None,
                      who: typing.Optional[TargetConverterType] = None):
        "Lightfy an image"
        await self.color_command("light", ctx, method, variations, who)

    @blurple_main.command("darkfy")
    @commands.cooldown(6, 120, commands.BucketType.member)
    @commands.cooldown(20, 60, commands.BucketType.guild)
    @commands.check(is_blurple)
    async def darkfy(self, ctx: MyContext, method: BlurpleVariationFlagType = "blurplefy",
                      variations: commands.Greedy[ColorVariation] = None,
                      who: typing.Optional[TargetConverterType] = None):
        "Darkfy an image"
        await self.color_command("dark", ctx, method, variations, who)

    @blurple_main.command("check")
    @commands.cooldown(2, 60, commands.BucketType.member)
    @commands.cooldown(30, 40, commands.BucketType.guild)
    @commands.check(is_blurple)
    async def check(self, ctx: MyContext, who: typing.Optional[TargetConverterType] = None):
        """Check an image to know if you're cool enough.

        ..Example blurple check

        ..Example blurple check Axobot"""

        url = await get_url_from_ctx(ctx, who)

        old_msg = await ctx.send(await ctx.bot._(ctx.channel, "color-event.blurple.check.intro", user=ctx.author.mention))
        async with aiohttp.ClientSession() as session:
            async with session.get(str(url)) as image:
                result = await check_blurple(await image.read())
        answer = "\n".join(f"> {color['name']}: {color['ratio']}%" for color in result['colors'])
        await ctx.reply(await self.bot._(ctx.channel, "color-event.blurple.check.result", user=ctx.author.mention, results=answer))
        if result["passed"] and self.bot.database_online and ctx.author.id not in self.cache:
            reward_points = 40
            await self.bot.get_cog("BotEvents").db_add_user_points(ctx.author.id, reward_points)
            self.cache.append(ctx.author.id)
            with open("blurple-cache.json", "w", encoding="utf-8") as jsonfile:
                json.dump(self.cache, jsonfile)
            await ctx.send(await self.bot._(ctx.channel, "color-event.blurple.check.reward", user=ctx.author.mention, amount=reward_points))
        if not isinstance(old_msg, discord.InteractionMessage):
            await old_msg.delete()

async def setup(bot):
    await bot.add_cog(Blurplefy(bot))
