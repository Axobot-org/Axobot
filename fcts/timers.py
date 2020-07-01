import discord
from discord.ext import commands
import copy

from fcts import args

class TimersCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
        self.file = "timers"
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr

    @commands.command(name="remindme")
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remindme(self, ctx: commands.Context, *, args):
        """Create a new reminder
        This is actually an alias of `reminder create`
        """
        ctx.message.content = ctx.prefix + "reminder create " + args
        new_ctx = await self.bot.get_context(ctx.message)
        await self.bot.invoke(new_ctx)
    
    
    @commands.group(name="reminder", aliases=["remind", "reminds", "rmd"])
    async def remind_main(self, ctx:commands.Context):
        """Ask the bot to remind you of something later

..Doc miscellaneous.html#reminders"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['reminder'])
    
    
    @remind_main.command(name="create", aliases=["add"])
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remind_create(self, ctx:commands.Context, duration:commands.Greedy[args.tempdelta], *, message):
        """Create a new reminder
        
        Please use the following format:
        `XXm` : XX minutes
        `XXh` : XX hours
        `XXd` : XX days
        `XXw` : XX weeks

        ..Example remindme create 49d Think about doing my homework
        """
        duration = sum(duration)
        if duration < 1:
            await ctx.send(await self.translate(ctx.channel, "fun", "reminds-too-short"))
            return
        if duration > 60*60*24*365*2:
            await ctx.send(await self.translate(ctx.channel, "fun", "reminds-too-long"))
            return
        if not self.bot.database_online:
            await ctx.send(await self.translate(ctx.channel, "rss", "no-db"))
            return
        f_duration = await ctx.bot.get_cog('TimeCog').time_delta(duration,lang=await self.translate(ctx.guild,'current_lang','current'), year=True, form='developed', precision=0)
        try:
            await ctx.bot.get_cog('Events').add_task("timer", duration, ctx.author.id, ctx.guild.id if ctx.guild else None, ctx.channel.id, message)
        except Exception as e:
            await ctx.send(await self.translate(ctx.channel, "server", "change-1"))
            await ctx.bot.get_cog("ErrorsCog").on_cmd_error(ctx,e)
        else:
            await ctx.send(await self.translate(ctx.channel, "fun", "reminds-saved", duration=f_duration))


    @remind_main.command(name="list")
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remind_list(self, ctx:commands.Context):
        """List your pending reminders
        """
        pass


def setup(bot: commands.Bot):
    bot.add_cog(TimersCog(bot))
