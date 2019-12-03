import discord, mysql.connector, importlib, datetime, random
from discord.ext import commands

from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)


class TimedCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = 'timed'
        self.table = 'timed'
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr


    @commands.command(name="tempmute")
    @commands.cooldown(5,20, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.can_mute)
    async def tempmute(self,ctx,user:discord.Member,time:commands.Greedy[args.tempdelta],*,reason="Unspecified"):
        """Mute a member for a defined duration
The bot can currently have up to 30 sec of latency. If it has more, check if you didn't remove the "Manage Roles" permission.
Durations : 
`XXm` : XX minutes
`XXh` : XX hours
`XXd` : XX days
Example: tempmute @someone 1d 3h Reason is becuz he's a bad guy
"""
        duration = sum(time)
        if duration==0:
            await ctx.send(time)
            try:
                raise commands.errors.BadArgument('Invalid duration: 0s')
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
                return
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