import importlib
import operator
import os
import random
import re
import string
import time
from collections import defaultdict
from io import BytesIO
from math import ceil
from typing import Literal, Optional, TypedDict

import aiohttp
import discord
import mysql
from cachingutils import acached
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageFont

from libs.arguments import args
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks
from libs.paginator import Paginator
from libs.serverconfig.options_list import options
from libs.tips import UserTip
from libs.xp_cards.generator import CardGeneration

importlib.reload(args)
importlib.reload(checks)

LeaderboardScope = Literal["global", "server"]


class Xp(commands.Cog):
    "XP system"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.cache = {'global':{}}
        self.levels = [0]
        self.embed_color = discord.Colour(0xffcf50)
        self.table = 'xp_beta' if bot.beta else 'xp'
        self.classic_xp_cooldown = 5 # seconds between each xp gain for global/local
        self.mee6_xp_cooldown = 60 # seconds between each xp gain for mee6-like
        self.minimal_size = 5
        self.spam_rate = 0.20
        self.xp_per_char = 0.11
        self.max_xp_per_msg = 70
        self.file = 'xp'
        self.sus = None
        self.default_xp_style = "dark"
        self.types = ['global','mee6-like','local']
        verdana_font = "./assets/fonts/Verdana.ttf"
        roboto_font = "./assets/fonts/Roboto-Medium.ttf"
        self.fonts = {
            'xp_fnt': ImageFont.truetype(verdana_font, 24),
            'NIVEAU_fnt': ImageFont.truetype(verdana_font, 42),
            'levels_fnt': ImageFont.truetype(verdana_font, 65),
            'rank_fnt': ImageFont.truetype(verdana_font, 29),
            'RANK_fnt': ImageFont.truetype(verdana_font, 23),
            'name_fnt': ImageFont.truetype(roboto_font, 40),
        }

    @commands.Cog.listener()
    async def on_ready(self):
        self.table = 'xp_beta' if self.bot.beta else 'xp'
        await self.db_load_cache(None)
        if not self.bot.database_online:
            await self.bot.unload_extension("fcts.xp")

    async def get_lvlup_chan(self, msg: discord.Message) -> discord.abc.Messageable:
        "Find the channel where to send the levelup message"
        value = await self.bot.get_config(msg.guild.id, "levelup_channel")
        if value == "none":
            return None
        if value == "any":
            return msg.channel
        if value == "dm":
            return msg.author.dm_channel or await msg.author.create_dm()
        return value

    @commands.Cog.listener(name="on_message")
    async def add_xp(self, msg: discord.Message):
        """Attribue un certain nombre d'xp à un message"""
        if msg.author.bot or msg.guild is None or not self.bot.xp_enabled:
            return
        # If axobot is already there, let it handle it
        if await self.bot.check_axobot_presence(guild=msg.guild, channel_id=msg.channel.id):
            return
        used_xp_type: str = await self.bot.get_config(msg.guild.id, "xp_type")
        if await self.check_noxp(msg) or not await self.bot.get_config(msg.guild.id, "enable_xp"):
            return
        rate: float = await self.bot.get_config(msg.guild.id, "xp_rate")
        if self.sus is None:
            if self.bot.get_cog('Utilities'):
                await self.reload_sus()
            else:
                self.sus = set()
        if self.bot.zombie_mode:
            return
        if used_xp_type == "global":
            await self.add_xp_0(msg, rate)
        elif used_xp_type == "mee6-like":
            await self.add_xp_1(msg, rate)
        elif used_xp_type == "local":
            await self.add_xp_2(msg, rate)

    async def add_xp_0(self, msg: discord.Message, _rate: float):
        """Global xp type"""
        if msg.author.id in self.cache['global']:
            if time.time() - self.cache['global'][msg.author.id][0] < self.classic_xp_cooldown:
                return
        content = msg.clean_content
        if len(content) < self.minimal_size or await self.check_spam(content) or await self.bot.potential_command(msg):
            return
        if len(self.cache["global"]) == 0:
            await self.db_load_cache(None)
        giv_points = await self.calc_xp(msg)
        if giv_points == 0:
            return
        if msg.author.id in self.cache['global']:
            prev_points = self.cache['global'][msg.author.id][1]
        else:
            prev_points = await self.db_get_xp(msg.author.id, None) or 0
        await self.db_set_xp(msg.author.id, giv_points, 'add')
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        self.cache['global'][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl, _, _ = await self.calc_level(self.cache['global'][msg.author.id][1], "global")
        ex_lvl, _, _ = await self.calc_level(prev_points, "global")
        if 0 < ex_lvl < new_lvl:
            await self.send_levelup(msg, new_lvl)
            await self.give_rr(msg.author, new_lvl, await self.rr_list_role(msg.guild.id))

    async def add_xp_1(self, msg:discord.Message, rate: float):
        """MEE6-like xp type"""
        if msg.guild.id not in self.cache:
            await self.db_load_cache(msg.guild.id)
        if msg.author.id in self.cache[msg.guild.id]:
            if time.time() - self.cache[msg.guild.id][msg.author.id][0] < self.mee6_xp_cooldown:
                return
        if await self.bot.potential_command(msg):
            return
        giv_points = round(random.randint(15,25) * rate)
        if msg.author.id in self.cache[msg.guild.id]:
            prev_points = self.cache[msg.guild.id][msg.author.id][1]
        else:
            prev_points = await self.db_get_xp(msg.author.id, msg.guild.id) or 0
        await self.db_set_xp(msg.author.id, giv_points, 'add', msg.guild.id)
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        self.cache[msg.guild.id][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl, _, _ = await self.calc_level(self.cache[msg.guild.id][msg.author.id][1], "mee6-like")
        ex_lvl, _, _ = await self.calc_level(prev_points, "mee6-like")
        if 0 < ex_lvl < new_lvl:
            await self.send_levelup(msg, new_lvl)
            await self.give_rr(msg.author, new_lvl, await self.rr_list_role(msg.guild.id))

    async def add_xp_2(self, msg:discord.Message, rate: float):
        """Local xp type"""
        if msg.guild.id not in self.cache:
            await self.db_load_cache(msg.guild.id)
        if msg.author.id in self.cache[msg.guild.id]:
            if time.time() - self.cache[msg.guild.id][msg.author.id][0] < self.classic_xp_cooldown:
                return
        content = msg.clean_content
        if len(content) < self.minimal_size or await self.check_spam(content) or await self.bot.potential_command(msg):
            return
        giv_points = round(await self.calc_xp(msg) * rate)
        if giv_points == 0:
            return
        if msg.author.id in self.cache[msg.guild.id]:
            prev_points = self.cache[msg.guild.id][msg.author.id][1]
        else:
            prev_points = await self.db_get_xp(msg.author.id, msg.guild.id) or 0
        await self.db_set_xp(msg.author.id, giv_points, 'add', msg.guild.id)
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        self.cache[msg.guild.id][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl, _, _ = await self.calc_level(self.cache[msg.guild.id][msg.author.id][1], "local")
        ex_lvl, _, _ = await self.calc_level(prev_points, "local")
        if 0 < ex_lvl < new_lvl:
            await self.send_levelup(msg, new_lvl)
            await self.give_rr(msg.author, new_lvl, await self.rr_list_role(msg.guild.id))


    async def check_noxp(self, msg: discord.Message) -> bool:
        "Returns True if the user cannot get xp in these conditions"
        if msg.guild is None:
            return False
        chans: Optional[list[discord.abc.Messageable]] = await self.bot.get_config(msg.guild.id, "noxp_channels")
        if chans is not None and msg.channel in chans:
            return True
        roles: Optional[list[discord.Role]] = await self.bot.get_config(msg.guild.id, "noxp_roles")
        if roles is not None:
            for role in roles:
                if role in msg.author.roles:
                    return True
        return False


    async def send_levelup(self, msg: discord.Message, lvl: int):
        """Envoie le message de levelup"""
        if self.bot.zombie_mode:
            return
        if msg.guild is None:
            return
        destination = await self.get_lvlup_chan(msg)
        if destination is None or (not msg.channel.permissions_for(msg.guild.me).send_messages):
            return
        text: Optional[str] = await self.bot.get_config(msg.guild.id, "levelup_msg")
        if text is None or len(text) == 0:
            text = random.choice(await self.bot._(msg.channel, "xp.default_levelup"))
            while '{random}' not in text and random.random() < 0.7:
                text = random.choice(await self.bot._(msg.channel, "xp.default_levelup"))
        if '{random}' in text:
            item = random.choice(await self.bot._(msg.channel, "xp.levelup-items"))
        else:
            item = ''
        text = text.format_map(self.bot.SafeDict(
            user=msg.author.mention,
            level=lvl,
            random=item,
            username=msg.author.display_name
        ))
        if isinstance(destination, discord.DMChannel) and msg.guild:
            embed = discord.Embed(
                title=await self.bot._(destination, "xp.levelup-dm.title"),
                color=discord.Color.gold(),
                description=text
            )
            footer = await self.bot._(destination, "xp.levelup-dm.footer", servername=msg.guild.name)
            embed.set_footer(text=footer, icon_url=msg.guild.icon)
            await destination.send(embed=embed)
        else:
            await destination.send(text)

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
            content = content.replace(match.group(0),match.group(1))
        matches = re.finditer(r'((?:http|www)[^\s]+)', content, re.MULTILINE)
        for _, match in enumerate(matches, start=1):
            content = content.replace(match.group(0),"")
        return min(round(len(content)*self.xp_per_char), self.max_xp_per_msg)

    async def calc_level(self, xp: int, system: Literal["global", "mee6-like", "local"]):
        """Calculate the level corresponding to a given xp amount
        Returns the current level, the xp needed for the next level and the xp needed for the current level"""
        if system != "mee6-like":
            if xp == 0:
                xp_for_level_1: int = ceil((1*125/7)**(20/13))
                return (0, xp_for_level_1, 0)
            lvl: int = ceil(0.056*xp**0.65)
            next_step = xp
            while ceil(0.056*next_step**0.65)==lvl:
                next_step += 1
            xp_for_current_lvl: int = ceil(((lvl-1)*125/7)**(20/13))
            return (lvl, next_step, xp_for_current_lvl)
        else:
            def recursive(lvl: int):
                t = 0
                for i in range(lvl):
                    t += 5*pow(i,2) + 50*i + 100
                return t

            if xp == 0:
                return (0, 100, 0)
            lvl = 0
            total_xp = 0
            while xp >= total_xp:
                total_xp += 5*pow(lvl,2) + 50*lvl + 100
                lvl += 1
            return (lvl-1, recursive(lvl), recursive(lvl-1))

    async def give_rr(self, member: discord.Member, level: int, rr_list: list, remove: bool=False):
        """Give (and remove?) roles rewards to a member"""
        c = 0
        has_roles = [x.id for x in member.roles]
        for role in [x for x in rr_list if x['level']<=level and x['role'] not in has_roles]:
            try:
                r = member.guild.get_role(role['role'])
                if r is None:
                    continue
                if not self.bot.beta:
                    await member.add_roles(r,reason="Role reward (lvl {})".format(role['level']))
                c += 1
            except Exception as err:
                if self.bot.beta:
                    self.bot.dispatch("error", err)
        if not remove:
            return c
        for role in [x for x in rr_list if x['level']>level and x['role'] in has_roles]:
            try:
                r = member.guild.get_role(role['role'])
                if r is None:
                    continue
                if not self.bot.beta:
                    await member.remove_roles(r,reason="Role reward (lvl {})".format(role['level']))
                c += 1
            except Exception as err:
                if self.bot.beta:
                    self.bot.dispatch("error", err)
        return c

    async def reload_sus(self):
        """Check who should be observed for potential xp cheating"""
        if not self.bot.database_online:
            return
        query = "SELECT userID FROM `users` WHERE `xp_suspect` = 1"
        async with self.bot.db_query(query) as query_result:
            if not query_result:
                return
            self.sus = {item['userID'] for item in query_result}
        self.bot.log.info("[xp] Reloaded xp suspects (%d suspects)", len(self.sus))

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
        cnx = self.bot.cnx_xp
        cursor = cnx.cursor()
        try:
            cursor.execute("SELECT 1 FROM `{}` LIMIT 1;".format(guild))
            return guild
        except mysql.connector.errors.ProgrammingError:
            if create_if_missing:
                cursor.execute("CREATE TABLE `{}` LIKE `example`;".format(guild))
                self.bot.log.info(f"[get_table] XP Table `{guild}` created")
                cursor.execute("SELECT 1 FROM `{}` LIMIT 1;".format(guild))
                return guild
            else:
                return None


    async def db_set_xp(self, user_id: int, points: int, action: Literal['add', 'set']='add', guild: int=None):
        """Ajoute/reset de l'xp à un utilisateur dans la database"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if points < 0:
                return True
            if guild is None:
                cnx = self.bot.cnx_axobot
            else:
                cnx = self.bot.cnx_xp
            table = await self.get_table_name(guild)
            cursor = cnx.cursor(dictionary = True)
            if action == 'add':
                query = f"INSERT INTO `{table}` (`userID`,`xp`) VALUES (%(u)s, %(p)s) ON DUPLICATE KEY UPDATE xp = xp + %(p)s;"
            else:
                query = f"INSERT INTO `{table}` (`userID`,`xp`) VALUES (%(u)s, %(p)s) ON DUPLICATE KEY UPDATE xp = %(p)s;"
            cursor.execute(query, {'p': points, 'u': user_id})
            cnx.commit()
            cursor.close()
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False

    async def db_get_xp(self, user_id: int, guild_id: Optional[int]) -> Optional[int]:
        "Get the xp of a user in a guild"
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild_id is None:
                cnx = self.bot.cnx_axobot
            else:
                cnx = self.bot.cnx_xp
            table = await self.get_table_name(guild_id, False)
            if table is None:
                return None
            query = f"SELECT `xp` FROM `{table}` WHERE `userID` = %s AND `banned` = 0"
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query, (user_id,))
            if result := cursor.fetchone():
                g = 'global' if guild_id is None else guild_id
                if isinstance(g, int) and g not in self.cache:
                    await self.db_load_cache(g)
                if user_id in self.cache[g].keys():
                    self.cache[g][user_id][1] = result['xp']
                else:
                    self.cache[g][user_id] = [round(time.time())-60,result ['xp']]
            cursor.close()
            return result['xp'] if result else None
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_users_count(self, guild_id: Optional[int]=None):
        """Get the number of ranked users in a guild (or in the global database)"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild_id is None:
                cnx = self.bot.cnx_axobot
            else:
                cnx = self.bot.cnx_xp
            table = await self.get_table_name(guild_id, False)
            if table is None:
                return 0
            query = f"SELECT COUNT(*) FROM `{table}` WHERE `banned`=0"
            cursor = cnx.cursor(dictionary = False)
            cursor.execute(query)
            rows = list(cursor)
            cursor.close()
            if rows is not None and len(rows) == 1:
                return rows[0][0]
            return 0
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_load_cache(self, guild_id: Optional[int]):
        "Load the XP cache for a given guild (or the global cache)"
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return
            if guild_id is None:
                self.bot.log.info("[xp] Loading XP cache (global)")
                cnx = self.bot.cnx_axobot
                query = f"SELECT `userID`,`xp` FROM `{self.table}` WHERE `banned`=0"
            else:
                self.bot.log.info(f"[xp] Loading XP cache (guild {guild_id})")
                table = await self.get_table_name(guild_id, False)
                if table is None:
                    self.cache[guild_id] = {}
                    return
                cnx = self.bot.cnx_xp
                query = f"SELECT `userID`,`xp` FROM `{table}` WHERE `banned`=0"
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            rows = list(cursor)
            if guild_id is None:
                self.cache['global'].clear()
                for row in rows:
                    self.cache['global'][row['userID']] = [round(time.time())-60, int(row['xp'])]
            else:
                if guild_id not in self.cache:
                    self.cache[guild_id] = {}
                for row in rows:
                    self.cache[guild_id][row['userID']] = [round(time.time())-60, int(row['xp'])]
            cursor.close()
            return
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_top(self, limit: int=None, guild: discord.Guild=None):
        "Get the top of the guild (or the global top)"
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild is not None and await self.bot.get_config(guild.id, "xp_type") != "global":
                cnx = self.bot.cnx_xp
                table = await self.get_table_name(guild.id, False)
                query = f"SELECT * FROM `{table}`ORDER BY `xp` DESC"
            else:
                cnx = self.bot.cnx_axobot
                query = f"SELECT * FROM `{self.table}` ORDER BY `xp` DESC"
            cursor = cnx.cursor(dictionary = True)
            try:
                cursor.execute(query)
            except mysql.connector.errors.ProgrammingError as err:
                if err.errno == 1146:
                    return list()
                raise err
            liste = list()
            if guild is None:
                liste = list(cursor)
                if limit is not None:
                    liste = liste[:limit]
            else:
                ids = [x.id for x in guild.members]
                i = 0
                l2 = list(cursor)
                if limit is None:
                    limit = len(l2)
                while len(liste)<limit and i<len(l2):
                    if l2[i]['userID'] in ids:
                        liste.append(l2[i])
                    i += 1
            cursor.close()
            return liste
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_rank(self, user_id: int, guild: discord.Guild=None):
        """Get the rank of a user"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild is not None and await self.bot.get_config(guild.id, "xp_type") != "global":
                cnx = self.bot.cnx_xp
                table = await self.get_table_name(guild.id, False)
                query = f"SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{table}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;"
            else:
                cnx = self.bot.cnx_axobot
                query = f"SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{self.table}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;"
            cursor = cnx.cursor(dictionary = True)
            try:
                cursor.execute(query)
            except mysql.connector.errors.ProgrammingError as err:
                if err.errno == 1146:
                    return {"rank":0, "xp":0}
                raise err
            userdata = {}
            i = 0
            users = set()
            if guild is not None:
                users = {x.id for x in guild.members}
            for x in cursor:
                if (guild is not None and x['userID'] in users) or guild is None:
                    i += 1
                if x['userID']== user_id:
                    # x['rank'] = i
                    userdata = x
                    userdata["rank"] = round(userdata["rank"])
                    break
            cursor.close()
            return userdata
        except Exception as err:
            self.bot.dispatch("error", err)

    async def db_get_total_xp(self):
        """Get the total number of earned xp"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            query = f"SELECT SUM(xp) as total FROM `{self.table}`"
            async with self.bot.db_query(query, fetchone=True) as query_results:
                result = round(query_results['total'])
            return result
        except Exception as err:
            self.bot.dispatch("error", err)


    async def get_image_from_url(self, url: str):
        "Download an image from an url"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return Image.open(BytesIO(await response.read()))

    async def clear_cards(self, delete_all: bool=False):
        """Delete outdated rank cards"""
        files =  os.listdir('./assets/cards/')
        done: set[str] = set()
        for f in sorted([f.split('-')+['./assets/cards/'+f] for f in files], key=operator.itemgetter(1), reverse=True):
            if delete_all or f[0] in done:
                os.remove(f[3])
            else:
                done.add(f[0])

    @commands.hybrid_command(name="rank")
    @app_commands.describe(user="The user to get the rank of. If not specified, it will be you.")
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1, 20, commands.BucketType.user)
    async def rank(self, ctx: MyContext, *, user: Optional[discord.User]=None):
        """Check how many xp you got
        If you don't specify any user, I'll send you your own XP

        ..Example rank

        ..Example rank @z_runner

        ..Doc user.html#check-the-xp-of-someone
        """
        try:
            if user is None:
                user = ctx.author
            if user.bot:
                return await ctx.send(await self.bot._(ctx.channel, "xp.bot-rank"))
            send_in_private = ctx.guild is None or await self.bot.get_config(ctx.guild.id, "rank_in_dm")
            await ctx.defer(ephemeral=send_in_private)
            if ctx.guild is not None:
                if not await self.bot.get_config(ctx.guild.id, "enable_xp"):
                    return await ctx.send(await self.bot._(ctx.guild.id, "xp.xp-disabled"))
                xp_used_type: str = await self.bot.get_config(ctx.guild.id, "xp_type")
            else:
                xp_used_type = options['xp_type']["default"]
            xp = await self.db_get_xp(user.id, None if xp_used_type == "global" else ctx.guild.id)
            if xp is None:
                if ctx.author == user:
                    return await ctx.send(await self.bot._(ctx.channel, "xp.1-no-xp"))
                return await ctx.send(await self.bot._(ctx.channel, "xp.2-no-xp"))
            levels_info = await self.calc_level(xp, xp_used_type)
            if xp_used_type == "global":
                ranks_nb = await self.db_get_users_count()
                try:
                    rank = (await self.db_get_rank(user.id))['rank']
                except KeyError:
                    rank = "?"
            else:
                ranks_nb = await self.db_get_users_count(ctx.guild.id)
                try:
                    rank = (await self.db_get_rank(user.id,ctx.guild))['rank']
                except KeyError:
                    rank = "?"
            if isinstance(rank, float):
                rank = int(rank)
            send_in_private = ctx.guild is None or await self.bot.get_config(ctx.guild.id, "rank_in_dm")
            use_author_dm = send_in_private and ctx.interaction is None
            # If we can send the rank card
            if ctx.guild is None or use_author_dm or ctx.channel.permissions_for(ctx.guild.me).attach_files:
                try:
                    await self.send_card(ctx, user, xp, rank, ranks_nb, levels_info)
                    return
                except Exception as err:  # pylint: disable=broad-except
                    # log the error and fall back to embed/text
                    self.bot.dispatch("error", err, ctx)
            # if we can send embeds
            if ctx.can_send_embed:
                await self.send_embed(ctx, user, xp, rank, ranks_nb, levels_info)
                return
            # fall back to raw text
            await self.send_txt(ctx, user, xp, rank, ranks_nb, levels_info)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)

    async def create_card(self, translation_map: dict[str, str], user: discord.User, style: str, xp: int, rank: int, ranks_nb: int, levels_info: tuple[int, int, int]):
        "Find the user rank card, or generate a new one, based on given data"
        static = not (
            user.display_avatar.is_animated()
            and await self.bot.get_cog("Users").db_get_user_config(user.id, "animated_card")
        )
        file_ext = 'png' if static else 'gif'
        filepath = f"./assets/cards/{user.id}-{xp}-{style}.{file_ext}"
        # check if the card has already been generated, and return it if it is the case
        if os.path.isfile(filepath):
            return discord.File(filepath)
        self.bot.log.debug(f"XP card for user {user.id} ({xp=} - {style=} - {static=})")
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
            duration = user_avatar.info['duration']
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

    async def send_card(self, ctx: MyContext, user: discord.User, xp: int, rank: int, ranks_nb: int, levels_info: tuple[int, int, int]):
        """Generate and send a user rank card
        levels_info contains (current level, xp needed for the next level, xp needed for the current level)"""
        style = await self.bot.get_cog('Utilities').get_xp_style(user)
        translations_map = await self.get_card_translations_map(ctx.channel)
        card_image = await self.create_card(translations_map, user, style, xp, rank, ranks_nb, levels_info)
        # check if we should send the card in DM or in the channel
        send_in_private = ctx.guild is None or await self.bot.get_config(ctx.guild.id, "rank_in_dm")
        try:
            if ctx.interaction:
                await ctx.send(file=card_image, ephemeral=send_in_private)
            elif send_in_private:
                await ctx.author.send(file=card_image)
                try:
                    await ctx.message.delete()
                except discord.HTTPException:
                    pass
            else:
                await ctx.send(file=card_image)
        except discord.errors.Forbidden:
            await ctx.send(await self.bot._(ctx.channel, "xp.card-forbidden"))
        except discord.errors.HTTPException:
            await ctx.send(await self.bot._(ctx.channel, "xp.card-too-large"))
        else:
            if style == self.default_xp_style:
                await self.send_rankcard_tip(ctx)
        if stats_cog := self.bot.get_cog("BotStats"):
            stats_cog.xp_cards["sent"] += 1

    async def send_rankcard_tip(self, ctx: MyContext):
        "Send a tip about the rank card personalisation"
        if random.random() > 0.2:
            return
        if not await self.bot.get_cog("Users").db_get_user_config(ctx.author.id, "show_tips"):
            # tips are disabled
            return
        if await self.bot.tips_manager.should_show_user_tip(ctx.author.id, UserTip.RANK_CARD_PERSONALISATION):
            # user has not seen this tip yet
            profile_cmd = await self.bot.get_command_mention("profile card")
            await self.bot.tips_manager.send_user_tip(ctx, UserTip.RANK_CARD_PERSONALISATION, profile_cmd=profile_cmd)

    async def send_embed(self, ctx: MyContext, user: discord.User, xp, rank, ranks_nb,  levels_info: tuple[int, int, int]):
        "Send the user rank as an embed (fallback from card generation)"
        txts = [await self.bot._(ctx.channel, "xp.card-level"), await self.bot._(ctx.channel, "xp.card-rank")]
        emb = discord.Embed(color=self.embed_color)
        emb.set_author(name=user.display_name, icon_url=user.display_avatar)
        emb.add_field(name='XP', value=f"{xp}/{levels_info[1]}")
        emb.add_field(name=txts[0].title(), value=levels_info[0])
        emb.add_field(name=txts[1].title(), value=f"{rank}/{ranks_nb}")
        send_in_private = await self.bot.get_config(ctx.guild.id, "rank_in_dm")
        if ctx.interaction:
            await ctx.send(embed=emb, ephemeral=send_in_private)
        elif send_in_private:
            await ctx.author.send(embed=emb)
        else:
            await ctx.send(embed=emb)

    async def send_txt(self, ctx: MyContext, user: discord.User, xp, rank, ranks_nb,  levels_info: tuple[int, int, int]):
        "Send the user rank as a text message (fallback from embed)"
        txts = [await self.bot._(ctx.channel, "xp.card-level"), await self.bot._(ctx.channel, "xp.card-rank")]
        msg = """__**{}**__
**XP** {}/{}
**{}** {}
**{}** {}/{}""".format(user.display_name, xp, levels_info[1], txts[0].title(), levels_info[0], txts[1].title(), rank, ranks_nb)
        send_in_private = await self.bot.get_config(ctx.guild.id, "rank_in_dm")
        if ctx.interaction:
            await ctx.send(msg, ephemeral=send_in_private)
        elif send_in_private:
            await ctx.author.send(msg)
        else:
            await ctx.send(msg)


    class TopPaginator(Paginator):
        "Paginator used to display the leaderboard"

        def __init__(self, client: Axobot, user: discord.User, guild: discord.Guild, scope: LeaderboardScope,
                     start_page: int, stop_label: str = "Quit", timeout: int = 180):
            super().__init__(client, user, stop_label, timeout)
            class Position(TypedDict):
                "A position in the leaderboard"
                username: str
                user_id: int
                level: int
                xp: int
                xp_label: str
            class RawData(TypedDict):
                "Raw data for the leaderboard"
                xp: int
                user_id: int

            self.guild = guild
            self.scope = scope
            self.page = start_page
            self.raw_data: list[Optional[RawData]] = []
            self.positions: list[Position] = []
            self.cog = client.get_cog("Xp")
            self.used_system: str = None
            self.max_page: int = 1

        def convert_average(self, nbr: int) -> str:
            "Convert a large number to its short version (ex: 1000000 -> 1M)"
            res = str(nbr)
            for power, symb in ((9,'G'), (6,'M'), (3,'k')):
                if nbr >= 10**power:
                    res = str(round(nbr/10**power, 1)) + symb
                    break
            return res

        async def get_page_count(self):
            return self.max_page

        @acached()
        async def get_user_rank(self):
            "Get the embed field content corresponding to the user's rank"
            pos = [(i+1, pos) for i, pos in enumerate(self.positions) if pos is not None and pos["user_id"] == self.user.id]
            field_name = "__" + await self.client._(self.guild, "xp.top-your") + "__"
            if len(pos) == 0:
                # fetch from raw data
                pos = [(i+1, pos) for i, pos in enumerate(self.raw_data) if pos is not None and pos["user_id"] == self.user.id]
                if len(pos) == 0:
                    value = await self.client._(self.guild, "xp.1-no-xp")
                else:
                    rank = pos[0][0]
                    level = await self.cog.calc_level(pos[0][1]["xp"], self.used_system)
                    xp_label = self.convert_average(pos[0][1]["xp"])
                    value = f"**#{rank} |** `lvl {level[0]}` **|** `xp {xp_label}`"
            else:
                rank, data = pos[0]
                value = f"**#{rank} |** `lvl {data['level']}` **|** `xp {data['xp_label']}`"
            return {
                "name": field_name,
                "value": value,
            }

        async def fetch_data(self):
            "Fetch the required data to display the leaderboard"
            self.used_system = await self.client.get_config(self.guild.id, 'xp_type')
            if self.used_system == "global":
                if self.scope == 'global':
                    if len(self.cog.cache["global"]) == 0:
                        await self.cog.db_load_cache(None)
                    self.raw_data = [
                        {"user_id": user_id, "xp": data[1]}
                        for user_id, data in self.cog.cache['global'].items()
                    ]
                else:
                    self.raw_data = [
                        {"user_id": int(row["userID"]), "xp": row["xp"]}
                        for row in await self.cog.db_get_top(10000, guild=self.guild)
                    ]
            else:
                if not self.guild.id in self.cog.cache.keys():
                    await self.cog.db_load_cache(self.guild.id)
                self.raw_data = [
                        {"user_id": user_id, "xp": data[1]}
                        for user_id, data in self.cog.cache[self.guild.id].items()
                    ]
            self.raw_data.sort(key=lambda x: x["xp"], reverse=True)
            self.max_page = ceil(len(self.raw_data)/20)
            self.positions = [None for _ in range(len(self.raw_data))]

        async def _load_page(self):
            "Load the user data for the current page"
            i = (self.page-1)*20
            for data in self.raw_data[(self.page-1)*20:self.page*20]:
                if self.positions[i] is not None:
                    i += 1
                    continue
                user = self.client.get_user(data["user_id"])
                if user is None:
                    try:
                        user = await self.client.fetch_user(data["user_id"])
                    except discord.NotFound:
                        user = await self.client._(self.guild, "xp.del-user")
                if isinstance(user, discord.User):
                    user_name = discord.utils.escape_markdown(user.display_name)
                    if len(user_name) > 18:
                        user_name = user_name[:15]+'...'
                    if user == self.user:
                        user_name = "__" + user_name + "__"
                else:
                    user_name = user
                level = await self.cog.calc_level(data["xp"], self.used_system)
                xp = self.convert_average(data["xp"])
                self.positions[i] = {
                    "username": user_name,
                    "user_id": data["user_id"],
                    "level": level[0],
                    "xp": data["xp"],
                    "xp_label": xp
                }
                i += 1

        async def get_page_content(self, _interaction, page: int):
            "Get the content of a page"
            if page > self.max_page:
                page = self.page = self.max_page
            await self._load_page()
            txt = []
            i = (page-1)*20
            for row in self.positions[(page-1)*20:page*20]:
                i += 1
                username = row['username']
                lvl = row['level']
                xp = row['xp_label']
                txt.append(f"{i} • **{username} |** `lvl {lvl}` **|** `xp {xp}`")
            # title
            if self.scope == "server" or self.used_system != "global":
                embed_title = await self.client._(self.guild, "xp.top-title-2")
            else:
                embed_title = await self.client._(self.guild, "xp.top-title-1")
            # field name
            field_title = await self.client._(self.guild, "xp.top-name", min=(page-1)*20+1, max=i, page=page, total=self.max_page)
            emb = discord.Embed(title=embed_title, color=self.cog.embed_color)
            emb.add_field(name=field_title, value="\n".join(txt), inline=False)
            # user rank
            emb.add_field(**await self.get_user_rank())
            # embed footer with user info
            emb.set_footer(text=self.user, icon_url=self.user.display_avatar)
            return {
                "embed": emb
            }

    @commands.hybrid_command(name="top")
    @app_commands.describe(page="The page number", scope="The scope of the leaderboard (global or server)")
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def top(self, ctx: MyContext, page: Optional[commands.Range[int, 1]]=1, scope: LeaderboardScope='global'):
        """Get the list of the highest XP users

        ..Example top

        ..Example top server

        ..Example top 7

        ..Doc user.html#get-the-general-ranking"""
        if ctx.guild is not None:
            if not await self.bot.get_config(ctx.guild.id,'enable_xp'):
                return await ctx.send(await self.bot._(ctx.guild.id, "xp.xp-disabled"))
        if page < 1:
            return await ctx.send(await self.bot._(ctx.channel, "xp.low-page"))
        await ctx.defer()
        _quit = await self.bot._(ctx.guild.id, "misc.quit")
        view = self.TopPaginator(self.bot, ctx.author, ctx.guild, scope, page, _quit.capitalize())
        await view.fetch_data()
        msg = await view.send_init(ctx)
        if msg:
            if await view.wait():
                # only manually disable if it was a timeout (ie. not a user stop)
                await view.disable(msg)


    @commands.command(name='set-xp', aliases=["setxp"])
    @commands.guild_only()
    @commands.check(checks.has_admin)
    async def set_xp(self, ctx: MyContext, user: discord.User, xp: commands.Range[int, 0, 10**15]):
        """Set the XP of a user

        ..Example set_xp 3000 @someone"""
        if user.bot:
            return await ctx.send(await self.bot._(ctx.guild.id, "xp.no-bot"))
        if await self.bot.get_config(ctx.guild.id, "xp_type") == "global":
            return await ctx.send(await self.bot._(ctx.guild.id, "xp.change-global-xp"))
        if xp < 0:
            return await ctx.send(await self.bot._(ctx.guild.id, "xp.negative-xp"))
        try:
            xp_used_type: str = await self.bot.get_config(ctx.guild.id, "xp_type")
            prev_xp = await self.db_get_xp(user.id, None if xp_used_type == "global" else ctx.guild.id)
            await self.db_set_xp(user.id, xp, action='set', guild=ctx.guild.id)
            await ctx.send(await self.bot._(ctx.guild.id, "xp.change-xp-ok", user=str(user), xp=xp))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "minecraft.serv-error"))
            self.bot.dispatch("error", err, ctx)
        else:
            if ctx.guild.id not in self.cache:
                await self.db_load_cache(ctx.guild.id)
            self.cache[ctx.guild.id][user.id] = [round(time.time()), xp]
            desc = f"XP of user {user} `{user.id}` edited (from {prev_xp} to {xp}) in server `{ctx.guild.id}`"
            self.bot.log.info("[xp] " + desc)
            emb = discord.Embed(description=desc,color=8952255, timestamp=self.bot.utcnow())
            emb.set_footer(text=ctx.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)

    async def gen_rr_id(self):
        return round(time.time()/2)

    async def rr_add_role(self, guild_id: int, role_id: int, level:int):
        """Add a role reward in the database"""
        reward_id = await self.gen_rr_id()
        query = "INSERT INTO `roles_rewards` (`ID`, `guild`, `role`, `level`) VALUES (%(i)s, %(g)s, %(r)s, %(l)s);"
        async with self.bot.db_query(query, { 'i': reward_id, 'g': guild_id, 'r': role_id, 'l': level }):
            pass
        return True

    async def rr_list_role(self, guild_id: int, level: int = -1):
        """List role rewards in the database"""
        if level < 0:
            query = "SELECT * FROM `roles_rewards` WHERE `guild`=%s ORDER BY `level`;"
            query_args = (guild_id,)
        else:
            query = "SELECT * FROM `roles_rewards` WHERE `guild`=%s AND `level`=%s ORDER BY `level`;"
            query_args = (guild_id, level)
        async with self.bot.db_query(query, query_args) as query_results:
            liste = list(query_results)
        return liste

    async def rr_remove_role(self, role_id: int):
        """Remove a role reward from the database"""
        query = "DELETE FROM `roles_rewards` WHERE `ID` = %s;"
        async with self.bot.db_query(query, (role_id,)):
            pass
        return True

    @commands.hybrid_group(name="roles-rewards", aliases=['rr'])
    @commands.guild_only()
    @app_commands.default_permissions(manage_roles=True)
    async def rr_main(self, ctx: MyContext):
        """Manage your roles rewards like a boss

        ..Doc server.html#roles-rewards"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @rr_main.command(name="add")
    @commands.check(checks.has_manage_roles)
    async def rr_add(self, ctx: MyContext, level: commands.Range[int, 1], *, role: discord.Role):
        """Add a role reward
        This role will be given to every member who reaches the level

        ..Example rr add 10 Slowly farming

        ..Doc server.html#roles-rewards"""
        try:
            if role.name == '@everyone':
                raise commands.BadArgument(f'Role "{role.name}" not found')
            l = await self.rr_list_role(ctx.guild.id)
            if len([x for x in l if x['level']==level]) > 0:
                return await ctx.send(await self.bot._(ctx.guild.id, "xp.already-1-rr"))
            max_rr: int = await self.bot.get_config(ctx.guild.id, "rr_max_number")
            if len(l) >= max_rr:
                return await ctx.send(await self.bot._(ctx.guild.id, "xp.too-many-rr", c=len(l)))
            await self.rr_add_role(ctx.guild.id,role.id,level)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "xp.rr-added", role=role.name,level=level))

    @rr_main.command(name="list")
    @commands.check(checks.bot_can_embed)
    async def rr_list(self, ctx: MyContext):
        """List every roles rewards of your server

        ..Doc server.html#roles-rewards"""
        try:
            roles_list = await self.rr_list_role(ctx.guild.id)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            if roles_list:
                desc = '\n'.join([
                    f"• <@&{x['role']}> : lvl {x['level']}"
                    for x in roles_list
                ])
            else:
                desc = await self.bot._(ctx.guild.id, "xp.no-rr-list", add=await self.bot.get_command_mention("roles-rewards add"))
            max_rr: int = await self.bot.get_config(ctx.guild.id, "rr_max_number")
            title = await self.bot._(ctx.guild.id,"xp.rr_list", c=len(roles_list), max=max_rr)
            emb = discord.Embed(title=title, description=desc, timestamp=ctx.message.created_at)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)

    @rr_main.command(name="remove")
    @commands.check(checks.has_manage_roles)
    async def rr_remove(self, ctx: MyContext, level: commands.Range[int, 1]):
        """Remove a role reward
        When a member reaches this level, no role will be given anymore

        ..Example roles-rewards remove 10

        ..Doc server.html#roles-rewards"""
        try:
            l = await self.rr_list_role(ctx.guild.id,level)
            if len(l) == 0:
                return await ctx.send(await self.bot._(ctx.guild.id, "xp.no-rr"))
            await self.rr_remove_role(l[0]['ID'])
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "xp.rr-removed", level=level))

    @rr_main.command(name="reload")
    @commands.check(checks.has_manage_roles)
    @commands.cooldown(1, 300, commands.BucketType.guild)
    async def rr_reload(self, ctx: MyContext):
        """Refresh roles rewards for the whole server

        ..Doc server.html#roles-rewards"""
        try:
            if not ctx.guild.me.guild_permissions.manage_roles:
                return await ctx.send(await self.bot._(ctx.guild.id,'moderation.mute.cant-mute'))
            count = 0
            rr_list = await self.rr_list_role(ctx.guild.id)
            if len(rr_list) == 0:
                await ctx.send(await self.bot._(ctx.guild, "xp.no-rr-2"))
                return
            used_system: str = await self.bot.get_config(ctx.guild.id, "xp_type")
            xps = [
                {'user': x['userID'], 'xp':x['xp']}
                for x in await self.db_get_top(limit=None, guild=None if used_system == "global" else ctx.guild)
            ]
            for member_data in xps:
                if member := ctx.guild.get_member(member_data['user']):
                    level = (await self.calc_level(member_data['xp'], used_system))[0]
                    count += await self.give_rr(member, level, rr_list, remove=True)
            await ctx.send(await self.bot._(ctx.guild.id, "xp.rr-reload", role_count=count,member_count=ctx.guild.member_count))
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)


async def setup(bot: Axobot):
    if bot.database_online:
        await bot.add_cog(Xp(bot))
