from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord

from core.enums import ServerWarningType
from core.formatutils import FormatUtils

from .types import DbTask
from .views import RecreateReminderView

if TYPE_CHECKING:
    from core.bot_classes import Axobot

class TaskHandler:
    "Handler for timed tasks (like reminders or planned unban)"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.log = logging.getLogger("bot.tasks")

    async def get_events_from_db(self, get_all: bool = False) -> list[DbTask]:
        """Renvoie une liste de tous les events qui doivent être exécutés"""
        try:
            query = ("SELECT * FROM `timed` WHERE beta=%s")
            events: list[dict] = []
            async with self.bot.db_query(query, (self.bot.beta,)) as query_results:
                for row in query_results:
                    row["begin"] = row["begin"].replace(tzinfo=timezone.utc)
                    if get_all:
                        events.append(row)
                    else:
                        now = self.bot.utcnow() if row["begin"].tzinfo else datetime.utcnow()
                        if row["begin"] + timedelta(seconds=row["duration"]) < now:
                            events.append(row)
            return events
        except Exception as err:  # pylint: disable=broad-except
            self.bot.dispatch("error", err)
            return []

    async def check_tasks(self):
        "Fetch and execute pending tasks"
        await self.bot.wait_until_ready()
        if not self.bot.database_online:
            return
        tasks_list = await self.get_events_from_db()
        if len(tasks_list) == 0:
            return
        self.log.debug("Iterating (%s tasks found)", len(tasks_list))
        for task in tasks_list:
            if task["action"] == "mute":
                try:
                    guild = self.bot.get_guild(task["guild"])
                    if guild is None:
                        continue
                    user = guild.get_member(task["user"])
                    if user is None:
                        continue
                    try:
                        await self.bot.get_cog("Moderation").unmute_member(guild, user, guild.me)
                    except discord.Forbidden:
                        continue
                    self.bot.dispatch("tempmute_expiration", guild, user, task["begin"])
                    await self.remove_task(task["ID"])
                except Exception as err:  # pylint: disable=broad-except
                    self.bot.dispatch("error", err)
                    self.log.error("Unmute: Unable to auto unmute %s", err)
            if task["action"] == "ban":
                try:
                    guild = self.bot.get_guild(task["guild"])
                    if guild is None:
                        continue
                    try:
                        user = await self.bot.fetch_user(task["user"])
                    except discord.DiscordException:
                        continue
                    try:
                        await guild.unban(user, reason="Temp ban expired"+self.bot.zws)
                    except discord.Forbidden:
                        await self.remove_task(task["ID"])
                        continue
                    self.bot.dispatch("tempban_expiration", guild, user, task["begin"])
                    await self.remove_task(task["ID"])
                except discord.errors.NotFound:
                    await self.remove_task(task["ID"])
                except Exception as err:  # pylint: disable=broad-except
                    self.bot.dispatch("error", err)
                    self.log.error("Unban: Unable to auto unban: %s", err)
            if task["action"] == "timer":
                try:
                    sent = await self.task_timer(task)
                except discord.errors.NotFound:
                    await self.remove_task(task["ID"])
                except Exception as err:  # pylint: disable=broad-except
                    self.bot.dispatch("error", err)
                    self.log.error("Reminder: Unable to send timer: %s", err)
                else:
                    if sent:
                        await self.remove_task(task["ID"])
            if task["action"] == "role-grant":
                try:
                    guild = self.bot.get_guild(task["guild"])
                    if guild is None:
                        continue
                    user = guild.get_member(task["user"])
                    if user is None:
                        continue
                    try:
                        data = json.loads(task["data"])
                    except (json.JSONDecodeError, KeyError):
                        continue
                    role = guild.get_role(data["role"])
                    if role is not None:
                        try:
                            await user.remove_roles(role, reason="Temp role expired")
                        except discord.Forbidden:
                            self.bot.dispatch(
                                "server_warning",
                                ServerWarningType.TEMP_ROLE_REMOVE_FORBIDDEN,
                                guild,
                                role=role,
                                user=user
                            )
                            self.log.warning("RoleGrant: Unable to remove temporary role: Forbidden")
                    await self.remove_task(task["ID"])
                except Exception as err:  # pylint: disable=broad-except
                    self.bot.dispatch("error", err)
                    self.log.error("RoleGrant: Unable to remove temporary role: %s", err)

    async def _get_or_fetch_user(self, user_id: int):
        if user := self.bot.get_user(user_id):
            return user
        try:
            return await self.bot.fetch_user(user_id)
        except discord.NotFound:
            pass
        return None

    async def task_timer(self, task: dict) -> bool:
        """Send a reminder
        Returns True if the reminder has been sent"""
        if task["user"] is None:
            return True
        if task["guild"] is not None:
            guild = self.bot.get_guild(task["guild"])
            if guild is None:
                return False
            channel = guild.get_channel_or_thread(task["channel"])
            member = await guild.fetch_member(task["user"])
            # if channel has been deleted, or if member left the guild, we send it in DM
            if channel is None or member is None or not channel.permissions_for(guild.me).send_messages:
                channel = await self._get_or_fetch_user(task["user"])
                if channel is None:
                    return False
        else:
            channel = await self._get_or_fetch_user(task["user"])
            if not channel:
                return False
        user = channel if isinstance(channel, discord.User) else self.bot.get_user(task["user"])
        if user is None:
            raise discord.errors.NotFound
        try:
            if self.bot.zombie_mode:
                return False
            f_duration = await FormatUtils.time_delta(task["duration"],
                                                      lang=await self.bot._(channel, "_used_locale"),
                                                      form="developed")

            if task["data"] is not None:
                task["data"] = json.loads(task["data"])
            text = await self.bot._(channel, "timers.rmd.embed-asked", user=user.mention, duration=f_duration)
            view = RecreateReminderView(self.bot, task)
            await view.init()
            if isinstance(channel, discord.User | discord.DMChannel) or channel.permissions_for(guild.me).embed_links:
                if task["data"] is not None and "msg_url" in task["data"]:
                    click_here = await self.bot._(channel, "timers.rmd.embed-link")
                    task["message"] += f'\n\n[{click_here}]({task["data"]["msg_url"]})'
                title = (await self.bot._(channel, "timers.rmd.embed-title")).capitalize()
                emb = discord.Embed(title=title, description=task["message"], color=4886754, timestamp=task["begin"])
                emb.set_footer(text=await self.bot._(channel, "timers.rmd.embed-date"))
                imgs = re.findall(r"(https://\S+\.(?:png|jpe?g|webp|gif))", task["message"])
                if len(imgs) > 0:
                    emb.set_image(url=imgs[0])
                msg = await channel.send(text, embed=emb, view=view)
                view.message = msg
            else:
                msg = await channel.send(text+"\n"+task["message"], view=view)
                view.message = msg
        except discord.errors.Forbidden:
            return False
        except Exception as err:  # pylint: disable=broad-except
            raise err
        return True

    async def add_task(self, action: str, duration: int, userid: int, guildid: int | None = None,
                       channelid: int | None = None, message: str | None = None, data: dict | None = None):
        """Add a task to the list"""
        tasks_list = await self.get_events_from_db(get_all=True)
        for task in tasks_list:
            if (task["user"] == userid
                    and task["guild"] == guildid
                    and task["action"] == action
                    and task["channel"] == channelid
                    and task["action"] != "timer"):
                return await self.update_duration(task["ID"], duration)
        data = None if data is None else json.dumps(data)
        query = "INSERT INTO `timed` (`guild`,`channel`,`user`,`action`,`duration`,`message`, `data`, `beta`) VALUES (%(guild)s,%(channel)s,%(user)s,%(action)s,%(duration)s,%(message)s,%(data)s,%(beta)s)"
        query_args = {
            "guild": guildid,
            "channel": channelid,
            "user": userid,
            "action": action,
            "duration": duration,
            "message": message,
            "data": data,
            "beta": self.bot.beta
        }
        async with self.bot.db_query(query, query_args):
            pass
        return True

    async def update_duration(self, task_id: int, new_duration: int):
        """Edit a task duration"""
        query = f"UPDATE `timed` SET `duration`={new_duration} WHERE `ID`={task_id}"
        async with self.bot.db_query(query):
            pass
        return True

    async def remove_task(self, task_id: int):
        """Remove a task (usually after execution)"""
        query = f"DELETE FROM `timed` WHERE `timed`.`ID` = {task_id}"
        async with self.bot.db_query(query):
            pass
        return True

    async def cancel_unmute(self, user_id: int, guild_id: int):
        """Cancel every automatic unmutes for a member"""
        try:
            query = "DELETE FROM `timed` WHERE action='mute' AND guild=%s AND user=%s AND beta=%s;"
            async with self.bot.db_query(query, (guild_id, user_id, self.bot.beta)):
                pass
        except Exception as err:  # pylint: disable=broad-except
            self.bot.dispatch("error", err)
