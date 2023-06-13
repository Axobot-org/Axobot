from libs.bot_classes import Axobot, MyContext
import discord
import importlib
import aiohttp
import json
import typing
from discord.ext import commands
from io import BytesIO

from fcts import checks
importlib.reload(checks)


class Backups(commands.Cog):
    """This cog is used to make and apply backups of a Discord server"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "s_backups"

    @commands.group(name='backup')
    @commands.guild_only()
    @commands.cooldown(2,120, commands.BucketType.guild)
    @commands.check(checks.has_admin)
    async def main_backup(self,ctx:MyContext):
        """Make and apply backups of your server

        ..Doc server.html#server-backup"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)


    @main_backup.command(name="load")
    async def backup_load(self, ctx: MyContext, *arguments: str):
        """Load a backup created with `backup create`
Arguments are:
    - reset: delete everything from the current server
    - delete_old_channels: delete every current channel/category
    - delete_old_roles: delete every current role
    - delete_old_emojis: delete every current emoji
    - delete_old_webhooks: well, same but with webhooks

..Example backup load

..Example backup load delete_old_roles delete_old_emojis

..Example backup load reset

..Doc server.html#server-backup"""
        # Analyzing arguments
        valid_args = ["reset","delete_old_channels","delete_old_roles","delete_old_emojis","delete_old_webhooks"]
        arguments = {a.lower() for a in arguments if a.lower() in valid_args}
        if "reset" in arguments:
            arguments.update(set(['delete_old_channels','delete_old_roles','delete_old_emojis','delete_old_webhooks']))
        # Loading backup from file
        try:
            data = json.loads(await ctx.message.attachments[0].read())
        except (json.decoder.JSONDecodeError, IndexError):
            await ctx.send(await self.bot._(ctx.guild, "s_backup.invalid_file"))
            return
        # Applying backup
        msg = await ctx.send(await self.bot._(ctx.guild, "s_backup.loading"))
        try:
            if data["_backup_version"] == 1:
                problems, logs = await self.BackupLoaderV1().load_backup(ctx, data, arguments)
            else:
                await ctx.send(await self.bot._(ctx.guild, "s_backup.invalid_version"))
                return
        except Exception as err: # pylint: disable=broad-except
            await ctx.bot.dispatch("error", err, ctx)
            await ctx.send(await self.bot._(ctx.guild, "s_backup.err"))
            return
        # Formatting and sending logs
        logs = "Found {} problems (including {} permissions issues)\n\n".format(sum(problems),problems[0]) + "\n".join(logs)
        if len(logs) > 1950:
            # If too many logs, send in a file
            logs = logs.replace("`[O]`","[O]").replace("`[-]`","[-]").replace("`[X]`","[X]")
            finish_msg = await self.bot._(ctx.guild, "s_backup.finished")
            try:
                await ctx.send(content=finish_msg,file=discord.File(BytesIO(logs.encode()),filename="logs.txt"))
            except discord.errors.NotFound: # if channel was deleted, send in DM
                await ctx.author.send(content=finish_msg,file=discord.File(BytesIO(logs.encode()),filename="logs.txt"))
            try:
                await msg.delete()
            except (discord.NotFound, discord.Forbidden): # can happens because deleted channel
                pass
        else:
            # Else, we just edit the message with logs
            try:
                await msg.edit(content=logs)
            except discord.errors.NotFound: # if channel was deleted, send in DM
                await ctx.author.send(logs)

    @main_backup.command(name="create")
    async def backup_create(self,ctx:MyContext):
        """Make and send a backup of this server
        You will find there the configuration of your server, every general settings, the list of members with their roles, the list of categories and channels (with their permissions), emotes, and webhooks.
        Please note that audit logs, messages and invites are not used

..Example backup create

..Doc server.html#server-backup"""
        try:
            data = await self.create_backup(ctx)
            file = discord.File(BytesIO(data.encode()), filename=f"backup-{ctx.guild.id}.json")
            await ctx.send(await self.bot._(ctx.guild.id, "s_backup.backup-done"), file=file)
        except Exception as e:
            await ctx.bot.get_cog('Errors').on_command_error(ctx,e)

    # --------

    async def create_backup(self,ctx:MyContext) -> str:
        async def get_channel_json(chan) -> dict:
            chan_js = {'id':chan.id,'name':chan.name,'position':chan.position}
            if isinstance(chan,discord.TextChannel):
                chan_js['type'] = 'TextChannel'
                chan_js['description'] = chan.topic
                chan_js['is_nsfw'] = chan.is_nsfw()
                chan_js['slowmode'] = chan.slowmode_delay
            elif isinstance(chan,discord.VoiceChannel):
                chan_js['type'] = 'VoiceChannel'
            else:
                chan_js['type'] = str(type(chan))
            perms = list()
            for iter_obj,iter_perm in chan.overwrites.items():
                temp2 = {'id':iter_obj.id}
                if isinstance(iter_obj,discord.Member):
                    temp2['type'] = 'member'
                else:
                    temp2['type'] = 'role'
                temp2['permissions'] = {}
                for x in iter(iter_perm):
                    if x[1] is not None:
                        temp2['permissions'][x[0]] = x[1]
                perms.append(temp2)
            chan_js['permissions_overwrites'] = perms
            return chan_js
        # ----
        g = ctx.guild
        back = {'_backup_version': 1,
            'name': g.name,
            'id': g.id,
            'owner': g.owner.id,
            'afk_timeout': g.afk_timeout,
            'icon': None if g.icon else g.icon.url,
            'verification_level': g.verification_level.value,
            'mfa_level': g.mfa_level,
            'explicit_content_filter': g.explicit_content_filter.value,
            'default_notifications': g.default_notifications.value,
            'created_at': int(g.created_at.timestamp()),
            'afk_channel': g.afk_channel.id if g.afk_channel is not None else None,
            'system_channel': g.system_channel.id if g.system_channel is not None else None}
        roles = list()
        for x in g.roles:
            roles.append({'id':x.id,'name':x.name,'color':x.colour.value,'position':x.position,'hoist':x.hoist,'mentionable':x.mentionable,'permissions':x.permissions.value})
        back['roles'] = roles
        categ = list()
        for category, channels in g.by_category():
            if category is None:
                temp = {'id': None}
            else:
                temp = {
                    'id': category.id,
                    'name': category.name,
                    'position': category.position,
                    'is_nsfw': category.is_nsfw()
                }
                perms = list()
                for iter_obj, iter_perm in category.overwrites.items():
                    temp2 = {'id':iter_obj.id}
                    if isinstance(iter_obj,discord.Member):
                        temp2['type'] = 'member'
                    else:
                        temp2['type'] = 'role'
                    temp2['permissions'] = {}
                    for i, value in iter(iter_perm):
                        if value is not None:
                            temp2['permissions'][i] = value
                    perms.append(temp2)
                temp['permissions_overwrites'] = perms
            temp['channels'] = list()
            for chan in channels:
                temp['channels'].append(await get_channel_json(chan))
            categ.append(temp)
        back['categories'] = categ
        back['emojis'] = {}
        for err in g.emojis:
            back['emojis'][err.name] = {"url": str(err.url), "roles": [x.id for x in err.roles]}
        try:
            banned = {}
            async for b in g.bans():
                banned[b.user.id] = b.reason
            back['banned_users'] = banned
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, ctx)
        try:
            webs = []
            for w in await g.webhooks():
                webs.append({
                    'channel': w.channel_id,
                    'name': w.name,
                    'avatar': w.display_avatar.url,
                    'url': w.url
                })
            back['webhooks'] = webs
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, ctx)
        back['members'] = []
        for memb in g.members:
            back['members'].append({'id': memb.id,
                'nickname': memb.nick,
                'bot': memb.bot,
                'roles': [x.id for x in memb.roles][1:] })
        return json.dumps(back, sort_keys=True, indent=4)

    # ----------

    class BackupLoaderV1:
        def __init__(self):
            pass

        async def urlToByte(self, url:str) -> typing.Optional[bytes]:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status>=200 and response.status<300:
                        res = await response.read()
                    else:
                        res = None
            return res

        async def load_roles(self, ctx:MyContext, problems: list, logs:list, symb:list, data:dict, args:tuple, roles_list:dict):
            "Create and update roles based on the backup map"
            if not ctx.guild.me.guild_permissions.manage_roles:
                logs.append(f"  {symb[0]} Unable to create or update roles: missing permissions")
                problems[0] += 1
                return
            for role_data in sorted(data["roles"], key=lambda role: role['position'], reverse=True):
                action = "edit"
                try:
                    rolename = role_data["name"]
                    role = ctx.guild.get_role(role_data["id"])
                    if role is None:
                        potential_roles = [x for x in ctx.guild.roles if x.name == role_data["name"]]
                        if len(potential_roles) == 0:
                            action = "create"
                            try:
                                role = await ctx.guild.create_role(name=role_data["name"])
                            except discord.DiscordException:
                                continue
                        else:
                            role = potential_roles[0]
                    if role_data["name"] == "@everyone":
                        if role.permissions.value != role_data["permissions"]:
                            await role.edit(permissions = discord.Permissions(role_data["permissions"]))
                    else:
                        kwargs = {}
                        if role.name != role_data["name"]:
                            kwargs["name"] = role_data["name"]
                        if role.permissions.value != role_data["permissions"]:
                            kwargs["permissions"] = discord.Permissions(role_data["permissions"])
                        if role.colour.value != role_data["color"]:
                            kwargs["colour"] = discord.Colour(role_data["color"])
                        if role.hoist != role_data["hoist"]:
                            kwargs["hoist"] = role_data["hoist"]
                        if role.mentionable != role_data["mentionable"]:
                            kwargs["mentionable"] = role_data["mentionable"]
                        if len(kwargs.keys()) > 0:
                            await role.edit(**kwargs)
                            if action == "create":
                                logs.append(f"  {symb[0]} Role {rolename} created")
                            else:
                                logs.append(f"  {symb[0]} Role {rolename} set".format(rolename))
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
            if "delete_old_roles" in args:
                for role_data in ctx.guild.roles:
                    if role_data in roles_list.values():
                        continue
                    try:
                        await role_data.delete()
                    except discord.errors.Forbidden:
                        logs.append(f"  {symb[0]} Unable to delete role {role_data.name}: missing permissions")
                        problems[0] += 1
                    except Exception as err:
                        if "404" not in str(err):
                            logs.append(f"  {symb[0]} Unable to delete role {role_data.name}: {err}")
                            problems[1] += 1
                    else:
                        logs.append(f"  {symb[0]} Role {role_data.name} deleted")
            del role, role_data
            for role_data in data["roles"]:
                role_data: dict[str, typing.Any]
                if role_data["position"] > 0 and (role := roles_list.get(roles_list[role_data["id"]])):
                    new_pos = min(max(ctx.guild.me.top_role.position-1,1), role_data["position"])
                    if role.position == new_pos:
                        continue
                    try:
                        await role.edit(position=new_pos)
                    except (discord.HTTPException, discord.Forbidden) as err:
                        if isinstance(err, discord.errors.Forbidden) and hasattr(err, "status") and err.status in {403, 400}:
                            logs.append(f"  {symb[0]} Unable to move role {role_data['name']} to position {new_pos}: missing permissions")
                            problems[0] += 1
                        else:
                            logs.append(f"  {symb[0]} Unable to move role {role_data['name']} to position {new_pos}: {err}")
                            problems[1] += 1

        async def load_categories(self, ctx:MyContext, problems: list, logs:list, symb:list, data:dict, args:tuple, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_channels:
                logs.append("  "+symb[0]+" Unable to create or update categories: missing permissions")
                problems[0] += 1
            else:
                for categ in data["categories"]:
                    action = "edit"
                    try:
                        if ("id" in categ.keys() and categ["id"] is None):
                            continue
                        # categname = categ["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        categname = categ["name"]
                        c = ctx.guild.get_channel(categ["id"])
                        if c is None:
                            c = [x for x in ctx.guild.categories if x.name == categ["name"]]
                            if len(c) == 0:
                                action = "create"
                                c = await ctx.guild.create_category(name=categ["name"])
                            else:
                                c = c[0]
                        kwargs = {}
                        if c.name != categ["name"]:
                            kwargs["name"] = categ["name"]
                        if c.nsfw != categ["is_nsfw"]:
                            kwargs["nsfw"] = categ["is_nsfw"]
                        if c.position != categ["position"]:
                            kwargs["position"] = categ["position"]
                        if len(kwargs.keys()) > 0:
                            await c.edit(**kwargs)
                            if action=="create":
                                logs.append("  "+symb[2]+" Category {} created".format(categname))
                            else:
                                logs.append("  "+symb[2]+" Category {} set".format(categname))
                        elif action=="create":
                                logs.append("  "+symb[2]+" Category {} created".format(categname))
                        else:
                            logs.append("  "+symb[1]+" No need to change category {}".format(categname))
                        channels_list[categ["id"]] = c
                    except discord.errors.Forbidden:
                        if action == "create":
                            await c.delete()
                        logs.append("  "+symb[0]+" Unable to {} category {}: missing permissions".format(action,categname))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to {} category {}: {}".format(action,categname,e))
                    else:
                        pass
                if "delete_old_channels" in args:
                    for categ in ctx.guild.categories:
                        if categ in channels_list.values():
                            continue
                        try:
                            await categ.delete()
                        except discord.errors.Forbidden:
                            logs.append("  "+symb[0]+" Unable to delete category {}: missing permissions".format(categ.name))
                            problems[0] += 1
                        except Exception as e:
                            logs.append("  "+symb[0]+" Unable to delete category {}: {}".format(categ.name,e))
                            problems[1] += 1
                        else:
                            logs.append("  "+symb[2]+" Category {} deleted".format(categ.name))

        async def load_channels(self, ctx:MyContext, problems:list, logs:list, symb:list, data:dict, args:tuple, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_channels:
                logs.append("  "+symb[0]+" Unable to create or update channels: missing permissions")
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
                        # channame = chan["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        channame = chan["name"]
                        c = ctx.guild.get_channel(chan["id"])
                        if c is None:
                            c = [x for x in ctx.guild.text_channels+ctx.guild.voice_channels if x.name == chan["name"]]
                            if len(c) == 0:
                                action = "create"
                                _categ = None if categ is None else channels_list[categ]
                                if chan["type"]=="TextChannel":
                                    c = await ctx.guild.create_text_channel(name=chan["name"],category=_categ)
                                else:
                                    c = await ctx.guild.create_voice_channel(name=chan["name"],category=_categ)
                            else:
                                c = c[0]
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
                            if action=="create":
                                logs.append("  "+symb[2]+" Channel {} created".format(channame))
                            else:
                                logs.append("  "+symb[2]+" Channel {} set".format(channame))
                        elif action=="create":
                                logs.append("  "+symb[2]+" Channel {} created".format(channame))
                        else:
                            logs.append("  "+symb[1]+" No need to change channel {}".format(channame))
                        channels_list[chan["id"]] = c
                    except discord.errors.Forbidden:
                        if action == "create":
                            await c.delete()
                        logs.append("  "+symb[0]+" Unable to {} channel {}: missing permissions".format(action,channame))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to {} channel {}: {}".format(action,channame,e))
                        problems[1] += 1
                    else:
                        pass
                if "delete_old_channels" in args:
                    for channel in ctx.guild.text_channels+ctx.guild.voice_channels:
                        if channel in channels_list.values():
                            continue
                        try:
                            await channel.delete()
                        except discord.errors.Forbidden:
                            logs.append("  "+symb[0]+" Unable to delete channel {}: missing permissions".format(channel.name))
                            problems[0] += 1
                        except Exception as e:
                            logs.append("  "+symb[0]+" Unable to delete channel {}: {}".format(channel.name,e))
                            problems[1] += 1
                        else:
                            logs.append("  "+symb[2]+" Channel {} deleted".format(channel.name))

        async def apply_perm(self, item:discord.abc.GuildChannel, perms:list, roles_list:dict):
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
                    await item.set_permissions(target,overwrite=new_perms)
                except discord.Forbidden:
                    pass

        async def load_perms(self, ctx:MyContext, problems:list, logs:list, symb:list, data:dict, args:tuple, roles_list:dict, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_roles:
                logs.append("  "+symb[0]+" Unable to update permissions: missing permissions")
                problems[0] += 1
            # categories
            for categ in data["categories"]:
                if "id" in categ.keys() and categ["id"] is not None and "permissions_overwrites" in categ.keys():
                    try:
                        real_category = channels_list[categ["id"]]
                        await self.apply_perm(real_category, categ["permissions_overwrites"], roles_list)
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to update permissions of category {}: {}".format(categ["name"],e))
                        problems[1] += 1
                    else:
                        logs.append("  "+symb[2]+" Permissions of category {} set".format(categ["name"]))
                if "channels" not in categ.keys():
                    continue
                for chan in categ["channels"]:
                    try:
                        if (chan["id"] not in channels_list.keys()) or ("permissions_overwrites" not in chan.keys()):
                            continue
                        real_channel = channels_list[chan["id"]]
                        await self.apply_perm(real_channel, chan["permissions_overwrites"], roles_list)
                    except discord.errors.Forbidden:
                        logs.append("     "+symb[0]+" Unable to update permissions of channel {}: missing permisions".format(chan["name"]))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("     "+symb[0]+" Unable to update permissions of channel {}: {}".format(chan["name"],e))
                        problems[1] += 1
                    else:
                        logs.append("    "+symb[2]+" Permissions of channel {} set".format(chan["name"]))

        async def load_members(self, ctx:MyContext, problems: list, logs:list, symb:list, data:dict, args:tuple,roles_list:dict):
            if "members" not in data.keys():
                return
            change_nicks = True
            if not ctx.guild.me.guild_permissions.manage_nicknames:
                change_nicks = False
                logs.append("  "+symb[0]+" Unable to change nicknames: missing permissions")
                problems[0] += 1
            change_roles = True
            if not ctx.guild.me.guild_permissions.manage_roles:
                change_roles = False
                logs.append("  "+symb[0]+" Unable to change roles: missing permissions")
                problems[0] += 1
            for memb in data["members"]:
                member = ctx.guild.get_member(memb["id"])
                if member is None:
                    continue
                try:
                    edition = list()
                    if member.nick != memb["nickname"] and change_nicks and (member.top_role.position < ctx.guild.me.top_role.position and ctx.guild.owner!=member):
                        await member.edit(nick=memb["nickname"])
                        edition.append("nickname")
                    roles = list()
                    for r in memb["roles"]:
                        try:
                            _role = roles_list[r]
                            if 0 < _role.position < ctx.guild.me.top_role.position:
                                roles.append(_role)
                        except KeyError:
                            pass
                    if roles != member.roles and change_roles and len(roles) > 0:
                        try:
                            await member.add_roles(*roles)
                        except discord.errors.Forbidden:
                            logs.append("  "+symb[0]+" Unable to give roles to user {}: missing permissions".format(member))
                            problems[0] += 1
                        except Exception as e:
                            logs.append("  "+symb[0]+" Unable to give roles to user {}: {}".format(member,e))
                            problems[1] += 1
                        else:
                            edition.append("roles")
                except Exception as e:
                    logs.append("  "+symb[0]+" Unable to set user {}: {}".format(member,e))
                    problems[1] += 1
                else:
                    if len(edition) > 0:
                        logs.append("  "+symb[2]+" Updated {} for user {}".format("and".join(edition),member))

        async def load_emojis(self, ctx:MyContext, problems: list, logs:list, symb:list, data:dict, args:tuple, roles_list:dict):
            if not ctx.guild.me.guild_permissions.manage_expressions:
                logs.append("  "+symb[0]+" Unable to create or update emojis: missing permissions")
                problems[0] += 1
            else:
                for emojiname, emojidata in data["emojis"].items():
                    try:
                        # emoji_name = emojiname.replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        if len([x for x in ctx.guild.emojis if x.name == emojiname]) > 0:
                            logs.append("  "+symb[1]+" Emoji {} already exists".format(emojiname))
                            continue
                        try:
                            icon = await self.urlToByte(emojidata["url"])
                        except aiohttp.ClientError:
                            icon = None
                        if icon is None:
                            logs.append("  "+symb[0]+" Unable to create emoji {}: the image has probably been deleted from Discord cache".format(emojiname))
                            continue
                        roles = list()
                        for r in emojidata["roles"]:
                            try:
                                _role = roles_list[r]
                                if 0 < _role.position < ctx.guild.me.top_role.position:
                                    roles.append(_role)
                            except KeyError:
                                pass
                        if len(roles) == 0:
                            roles = None
                        await ctx.guild.create_custom_emoji(name=emojiname, image=icon, roles=roles)
                    except discord.errors.Forbidden:
                        logs.append("  "+symb[0]+" Unable to create emoji {}: missing permissions".format(emojiname))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to create emoji {}: {}".format(emojiname,e))
                        problems[1] += 1
                    else:
                        logs.append("  "+symb[2]+" Emoji {} created".format(emojiname))
                if "delete_old_emojis" in args:
                    for emoji in ctx.guild.emojis:
                        if emoji.name in data["emojis"].keys():
                            continue
                        try:
                            await emoji.delete()
                        except discord.errors.Forbidden:
                            logs.append("  "+symb[0]+" Unable to delete emoji {}: missing permissions".format(emoji.name))
                            problems[0] += 1
                        except Exception as e:
                            if not "404" in str(e):
                                logs.append("  "+symb[0]+" Unable to delete emoji {}: {}".format(emoji.name,e))
                                problems[1] += 1
                        else:
                            logs.append("  "+symb[2]+" Emoji {} deleted".format(emoji.name))

        async def load_webhooks(self, ctx:MyContext, problems: list, logs:list, symb:list, data:dict, args:tuple, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_webhooks:
                logs.append("  "+symb[0]+" Unable to create or update webhooks: missing permissions")
                problems[0] += 1
            else:
                created_webhooks_urls = list()
                for webhook in data["webhooks"]:
                    try:
                        # webhookname = webhook["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        webhookname = webhook["name"]
                        if len([x for x in await ctx.guild.webhooks() if x.url == webhook["url"]]) > 0:
                            logs.append("  "+symb[1]+" Webhook {} already exists".format(webhookname))
                            continue
                        try:
                            icon = await self.urlToByte(webhook["avatar"])
                        except aiohttp.ClientError:
                            logs.append("  "+symb[0]+" Unable to get avatar of wbehook {}: the image has probably been deleted from Discord cache".format(webhookname))
                            icon = None
                        try:
                            real_channel = channels_list[webhook["channel"]]
                        except KeyError:
                            logs.append("  "+symb[0]+" Unable to create wbehook {}: unable to get the text channel".format(webhookname))
                            continue
                        await real_channel.create_webhook(name=webhook["name"], avatar=icon)
                    except discord.errors.Forbidden:
                        logs.append("  "+symb[0]+" Unable to create webhook {}: missing permissions".format(webhookname))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to create webhook {}: {}".format(webhookname,e))
                        problems[1] += 1
                    else:
                        logs.append("  "+symb[2]+" Webhook {} created".format(webhookname))
                        created_webhooks_urls.append(webhook["url"])
                if "delete_old_webhooks" in args:
                    for web in await ctx.guild.webhooks():
                        if web.url in created_webhooks_urls:
                            continue
                        try:
                            await web.delete()
                        except discord.errors.Forbidden:
                            logs.append("  "+symb[0]+" Unable to delete webhook {}: missing permissions".format(web.name))
                            problems[0] += 1
                        except Exception as e:
                            if not "404" in str(e):
                                logs.append("  "+symb[0]+" Unable to delete webhook {}: {}".format(web.name,e))
                                problems[1] += 1
                        else:
                            logs.append("  "+symb[2]+" Webhook {} deleted".format(web.name))


        async def load_backup(self,ctx:MyContext, data:dict, args:list) -> typing.Tuple[list,list]:
            "Load a backup in a server, for backups version 1"
            if data.pop('_backup_version',None) != 1:
                return ([0,1], ["Unknown backup version"])
            symb = ["`[X]`","`[-]`","`[O]`"]
            problems = [0,0]
            logs = list()
            # afk_timeout
            if ctx.guild.afk_timeout == data["afk_timeout"]:
                logs.append(symb[1]+" No need to change AFK timeout duration")
            else:
                try:
                    await ctx.guild.edit(afk_timeout=data["afk_timeout"])
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set AFK timeout duration: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set AFK timeout duration: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" AFK timeout duration set to {}s".format(data["afk_timeout"]))
            # banned_users
            try:
                banned_users = [x.user.id async for x in ctx.guild.bans(limit=None)]
                users_to_ban = [x for x in data["banned_users"].items() if x[0] not in banned_users]
                if len(users_to_ban) == 0:
                    logs.append(symb[1]+" No user to ban")
                else:
                    for x in users_to_ban:
                        user,reason = x
                        try:
                            await ctx.guild.ban(discord.Object(user),reason=reason,delete_message_days=0)
                        except discord.errors.NotFound:
                            pass
                    logs.append(symb[2]+" Banned users updated ({} users)".format(len(data["banned_users"].keys())))
            except discord.errors.Forbidden:
                logs.append(symb[0]+" Unable to ban users: missing permissions")
                problems[0] += 1
            except Exception as e:
                logs.append(symb[0]+f" Unable to ban users: {e}")
                problems[1] += 1
            # default_notifications
            if ctx.guild.default_notifications.value == data["default_notifications"]:
                logs.append(symb[1]+" No need to change default notifications")
            else:
                try:
                    default_notif = discord.NotificationLevel(data["default_notifications"])
                    await ctx.guild.edit(default_notifications = default_notif)
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set default notifications: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set default notifications: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Default notifications set to "+default_notif.name)
            # explicit_content_filter
            if ctx.guild.explicit_content_filter.value == data["explicit_content_filter"]:
                logs.append(symb[1]+" No need to change content filter")
            else:
                try:
                    contentFilter = discord.ContentFilter(data["explicit_content_filter"])
                    await ctx.guild.edit(explicit_content_filter = contentFilter)
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set content filter: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set content filter: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Explicit content filter set to "+contentFilter.name)
            # icon
            try:
                icon = None if data['icon'] is None else await self.urlToByte(data['icon'])
            except aiohttp.ClientError:
                icon = None
            if icon is not None or data['icon'] is None:
                try:
                    await ctx.guild.edit(icon = icon)
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set server icon: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set server icon: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Server icon updated")
            elif data["icon"] is None:
                logs.append(symb[2]+" Server icon deleted")
            else:
                logs.append(symb[0]+" Unable to set server icon: the image has probably been deleted from Discord cache")
                problems[1] += 1
            # mfa_level
            if ctx.guild.mfa_level != data["mfa_level"]:
                logs.append(symb[0]+" Unable to change 2FA requirement: only owner can do that")
                problems[0] += 1
            else:
                logs.append(symb[1]+" No need to change 2FA requirement")
                problems[1] += 1
            # name
            if ctx.guild.name == data["name"]:
                logs.append(symb[1]+" No need to change server name")
            else:
                try:
                    await ctx.guild.edit(name = data["name"])
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set server name: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set server name: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Server name set to "+data["name"])
            # verification_level
            if ctx.guild.verification_level.value == data["verification_level"]:
                logs.append(symb[1]+" No need to change verification level")
            else:
                try:
                    verif_level = discord.VerificationLevel(data["verification_level"])
                    await ctx.guild.edit(verification_level=verif_level)
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set verification level: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set verification level: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Verification level set to "+verif_level.name)
            # roles
            logs.append(" - Creating roles")
            roles_list = {}
            await self.load_roles(ctx, problems, logs, symb, data, args, roles_list)
            # categories
            logs.append(" - Creating categories")
            channels_list = {}
            await self.load_categories(ctx, problems, logs, symb, data, args, channels_list)
            # channels
            logs.append(" - Creating channels")
            await self.load_channels(ctx, problems, logs, symb, data, args, channels_list)
            # channels permissions
            logs.append(" - Updating categories and channels permissions")
            await self.load_perms(ctx, problems, logs, symb, data, args, roles_list, channels_list)
            # members
            logs.append(" - Updating members roles and nick")
            await self.load_members(ctx, problems, logs, symb, data, args, roles_list)
            # emojis
            logs.append(" - Creating emojis")
            await self.load_emojis(ctx, problems, logs, symb, data, args, roles_list)
            # webhooks
            logs.append(" - Creating webhooks")
            await self.load_webhooks(ctx, problems, logs, symb, data, args, channels_list)

            return problems,logs

async def setup(bot):
    await bot.add_cog(Backups(bot))