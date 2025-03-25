import asyncio
import datetime
import logging
import os
import random
import re
import string
import time
from collections import defaultdict
from io import BytesIO
from typing import Any, Literal

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from mysql.connector.errors import ProgrammingError as MySQLProgrammingError
from PIL import Image, ImageFont

from core.bot_classes import Axobot
from core.safedict import SafeDict
from core.tips import UserTip
from modules.serverconfig.src.converters import GuildMessageableChannel

from .cards import CardGeneration
from .src.top_paginator import LeaderboardScope, TopPaginator
from .src.types import UserVoiceConnection
from .src.xp_math import (get_level_from_xp_global, get_level_from_xp_mee6,
                          get_xp_from_level_global, get_xp_from_level_mee6)

XpSystemType = Literal["global", "mee6-like", "local"]

class Xp(commands.Cog):
    "XP system"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "xp"
        self.log = logging.getLogger("bot.xp")

        # map userId -> (last xp timestamp, xp count)
        self.leaderboard_cache: dict[int | Literal["global"], dict[int, tuple[int, int]]] = {"global": {}}
        # set of users suspected of cheating
        self.sus: set[int] | None = None
        # map of (guildId, userId) -> voice connection data
        self.voice_cache: dict[tuple[int, int], UserVoiceConnection] = {}
        # embed color for rank/top messages
        self.embed_color = discord.Colour(0xffcf50)
        # database table used to store global xp (local systems are stored in a different database)
        self.table = "xp_beta" if bot.beta else "xp"
        # seconds between each xp gain for global/local
        self.classic_xp_cooldown = 5
        # seconds between each xp gain for mee6-like
        self.mee6_xp_cooldown = 60
        # minimal length of a message to grant xp
        self.minimal_size = 5
        # maximum rate of each character in a message
        self.spam_rate = 0.20
        # xp granted per character
        self.xp_per_char = 0.11
        # maximum xp granted per message
        self.max_xp_per_msg = 70
        # default xp card style
        self.default_xp_style = "dark"

        verdana_font = "./assets/fonts/Verdana.ttf"
        roboto_font = "./assets/fonts/Roboto-Medium.ttf"
        self.fonts = {
            "xp_fnt": ImageFont.truetype(verdana_font, 24),
            "NIVEAU_fnt": ImageFont.truetype(verdana_font, 42),
            "levels_fnt": ImageFont.truetype(verdana_font, 65),
            "rank_fnt": ImageFont.truetype(verdana_font, 29),
            "RANK_fnt": ImageFont.truetype(verdana_font, 23),
            "name_fnt": ImageFont.truetype(roboto_font, 40),
        }

    @commands.Cog.listener()
    async def on_ready(self):
        "Load global cache"
        if not self.bot.database_online:
            await self.bot.unload_module("xp")
            return
        self.table = "xp_beta" if self.bot.beta else "xp"
        await self.db_load_cache(None)

    async def cog_load(self):
        # pylint: disable=no-member
        self.xp_decay_loop.start()
        self.clear_cards_loop.start()

    async def cog_unload(self):
        # pylint: disable=no-member
        if self.xp_decay_loop.is_running():
            self.xp_decay_loop.stop()
        if self.clear_cards_loop.is_running():
            self.clear_cards_loop.stop()

    async def get_lvlup_channel(self, member: discord.Member, fallback: discord.abc.GuildChannel | None) -> (
            None | discord.DMChannel | discord.TextChannel | discord.VoiceChannel | discord.StageChannel | discord.Thread):
        "Find the channel where to send the levelup message"
        value = await self.bot.get_config(member.guild.id, "levelup_channel")
        if value == "none":
            return None
        if value == "any" and fallback is not None:
            return fallback
        if value in ("dm", "any"):
            return member.dm_channel or await member.create_dm()
        return value

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Remove role rewards when a role is deleted"""
        if self.bot.database_online:
            await self.db_remove_rr_from_role(role.guild.id, role.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Register voice activity for potential XP rewards"""
        if member.bot or member.guild is None or not self.bot.database_online or not self.bot.xp_enabled:
            return
        if isinstance(before.channel, discord.VoiceChannel) and isinstance(after.channel, discord.VoiceChannel):
            return
        if (
            before.channel is None
            and after.channel != member.guild.afk_channel
            and isinstance(after.channel, discord.VoiceChannel)
        ): # user joined a channel
            self.voice_cache[(member.guild.id, member.id)] = UserVoiceConnection()
        elif (
            after.channel is None
            and before.channel != member.guild.afk_channel
            and isinstance(before.channel, discord.VoiceChannel)
        ): # user left a channel
            if connection_data := self.voice_cache.pop((member.guild.id, member.id), None):
                if member.guild.afk_channel is None or member.guild.afk_timeout == 0:
                    return
                used_xp_type: str = await self.bot.get_config(member.guild.id, "xp_type")
                if used_xp_type not in {"local", "mee6-like"}:
                    return
                if await self.is_member_restricted_from_xp(member, before.channel):
                    return
                await self.register_voice_xp(member, used_xp_type, before.channel.id, connection_data)

    @commands.Cog.listener(name="on_message")
    async def add_xp(self, msg: discord.Message):
        """Check conditions and grant xp to a user for written messages"""
        if not self.bot.xp_enabled or not self.bot.database_online:
            return
        if msg.author.bot or msg.is_system() or msg.flags.forwarded or msg.guild is None:
            return
        if await self.is_member_restricted_from_xp(msg.author, msg.channel):
            return
        if self.sus is None:
            if self.bot.get_cog("Utilities"):
                await self.reload_sus()
            else:
                self.sus = set()
        used_xp_type: str = await self.bot.get_config(msg.guild.id, "xp_type")
        if self.bot.zombie_mode:
            return
        if used_xp_type == "global":
            await self.register_written_xp__global(msg)
            return
        rate: float = await self.bot.get_config(msg.guild.id, "xp_rate")
        if used_xp_type == "mee6-like":
            await self.register_written_xp__mee6(msg, rate)
        elif used_xp_type == "local":
            await self.register_written_xp__local(msg, rate)

    async def register_voice_xp(self, member: discord.Member, used_xp_type: XpSystemType,
                                voice_channel_id: int,
                                connection_data: UserVoiceConnection):
        """Register voice activity for potential XP rewards
        This method assumes the xp system is not 'global', and always write to the guild table instead of the global table"""
        valuable_time_spent = connection_data.time_since_connection() - member.guild.afk_timeout * 1.5
        if valuable_time_spent < 0:
            # user may have been AFK
            return
        time_since_last_xp = connection_data.time_since_last_xp()
        if time_since_last_xp is None:
            time_since_last_xp = valuable_time_spent
        if time_since_last_xp is not None and time_since_last_xp < 60:
            # already got some XP for the last minute
            return
        if xp_per_minute := await self.bot.get_config(member.guild.id, "voice_xp_per_min"):
            prev_points = await self.get_member_xp(member, member.guild.id)
            rate: float = await self.bot.get_config(member.guild.id, "xp_rate")
            xp = round(xp_per_minute * rate * time_since_last_xp / 60)
            await self.db_set_xp(member.id, xp, "add", member.guild.id)
            connection_data.last_xp_time = time.time()
            await asyncio.sleep(0.5) # wait for potential temporary channels to be deleted
            try:
                voice_channel = await member.guild.fetch_channel(voice_channel_id)
            except discord.HTTPException:
                voice_channel = None
            await self.update_cache_and_execute_actions(member, voice_channel, used_xp_type, prev_points, xp)

    async def register_written_xp__global(self, msg: discord.Message):
        """Global xp type"""
        if msg.author.id in self.leaderboard_cache["global"]:
            if time.time() - self.leaderboard_cache["global"][msg.author.id][0] < self.classic_xp_cooldown:
                return
        content = msg.clean_content
        if len(content) < self.minimal_size or await self.check_spam(content):
            return
        if len(self.leaderboard_cache["global"]) == 0:
            await self.db_load_cache(None)
        giv_points = await self.calc_xp(msg)
        if giv_points == 0:
            return
        prev_points = await self.get_member_xp(msg.author, "global")
        await self.db_set_xp(msg.author.id, giv_points, "add")
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        await self.update_cache_and_execute_actions(msg.author, msg.channel, "global", prev_points, giv_points)

    async def register_written_xp__mee6(self, msg:discord.Message, rate: float):
        """MEE6-like xp type"""
        if msg.guild.id not in self.leaderboard_cache:
            await self.db_load_cache(msg.guild.id)
        if msg.author.id in self.leaderboard_cache[msg.guild.id]:
            if time.time() - self.leaderboard_cache[msg.guild.id][msg.author.id][0] < self.mee6_xp_cooldown:
                return
        giv_points = round(random.randint(15,25) * rate)
        prev_points = await self.get_member_xp(msg.author, msg.guild.id)
        await self.db_set_xp(msg.author.id, giv_points, "add", msg.guild.id)
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        await self.update_cache_and_execute_actions(msg.author, msg.channel, "mee6-like", prev_points, giv_points)

    async def register_written_xp__local(self, msg:discord.Message, rate: float):
        """Local xp type"""
        if msg.guild.id not in self.leaderboard_cache:
            await self.db_load_cache(msg.guild.id)
        if msg.author.id in self.leaderboard_cache[msg.guild.id]:
            if time.time() - self.leaderboard_cache[msg.guild.id][msg.author.id][0] < self.classic_xp_cooldown:
                return
        content = msg.clean_content
        if len(content) < self.minimal_size or await self.check_spam(content):
            return
        giv_points = round(await self.calc_xp(msg) * rate)
        if giv_points == 0:
            return
        prev_points = await self.get_member_xp(msg.author, msg.guild.id)
        await self.db_set_xp(msg.author.id, giv_points, "add", msg.guild.id)
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        await self.update_cache_and_execute_actions(msg.author, msg.channel, "local", prev_points, giv_points)

    async def is_member_restricted_from_xp(self, member: discord.Member, channel: discord.abc.GuildChannel) -> bool:
        "Returns True if the user cannot get xp due to the guild configuration"
        if not await self.bot.get_config(channel.guild.id, "enable_xp"):
            return True
        noxp_channels: list[GuildMessageableChannel] | None = await self.bot.get_config(channel.guild.id, "noxp_channels")
        if noxp_channels is not None and channel in noxp_channels:
            return True
        roles: list[discord.Role] | None = await self.bot.get_config(channel.guild.id, "noxp_roles")
        if roles is not None:
            for role in roles:
                if role in member.roles:
                    return True
        return False

    async def get_member_xp(self, member: discord.Member, system_id: int | Literal["global"]):
        "Get the current member XP value from the cache, or fetch from database"
        if member.id in self.leaderboard_cache.get(system_id, {}):
            return self.leaderboard_cache[system_id][member.id][1]
        if system_id == "global":
            return await self.db_get_xp(member.id, None) or 0
        return await self.db_get_xp(member.id, member.guild.id) or 0

    async def update_cache_and_execute_actions(self, member: discord.Member, channel: discord.abc.GuildChannel,
                                               system: XpSystemType, prev_points: int, points_to_give: int):
        """Update the XP cache, check for new level reached, and if need be send levelup/give role rewards"""
        system_id = "global" if system == "global" else member.guild.id
        self.leaderboard_cache[system_id][member.id] = [round(time.time()), prev_points+points_to_give]
        new_lvl, _, _ = await self.calc_level(self.leaderboard_cache[system_id][member.id][1], system)
        ex_lvl, _, _ = await self.calc_level(prev_points, system)
        if 0 < ex_lvl < new_lvl:
            await self.send_levelup(member, channel, new_lvl)
            await self.give_rr(member, new_lvl, await self.db_list_rr(system_id))

    async def send_levelup(self, member: discord.Member, channel: discord.abc.GuildChannel | None, lvl: int):
        """Envoie le message de levelup"""
        if self.bot.zombie_mode or member.guild is None:
            return
        destination = await self.get_lvlup_channel(member, channel)
        # if no destination could be found, or destination is in guild and bot can't send messages: abort
        if destination is None or (
            not isinstance(destination, discord.DMChannel) and not destination.permissions_for(member.guild.me).send_messages
        ):
            return
        text: str | None = await self.bot.get_config(member.guild.id, "levelup_msg")
        i18n_source = channel or member.guild
        if text is None or len(text) == 0:
            text = random.choice(await self.bot._(i18n_source, "xp.default_levelup"))
            while "{random}" not in text and random.random() < 0.7:
                text = random.choice(await self.bot._(i18n_source, "xp.default_levelup"))
        if "{random}" in text:
            item = random.choice(await self.bot._(i18n_source, "xp.levelup-items"))
        else:
            item = ''
        text = text.format_map(SafeDict(
            user=member.mention,
            level=lvl,
            random=item,
            username=member.display_name
        ))
        silent_message: bool = await self.bot.get_config(member.guild.id, "levelup_silent_mention")
        if isinstance(destination, discord.DMChannel) and member.guild:
            embed = discord.Embed(
                title=await self.bot._(destination, "xp.levelup-dm.title"),
                color=discord.Color.gold(),
                description=text
            )
            footer = await self.bot._(destination, "xp.levelup-dm.footer", servername=member.guild.name)
            embed.set_footer(text=footer, icon_url=member.guild.icon)
            await destination.send(embed=embed, silent=silent_message)
        else:
            await destination.send(text, silent=silent_message)

    async def check_spam(self, text: str):
        """Vérifie si un text contient du spam"""
        if len(text) > 0 and (text[0] in string.punctuation or text[1] in string.punctuation):
            return True
        characters_count: dict[str, int] = defaultdict(int)
        for character in text:
            characters_count[character] += 1
        for v in characters_count.values():
            if v/len(text) > self.spam_rate:
                return True
        return False

    async def calc_xp(self, msg: discord.Message):
        """Calcule le nombre d'xp correspondant à un message"""
        content = msg.clean_content
        matches = re.finditer(r"<a?(:\w+:)\d+>", content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0), match.group(1))
        matches = re.finditer(r"((?:http|www)[^\s]+)", content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0),"")
        return min(round(len(content)*self.xp_per_char), self.max_xp_per_msg)

    async def calc_level(self, xp: int, system: XpSystemType):
        """Calculate the level corresponding to a given xp amount
        Returns the current level, the xp needed for the next level and the xp needed for the current level"""
        if system == "mee6-like":
            if xp == 0:
                return (0, 100, 0)
            current_level = await get_level_from_xp_mee6(xp)
            xp_for_current_lvl = await get_xp_from_level_mee6(current_level)
            xp_for_next_lvl = await get_xp_from_level_mee6(current_level+1)
            return (current_level, xp_for_next_lvl, xp_for_current_lvl)
        # global/local system
        if xp == 0:
            xp_for_level_2 = await get_xp_from_level_global(2)
            return (1, xp_for_level_2, 0)
        current_level = await get_level_from_xp_global(xp)
        xp_for_current_lvl = await get_xp_from_level_global(current_level)
        xp_for_next_lvl = await get_xp_from_level_global(current_level+1)
        return (current_level, xp_for_next_lvl, xp_for_current_lvl)


    async def give_rr(self, member: discord.Member, level: int, rr_list: list[dict], remove: bool=False):
        """Give (and remove?) roles rewards to a member"""
        if not member.guild.me.guild_permissions.manage_roles:
            return 0
        count = 0
        has_roles = {role.id for role in member.roles}
        bot_top_role_position = member.guild.me.top_role.position
        # list roles to add to this member
        roles_to_give: list[discord.Role] = []
        for role in [rr for rr in rr_list if rr["level"] <= level and rr["role"] not in has_roles]:
            role = member.guild.get_role(role["role"])
            if role is None or role.position >= bot_top_role_position:
                continue
            roles_to_give.append(role)
        # give missing roles
        try:
            if not self.bot.beta:
                await member.add_roles(*roles_to_give, reason="Role rewards")
            count += len(roles_to_give)
        except Exception as err:
            if self.bot.beta:
                self.bot.dispatch("error", err)
        if not remove:
            return count
        # list roles to remove from this member
        roles_to_remove: list[discord.Role] = []
        for role in [rr for rr in rr_list if rr["level"] > level and rr["role"] in has_roles]:
            role = member.guild.get_role(role["role"])
            if role is None or role.position >= bot_top_role_position:
                continue
            roles_to_remove.append(role)
        # remove unauthorized roles
        try:
            if not self.bot.beta:
                await member.remove_roles(*roles_to_remove, reason="Role rewards")
            count += len(roles_to_remove)
        except Exception as err:
            if self.bot.beta:
                self.bot.dispatch("error", err)
        return count

    async def reload_sus(self):
        """Check who should be observed for potential xp cheating"""
        if not self.bot.database_online:
            return
        query = "SELECT userID FROM `users` WHERE `xp_suspect` = 1"
        async with self.bot.db_main.read(query) as query_result:
            if not query_result:
                return
            self.sus = {item["userID"] for item in query_result}
        self.log.info("Reloaded xp suspects (%s suspects)", len(self.sus))

    async def send_sus_msg(self, msg: discord.Message, xp: int):
        """Send a message into the sus channel"""
        chan = self.bot.get_channel(785877971944472597)
        emb = discord.Embed(
            title=f"#{msg.channel.name} | {msg.guild.name} | {msg.guild.id}",
            description=msg.content
        ).set_footer(text=str(msg.author.id)).set_author(
            name=str(msg.author),
            icon_url=msg.author.display_avatar.url).add_field(name="XP given", value=str(xp))
        await chan.send(embed=emb)


    async def get_table_name(self, guild: int, create_if_missing: bool=True):
        """Get the table name of a guild, and create one if no one exist"""
        if guild is None:
            return self.table
        try:
            async with self.bot.db_xp.read(f"SELECT 1 FROM `{guild}` LIMIT 1;"):
                return guild
        except MySQLProgrammingError:
            if create_if_missing:
                async with self.bot.db_xp.write(f"CREATE TABLE `{guild}` LIKE `example`;"):
                    self.log.info("[get_table] XP Table `%s` created", guild)
                async with self.bot.db_xp.read(f"SELECT 1 FROM `{guild}` LIMIT 1;"):
                    return guild
            return None


    async def db_set_xp(self, user_id: int, points: int, action: Literal["add", "set"]="add", guild_id: int | None=None):
        """Ajoute/reset de l'xp à un utilisateur dans la database"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_module("xp")
                return None
            if points <= 0:
                return True
            if guild_id is None:
                db = self.bot.db_main
            else:
                db = self.bot.db_xp
            table = await self.get_table_name(guild_id)
            if action == "add":
                query = f"INSERT INTO `{table}` (`userID`,`xp`) VALUES (%(u)s, %(p)s) ON DUPLICATE KEY UPDATE xp = xp + %(p)s;"
            else:
                query = f"INSERT INTO `{table}` (`userID`,`xp`) VALUES (%(u)s, %(p)s) ON DUPLICATE KEY UPDATE xp = %(p)s;"
            async with db.write(query, {'p': points, 'u': user_id}):
                pass
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False

    async def db_remove_user(self, user_id :int, guild_id: int | None=None):
        "Removes a user from the xp table"
        if not self.bot.database_online:
            await self.bot.unload_module("xp")
            return
        if guild_id is None:
            db = self.bot.db_main
        else:
            db = self.bot.db_xp
        table = await self.get_table_name(guild_id)
        query = f"DELETE FROM `{table}` WHERE `userID`=%(u)s;"
        async with db.write(query, {'u': user_id}):
            pass

    async def db_get_xp(self, user_id: int, guild_id: int | None) -> int | None:
        "Get the xp of a user in a guild"
        if not self.bot.database_online:
            await self.bot.unload_module("xp")
            return None
        if guild_id is None:
            db = self.bot.db_main
        else:
            db = self.bot.db_xp
        table = await self.get_table_name(guild_id, False)
        if table is None:
            return None
        query = f"SELECT `xp` FROM `{table}` WHERE `userID` = %s AND `banned` = 0"
        async with db.read(query, (user_id,), fetchone=True) as query_result:
            if query_result:
                g = "global" if guild_id is None else guild_id
                if isinstance(g, int) and g not in self.leaderboard_cache:
                    await self.db_load_cache(g)
                if user_id in self.leaderboard_cache[g].keys():
                    self.leaderboard_cache[g][user_id][1] = query_result["xp"]
                else:
                    self.leaderboard_cache[g][user_id] = [round(time.time())-60, query_result ["xp"]]
        return query_result["xp"] if query_result else None

    async def db_get_users_count(self, guild_id: int | None=None):
        """Get the number of ranked users in a guild (or in the global database)"""
        if not self.bot.database_online:
            await self.bot.unload_module("xp")
            return None
        if guild_id is None:
            db = self.bot.db_main
        else:
            db = self.bot.db_xp
        table = await self.get_table_name(guild_id, False)
        if table is None:
            return 0
        query = f"SELECT COUNT(*) FROM `{table}` WHERE `banned`=0"
        async with db.read(query, fetchone=True, astuple=True) as query_result:
            if isinstance(query_result, tuple) and len(query_result) == 1:
                return query_result[0]
            return 0

    async def db_load_cache(self, guild_id: int | None):
        "Load the XP cache for a given guild (or the global cache)"
        if not self.bot.database_online:
            await self.bot.unload_module("xp")
            return
        if guild_id is None:
            self.log.info("Loading XP cache (global)")
            db = self.bot.db_main
            query = f"SELECT `userID`,`xp` FROM `{self.table}` WHERE `banned`=0"
        else:
            self.log.info("Loading XP cache (guild %s)", guild_id)
            table = await self.get_table_name(guild_id, False)
            if table is None:
                self.leaderboard_cache[guild_id] = {}
                return
            db = self.bot.db_xp
            query = f"SELECT `userID`,`xp` FROM `{table}` WHERE `banned`=0"
        async with db.read(query) as rows:
            if not isinstance(rows, list):
                raise TypeError(f"rows should be a list, received {type(rows)}")
        if guild_id is None:
            self.leaderboard_cache["global"].clear()
            for row in rows:
                self.leaderboard_cache["global"][row["userID"]] = [round(time.time())-60, int(row["xp"])]
        else:
            if guild_id not in self.leaderboard_cache:
                self.leaderboard_cache[guild_id] = {}
            for row in rows:
                self.leaderboard_cache[guild_id][row["userID"]] = [round(time.time())-60, int(row["xp"])]

    async def db_get_top(self, limit: int=None, guild: discord.Guild=None):
        "Get the top of the guild (or the global top)"
        try:
            if not self.bot.database_online:
                await self.bot.unload_module("xp")
                return None
            if guild is not None and await self.bot.get_config(guild.id, "xp_type") != "global":
                db = self.bot.db_xp
                table = await self.get_table_name(guild.id, False)
                query = f"SELECT * FROM `{table}`ORDER BY `xp` DESC"
            else:
                db = self.bot.db_main
                query = f"SELECT * FROM `{self.table}` ORDER BY `xp` DESC"
            try:
                async with db.read(query) as rows:
                    if not isinstance(rows, list):
                        raise TypeError(f"rows should be a list, received {type(rows)}")
            except MySQLProgrammingError as err:
                if err.errno == 1146:
                    return []
                raise err
            result: list[dict[str, Any]]
            if guild is None:
                result = rows
                if limit is not None:
                    result = result[:limit]
            else:
                result = []
                ids = [x.id for x in guild.members]
                i = 0
                if limit is None:
                    limit = len(rows)
                while len(result) < limit and i < len(rows):
                    if rows[i]["userID"] in ids:
                        result.append(rows[i])
                    i += 1
            return result
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_rank(self, user_id: int, guild: discord.Guild=None):
        """Get the rank of a user"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_module("xp")
                return None
            if guild is not None and await self.bot.get_config(guild.id, "xp_type") != "global":
                db = self.bot.db_xp
                table = await self.get_table_name(guild.id, False)
                query = f"SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{table}` p, \
                    (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;"
            else:
                db = self.bot.db_main
                query = f"SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{self.table}` p, \
                    (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;"
            try:
                async with db.read(query) as rows:
                    if not isinstance(rows, list):
                        raise TypeError(f"cursor should be a list, received {type(rows)}")
            except MySQLProgrammingError as err:
                if err.errno == 1146:
                    return {"rank": 0, "xp": 0}
                raise err
            userdata = {}
            i = 0
            users = set()
            if guild is not None:
                users = {x.id for x in guild.members}
            for row in rows:
                if (guild is not None and row["userID"] in users) or guild is None:
                    i += 1
                if row["userID"]== user_id:
                    userdata = dict(row)
                    userdata["rank"] = round(userdata["rank"])
                    break
            return userdata
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_total_xp(self):
        """Get the total number of earned xp"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_module("xp")
                return None
            query = f"SELECT SUM(xp) as total FROM `{self.table}`"
            async with self.bot.db_main.read(query, fetchone=True) as query_results:
                result = round(query_results["total"])
            return result
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_guilds_decays(self):
        "Get a list of guilds where xp decay is enabled"
        query = "SELECT `guild_id`, CAST(`value` AS INT) AS 'value' FROM `serverconfig` WHERE `option_name` = 'xp_decay' AND `value` > 0 AND `beta` = %s"
        async with self.bot.db_main.read(query, (self.bot.beta,)) as query_result:
            return query_result

    @tasks.loop(time=datetime.time(hour=0, tzinfo=datetime.UTC))
    async def xp_decay_loop(self):
        "Remove some xp to every member every day at midnight"
        guilds = await self.db_get_guilds_decays()
        decay_query = "UPDATE `{table}` SET `xp` = GREATEST(CAST(`xp` AS SIGNED) - %s, 0)"
        cleanup_query = "DELETE FROM `{table}` WHERE `xp` <= 0"
        guilds_count = users_count = 0
        for guild_data in guilds:
            guild_id, value = guild_data["guild_id"], guild_data["value"]
            # check if axobot is still there
            if self.bot.get_guild(guild_id) is None:
                continue
            # check if xp_type is not 'global'
            if await self.bot.get_config(guild_id, "xp_type") == "global":
                continue
            # apply decay
            async with self.bot.db_xp.write(decay_query.format(table=guild_id), (value,), returnrowcount=True) as row_count:
                users_count += row_count
                # if xp has been edited, invalidate cache
                if row_count > 0 and guild_id in self.leaderboard_cache:
                    del self.leaderboard_cache[guild_id]
            # remove members with 0xp or less
            async with self.bot.db_xp.write(cleanup_query.format(table=guild_id), returnrowcount=True) as row_count:
                self.log.info("xp decay: removed %s members from guild %s", row_count, guild_id)
            guilds_count += 1
        log_text = f"XP decay: removed xp of {users_count} users from {guilds_count} guilds"
        emb = discord.Embed(description=log_text, color=0x66ffcc, timestamp=self.bot.utcnow())
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        self.bot.log.info(log_text)
        await self.bot.send_embed(emb, url="loop")

    @xp_decay_loop.before_loop
    async def before_xp_decay_loop(self):
        await self.bot.wait_until_ready()

    @xp_decay_loop.error
    async def on_xp_decay_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "XP decay loop has stopped  <@279568324260528128>")

    @tasks.loop(hours=1)
    async def clear_cards_loop(self, delete_all: bool=False):
        """Delete outdated rank cards

        A card is 'outdated' if the user generated another card with more total xp,
        so we sort the files list by total xp (descending) and keep only the first card of each user"""
        folder_path = "./assets/cards/"
        files = os.listdir(folder_path)
        done: set[str] = set()
        for f in sorted([f.split('-') for f in files if not f.startswith('.')], key=lambda f: int(f[1]), reverse=True):
            if delete_all or f[0] in done:
                os.remove(folder_path + "-".join(f))
            else:
                done.add(f[0])

    @clear_cards_loop.before_loop
    async def before_clear_cards_loop(self):
        await self.bot.wait_until_ready()

    @clear_cards_loop.error
    async def on_clear_cards_loop_error(self, error: Exception):
        self.bot.dispatch("error", error, "XP decay loop has stopped  <@279568324260528128>")


    async def get_image_from_url(self, url: str):
        "Download an image from an url"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return Image.open(BytesIO(await response.read()))


    @app_commands.command(name="rank")
    @app_commands.describe(user="The user to get the rank of. If not specified, it will be you.")
    @app_commands.checks.cooldown(1, 15)
    async def rank(self, interaction: discord.Interaction, user: discord.User | None = None):
        """Check how many xp you got
        If you don't specify any user, I'll send you your own XP

        ..Example rank

        ..Example rank @z_runner

        ..Doc xp.html#check-the-xp-of-someone
        """
        if user is None:
            user = interaction.user
        if user.bot:
            await interaction.response.send_message(
                await self.bot._(interaction, "xp.bot-rank"), ephemeral=True
            )
            return
        send_in_private = interaction.guild is None or await self.bot.get_config(interaction.guild_id, "rank_in_private")
        await interaction.response.defer(ephemeral=send_in_private)
        if interaction.guild is not None:
            if not await self.bot.get_config(interaction.guild_id, "enable_xp"):
                await interaction.followup.send(await self.bot._(interaction, "xp.xp-disabled"))
                return
            xp_used_type: str = await self.bot.get_config(interaction.guild_id, "xp_type")
        else:
            xp_used_type = (await self.bot.get_options_list())["xp_type"]["default"]
        xp = await self.db_get_xp(user.id, None if xp_used_type == "global" else interaction.guild_id)
        if xp is None:
            if interaction.user == user:
                await interaction.followup.send(await self.bot._(interaction, "xp.1-no-xp"))
            else:
                await interaction.followup.send(await self.bot._(interaction, "xp.2-no-xp"))
            return
        levels_info = await self.calc_level(xp, xp_used_type)
        if xp_used_type == "global":
            ranks_nb = await self.db_get_users_count()
            try:
                rank = (await self.db_get_rank(user.id))["rank"]
            except KeyError:
                rank = "?"
        else:
            ranks_nb = await self.db_get_users_count(interaction.guild_id)
            try:
                rank = (await self.db_get_rank(user.id, interaction.guild))["rank"]
            except KeyError:
                rank = "?"
        if isinstance(rank, float):
            rank = int(rank)
        send_in_private = interaction.guild is None or await self.bot.get_config(interaction.guild_id, "rank_in_private")
        # If we can send the rank card
        try:
            await self.send_card(interaction, user, xp, rank, ranks_nb, levels_info)
            return
        except Exception as err:  # pylint: disable=broad-except
            # log the error and fall back to embed/text
            self.bot.dispatch("error", err, interaction)
        # if we can send embeds
        await self.send_embed(interaction, user, xp, rank, ranks_nb, levels_info)

    async def create_card(self, translation_map: dict[str, str], user: discord.User, style: str, xp: int, rank: int,
                          ranks_nb: int, levels_info: tuple[int, int, int]):
        "Find the user rank card, or generate a new one, based on given data"
        static = not (
            user.display_avatar.is_animated()
            and await self.bot.get_cog("Users").db_get_user_config(user.id, "animated_card")
        )
        file_ext = "png" if static else "gif"
        filepath = f"./assets/cards/{user.id}-{xp}-{style}.{file_ext}"
        # check if the card has already been generated, and return it if it is the case
        if os.path.isfile(filepath):
            return discord.File(filepath)
        self.log.debug("Generating new XP card for user %s (xp=%s - style=%s - static=%s)", user.id, xp, style, static)
        user_avatar = await self.get_image_from_url(user.display_avatar.replace(format=file_ext, size=256).url)
        card_generator = CardGeneration(
            card_name=style,
            translation_map=translation_map,
            username=user.display_name,
            avatar=user_avatar,
            level=levels_info[0],
            rank=rank,
            participants=ranks_nb,
            xp_to_current_level=levels_info[2],
            xp_to_next_level=levels_info[1],
            total_xp=xp
        )
        generated_card = card_generator.draw_card()
        if isinstance(generated_card, list):
            duration = user_avatar.info["duration"]
            if card_generator.skip_second_frames:
                duration *= 2
            generated_card[0].save(
                filepath,
                save_all=True, append_images=generated_card[1:], duration=duration, loop=0, disposal=2
            )
        else:
            generated_card.save(filepath)
        card_image = discord.File(filepath, filename=f"{user.id}-{xp}-{rank}.{file_ext}")

        # update our internal stats for the number of cards generated
        if users_cog := self.bot.get_cog("Users"):
            try:
                await users_cog.db_used_rank(user.id)
            except Exception as err:
                self.bot.dispatch("error", err)
        if stats_cog := self.bot.get_cog("BotStats"):
            stats_cog.xp_cards["generated"] += 1
        return card_image

    async def get_card_translations_map(self, source) -> dict[str, str]:
        return {
            "LEVEL": await self.bot._(source, "xp.card-level"),
            "RANK": await self.bot._(source, "xp.card-rank"),
            "xp_left": await self.bot._(source, "xp.card-xp-left"),
            "total_xp": await self.bot._(source, "xp.card-xp-total"),
        }

    async def send_card(self, interaction: discord.Interaction, user: discord.User, xp: int, rank: int, ranks_nb: int,
                        levels_info: tuple[int, int, int]):
        """Generate and send a user rank card
        levels_info contains (current level, xp needed for the next level, xp needed for the current level)"""
        style = await self.bot.get_cog("Utilities").get_xp_style(user)
        translations_map = await self.get_card_translations_map(interaction)
        card_image = await self.create_card(translations_map, user, style, xp, rank, ranks_nb, levels_info)
        # check if we should send the card in DM or in the channel
        send_in_private = interaction.guild is None or await self.bot.get_config(interaction.guild_id, "rank_in_private")
        try:
            await interaction.followup.send(file=card_image, ephemeral=send_in_private)
        except discord.errors.HTTPException:
            await interaction.followup.send(await self.bot._(interaction, "xp.card-too-large"), ephemeral=True)
        else:
            if style == self.default_xp_style:
                try:
                    await self.send_rankcard_tip(interaction, ephemeral=send_in_private)
                except Exception as err:  # pylint: disable=broad-except
                    # if something goes wrong, don't notify the user
                    self.bot.dispatch("error", err, interaction)
        if stats_cog := self.bot.get_cog("BotStats"):
            stats_cog.xp_cards["sent"] += 1

    async def send_rankcard_tip(self, interaction: discord.Interaction, ephemeral: bool):
        "Send a tip about the rank card personalisation"
        if random.random() > 0.2:
            return
        if not await self.bot.get_cog("Users").db_get_user_config(interaction.user.id, "show_tips"):
            # tips are disabled
            return
        if await self.bot.tips_manager.should_show_user_tip(interaction.user.id, UserTip.RANK_CARD_PERSONALISATION):
        # user has not seen this tip yet
            profile_cmd = await self.bot.get_command_mention("profile card")
            await self.bot.tips_manager.send_user_tip(
                interaction,
                UserTip.RANK_CARD_PERSONALISATION,
                ephemeral=ephemeral,
                profile_cmd=profile_cmd
            )

    async def send_embed(self, interaction: discord.Interaction, user: discord.User, xp, rank, ranks_nb,
                         levels_info: tuple[int, int, int]):
        "Send the user rank as an embed (fallback from card generation)"
        txts = [await self.bot._(interaction, "xp.card-level"), await self.bot._(interaction, "xp.card-rank")]
        emb = discord.Embed(color=self.embed_color)
        emb.set_author(name=user.display_name, icon_url=user.display_avatar)
        emb.add_field(name="XP", value=f"{xp}/{levels_info[1]}")
        emb.add_field(name=txts[0].title(), value=levels_info[0])
        emb.add_field(name=txts[1].title(), value=f"{rank}/{ranks_nb}")
        send_in_private = await self.bot.get_config(interaction.guild_id, "rank_in_private")
        await interaction.followup.send(embed=emb, ephemeral=send_in_private)

    @app_commands.command(name="top")
    @app_commands.describe(page="The page number", scope="The scope of the leaderboard (global or server)")
    @app_commands.checks.cooldown(5, 60)
    async def top(self, interaction: discord.Interaction, page: app_commands.Range[int, 1]=1, scope: LeaderboardScope="global"):
        """Get the list of the highest XP users

        ..Example top

        ..Example top server

        ..Example top 7

        ..Doc xp.html#get-the-general-ranking"""
        if interaction.guild is not None and not await self.bot.get_config(interaction.guild_id, "enable_xp"):
            await interaction.response.send_message(
                await self.bot._(interaction, "xp.xp-disabled"), ephemeral=True
            )
            return
        await interaction.response.defer()
        _quit = await self.bot._(interaction, "misc.quit")
        view = TopPaginator(self.bot, interaction.user, interaction.guild, scope, page, _quit.capitalize())
        await view.fetch_data()
        msg = await view.send_init(interaction)
        await self.send_online_leaderboard_tip(interaction, url=view.url, ephemeral=True)
        if msg and await view.wait():
            # only manually disable if it was a timeout (ie. not a user stop)
            await view.disable(msg)

    async def send_online_leaderboard_tip(self, interaction: discord.Interaction, url: str, ephemeral: bool):
        "Send a tip about the leaderboard being available online"
        if random.random() > 0.8:
            return
        if not await self.bot.get_cog("Users").db_get_user_config(interaction.user.id, "show_tips"):
            # tips are disabled
            return
        if await self.bot.tips_manager.should_show_user_tip(interaction.user.id, UserTip.ONLINE_LEADERBOARD_ACCESS):
        # user has not seen this tip yet
            await self.bot.tips_manager.send_user_tip(
                interaction,
                UserTip.ONLINE_LEADERBOARD_ACCESS,
                ephemeral=ephemeral,
                url=url
            )


    @app_commands.command(name="set-xp")
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        user="The user to set the XP of",
        xp="The new XP value. Set to 0 to remove the user from the leaderboard",
    )
    @app_commands.guild_only()
    @app_commands.checks.cooldown(3, 15)
    async def set_xp(self, interaction: discord.Interaction, user: discord.User, xp: app_commands.Range[int, 0, 10**15]):
        """Set the XP of a user

        ..Example set_xp @someone 3000"""
        if user.bot:
            await interaction.response.send_message(
                await self.bot._(interaction, "xp.no-bot"), ephemeral=True
            )
            return
        # check if the xp system is enabled and local
        xp_used_type: str = await self.bot.get_config(interaction.guild_id, "xp_type")
        if xp_used_type == "global":
            await interaction.response.send_message(
                await self.bot._(interaction, "xp.change-global-xp"), ephemeral=True
            )
            return
        await interaction.response.defer()
        # get the current value (for internal logs)
        prev_xp = await self.db_get_xp(user.id, interaction.guild_id)
        # set the new xp value
        if xp == 0:
            await self.db_remove_user(user.id, interaction.guild_id)
        else:
            await self.db_set_xp(user.id, xp, action="set", guild_id=interaction.guild_id)
        # confirm success
        await interaction.followup.send(await self.bot._(interaction, "xp.change-xp-ok", user=str(user), xp=xp))
        # update cache
        if interaction.guild_id not in self.leaderboard_cache:
            await self.db_load_cache(interaction.guild_id)
        self.leaderboard_cache[interaction.guild_id][user.id] = [round(time.time()), xp]
        # send internal logs of the change
        desc = f"XP of user {user} `{user.id}` edited (from {prev_xp} to {xp}) in server `{interaction.guild_id}`"
        self.log.info(desc)
        emb = discord.Embed(description=desc, color=8952255, timestamp=self.bot.utcnow())
        emb.set_footer(text=interaction.guild.name)
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb)

    async def db_add_rr(self, guild_id: int, role_id: int, level:int):
        """Add a role reward in the database"""
        query = "INSERT INTO `roles_rewards` (`guild`, `role`, `level`) VALUES (%(g)s, %(r)s, %(l)s);"
        async with self.bot.db_main.write(query, { 'g': guild_id, 'r': role_id, 'l': level }):
            pass
        return True

    async def db_list_rr(self, guild_id: int, level: int = -1):
        """List role rewards in the database"""
        if level < 0:
            query = "SELECT * FROM `roles_rewards` WHERE `guild`=%s ORDER BY `level`;"
            query_args = (guild_id,)
        else:
            query = "SELECT * FROM `roles_rewards` WHERE `guild`=%s AND `level`=%s ORDER BY `level`;"
            query_args = (guild_id, level)
        async with self.bot.db_main.read(query, query_args) as query_results:
            liste = list(query_results)
        return liste

    async def db_remove_rr(self, role_reward_id: int):
        """Remove a role reward from the database"""
        query = "DELETE FROM `roles_rewards` WHERE `ID` = %s;"
        async with self.bot.db_main.write(query, (role_reward_id,)):
            pass
        return True

    async def db_remove_rr_from_role(self, guild_id: int, role_id: int):
        """Remove a role reward from the database"""
        query = "DELETE FROM `roles_rewards` WHERE `guild` = %s AND `role` = %s;"
        async with self.bot.db_main.write(query, (guild_id, role_id)):
            pass
        return True

    rr_main = app_commands.Group(
        name="roles-rewards",
        description="Manage your roles rewards like a boss",
        default_permissions=discord.Permissions(manage_roles=True),
        guild_only=True,
    )

    @rr_main.command(name="add")
    async def rr_add(self, interaction: discord.Interaction, level: app_commands.Range[int, 1], role: discord.Role):
        """Add a role reward
        This role will be given to every member who reaches the level

        ..Example rr add 10 Slowly farming

        ..Doc xp.html#roles-rewards"""
        if role.name == "@everyone":
            raise commands.BadArgument(f"Role \"{role.name}\" not found")
        await interaction.response.defer()
        l = await self.db_list_rr(interaction.guild_id)
        if len([x for x in l if x["level"]==level]) > 0:
            await interaction.followup.send(await self.bot._(interaction, "xp.already-1-rr"))
            return
        max_rr: int = await self.bot.get_config(interaction.guild_id, "rr_max_number")
        if len(l) >= max_rr:
            await interaction.followup.send(await self.bot._(interaction, "xp.too-many-rr", c=len(l)))
            return
        await self.db_add_rr(interaction.guild_id, role.id, level)
        await interaction.followup.send(await self.bot._(interaction, "xp.rr-added", role=role.name, level=level))

    @rr_main.command(name="list")
    async def rr_list(self, interaction: discord.Interaction):
        """List every roles rewards of your server

        ..Doc xp.html#roles-rewards"""
        await interaction.response.defer()
        if roles_list := await self.db_list_rr(interaction.guild_id):
            desc = '\n'.join([
                f"• <@&{x['role']}> : lvl {x['level']}"
                for x in roles_list
            ])
        else:
            roles_list = []
            desc = await self.bot._(
                interaction,
                "xp.no-rr-list",
                add=await self.bot.get_command_mention("roles-rewards add")
            )
        max_rr: int = await self.bot.get_config(interaction.guild_id, "rr_max_number")
        title = await self.bot._(interaction,"xp.rr_list", c=len(roles_list), max=max_rr)
        emb = discord.Embed(title=title, description=desc)
        await interaction.followup.send(embed=emb)

    @rr_main.command(name="remove")
    async def rr_remove(self, interaction: discord.Interaction, level: app_commands.Range[int, 1]):
        """Remove a role reward
        When a member reaches this level, no role will be given anymore

        ..Example roles-rewards remove 10

        ..Doc xp.html#roles-rewards"""
        await interaction.response.defer()
        roles_list = await self.db_list_rr(interaction.guild_id, level)
        if len(roles_list) == 0:
            await interaction.followup.send(await self.bot._(interaction, "xp.no-rr"))
            return
        await self.db_remove_rr(roles_list[0]["ID"])
        await interaction.followup.send(await self.bot._(interaction, "xp.rr-removed", level=level))

    @rr_main.command(name="reload")
    @app_commands.checks.cooldown(1, 300)
    async def rr_reload(self, interaction: discord.Interaction):
        """Refresh roles rewards for the whole server

        ..Doc xp.html#roles-rewards"""
        if not interaction.guild.me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                await self.bot._(interaction, "moderation.mute.cant-mute"), ephemeral=True
            )
            return
        await interaction.response.defer()
        count = 0
        rr_list = await self.db_list_rr(interaction.guild_id)
        if len(rr_list) == 0:
            await interaction.followup.send(await self.bot._(interaction, "xp.no-rr-2"))
            return
        used_system: str = await self.bot.get_config(interaction.guild_id, "xp_type")
        xps = [
            {"user": x["userID"], "xp": x["xp"]}
            for x in await self.db_get_top(limit=None, guild=None if used_system == "global" else interaction.guild)
        ]
        for member_data in xps:
            if member := interaction.guild.get_member(member_data["user"]):
                level = (await self.calc_level(member_data["xp"], used_system))[0]
                count += await self.give_rr(member, level, rr_list, remove=True)
        await interaction.followup.send(
            await self.bot._(interaction, "xp.rr-reload", role_count=count, member_count=interaction.guild.member_count)
        )


async def setup(bot: Axobot):
    if bot.database_online:
        await bot.add_cog(Xp(bot))
