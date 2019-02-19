from discord.ext import commands
import discord, re, datetime, random, json, os
from fcts import checks

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
    @commands.check(checks.can_slowmode)
    async def slowmode(self,ctx,time=None):
        """Keep your chat cool"""
        if not ctx.channel.permissions_for(ctx.guild.me).manage_channels:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-slowmode"))
            return
        if time==None:
            return await ctx.send(str(await self.translate(ctx.guild.id,"modo","slowmode-info")).format(ctx.channel.slowmode_delay))
        if time.isnumeric():
            time = int(time)
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
    @commands.check(checks.can_clear)
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
        # 0: does  -  2: does not  -  1: why do we care?
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
            mentions = [x.mention for x in ctx.message.mentions]
            if ctx.prefix.strip() in mentions:
                mentions.remove(ctx.prefix.strip())
            if mentions != []:
                return c1 and c2 and c3 and c4 and m.author.mention in mentions
            else:
                return c1 and c2 and c3 and c4
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=number, check=check)
        await ctx.send(str(await self.translate(ctx.guild,"modo","clear-0")).format(len(deleted)),delete_after=2.0)
        log = str(await self.translate(ctx.guild.id,"logs","clear")).format(channel=ctx.channel.mention,number=len(deleted))
        await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"clear",log,ctx.author)
        

    @commands.command(name="kick")
    @commands.cooldown(5, 20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_kick)
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
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="kick",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
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
    @commands.check(checks.can_warn)
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
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="warn",ModID=ctx.author.id,Reason=message,date=datetime.datetime.now()).create_id(caseIDs)
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
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    async def get_muted_role(self,guild):
        return discord.utils.get(guild.roles,name="muted")

    async def mute_event(self,member,author,reason,caseID):
        role = await self.get_muted_role(member.guild)
        await member.add_roles(role,reason=reason)
        log = str(await self.translate(member.guild.id,"logs","mute-on")).format(member=member,reason=reason,case=caseID)
        await self.bot.cogs["Events"].send_logs_per_server(member.guild,"mute",log,author)

    @commands.command(name="mute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
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
        role = await self.get_muted_role(ctx.guild)
        if role in user.roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","already-mute"))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return
        if role == None:
            role = await self.configure_muted_role(ctx.guild)
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-created"))
        if role.position > ctx.guild.me.roles[-1].position:
            await ctx.send(await self.translate(ctx.guild.id,"modo","mute-high"))
            return
        caseID = "'Unsaved'"
        try:
            reason = await self.bot.cogs["UtilitiesCog"].clear_msg(reason,everyone = not ctx.channel.permissions_for(ctx.author).mention_everyone)
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="mute",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await self.mute_event(user,ctx.author,reason,caseID)
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","mute-1")).format(user,reason))
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)


    async def unmute_event(self,guild,user,author):
        role = await self.get_muted_role(guild)
        if role==None or not role in user.roles:
            return
        if author==guild.me:
            await user.remove_roles(role,reason="automatic unmute")
        else:
            await user.remove_roles(role,reason="unmuted by {}".format(author))
        log = str(await self.translate(guild.id,"logs","mute-off")).format(member=user)
        await self.bot.cogs["Events"].send_logs_per_server(guild,"mute",log,author)

    @commands.command(name="unmute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def unmute(self,ctx,user:discord.Member):
        """Unmute someone
        This will remove the role 'muted' for the targeted member"""
        role = await self.get_muted_role(ctx.guild)
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
            await self.unmute_event(ctx.guild,user,ctx.author)
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","unmute-1")).format(user))
            try:
                await ctx.message.delete()
            except:
                pass
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)



    @commands.command(name="ban")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_ban)
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
            self.bot.log.info("L'utilisateur {} a été banni du serveur {} pour la raison {}".format(user.id,ctx.guild.id,reason))
            await self.bot.cogs['Events'].add_event('ban')
            caseID = "'Unsaved'"
            if self.bot.database_online:
                CasesCog = self.bot.cogs['CasesCog']
                caseIDs = await CasesCog.get_ids()
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="ban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
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
    @commands.check(checks.can_ban)
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
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="unban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
            await ctx.send(str( await self.translate(ctx.guild.id,"modo","unban")).format(user))
            log = str(await self.translate(ctx.guild.id,"logs","unban")).format(member=user,reason=reason,case=caseID)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"ban",log,ctx.author)
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)

    @commands.command(name="softban")
    @commands.guild_only()
    @commands.check(checks.can_kick)
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
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="softban",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now()).create_id(caseIDs)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            try:
                await ctx.message.delete()
            except:
                pass
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
    @commands.check(checks.can_see_banlist)
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

    @emoji_group.command(name="clear")
    @commands.bot_has_permissions(manage_messages=True)
    async def emoji_clear(self,ctx,message:int):
        """Remove all reactions under a message"""
        try:
            msg = await ctx.channel.get_message(message)
        except discord.errors.NotFound:
            return await ctx.send(await self.translate(ctx.guild.id,"modo","react-clear"))
        except Exception as e:
            return await ctx.send(str(await self.translate(ctx.guild.id,"modo","pin-error")).format(e))
        await msg.clear_reactions()
        await ctx.message.delete()

    @emoji_group.command(name="list")
    async def emoji_list(self,ctx):
        """List every emoji of your server"""
        structure = await self.translate(ctx.guild.id,"modo","em-list")
        date = ctx.bot.cogs['TimeCog'].date
        lang = await self.translate(ctx.guild.id,"current_lang","current")
        priv = "**"+await self.translate(ctx.guild.id,"modo","em-private")+"**"
        title = str(await self.translate(ctx.guild.id,"modo","em-list-title")).format(ctx.guild.name)
        try:
            emotes = [structure.format(x,x.name,await date(x.created_at,lang,year=True,hour=False,digital=True),priv if len(x.roles)>0 else '') for x in ctx.guild.emojis if not x.animated]
            emotes += [structure.format(x,x.name,await date(x.created_at,lang,year=True,hour=False,digital=True),priv if len(x.roles)>0 else '') for x in ctx.guild.emojis if x.animated]
            nbr = len(emotes)
            fields = list()
            for i in range(0, nbr, 10):
                l = list()
                for x in emotes[i:i+10]:
                    l.append(x)
                fields.append({'name':"{}-{}".format(i+1,i+10 if i+10<nbr else nbr), 'value':"\n".join(l), 'inline':False})
            if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                embed = ctx.bot.cogs['EmbedCog'].Embed(title=title,fields=fields,color=self.bot.cogs["ServerCog"].embed_color).create_footer(ctx.author)
                await ctx.send(embed=embed.discord_embed())
            else:
                await ctx.send(await self.translate(ctx.guild.id,"fun","no-embed-perms"))
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)



    @commands.command(name="pin")
    @commands.check(checks.can_pin_msg)
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

    @commands.command(name='backup')
    @commands.guild_only()
    @commands.cooldown(2,120, commands.BucketType.guild)
    @commands.has_permissions(administrator=True)
    async def backup_server(self,ctx):
        """Make and send a backup of this server
        You will find there the configuration of your server, every general settings, the list of members with their roles, the list of categories and channels (with their permissions), emotes, and webhooks.
        Please note that audit logs, messages and invites are not used"""
        try:
            g = ctx.guild
            back = {'name':g.name,'id':g.id,'owner':g.owner.id,'voiceregion':str(g.region),'afk_timeout':g.afk_timeout,'afk_channel':g.afk_channel,'icon':g.icon_url,'verification_level':str(g.verification_level),'mfa_level':g.mfa_level,'explicit_content_filter':str(g.explicit_content_filter),'default_notifications':str(g.default_notifications),'created_at':int(g.created_at.timestamp())}
            back['system_channel'] = g.system_channel.id if g.system_channel!=None else None
            roles = list()
            for x in g.roles:
                roles.append({'id':x.id,'name':x.name,'color':str(x.colour),'position':x.position,'hoist':x.hoist,'mentionable':x.mentionable,'permissions':x.permissions.value})
            back['roles'] = roles
            categ = list()
            for x in g.by_category():
                c,l = x[0],x[1]
                if c==None:
                    temp = {'type':None}
                else:
                    temp = {'id':c.id,'name':c.name,'position':c.position,'is_nsfw':c.is_nsfw()}
                    perms = list()
                    for p in c.overwrites:
                        temp2 = {'id':p[0].id}
                        if isinstance(p[0],discord.Member):
                            temp2['type'] = 'member'
                        else:
                            temp2['type'] = 'role'
                        temp2['permissions'] = dict()
                        for x in iter(p[1]):
                            if x[1] != None:
                                temp2['permissions'][x[0]] = x[1]
                        perms.append(temp2)
                    temp['permissions_overwrites'] = perms
                temp['channels'] = list()
                for chan in l:
                    chan_js = {'id':chan.id,'name':chan.name,'position':chan.position}
                    if isinstance(chan,discord.TextChannel):
                        chan_js['type'] = 'TextChannel'
                        chan_js['description'] = chan.topic
                    elif isinstance(chan,discord.VoiceChannel):
                        chan_js['type'] = 'VoiceChannel'
                    else:
                        chan_js['type'] = str(type(chan))
                    perms = list()
                    for p in chan.overwrites:
                        temp2 = {'id':p[0].id}
                        if isinstance(p[0],discord.Member):
                            temp2['type'] = 'member'
                        else:
                            temp2['type'] = 'role'
                        temp2['permissions'] = dict()
                        for x in iter(p[1]):
                            if x[1] != None:
                                temp2['permissions'][x[0]] = x[1]
                        perms.append(temp2)
                    chan_js['permissions_overwrites'] = perms
                    temp['channels'].append(chan_js)
                categ.append(temp)
            back['categories'] = categ
            back['emojis'] = dict()
            for e in g.emojis:
                back['emojis'][e.name] = e.url
            try:
                banned = dict()
                for b in await g.bans():
                    banned[b.user.id] = b.reason
                back['banned_users'] = banned
            except:
                await ctx.send("msg-ban")
            try:
                webs = list()
                for w in await g.webhooks():
                    webs.append({'channel':w.channel_id,'name':w.name,'avatar':w.avatar_url,'url':w.url})
                back['webhooks'] = webs
            except:
                await ctx.send("msg-webhook")
            back['members'] = list()
            for memb in g.members:
                back['members'].append({'id':memb.id,'nickname':memb.nick,'bot':memb.bot,'roles':[x.id for x in memb.roles][1:]})
            js = json.dumps(back, sort_keys=True, indent=4)
            directory = 'backup/{}.json'.format(g.id)
            if not os.path.exists('backup/'):
                os.makedirs('backup/')
            with open(directory,'w',encoding='utf-8') as file:
                file.write(js)
            await ctx.send('Terminé !',file=discord.File(directory))
        except Exception as e:
            await ctx.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)


    async def configure_muted_role(self,guild):
        """Ajoute le rôle muted au serveur, avec les permissions nécessaires"""
        if not guild.me.guild_permissions.manage_roles:
            return False
        try:
            role = await guild.create_role(name="muted")
            for x in guild.by_category():
                count = 0
                category,channelslist = x[0],x[1]
                for channel in channelslist:
                    if len(channel.changed_roles)!=0 and channel.changed_roles!=category.changed_roles:
                        await channel.set_permissions(role,send_messages=False)
                        for r in channel.changed_roles:
                            if r.permissions.send_messages:
                                obj = channel.overwrites_for(r)
                                obj.send_messages=None
                                await channel.set_permissions(r,overwrite=obj)
                        count += 1
                await category.set_permissions(role,send_messages=False)
            return role
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,None)


def setup(bot):
    bot.add_cog(ModeratorCog(bot))