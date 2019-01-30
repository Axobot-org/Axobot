from discord.ext import commands
import discord, re, datetime, random


async def can_mute(ctx):
    """Check if someone can mute"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"mute")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles

async def can_warn(ctx):
    """Check if someone can warn"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"warn")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_roles

async def can_kick(ctx):
    """Check if someone can kick"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"kick")
    else:
        return ctx.channel.permissions_for(ctx.author).kick_members

async def can_ban(ctx):
    """Check if someone can ban"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"ban")
    else:
        return ctx.channel.permissions_for(ctx.author).ban_members

async def can_slowmode(ctx):
    """Check if someone can use slowmode"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"slowmode")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_channels

async def can_clear(ctx):
    """Check if someone can use clear"""
    if ctx.bot.database_online:
        return await ctx.bot.cogs["ServerCog"].staff_finder(ctx.author,"clear")
    else:
        return ctx.channel.permissions_for(ctx.author).manage_messages

async def can_see_banlist(ctx):
    """Check if someone can see the banlist"""
    return ctx.channel.permissions_for(ctx.author).administrator or await ctx.bot.cogs["AdminCog"].check_if_admin(ctx)

async def can_pin_msg(ctx):
    """... if someone can pin a message"""
    return ctx.channel.permissions_for(ctx.author).manage_messages or await ctx.bot.cogs["AdminCog"].check_if_admin(ctx)

class ModeratorCog:
    """Here you will find everything you need to moderate your server. Please note that most of the commands are reserved for certain members only."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "moderation"
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
        
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
    
    @commands.command(name="slowmode")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.check(can_slowmode)
    async def slowmode(self,ctx,time='off'):
        """Keep your chat cool"""
        if time.isnumeric():
            time = int(time)
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-slowmode"))
            return
        if time == 'off' or time==0:
            await ctx.bot.http.request(discord.http.Route('PATCH', '/channels/{cid}', cid=ctx.channel.id), json={'rate_limit_per_user':0})
            message = await self.translate(ctx.guild.id,"modo","slowmode-0")
            log = str(await self.translate(ctx.guild.id,"logs","slowmode-disabled")).format(channel=ctx.channel.mention)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"slowmode",log,ctx.author)
        elif type(time)==int:
            if time>120:
                message = await self.translate(ctx.guild.id,"modo","slowmode-1")
            else:
                await ctx.bot.http.request(discord.http.Route('PATCH', '/channels/{cid}', cid=ctx.channel.id), json={'rate_limit_per_user':time})
                message = str(await self.translate(ctx.guild.id,"modo","slowmode-2")).format(ctx.channel.mention,time)
                log = str(await self.translate(ctx.guild.id,"logs","slowmode-enabled")).format(channel=ctx.channel.mention,seconds=time)
                await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"slowmode",log,ctx.author)
        else:
                message = await self.translate(ctx.guild.id,"modo","slowmode-3")
        await ctx.send(message)
        

    @commands.command(name="clear")
    @commands.cooldown(4, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_clear)
    async def clear(self,ctx,number:int,*,params=''):
        """Keep your chat clean
        <number> : number of messages to check
        Available parameters :
            <@user> : list of users to check (just mention them)
            ('-f' or) '+f' : delete if the message  (does not) contain any file
            ('-l' or) '+l' : delete if the message (does not) contain any link
            ('-p' or) '+p' : delete if the message is (not) pinned
            ('-i' or) '+i' : delete if the message contain a discord invite
        By default, the bot will not delete pinned messages"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.translate(ctx.guild.id,"modo","need-manage-messages"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).read_message_history:
            await ctx.send(await self.translate(ctx.guild.id,"modo","need-read-history"))
            return
        if number<1:
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","clear-1"))+" "+self.bot.cogs['EmojiCog'].customEmojis["owo"])
            return
        #file
        if "-f" in params:
            files = 0
        elif "+f" in params:
            files = 2
        else:
            files = 1
        #link
        if "-l" in params:
            links = 0
        elif "+l" in params:
            links = 2
        else:
            links = 1
        #pinned
        if '-p' in params:
            pinned = 0
        elif "+p" in params:
            pinned = 2
        else:
            pinned = 1
        #invite
        if '-i' in params:
            invites = 0
        elif "+i" in params:
            invites = 2
        else:
            invites = 1
        #user
        if ctx.message.mentions != []:
            users = ctx.message.mentions
        else:
            users = ctx.guild.members
        #0: does  -  2: does not  -  1: why do we care?
        def check(m):
            i = self.bot.cogs["UtilitiesCog"].sync_check_discord_invite(m.content)
            r = self.bot.cogs["UtilitiesCog"].sync_check_any_link(m.content)
            c1 = c2 = c3 = c4 = True
            if pinned != 1:
                if (m.pinned and pinned==0) or (not m.pinned and pinned==2):
                    c1 = False
            else:
                c1 = not m.pinned
            if files != 1:
                if (m.attachments != [] and files==0) or (m.attachments==[] and files==2):
                    c2 = False
            if links != 1:
                if (r == None and links==2) or (r != None and links==0):
                    c3 = False
            if invites != 1:
                if (i == None and invites==2) or (i != None and invites==0):
                    c4 = False
            #return ((m.pinned == pinned) or ((m.attachments != []) == files) or ((r != None) == links)) and m.author in users
            return c1 and c2 and c3 and c4 and m.author in users
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=number, check=check)
        await ctx.send(str(await self.translate(ctx.guild,"modo","clear-0")).format(len(deleted)),delete_after=2.0)
        log = str(await self.translate(ctx.guild.id,"logs","clear")).format(channel=ctx.channel.mention,number=len(deleted))
        await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        

    @commands.command(name="kick")
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_kick)
    async def kick(self,ctx,user:discord.Member,*,reason="Unspecified"):
        """Kick a member from this server"""
        try:
            if not ctx.channel.permissions_for(ctx.guild.me).kick_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-kick"))
                return
            if self.bot.database_online:
                if await self.bot.cogs["ServerCog"].staff_finder(user,"kick") or user==ctx.guild.me:
                    return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            elif user==ctx.guild.me or ctx.channel.permissions_for(user).kick_members:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            if user.roles[-1].position > ctx.guild.me.roles[-1].position:
                await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
                return
            if user.id not in self.bot.cogs['WelcomerCog'].no_message:
                try:
                    if reason == "Unspecified":
                        await user.send(str(await self.translate(ctx.guild.id,"modo","kick-noreason")).format(ctx.guild.name))
                    else:
                        await user.send(str(await self.translate(ctx.guild.id,"modo","kick-reason")).format(ctx.guild.name,reason))
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    pass
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.kick(user,reason=reason)
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(guildID=ctx.guild.id,memberID=user.id,Type="kick",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","kick")).format(user,reason))
            log = str(await self.translate(ctx.guild.id,"logs","kick")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"kick",log,ctx.author)
        except discord.errors.Forbidden:
            await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
        await self.bot.cogs['Events'].add_event('kick')


    @commands.command(name="warn")
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_warn)
    async def warn(self,ctx,user:discord.Member,*,message):
        """Send a warning to a member."""
        try:
            if self.bot.database_online and await self.bot.cogs["ServerCog"].staff_finder(user,"warn"):
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
            if user.bot and not user.id==423928230840500254:
                await ctx.send(await self.translate(ctx.guild.id,"modo","warn-bot"))
                return
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            return
        try:
            try:
                await user.send(str(await self.translate(ctx.guild.id,"modo","warn-mp")).format(ctx.guild.name,message))
            except:
                pass
            message = await self.bot.cogs["UtilitiesCog"].clear_msg(message,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(guildID=ctx.guild.id,memberID=user.id,Type="warn",ModID=ctx.author.id,Reason=message,date=datetime.datetime.now()).create_id(caseIDs)
                caseID = "'Unsaved'"
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                else:
                    await ctx.send(str(await self.translate(ctx.guild.id,"modo","warn-1")).format(user,message))
                log = str(await self.translate(ctx.guild.id,"logs","warn")).format(member=user,reason=message,case=caseID)
                await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"warn",log,ctx.author)
            else:
                await ctx.send(await self.translate(ctx.guild.id,'modo','warn-but-db'))
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @commands.command(name="mute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_mute)
    async def mute(self,ctx,user:discord.Member,*,reason="Unspecified"):
        """Mute someone. When someone is muted, the bot adds the role "muted" to him"""
        try:
            if self.bot.database_online and await self.bot.cogs["ServerCog"].staff_finder(user,"mute") or user==ctx.guild.me:
                await ctx.send(str(await self.translate(ctx.guild.id,"modo","staff-mute"))+random.choice([':confused:',':upside_down:',self.bot.cogs['EmojiCog'].customEmojis['wat'],':no_mouth:',self.bot.cogs['EmojiCog'].customEmojis['owo'],':thinking:',]))
                return
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            return
        role = discord.utils.get(ctx.guild.roles,name="muted")
        if role in user.roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","already-mute"))
            return
        if role == None:
            await ctx.send(await self.translate(ctx.guild.id,"modo","no-mute"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return
        if role.position > ctx.guild.me.roles[-1].position:
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-high"))
            return
        caseID = "'Unsaved'"
        try:
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(guildID=ctx.guild.id,memberID=user.id,Type="mute",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await user.add_roles(role,reason=reason)
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","mute-1")).format(user,reason))
            log = str(await self.translate(ctx.guild.id,"logs","mute-on")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"mute",log,ctx.author)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)


    @commands.command(name="unmute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_mute)
    async def unmute(self,ctx,user:discord.Member):
        """Unmute someone
        This will remove the role 'muted' for the targeted member"""
        role = discord.utils.get(ctx.guild.roles,name="muted")
        if role not in user.roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","already-unmute"))
            return
        if role == None:
            await ctx.send(await self.translate(ctx.guild.id,"modo","no-mute"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return
        if role.position > ctx.guild.me.roles[-1].position:
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-high"))
            return
        try:
            await user.remove_roles(role,reason="unmuted by {}".format(ctx.author))
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","unmute-1")).format(user))
            log = str(await self.translate(ctx.guild.id,"logs","mute-off")).format(member=user)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"mute",log,ctx.author)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)


    @commands.command(name="ban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_ban)
    async def ban(self,ctx,user,*,reason="Unspecified"):
        """Ban someone"""
        try:
            backup = user
            try:
                user = await commands.UserConverter().convert(ctx,user)
            except:
                if user.isnumeric():
                    try:
                        user = await self.bot.get_user_info(int(user))
                        del backup
                    except:
                        user = None
            if user==None or type(user)==str:
                await ctx.send(str(await self.translate(ctx.guild.id,"modo","cant-find-user")).format(backup))
                return
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
            if user in ctx.guild.members:
                member = ctx.guild.get_member(user.id)
                if self.bot.database_online and await self.bot.cogs["ServerCog"].staff_finder(member,"ban") or user==ctx.guild.me:
                    await ctx.send(await self.translate(ctx.guild.id,"modo","staff-ban"))
                    return
                elif not self.bot.database_online and (ctx.channel.permissions_for(member).ban_members or user==ctx.guild.me):
                    await ctx.send(await self.translate(ctx.guild.id,"modo","staff-ban"))
                    return
                if member.roles[-1].position > ctx.guild.me.roles[-1].position:
                    await ctx.send(await self.translate(ctx.guild.id,"modo","ban-1"))
                    return
            if user in self.bot.users and user.id not in self.bot.cogs['WelcomerCog'].no_message:
                try:
                    if reason == "Unspecified":
                        await user.send(str(await self.translate(ctx.guild.id,"modo","ban-noreason")).format(ctx.guild.name))
                    else:
                        await user.send(str(await self.translate(ctx.guild.id,"modo","ban-reason")).format(ctx.guild.name,reason))
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    pass
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.ban(user,reason=reason,delete_message_days=0)
            await self.bot.cogs['Events'].add_event('ban')
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(guildID=ctx.guild.id,memberID=user.id,Type="ban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","ban")).format(user,reason))
            log = str(await self.translate(ctx.guild.id,"logs","ban")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"ban",log,ctx.author)
        except discord.errors.Forbidden:
            await ctx.send(await self.translate(ctx.guild.id,"modo","ban-1"))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @commands.command(name="unban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(can_ban)
    async def unban(self,ctx,user,*,reason="Unspecified"):
        """Unban someone"""
        try:
            backup = user
            try:
                user = await commands.UserConverter().convert(ctx,user)
            except:
                if user.isnumeric():
                    try:
                        user = await self.bot.get_user_info(int(user))
                        del backup
                    except:
                        await ctx.send(str(await self.translate(ctx.guild.id,"modo","cant-find-user")).format(backup))
                        return
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
            banned_list = [x[1] for x in await ctx.guild.bans()]
            if user not in banned_list:
                await ctx.send(await self.translate(ctx.guild.id,"modo","ban-user-here"))
                return
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.unban(user,reason=reason)
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']         
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(guildID=ctx.guild.id,memberID=user.id,Type="unban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","unban")).format(user))
            log = str(await self.translate(ctx.guild.id,"logs","unban")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"ban",log,ctx.author)
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @commands.command(name="softban")
    @commands.guild_only()
    @commands.check(can_kick)
    async def softban(self,ctx,user:discord.Member,reason="Unspecified"):
        """Kick a member and lets Discord delete all his messages up to 7 days old.
        Permissions for using this command are the same as for the kick"""
        try:
            if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
            if self.bot.database_online:
                if await self.bot.cogs["ServerCog"].staff_finder(user,"kick") or user==ctx.guild.me:
                    return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            elif user==ctx.guild.me or ctx.channel.permissions_for(user).kick_members:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-kick"))
            if user.roles[-1].position > ctx.guild.me.roles[-1].position:
                await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
                return
            try:
                if reason == "Unspecified":
                    await user.send(str(await self.translate(ctx.guild.id,"modo","kick-noreason")).format(ctx.guild.name))
                else:
                    await user.send(str(await self.translate(ctx.guild.id,"modo","kick-reason")).format(ctx.guild.name,reason))
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                pass
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            await ctx.guild.ban(user,reason=reason,delete_message_days=7)
            await user.unban()
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(guildID=ctx.guild.id,memberID=user.id,Type="softban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","kick")).format(user,reason))
            log = str(await self.translate(ctx.guild.id,"logs","softban")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"softban",log,ctx.author)
        except discord.errors.Forbidden:
            await ctx.send(await self.translate(ctx.guild.id,"modo","kick-1"))
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)


    @commands.command(name="banlist")
    @commands.guild_only()
    @commands.check(can_see_banlist)
    async def banlist(self,ctx,reasons:bool=True):
        """Check the list of currently banned members. 
