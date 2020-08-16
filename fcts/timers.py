import discord
from discord.ext import commands
import copy
import datetime

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

    @commands.command(name="remindme", aliases=['rmd'])
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remindme(self, ctx: commands.Context, *, args):
        """Create a new reminder
        This is actually an alias of `reminder create`
        """
        ctx.message.content = ctx.prefix + "reminder create " + args
        new_ctx = await self.bot.get_context(ctx.message)
        await self.bot.invoke(new_ctx)
    

    @commands.group(name="reminder", aliases=["remind", "reminds"])
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

        ..Doc miscellaneous.html#create-a-new-reminder
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

        ..Doc miscellaneous.html#list-your-reminders
        """
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = (f"SELECT *, CONVERT_TZ(`begin`, @@session.time_zone, '+00:00') AS `utc_begin` FROM `timed` WHERE user={ctx.author.id} AND action='timer'")
        cursor.execute(query)
        if cursor.rowcount == 0:
            await ctx.send(await self.translate(ctx.channel, "timers", "rmd-empty"))
            return
        txt = await self.translate(ctx.channel, "timers", "rmd-item")
        time_delta = self.bot.get_cog("TimeCog").time_delta
        lang = await self.translate(ctx.channel, "current_lang", "current")
        liste = list()
        for item in cursor:
            ctx2 = copy.copy(ctx)
            ctx2.message.content = item["message"]
            item["message"] = await commands.clean_content(fix_channel_mentions=True).convert(ctx2, item["message"])
            msg = item['message'] if len(item['message'])<=50 else item['message'][:47]+"..."
            msg = "`"+msg.replace('`', '\\`')+"`"
            chan = '<#'+str(item['channel'])+'>'
            end = item["utc_begin"] + datetime.timedelta(seconds=item['duration'])
            duration = await time_delta(datetime.datetime.utcnow(), end, lang=lang, year=True, form="temp", precision=0)
            item = txt.format(id=item['ID'], duration=duration, channel=chan, msg=msg)
            liste.append(item)
        cursor.close()
        if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            if len("\n".join(liste)) > 2000:
                desc = ""
                step = 5
                fields = [{"name":self.bot.zws, "value":"\n".join(liste[i:i+step])} for i in range(0, len(liste), step)][:25]
            else:
                desc = "\n".join(liste)
                fields = None
            emb = ctx.bot.get_cog("EmbedCog").Embed(title=await self.translate(ctx.channel, "timers", "rmd-title"), desc=desc, fields=fields, color=16108042)
            await ctx.send(embed=emb)
        else:
            t = "**"+await self.translate(ctx.channel, "timers", "rmd-title")+"**\n\n"
            await ctx.send(t+"\n".join(liste))
    
    @remind_main.command(name="delete", aliases=["remove", "del"])
    @commands.cooldown(5,30,commands.BucketType.user)
    async def remind_del(self, ctx:commands.Context, ID:int):
        """Delete a reminder
        ID can be found with the `reminder list` command.

        ..Example rmd delete 253

        ..Doc miscellaneous.html#delete-a-reminder
        """
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = (f"SELECT ID, message FROM `timed` WHERE user={ctx.author.id} AND action='timer' AND ID={ID}")
        cursor.execute(query)
        if cursor.rowcount == 0:
            await ctx.send(await self.translate(ctx.channel, "timers", "rmd-empty"))
            return
        item = list(cursor)[0]
        cursor.close()
        ctx2 = copy.copy(ctx)
        ctx2.message.content = item["message"]
        item["message"] = (await commands.clean_content(fix_channel_mentions=True).convert(ctx2, item["message"])).replace("`", "\\`")
        await self.bot.get_cog("Events").remove_task(item["ID"])
        await ctx.send(await self.translate(ctx.channel, "timers", "rmd-deleted", id=item["ID"], message=item["message"]))



def setup(bot: commands.Bot):
    bot.add_cog(TimersCog(bot))
