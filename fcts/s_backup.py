import discord
import importlib, aiohttp, json, os, typing
from discord.ext import commands
from io import BytesIO

from fcts import checks
importlib.reload(checks)


class BackupCog(commands.Cog):
    """This cog is used to make and apply backups of a Discord server"""

    def __init__(self,bot):
        self.bot = bot
        self.file = "s_backup"
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr


    @commands.group(name='backup')
    @commands.guild_only()
    @commands.cooldown(2,120, commands.BucketType.guild)
    @commands.check(checks.has_admin)
    async def main_backup(self,ctx:commands.Context):
        pass


    @main_backup.command(name="load")
    async def backup_load(self,ctx:commands.Context,*arguments):
        """Load a backup created with `backup create`
Arguments are:
    - reset: delete everything from the current server
    - delete_old_channels: delete every current channel/category
    - delete_old_roles: delete every current role
    - delete_old_emojis: delete every current emoji
    - delete_old_webhooks: well, same but with webhooks"""
        # Analyzing arguments
        valid_args = ["reset","delete_old_channels","delete_old_roles","delete_old_emojis","delete_old_webhooks"]
        arguments = set([a.lower() for a in arguments if a.lower() in valid_args])
        if "reset" in arguments:
            arguments.update(set(['delete_old_channels','delete_old_roles','delete_old_emojis','delete_old_webhooks']))
        # Loading backup from file
        try:
            data = json.loads(await ctx.message.attachments[0].read())
        except:
            await ctx.send(await self.translate(ctx.guild,"s_backup","invalid_file"))
            return
        # Applying backup
        msg = await ctx.send(await self.translate(ctx.guild,"s_backup","loading"))
        try:
            if data["_backup_version"] == 1:
                problems, logs = await self.BackupLoaderV1().load_backup(ctx,data,arguments)
            else:
                await ctx.send(await self.translate(ctx.guild,"s_backup","invalid_version"))
                return
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild,"s_backup","err"))
            await ctx.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
            return
        # Formatting and sending logs
        logs = "Found {} problems (including {} permissions issues)\n\n".format(sum(problems),problems[0]) + "\n".join(logs)
        if len(logs)>1950:
            # If too many logs, send in a file
            logs = logs.replace("`[O]`","[O]").replace("`[-]`","[-]").replace("`[X]`","[X]")
            finish_msg = await self.translate(ctx.guild,"s_backup","finished")
            try:
                await ctx.send(content=finish_msg,file=discord.File(BytesIO(logs.encode()),filename="logs.txt"))
            except discord.errors.NotFound: # if channel was deleted, send in DM
                await ctx.author.send(content=finish_msg,file=discord.File(BytesIO(logs.encode()),filename="logs.txt"))
            try:
                await msg.delete()
            except: # can happens because deleted channel
                pass
        else:
            # Else, we just edit the message with logs
            try:
                await msg.edit(content=logs)
            except discord.errors.NotFound: # if channel was deleted, send in DM
                await ctx.author.send(logs)

    @main_backup.command(name="create")
    async def backup_create(self,ctx:commands.Context):
        """Make and send a backup of this server
        You will find there the configuration of your server, every general settings, the list of members with their roles, the list of categories and channels (with their permissions), emotes, and webhooks.
        Please note that audit logs, messages and invites are not used"""
        try:
            directory = await self.create_backup(ctx)
            await ctx.send(await self.translate(ctx.guild.id,'modo','backup-done'),file=discord.File(directory))
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
    
    # --------

    async def create_backup(self,ctx:commands.Context) -> str:
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
                temp2['permissions'] = dict()
                for x in iter(iter_perm):
                    if x[1] != None:
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
            'voiceregion': g.region.value,
            'afk_timeout': g.afk_timeout,
            'icon': None if len(g.icon_url)==0 else str(g.icon_url),
            'verification_level': g.verification_level.value,
            'mfa_level': g.mfa_level,
            'explicit_content_filter': g.explicit_content_filter.value,
            'default_notifications': g.default_notifications.value,
            'created_at': int(g.created_at.timestamp()),
            'afk_channel': g.afk_channel.id if g.afk_channel!=None else None,
            'system_channel': g.system_channel.id if g.system_channel!=None else None}
        roles = list()
        for x in g.roles:
            roles.append({'id':x.id,'name':x.name,'color':x.colour.value,'position':x.position,'hoist':x.hoist,'mentionable':x.mentionable,'permissions':x.permissions.value})
        back['roles'] = roles
        categ = list()
        for x in g.by_category():
            c,l = x[0],x[1]
            if c==None:
                temp = {'id': None}
            else:
                temp = {'id': c.id,
                    'name': c.name,
                    'position': c.position,
                    'is_nsfw': c.is_nsfw() }
                perms = list()
                for iter_obj, iter_perm in c.overwrites.items():
                    temp2 = {'id':iter_obj.id}
                    if isinstance(iter_obj,discord.Member):
                        temp2['type'] = 'member'
                    else:
                        temp2['type'] = 'role'
                    temp2['permissions'] = dict()
                    for x in iter(iter_perm):
                        if x[1] != None:
                            temp2['permissions'][x[0]] = x[1]
                    perms.append(temp2)
                temp['permissions_overwrites'] = perms
            temp['channels'] = list()
            for chan in l:
                temp['channels'].append(await get_channel_json(chan))
            categ.append(temp)
        back['categories'] = categ
        back['emojis'] = dict()
        for e in g.emojis:
            back['emojis'][e.name] = {"url": str(e.url), "roles": [x.id for x in e.roles]}
        try:
            banned = dict()
            for b in await g.bans():
                banned[b.user.id] = b.reason
            back['banned_users'] = banned
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_error(e,ctx)
        try:
            webs = list()
            for w in await g.webhooks():
                webs.append({'channel':w.channel_id,'name':w.name,'avatar':str(w.avatar_url),'url':w.url})
            back['webhooks'] = webs
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_error(e,ctx)
        back['members'] = list()
        for memb in g.members:
            back['members'].append({'id': memb.id,
                'nickname': memb.nick,
                'bot': memb.bot,
                'roles': [x.id for x in memb.roles][1:] })
        js = json.dumps(back, sort_keys=True, indent=4)
        directory = 'backup/{}.json'.format(g.id)
        if not os.path.exists('backup/'):
            os.makedirs('backup/')
        with open(directory,'w',encoding='utf-8') as file:
            file.write(js)
            return directory

    # ----------

    class BackupLoaderV1:
        def __init__(self):
            pass
    
        async def urlToByte(self,url:str) -> typing.Optional[bytes]:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.get(url) as response:
                    if response.status>=200 and response.status<300:
                        res = await response.read()
                    else:
                        res = None
            return res
        
        async def load_roles(self, ctx:commands.Context, problems: list, logs:list, symb:list, data:dict, args:tuple,roles_list:dict):
            if not ctx.guild.me.guild_permissions.manage_roles:
                logs.append("  "+symb[0]+" Unable to create or update roles: missing permissions")
                problems[0] += 1
                roles_list = {x.id: x for x in ctx.guild.roles}
            else:
                for role in data["roles"]:
                    try:
                        rolename = role["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        action = "edit"
                        r = ctx.guild.get_role(role["id"])
                        if r == None:
                            r = [x for x in ctx.guild.roles if x.name == role["name"]]
                            if len(r) == 0:
                                action = "create"
                                try:
                                    r = await ctx.guild.create_role(name=role["name"])
                                except Exception as e:
                                    pass
                            else:
                                r = r[0]
                        if role["name"] == "@everyone":
                            if r.permissions.value != role["permissions"]:
                                await r.edit(permissions = discord.Permissions(role["permissions"]))
                        else:
                            kwargs = dict()
                            if r.name != role["name"]:
                                kwargs["name"] = role["name"]
                            if r.permissions.value != role["permissions"]:
                                kwargs["permissions"] = discord.Permissions(role["permissions"])
                            if r.colour.value != role["color"]:
                                kwargs["colour"] = discord.Colour(role["color"])
                            if r.hoist != role["hoist"]:
                                kwargs["hoist"] = role["hoist"]
                            if r.mentionable != role["mentionable"]:
                                kwargs["mentionable"] = role["mentionable"]
                            if len(kwargs.keys()) > 0:
                                await r.edit(**kwargs)
                                if action=="create":
                                    logs.append("  "+symb[2]+" Role {} created".format(rolename))
                                else:
                                    logs.append("  "+symb[2]+" Role {} set".format(rolename))
                            elif action=="create":
                                logs.append("  "+symb[2]+" Role {} created".format(rolename))
                            else:
                                logs.append("  "+symb[1]+" No need to change role {}".format(rolename))
                        roles_list[role["id"]] = r
                    except discord.errors.Forbidden:
                        if action == "create":
                            await r.delete()
                        logs.append("  "+symb[0]+" Unable to {} role {}: missing permissions".format(action,rolename))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to {} role {}: {}".format(action,rolename,e))
                        problems[1] += 1
                    else:
                        pass
                if "delete_old_roles" in args:
                    for role in ctx.guild.roles:
                        if role in roles_list.values():
                            continue
                        try:
                            await role.delete()
                        except discord.errors.Forbidden:
                            logs.append("  "+symb[0]+" Unable to delete role {}: missing permissions".format(role.name))
                            problems[0] += 1
                        except Exception as e:
                            if not "404" in str(e):
                                logs.append("  "+symb[0]+" Unable to delete role {}: {}".format(role.name,e))
                                problems[1] += 1
                        else:
                            logs.append("  "+symb[2]+" Role {} deleted".format(role.name))
                for r in data["roles"]:
                    if r["id"] in roles_list.keys() and r["position"]>0:
                        new_pos = min(max(ctx.guild.me.top_role.position-1,1), r["position"])
                        try:
                            await roles_list[r["id"]].edit(position = new_pos)
                        except Exception as e:
                            if isinstance(e,discord.errors.HTTPException) or (isinstance(e,discord.errors.HTTPException) and hasattr(e,"status") and e.status in (403,400)):
                                logs.append("  "+symb[0]+" Unable to move role {} to position {}: missing permissions".format(r["name"],new_pos))
                                problems[0] += 1
                            else:
                                logs.append("  "+symb[0]+" Unable to move role {} to position {}: {}".format(r["name"],new_pos,e))
                                problems[1] += 1

        async def load_categories(self, ctx:commands.Context, problems: list, logs:list, symb:list, data:dict, args:tuple, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_channels:
                logs.append("  "+symb[0]+" Unable to create or update categories: missing permissions")
                problems[0] += 1
                channels_list = {x.id: x for x in ctx.guild.channels}
            else:
                for categ in data["categories"]:
                    try:
                        if ("id" in categ.keys() and categ["id"] == None):
                            continue
                        categname = categ["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        action = "edit"
                        c = ctx.guild.get_channel(categ["id"])
                        if c == None:
                            c = [x for x in ctx.guild.categories if x.name == categ["name"]]
                            if len(c) == 0:
                                action = "create"
                                c = await ctx.guild.create_category(name=categ["name"])
                            else:
                                c = c[0]
                        kwargs = dict()
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

        async def load_channels(self, ctx:commands.Context, problems:list, logs:list, symb:list, data:dict, args:tuple, channels_list:dict):
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
                    try:
                        channame = chan["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        action = "edit"
                        c = ctx.guild.get_channel(chan["id"])
                        if c == None:
                            c = [x for x in ctx.guild.text_channels+ctx.guild.voice_channels if x.name == chan["name"]]
                            if len(c) == 0:
                                action = "create"
                                _categ = None if categ==None else channels_list[categ]
                                if chan["type"]=="TextChannel":
                                    c = await ctx.guild.create_text_channel(name=chan["name"],category=_categ)
                                else:
                                    c = await ctx.guild.create_voice_channel(name=chan["name"],category=_categ)
                            else:
                                c = c[0]
                        kwargs = dict()
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
                if target == None:
                    continue
                new_perms = discord.PermissionOverwrite(**perm["permissions"])
                if item.overwrites_for(target) == new_perms:
                    continue
                try:
                    await item.set_permissions(target,overwrite=new_perms)
                except:
                    pass

        async def load_perms(self, ctx:commands.Context, problems:list, logs:list, symb:list, data:dict, args:tuple, roles_list:dict, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_roles:
                logs.append("  "+symb[0]+" Unable to update permissions: missing permissions")
                problems[0] += 1
            # categories
            for categ in data["categories"]:
                if "id" in categ.keys() and categ["id"] != None and "permissions_overwrites" in categ.keys():
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

        async def load_members(self, ctx:commands.Context, problems: list, logs:list, symb:list, data:dict, args:tuple,roles_list:dict):
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
                if member == None:
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
                    if roles != member.roles and change_roles and len(roles)>0:
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
                    if len(edition)>0:
                        logs.append("  "+symb[2]+" Updated {} for user {}".format("and".join(edition),member))

        async def load_emojis(self, ctx:commands.Context, problems: list, logs:list, symb:list, data:dict, args:tuple, roles_list:dict):
            if not ctx.guild.me.guild_permissions.manage_emojis:
                logs.append("  "+symb[0]+" Unable to create or update emojis: missing permissions")
                problems[0] += 1
            else:
                for emojiname, emojidata in data["emojis"].items():
                    try:
                        emoji_name = emojiname.replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        if len([x for x in ctx.guild.emojis if x.name == emojiname]) > 0:
                            logs.append("  "+symb[1]+" Emoji {} already exists".format(emojiname))
                            continue
                        try:
                            icon = await self.urlToByte(emojidata["url"])
                        except:
                            logs.append("  "+symb[0]+" Unable to create emoji {}: the image has probably been deleted from Discord cache".format(emoji_name))
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
                        logs.append("  "+symb[0]+" Unable to create emoji {}: missing permissions".format(emoji_name))
                        problems[0] += 1
                    except Exception as e:
                        logs.append("  "+symb[0]+" Unable to create emoji {}: {}".format(emoji_name,e))
                        problems[1] += 1
                    else:
                        logs.append("  "+symb[2]+" Emoji {} created".format(emoji_name))
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

        async def load_webhooks(self, ctx:commands.Context, problems: list, logs:list, symb:list, data:dict, args:tuple, channels_list:dict):
            if not ctx.guild.me.guild_permissions.manage_webhooks:
                logs.append("  "+symb[0]+" Unable to create or update webhooks: missing permissions")
                problems[0] += 1
            else:
                created_webhooks_urls = list()
                for webhook in data["webhooks"]:
                    try:
                        webhookname = webhook["name"].replace("@everyone","@"+u'\u200b'+"everyone").replace("@here","@"+u'\u200b'+"here")
                        if len([x for x in await ctx.guild.webhooks() if x.url == webhook["url"]]) > 0:
                            logs.append("  "+symb[1]+" Webhook {} already exists".format(webhookname))
                            continue
                        try:
                            icon = await self.urlToByte(webhook["avatar"])
                        except:
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


        async def load_backup(self,ctx:commands.Context, data:dict, args:list) -> (list,list):
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
                banned_users = [x[0].id for x in await ctx.guild.bans()]
                users_to_ban = [x for x in data["banned_users"].items() if x[0] not in banned_users]
                if len(users_to_ban)==0:
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
                icon = None if data['icon']==None else await self.urlToByte(data['icon'])
            except:
                icon = None
            if icon!=None or data['icon']==None:
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
            elif data["icon"] == None:
                logs.append(symb[2]+" Server icon deleted")
            else:
                problems[1] += 1
                logs.append(symb[0]+" Unable to set server icon: the image has probably been deleted from Discord cache")
            # mfa_level
            if ctx.guild.mfa_level != data["mfa_level"]:
                logs.append(symb[0]+" Unable to change 2FA requirement: only owner can do that")
            else:
                logs.append(symb[1]+" No need to change 2FA requirement")
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
            # voiceregion
            if ctx.guild.region.value == data["voiceregion"]:
                logs.append(symb[1]+" No need to change voice region")
            else:
                try:
                    voicereg = discord.VoiceRegion(data["voiceregion"])
                    await ctx.guild.edit(region=voicereg)
                except discord.errors.Forbidden:
                    logs.append(symb[0]+" Unable to set voice region: missing permissions")
                    problems[0] += 1
                except Exception as e:
                    logs.append(symb[0]+f" Unable to set voice region: {e}")
                    problems[1] += 1
                else:
                    logs.append(symb[2]+" Voice region set to "+voicereg.name)
            # roles
            logs.append(" - Creating roles")
            roles_list = dict()
            await self.load_roles(ctx, problems, logs, symb, data, args, roles_list)
            # categories
            logs.append(" - Creating categories")
            channels_list = dict()
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

def setup(bot):
    bot.add_cog(BackupCog(bot))