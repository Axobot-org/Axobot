import discord
import importlib
import re
import operator
import aiohttp
from fcts import args
from discord.ext import commands
from typing import List
from classes import zbot, MyContext

importlib.reload(args)


class Utilities(commands.Cog):
    """This cog has various useful functions for the rest of the bot."""

    def __init__(self, bot: zbot):
        self.bot = bot
        self.list_prefixs = dict()
        self.file = "utilities"
        self.config = {}
        self.table = 'users'
        self.new_pp = False
        bot.add_check(self.global_check)

    def cog_unload(self):
        self.bot.remove_check(self.global_check)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.get_bot_infos()

    async def get_bot_infos(self):
        config_list = await self.bot.cogs['Servers'].get_bot_infos(self.bot.user.id)
        if len(config_list) > 0:
            self.config = config_list[0]
            self.config.pop('token', None)
            return self.config
        return None

    def find_prefix(self, guild: discord.Guild):
        if guild is None or not self.bot.database_online:
            return '!'
        if str(guild.id) in self.list_prefixs.keys():
            return self.list_prefixs[str(guild.id)]
        else:
            cnx = self.bot.cogs['Servers'].bot.cnx_frm
            cursor = cnx.cursor(dictionary=True)
            cursor.execute("SELECT `prefix` FROM `{}` WHERE `ID`={}".format(
                self.bot.cogs["Servers"].table, guild.id))
            liste = list()
            for x in cursor:
                if len(x['prefix']) > 0:
                    liste.append(x['prefix'])
            if liste == []:
                self.list_prefixs[str(guild.id)] = '!'
                return '!'
            self.list_prefixs[str(guild.id)] = liste[0]
            return str(liste[0])

    def update_prefix(self, ID: int, prefix: str):
        try:
            self.bot.log.debug(
                "Prefix updated for guild {} : changed to {}".format(ID, prefix))
        except:
            pass
        self.list_prefixs[str(ID)] = prefix

    async def find_everything(self, ctx: MyContext, name: str, Type: str=None):
        item = None
        if type(Type) == str:
            Type = Type.lower()
        if Type is None:
            for i in [commands.MemberConverter, commands.RoleConverter,
                      commands.TextChannelConverter, commands.VoiceChannelConverter, commands.InviteConverter,
                      args.user, commands.EmojiConverter, commands.CategoryChannelConverter, args.snowflake]:
                try:
                    a = await i().convert(ctx, name)
                    item = a
                    if item is not None:
                        return item
                except:
                    pass
            return None
        elif Type == 'member':
            try:
                item = await commands.MemberConverter().convert(ctx, name)
            except:
                pass
        elif Type == 'role':
            try:
                item = await commands.RoleConverter().convert(ctx, name)
            except:
                pass
        elif Type == 'user':
            try:
                item = await commands.UserConverter().convert(ctx, name)
            except:
                if name.isnumeric():
                    item = await self.bot.fetch_user(int(name))
        elif Type == 'textchannel':
            try:
                item = await commands.TextChannelConverter().convert(ctx, name)
            except:
                pass
        elif Type == 'invite':
            try:
                item = await commands.InviteConverter().convert(ctx, name)
            except:
                pass
        elif Type == 'voicechannel':
            try:
                item = await commands.VoiceChannelConverter().convert(ctx, name)
            except:
                pass
        elif Type == 'channel':
            try:
                item = await commands.TextChannelConverter().convert(ctx, name)
            except:
                try:
                    item = await commands.VoiceChannelConverter().convert(ctx, name)
                except:
                    pass
        elif Type == 'emoji':
            try:
                item = await commands.EmojiConverter().convert(ctx, name)
            except:
                pass
        elif Type == 'category':
            try:
                item = await commands.CategoryChannelConverter().convert(ctx, name)
            except:
                pass
        elif (Type == 'guild' or Type == "server") and name.isnumeric():
            item = self.bot.get_guild(int(name))
        elif Type in ["snowflake", "id"]:
            try:
                item = await args.snowflake().convert(ctx, name)
            except:
                pass
        return item

    async def find_img(self, name: str):
        return discord.File("../images/{}".format(name))

    async def suppr(self, msg: discord.Message):
        try:
            await msg.delete()
        except:
            print("Unable to delete message "+str(msg))

    async def global_check(self, ctx: MyContext):
        """Do a lot of checks before executing a command (banned guilds, system message etc)"""
        if self.bot.zombie_mode:
            if isinstance(ctx, commands.Context) and ctx.command.name in self.bot.allowed_commands:
                return True
            return False
        if not isinstance(ctx, commands.Context) or self.config is None:
            return True
        if ctx.message.type != discord.MessageType.default:
            return False
        if await self.bot.cogs['Admin'].check_if_admin(ctx):
            return True
        elif not self.config:
            await self.get_bot_infos()
        if len(self.config) == 0 or self.config is None:
            return True
        if ctx.guild is not None:
            if str(ctx.guild.id) in self.config['banned_guilds'].split(";"):
                return False
        if str(ctx.author.id) in self.config['banned_users'].split(";"):
            return False
        return True
    
    async def get_members_repartition(self, members: List[discord.Member]):
        """Get number of total/online/bots members in a selection"""
        bots = online = total = 0
        for u in members:
            if u.bot:
                bots += 1
            if u.status != discord.Status.offline:
                online += 1
            total += 1
        return total, bots, online

    async def check_any_link(self, text: str):
        ch = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(ch, text)

    async def check_discord_invite(self, text: str):
        ch = r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)"
        return re.search(ch, text)

    def sync_check_any_link(self, text: str):
        ch = r"(https?://?(?:[-\w.]|(?:%[\da-fA-F]{2}))+|discord.gg/[^\s]+)"
        return re.search(ch, text)

    def sync_check_discord_invite(self, text: str):
        ch = r"((?:discord\.gg|discord(?:app)?.com/invite|discord.me)/.+)"
        return re.search(ch, text)

    async def clear_msg(self, text: str, everyone: bool=False, ctx: MyContext=None, emojis: bool=True):
        """Remove every mass mention from a text, and add custom emojis"""
        # if everyone:
        #     text = text.replace("@everyone","@"+u"\u200B"+"everyone").replace("@here","@"+u"\u200B"+"here")
        # for x in re.finditer(r'<(a?:[^:]+:)\d+>',text):
        #    text = text.replace(x.group(0),x.group(1))
        # for x in self.bot.emojis: #  (?<!<|a)(:[^:<]+:)
        #    text = text.replace(':'+x.name+':',str(x))
        if emojis:
            for x in re.finditer(r'(?<!<|a):([^:<]+):', text):
                try:
                    if ctx is not None:
                        em = await commands.EmojiConverter().convert(ctx, x.group(1))
                    else:
                        if x.group(1).isnumeric():
                            em = self.bot.get_emoji(int(x.group(1)))
                        else:
                            em = discord.utils.find(
                                lambda e: e.name == x.group(1), self.bot.emojis)
                except:
                    # except Exception as e:
                    # print(e)
                    continue
                if em is not None:
                    text = text.replace(x.group(0), "<{}:{}:{}>".format(
                        'a' if em.animated else '', em.name, em.id))
        return text

    async def get_db_userinfo(self, columns=[], criters=["userID > 1"], relation="AND", Type=dict):
        """Get every info about a user with the database"""
        await self.bot.wait_until_ready()
        if not (isinstance(columns, (list, tuple)) and isinstance(criters, (list, tuple))):
            raise ValueError
        if not self.bot.database_online:
            return None
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=(Type==dict))
        if columns == []:
            cl = "*"
        else:
            cl = "`"+"`,`".join(columns)+"`"
        relation = " "+relation+" "
        query = ("SELECT {} FROM `{}` WHERE {}".format(
            cl, self.table, relation.join(criters)))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        if len(liste) == 1:
            return liste[0]
        elif len(liste) > 1:
            return liste
        else:
            return None

    async def change_db_userinfo(self, userID: int, key: str, value):
        """Change something about a user in the database"""
        try:
            if not self.bot.database_online:
                return None
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary=True)
            query = "INSERT INTO `{t}` (`userID`,`{k}`) VALUES (%(u)s,%(v)s) ON DUPLICATE KEY UPDATE {k} = %(v)s;".format(
                t=self.table, k=key)
            cursor.execute(query, {'u': userID, 'v': value})
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['Errors'].on_error(e, None)
            return False

    async def get_number_premium(self):
        """Return the number of premium users"""
        try:
            params = await self.get_db_userinfo(criters=['Premium=1'])
            return len(params)
        except Exception as e:
            await self.bot.cogs['Errors'].on_error(e, None)

    async def get_xp_style(self, user: discord.User) -> str:
        parameters = None
        try:
            parameters = await self.get_db_userinfo(criters=["userID="+str(user.id)], columns=['xp_style'])
        except Exception as e:
            await self.bot.cogs["Errors"].on_error(e, None)
        if parameters is None or parameters['xp_style'] == '':
            return 'dark'
        return parameters['xp_style']

    async def add_check_reaction(self, message: discord.Message):
        if self.bot.zombie_mode:
            return
        try:
            emoji = discord.utils.get(self.bot.emojis, name='greencheck')
            if emoji:
                await message.add_reaction(emoji)
            else:
                await message.add_reaction('\u2705')
        except discord.Forbidden:
            await message.channel.send(":ok:")
        except:
            pass

    async def allowed_card_styles(self, user: discord.User):
        """Retourne la liste des styles autorisées pour la carte d'xp de cet utilisateur"""
        liste = ['blue', 'dark', 'green', 'grey', 'orange',
                 'purple', 'red', 'turquoise', 'yellow']
        if not self.bot.database_online:
            return sorted(liste)
        liste2 = []
        if await self.bot.get_cog('Admin').check_if_admin(user):
            liste2.append('admin')
        if not self.bot.database_online:
            return sorted(liste2)+sorted(liste)
        userflags: list = await self.bot.get_cog('Users').get_userflags(user)
        if 'support' in userflags:
            liste2.append('support')
        if 'contributor' in userflags:
            liste2.append('contributor')
        if 'partner' in userflags:
            liste2.append('partner')
        if 'premium' in userflags:
            liste2.append('premium')
        unlocked: list = await self.bot.get_cog('Users').get_rankcards(user)
        if 'blurple_19' in unlocked:
            liste.append('blurple19')
        if 'blurple_20' in unlocked:
            liste.append('blurple20')
        if 'rainbow' in unlocked:
            liste.append('rainbow')
        if 'christmas_19' in unlocked:
            liste.append('christmas19')
        if 'christmas_20' in unlocked:
            liste.append('christmas20')
        if 'halloween_20' in unlocked:
            liste.append('halloween20')
        return sorted(liste2)+sorted(liste)

    async def get_languages(self, user: discord.User, limit: int=0):
        """Get the most used languages of an user
        If limit=0, return every languages"""
        if not self.bot.database_online:
            return ["en"]
        languages = list()
        disp_lang = list()
        available_langs = self.bot.cogs['Languages'].languages
        for s in self.bot.guilds:
            if user in s.members:
                lang = await self.bot.get_config(s.id, 'language')
                if lang is None:
                    lang = available_langs.index(
                        self.bot.cogs['Servers'].default_language)
                languages.append(lang)
        for e in range(len(self.bot.cogs['Languages'].languages)):
            if languages.count(e) > 0:
                disp_lang.append((available_langs[e], round(
                    languages.count(e)/len(languages), 2)))
        disp_lang.sort(key=operator.itemgetter(1), reverse=True)
        if limit == 0:
            return disp_lang
        else:
            return disp_lang[:limit]

    async def add_user_eventPoint(self, userID: int, points: int, override: bool = False, check_event: bool = True):
        """Add some events points to a user
        if override is True, then the number of points will override the old score"""
        try:
            if not self.bot.database_online:
                return True
            if check_event and self.bot.current_event is None:
                return True
            cnx = self.bot.cnx_frm
            cursor = cnx.cursor(dictionary=True)
            if override:
                query = ("INSERT INTO `{t}` (`userID`,`events_points`) VALUES ('{u}',{p}) ON DUPLICATE KEY UPDATE events_points = '{p}';".format(
                    t=self.table, u=userID, p=points))
            else:
                query = ("INSERT INTO `{t}` (`userID`,`events_points`) VALUES ('{u}',{p}) ON DUPLICATE KEY UPDATE events_points = events_points + '{p}';".format(
                    t=self.table, u=userID, p=points))
            cursor.execute(query)
            cnx.commit()
            cursor.close()
            return True
        except Exception as e:
            await self.bot.cogs['Errors'].on_error(e, None)
            return False

    async def get_eventsPoints_rank(self, userID: int):
        "Get the ranking of an user"
        if not self.bot.database_online:
            return None
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=True)
        query = (
            f"SELECT userID, events_points, FIND_IN_SET( events_points, ( SELECT GROUP_CONCAT( events_points ORDER BY events_points DESC ) FROM {self.table} ) ) AS rank FROM {self.table} WHERE userID = {userID}")
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        if len(liste) == 0:
            return None
        return liste[0]

    async def get_eventsPoints_nbr(self) -> int:
        if not self.bot.database_online:
            return 0
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary=False)
        query = f"SELECT COUNT(*) FROM {self.table} WHERE events_points > 0"
        cursor.execute(query)
        result = list(cursor)[0][0]
        cursor.close()
        return result

    async def check_votes(self, userid: int) -> list:
        """check if a user voted on any bots list website"""
        votes = list()
        async with aiohttp.ClientSession() as session:
            try:  # https://top.gg/bot/486896267788812288
                async with session.get(f'https://top.gg/api/bots/486896267788812288/check?userId={userid}', headers={'Authorization': str(self.bot.dbl_token)}) as r:
                    js = await r.json()
                    if js["voted"]:
                        votes.append(("Discord Bots List", "https://top.gg/"))
            except Exception as e:
                await self.bot.get_cog("Errors").on_error(e, None)
            try:  # https://botlist.space/bot/486896267788812288
                headers = {'Authorization': self.bot.others['botlist.space']}
                async with session.get('https://api.botlist.space/v1/bots/486896267788812288/upvotes', headers=headers) as r:
                    js = await r.json()
                    if str(userid) in [x["user"]['id'] for x in js]:
                        votes.append(
                            ("botlist.space", "https://botlist.space/"))
            except Exception as e:
                await self.bot.get_cog("Errors").on_error(e, None)
            try:  # https://discord.boats/bot/486896267788812288
                headers = {'Authorization': self.bot.others['discordboats']}
                async with session.get(f"https://discord.boats/api/bot/486896267788812288/voted?id={userid}", headers=headers) as r:
                    js = await r.json()
                    if (not js["error"]) and js["voted"]:
                        votes.append(
                            ("Discord Boats", "https://discord.boats/"))
            except Exception as e:
                await self.bot.get_cog("Errors").on_error(e, None)
            return votes


def setup(bot):
    bot.add_cog(Utilities(bot))
