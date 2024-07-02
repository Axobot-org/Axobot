import datetime
import time

import discord
from asyncache import cached
from cachetools import TTLCache
from discord import app_commands
from discord.ext import commands

from core.arguments import args
from core.bot_classes import Axobot
from core.checks import checks
from core.formatutils import FormatUtils
from core.paginator import PaginatedSelectView
from core.views import ConfirmView

ReminderTextArgument = app_commands.Range[str, 1, 1000]

class Timers(commands.Cog):
    "Reminders system"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "timers"

    async def db_get_reminder(self, reminder_id: int, user: int | None = None) -> dict | None:
        "Get a specific reminder for a user"
        if user is not None:
            query = "SELECT * FROM `timed` WHERE user=%s AND action='timer' AND ID=%s AND `beta`=%s"
            q_args = (user, reminder_id, self.bot.beta)
        else:
            query = "SELECT * FROM `timed` WHERE action='timer' AND ID=%s AND `beta`=%s"
            q_args = (reminder_id, self.bot.beta)
        async with self.bot.db_query(query, q_args, fetchone=True) as query_result:
            return query_result

    async def db_get_user_reminders(self, user: int) -> list[dict]:
        "Get every active user reminder"
        query = "SELECT * FROM `timed` WHERE user=%s AND action='timer' AND `beta`=%s"
        async with self.bot.db_query(query, (user, self.bot.beta)) as query_results:
            return query_results

    async def db_get_user_reminders_count(self, user: int) -> int:
        "Get the number of active user reminder"
        query = "SELECT COUNT(*) as count FROM `timed` WHERE user=%s AND action='timer' AND `beta`=%s"
        async with self.bot.db_query(query, (user, self.bot.beta), fetchone=True) as query_results:
            return query_results["count"]

    async def db_delete_reminder(self, reminder_id: int, user: int):
        "Delete a reminder for a user"
        query = "DELETE FROM `timed` WHERE user=%s AND action='timer' AND ID=%s AND `beta`=%s"
        async with self.bot.db_query(query, (user, reminder_id, self.bot.beta), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_delete_reminders(self, reminder_ids: list[int], user: int) -> bool:
        "Delete multiple reminders for a user"
        list_placeholder = ",".join(["%s"] * len(reminder_ids))
        query = f"DELETE FROM `timed` WHERE user=%s AND action='timer' AND ID IN ({list_placeholder})"
        async with self.bot.db_query(query, (user, *reminder_ids), returnrowcount=True) as query_result:
            return query_result > 0

    async def db_delete_all_user_reminders(self, user: int):
        "Delete every reminder for a user"
        query = "DELETE FROM `timed` WHERE user=%s AND action='timer' AND `beta`=%s"
        async with self.bot.db_query(query, (user, self.bot.beta)) as _:
            pass

    async def db_register_reminder_snooze(self, original_duration: int, new_duration: int):
        "Register a snooze"
        query = "INSERT INTO `reminder_snoozes_logs` (`original_duration`, `snooze_duration`, `beta`) VALUES (%s, %s, %s)"
        async with self.bot.db_query(query, (original_duration, new_duration, self.bot.beta)):
            pass

    @cached(TTLCache(1_000, ttl=60))
    async def format_duration_left(self, end_date: datetime.datetime, lang: str) -> str:
        "Format the duration left for a reminder"
        now = self.bot.utcnow()
        if now > end_date:
            return "-" + await FormatUtils.time_delta(
                end_date, now,
                lang=lang, year=True, seconds=False, form="short"
            )
        return await FormatUtils.time_delta(
            now, end_date,
            lang=lang, year=True, seconds=False, form="short"
        )

    @cached(TTLCache(1_000, ttl=30))
    async def _get_reminders_for_choice(self, user_id: int):
        "Returns a list of reminders for a given user"
        return await self.db_get_user_reminders(user_id)

    @cached(TTLCache(1_000, ttl=60))
    async def _format_reminder_choice(self, current: str, lang: str, reminder_id: int, begin_date: datetime.datetime,
                                      duration: str, reminder_message: str
                                      ) -> tuple[bool, float, app_commands.Choice[str]] | None:
        "Format a reminder for a discord Choice"
        end_date: datetime.datetime = begin_date + datetime.timedelta(seconds=duration)
        f_duration = await self.format_duration_left(end_date, lang)
        label: str = f_duration + " - " + reminder_message
        if current not in label:
            return None
        if len(label) > 40:
            label = label[:37] + "..."
        choice = app_commands.Choice(value=str(reminder_id), name=label)
        priority = not reminder_message.lower().startswith(current)
        return (priority, -end_date.timestamp(), choice)


    @cached(TTLCache(1_000, ttl=30))
    async def get_reminders_choice(self, user_id: int, lang: str, current: str) -> list[app_commands.Choice[str]]:
        "Returns a list of reminders Choice for a given user, matching the current input"
        reminders = await self._get_reminders_for_choice(user_id)
        if len(reminders) == 0:
            return []
        choices: list[tuple[bool, int, app_commands.Choice[str]]] = []
        for reminder in reminders:
            if formated_reminder := await self._format_reminder_choice(
                current, lang, reminder["ID"], reminder["begin"], reminder["duration"], reminder["message"]
                ):
                choices.append(formated_reminder)
        return [choice for _, _, choice in sorted(choices, key=lambda x: x[0:2])]


    @app_commands.command(name="remindme")
    @app_commands.describe(duration="The duration to wait, eg. '2d 4h'", message="The message to remind you of")
    @app_commands.checks.cooldown(5, 60)
    @app_commands.check(checks.database_connected)
    async def remindme(self, interaction: discord.Interaction, duration: args.GreedyDurationArgument,
                       message: ReminderTextArgument):
        """Create a new reminder
        This is actually an alias of `/reminder create`

        Please use the following duration format:
        `XXm` : XX minutes
        `XXh` : XX hours
        `XXd` : XX days
        `XXw` : XX weeks
        `XXm` : XX months

        ..Example remindme 3h 5min It's pizza time!

        ..Example remindme 3months Christmas is coming!

        ..Doc miscellaneous.html#create-a-new-reminder"""
        await self._create_reminder(interaction, duration, message)


    remind_main = app_commands.Group(
        name="reminders",
        description="Manage your pending reminders",
    )

    @remind_main.command(name="create")
    @app_commands.describe(duration="The duration to wait, eg. '2d 4h'", message="The message to remind you of")
    @app_commands.checks.cooldown(5, 60)
    @app_commands.check(checks.database_connected)
    async def remind_create(self, interaction: discord.Interaction, duration: args.GreedyDurationArgument,
                            message: ReminderTextArgument):
        """Create a new reminder

        Please use the following duration format:
        `XXm` : XX minutes
        `XXh` : XX hours
        `XXd` : XX days
        `XXw` : XX weeks
        `XXm` : XX months

        ..Example reminders create 49d Think about doing my homework

        ..Example reminders create 3h 5min It's pizza time!

        ..Doc miscellaneous.html#create-a-new-reminder
        """
        await self._create_reminder(interaction, duration, message)

    async def _create_reminder(self, interaction: discord.Interaction, duration: int, message: str):
        "Create a new reminder, from either '/remindme' or '/reminder create'"
        if duration <= 0:
            await interaction.response.send_message(
                await self.bot._(interaction, "timers.rmd.too-short"), ephemeral=True
            )
            return
        if duration > 60*60*24*365*5:
            await interaction.response.send_message(
                await self.bot._(interaction, "timers.rmd.too-long"), ephemeral=True
            )
            return
        await interaction.response.defer()
        lang = await self.bot._(interaction, "_used_locale")
        f_duration = await FormatUtils.time_delta(duration, lang=lang, year=True, form="developed")
        if msg := await interaction.original_response():
            data = {"msg_url": msg.jump_url}
        else:
            data = {}
        await self.bot.task_handler.add_task(
            "timer",
            duration,
            interaction.user.id,
            interaction.guild_id,
            interaction.channel.id,
            message,
            data
        )
        timestamp = f"<t:{time.time() + duration:.0f}>"
        await interaction.followup.send(
            await self.bot._(interaction, "timers.rmd.saved", duration=f_duration, timestamp=timestamp)
        )


    @remind_main.command(name="list")
    @app_commands.checks.cooldown(5, 60)
    @app_commands.check(checks.database_connected)
    async def remind_list(self, interaction: discord.Interaction):
        """List your pending reminders

        ..Doc miscellaneous.html#list-your-reminders
        """
        await interaction.response.defer(ephemeral=interaction.guild is not None)
        reminders = await self.db_get_user_reminders(interaction.user.id)
        if len(reminders) == 0:
            await interaction.followup.send(await self.bot._(interaction, "timers.rmd.empty"))
            return
        txt = await self.bot._(interaction, "timers.rmd.item")
        lang = await self.bot._(interaction, "_used_locale")
        reminders_formated_list: list[int, str] = []
        ctx = await commands.Context.from_interaction(interaction)
        for item in reminders:
            item["message"] = await commands.clean_content(fix_channel_mentions=True).convert(ctx, item["message"])
            msg = item["message"] if len(item["message"])<=50 else item["message"][:47]+"..."
            msg = discord.utils.escape_markdown(msg).replace("\n", " ")
            chan = f"<#{item['channel']}>"
            end: datetime.datetime = item["begin"] + datetime.timedelta(seconds=item["duration"])
            duration = await self.format_duration_left(end, lang)
            item = txt.format(id=item["ID"], duration=duration, channel=chan, msg=msg)
            reminders_formated_list.append((-end.timestamp(), item))
        reminders_formated_list.sort()
        labels = [item[1] for item in reminders_formated_list]
        emb = discord.Embed(title=await self.bot._(interaction, "timers.rmd.title"),color=16108042)
        if len("\n".join(labels)) > 2000:
            step = 5
            for i in range(0, max(25, len(labels)), step):
                emb.add_field(name=self.bot.zws, value="\n".join(labels[i:i+step]), inline=False)
        else:
            emb.description = "\n".join(labels)
        await interaction.followup.send(embed=emb)

    async def transform_reminders_options(self, reminders: list[dict]):
        "Transform reminders data into discord SelectOption"
        res = []
        for reminder in reminders:
            if len(reminder["message"]) > 90:
                reminder["message"] = reminder["message"][:89] + '…'
            label = reminder["message"]
            desc = f"{reminder['tr_channel']} - {reminder['tr_duration']}"
            res.append(discord.SelectOption(value=str(reminder["id"]), label=label, description=desc))
        return res

    async def ask_reminder_ids(self, input_id: int | None, interaction: discord.Interaction, title: str) -> list[int] | None:
        "Ask the user to select reminder IDs"
        selection = []
        if input_id is not None:
            input_reminder = await self.db_get_reminder(input_id, interaction.user.id)
            if not input_reminder:
                input_id = None
            else:
                selection.append(input_reminder["ID"])
        if input_id is None:
            reminders = await self.db_get_user_reminders(interaction.user.id)
            if len(reminders) == 0:
                await interaction.followup.send(await self.bot._(interaction, "timers.rmd.empty"))
                return
            reminders_data: list[dict] = []
            lang = await self.bot._(interaction, "_used_locale")
            for reminder in reminders:
                rmd_data = {
                    "id": reminder["ID"],
                    "message": reminder["message"]
                }
                # channel name
                if channel := self.bot.get_channel(reminder["channel"]):
                    rmd_data["tr_channel"] = "DM" if isinstance(channel, discord.abc.PrivateChannel) else ("#" + channel.name)
                else:
                    rmd_data["tr_channel"] = reminder["channel"]
                # duration
                end: datetime.datetime = reminder["begin"] + datetime.timedelta(seconds=reminder["duration"])
                now = self.bot.utcnow()
                if now > end:
                    duration = "-" + await FormatUtils.time_delta(
                        end, now,
                        lang=lang, year=True, form="short", seconds=False
                    )
                else:
                    duration = await FormatUtils.time_delta(
                        now, end,
                        lang=lang, year=True, form="short", seconds=False
                    )
                rmd_data["tr_duration"] = duration
                # append to the list
                reminders_data.append(rmd_data)
            form_placeholder = await self.bot._(interaction, "timers.rmd.select-placeholder")
            view = PaginatedSelectView(self.bot,
                message=title,
                options=await self.transform_reminders_options(reminders_data),
                user=interaction.user,
                placeholder=form_placeholder,
                max_values=len(reminders_data)
            )
            msg = await view.send_init(interaction)
            await view.wait()
            if view.values is None:
                # timeout
                await view.disable(msg)
                return
            try:
                if isinstance(view.values, str):
                    selection = [int(view.values)]
                else:
                    selection = list(map(int, view.values))
            except ValueError:
                selection = []
                self.bot.dispatch("error", ValueError(f"Invalid reminder IDs: {view.values}"), interaction)
        if len(selection) == 0:
            cmd = await self.bot.get_command_mention("about")
            await interaction.followup.send(await self.bot._(interaction, "errors.unknown2", about=cmd))
            return
        return selection

    @remind_main.command(name="cancel")
    @app_commands.checks.cooldown(5, 30)
    @app_commands.check(checks.database_connected)
    async def remind_del(self, interaction: discord.Interaction, reminder_id: int | None = None):
        """Delete a reminder
        ID can be found with the `reminder list` command.

        ..Example reminders cancel

        ..Example reminders cancel 253

        ..Doc miscellaneous.html#delete-a-reminder
        """
        ephemeral = interaction.guild is not None
        await interaction.response.defer(ephemeral=ephemeral)
        ids = await self.ask_reminder_ids(reminder_id, interaction, await self.bot._(interaction, "timers.rmd.delete.title"))
        if ids is None:
            return
        if await self.db_delete_reminders(ids, interaction.user.id):
            for rmd_id in ids:
                await self.bot.task_handler.remove_task(rmd_id)
            await interaction.followup.send(
                await self.bot._(interaction, "timers.rmd.delete.success", count=len(ids)),
                ephemeral=ephemeral
            )
        else:
            await interaction.followup.send(
                await self.bot._(interaction, "timers.rmd.delete.error"),
                ephemeral=ephemeral
            )
            try:
                raise ValueError(f"Failed to delete reminders: {ids}")
            except ValueError as err:
                self.bot.dispatch("error", err, interaction)

    @remind_del.autocomplete("reminder_id")
    async def remind_del_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete for the reminder ID"
        try:
            return await self.get_reminders_choice(interaction.user.id, "en", current.lower())
        except Exception as err:
            self.bot.dispatch("interaction_error", interaction, err)

    @remind_main.command(name="clear")
    @app_commands.checks.cooldown(3, 60)
    @app_commands.check(checks.database_connected)
    async def remind_clear(self, interaction: discord.Interaction):
        """Remove every pending reminder

        ..Doc miscellaneous.html#clear-every-reminders"""
        ephemeral = interaction.guild is not None
        await interaction.response.defer(ephemeral=ephemeral)
        count = await self.db_get_user_reminders_count(interaction.user.id)
        if count == 0:
            await interaction.followup.send(await self.bot._(interaction, "timers.rmd.empty"), ephemeral=ephemeral)
            return

        confirm_view = ConfirmView(self.bot, interaction.channel,
            validation=lambda inter: inter.user==interaction.user,
            timeout=20
        )
        await confirm_view.init()
        await interaction.followup.send(
            await self.bot._(interaction, "timers.rmd.confirm", count=count), view=confirm_view,
            ephemeral=ephemeral
        )

        await confirm_view.wait()
        await confirm_view.disable(interaction)
        if confirm_view.value is None:
            await interaction.followup.send(await self.bot._(interaction, "timers.rmd.cancelled"), ephemeral=ephemeral)
            return
        if confirm_view.value:
            await self.db_delete_all_user_reminders(interaction.user.id)
            await interaction.followup.send(await self.bot._(interaction, "timers.rmd.cleared"), ephemeral=ephemeral)


    @commands.Cog.listener()
    async def on_reminder_snooze(self, initial_duration: int, snooze_duration: int):
        "Called when a reminder is snoozed"
        await self.db_register_reminder_snooze(initial_duration, snooze_duration)


async def setup(bot):
    await bot.add_cog(Timers(bot))
