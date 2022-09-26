import copy
import datetime
from typing import Optional

import discord
from discord.ext import commands
from libs.classes import ConfirmView, MyContext, Zbot
from libs.formatutils import FormatUtils

from . import args, checks

class ReminderSelectView(discord.ui.View):
    "Used to ask to select a reminder to delete"
    def __init__(self, reminders: list[dict], placeholder: str):
        super().__init__()
        options = self.build_options(reminders)
        self.select = discord.ui.Select(placeholder=placeholder, min_values=1, max_values=len(reminders), options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
        self.reminders: Optional[list[str]] = None

    def build_options(self, reminders: list[dict]):
        "Build the options list for Discord"
        res = []
        for reminder in reminders:
            if len(reminder['message']) > 90:
                reminder['message'] = reminder['message'][:89] + '…'
            label = reminder['message']
            desc = f"{reminder['tr_channel']} - {reminder['tr_duration']}"
            res.append(discord.SelectOption(value=reminder['id'], label=label, description=desc))
        return res

    async def disable(self, message: discord.Message):
        "Disable the view and update the message"
        self.select.disabled = True
        await message.edit(view=self)
        self.stop()

    async def callback(self, interaction: discord.Interaction):
        "Called when the dropdown menu has been validated by the user"
        self.reminders = self.select.values
        await interaction.response.defer()
        self.select.disabled = True
        await interaction.edit_original_response(view=self)
        self.stop()

class Timers(commands.Cog):
    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "timers"

    async def db_get_reminder(self, reminder_id: int, user: Optional[int] = None) -> Optional[dict]:
        if user is not None:
            query = "SELECT * FROM `timed` WHERE user=%s AND action='timer' AND ID=%s"
            args = (user, reminder_id)
        else:
            query = "SELECT * FROM `timed` WHERE action='timer' AND ID=%s"
            args = (reminder_id, )
        async with self.bot.db_query(query, args, fetchone=True) as query_result:
            return query_result

    async def db_get_user_reminders(self, user: int) -> list[dict]:
        "Get every active user reminder"
        query = "SELECT * FROM `timed` WHERE user=%s AND action='timer'"
        async with self.bot.db_query(query, (user,)) as query_results:
            return query_results

    async def db_get_user_reminders_count(self, user: int) -> int:
        "Get the number of active user reminder"
        query = "SELECT COUNT(*) as count FROM `timed` WHERE user=%s AND action='timer'"
        async with self.bot.db_query(query, (user,), fetchone=True) as query_results:
            return query_results["count"]

    async def db_delete_reminder(self, reminder_id: int, user: int):
        "Delete a reminder for a user"
        query = "DELETE FROM `timed` WHERE user=%s AND action='timer' AND ID=%s"
        async with self.bot.db_query(query, (user, reminder_id), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_delete_all_user_reminders(self, user: int):
        query = "DELETE FROM `timed` WHERE user=%s AND action='timer'"
        async with self.bot.db_query(query, (user,)) as query_results:
            pass

    @commands.command(name="remindme", aliases=['rmd'])
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remindme(self, ctx: MyContext, *, args):
        """Create a new reminder
        This is actually an alias of `reminder create`

        ..Example rmd 3h 5min It's pizza time!

        ..Example remindme 3months Christmas is coming!

        ..Doc miscellaneous.html#create-a-new-reminder"""
        ctx.message.content = ctx.prefix + ("reminder " if args.startswith('create') else "reminder create ") + args
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
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.too-short"))
            return
        if duration > 60*60*24*365*5:
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.too-long"))
            return
        f_duration = await FormatUtils.time_delta(duration,lang=await self.bot._(ctx.channel,'_used_locale'), year=True, form='developed')
        try:
            d = {'msg_url': ctx.message.jump_url}
            await ctx.bot.task_handler.add_task("timer", duration, ctx.author.id, ctx.guild.id if ctx.guild else None, ctx.channel.id, message, data=d)
        except Exception as err:
            await ctx.bot.get_cog("Errors").on_command_error(ctx, err)
        else:
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.saved", duration=f_duration))


    @remind_main.command(name="list")
    @commands.cooldown(5,60,commands.BucketType.user)
    async def remind_list(self, ctx: MyContext):
        """List your pending reminders

        ..Doc miscellaneous.html#list-your-reminders
        """
        reminders = await self.db_get_user_reminders(ctx.author.id)
        if len(reminders) == 0:
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.empty"))
            return
        txt = await self.bot._(ctx.channel, "timers.rmd.item")
        lang = await self.bot._(ctx.channel, '_used_locale')
        liste = []
        for item in reminders:
            ctx2 = copy.copy(ctx)
            ctx2.message.content = item["message"]
            item["message"] = await commands.clean_content(fix_channel_mentions=True).convert(ctx2, item["message"])
            msg = item['message'] if len(item['message'])<=50 else item['message'][:47]+"..."
            msg = discord.utils.escape_markdown(msg).replace("\n", " ")
            chan = '<#'+str(item['channel'])+'>'
            end: datetime.datetime = item["begin"] + datetime.timedelta(seconds=item['duration'])
            end = end.astimezone(datetime.timezone.utc)
            a = ctx.bot.utcnow() if end.tzinfo else datetime.datetime.utcnow()
            duration = await FormatUtils.time_delta(
                a, end,
                lang=lang, year=True, form="short"
            )
            item = txt.format(id=item['ID'], duration=duration, channel=chan, msg=msg)
            liste.append(item)
        if ctx.can_send_embed:
            emb = discord.Embed(title=await self.bot._(ctx.channel, "timers.rmd.title"),color=16108042)
            if len("\n".join(liste)) > 2000:
                step = 5
                for i in range(0, max(25,len(liste)), step):
                    emb.add_field(name=self.bot.zws, value="\n".join(liste[i:i+step]), inline=False)
            else:
                emb.description = "\n".join(liste)
            await ctx.send(embed=emb)
        else:
            text = "**"+await self.bot._(ctx.channel, "timers.rmd.title")+"**\n\n".join(liste)
            await ctx.send(text)

    async def ask_reminder_ids(self, input_id: Optional[int], ctx: MyContext, title: str) -> Optional[list[int]]:
        "Ask the user to select reminder IDs"
        selection = []
        if input_id is not None:
            input_reminder = await self.db_get_reminder(input_id, ctx.author.id)
            if not input_reminder:
                input_id = None
            else:
                selection.append(input_reminder["ID"])
        if input_id is None:
            reminders = await self.db_get_user_reminders(ctx.author.id)
            if len(reminders) == 0:
                await ctx.send(await self.bot._(ctx.channel, "timers.rmd.empty"))
                return
            reminders_data: list[dict] = []
            lang = await self.bot._(ctx.channel, '_used_locale')
            for reminder in reminders[:25]:
                rmd_data = {
                    "id": reminder["ID"],
                    "message": reminder["message"]
                }
                # channel name
                if channel := self.bot.get_channel(reminder["channel"]):
                    rmd_data["tr_channel"] = "#" + channel.name
                else:
                    rmd_data["tr_channel"] = reminder["channel"]
                # duration
                end: datetime.datetime = reminder["begin"] + datetime.timedelta(seconds=reminder['duration'])
                end = end.astimezone(datetime.timezone.utc)
                duration = await FormatUtils.time_delta(ctx.bot.utcnow(), end, lang=lang, year=True, form="short")
                rmd_data["tr_duration"] = duration
                # append to the list
                reminders_data.append(rmd_data)
            form_placeholder = await self.bot._(ctx.channel, 'timers.rmd.select-placeholder')
            view = ReminderSelectView(reminders_data, form_placeholder)
            msg = await ctx.send(title, view=view)
            await view.wait()
            if view.reminders is None:
                # timeout
                await view.disable(msg)
                return
            try:
                selection = list(map(int, view.reminders))
            except ValueError:
                selection = []
                self.bot.dispatch("error", ValueError(f"Invalid reminder IDs: {view.reminders}"), ctx)
        if len(selection) == 0:
            await ctx.send(await self.bot._(ctx.guild, "rss.fail-add"))
            return
        return selection

    @remind_main.command(name="delete", aliases=["remove", "del"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def remind_del(self, ctx: MyContext, ID: Optional[int] = None):
        """Delete a reminder
        ID can be found with the `reminder list` command.

        ..Example reminders delete

        ..Example reminders delete 253

        ..Doc miscellaneous.html#delete-a-reminder
        """
        ids = await self.ask_reminder_ids(ID, ctx, await ctx.bot._(ctx.channel, "timers.rmd.delete.title"))
        if ids is None:
            return
        count = 0
        for reminder_id in ids:
            if await self.db_delete_reminder(reminder_id, ctx.author.id):
                await self.bot.task_handler.remove_task(reminder_id)
                count += 1
        await ctx.send(await self.bot._(ctx.channel, "timers.rmd.delete.success", count=count))

    @remind_main.command(name="clear")
    @commands.cooldown(3, 60, commands.BucketType.user)
    async def remind_clear(self, ctx: MyContext):
        """Remove every pending reminder

        ..Doc miscellaneous.html#clear-every-reminders"""
        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).add_reactions):
            await ctx.send(await self.bot._(ctx.channel, "fun.cant-react"))
            return
        count = await self.db_get_user_reminders_count(ctx.author.id)
        if count == 0:
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.empty"))
            return

        confirm_view = ConfirmView(self.bot, ctx.channel,
            validation=lambda inter: inter.user==ctx.author,
            timeout=20)
        await confirm_view.init()
        await ctx.send(await self.bot._(ctx.channel, "timers.rmd.confirm", count=count), view=confirm_view)

        await confirm_view.wait()
        if confirm_view.value is None:
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.cancelled"))
            return
        if confirm_view.value:
            await self.db_delete_all_user_reminders(ctx.author.id)
            await ctx.send(await self.bot._(ctx.channel, "timers.rmd.cleared"))


async def setup(bot):
    await bot.add_cog(Timers(bot))
