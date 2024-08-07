import json
from io import BytesIO
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from core.bot_classes import Axobot


class LoadArguments:
    """Arguments for the load_backup function"""
    def __init__(self, match_by_name: bool, delete_old_channels: bool, delete_old_roles: bool, delete_old_emojis: bool,
                 delete_old_webhooks: bool):
        self.match_by_name = match_by_name
        self.delete_old_channels = delete_old_channels
        self.delete_old_roles = delete_old_roles
        self.delete_old_emojis = delete_old_emojis
        self.delete_old_webhooks = delete_old_webhooks


class Backups(commands.Cog):
    """This cog is used to make and apply backups of a Discord server"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "s_backups"
        self.backups_loading: set[int] = set()

    main_backup = app_commands.Group(
        name="server-backup",
        description="Make and apply backups of your server",
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True,
    )

    @main_backup.command(name="load")
    @app_commands.checks.cooldown(1, 180)
    @app_commands.describe(
        backup_file="The JSON file to load, created by the `server-backup create` command",
        match_by_name="If False, only match channels/roles by ID and do not fallback to name",
        delete_old_channels="If True, delete every current channel/category that is not in the backup",
        delete_old_roles="If True, delete every current role that is not in the backup",
        delete_old_emojis="If True, delete every current emoji that is not in the backup",
        delete_old_webhooks="If True, delete every current webhook that is not in the backup",
    )
    async def backup_load(self, interaction: discord.Interaction,
                          backup_file: discord.Attachment,
                          match_by_name: bool = True,
                          delete_old_channels: bool = False,
                          delete_old_roles: bool = False,
                          delete_old_emojis: bool = False,
                          delete_old_webhooks: bool = False,
                          ):
        """Load a backup created with `server-backup create`
Arguments are:
    - delete_old_channels: delete every current channel/category
    - delete_old_roles: delete every current role
    - delete_old_emojis: delete every current emoji
    - delete_old_webhooks: well, same but with webhooks

..Example backup load

..Example backup load delete_old_roles:True delete_old_emojis:True

