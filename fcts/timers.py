import asyncio
import discord
from discord.ext import commands
import copy
import datetime

from fcts import args, checks
from utils import zbot, MyContext

class Timers(commands.Cog):
    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "timers"

    @commands.command(name="remindme", aliases=['rmd'])
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remindme(self, ctx: MyContext, *, args):
        """Create a new reminder
        This is actually an alias of `reminder create`
        
        ..Example rmd 3h 5min It's pizza time!

        ..Doc miscellaneous.html#create-a-new-reminder"""
        ctx.message.content = ctx.prefix + "reminder create " + args
        new_ctx = await self.bot.get_context(ctx.message)
        await self.bot.invoke(new_ctx)
    

    @commands.group(name="reminder", aliases=["remind", "reminds", "reminders"])
    async def remind_main(self, ctx: MyContext):
        """Ask the bot to remind you of something later

        ..Doc miscellaneous.html#reminders"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx,['reminder'])
    
    
    @remind_main.command(name="create", aliases=["add"])
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    @commands.check(checks.database_connected)
    async def remind_create(self, ctx: MyContext, duration: commands.Greedy[args.tempdelta], *, message):
        """Create a new reminder
        
        Please use the following format:
        `XXm` : XX minutes
        `XXh` : XX hours
        `XXd` : XX days
        `XXw` : XX weeks

        ..Example reminder create 49d Think about doing my homework

        ..Doc miscellaneous.html#create-a-new-reminder
        """
        duration = sum(duration)
        if duration < 1:
            await ctx.send(await self.bot._(ctx.channel, "fun", "reminds-too-short"))
            return
        if duration > 60*60*24*365*5:
            await ctx.send(await self.bot._(ctx.channel, "fun", "reminds-too-long"))
            return
        f_duration = await ctx.bot.get_cog('TimeUtils').time_delta(duration,lang=await self.bot._(ctx.channel,'current_lang','current'), year=True, form='developed', precision=0)
        try:
            d = {'msg_url': ctx.message.jump_url}
            await ctx.bot.get_cog('Events').add_task("timer", duration, ctx.author.id, ctx.guild.id if ctx.guild else None, ctx.channel.id, message, data=d)
        except Exception as e:
            await ctx.bot.get_cog("Errors").on_command_error(ctx,e)
        else:
            await ctx.send(await self.bot._(ctx.channel, "fun", "reminds-saved", duration=f_duration))


    @remind_main.command(name="list")
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remind_list(self, ctx: MyContext):
        """List your pending reminders

        ..Doc miscellaneous.html#list-your-reminders
        """
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = (f"SELECT *, CONVERT_TZ(`begin`, @@session.time_zone, '+00:00') AS `utc_begin` FROM `timed` WHERE user={ctx.author.id} AND action='timer'")
        cursor.execute(query)
        if cursor.rowcount == 0:
            await ctx.send(await self.bot._(ctx.channel, "timers", "rmd-empty"))
            return
        txt = await self.bot._(ctx.channel, "timers", "rmd-item")
        time_delta = self.bot.get_cog("TimeUtils").time_delta
        lang = await self.bot._(ctx.channel, "current_lang", "current")
        liste = list()
        for item in cursor:
            ctx2 = copy.copy(ctx)
            ctx2.message.content = item["message"]
            item["message"] = await commands.clean_content(fix_channel_mentions=True).convert(ctx2, item["message"])
            msg = item['message'] if len(item['message'])<=50 else item['message'][:47]+"..."
            msg = discord.utils.escape_markdown(msg).replace("\n", " ")
            # msg = "\n```\n" + msg.replace("```", "​`​`​`") + "\n```"
            chan = '<#'+str(item['channel'])+'>'
            end = item["utc_begin"] + datetime.timedelta(seconds=item['duration'])
            duration = await time_delta(datetime.datetime.utcnow(), end, lang=lang, year=True, form="temp", precision=0)
            item = txt.format(id=item['ID'], duration=duration, channel=chan, msg=msg)
            liste.append(item)
        cursor.close()
        if ctx.can_send_embed:
            if len("\n".join(liste)) > 2000:
                desc = ""
                step = 5
                fields = [{"name":self.bot.zws, "value":"\n".join(liste[i:i+step])} for i in range(0, len(liste), step)][:25]
            else:
                desc = "\n".join(liste)
                fields = None
            emb = ctx.bot.get_cog("Embeds").Embed(title=await self.bot._(ctx.channel, "timers", "rmd-title"), desc=desc, fields=fields, color=16108042)
            await ctx.send(embed=emb)
        else:
            t = "**"+await self.bot._(ctx.channel, "timers", "rmd-title")+"**\n\n"
            await ctx.send(t+"\n".join(liste))
    
    @remind_main.command(name="delete", aliases=["remove", "del"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def remind_del(self, ctx: MyContext, ID: int):
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
            await ctx.send(await self.bot._(ctx.channel, "timers", "rmd-empty"))
            return
        item = list(cursor)[0]
        cursor.close()
        ctx2 = copy.copy(ctx)
        ctx2.message.content = item["message"]
        item["message"] = (await commands.clean_content(fix_channel_mentions=True).convert(ctx2, item["message"])).replace("`", "\\`")
        await self.bot.get_cog("Events").remove_task(item["ID"])
        await ctx.send(await self.bot._(ctx.channel, "timers", "rmd-deleted", id=item["ID"], message=item["message"]))
    
    @remind_main.command(name="clear")
    @commands.cooldown(3, 45, commands.BucketType.user)
    async def remind_clear(self, ctx: MyContext):
        """Remove every pending reminder
        
        ..Doc miscellaneous.html#clear-every-reminders"""
        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).add_reactions):
            await ctx.send(await self.bot._(ctx.channel, "fun", "cant-react"))
            return
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        query = "SELECT COUNT(*) as count FROM `timed` WHERE action='timer' AND user=%s"
        cursor.execute(query, (ctx.author.id,))
        count = list(cursor)[0]['count']
        if count == 0:
            await ctx.send(await self.bot._(ctx.channel, "timers", "rmd-empty"))
            return
        msg = await ctx.send(await self.bot._(ctx.channel, "timers", "rmd-confirm", count=count))
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')
        
        def check(reaction: discord.Reaction, user: discord.Member):
            return user==ctx.author and reaction.message == msg and str(reaction.emoji) in ('✅', '❌')
        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
        except asyncio.TimeoutError:
            cursor.close()
            await ctx.send(await self.bot._(ctx.channel, 'timers', 'rmd-cancelled'))
            return
        if str(reaction.emoji) == '❌':
            cursor.close()
            await ctx.send(await self.bot._(ctx.channel, 'timers', 'rmd-cancelled'))
            return
        query = "DELETE FROM `timed` WHERE action='timer' AND user=%s"
        cursor.execute(query, (ctx.author.id,))
        cnx.commit()
        cursor.close()
        await ctx.send(await self.bot._(ctx.channel, 'timers', 'rmd-cleared'))


def setup(bot: commands.Bot):
    bot.add_cog(Timers(bot))
