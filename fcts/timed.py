import discord, mysql.connector, importlib, datetime, random
from discord.ext import commands

from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)


class TimedCog:

    def __init__(self,bot):
        self.bot = bot
        self.file = 'timed'
        self.table = 'timed'
        self.usable_actions = ['mute','ban']
        try:
            self.connect = bot.cogs['ServerCog'].connect
        except:
            pass
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    async def on_ready(self):
        self.connect = self.bot.cogs['ServerCog'].connect
        self.translate = self.bot.cogs['LangCog'].tr


    async def add_action(self,guild,user,action,begin,duration):
        """add a new server to the db"""
        if not all([type(x)==int for x in (user,guild,begin,duration)]):
            raise ValueError
        cnx = self.connect()
        cursor = cnx.cursor()
        query = ("INSERT INTO `{}` (`guild`,`user`,`action`,`begin`,`duration`) VALUES ('{}','{}','{}','{}','{}')".format(self.table,guild,user,action,begin,duration))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True

    async def get_infos(self,columns=[],criters=["ID>1"],relation="AND",Dict=True):
        """return every options of a server"""
        await self.bot.wait_until_ready()
        if type(columns)!=list or type(criters)!=list:
            raise ValueError
        cnx = self.connect()
        cursor = cnx.cursor(dictionary = Dict)
        if columns == []:
            cl = "*"
        else:
            cl = "`"+"`,`".join(columns)+"`"
        relation = " "+relation+" "
        query = ("SELECT {} FROM `{}` WHERE {}".format(cl,self.table,relation.join(criters)))
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cnx.close()
        return liste
    
    async def delete_server(self,user,guild,action):
        """remove a server from the db"""
        if type(user)!=int or type(guild)!=int:
            raise ValueError
        cnx = self.connect()
        cursor = cnx.cursor()
        query = ("DELETE FROM `{}` WHERE `user`='{}' AND `guild`='{}' AND `action`='{}'".format(self.table,user,guild,action))
        cursor.execute(query)
        cnx.commit()
        cnx.close()
        return True


    @commands.command(name="tempmute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def test(self,ctx,user:discord.Member,time:commands.Greedy[args.tempdelta],*,reason="Unspecified"):
        duration = sum(time)
        f_duration = await self.bot.cogs['TimeCog'].time_delta(duration,lang='en',form='temp',precision=0)
        try:
            if self.bot.database_online and await self.bot.cogs["ServerCog"].staff_finder(user,"mute") or user==ctx.guild.me:
                await ctx.send(str(await self.translate(ctx.guild.id,"modo","staff-mute"))+random.choice([':confused:',':upside_down:',self.bot.cogs['EmojiCog'].customEmojis['wat'],':no_mouth:',self.bot.cogs['EmojiCog'].customEmojis['owo'],':thinking:',]))
                return
            elif not self.bot.database_online and ctx.channel.permissions_for(user).manage_roles:
                return await ctx.send(await self.translate(ctx.guild.id,"modo","staff-warn"))
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            return
        role = await self.bot.cogs['ModeratorCog'].get_muted_role(ctx.guild)
        if role in user.roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","already-mute"))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.translate(ctx.guild.id,"modo","cant-mute"))
            return
        if role == None:
            role = await self.bot.cogs['ModeratorCog'].configure_muted_role(ctx.guild)
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
                case = CasesCog.Case(bot=self.bot,guildID=ctx.guild.id,memberID=user.id,Type="tempmute",ModID=ctx.author.id,Reason=reason,date=datetime.datetime.now(),duration=duration).create_id(caseIDs)
                await self.bot.cogs['Events'].add_task(ctx.guild.id,user.id,'mute',duration)
                try:
                    await CasesCog.add_case(case)
                    caseID = case.id
                except Exception as e:
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
            await user.add_roles(role,reason=reason)
            await ctx.send(str(await self.translate(ctx.guild.id,"modo","tempmute-1")).format(user,reason,f_duration))
            log = str(await self.translate(ctx.guild.id,"logs","tempmute-on")).format(member=user,reason=reason,case=caseID,duration=f_duration)
            await self.bot.cogs["Events"].send_logs_per_server(ctx.guild,"mute",log,ctx.author)
            if ctx.channel.permissions_for(ctx.guild.me).manage_messages:
                await ctx.message.delete()
        except Exception as e:
            await ctx.send(await self.translate(ctx.guild.id,"modo","error"))
            await self.bot.cogs['ErrorsCog'].on_error(e,ctx)



def setup(bot):
    bot.add_cog(TimedCog(bot))