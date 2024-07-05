import json
import re
from difflib import SequenceMatcher
from typing import Any, Awaitable, Callable

import aiohttp
import discord
from asyncache import cached
from cachetools import TTLCache
from dateutil.parser import isoparse
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot
from core.formatutils import FormatUtils
from modules.rss.src import FeedObject

SERVER_ADDRESS_REGEX = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|"
                                  r"^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)+([A-Za-z]|"
                                  r"[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$")

def _similar(input_1: str, input_2: str):
    "Compare two strings and output the similarity ratio"
    return SequenceMatcher(None, input_1, input_2).ratio()


class MCServer:
    "Class containing all the data about a Minecraft server info, and methods to create a Discord embed from it"
    def __init__(self, ip: str, max_players: int, online_players: int, players: list[str], ping: float,
                    img: str | None, version: str, api: str, desc: str):
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
        self.desc = re.sub(r"§.", '', self.desc)
        self.desc = re.sub(r"[ \t\r]{2,}", ' ', self.desc).strip()
        return self

    async def create_msg(self, source: discord.Interaction | discord.Guild, translate: Callable[[Any, str], Awaitable[str]]):
        "Create a Discord embed from the saved data"
        if self.players == [] and self.online_players != 0:
            players = [await translate(source, "minecraft.no-player-list")]
        else:
            players = [discord.utils.escape_markdown(name) for name in self.players]
        embed = discord.Embed(
            title=await translate(source, "minecraft.serv-title", ip=self.ip),
            color=discord.Colour(0x417505),
        )
        embed.set_footer(text=await translate(source, "minecraft.server.from-provider", provider=self.api))
        if self.image is not None:
            embed.set_thumbnail(url=self.image)
        embed.add_field(name=await translate(source, "minecraft.server.version"), value=self.version)
        embed.add_field(
            name=await translate(source, "minecraft.server.players-count"),
            value=f"{self.online_players}/{self.max_players}"
        )
        if len(players) > 20:
            embed.add_field(name=await translate(source, "minecraft.server.players-list-20"), value=", ".join(players[:20]))
        elif players:
            embed.add_field(name=await translate(source, "minecraft.server.players-list-all"), value=", ".join(players))
        if self.ping is not None:
            embed.add_field(name=await translate(source, "minecraft.server.latency"), value=f"{self.ping:.0f} ms")
        if self.desc:
            embed.add_field(
                name=await translate(source, "minecraft.server.description"),
                value="```\n" + self.desc + "\n```",
                inline=False
            )
        return embed

