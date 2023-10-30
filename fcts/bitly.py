from discord.ext import commands

from libs import bitly_api
from libs.arguments import args
from libs.bot_classes import Axobot, MyContext


class Bitly(commands.Cog):
    "Shorten or expand urls using Bitly services"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "bitly"
        self.bitly_client = bitly_api.Bitly(api_key=self.bot.others['bitly'])

    @commands.group(name="bitly")
    async def bitly_main(self, ctx: MyContext):
        """Bit.ly website, but in Discord
        Create shortened url and unpack them by using Bitly services

        ..Doc miscellaneous.html#bitly-urls"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)
        elif ctx.invoked_subcommand is None and ctx.subcommand_passed is not None:
            try:
                url = await args.URL.convert(ctx,ctx.subcommand_passed)
            except commands.BadArgument:
                return
            if url.domain in ['bit.ly','bitly.com','bitly.is']:
                await self.bitly_find(ctx, url)
            else:
                await self.bitly_create(ctx, url)

    @bitly_main.command(name="create", aliases=["shorten"])
    async def bitly_create(self, ctx: MyContext, url: args.URL):
        """Create a shortened url

        ..Example bitly create https://fr-minecraft.net

        ..Doc miscellaneous.html#bitly-urls"""
        if url.domain == 'bit.ly':
            return await ctx.send(await self.bot._(ctx.channel,'info.bitly_already_shortened'))
        await ctx.send(await self.bot._(ctx.channel,'info.bitly_short', url=self.bitly_client.shorten_url(url.url)))

    @bitly_main.command(name="find", aliases=['expand'])
    async def bitly_find(self, ctx: MyContext, url: args.URL):
        """Find the long url from a bitly link

        ..Example bitly find https://bit.ly/2JEHsUf

        ..Doc miscellaneous.html#bitly-urls"""
        if url.domain != 'bit.ly':
            return await ctx.send(await self.bot._(ctx.channel,'info.bitly_nobit'))
        await ctx.send(await self.bot._(ctx.channel,'info.bitly_long', url=self.bitly_client.expand_url(url.url)))


async def setup(bot):
    await bot.add_cog(Bitly(bot))
