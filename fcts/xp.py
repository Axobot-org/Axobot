import asyncio
import importlib
import operator
import os
import random
import re
import string
import time
import typing
from io import BytesIO
from math import ceil, sqrt
from urllib.request import Request, urlopen

import aiohttp
import discord
import mysql
import numpy as np
from discord.ext import commands
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageSequence

from libs.tips import UserTip

from . import args, checks

importlib.reload(args)
importlib.reload(checks)
from libs.bot_classes import Axobot, MyContext
from libs.serverconfig.options_list import options


class Xp(commands.Cog):

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.cache = {'global':{}}
        self.levels = [0]
        self.embed_color = discord.Colour(0xffcf50)
        self.table = 'xp_beta' if bot.beta else 'xp'
        self.cooldown = 30
        self.minimal_size = 5
        self.spam_rate = 0.20
        self.xp_per_char = 0.11
        self.max_xp_per_msg = 70
        self.file = 'xp'
        self.sus = None
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
        await self.bdd_load_cache(-1)
        if not self.bot.database_online:
            await self.bot.unload_extension("fcts.xp")

    async def get_lvlup_chan(self, msg: discord.Message):
        value = await self.bot.get_config(msg.guild.id,"levelup_channel")
        if value == "none":
            return None
        if value == "any":
            return msg.channel
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
    
    async def add_xp_0(self, msg: discord.Message, rate: float):
        """Global xp type"""
        if msg.author.id in self.cache['global'].keys():
            if time.time() - self.cache['global'][msg.author.id][0] < self.cooldown:
                return
        content = msg.clean_content
        if len(content)<self.minimal_size or await self.check_spam(content) or await self.bot.potential_command(msg):
            return
        if len(self.cache["global"]) == 0:
            await self.bdd_load_cache(-1)
        giv_points = await self.calc_xp(msg)
        if msg.author.id in self.cache['global'].keys():
            prev_points = self.cache['global'][msg.author.id][1]
        else:
            prev_points = await self.bdd_get_xp(msg.author.id, None)
            if prev_points is not None and len(prev_points) > 0:
                prev_points = prev_points[0]['xp']
            else:
                prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points, 'add')
        # check for sus people
        if msg.author.id in self.sus:
            await self.send_sus_msg(msg, giv_points)
        self.cache['global'][msg.author.id] = [round(time.time()), prev_points+giv_points]
        new_lvl, _, _ = await self.calc_level(self.cache['global'][msg.author.id][1], "global")
        ex_lvl, _, _ = await self.calc_level(prev_points, "global")
        if 0 < ex_lvl < new_lvl:
            await self.send_levelup(msg, new_lvl)
            await self.give_rr(msg.author, new_lvl, await self.rr_list_role(msg.guild.id))
            await self.bot.get_cog("Utilities").add_user_eventPoint(msg.author.id, round(new_lvl/5))
    
    async def add_xp_1(self, msg:discord.Message, rate: float):
        """MEE6-like xp type"""
        if msg.guild.id not in self.cache.keys():
            await self.bdd_load_cache(msg.guild.id)
        if msg.author.id in self.cache[msg.guild.id].keys():
            if time.time() - self.cache[msg.guild.id][msg.author.id][0] < 60:
                return
        if await self.bot.potential_command(msg):
            return
        giv_points = round(random.randint(15,25) * rate)
        if msg.author.id in self.cache[msg.guild.id].keys():
            prev_points = self.cache[msg.guild.id][msg.author.id][1]
        else:
            prev_points = await self.bdd_get_xp(msg.author.id, msg.guild.id)
            if prev_points is not None and len(prev_points) > 0:
                prev_points = prev_points[0]['xp']
            else:
                prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points, 'add', msg.guild.id)
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
        if msg.guild.id not in self.cache.keys():
            await self.bdd_load_cache(msg.guild.id)
        if msg.author.id in self.cache[msg.guild.id].keys():
            if time.time() - self.cache[msg.guild.id][msg.author.id][0] < self.cooldown:
                return
        content = msg.clean_content
        if len(content)<self.minimal_size or await self.check_spam(content) or await self.bot.potential_command(msg):
            return
        giv_points = round(await self.calc_xp(msg) * rate)
        if msg.author.id in self.cache[msg.guild.id].keys():
            prev_points = self.cache[msg.guild.id][msg.author.id][1]
        else:
            prev_points = await self.bdd_get_xp(msg.author.id, msg.guild.id)
            if prev_points is not None and len(prev_points) > 0:
                prev_points = prev_points[0]['xp']
            else:
                prev_points = 0
        await self.bdd_set_xp(msg.author.id, giv_points, 'add', msg.guild.id)
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
        """Check if this channel/user can get xp"""
        if msg.guild is None:
            return False
        chans: typing.Optional[discord.abc.MessageableChannel] = await self.bot.get_config(msg.guild.id, "noxp_channels")
        return chans is not None and msg.channel in chans


    async def send_levelup(self, msg: discord.Message, lvl: int):
        """Envoie le message de levelup"""
        if self.bot.zombie_mode:
            return
        if msg.guild is None:
            return
        destination = await self.get_lvlup_chan(msg)
        if destination is None or (not msg.channel.permissions_for(msg.guild.me).send_messages):
            return
        text: typing.Optional[str] = await self.bot.get_config(msg.guild.id, "levelup_msg")
        if text is None or len(text) == 0:
            text = random.choice(await self.bot._(msg.channel, "xp.default_levelup"))
            while (not '{random}' in text) and random.random() < 0.75:
                text = random.choice(await self.bot._(msg.channel, "xp.default_levelup"))
        if '{random}' in text:
            item = random.choice(await self.bot._(msg.channel, "xp.levelup-items"))
        else:
            item = ''
        await destination.send(text.format_map(self.bot.SafeDict(
            user=msg.author.mention,
            level=lvl,
            random=item,
            username=msg.author.display_name
        )))

    async def check_spam(self, text: str):
        """Vérifie si un text contient du spam"""
        if len(text)>0 and (text[0] in string.punctuation or text[1] in string.punctuation):
            return True
        d = dict()
        for c in text:
            if c in d.keys():
                d[c] += 1
            else:
                d[c] = 1
        for v in d.values():
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

    async def calc_level(self, xp: int, system: typing.Literal["global", "mee6-like", "local"]):
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
        cog = self.bot.get_cog("Utilities")
        if cog is None:
            return
        result = await cog.get_db_userinfo(['userID'], ['xp_suspect=1'])
        if result is None or len(result) == 0:
            return
        if len(result) > 1:
            result = [item['userID'] for item in result]
        self.sus = set(result)
        self.bot.log.info("[xp] Reloaded xp suspects (%d suspects)", len(self.sus))
    
    async def send_sus_msg(self, msg: discord.Message, xp: int):
        """Send a message into the sus channel"""
        chan = self.bot.get_channel(785877971944472597)
        emb = discord.Embed(
            title=f"#{msg.channel.name} | {msg.guild.name} | {msg.guild.id}",
            description=msg.content
        ).set_footer(text=str(msg.author.id)).set_author(name=str(msg.author), icon_url=msg.author.display_avatar.url).add_field(name="XP given", value=str(xp))
        await chan.send(embed=emb)


    async def get_table(self, guild: int, createIfNeeded: bool=True):
        """Get the table name of a guild, and create one if no one exist"""
        if guild is None:
            return self.table
        cnx = self.bot.cnx_xp
        cursor = cnx.cursor()
        try:
            cursor.execute("SELECT 1 FROM `{}` LIMIT 1;".format(guild))
            return guild
        except mysql.connector.errors.ProgrammingError:
            if createIfNeeded:
                cursor.execute("CREATE TABLE `{}` LIKE `example`;".format(guild))
                self.bot.log.info(f"[get_table] XP Table `{guild}` created")
                cursor.execute("SELECT 1 FROM `{}` LIMIT 1;".format(guild))
                return guild
            else:
                return None


    async def bdd_set_xp(self, userID: int, points: int, Type: str='add', guild: int=None):
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
            table = await self.get_table(guild)
            cursor = cnx.cursor(dictionary = True)
            if Type=='add':
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = xp + '{p}';".format(t=table,p=points,u=userID))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`xp`) VALUES ('{u}','{p}') ON DUPLICATE KEY UPDATE xp = '{p}';".format(t=table,p=points,u=userID))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False
    
    async def bdd_get_xp(self, userID: int, guild: int):
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild is None:
                cnx = self.bot.cnx_axobot
            else:
                cnx = self.bot.cnx_xp
            table = await self.get_table(guild, False)
            if table is None:
                return None
            query = ("SELECT `xp` FROM `{}` WHERE `userID`={} AND `banned`=0".format(table,userID))
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            if len(liste) == 1:
                g = 'global' if guild is None else guild
                if isinstance(g, int) and g not in self.cache:
                    await self.bdd_load_cache(g)
                if userID in self.cache[g].keys():
                    self.cache[g][userID][1] = liste[0]['xp']
                else:
                    self.cache[g][userID] = [round(time.time())-60,liste[0]['xp']]
            cursor.close()
            return liste
        except Exception as err:
            self.bot.dispatch("error", err)
    
    async def bdd_get_nber(self, guild: int=None):
        """Get the number of ranked users"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild is None:
                cnx = self.bot.cnx_axobot
            else:
                cnx = self.bot.cnx_xp
            table = await self.get_table(guild, False)
            if table is None:
                return 0
            query = ("SELECT COUNT(*) FROM `{}` WHERE `banned`=0".format(table))
            cursor = cnx.cursor(dictionary = False)
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            cursor.close()
            if liste is not None and len(liste) == 1:
                return liste[0][0]
            return 0
        except Exception as err:
            self.bot.dispatch("error", err)

    async def bdd_load_cache(self, guild: int):
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return
            target_global = (guild == -1)
            if target_global:
                self.bot.log.info("[xp] Loading XP cache (global)")
                cnx = self.bot.cnx_axobot
                query = ("SELECT `userID`,`xp` FROM `{}` WHERE `banned`=0".format(self.table))
            else:
                self.bot.log.info("[xp] Loading XP cache (guild {})".format(guild))
                table = await self.get_table(guild,False)
                if table is None:
                    self.cache[guild] = dict()
                    return 
                cnx = self.bot.cnx_xp
                query = ("SELECT `userID`,`xp` FROM `{}` WHERE `banned`=0".format(table))
            cursor = cnx.cursor(dictionary = True)
            cursor.execute(query)
            liste = list()
            for x in cursor:
                liste.append(x)
            if target_global:
                if len(self.cache['global'].keys()) == 0:
                    self.cache['global'] = dict()
                for l in liste:
                    self.cache['global'][l['userID']] = [round(time.time())-60, int(l['xp'])]
            else:
                if guild not in self.cache.keys():
                    self.cache[guild] = dict()
                for l in liste:
                    self.cache[guild][l['userID']] = [round(time.time())-60, int(l['xp'])]
            cursor.close()
            return
        except Exception as err:
            self.bot.dispatch("error", err)

    async def bdd_get_top(self, top: int=None, guild: discord.Guild=None):
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild is not None and await self.bot.get_config(guild.id, "xp_type") != "global":
                cnx = self.bot.cnx_xp
                query = ("SELECT * FROM `{}` order by `xp` desc".format(await self.get_table(guild.id,False)))
            else:
                cnx = self.bot.cnx_axobot
                query = ("SELECT * FROM `{}` order by `xp` desc".format(self.table))
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
                if top is not None:
                    liste = liste[:top]
            else:
                ids = [x.id for x in guild.members]
                i = 0
                l2 = list(cursor)
                if top is None:
                    top = len(l2)
                while len(liste)<top and i<len(l2):
                    if l2[i]['userID'] in ids:
                        liste.append(l2[i])
                    i += 1
            cursor.close()
            return liste
        except Exception as err:
            self.bot.dispatch("error", err)

    async def bdd_get_rank(self, user_id: int, guild: discord.Guild=None):
        """Get the rank of a user"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            if guild is not None and await self.bot.get_config(guild.id, "xp_type") != "global":
                cnx = self.bot.cnx_xp
                query = ("SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;".format(await self.get_table(guild.id, False)))
            else:
                cnx = self.bot.cnx_axobot
                query = ("SELECT `userID`,`xp`, @curRank := @curRank + 1 AS rank FROM `{}` p, (SELECT @curRank := 0) r WHERE `banned`='0' ORDER BY xp desc;".format(self.table))
            cursor = cnx.cursor(dictionary = True)
            try:
                cursor.execute(query)
            except mysql.connector.errors.ProgrammingError as err:
                if err.errno == 1146:
                    return {"rank":0, "xp":0}
                raise err
            userdata = dict()
            i = 0
            users = list()
            if guild is not None:
                users = [x.id for x in guild.members]
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

    async def bdd_total_xp(self):
        """Get the total number of earned xp"""
        try:
            if not self.bot.database_online:
                await self.bot.unload_extension("fcts.xp")
                return None
            query = f"SELECT SUM(xp) as total FROM `{self.table}`"
            async with self.bot.db_query(query, fetchone=True) as query_results:
                result = round(query_results['total'])

            # cnx = self.bot.cnx_xp
            # cursor = cnx.cursor()
            # cursor.execute("show tables")
            # tables = [x[0] for x in cursor if x[0].isnumeric()]
            # for table in tables:
            #     cursor.execute("SELECT SUM(xp) FROM `{}`".format(table))
            #     res = [x for x in cursor]
            #     if res[0][0] is not None:
            #         result += round(res[0][0])
            # cursor.close()
            return result
        except Exception as err:
            self.bot.dispatch("error", err)


    async def get_raw_image(self, url:str):
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        im = Image.open(BytesIO(urlopen(req).read()))
        return im

    def calc_pos(self, text:str, font, x: int, y: int, align: str='center'):
        w,h = font.getsize(text)
        if align == 'center':
            return x-w/2,y-h/2
        elif align == 'right':
            return x-w,y-h/2

    async def create_card(self, user: discord.User, style, xp, used_system: str, rank=[1,0], txt=['NIVEAU','RANG'], force_static=False, levels_info=None):
        """Crée la carte d'xp pour un utilisateur"""
        card = Image.open("./assets/card-models/{}.png".format(style))
        bar_colors = await self.get_xp_bar_color(user.id)
        if levels_info is None:
            levels_info = await self.calc_level(xp, used_system)
        colors = {'name':(124, 197, 118),'xp':(124, 197, 118),'NIVEAU':(255, 224, 77),'rank':(105, 157, 206),'bar':bar_colors, 'bar_background': (180, 180, 180)}
        if style in {'blurple21', 'blurple22'}:
            colors = {'name':(240, 240, 255),'xp':(235, 235, 255),'NIVEAU':(245, 245, 255),'rank':(255, 255, 255),'bar':(250, 250, 255), 'bar_background': (27, 29, 31)}

        if not user.display_avatar.is_animated() or force_static:
            pfp = await self.get_raw_image(user.display_avatar.replace(format="png", size=256))
            img = await self.bot.loop.run_in_executor(None,self.add_overlay,pfp.resize(size=(282,282)),user,card,xp,rank,txt,colors,levels_info)
            img.save('./assets/cards/{}-{}-{}.png'.format(user.id,xp,rank[0]))
            card.close()
            return discord.File('./assets/cards/{}-{}-{}.png'.format(user.id,xp,rank[0]))

        else:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(str(user.display_avatar.replace(format='gif',size=256))) as r:
                    response = await r.read()
                    pfp = Image.open(BytesIO(response))

            images = []
            duration = []
            frames = [frame.copy() for frame in ImageSequence.Iterator(pfp)]
            for frame in frames:
                frame = frame.convert(mode='RGBA')
                img = await self.bot.loop.run_in_executor(None,self.add_overlay,frame.resize(size=(282,282)),user,card.copy(),xp,rank,txt,colors,levels_info)
                img = ImageEnhance.Contrast(img).enhance(1.5).resize((800,265))
                images.append(img)
                duration.append(pfp.info['duration'])

            card.close()

            # image_file_object = BytesIO()
            gif = images[0]
            filename = './assets/cards/{}-{}-{}.gif'.format(user.id,xp,rank[0])
            gif.save(filename, format='gif', save_all=True, append_images=images[1:], loop=0, duration=duration, subrectangles=True)
            # image_file_object.seek(0)
            # return discord.File(fp=image_file_object, filename='card.gif')
            return discord.File('./assets/cards/{}-{}-{}.gif'.format(user.id,xp,rank[0]))
            # imageio.mimwrite('./assets/cards/{}-{}-{}.gif'.format(user.id,xp,rank[0]), images, format="GIF-PIL", duration=duration, subrectangles=True)
            # return discord.File('./assets/cards/{}-{}-{}.gif'.format(user.id,xp,rank[0]))

    def compress(self, original_file, max_size, scale: float):
        assert(0.0 < scale < 1.0)
        orig_image = Image.open(original_file)
        cur_size = orig_image.size

        while True:
            cur_size = (int(cur_size[0] * scale), int(cur_size[1] * scale))
            resized_file = orig_image.resize(cur_size, Image.ANTIALIAS)

            with BytesIO() as file_bytes:
                resized_file.save(file_bytes, optimize=True, quality=95, format='png')

                if file_bytes.tell() <= max_size:
                    file_bytes.seek(0, 0)
                    return file_bytes

    def add_overlay(self, pfp, user: discord.User, img, xp: int, rank: list, txt: list, colors, levels_info):
        #img = Image.new('RGBA', (card.width, card.height), color = (250,250,250,0))
        #img.paste(pfp, (20, 29))
        #img.paste(card, (0, 0), card)
        cardL = img.load()
        pfpL = pfp.load()
        for x in range(list(img.size)[0]):
            for y in range(img.size[1]):
                if sqrt((x-162)**2 + (y-170)**2) < 139:
                    cardL[x,y] = pfpL[x-20,y-29]
                elif cardL[x, y][3]<128:
                    cardL[x,y] = (255,255,255,0)


        xp_fnt = self.fonts['xp_fnt']
        NIVEAU_fnt = self.fonts['NIVEAU_fnt']
        levels_fnt = self.fonts['levels_fnt']
        rank_fnt = self.fonts['rank_fnt']
        RANK_fnt = self.fonts['RANK_fnt']
        name_fnt = self.fonts['name_fnt']

        img = self.add_xp_bar(img,xp-levels_info[2],levels_info[1]-levels_info[2],colors['bar'], colors['bar_background'])
        d = ImageDraw.Draw(img)
        d.text(self.calc_pos(user.name,name_fnt,610,68), user.name, font=name_fnt, fill=colors['name'])
        temp = '{} / {} xp ({}/{})'.format(xp-levels_info[2],levels_info[1]-levels_info[2],xp,levels_info[1])
        d.text((self.calc_pos(temp,xp_fnt,625,237)), temp, font=xp_fnt, fill=colors['xp'])
        d.text((380,140), txt[0], font=NIVEAU_fnt, fill=colors['NIVEAU'])
        d.text((self.calc_pos(str(levels_info[0]),levels_fnt,740,160,'right')), str(levels_info[0]), font=levels_fnt, fill=colors['xp'])
        temp = '{x[0]}/{x[1]}'.format(x=rank)
        d.text((self.calc_pos(txt[1],RANK_fnt,893,147,'center')), txt[1], font=RANK_fnt, fill=colors['rank'])
        d.text((self.calc_pos(temp,rank_fnt,893,180,'center')), temp, font=rank_fnt, fill=colors['rank'])
        return img

    def add_xp_bar(self, img, xp: int, needed_xp: int, color: tuple[int, int, int], background: tuple[int, int, int]):
        """Colorize the xp bar"""
        error_rate = 25
        data = np.array(img)   # "data" is a height x width x 4 numpy array
        red, green, blue, alpha = data.T # Temporarily unpack the bands for readability

        # Replace white with red... (leaves alpha values alone...)
        white_areas = (abs(red)-background[0] < error_rate) & (
            abs(blue)-background[1] < error_rate) & (abs(green)-background[2] < error_rate)
        white_areas[:298] = False & False & False
        white_areas[..., :260] = False & False & False
        white_areas[..., 300:] = False & False & False
        max_x = round(298 + (980-298)*xp/needed_xp)
        white_areas[max_x:] = False & False & False
        #white_areas[298:980] = True & True & True
        data[..., :-1][white_areas.T] = color # Transpose back needed
        return Image.fromarray(data)

    async def get_xp_bar_color(self, userID:int):
        return (45,180,105)
    
    async def get_xp(self, user: discord.User, guild_id: int):
        xp = await self.bdd_get_xp(user.id, guild_id)
        if xp is None or (isinstance(xp,list) and len(xp) == 0):
            return
        return xp[0]['xp']

    @commands.command(name="rank")
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(1,20,commands.BucketType.user)
    async def rank(self, ctx: MyContext, *, user: args.user=None):
        """Display a user XP.
        If you don't send any user, I'll display your own XP

        ..Example rank

        ..Example rank Z_runner#7515

        ..Doc user.html#check-the-xp-of-someone
        """
        try:
            if user is None:
                user = ctx.author
            if user.bot:
                return await ctx.send(await self.bot._(ctx.channel, "xp.bot-rank"))
            if ctx.guild is not None:
                if not await self.bot.get_config(ctx.guild.id, "enable_xp"):
                    return await ctx.send(await self.bot._(ctx.guild.id, "xp.xp-disabled"))
                xp_used_type: str = await self.bot.get_config(ctx.guild.id, "xp_type")
            else:
                xp_used_type = options['xp_type']["default"]
            xp = await self.get_xp(user,None if xp_used_type == "global" else ctx.guild.id)
            if xp is None:
                if ctx.author == user:
                    return await ctx.send(await self.bot._(ctx.channel, "xp.1-no-xp"))
                return await ctx.send(await self.bot._(ctx.channel, "xp.2-no-xp"))
            levels_info = None
            if xp_used_type == "global":
                ranks_nb = await self.bdd_get_nber()
                try:
                    rank = (await self.bdd_get_rank(user.id))['rank']
                except KeyError:
                    rank = "?"
            else:
                ranks_nb = await self.bdd_get_nber(ctx.guild.id)
                try:
                    rank = (await self.bdd_get_rank(user.id,ctx.guild))['rank']
                except KeyError:
                    rank = "?"
            if isinstance(rank, float):
                rank = int(rank)
            send_in_private = ctx.guild is None or await self.bot.get_config(ctx.guild.id, "rank_in_dm")
            use_author_dm = send_in_private and ctx.interaction is None
            # If we can send the rank card
            if ctx.guild is None or use_author_dm or ctx.channel.permissions_for(ctx.guild.me).attach_files:
                try:
                    await self.send_card(ctx, user, xp, rank, ranks_nb, xp_used_type, levels_info)
                    return
                except Exception as err:  # pylint: disable=broad-except
                    # log the error and fall back to embed/text
                    self.bot.dispatch("error", err, ctx)
            # if we can send embeds
            if ctx.can_send_embed:
                await self.send_embed(ctx, user, xp, rank, ranks_nb, levels_info, xp_used_type)
                return
            # fall back to raw text
            await self.send_txt(ctx, user, xp, rank, ranks_nb, levels_info, xp_used_type)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)

    async def send_card(self, ctx: MyContext, user: discord.User, xp: int, rank: int, ranks_nb: int, used_system: str, levels_info=None):
        try:
            myfile = discord.File('./assets/cards/{}-{}-{}.{}'.format(user.id,xp,rank,'gif' if user.display_avatar.is_animated() else 'png'))
        except FileNotFoundError:
            style = await self.bot.get_cog('Utilities').get_xp_style(user)
            txts = [await self.bot._(ctx.channel, "xp.card-level"), await self.bot._(ctx.channel, "xp.card-rank")]
            static = await self.bot.get_cog('Utilities').get_db_userinfo(['animated_card'],[f'`userID`={user.id}'])
            if user.display_avatar.is_animated():
                if static is not None:
                    static = not static['animated_card']
                else:
                    static = True
            self.bot.log.debug("XP card for user {} ({}xp - style {})".format(user.id,xp,style))
            myfile = await self.create_card(user,style,xp,used_system,[rank,ranks_nb],txts,force_static=static,levels_info=levels_info)
            if UsersCog := self.bot.get_cog("Users"):
                try:
                    await UsersCog.used_rank(user.id)
                except Exception as err:
                    self.bot.dispatch("error", err, ctx)
            if statsCog := self.bot.get_cog("BotStats"):
                statsCog.xp_cards["generated"] += 1
        send_in_private = ctx.guild is None or await self.bot.get_config(ctx.guild.id, "rank_in_dm")
        try:
            if ctx.interaction:
                await ctx.send(file=myfile, ephemeral=send_in_private)
            elif send_in_private:
                await ctx.author.send(file=myfile)
            else:
                await ctx.send(file=myfile)
        except discord.errors.HTTPException:
            await ctx.send(await self.bot._(ctx.channel, "xp.card-too-large"))
        else:
            await self.send_rankcard_tip(ctx)
        if statsCog := self.bot.get_cog("BotStats"):
            statsCog.xp_cards["sent"] += 1

    async def send_rankcard_tip(self, ctx: MyContext):
        if random.random() < 0.2 and await self.bot.tips_manager.should_show_user_tip(ctx.author.id, UserTip.RANK_CARD_PERSONALISATION):
            profile_cmd = await self.bot.get_command_mention("profile card")
            await self.bot.tips_manager.send_tip(ctx, UserTip.RANK_CARD_PERSONALISATION, profile_cmd=profile_cmd)

    async def send_embed(self, ctx: MyContext, user: discord.User, xp, rank, ranks_nb, levels_info, used_system: str):
        txts = [await self.bot._(ctx.channel, "xp.card-level"), await self.bot._(ctx.channel, "xp.card-rank")]
        if levels_info is None:
            levels_info = await self.calc_level(xp, used_system)
        emb = discord.Embed(color=self.embed_color)
        emb.set_author(name=user, icon_url=user.display_avatar)
        emb.add_field(name='XP', value="{}/{}".format(xp, levels_info[1]))
        emb.add_field(name=txts[0].title(), value=levels_info[0])
        emb.add_field(name=txts[1].title(), value="{}/{}".format(rank, ranks_nb))
        send_in_private = await self.bot.get_config(ctx.guild.id, "rank_in_dm")
        if ctx.interaction:
            await ctx.send(embed=emb, ephemeral=send_in_private)
        elif send_in_private:
            await ctx.author.send(embed=emb)
        else:
            await ctx.send(embed=emb)

    async def send_txt(self, ctx: MyContext, user: discord.User, xp, rank, ranks_nb, levels_info, used_system: str):
        txts = [await self.bot._(ctx.channel, "xp.card-level"), await self.bot._(ctx.channel, "xp.card-rank")]
        if levels_info is None:
            levels_info = await self.calc_level(xp, used_system)
        msg = """__**{}**__
**XP** {}/{}
**{}** {}
**{}** {}/{}""".format(user.name, xp, levels_info[1], txts[0].title(), levels_info[0], txts[1].title(), rank, ranks_nb)
        send_in_private = await self.bot.get_config(ctx.guild.id, "rank_in_dm")
        if ctx.interaction:
            await ctx.send(msg, ephemeral=send_in_private)
        elif send_in_private:
            await ctx.author.send(msg)
        else:
            await ctx.send(msg)

    def convert_average(self, nbr: int) -> str:
        res = str(nbr)
        for power, symb in ((9,'G'), (6,'M'), (3,'k')):
            if nbr >= 10**power:
                res = str(round(nbr/10**power, 1)) + symb
                break
        return res

    async def create_top_main(self, ranks, nbr, page, ctx: MyContext, used_system: str):
        txt = list()
        i = (page-1)*nbr
        for u in ranks[:nbr]:
            i += 1
            user = self.bot.get_user(u['user'])
            if user is None:
                try:
                    user = await self.bot.fetch_user(u['user'])
                except discord.NotFound:
                    user = await self.bot._(ctx.channel, "xp.del-user")
            if isinstance(user, discord.User):
                user_name = discord.utils.escape_markdown(user.name)
                if len(user_name) > 18:
                    user_name = user_name[:15]+'...'
            else:
                user_name = user
            l = await self.calc_level(u['xp'], used_system)
            xp = self.convert_average(u['xp'])
            txt.append('{} • **{} |** `lvl {}` **|** `xp {}`'.format(i,"__"+user_name+"__" if user==ctx.author else user_name,l[0],xp))
        return txt,i

    @commands.command(name="top")
    @commands.bot_has_permissions(send_messages=True)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def top(self, ctx: MyContext, page: typing.Optional[int]=1, scope: args.LeaderboardType='global'):
        """Get the list of the highest levels
        Each page has 20 users

        ..Example top 3

        ..Example top 7 guild

        ..Example top guild

        ..Doc user.html#get-the-general-ranking"""
        if ctx.guild is not None:
            if not await self.bot.get_config(ctx.guild.id,'enable_xp'):
                return await ctx.send(await self.bot._(ctx.guild.id, "xp.xp-disabled"))
            xp_system_used: str = await self.bot.get_config(ctx.guild.id,'xp_type')
        else:
            xp_system_used = "global"
        if xp_system_used == "global":
            if scope == 'global':
                if len(self.cache["global"]) == 0:
                    await self.bdd_load_cache(-1)
                ranks = sorted([{'userID':key, 'xp':value[1]} for key,value in self.cache['global'].items()], key=lambda x:x['xp'], reverse=True)
                max_page = ceil(len(self.cache['global'])/20)
            elif scope == 'guild':
                ranks = await self.bdd_get_top(10000, guild=ctx.guild)
                max_page = ceil(len(ranks)/20)
        else:
            #ranks = await self.bdd_get_top(20*page,guild=ctx.guild)
            if not ctx.guild.id in self.cache.keys():
                await self.bdd_load_cache(ctx.guild.id)
            ranks = sorted([{'userID':key, 'xp':value[1]} for key,value in self.cache[ctx.guild.id].items()], key=lambda x:x['xp'], reverse=True)
            max_page = ceil(len(ranks)/20)
        if page < 1:
            return await ctx.send(await self.bot._(ctx.channel, "xp.low-page"))
        elif max_page == 0:
            return await ctx.send(await self.bot._(ctx.channel, "xp.no-rank"))
        elif page > max_page:
            return await ctx.send(await self.bot._(ctx.channel, "xp.high-page"))
        ranks = ranks[(page-1)*20:]
        ranks = [{'user':x['userID'],'xp':x['xp']} for x in ranks]
        nbr = 20
        txt, i = await self.create_top_main(ranks,nbr,page,ctx,xp_system_used)
        while len("\n".join(txt)) > 1000 and nbr > 0:
            nbr -= 1
            txt, i = await self.create_top_main(ranks,nbr,page,ctx,xp_system_used)
            await asyncio.sleep(0.2)
        f_name = await self.bot._(ctx.channel, "xp.top-name", min=(page-1)*20+1, max=i, page=page, total=max_page)
        # author
        rank = await self.bdd_get_rank(ctx.author.id,ctx.guild if (scope=='guild' or xp_system_used != "global") else None)
        if len(rank) == 0:
            your_rank = {'name':"__"+await self.bot._(ctx.channel, "xp.top-your")+"__",'value':await self.bot._(ctx.guild, "xp.1-no-xp")}
        else:
            lvl = await self.calc_level(rank['xp'], xp_system_used)
            lvl = lvl[0]
            rk = rank['rank'] if 'rank' in rank.keys() else '?'
            xp = self.convert_average(rank['xp'])
            your_rank = {'name':"__"+await self.bot._(ctx.channel, "xp.top-your")+"__", 'value':"**#{} |** `lvl {}` **|** `xp {}`".format(rk, lvl, xp)}
            del rk
        # title
        if scope == 'guild' or xp_system_used != "global":
            t = await self.bot._(ctx.channel, "xp.top-title-2")
        else:
            t = await self.bot._(ctx.channel, "xp.top-title-1")
        if ctx.can_send_embed:
            emb = discord.Embed(title=t, color=self.embed_color)
            emb.add_field(name=f_name, value="\n".join(txt), inline=False)
            emb.add_field(**your_rank)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)
        else:
            await ctx.send(f_name+"\n\n"+'\n'.join(txt))


    async def clear_cards(self, all: bool=False):
        """Delete outdated rank cards"""
        files =  os.listdir('./assets/cards/')
        done: set[str] = set()
        for f in sorted([f.split('-')+['./assets/cards/'+f] for f in files], key=operator.itemgetter(1), reverse=True):
            if all or f[0] in done:
                os.remove(f[3])
            else:
                done.add(f[0])


    @commands.command(name='set_xp', aliases=["setxp", "set-xp"])
    @commands.guild_only()
    @commands.check(checks.has_admin)
    async def set_xp(self, ctx: MyContext, user: args.user, xp: int):
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
            prev_xp = await self.get_xp(user, None if xp_used_type == "global" else ctx.guild.id)
            await self.bdd_set_xp(user.id, xp, Type='set', guild=ctx.guild.id)
            await ctx.send(await self.bot._(ctx.guild.id, "xp.change-xp-ok", user=str(user), xp=xp))
        except Exception as err:
            await ctx.send(await self.bot._(ctx.guild.id, "minecraft.serv-error"))
            self.bot.dispatch("error", err, ctx)
        else:
            if ctx.guild.id not in self.cache.keys():
                await self.bdd_load_cache(ctx.guild.id)
            self.cache[ctx.guild.id][user.id] = [round(time.time()), xp]
            s = "XP of user {} `{}` edited (from {} to {}) in server `{}`".format(user, user.id, prev_xp, xp, ctx.guild.id)
            self.bot.log.info("[xp] " + s)
            emb = discord.Embed(description=s,color=8952255, timestamp=self.bot.utcnow())
            emb.set_footer(text=ctx.guild.name)
            emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
            await self.bot.send_embed(emb)

    async def gen_rr_id(self):
        return round(time.time()/2)

    async def rr_add_role(self, guildID:int, roleID:int, level:int):
        """Add a role reward in the database"""
        ID = await self.gen_rr_id()
        query = "INSERT INTO `roles_rewards` (`ID`,`guild`,`role`,`level`) VALUES (%(i)s,%(g)s,%(r)s,%(l)s);"
        async with self.bot.db_query(query, { 'i': ID, 'g': guildID, 'r': roleID, 'l': level }):
            pass
        return True

    async def rr_list_role(self, guild:int, level:int=-1):
        """List role rewards in the database"""
        if level < 0:
            query = f"SELECT * FROM `roles_rewards` WHERE guild={guild} ORDER BY level;"
        else:
            query = f"SELECT * FROM `roles_rewards` WHERE guild={guild} AND level={level} ORDER BY level;"
        async with self.bot.db_query(query) as query_results:
            liste = list(query_results)
        return liste

    async def rr_remove_role(self, ID:int):
        """Remove a role reward from the database"""
        query = ("DELETE FROM `roles_rewards` WHERE `ID`={};".format(ID))
        async with self.bot.db_query(query):
            pass
        return True

    @commands.group(name="roles_rewards", aliases=['rr'])
    @commands.guild_only()
    async def rr_main(self, ctx: MyContext):
        """Manage your roles rewards like a boss
        
        ..Doc server.html#roles-rewards"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @rr_main.command(name="add")
    @commands.check(checks.has_manage_guild)
    async def rr_add(self, ctx: MyContext, level:int, *, role:discord.Role):
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
            l = await self.rr_list_role(ctx.guild.id)
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)
        else:
            des = '\n'.join(["• <@&{}> : lvl {}".format(x['role'], x['level']) for x in l])
            max_rr: int = await self.bot.get_config(ctx.guild.id, "rr_max_number")
            title = await self.bot._(ctx.guild.id,"xp.rr_list", c=len(l), max=max_rr)
            emb = discord.Embed(title=title, description=des, timestamp=ctx.message.created_at)
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=emb)

    @rr_main.command(name="remove")
    @commands.check(checks.has_manage_guild)
    async def rr_remove(self, ctx: MyContext, level:int):
        """Remove a role reward
        When a member reaches this level, no role will be given anymore

        ..Example roles_rewards remove 10

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
    @commands.check(checks.has_manage_guild)
    @commands.cooldown(1,300,commands.BucketType.guild)
    async def rr_reload(self, ctx: MyContext):
        """Refresh roles rewards for the whole server

        ..Doc server.html#roles-rewards"""
        try:
            if not ctx.guild.me.guild_permissions.manage_roles:
                return await ctx.send(await self.bot._(ctx.guild.id,'moderation.mute.cant-mute'))
            c = 0
            rr_list = await self.rr_list_role(ctx.guild.id)
            if len(rr_list) == 0:
                await ctx.send(await self.bot._(ctx.guild, "xp.no-rr-2"))
                return
            used_system: str = await self.bot.get_config(ctx.guild.id, "xp_type")
            xps = [
                {'user':x['userID'],'xp':x['xp']}
                for x in await self.bdd_get_top(top=None, guild=None if used_system == "global" else ctx.guild)
            ]
            for member in xps:
                m = ctx.guild.get_member(member['user'])
                if m is not None:
                    level = (await self.calc_level(member['xp'], used_system))[0]
                    c += await self.give_rr(m, level, rr_list, remove=True)
            await ctx.send(await self.bot._(ctx.guild.id, "xp.rr-reload", role_count=c,member_count=ctx.guild.member_count))
        except Exception as err:
            self.bot.dispatch("command_error", ctx, err)


async def setup(bot: Axobot):
    if bot.database_online:
        await bot.add_cog(Xp(bot))