The 'reasons' parameter is used to display the ban reasons.

You must be an administrator of this server to use this command."""
        if not ctx.channel.permissions_for(ctx.guild.me).ban_members:
                await ctx.send(await self.translate(ctx.guild.id,"modo","cant-ban"))
                return
        try:
            liste = await ctx.guild.bans()
        except:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
        desc = list()
        if len(liste)==0:
            desc.append(await self.translate(ctx.guild.id,"modo","no-bans"))
        if reasons:
            for case in liste:
                desc.append("{}  *({})*".format(case[1],case[0]))
        else:
            for case in liste:
                desc.append("{}".format(case[1]))
        embed = ctx.bot.cogs['EmbedCog'].Embed(title=str(await self.translate(ctx.guild.id,"modo","ban-list-title")).format(ctx.guild.name), color=self.bot.cogs["ServerCog"].embed_color, desc="\n".join(desc), time=ctx.message.created_at)
        embed.create_footer(ctx.author)
        await ctx.send(embed=embed.discord_embed(),delete_after=10)


    @commands.group(name="emoji")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    @commands.cooldown(5,20, commands.BucketType.guild)
    async def emoji_group(self,ctx):
        """Manage your emoji
        Administrator permission is required"""
        return
    
    @emoji_group.command(name="rename")
    async def emoji_rename(self,ctx,emoji:discord.Emoji,name):
        """Rename an emoji"""
        if emoji.guild != ctx.guild:
            await ctx.send(await self.translate(ctx.guild.id,"modo","wrong-guild"))
            return
        if not ctx.channel.permissions_for(ctx.guild.me).manage_emojis:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-emoji"))
            return
        await emoji.edit(name=name)
        await ctx.send(str(await self.translate(ctx.guild.id,"modo","emoji-renamed")).format(emoji))

    @emoji_group.command(name="restrict")
    async def emoji_restrict(self,ctx,emoji:discord.Emoji,*,roles):
        """Restrict the use of an emoji to certain roles"""
        if emoji.guild != ctx.guild:
            await ctx.send(await self.translate(ctx.guild.id,"modo","wrong-guild"))
            return
        r = list()
        if not ctx.channel.permissions_for(ctx.guild.me).manage_emojis:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-emoji"))
            return
        for role in roles.split(","):
            role = role.strip()
            if role == "everyone":
                role = "@everyone"
            try:
                role = await commands.RoleConverter().convert(ctx,role)
            except commands.errors.BadArgument:
                msg = await self.translate(ctx.guild.id,"server","change-3")
                await ctx.send(msg.format(role))
                return
            r.append(role)
        await emoji.edit(name=emoji.name,roles=r)
        await ctx.send(str(await self.translate(ctx.guild.id,"modo","emoji-valid")).format(emoji,", ".join([x.name for x in r])))



    @commands.command(name="pin")
    @commands.check(can_pin_msg)
    async def pin_msg(self,ctx,msg:int):
        """Pin a message
ID corresponds to the Identifier of the message"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            await ctx.send(await self.translate(ctx.guild,"modo","cant-pin"))
            return
        try:
            message = await ctx.channel.get_message(msg)
        except Exception as e:
            await ctx.send(str(await self.translate(ctx.guild,"modo","pin-error")).format(e))
            return
        try:
            await message.pin()
        except Exception as e:
            await ctx.send(str(await self.translate(ctx.guild,"modo","pin-error-2")).format(e))
            return


def setup(bot):
    bot.add_cog(ModeratorCog(bot))