class Minecraft(commands.Cog):
    """Cog gathering all commands related to the Minecraft® game"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.feeds = {}
        self.file = "minecraft"
        self.embed_color = 0x16BD06
        self.uuid_cache: dict[str, str] = {}
        self._session: aiohttp.ClientSession | None = None

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

    mc_main = app_commands.Group(
        name="minecraft",
        description="Search for info about servers/players/mods from Minecraft",
    )

    @mc_main.command(name="mod")
    @app_commands.checks.cooldown(5, 20)
    async def mc_mod(self, interaction: discord.Interaction, *, mod_name: str):
        """Get info about any mod registered on CurseForge or Modrinth

        ..Example minecraft mod Minecolonies

        ..Doc minecraft.html#mc"""
        await interaction.response.defer()
        if cf_result := await self.get_mod_from_curseforge(interaction, mod_name):
            cf_embed, cf_pertinence = cf_result
            if cf_pertinence > 0.9:
                await interaction.followup.send(embed=cf_embed)
                return
        else:
            cf_embed, cf_pertinence = None, 0
        if mr_result := await self.get_mod_from_modrinth(interaction, mod_name):
            mr_embed, mr_pertinence = mr_result
            if mr_pertinence > 0.9:
                await interaction.followup.send(embed=mr_embed)
                return
        else:
            mr_embed, mr_pertinence = None, 0
        if cf_pertinence > mr_pertinence and cf_embed is not None:
            await interaction.followup.send(embed=cf_embed)
            return
        elif mr_embed is not None:
            await interaction.followup.send(embed=mr_embed)
            return
        await interaction.followup.send(await self.bot._(interaction, "minecraft.no-mod"))

    async def get_mod_from_curseforge(self, interaction: discord.Interaction, search_value: str):
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
            x["gameVersion"] for x in search["latestFilesIndexes"]
        )
        versions = " - ".join(
            sorted(versions, reverse=True,
                   key=lambda a: list(map(int, a.split('.'))))
        )
        data = {
            "name": search["name"],
            "authors": authors,
            "release": date,
            "categories": categories,
            "summary": search["summary"],
            "versions": versions,
            "downloads": int(search["downloadCount"]),
            "id-curseforge": str(search["id"])
        }
        title = await self.bot._(interaction, "minecraft.mod-title") + " - " + search["name"]
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            url=search["links"]["websiteUrl"],
        )
        if logo := search["logo"]:
            embed.set_thumbnail(url=logo["thumbnailUrl"])
        lang = await self.bot._(interaction, "_used_locale")
        for name, data_value in data.items():
            if not data_value:
                continue
            translation = await self.bot._(interaction, "minecraft.mod-fields."+name)
            if isinstance(data_value, int):
                data_value = await FormatUtils.format_nbr(data_value, lang)
            inline = (
                name in {"authors", "release", "downloads", "id-curseforge"}
                or name == "categories" and len(data_value) < 100
            )
            embed.add_field(name=translation, value=data_value, inline=inline)
        return embed, pertinence

    async def get_mod_from_modrinth(self, interaction: discord.Interaction, search_value: str):
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
            "downloads": int(search["downloads"]),
            "id-modrinth": search["slug"]
        }
        title = await self.bot._(interaction, "minecraft.mod-title") + " - " + search["title"]
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            url="https://modrinth.com/mod/" + search["slug"],
        )
        if logo := search["icon_url"]:
            embed.set_thumbnail(url=logo)
        lang = await self.bot._(interaction, "_used_locale")
        for name, data_value in data.items():
            if not data_value:
                continue
            translation = await self.bot._(interaction, "minecraft.mod-fields."+name)
            if isinstance(data_value, int):
                data_value = await FormatUtils.format_nbr(data_value, lang)
            inline = name in {"author", "release", "downloads", "id-modrinth"} or name == "categories" and len(data_value) < 100
            embed.add_field(name=translation, value=data_value, inline=inline)
        return embed, pertinence

    @mc_main.command(name="skin")
    @app_commands.checks.cooldown(5, 20)
    async def mc_skin(self, interaction: discord.Interaction, username: str):
        """Get the skin of any Minecraft Java player

        ..Example minecraft skin Notch

        ..Doc minecraft.html#mc"""
        await interaction.response.defer()
        uuid = await self.username_to_uuid(username)
        if uuid is None:
            await interaction.followup.send(await self.bot._(interaction, "minecraft.player-not-found"))
            return
        title = await self.bot._(interaction, "minecraft.player-skin-title", player=username)
        download = await self.bot._(interaction, "minecraft.player-skin-download")
        emb = discord.Embed(
            title=title,
            color=self.embed_color,
            description=f"[{download}](https://visage.surgeplay.com/skin/{uuid})"
        )
        emb.set_image(url="https://visage.surgeplay.com/full/384/" + uuid)
        await interaction.followup.send(embed=emb)

    @mc_main.command(name="server")
    @app_commands.checks.cooldown(5, 20)
    async def mc_server(self, interaction: discord.Interaction, ip: str, port: int | None = None):
        """Get infos about any Minecraft Java server

        ..Example minecraft server play.gunivers.net

        ..Doc minecraft.html#mc"""
        if (validation := await self.validate_server_ip(ip, port)) is None:
            await interaction.response.send_message(
                await self.bot._(interaction, "minecraft.invalid-ip"),
                ephemeral=True
            )
            return
        ip, port = validation
        port_str = str(port) if port else ''
        await interaction.response.defer()
        obj = await self.create_server_1(interaction, ip, port_str)
        embed = await self.form_msg_server(obj, interaction, (ip, port_str))
        await interaction.followup.send(embed=embed)

    @mc_main.command(name="follow-server")
    @app_commands.guild_only()
    @app_commands.checks.cooldown(5, 20)
    async def mc_follow_server(self, interaction: discord.Interaction, ip: str, port: int | None = None,
                               channel: discord.TextChannel | None = None):
        """Follow a server's info in real time in your channel

        ..Example minecraft follow-server mc.hypixel.net

        ..Doc minecraft.html#mc"""
        if not self.bot.database_online:
            await interaction.response.send_message(await self.bot._(interaction, "cases.no_database"), ephemeral=True)
            return
        if (validation := await self.validate_server_ip(ip, port)) is None:
            await interaction.response.send_message(await self.bot._(interaction, "minecraft.invalid-ip"), ephemeral=True)
            return
        ip, port = validation
        await interaction.response.defer()
        is_over, flow_limit = await self.bot.get_cog("Rss").is_overflow(interaction.guild)
        if is_over:
            await interaction.followup.send(await self.bot._(interaction, "rss.flow-limit", limit=flow_limit))
            return
        if channel is None:
            channel = interaction.channel
        bot_perms = channel.permissions_for(interaction.guild.me)
        if not bot_perms.send_messages or not bot_perms.embed_links:
            await interaction.followup.send(await self.bot._(interaction, "minecraft.serv-follow.missing-perms"))
            return
        if port is None:
            display_ip = ip
        else:
            display_ip = f"{ip}:{port}"
        await self.bot.get_cog("Rss").db_add_feed(interaction.guild.id, channel.id, "mc", f"{ip}:{port or ''}")
        await interaction.followup.send(
            await self.bot._(interaction, "minecraft.serv-follow.success", ip=display_ip, channel=channel.mention)
        )

    async def validate_server_ip(self, ip: str, port: int | None = None):
        "Validate a server IP and port"
        if ip.count(":") > 1 or (port is not None and ip.count(":") == 1):
            return None
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

    async def create_server_1(self, source: discord.Interaction | discord.Guild,
                              ip: str, port: str | None=None) -> str | MCServer:
        "Collect and serialize server data from a given IP, using minetools.eu"
        if port is None:
            url = "https://api.minetools.eu/ping/"+str(ip)
        else:
            url = "https://api.minetools.eu/ping/"+str(ip)+"/"+str(port)
        try:
            async with self.session.get(url, timeout=5) as resp:
                data: dict = await resp.json()
        except Exception:
            return await self.create_server_2(source, ip, port)
        if "error" in data:
            if data["error"] != "timed out":
                self.bot.log.warning("(mc-server) Error on: " +
                                  url+"\n   "+data["error"])
            return data["error"]
        players: list[str] = []
        try:
            for player in data["players"]["sample"]:
                players.append(player["name"])
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
        version = data["version"]["name"]
        online_players = data["players"]["online"]
        max_players = data["players"]["max"]
        latency = data["latency"]
        return await MCServer(
            formated_ip, version=version, online_players=online_players, max_players=max_players, players=players, img=img_url,
            ping=latency, desc=data["description"], api="api.minetools.eu"
        ).clear_desc()

    async def create_server_2(self, source: discord.Interaction | discord.Guild, ip: str, port: str | None):
        "Collect and serialize server data from a given IP, using mcsrvstat.us"
        if port is None:
            url = "https://api.mcsrvstat.us/1/"+str(ip)
        else:
            url = "https://api.mcsrvstat.us/1/"+str(ip)+"/"+str(port)
        try:
            async with self.session.get(url, timeout=5) as resp:
                data: dict = await resp.json()
        except (aiohttp.ClientConnectorError, aiohttp.ContentTypeError):
            return await self.bot._(source, "minecraft.no-api")
        except json.decoder.JSONDecodeError:
            return await self.bot._(source, "minecraft.serv-error")
        except Exception as err:
            self.bot.log.error(f"[mc-server-2] Erreur sur l'url {url} :")
            self.bot.dispatch("error", err, f"While checking minecraft server {ip}")
            return await self.bot._(source, "minecraft.serv-error")
        if data["debug"]["ping"] is False:
            return await self.bot._(source, "minecraft.no-ping")
        if "list" in data["players"]:
            players = data["players"]["list"][:20]
        else:
            players = []
        if "software" in data:
            version = data["software"]+" "+data["version"]
        else:
            version = data["version"]
        formated_ip = f"{ip}:{port}" if port is not None else str(ip)
        desc = "\n".join(data["motd"]["clean"])
        online_players = data["players"]["online"]
        max_players = data["players"]["max"]
        l = None
        return await MCServer(
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

    async def send_msg_server(self, obj: str | MCServer, channel: discord.abc.Messageable, ip: tuple[str, str | None]):
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

    async def form_msg_server(self, obj: str | MCServer, source: discord.Interaction | discord.Guild, ip: tuple[str, str | None]):
        "Create the embed from the saved data"
        if isinstance(obj, str):
            if ip[1] is None:
                ip = ip[0]
            else:
                ip = f"{ip[0]}:{ip[1]}"
            return discord.Embed(
                title=await self.bot._(source, "minecraft.serv-title", ip=ip),
                color=discord.Colour(0x417505),
                description=obj,
            )
        return await obj.create_msg(source, self.bot._)

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
                    await self.bot.get_cog("Rss").db_update_feed(
                        feed.feed_id,
                        [("structure", str(msg.id)), ("date", self.bot.utcnow())]
                    )
                    if send_stats:
                        if statscog := self.bot.get_cog("BotStats"):
                            statscog.rss_stats["messages"] += 1
                return True
            err = await self.form_msg_server(obj, guild, i)
            await msg.edit(embed=err)
            if statscog := self.bot.get_cog("BotStats"):
                statscog.rss_stats["messages"] += 1
            return True
        except Exception as err:
            self.bot.dispatch("error", err)
            return False


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
