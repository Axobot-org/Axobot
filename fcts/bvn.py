import discord, datetime
from discord.ext import commands

class WelcomerCog(commands.Cog):
    """Cog which manages the departure and arrival of members in the servers"""
    
    def __init__(self,bot):
        self.bot = bot
        self.file = "bvn"
        self.no_message = [392766377078816789,504269440872087564,552273019020771358]
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
    

    async def new_member(self,member):
        """Fonction principale appelée lorsqu'un membre rejoint un serveur"""
        # await self.send_log(member,"welcome")
        if self.bot.database_online:
            await self.bot.cogs["ServerCog"].update_memberChannel(member.guild)
            await self.send_msg(member,"welcome")
            self.bot.loop.create_task(self.give_roles(member))
            await self.give_roles_back(member)
        if member.guild.id==356067272730607628:
            await self.check_owner_server(member)
            await self.check_support(member)
            await self.check_contributor(member)
        
        
    
    async def bye_member(self,member):
        """Fonction principale appelée lorsqu'un membre quitte un serveur"""
        # await self.send_log(member,"leave")
        if self.bot.database_online:
            await self.bot.cogs["ServerCog"].update_memberChannel(member.guild)
            await self.send_msg(member,"leave")
            await self.bot.cogs['Events'].check_user_left(member)


    async def send_msg(self,member,Type):
        msg = await self.bot.cogs['ServerCog'].find_staff(member.guild.id,Type)
        if await self.raid_check(member) or member.id in self.no_message:
            return
        if await self.bot.cogs['UtilitiesCog'].check_any_link(member.name) != None:
            return
        if msg not in ['',None]:
            ch = await self.bot.cogs['ServerCog'].find_staff(member.guild.id,'welcome_channel')
            if ch is None:
                return
            ch = ch.split(';')
            msg = await self.bot.cogs['UtilitiesCog'].clear_msg(msg,ctx=None)
            for channel in ch:
                if not channel.isnumeric():
                    continue
                channel = member.guild.get_channel(int(channel))
                if channel is None:
                    continue
                botormember = await self.translate(member.guild,"keywords",'bot' if member.bot else 'member')
                try:
                    msg = msg.format_map(self.bot.SafeDict(user=member.mention if Type=='welcome' else member.name,server=member.guild.name,owner=member.guild.owner.name,member_count=len(member.guild.members),type=botormember))
                    msg = await self.bot.cogs["UtilitiesCog"].clear_msg(msg,everyone=False)
                    await channel.send(msg)
                except Exception as e:
                    await self.bot.cogs["ErrorsCog"].on_error(e,None)

    async def check_owner_server(self,member):
        """Vérifie si un nouvel arrivant est un propriétaire de serveur"""
        servers = [x for x in self.bot.guilds if x.owner==member and len(x.members)>10]
        if len(servers)>0:
            role = member.guild.get_role(486905171738361876)
            if role==None:
                self.bot.log.warn('[check_owner_server] Owner role not found')
                return
            if role not in member.roles:
                await member.add_roles(role,reason="This user support me")
            
    async def check_support(self,member):
        """Vérifie si un nouvel arrivant fait partie du support"""
        if await self.bot.cogs['UtilitiesCog'].is_support(member):
            role = member.guild.get_role(412340503229497361)
            if role!=None:
                await member.add_roles(role)
            else:
                self.bot.log.warn('[check_support] Support role not found')

    async def check_contributor(self,member):
        """Vérifie si un nouvel arrivant est un contributeur"""
        if await self.bot.cogs['UtilitiesCog'].is_contributor(member):
            role = member.guild.get_role(552428810562437126)
            if role!=None:
                await member.add_roles(role)
            else:
                self.bot.log.warn('[check_contributor] Contributor role not found')

    async def give_roles_back(self,member):
        """Give roles rewards/muted role to new users"""
        used_xp_type = await self.bot.cogs['ServerCog'].find_staff(member.guild.id,'xp_type')
        xp = await self.bot.cogs['XPCog'].bdd_get_xp(member.id, None if used_xp_type==0 else member.guild.id)
        if xp != None and len(xp) == 1:
            await self.bot.cogs['XPCog'].give_rr(member,(await self.bot.cogs['XPCog'].calc_level(xp[0]['xp'],used_xp_type))[0],await self.bot.cogs['XPCog'].rr_list_role(member.guild.id))


    async def kick(self,member,reason):
        try:
            await member.guild.kick(member,reason=reason)
        except:
            pass
    
    async def ban(self,member,reason):
        try:
            await member.guild.ban(member,reason=reason)
        except:
            pass

    async def raid_check(self,member):
        if member.guild is None:
            return False
        level = str(await self.bot.cogs['ServerCog'].find_staff(member.guild.id,"anti_raid"))
        if not level.isnumeric() or member.guild.channels[0].permissions_for(member.guild.me).kick_members == False:
            return
        c = False
        level = int(level)
        can_ban = member.guild.get_member(self.bot.user.id).guild_permissions.ban_members
        if level == 0:
            return c
        if level >= 1:
            if await self.bot.cogs['UtilitiesCog'].check_discord_invite(member.name) != None:
                await self.kick(member,await self.translate(member.guild.id,"logs","d-invite"))
                c = True
        if level >= 2:
            if (datetime.datetime.utcnow() - member.created_at).seconds <= 5*60:
                await self.kick(member,await self.translate(member.guild.id,"logs","d-young"))
                c = True
        if level >= 3 and can_ban:
            if await self.bot.cogs['UtilitiesCog'].check_discord_invite(member.name) != None:
                await self.ban(member,await self.translate(member.guild.id,"logs","d-invite"))
                c = True
            if (datetime.datetime.utcnow() - member.created_at).seconds <= 30*60:
                await self.kick(member,await self.translate(member.guild.id,"logs","d-young"))
                c = True
        if level >= 4:
            if (datetime.datetime.utcnow() - member.created_at).seconds <= 30*60:
                await self.kick(member,await self.translate(member.guild.id,"logs","d-young"))
                c = True
            if (datetime.datetime.utcnow() - member.created_at).seconds <= 120*60 and can_ban:
                await self.ban(member,await self.translate(member.guild.id,"logs","d-young"))
                c = True
        return c


    async def give_roles(self,member):
        """Give new roles to new users"""
        try:
            roles = str(await self.bot.cogs['ServerCog'].find_staff(member.guild.id,"welcome_roles"))
            for r in roles.split(";"):
                if (not r.isnumeric()) or len(r)==0:
                    continue
                role = member.guild.get_role(int(r))
                if role != None:
                    try:
                        await member.add_roles(role,reason=await self.translate(member.guild.id,"logs","d-welcome_roles"))
                    except discord.errors.Forbidden:
                        await self.bot.cogs['Events'].send_logs_per_server(member.guild,'error',await self.translate(member.guild,'bvn','error-give-roles',r=role.name,u=str(member)), member.guild.me)
        except discord.errors.NotFound:
            pass
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)


    async def send_log(self,member,Type):
        """Send a log to the logging channel"""
        if member.id in self.no_message or member.id==self.bot.user.id:
            return
        if member.guild.id in self.bot.cogs['ReloadsCog'].ignored_guilds:
            return
        try:
            t = "Bot" if member.bot else "Member"
            if Type == "welcome":
                desc = "{} {} ({}) joined {} ({})".format(t,member,member.id,member.guild.name,member.guild.id)
            else:
                desc = "{} {} ({}) left {} ({})".format(t,member,member.id,member.guild.name,member.guild.id)
            emb = self.bot.cogs["EmbedCog"].Embed(desc=desc,color=16098851).update_timestamp().set_author(self.bot.user)
            await self.bot.cogs["EmbedCog"].send([emb],url='members')
            self.bot.log.info(desc)
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,None)

def setup(bot):
    bot.add_cog(WelcomerCog(bot))