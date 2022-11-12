import json

from discord import app_commands
from discord.ext import commands

from libs.bot_classes import PRIVATE_GUILD_ID, MyContext, Zbot
from libs.twitch.api_agent import TwitchApiAgent


class Twitch(commands.Cog):
    "Handle twitch streams"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "twitch"
        self.agent = TwitchApiAgent()

    async def cog_load(self):
        await self.agent.api_login(
            self.bot.others["twitch_client_id"],
            self.bot.others["twitch_client_secret"]
        )
        self.bot.log.info("[twitch] connected to API")

    async def cog_unload(self):
        "Close the Twitch session"
        await self.agent.close_session()
        self.bot.log.info("[twitch] connection closed")
    
    @commands.hybrid_group(name="twitch")
    @app_commands.guilds(PRIVATE_GUILD_ID)
    @app_commands.default_permissions(manage_guild=True)
    @commands.guild_only()
    async def twitch(self, ctx: MyContext):
        "Twitch commands"
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @twitch.command(name="test")
    async def test_twitch(self, ctx: MyContext, *user: str):
        "Test the Twitch API"
        resp = await self.agent.get_user_stream(*user)
        await ctx.send(json.dumps(resp, indent=4))

    @twitch.command(name="status")
    async def ping_twitch(self, ctx: MyContext):
        "Check the twitch connection"
        await ctx.send(f"""{self.agent.is_token_valid = }
{self.agent.is_connected = }""")


async def setup(bot: Zbot):
    await bot.add_cog(Twitch(bot))