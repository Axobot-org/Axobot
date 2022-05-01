import copy
import discord
from discord.ext import commands
from libs.classes import Zbot, MyContext
from libs.antiscam import AntiScamAgent, Message

from fcts import checks

def is_immune(member: discord.Member) -> bool:
    "Check if a member is immune to the anti-scam feature"
    return (member.bot
            or member.guild_permissions.administrator
            or member.guild_permissions.manage_messages
            or member.guild_permissions.manage_guild)

class AntiScam(commands.Cog):
    "Anti scam feature which read every message and detect if they are malicious"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "antiscam"
        self.agent = AntiScamAgent()

    async def send_bot_log(self, msg: discord.Message):
        "Send a log to the bot internal log channel"
        emb = discord.Embed(title="Scam message deleted", description=msg.content, color=discord.Color.red())
        emb.set_author(name=msg.author, icon_url=msg.author.display_avatar)
        emb.set_footer(text=f"{msg.guild.name} ({msg.guild.id})" if msg.guild else "No guild")
        await self.bot.send_embed([emb])

    @commands.group(name="antiscam")
    async def antiscam(self, ctx: MyContext):
        """Everything related to the antiscam feature

        ..Doc moderator.html#anti-scam"""

    @antiscam.command(name="test")
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def antiscam_test(self, ctx: MyContext, *, msg: str):
        """Test the antiscam feature with a given message

        ..Example antiscam test free nitro for everyone at bit.ly/tomato"""
        data = Message.from_raw(msg, 0)
        pred = self.agent.predict_bot(data)
        await ctx.send(pred.to_string(self.agent.categories) + f"\nURL risk score: {data.url_score}")

    @antiscam.command(name="enable")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def antiscam_enable(self, ctx: MyContext):
        """Enable the anti scam feature in your server

        ..Doc moderator.html#anti-scam"""
        msg: discord.Message = copy.copy(ctx.message)
        msg.content =  f'{ctx.prefix}config change anti_scam true'
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @antiscam.command(name="disable")
    @commands.guild_only()
    @commands.check(checks.has_manage_guild)
    async def antiscam_disable(self, ctx: MyContext):
        """Disable the anti scam feature in your server

        ..Doc moderator.html#anti-scam"""
        msg: discord.Message = copy.copy(ctx.message)
        msg.content =  f'{ctx.prefix}config change anti_scam false'
        new_ctx = await self.bot.get_context(msg)
        await self.bot.invoke(new_ctx)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        "Check any message for scam dangerousity"
        if not msg.guild or len(msg.content) < 10 or is_immune(msg.author) or await self.bot.potential_command(msg):
            return
        await self.bot.wait_until_ready()
        if not await self.bot.get_config(msg.guild.id, "anti_scam"):
            return
        message: Message = Message.from_raw(msg.content, len(msg.mentions))
        if len(message.normd_message) < 3:
            return
        result = self.agent.predict_bot(message)
        if result.result > 1:
            message.category = 0
            print("GOT", message.message, result.probabilities[2])
            if result.probabilities[1] < 0.005: # if probability of not being harmless is less than 0.5%
                try:
                    await msg.delete() # try to delete it, silently fails
                except discord.Forbidden:
                    pass
                await self.send_bot_log(msg)
                self.bot.dispatch("antiscam_delete", msg, result)
                # msg_id = await bot.insert_msg(message)
                # await bot.send_report(msg, msg_id, message)
            elif result.probabilities[1] < 0.3:
                self.bot.dispatch("antiscam_warn", msg, result)


async def setup(bot):
    await bot.add_cog(AntiScam(bot))
