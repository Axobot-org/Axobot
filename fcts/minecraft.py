import datetime
import json
import re
import time
from typing import Any, Union

import aiohttp
import discord
import frmc_lib
from dateutil.parser import isoparse
from discord.ext import commands
from frmc_lib import SearchType

from fcts import checks
from libs.bot_classes import Axobot, MyContext
from libs.formatutils import FormatUtils
from libs.rss.rss_general import FeedObject


class Minecraft(commands.Cog):
    """Cog gathering all commands related to the Minecraft® game.
Every information come from the website www.fr-minecraft.net"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.feeds = {}
        self.file = "minecraft"
        self.embed_color = 0x16BD06
        self.uuid_cache: dict[str, str] = {}

    @commands.command(name="mojang", aliases=['mojang_status'], enabled=False)
    @commands.cooldown(5, 20, commands.BucketType.user)
    async def mojang_status(self, ctx: MyContext):
        """Get Mojang server status

        ..Doc minecraft.html#mojang"""
        desc = await self.bot._(ctx.channel, "minecraft.mojang_desc")
        async with aiohttp.ClientSession() as session:
            # async with session.get('https://api.bowie-co.nz/api/v1/mojang/check') as r:
            async with session.get('https://status.mojang.com/check') as r:
                data = await r.json()
        if ctx.can_send_embed:
            embed = discord.Embed(color=discord.Colour(
                0x699bf9), timestamp=ctx.message.created_at)
            embed.set_thumbnail(
                url="https://www.minecraft-france.fr/wp-content/uploads/2020/05/mojang-logo-2.gif")
            embed.set_author(name="Mojang Studios - Services Status", url="https://status.mojang.com/check",
                             icon_url="https://www.minecraft.net/content/dam/franchise/logos/Mojang-Studios-Logo-Redbox.png")
            embed.set_footer(text="Requested by {}".format(
                ctx.author.display_name), icon_url=ctx.author.display_avatar.replace(format="png", size=512))
        else:
            text = "Mojang Studios - Services Status (requested by {})".format(
                ctx.author)

        async def get_status(key, value) -> tuple[str]:
            if key == "www.minecraft.net/en-us":
                key = "minecraft.net"
            if value == "green":
                k = self.bot.emojis_manager.customs['green_check'] + key
            elif value == "red":
                k = self.bot.emojis_manager.customs['red_cross'] + key
            elif value == 'yellow':
                k = self.bot.emojis_manager.customs['neutral_check'] + key
            else:
                k = self.bot.emojis_manager.customs['blurple'] + key
                dm = self.bot.get_user(279568324260528128).dm_channel
                if dm is None:
                    await self.bot.get_user(279568324260528128).create_dm()
                    dm = self.bot.get_user(279568324260528128).dm_channel
                await dm.send("Status mojang inconnu : " + value + " (serveur " + key + ")")
            if key in desc.keys():
                v = desc[key]
            else:
                v = ''
            return k, v

        if isinstance(data, dict):
            for K, V in data.items():
                k, v = await get_status(K, V)
                if ctx.can_send_embed:
                    embed.add_field(name=k, value=v, inline=False)
                else:
                    text += "\n {} *({})*".format(k, v)
        else:
            for item in data:
                if len(item) != 1:
                    continue
                k, v = await get_status(*list(item.items())[0])
                if ctx.can_send_embed:
                    embed.add_field(name=k, value=v, inline=False)
                else:
                    text += "\n {} *({})*".format(k, v)
        if ctx.can_send_embed:
            await ctx.send(embed=embed)
        else:
            await ctx.send(text)

    @commands.group(name="minecraft", aliases=["mc"])
    @commands.cooldown(5, 30, commands.BucketType.user)
    async def mc_main(self, ctx: MyContext):
        """Search for Minecraft game items/servers

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

    @mc_main.command(name="block", aliases=["bloc"])
    async def mc_block(self, ctx: MyContext, *, value='help'):
        """Get info about any block

        ..Doc minecraft.html#mc

        ..Example mc block stone"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "minecraft.block-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        try:
            block: frmc_lib.Item = frmc_lib.main(value, SearchType.BLOCK)
        except frmc_lib.ItemNotFoundError:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-block"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel, "minecraft.names"))[0], block.name)
        embed = discord.Embed(title=title, color=self.embed_color, url=block.url,
            timestamp=ctx.message.created_at, description=await self.bot._(ctx.channel, "minecraft.contact-mail"))
        if block.image:
            embed.set_thumbnail(url=block.image.replace(" ", "%20"))
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        embed.add_field(name="Nom", value=block.name, inline=False)
        l = ("\n".join(block.item_ids), block.stack_size, block.creative_tab, block.damages,
             block.durability, block.tool, block.tnt_resistance, ", ".join(block.mobs), block.version)
        for e, v in enumerate(await self.bot._(ctx.channel, "minecraft.block-fields")):
            if l[e] not in [None, '']:
                try:
                    embed.add_field(name=v, value=l[e], inline=False)
                except IndexError:
                    pass
        await self.send_embed(ctx, embed)

    @mc_main.command(name="entity", aliases=["entité", "mob"])
    async def mc_entity(self, ctx: MyContext, *, value='help'):
        """Get info about any entity

        ..Doc minecraft.html#mc

        ..Example mc entity slime"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "minecraft.entity-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        try:
            entity: frmc_lib.Entity = frmc_lib.main(value, SearchType.ENTITY)
        except frmc_lib.ItemNotFoundError:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-entity"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel, "minecraft.names"))[1], entity.name)
        embed = discord.Embed(title=title, color=self.embed_color, url=entity.url, timestamp=ctx.message.created_at, description=await self.bot._(ctx.channel, "minecraft.contact-mail"))
        if entity.image:
            embed.set_thumbnail(url=entity.image)
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        embed.add_field(name="Nom", value=entity.name, inline=False)
        l = (entity.entity_ids, entity.entity_type, entity.health, entity.attack,
             entity.xp, ", ".join(entity.biomes), entity.version)
        for e, v in enumerate(await self.bot._(ctx.channel, "minecraft.entity-fields")):
            if l[e] not in [None, '']:
                try:
                    embed.add_field(name=v, value=l[e], inline=False)
                except IndexError:
                    pass
        if entity.sizes != [0, 0, 0]:
            embed.add_field(name="Dimensions", value=await self.bot._(ctx.channel, "minecraft.dimensions", la=entity.sizes[0], lo=entity.sizes[1], ha=entity.sizes[2]))
        await self.send_embed(ctx, embed)

    @mc_main.command(name="item", aliases=['object'])
    async def mc_item(self, ctx: MyContext, *, value='help'):
        """Get info about any item

        ..Doc minecraft.html#mc

        ..Example mc item stick"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "minecraft.item-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        try:
            item: frmc_lib.Item = frmc_lib.main(value, SearchType.ITEM)
        except frmc_lib.ItemNotFoundError:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-item"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel, "minecraft.names"))[2], item.name)
        embed = discord.Embed(title=title, color=self.embed_color, url=item.url, timestamp=ctx.message.created_at, description=await self.bot._(ctx.channel, "minecraft.contact-mail"))
        if item.image is not None:
            embed.set_thumbnail(url=item.image)
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        embed.add_field(name="Nom", value=item.name, inline=False)
        l = ('\n'.join(item.item_ids), item.stack_size, item.creative_tab, item.damages,
             item.durability, item.tool, ", ".join(item.mobs), item.version)
        for e, v in enumerate(await self.bot._(ctx.channel, "minecraft.item-fields")):
            if l[e] not in [None, '']:
                try:
                    embed.add_field(name=v, value=l[e], inline=False)
                except IndexError:
                    pass
        await self.send_embed(ctx, embed)

    @mc_main.command(name="command", aliases=["commande", "cmd"])
    async def mc_cmd(self, ctx: MyContext, *, value='help'):
        """Get info about any command

        ..Doc minecraft.html#mc

        ..Example mc cmd execute if"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "minecraft.cmd-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        try:
            cmd: frmc_lib.Command = frmc_lib.main(value, SearchType.COMMAND)
        except frmc_lib.ItemNotFoundError:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-cmd"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel, "minecraft.names"))[3], cmd.name)
        embed = discord.Embed(title=title, color=self.embed_color, url=cmd.url, timestamp=ctx.message.created_at, description=await self.bot._(ctx.channel, "minecraft.contact-mail"))
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        l = (cmd.name, " ".join(cmd.syntax), cmd.examples, cmd.version)
        for e, v in enumerate(await self.bot._(ctx.channel, "minecraft.cmd-fields")):
            if e == 2:
                if len(l[e]) > 0:
                    examples = list()
                    for ex in l[e]:
                        s = "`{}`\n*{}*".format(ex[0], ex[1])
                        if len("\n".join(examples) + s) > 1024:
                            break
                        examples.append(s)
                    embed.add_field(name=v, value="\n".join(
                        examples), inline=False)
                continue
            if l[e] not in [None, '']:
                try:
                    embed.add_field(name=v, value=l[e], inline=False)
                except IndexError:
                    pass
        await self.send_embed(ctx, embed)

    @mc_main.command(name="advancement", aliases=["advc", "progrès"])
    async def mc_advc(self, ctx: MyContext, *, value='help'):
        """Get info about any advancement

        ..Example mc advc suit up

        ..Doc minecraft.html#mc"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "minecraft.adv-help"))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        try:
            adv: frmc_lib.Advancement = frmc_lib.main(value, SearchType.ADVANCEMENT)
        except frmc_lib.ItemNotFoundError:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-adv"))
            return
        title = "{} - {}".format((await self.bot._(ctx.channel, "minecraft.names"))[4], adv.name)
        embed = discord.Embed(title=title, color=self.embed_color, url=adv.url, timestamp=ctx.message.created_at, description=await self.bot._(ctx.channel, "minecraft.contact-mail"))
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        if adv.image is not None:
            embed.set_thumbnail(url=adv.image)
        # ("Nom","Identifiant","Type","Action","Parent","Enfants","Version d'ajout")
        l = (adv.name, adv.adv_id, adv.adv_type, adv.description,
             adv.parent, ", ".join(adv.children), adv.version)
        for e, v in enumerate(await self.bot._(ctx.channel, "minecraft.adv-fields")):
            if l[e] not in [None, '']:
                try:
                    embed.add_field(name=v, value=l[e], inline=False)
                except IndexError:
                    pass
        await self.send_embed(ctx, embed)

    @mc_main.command(name="mod", aliases=["mods"])
    async def mc_mod(self, ctx: MyContext, *, value: str = 'help'):
        """Get info about any mod registered on CurseForge

        ..Example mc mod Minecolonies

        ..Doc minecraft.html#mc"""
        if value == 'help':
            await ctx.send(await self.bot._(ctx.channel, "minecraft.mod-help", p=ctx.prefix))
            return
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        url = 'https://api.curseforge.com/v1/mods/search'
        header = {
            "x-api-key": self.bot.others["curseforge"]
        }
        params = {
            "gameId": 432,
            "classId": 6,
            "sortField": 2,
            "sortOrder": "desc",
            "searchFilter": value
        }
        async with aiohttp.ClientSession(loop=self.bot.loop, headers=header) as session:
            async with session.get(url, params=params, timeout=10) as resp:
                search: list[dict[str, Any]] = (await resp.json())["data"]
        if len(search) == 0:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-mod"))
            return
        search = search[0]
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
            "id": search['id']
        }
        title = "{} - {}".format((await self.bot._(ctx.channel, "minecraft.names"))[5], search['name'])
        embed = discord.Embed(
            title=title,
            color=self.embed_color,
            url=search["links"]['websiteUrl'],
            timestamp=ctx.message.created_at)
        embed.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        if logo := search['logo']:
            embed.set_thumbnail(url=logo['thumbnailUrl'])
        lang = await self.bot._(ctx.channel, "_used_locale")
        for name, data_value in data.items():
            if not data_value:
                continue
            translation = await self.bot._(ctx.channel, "minecraft.mod-fields."+name)
            if isinstance(data_value, int):
                data_value = await FormatUtils.format_nbr(data_value, lang)
            inline = name in {"authors", "release", "downloads", "id"} or name == "categories" and len(data_value) < 100
            embed.add_field(name=translation, value=data_value, inline=inline)
        await self.send_embed(ctx, embed)

    @mc_main.command(name="skin")
    @commands.check(checks.bot_can_embed)
    async def mc_skin(self, ctx: MyContext, username):
        """Get the skin of any Java player

        ..Example mc skin Notch

        ..Doc minecraft.html#mc"""
        if not ctx.can_send_embed:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.no-embed"))
            return
        uuid = await self.username_to_uuid(username)
        if uuid is None:
            await ctx.send(await self.bot._(ctx.channel, "minecraft.player-not-found"))
            return
        title = await self.bot._(ctx.channel, "minecraft.player-skin-title", player=username)
        download = await self.bot._(ctx.channel, "minecraft.player-skin-download")
        emb = discord.Embed(
            title=title, color=self.embed_color, description=f"[{download}](https://crafatar.com/skins/{uuid})")
        emb.set_image(url=f"https://crafatar.com/renders/body/{uuid}?overlay")
        await self.send_embed(ctx, emb)

    @mc_main.command(name="server")
    async def mc_server(self, ctx: MyContext, ip: str, port: int = None):
        """Get infos about any Minecraft server

        ..Example mc server play.gunivers.net

        ..Doc minecraft.html#mc"""
        if ":" in ip and port is None:
            i = ip.split(":")
            ip, port = i[0], i[1]
        obj = await self.create_server_1(ctx.guild, ip, port)
        await self.send_msg_server(obj, ctx.channel, (ip, port))

    @mc_main.command(name="add")
    @commands.guild_only()
    async def mc_add_server(self, ctx: MyContext, ip, port: int = None):
        """Follow a server's info (regularly displayed on this channel)

        ..Example mc add mc.hypixel.net

        ..Doc minecraft.html#mc"""
        if not ctx.bot.database_online:
            return await ctx.send(await self.bot._(ctx.guild.id, "cases.no_database"))
        if ":" in ip and port is None:
            i = ip.split(":")
            ip, port = i[0], i[1]
        elif port is None:
            port = ''
        is_over, flow_limit = await self.bot.get_cog('Rss').is_overflow(ctx.guild)
        if is_over:
            await ctx.send(await self.bot._(ctx.guild.id, "rss.flow-limit", limit=flow_limit))
            return
        try:
            if port is None:
                display_ip = ip
            else:
                display_ip = f"{ip}:{port}"
            await self.bot.get_cog('Rss').db_add_feed(ctx.guild.id, ctx.channel.id, 'mc', f"{ip}:{port}")
            await ctx.send(await self.bot._(ctx.guild, "minecraft.success-add", ip=display_ip, channel=ctx.channel.mention))
        except Exception as err:
            cmd = await self.bot.get_command_mention("about")
            await ctx.send(await self.bot._(ctx.guild, "errors.unknown2", about=cmd))
            self.bot.dispatch("error", err, ctx)

    async def create_server_1(self, guild: discord.Guild, ip: str, port=None) -> Union[str, 'MCServer']:
        "Collect and serialize server data from a given IP, using minetools.eu"
        if port is None:
            url = "https://api.minetools.eu/ping/"+str(ip)
        else:
            url = "https://api.minetools.eu/ping/"+str(ip)+"/"+str(port)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    r: dict = await resp.json()
        except Exception:
            return await self.create_server_2(guild, ip, port)
        if "error" in r:
            if r['error'] != 'timed out':
                self.bot.log.warning("(mc-server) Error on: " +
                                  url+"\n   "+r['error'])
            return r["error"]
        players = []
        try:
            for p in r['players']['sample']:
                players.append(p['name'])
                if len(players) > 30:
                    break
        except KeyError:
            players = []
        if not players:
            if r['players']['online'] == 0:
                players = [str(await self.bot._(guild, "misc.none")).capitalize()]
            else:
                players = [await self.bot._(guild, "minecraft.no-player-list")]
        IP = f"{ip}:{port}" if port is not None else str(ip)
        if r["favicon"] is not None:
            img_url = "https://api.minetools.eu/favicon/" + \
                str(ip) + str("/"+str(port) if port is not None else '')
        else:
            img_url = None
        v = r['version']['name']
        o = r['players']['online']
        m = r['players']['max']
        l = r['latency']
        return await self.MCServer(IP, version=v, online_players=o, max_players=m, players=players, img=img_url, ping=l, desc=r['description'], api='api.minetools.eu').clear_desc()

    async def create_server_2(self, guild: discord.Guild, ip: str, port: str):
        "Collect and serialize server data from a given IP, using mcsrvstat.us"
        if port is None:
            url = "https://api.mcsrvstat.us/1/"+str(ip)
        else:
            url = "https://api.mcsrvstat.us/1/"+str(ip)+"/"+str(port)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=5) as resp:
                    r: dict = await resp.json()
        except aiohttp.ClientConnectorError:
            return await self.bot._(guild, "minecraft.no-api")
        except json.decoder.JSONDecodeError:
            return await self.bot._(guild, "minecraft.serv-error")
        except Exception as err:
            self.bot.log.error(f"[mc-server-2] Erreur sur l'url {url} :")
            self.bot.dispatch("error", err, f"While checking minecraft server {ip}")
            return await self.bot._(guild, "minecraft.serv-error")
        if r["debug"]["ping"] is False:
            return await self.bot._(guild, "minecraft.no-ping")
        if 'list' in r['players'].keys():
            players = r['players']['list'][:20]
        else:
            players = []
        if players == []:
            if r['players']['online'] == 0:
                players = [str(await self.bot._(guild, "misc.none")).capitalize()]
            else:
                players = [await self.bot._(guild, "minecraft.no-player-list")]
        if "software" in r.keys():
            version = r["software"]+" "+r['version']
        else:
            version = r['version']
        IP = f"{ip}:{port}" if port is not None else str(ip)
        desc = "\n".join(r['motd']['clean'])
        o = r['players']['online']
        m = r['players']['max']
        l = None
        return await self.MCServer(IP, version=version, online_players=o, max_players=m, players=players, img=None, ping=l, desc=desc, api="api.mcsrvstat.us").clear_desc()

    async def username_to_uuid(self, username: str) -> str:
        """Convert a minecraft username to its uuid"""
        if username in self.uuid_cache:
            return self.uuid_cache[username]
        url = "https://api.mojang.com/users/profiles/minecraft/"+username
        async with aiohttp.ClientSession(loop=self.bot.loop) as session:
            async with session.get(url, timeout=10) as resp:
                try:
                    search: dict = await resp.json()
                    self.uuid_cache[username] = search.get("id")
                except aiohttp.ContentTypeError:
                    self.uuid_cache[username] = None
        return self.uuid_cache[username]

    class MCServer:
        def __init__(self, ip: str, max_players: int, online_players: int, players: list[str], ping: float, img, version, api: str, desc: str):
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
                    p = ["Aucun"]
                else:
                    p: list[str] = [await translate(guild, "minecraft.no-player-list")]
            else:
                p = self.players
            embed = discord.Embed(title=await translate(guild, "minecraft.serv-title", ip=self.ip), color=discord.Colour(0x417505), timestamp=datetime.datetime.utcfromtimestamp(time.time()))
            embed.set_footer(text="From {}".format(self.api))
            if self.image is not None:
                embed.set_thumbnail(url=self.image)
            embed.add_field(name="Version", value=self.version)
            embed.add_field(name=await translate(guild, "minecraft.serv-0"), value="{}/{}".format(self.online_players, self.max_players))
            if len(p) > 20:
                embed.add_field(name=await translate(guild, "minecraft.serv-1"), value=", ".join(p[:20]))
            else:
                embed.add_field(name=await translate(guild, "minecraft.serv-2"), value=", ".join(p))
            if self.ping is not None:
                embed.add_field(name=await translate(guild, "minecraft.serv-3"), value=f'{self.ping} ms')
            if self.desc:
                embed.add_field(name="Description", value=self.desc, inline=False)
            return embed

    async def send_msg_server(self, obj, channel: discord.abc.Messageable, ip: str):
        "Send the message into a Discord channel"
        guild = None if isinstance(
            channel, discord.DMChannel) else channel.guild
        e = await self.form_msg_server(obj, guild, ip)
        if self.bot.zombie_mode:
            return
        if isinstance(channel, discord.DMChannel) or channel.permissions_for(channel.guild.me).embed_links:
            msg = await channel.send(embed=e)
        else:
            try:
                await channel.send(await self.bot._(guild, "minecraft.cant-embed"))
            except discord.errors.Forbidden:
                pass
            msg = None
        return msg

    async def form_msg_server(self, obj, guild: discord.Guild, ip: str):
        if isinstance(obj, str):
            if ip[1] is None:
                ip = ip[0]
            else:
                ip = f"{ip[0]}:{ip[1]}"
            return discord.Embed(title=await self.bot._(guild, "minecraft.serv-title", ip=ip), color=discord.Colour(0x417505), description=obj, timestamp=datetime.datetime.utcfromtimestamp(time.time()))
        else:
            return await obj.create_msg(guild, self.bot._)

    async def find_msg(self, channel: discord.TextChannel, ip: list, feed_id: str):
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
                    await self.bot.get_cog('Rss').db_update_feed(feed.feed_id, [('structure', str(msg.id)), ('date', self.bot.utcnow())])
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


async def setup(bot):
    await bot.add_cog(Minecraft(bot))