..Doc server.html#server-backup"""
        if interaction.guild_id in self.backups_loading:
            await interaction.response.send_message(
                await self.bot._(interaction, "s_backup.already_running"), ephemeral=True
            )
            return
        # Loading backup from file
        try:
            data = json.loads(await backup_file.read())
        except (json.decoder.JSONDecodeError, IndexError):
            await interaction.response.send_message(
                await self.bot._(interaction, "s_backup.invalid_file"), ephemeral=True
            )
            return
        await interaction.response.send_message(
            await self.bot._(interaction, "s_backup.loading")
        )
        # compiling args
        arguments = LoadArguments(
            match_by_name,
            delete_old_channels,
            delete_old_roles,
            delete_old_emojis,
            delete_old_webhooks
        )
        self.backups_loading.add(interaction.guild_id)
        # try to apply backup
        try:
            if data["_backup_version"] == 1:
                problems, logs = await self.BackupLoaderV1().load_backup(interaction, data, arguments)
            else:
                await interaction.edit_original_response(await self.bot._(interaction, "s_backup.invalid_version"))
                self.backups_loading.remove(interaction.guild_id)
                return
        except Exception as err:  # pylint: disable=broad-except
            self.bot.dispatch("error", err, interaction)
            await interaction.edit_original_response(await self.bot._(interaction, "s_backup.err"))
            self.backups_loading.remove(interaction.guild_id)
            return
        # Formatting and sending logs
        logs = f"Found {sum(problems)} problems (including {problems[0]} permissions issues)\n\n" + "\n".join(
            logs)
        if len(logs) > 1950:
            # If too many logs, send in a file
            logs = logs.replace("`[O]`", "[O]").replace(
                "`[-]`", "[-]").replace("`[X]`", "[X]")
            finish_msg = await self.bot._(interaction, "s_backup.finished")
            try:
                await interaction.followup.send(finish_msg, file=discord.File(BytesIO(logs.encode()), filename="logs.txt"))
            except discord.errors.HTTPException:  # if channel was deleted, send in DM
                await interaction.user.send(finish_msg, file=discord.File(BytesIO(logs.encode()), filename="logs.txt"))
        else:
            # Else, we just edit the message with logs
            try:
                await interaction.followup.send(logs)
            except discord.errors.NotFound:  # if channel was deleted, send in DM
                await interaction.user.send(logs)
        self.backups_loading.remove(interaction.guild_id)

    @main_backup.command(name="create")
    @app_commands.checks.cooldown(1, 60)
    async def backup_create(self, interaction: discord.Interaction):
        """Make and send a backup of this server
        You will find there the configuration of your server, every general settings, the list of members with their roles, the list of categories and channels (with their permissions), emotes, and webhooks.
        Please note that audit logs, messages and invites are not used

..Example backup create

..Doc server.html#server-backup"""
        await interaction.response.defer()
        data = await self.create_backup(interaction)
        file = discord.File(BytesIO(data.encode()),
                            filename=f"backup-{interaction.guild_id}.json")
        await interaction.followup.send(await self.bot._(interaction, "s_backup.backup-done"), file=file)

    # --------

    async def create_backup(self, interaction: discord.Interaction) -> str:
        "Create a backup of the server and return it as a JSON string"
        async def get_channel_json(chan: discord.abc.GuildChannel) -> dict:
            chan_js = {"id": chan.id, "name": chan.name, "position": chan.position}
            if isinstance(chan, discord.TextChannel):
                chan_js["type"] = "TextChannel"
                chan_js["description"] = chan.topic
                chan_js["is_nsfw"] = chan.is_nsfw()
                chan_js["slowmode"] = chan.slowmode_delay
            elif isinstance(chan, discord.VoiceChannel):
                chan_js["type"] = "VoiceChannel"
            else:
                chan_js["type"] = str(type(chan))
            perms: list[dict[str, Any]] = []
            for iter_obj, iter_perm in chan.overwrites.items():
                temp2 = {"id": iter_obj.id}
                if isinstance(iter_obj, discord.Member):
                    temp2["type"] = "member"
                else:
                    temp2["type"] = "role"
                temp2["permissions"] = {}
                for x in iter(iter_perm):
                    if x[1] is not None:
                        temp2["permissions"][x[0]] = x[1]
                perms.append(temp2)
            chan_js["permissions_overwrites"] = perms
            return chan_js
        # ----
        g = interaction.guild
        back = {
            "_backup_version": 1,
            "name": g.name,
            "id": g.id,
            "owner": g.owner.id,
            "afk_timeout": g.afk_timeout,
            "icon": g.icon.url if g.icon else None,
            "verification_level": g.verification_level.value,
            "mfa_level": g.mfa_level,
            "explicit_content_filter": g.explicit_content_filter.value,
            "default_notifications": g.default_notifications.value,
            "created_at": int(g.created_at.timestamp()),
            "afk_channel": g.afk_channel.id if g.afk_channel is not None else None,
            "system_channel": g.system_channel.id if g.system_channel is not None else None
        }
        roles: list[dict[str, Any]] = []
        for x in g.roles:
            roles.append({
                "id": x.id,
                "name": x.name,
                "color": x.colour.value,
                "position": x.position,
                "hoist": x.hoist,
                "mentionable": x.mentionable,
                "permissions": x.permissions.value
            })
        back["roles"] = roles
        categ: list[dict[str, Any]] = []
        for category, channels in g.by_category():
            if category is None:
                temp = {"id": None}
            else:
                temp = {
                    "id": category.id,
                    "name": category.name,
                    "position": category.position,
                    "is_nsfw": category.is_nsfw()
                }
                perms: list[dict[str, Any]] = []
                for iter_obj, iter_perm in category.overwrites.items():
                    temp2 = {"id": iter_obj.id}
                    if isinstance(iter_obj, discord.Member):
                        temp2["type"] = "member"
                    else:
                        temp2["type"] = "role"
                    temp2["permissions"] = {}
                    for i, value in iter(iter_perm):
                        if value is not None:
                            temp2["permissions"][i] = value
                    perms.append(temp2)
                temp["permissions_overwrites"] = perms
            temp["channels"] = []
            for chan in channels:
                temp["channels"].append(await get_channel_json(chan))
            categ.append(temp)
        back["categories"] = categ
        back["emojis"] = {}
        for emoji in g.emojis:
            back["emojis"][emoji.name] = {
                "url": str(emoji.url),
                "roles": [x.id for x in emoji.roles]
            }
        try:
            banned = {}
            async for b in g.bans():
                banned[b.user.id] = b.reason
            back["banned_users"] = banned
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, interaction)
        try:
            webs = []
            for w in await g.webhooks():
                webs.append({
                    "channel": w.channel_id,
                    "name": w.name,
                    "avatar": w.display_avatar.url,
                    "url": w.url
                })
            back["webhooks"] = webs
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, interaction)
        back["members"] = []
        for memb in g.members:
            back["members"].append({
                "id": memb.id,
                "nickname": memb.nick,
                "bot": memb.bot,
                "roles": [x.id for x in memb.roles][1:]
            })
        return json.dumps(back, sort_keys=True, indent=4)

    # ----------

    class BackupLoaderV1:
        "Utility class to load backups from the v1 format"
        def __init__(self):
            pass

        async def url_to_byte(self, url: str) -> bytes | None:
            "Fetch an image from an URL and return it as bytes, or None if the image is not found"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status >= 200 and response.status < 300:
                        res = await response.read()
                    else:
                        res = None
            return res

        async def load_roles(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                             args: LoadArguments, roles_list: dict[int, discord.Role]):
            "Create and update roles based on the backup map"
            if not interaction.guild.me.guild_permissions.manage_roles:
                logs.append(f"  {symb[0]} Unable to create or update roles: missing permissions")
                problems[0] += 1
                return
            for role_data in sorted(data["roles"], key=lambda role: role["position"], reverse=True):
                action = "edit"
                try:
                    rolename = role_data["name"]
                    role = interaction.guild.get_role(role_data["id"])
                    if role is None:
                        potential_roles = [x for x in interaction.guild.roles if x.name == role_data["name"]]
                        if args.match_by_name and len(potential_roles) > 0:
                            role = potential_roles[0]
                        else:
                            action = "create"
                            try:
                                role = await interaction.guild.create_role(name=role_data["name"])
                            except discord.DiscordException:
                                continue
                    if role_data["name"] == "@everyone":
                        if role.permissions.value != role_data["permissions"]:
                            await role.edit(permissions=discord.Permissions(role_data["permissions"]))
                    else:
                        kwargs = {}
                        if role.name != role_data["name"]:
                            kwargs["name"] = role_data["name"]
                        if role.permissions.value != role_data["permissions"]:
                            kwargs["permissions"] = discord.Permissions(
                                role_data["permissions"])
                        if role.colour.value != role_data["color"]:
                            kwargs["colour"] = discord.Colour(
                                role_data["color"])
                        if role.hoist != role_data["hoist"]:
                            kwargs["hoist"] = role_data["hoist"]
                        if role.mentionable != role_data["mentionable"]:
                            kwargs["mentionable"] = role_data["mentionable"]
                        if len(kwargs.keys()) > 0:
                            await role.edit(**kwargs)
                            if action == "create":
                                logs.append(f"  {symb[0]} Role {rolename} created")
                            else:
                                logs.append(f"  {symb[0]} Role {rolename} set")
                        elif action == "create":
                            logs.append(f"  {symb[0]} Role {rolename} created")
                        else:
                            logs.append(f"  {symb[0]} No need to change role {rolename}")
                    roles_list[role_data["id"]] = role
                except discord.Forbidden:
                    if action == "create":
                        await role.delete()
                    logs.append(f"  {symb[0]} Unable to {action} role {rolename}: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(f"  {symb[0]} Unable to {action} role {rolename}: {err}")
                    problems[1] += 1
                else:
                    pass
            if args.delete_old_roles:
                for role in interaction.guild.roles:
                    if role in roles_list.values():
                        continue
                    try:
                        await role.delete()
                    except discord.errors.Forbidden:
                        logs.append(f"  {symb[0]} Unable to delete role {role.name}: missing permissions")
                        problems[0] += 1
                    except Exception as err:
                        if "404" not in str(err):
                            logs.append(f"  {symb[0]} Unable to delete role {role.name}: {err}")
                            problems[1] += 1
                    else:
                        logs.append(f"  {symb[0]} Role {role.name} deleted")
            del role
            for role_data in data["roles"]:
                role_data: dict[str, Any]
                role_id: int = role_data["id"]
                if role_data["position"] > 0 and role_id in roles_list and (role := roles_list.get(roles_list[role_id])):
                    new_pos = min(
                        max(interaction.guild.me.top_role.position-1, 1), role_data["position"])
                    if role.position == new_pos:
                        continue
                    try:
                        await role.edit(position=new_pos)
                    except (discord.HTTPException, discord.Forbidden) as err:
                        if isinstance(err, discord.errors.Forbidden) and hasattr(err, "status") and err.status in {403, 400}:
                            logs.append(
                                f"  {symb[0]} Unable to move role {role_data['name']} to position {new_pos}: missing permissions")
                            problems[0] += 1
                        else:
                            logs.append(f"  {symb[0]} Unable to move role {role_data['name']} to position {new_pos}: {err}")
                            problems[1] += 1

        async def load_categories(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                                  args: LoadArguments, channels_list: dict):
            "Create and update channel categories based on the backup map"
            if not interaction.guild.me.guild_permissions.manage_channels:
                logs.append(f"  {symb[0]} Unable to create or update categories: missing permissions")
                problems[0] += 1
            else:
                for categ in data["categories"]:
                    action = "edit"
                    try:
                        if ("id" in categ.keys() and categ["id"] is None):
                            continue
                        categname = categ["name"]
                        c = interaction.guild.get_channel(categ["id"])
                        if c is None:
                            potential_categories = [x for x in interaction.guild.categories if x.name == categ["name"]]
                            if args.match_by_name and len(potential_categories) > 0:
                                c = potential_categories[0]
                            else:
                                action = "create"
                                c = await interaction.guild.create_category(name=categ["name"])
                        kwargs = {}
                        if c.name != categ["name"]:
                            kwargs["name"] = categ["name"]
                        if c.nsfw != categ["is_nsfw"]:
                            kwargs["nsfw"] = categ["is_nsfw"]
                        if c.position != categ["position"]:
                            kwargs["position"] = categ["position"]
                        if len(kwargs.keys()) > 0:
                            await c.edit(**kwargs)
                            if action == "create":
                                logs.append(f"  {symb[2]} Category {categname} created")
                            else:
                                logs.append(f"  {symb[2]} Category {categname} set")
                        elif action == "create":
                            logs.append(f"  {symb[2]} Category {categname} created")
                        else:
                            logs.append(f"  {symb[1]} No need to change category {categname}")
                        channels_list[categ["id"]] = c
                    except discord.errors.Forbidden:
                        if action == "create":
                            await c.delete()
                        logs.append(f"  {symb[0]} Unable to {action} category {categname}: missing permissions")
                        problems[0] += 1
                    except Exception as err:
                        logs.append(f"  {symb[0]} Unable to {action} category {categname}: {err}")
                    else:
                        pass
                if args.delete_old_channels:
                    for categ in interaction.guild.categories:
                        if categ in channels_list.values():
                            continue
                        try:
                            await categ.delete()
                        except discord.errors.Forbidden:
                            logs.append(f"  {symb[0]} Unable to delete category {categ.name}: missing permissions")
                            problems[0] += 1
                        except Exception as err:
                            logs.append(f"  {symb[0]} Unable to delete category {categ.name}: {err}")
                            problems[1] += 1
                        else:
                            logs.append(f"  {symb[2]} Category {categ.name} deleted")

        async def load_channels(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                                args: LoadArguments, channels_list: dict):
            "Create and update channels based on the backup map"
            if not interaction.guild.me.guild_permissions.manage_channels:
                logs.append(f"  {symb[0]} Unable to create or update channels: missing permissions")
                problems[0] += 1
            else:
                _channels_to_make = [
                    (ch, category["id"] if "id" in category.keys() else None)
                    for category in data["categories"]
                    for ch in category["channels"]
                ]
                for chan, categ in _channels_to_make:
                    action = "edit"
                    try:
                        channame = chan["name"]
                        c = interaction.guild.get_channel(chan["id"])
                        if c is None:
                            potential_channels = [
                                x
                                for x in interaction.guild.text_channels + interaction.guild.voice_channels
                                if x.name == chan["name"]
                            ]
                            if args.match_by_name and len(potential_channels) > 0:
                                c = potential_channels[0]
                            else:
                                action = "create"
                                _categ = None if categ is None else channels_list[categ]
                                if chan["type"] == "TextChannel":
                                    c = await interaction.guild.create_text_channel(name=chan["name"], category=_categ)
                                else:
                                    c = await interaction.guild.create_voice_channel(name=chan["name"], category=_categ)
                        kwargs = {}
                        if c.name != chan["name"]:
                            kwargs["name"] = chan["name"]
                        if "is_nsfw" in chan.keys() and c.nsfw != chan["is_nsfw"]:
                            kwargs["nsfw"] = chan["is_nsfw"]
                        if c.position != chan["position"]:
                            kwargs["position"] = chan["position"]
                        if "description" in chan.keys() and c.topic != chan["description"]:
                            kwargs["topic"] = chan["description"]
                        if "slowmode" in chan.keys() and c.slowmode_delay != chan["slowmode"]:
                            kwargs["slowmode_delay"] = chan["slowmode"]
                        if len(kwargs.keys()) > 0:
                            await c.edit(**kwargs)
                            if action == "create":
                                logs.append(f"  {symb[2]} Channel {channame} created")
                            else:
                                logs.append(f"  {symb[2]} Channel {channame} set")
                        elif action == "create":
                            logs.append(f"  {symb[2]} Channel {channame} created")
                        else:
                            logs.append(f"  {symb[1]} No need to change channel {channame}")
                        channels_list[chan["id"]] = c
                    except discord.errors.Forbidden:
                        if action == "create":
                            await c.delete()
                        logs.append(f"  {symb[0]} Unable to {action} channel {channame}: missing permissions")
                        problems[0] += 1
                    except Exception as err:
                        logs.append(f"  {symb[0]} Unable to {action} channel {channame}: {err}")
                        problems[1] += 1
                    else:
                        pass
                if args.delete_old_channels:
                    for channel in interaction.guild.text_channels + interaction.guild.voice_channels:
                        if channel in channels_list.values():
                            continue
                        try:
                            await channel.delete()
                        except discord.errors.Forbidden:
                            logs.append(f"  {symb[0]} Unable to delete channel {channel.name}: missing permissions")
                            problems[0] += 1
                        except Exception as err:
                            logs.append(f"  {symb[0]} Unable to delete channel {channel.name}: {err}")
                            problems[1] += 1
                        else:
                            logs.append(f"  {symb[2]} Channel {channel.name} deleted")

        async def apply_perm(self, item: discord.abc.GuildChannel, perms: list, roles_list: dict):
            "Apply a set of permissions to a guild channel"
            for perm in perms:
                target = None
                if perm["type"] == "role" and perm["id"] in roles_list.keys():
                    target = roles_list[perm["id"]]
                elif perm["type"] == "user":
                    target = item.guild.get_member(perm["id"])
                if target is None:
                    continue
                new_perms = discord.PermissionOverwrite(**perm["permissions"])
                if item.overwrites_for(target) == new_perms:
                    continue
                try:
                    await item.set_permissions(target, overwrite=new_perms)
                except discord.Forbidden:
                    pass

        async def load_perms(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                             _args: LoadArguments, roles_list: dict, channels_list: dict):
            "Sync category and channel permissions based on the backup map"
            if not interaction.guild.me.guild_permissions.manage_roles:
                logs.append(f"  {symb[0]} Unable to update permissions: missing permissions")
                problems[0] += 1
            # categories
            for categ in data["categories"]:
                if "id" in categ.keys() and categ["id"] is not None and "permissions_overwrites" in categ.keys():
                    try:
                        real_category = channels_list[categ["id"]]
                        await self.apply_perm(real_category, categ["permissions_overwrites"], roles_list)
                    except Exception as err:
                        logs.append(f"  {symb[0]} Unable to update permissions of category {categ['name']}: {err}")
                        problems[1] += 1
                    else:
                        logs.append(f"  {symb[2]} Permissions of category {categ['name']} set")
                if "channels" not in categ.keys():
                    continue
                for chan in categ["channels"]:
                    try:
                        if (chan["id"] not in channels_list.keys()) or ("permissions_overwrites" not in chan.keys()):
                            continue
                        real_channel = channels_list[chan["id"]]
                        await self.apply_perm(real_channel, chan["permissions_overwrites"], roles_list)
                    except discord.errors.Forbidden:
                        logs.append(f"     {symb[0]} Unable to update permissions of channel {chan['name']}: missing permisions")
                        problems[0] += 1
                    except Exception as err:
                        logs.append(f"     {symb[0]} Unable to update permissions of channel {chan['name']}: {err}")
                        problems[1] += 1
                    else:
                        logs.append(f"     {symb[2]} Permissions of channel {chan['name']} set")

        async def load_members(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                               _args: LoadArguments, roles_list: dict[int, discord.Role]):
            "Sync member nicknames and roles based on the backup map"
            if "members" not in data.keys():
                return
            change_nicks = True
            if not interaction.guild.me.guild_permissions.manage_nicknames:
                change_nicks = False
                logs.append(f"  {symb[0]} Unable to change nicknames: missing permissions")
                problems[0] += 1
            change_roles = True
            if not interaction.guild.me.guild_permissions.manage_roles:
                change_roles = False
                logs.append(f"  {symb[0]} Unable to change roles: missing permissions")
                problems[0] += 1
            for memb in data["members"]:
                member = interaction.guild.get_member(memb["id"])
                if member is None:
                    continue
                try:
                    edition: list[str] = []
                    if member.nick != memb["nickname"] and change_nicks and (
                        member.top_role.position < interaction.guild.me.top_role.position and interaction.guild.owner != member
                        ):
                        await member.edit(nick=memb["nickname"])
                        edition.append("nickname")
                    roles = []
                    for r in memb["roles"]:
                        try:
                            _role = roles_list[r]
                            if 0 < _role.position < interaction.guild.me.top_role.position:
                                roles.append(_role)
                        except KeyError:
                            pass
                    if roles != member.roles and change_roles and len(roles) > 0:
                        try:
                            await member.add_roles(*roles)
                        except discord.errors.Forbidden:
                            logs.append(f"  {symb[0]} Unable to give roles to user {member}: missing permissions")
                            problems[0] += 1
                        except Exception as err:
                            logs.append(f"  {symb[0]} Unable to give roles to user {member}: {err}")
                            problems[1] += 1
                        else:
                            edition.append("roles")
                except Exception as err:
                    logs.append(f"  {symb[0]} Unable to set user {member}: {err}")
                    problems[1] += 1
                else:
                    if len(edition) > 0:
                        logs.append(f"  {symb[2]} Updated {'and'.join(edition)} for user {member}")

        async def load_emojis(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                              args: LoadArguments, roles_list: dict):
            "Sync guild emojis based on the backup map"
            if not interaction.guild.me.guild_permissions.manage_expressions:
                logs.append(
                    f"  {symb[0]} Unable to create or update emojis: missing permissions")
                problems[0] += 1
            else:
                for emojiname, emojidata in data["emojis"].items():
                    try:
                        if len([x for x in interaction.guild.emojis if x.name == emojiname]) > 0:
                            logs.append(f"  {symb[1]} Emoji {emojiname} already exists")
                            continue
                        try:
                            icon = await self.url_to_byte(emojidata["url"])
                        except aiohttp.ClientError:
                            icon = None
                        if icon is None:
                            logs.append(
                                f"  {symb[0]} Unable to create emoji {emojiname}:"\
                                " the image has probably been deleted from Discord cache")
                            continue
                        roles = list()
                        for r in emojidata["roles"]:
                            try:
                                _role = roles_list[r]
                                if 0 < _role.position < interaction.guild.me.top_role.position:
                                    roles.append(_role)
                            except KeyError:
                                pass
                        if len(roles) == 0:
                            roles = None
                        await interaction.guild.create_custom_emoji(name=emojiname, image=icon, roles=roles)
                    except discord.errors.Forbidden:
                        logs.append(f"  {symb[0]} Unable to create emoji {emojiname}: missing permissions")
                        problems[0] += 1
                    except Exception as err:
                        logs.append(f"  {symb[0]} Unable to create emoji {emojiname}: {err}")
                        problems[1] += 1
                    else:
                        logs.append(f"  {symb[2]} Emoji {emojiname} created")
                if args.delete_old_emojis:
                    for emoji in interaction.guild.emojis:
                        if emoji.name in data["emojis"].keys():
                            continue
                        try:
                            await emoji.delete()
                        except discord.errors.Forbidden:
                            logs.append(f"  {symb[0]} Unable to delete emoji {emoji.name}: missing permissions")
                            problems[0] += 1
                        except Exception as err:
                            if "404" not in str(err):
                                logs.append(f"  {symb[0]} Unable to delete emoji {emoji.name}: {err}")
                                problems[1] += 1
                        else:
                            logs.append(f"  {symb[2]} Emoji {emoji.name} deleted")

        async def load_webhooks(self, interaction: discord.Interaction, problems: list, logs: list, symb: list, data: dict,
                                args: LoadArguments, channels_list: dict):
            "Sync webhooks based on the backup map"
            if not interaction.guild.me.guild_permissions.manage_webhooks:
                logs.append(f"  {symb[0]} Unable to create or update webhooks: missing permissions")
                problems[0] += 1
            else:
                created_webhooks_urls: list[str] = []
                for webhook in data["webhooks"]:
                    try:
                        webhookname = webhook["name"]
                        if len([x for x in await interaction.guild.webhooks() if x.url == webhook["url"]]) > 0:
                            logs.append(f"  {symb[1]} Webhook {webhookname} already exists")
                            continue
                        try:
                            icon = await self.url_to_byte(webhook["avatar"])
                        except aiohttp.ClientError:
                            logs.append(f"  {symb[0]} Unable to get avatar of wbehook {webhookname}:"\
                                        " the image has probably been deleted from Discord cache")
                            icon = None
                        try:
                            real_channel = channels_list[webhook["channel"]]
                        except KeyError:
                            logs.append(f"  {symb[0]} Unable to create wbehook {webhookname}: unable to get the text channel")
                            continue
                        await real_channel.create_webhook(name=webhook["name"], avatar=icon)
                    except discord.errors.Forbidden:
                        logs.append(f"  {symb[0]} Unable to create webhook {webhookname}: missing permissions")
                        problems[0] += 1
                    except Exception as err:
                        logs.append(f"  {symb[0]} Unable to create webhook {webhookname}: {err}")
                        problems[1] += 1
                    else:
                        logs.append(f"  {symb[2]} Webhook {webhookname} created")
                        created_webhooks_urls.append(webhook["url"])
                if args.delete_old_webhooks:
                    for web in await interaction.guild.webhooks():
                        if web.url in created_webhooks_urls:
                            continue
                        try:
                            await web.delete()
                        except discord.errors.Forbidden:
                            logs.append(f"  {symb[0]} Unable to delete webhook {web.name}: missing permissions")
                            problems[0] += 1
                        except Exception as err:
                            if "404" not in str(err):
                                logs.append(f"  {symb[0]} Unable to delete webhook {web.name}: {err}")
                                problems[1] += 1
                        else:
                            logs.append(f"  {symb[2]} Webhook {web.name} deleted")

        async def load_backup(self, interaction: discord.Interaction, data: dict, args: LoadArguments) -> tuple[list, list]:
            "Load a backup in a server, for backups version 1"
            if data.pop("_backup_version", None) != 1:
                return ([0, 1], ["Unknown backup version"])
            symb = ["`[X]`", "`[-]`", "`[O]`"]
            problems = [0, 0]
            logs: list[str] = []
            # afk_timeout
            if interaction.guild.afk_timeout == data["afk_timeout"]:
                logs.append(f"{symb[1]} No need to change AFK timeout duration")
            else:
                try:
                    await interaction.guild.edit(afk_timeout=data["afk_timeout"])
                except discord.errors.Forbidden:
                    logs.append(f"{symb[0]} Unable to set AFK timeout duration: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(f"{symb[0]} Unable to set AFK timeout duration: {err}")
                    problems[1] += 1
                else:
                    logs.append(f"{symb[2]} AFK timeout duration set to {data['afk_timeout']}s")
            # banned_users
            if "banned_users" in data:
                try:
                    banned_users = [x.user.id async for x in interaction.guild.bans(limit=None)]
                    users_to_ban = [
                        x
                        for x in data["banned_users"].items()
                        if x[0] not in banned_users
                    ]
                    if len(users_to_ban) == 0:
                        logs.append(symb[1]+" No user to ban")
                    else:
                        for x in users_to_ban:
                            user, reason = x
                            try:
                                await interaction.guild.ban(discord.Object(user), reason=reason, delete_message_days=0)
                            except discord.errors.NotFound:
                                pass
                        logs.append(f"{symb[2]} Banned users updated ({len(data['banned_users'])} users)")
                except discord.errors.Forbidden:
                    logs.append(f"{symb[0]} Unable to ban users: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(f"{symb[0]} Unable to ban users: {err}")
                    problems[1] += 1
            # default_notifications
            if interaction.guild.default_notifications.value == data["default_notifications"]:
                logs.append(f"{symb[1]} No need to change default notifications")
            else:
                try:
                    default_notif = discord.NotificationLevel(
                        data["default_notifications"])
                    await interaction.guild.edit(default_notifications=default_notif)
                except discord.errors.Forbidden:
                    logs.append(f"{symb[0]} Unable to set default notifications: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(f"{symb[0]} Unable to set default notifications: {err}")
                    problems[1] += 1
                else:
                    logs.append(f"{symb[2]} Default notifications set to "+default_notif.name)
            # explicit_content_filter
            if interaction.guild.explicit_content_filter.value == data["explicit_content_filter"]:
                logs.append(symb[1]+" No need to change content filter")
            else:
                try:
                    content_filter = discord.ContentFilter(
                        data["explicit_content_filter"])
                    await interaction.guild.edit(explicit_content_filter=content_filter)
                except discord.errors.Forbidden:
                    logs.append(f"{symb[0]} Unable to set content filter: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(f"{symb[0]} Unable to set content filter: {err}")
                    problems[1] += 1
                else:
                    logs.append(f"{symb[2]} Explicit content filter set to "+content_filter.name)
            # icon
            try:
                icon = None if data["icon"] is None else await self.url_to_byte(data["icon"])
            except aiohttp.ClientError:
                icon = None
            if icon is not None or data["icon"] is None:
                try:
                    await interaction.guild.edit(icon=icon)
                except discord.errors.Forbidden:
                    logs.append(
                        symb[0]+" Unable to set server icon: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(symb[0]+f" Unable to set server icon: {err}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Server icon updated")
            elif data["icon"] is None:
                logs.append(symb[2]+" Server icon deleted")
            else:
                logs.append(
                    symb[0]+" Unable to set server icon: the image has probably been deleted from Discord cache")
                problems[1] += 1
            # mfa_level
            if interaction.guild.mfa_level != data["mfa_level"]:
                logs.append(
                    symb[0]+" Unable to change 2FA requirement: only owner can do that")
                problems[0] += 1
            else:
                logs.append(symb[1]+" No need to change 2FA requirement")
                problems[1] += 1
            # name
            if interaction.guild.name == data["name"]:
                logs.append(symb[1]+" No need to change server name")
            else:
                try:
                    await interaction.guild.edit(name=data["name"])
                except discord.errors.Forbidden:
                    logs.append(
                        symb[0]+" Unable to set server name: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(symb[0]+f" Unable to set server name: {err}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Server name set to "+data["name"])
            # verification_level
            if interaction.guild.verification_level.value == data["verification_level"]:
                logs.append(symb[1]+" No need to change verification level")
            else:
                try:
                    verif_level = discord.VerificationLevel(
                        data["verification_level"])
                    await interaction.guild.edit(verification_level=verif_level)
                except discord.errors.Forbidden:
                    logs.append(
                        symb[0]+" Unable to set verification level: missing permissions")
                    problems[0] += 1
                except Exception as err:
                    logs.append(
                        symb[0]+f" Unable to set verification level: {err}")
                    problems[1] += 1
                else:
                    logs.append(
                        symb[2]+" Verification level set to "+verif_level.name)
            # roles
            logs.append(" - Creating roles")
            roles_list: dict[int, discord.Role] = {}
            await self.load_roles(interaction, problems, logs, symb, data, args, roles_list)
            # categories
            logs.append(" - Creating categories")
            channels_list = {}
            await self.load_categories(interaction, problems, logs, symb, data, args, channels_list)
            # channels
            logs.append(" - Creating channels")
            await self.load_channels(interaction, problems, logs, symb, data, args, channels_list)
            # channels permissions
            logs.append(" - Updating categories and channels permissions")
            await self.load_perms(interaction, problems, logs, symb, data, args, roles_list, channels_list)
            # members
            logs.append(" - Updating members roles and nick")
            await self.load_members(interaction, problems, logs, symb, data, args, roles_list)
            # emojis
            logs.append(" - Creating emojis")
            await self.load_emojis(interaction, problems, logs, symb, data, args, roles_list)
            # webhooks
            if "webhooks" in data:
                logs.append(" - Creating webhooks")
                await self.load_webhooks(interaction, problems, logs, symb, data, args, channels_list)

            return problems, logs


async def setup(bot):
    await bot.add_cog(Backups(bot))
