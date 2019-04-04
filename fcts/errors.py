import discord, sys, traceback, random, re
from discord.ext import commands

class ErrorsCog(commands.Cog):
    """General cog for error management."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "errors"
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr

    async def search_err(self,form:list,sentence:str):
        for x in form:
            r = re.search(x,sentence)
            if r!= None:
                return r

    async def on_cmd_error(self,ctx,error):
        """The event triggered when an error is raised while invoking a command."""
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return
        
        ignored = (commands.CommandNotFound,commands.CheckFailure,commands.ConversionError,commands.BotMissingPermissions,discord.errors.Forbidden)
        
        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored) and not self.bot.beta:
            return
        elif isinstance(error,ignored):
            return await ctx.send("`ERROR:` {}".format(error))
        elif isinstance(error,commands.CommandOnCooldown):
            if await self.bot.cogs['AdminCog'].check_if_admin(ctx):
                await ctx.reinvoke()
                return
            await ctx.send(str(await self.translate(ctx.channel,'errors','cooldown')).format(round(error.retry_after,2)))
            return
        elif isinstance(error,(commands.BadArgument,commands.BadUnionArgument)):
            # Could not convert "limit" into int. OR Converting to "int" failed for parameter "number".
            r = re.search(r'Could not convert \"(?P<arg>[^\"]+)\" into (?P<type>[^.\n]+)',str(error))
            if r==None:
                r = re.search(r'Converting to \"(?P<type>[^\"]+)\" failed for parameter \"(?P<arg>[^.\n]+)\"',str(error))
            if r!=None:
                return await ctx.send(str(await self.translate(ctx.channel,'errors','badarguments')).format(r.group('arg'),r.group('type')))
            # Member "Z_runner" not found
            r = re.search(r'Member \"([^\"]+)\" not found',str(error))
            if r!=None:
                return await ctx.send(str(await self.translate(ctx.channel,'errors','membernotfound')).format(r.group(1)))
            # User "Z_runner" not found
            r = re.search(r'User \"([^\"]+)\" not found',str(error))
            if r!=None:
                return await ctx.send(str(await self.translate(ctx.channel,'errors','usernotfound')).format(r.group(1)))
            # Role "Admin" not found
            r = re.search(r'Role \"([^\"]+)\" not found',str(error))
            if r!=None:
                return await ctx.send(str(await self.translate(ctx.channel,'errors','rolenotfound')).format(r.group(1)))
             # Role "Admin" not found
            r = re.search(r'Colour \"([^\"]+)\" is invalid',str(error))
            if r!=None:
                return await ctx.send(str(await self.translate(ctx.channel,'errors','invalidcolor')).format(r.group(1)))
            # Invalid duration: 2d
            r = re.search(r'Invalid duration: ([^\" ]+)',str(error))
            if r != None:
                return await ctx.send(str(await self.translate(ctx.channel,'errors','duration')).format(r.group(1)))
            print('errors -',error)
        elif isinstance(error,commands.MissingRequiredArgument):
            await ctx.send(str(await self.translate(ctx.channel,'errors','missingargument')).format(error.param.name,random.choice([':eyes:','',':confused:',':thinking:',''])))
            return
        elif isinstance(error,commands.DisabledCommand):
            await ctx.send(str(await self.translate(ctx.channel,'errors','disabled')).format(ctx.invoked_with))
            return
        else:
            try:
                await ctx.send("`ERROR:` "+str(error))
            except:
                self.bot.log.info("[on_cmd_error] Can't send error on channel {}".format(ctx.channel.id))
        # All other Errors not returned come here... And we can just print the default TraceBack.
        self.bot.log.warning('Ignoring exception in command {}:'.format(ctx.command), exc_info=True)
        await self.on_error(error,ctx)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await self.on_cmd_error(ctx,error)

    @commands.Cog.listener()
    async def on_error(self,error_msg,ctx):
        try:
            sysexc = sys.exc_info()
            s = str(sysexc[0]).split("<class '")
            if len(s)>1:
                s = s[1].split("'>")[0]
            else:
                s = str(error_msg)
            msg = """```python
Traceback (most recent call last):
{T} {S}
```""".format(T=" ".join(traceback.format_tb(sysexc[2])),S=s+' : '+str(sysexc[1]))
            if ctx == None:
                await self.senf_err_msg("Internal Error\n"+msg)
            elif ctx.guild == None:
                await self.senf_err_msg("DM | "+ctx.channel.recipient.name+"\n"+msg)
            else:
                await self.senf_err_msg(ctx.guild.name+" | "+ctx.channel.name+"\n"+msg)
        except Exception as e:
            self.bot.log.warn("[on_error]",e)
        try:
            if sys.exc_info()[0] != None:
                S = str(sys.exc_info()[0]).split("<class '")[1].split("'>")[0]+' : '+str(sys.exc_info()[1])
            else:
                S = "None"
            print("""Traceback (most recent call last):
{T} {S}
""".format(T=" ".join(traceback.format_tb(sys.exc_info()[2])),S=S))
        except Exception as e:
            self.bot.log.warn("[on_error]",e)


    async def senf_err_msg(self,msg):
        """Envoie un message dans le salon d'erreur"""
        salon = self.bot.get_channel(491370492561981474)
        if salon == None:
            return False
        await salon.send(msg)
        return True


def setup(bot):
    bot.add_cog(ErrorsCog(bot))
