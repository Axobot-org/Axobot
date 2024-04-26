import datetime
import json
import re
import time
from difflib import SequenceMatcher
from typing import Any, Optional, Union

import aiohttp
import discord
from asyncache import cached
from cachetools import TTLCache
from dateutil.parser import isoparse
from discord import app_commands
from discord.ext import commands

from fcts.rss import can_use_rss
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks
from libs.formatutils import FormatUtils
from libs.rss.rss_general import FeedObject

SERVER_ADDRESS_REGEX = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|"
                                  r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)+([A-Za-z]|"
                                  r"[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$")

def _similar(input_1: str, input_2: str):
    "Compare two strings and output the similarity ratio"
    return SequenceMatcher(None, input_1, input_2).ratio()

class Minecraft(commands.Cog):
    """Cog gathering all commands related to the Minecraft® game"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.feeds = {}
        self.file = "minecraft"
        self.embed_color = 0x16BD06
        self.uuid_cache: dict[str, str] = {}
        self._session: Optional[aiohttp.ClientSession] = None

    @property
    def session(self):
        "Get the aiohttp session"
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    async def cog_unload(self):
        if self._session is not None:
            await self._session.close()
            self._session = None


    @commands.hybrid_group(name="minecraft")
    async def mc_main(self, ctx: MyContext):
        """Search for info about servers/players/mods from Minecraft

        ..Doc minecraft.html#mc"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    async def send_embed(self, ctx: MyContext, embed: discord.Embed):
        "Try to send an embed into a channel, or report the error if it fails"
        try:
            await ctx.send(embed=embed)
        except discord.DiscordException as err:
            self.bot.dispatch("error", err, ctx)
            await ctx.send(await self.bot._(ctx.channel, "minecraft.serv-error"))

    @mc_main.command(name="mod")
    @app_commands.checks.cooldown(5, 20)
    async def mc_mod(self, ctx: MyContext, *, mod_name: str):
        """Get info about any mod registered on CurseForge or Modrinth

        ..Example minecraft mod Minecolonies

        ..Doc minecraft.html#mc"""
        await ctx.defer()
        if cf_result := await self.get_mod_from_curseforge(ctx, mod_name):
            cf_embed, cf_pertinence = cf_result
            if cf_pertinence > 0.9:
                await self.send_embed(ctx, cf_embed)
                return
        else:
            cf_embed, cf_pertinence = None, 0
        if mr_result := await self.get_mod_from_modrinth(ctx, mod_name):
            mr_embed, mr_pertinence = mr_result
            if mr_pertinence > 0.9:
                await self.send_embed(ctx, mr_embed)
                return
        else:
            mr_embed, mr_pertinence = None, 0
        if cf_pertinence > mr_pertinence and cf_embed is not None:
            await self.send_embed(ctx, cf_embed)
            return
        elif mr_embed is not None:
            await self.send_embed(ctx, mr_embed)
            return
        await ctx.send(await self.bot._(ctx.channel, "minecraft.no-mod"))

    async def get_mod_from_curseforge(self, ctx: MyContext, search_value: str):
        "Get a mod data from the CurseForge API"
        url = "https://api.curseforge.com/v1/mods/search"
        header = {
            "x-api-key": self.bot.others["curseforge"]
        }
        params = {
            "gameId": 432,
            "classId": 6,
            "sortField": 2,
            "sortOrder": "desc",
            "searchFilter": search_value
        }
        async with self.session.get(url, params=params, headers=header, timeout=10) as resp:
            if resp.status >= 400:
                raise ValueError(f"CurseForge API returned {resp.status} for {search_value}")
            api_results: list[dict[str, Any]] = (await resp.json())["data"]
        if len(api_results) == 0:
            return
        search = api_results[0]
        pertinence = _similar(search_value.lower(), search["name"].lower())
        if pertinence < 0.5:
            return
        authors = ", ".join([
            f"[{x['name']}]({x['url']})" for x in search['authors']
        ])
        date = f"<t:{isoparse(search['dateModified']).timestamp():.0f}>"
        categories = " - ".join(f"[{category['name']}]({category['url']})" for category in search["categories"])
        versions = set(
            x['gameVersion'] for x in search['latestFilesIndexes']
        )
        versions = " - ".join(
            sorted(versions, reverse=True,
                   key=lambda a: list(map(int, a.split('.'))))
        )
        data = {
            "name": search['name'],
            "authors": authors,
            "release": date,
            "categories": categories,
            "summary": search['summary'],
            "versions": versions,
            "downloads": int(search['downloadCount']),
            "id-curseforge": str(search['id'])
        }
        title = await self.bot._(ctx.channel, "minecraft.mod-title") + " - " + search['name']
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            url=search["links"]['websiteUrl'],
            timestamp=ctx.message.created_at
        )
        if logo := search['logo']:
            embed.set_thumbnail(url=logo['thumbnailUrl'])
        lang = await self.bot._(ctx.channel, "_used_locale")
        for name, data_value in data.items():
            if not data_value:
                continue
            translation = await self.bot._(ctx.channel, "minecraft.mod-fields."+name)
            if isinstance(data_value, int):
                data_value = await FormatUtils.format_nbr(data_value, lang)
            inline = (
                name in {"authors", "release", "downloads", "id-curseforge"}
                or name == "categories" and len(data_value) < 100
            )
            embed.add_field(name=translation, value=data_value, inline=inline)
        return embed, pertinence

    async def get_mod_from_modrinth(self, ctx: MyContext, search_value: str):
        "Get a mod data from the Modrinth API"
        url = "https://api.modrinth.com/v2/search"
        params = {
            "query": search_value,
            "facets": "[[\"project_type:mod\"]]",
        }
        async with self.session.get(url, params=params, timeout=10) as resp:
            if resp.status >= 400:
                raise ValueError(f"Modrinth API returned {resp.status} for {search_value}")
            api_results: list[dict[str, Any]] = (await resp.json())["hits"]
        if len(api_results) == 0:
            return
        search = api_results[0]
        pertinence = _similar(search_value.lower(), search["title"].lower())
        if pertinence < 0.5:
            return
        date = f"<t:{isoparse(search['date_modified']).timestamp():.0f}>"
        categories = " - ".join(search["display_categories"]) if "display_categories" in search else ""
        versions = " - ".join(search["versions"])
        data = {
            "name": search["title"],
            "author": search["author"],
            "release": date,
            "categories": categories,
            "summary": search["description"],
            "versions": versions,
            "downloads": int(search['downloads']),
            "id-modrinth": search["slug"]
        }
        title = await self.bot._(ctx.channel, "minecraft.mod-title") + " - " + search["title"]
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            url="https://modrinth.com/mod/" + search["slug"],
            timestamp=ctx.message.created_at
        )
        if logo := search["icon_url"]:
            embed.set_thumbnail(url=logo)
        lang = await self.bot._(ctx.channel, "_used_locale")
        for name, data_value in data.items():
            if not data_value:
                continue
            translation = await self.bot._(ctx.channel, "minecraft.mod-fields."+name)
            if isinstance(data_value, int):
                data_value = await FormatUtils.format_nbr(data_value, lang)
            inline = name in {"author", "release", "downloads", "id-modrinth"} or name == "categories" and len(data_value) < 100
            embed.add_field(name=translation, value=data_value, inline=inline)
        return embed, pertinence

    @mc_main.command(name="skin")
    @app_commands.checks.cooldown(5, 20)
    @commands.check(checks.bot_can_embed)
    async def mc_skin(self, ctx: MyContext, username: str):
        """Get the skin of any Minecraft Java player

        ..Example minecraft skin Notch

        ..Doc minecraft.html#mc"""
        await ctx.defer()
        uuid = await self.username_to_uuid(username)
        if uuid is None:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.player-not-found"))
            return
        title = await self.bot._(ctx.channel, "minecraft.player-skin-title", player=username)
        download = await self.bot._(ctx.channel, "minecraft.player-skin-download")
        emb = discord.Embed(
            title=title, color=self.embed_color, description=f"[{download}](https://visage.surgeplay.com/skin/{uuid})")
        emb.set_image(url="https://visage.surgeplay.com/full/384/" + uuid)
        await self.send_embed(ctx, emb)

    @mc_main.command(name="server")
    @app_commands.checks.cooldown(5, 20)
    async def mc_server(self, ctx: MyContext, ip: str, port: Optional[int] = None):
        """Get infos about any Minecraft Java server

        ..Example minecraft server play.gunivers.net

        ..Doc minecraft.html#mc"""
        if (validation := await self.validate_server_ip(ip, port)) is None:
            await ctx.send(await self.bot._(ctx.guild.id, "minecraft.invalid-ip"))
            return
        ip, port = validation
        port_str = str(port) if port else ''
        await ctx.defer()
        obj = await self.create_server_1(ctx.guild, ip, port_str)
        embed = await self.form_msg_server(obj, ctx.guild, (ip, port_str))
        await ctx.send(embed=embed)

    @mc_main.command(name="follow-server")
    @commands.guild_only()
    @commands.check(can_use_rss)
    @app_commands.checks.cooldown(5, 20)
    async def mc_follow_server(self, ctx: MyContext, ip: str, port: Optional[int] = None,
                               channel: Optional[discord.TextChannel] = None):
        """Follow a server's info in real time in your channel

        ..Example minecraft follow-server mc.hypixel.net

        ..Doc minecraft.html#mc"""
        await ctx.guild.get_channel_or_thread()
        if not ctx.bot.database_online:
            await ctx.send(await self.bot._(ctx.guild.id, "cases.no_database"))
            return
        if (validation := await self.validate_server_ip(ip, port)) is None:
            await ctx.send(await self.bot._(ctx.guild.id, "minecraft.invalid-ip"))
            return
        ip, port = validation
        await ctx.defer()
        is_over, flow_limit = await self.bot.get_cog('Rss').is_overflow(ctx.guild)
        if is_over:
            await ctx.send(await self.bot._(ctx.guild.id, "rss.flow-limit", limit=flow_limit))
            return
        if channel is None:
            channel = ctx.channel
        if not channel.permissions_for(ctx.guild.me).send_messages or not channel.permissions_for(ctx.guild.me).embed_links:
            await ctx.send(await self.bot._(ctx.guild.id, "minecraft.serv-follow.missing-perms"))
            return
        try:
            if port is None:
                display_ip = ip
            else:
                display_ip = f"{ip}:{port}"
            await self.bot.get_cog('Rss').db_add_feed(ctx.guild.id, channel.id, 'mc', f"{ip}:{port or ''}")
            await ctx.send(await self.bot._(ctx.guild, "minecraft.serv-follow.success", ip=display_ip, channel=channel.mention))
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, ctx)

    async def validate_server_ip(self, ip: str, port: Optional[int] = None):
        "Validate a server IP and port"
        if ":" in ip and port is None:
            ip, port_str = ip.split(":")
            if not port_str.isnumeric():
                return None
            port = int(port_str)
        if port is not None:
            if not 0 < port < 65536:
                return None
        if not SERVER_ADDRESS_REGEX.match(ip):
            return None
        return ip, port

    async def create_server_1(self, guild: discord.Guild, ip: str, port: Optional[str]=None) -> Union[str, 'MCServer']:
        "Collect and serialize server data from a given IP, using minetools.eu"
        if port is None:
            url = "https://api.minetools.eu/ping/"+str(ip)
        else:
            url = "https://api.minetools.eu/ping/"+str(ip)+"/"+str(port)
        try:
            async with self.session.get(url, timeout=5) as resp:
                data: dict = await resp.json()
        except Exception:
            return await self.create_server_2(guild, ip, port)
        if "error" in data:
            if data['error'] != 'timed out':
                self.bot.log.warning("(mc-server) Error on: " +
                                  url+"\n   "+data['error'])
            return data["error"]
        players: list[str] = []
        try:
            for player in data['players']['sample']:
                players.append(player['name'])
                if len(players) > 30:
                    break
        except KeyError:
            players = []
        formated_ip = f"{ip}:{port}" if port is not None else str(ip)
        if data["favicon"] is not None:
            img_url = "https://api.minetools.eu/favicon/" + \
                str(ip) + str("/"+str(port) if port is not None else '')
        else:
            img_url = None
        version = data['version']['name']
        online_players = data['players']['online']
        max_players = data['players']['max']
        latency = data['latency']
        return await self.MCServer(
            formated_ip, version=version, online_players=online_players, max_players=max_players, players=players, img=img_url,
            ping=latency, desc=data['description'], api='api.minetools.eu'
        ).clear_desc()

    async def create_server_2(self, guild: discord.Guild, ip: str, port: Optional[str]):
        "Collect and serialize server data from a given IP, using mcsrvstat.us"
        if port is None:
            url = "https://api.mcsrvstat.us/1/"+str(ip)
        else:
            url = "https://api.mcsrvstat.us/1/"+str(ip)+"/"+str(port)
        try:
            async with self.session.get(url, timeout=5) as resp:
                data: dict = await resp.json()
        except (aiohttp.ClientConnectorError, aiohttp.ContentTypeError):
            return await self.bot._(guild, "minecraft.no-api")
        except json.decoder.JSONDecodeError:
            return await self.bot._(guild, "minecraft.serv-error")
        except Exception as err:
            self.bot.log.error(f"[mc-server-2] Erreur sur l'url {url} :")
            self.bot.dispatch("error", err, f"While checking minecraft server {ip}")
            return await self.bot._(guild, "minecraft.serv-error")
        if data["debug"]["ping"] is False:
            return await self.bot._(guild, "minecraft.no-ping")
        if 'list' in data['players']:
            players = data['players']['list'][:20]
        else:
            players = []
        if "software" in data:
            version = data["software"]+" "+data['version']
        else:
            version = data['version']
        formated_ip = f"{ip}:{port}" if port is not None else str(ip)
        desc = "\n".join(data['motd']['clean'])
        online_players = data['players']['online']
        max_players = data['players']['max']
        l = None
        return await self.MCServer(
            formated_ip, version=version, online_players=online_players, max_players=max_players, players=players, img=None,
            ping=l, desc=desc, api="api.mcsrvstat.us"
        ).clear_desc()

    @cached(TTLCache(maxsize=1_000, ttl=60*60*24*7)) # 1 week
    async def username_to_uuid(self, username: str) -> str:
        """Convert a minecraft username to its uuid"""
        if username in self.uuid_cache:
            return self.uuid_cache[username]
        url = "https://api.mojang.com/users/profiles/minecraft/"+username
        async with self.session.get(url, timeout=10) as resp:
            try:
                search: dict = await resp.json()
                self.uuid_cache[username] = search.get("id")
            except aiohttp.ContentTypeError:
                self.uuid_cache[username] = None
        return self.uuid_cache[username]

    class MCServer:
        "Class containing all the data about a Minecraft server info, and methods to create a Discord embed from it"
        def __init__(self, ip: str, max_players: int, online_players: int, players: list[str], ping: float,
                     img: Optional[str], version: str, api: str, desc: str):
            self.ip = ip
            self.max_players = max_players
            self.online_players = online_players
            self.players = players
            if str(ping).isnumeric():
                self.ping = round(float(ping), 3)
            else:
                self.ping = ping
            self.image = img
            self.version = version
            self.api = api
            self.desc = desc

        async def clear_desc(self):
            "Clear the server description from any tabulation or color syntax"
            self.desc = re.sub(r'§.', '', self.desc)
            self.desc = re.sub(r'[ \t\r]{2,}', ' ', self.desc).strip()
            return self

        async def create_msg(self, guild: discord.Guild, translate):
            "Create a Discord embed from the saved data"
            if self.players == []:
                if self.online_players == 0:
                    p = [str(await translate(guild, "misc.none")).capitalize()]
                else:
                    p: list[str] = [await translate(guild, "minecraft.no-player-list")]
            else:
                p = self.players
            embed = discord.Embed(
                title=await translate(guild, "minecraft.serv-title", ip=self.ip),
                color=discord.Colour(0x417505),
                timestamp=datetime.datetime.utcfromtimestamp(time.time())
            )
            embed.set_footer(text=await translate(guild, "minecraft.server.from-provider", provider=self.api))
            if self.image is not None:
                embed.set_thumbnail(url=self.image)
            embed.add_field(name=await translate(guild, "minecraft.server.version"), value=self.version)
            embed.add_field(
                name=await translate(guild, "minecraft.server.players-count"),
                value=f"{self.online_players}/{self.max_players}"
            )
            if len(p) > 20:
                embed.add_field(name=await translate(guild, "minecraft.server.players-list-20"), value=", ".join(p[:20]))
            else:
                embed.add_field(name=await translate(guild, "minecraft.server.players-list-all"), value=", ".join(p))
            if self.ping is not None:
                embed.add_field(name=await translate(guild, "minecraft.server.latency"), value=f"{self.ping:.0f} ms")
            if self.desc:
                embed.add_field(
                    name=await translate(guild, "minecraft.server.description"),
                    value="```\n" + self.desc + "\n```",
                    inline=False
                )
            return embed

    async def send_msg_server(self, obj: Union[str, "MCServer"], channel: discord.abc.Messageable, ip: tuple[str, Optional[str]]):
        "Send the message into a Discord channel"
        guild = None if isinstance(channel, discord.DMChannel) else channel.guild
        embed = await self.form_msg_server(obj, guild, ip)
        if self.bot.zombie_mode:
            return
        if isinstance(channel, discord.DMChannel) or channel.permissions_for(channel.guild.me).embed_links:
            msg = await channel.send(embed=embed)
        else:
            try:
                await channel.send(await self.bot._(guild, "minecraft.cant-embed"))
            except discord.errors.Forbidden:
                pass
            msg = None
        return msg

    async def form_msg_server(self, obj: Union[str, "MCServer"], guild: discord.Guild, ip: tuple[str, Optional[str]]):
        "Create the embed from the saved data"
        if isinstance(obj, str):
            if ip[1] is None:
                ip = ip[0]
            else:
                ip = f"{ip[0]}:{ip[1]}"
            return discord.Embed(
                title=await self.bot._(guild, "minecraft.serv-title", ip=ip),
                color=discord.Colour(0x417505),
                description=obj,
                timestamp=datetime.datetime.utcfromtimestamp(time.time())
            )
        return await obj.create_msg(guild, self.bot._)

    async def find_msg(self, channel: discord.TextChannel, _ip: list, feed_id: str):
        "Find the minecraft server message posted from that feed"
        if channel is None:
            return None
        if feed_id.isnumeric():
            try:
                return await channel.fetch_message(int(feed_id))
            except (discord.Forbidden, discord.NotFound):
                pass
        return None

    async def check_feed(self, feed: FeedObject, send_stats: bool):
        "Refresh a minecraft server feed"
        i = feed.link.split(':')
        if i[1] == '':
            i[1] = None
        guild = self.bot.get_guild(feed.guild_id)
        if guild is None:
            self.bot.log.warn("[minecraft feed] Cannot find guild %s", feed.guild_id)
            return False
        if feed.link in self.feeds:
            obj = self.feeds[feed.link]
        else:
            try:
                obj = await self.create_server_1(guild, i[0], i[1])
            except Exception as err:
                self.bot.dispatch("error", err, f"Guild {feed.guild_id} - id {feed.feed_id}")
                return False
            self.feeds[feed.link] = obj
        try:
            channel = guild.get_channel_or_thread(feed.channel_id)
            if channel is None:
                self.bot.log.warn("[minecraft feed] Cannot find channel %s in guild %s", feed.channel_id, feed.guild_id)
                return False
            msg = await self.find_msg(channel, i, feed.structure)
            if msg is None:
                msg = await self.send_msg_server(obj, channel, i)
                if msg is not None:
                    await self.bot.get_cog('Rss').db_update_feed(
                        feed.feed_id,
                        [('structure', str(msg.id)), ('date', self.bot.utcnow())]
                    )
                    if send_stats:
                        if statscog := self.bot.get_cog("BotStats"):
                            statscog.rss_stats['messages'] += 1
                return True
            err = await self.form_msg_server(obj, guild, i)
            await msg.edit(embed=err)
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats['messages'] += 1
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
