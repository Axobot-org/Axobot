import discord, sys, traceback, random, re
from discord.ext import commands

class ErrorsCog:
    """General cog for error management."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "errors"
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
        
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr

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
        if isinstance(error, ignored):
            return
        elif isinstance(error,commands.CommandOnCooldown):
            await ctx.send(str(await self.translate(ctx.guild,'errors','cooldown')).format(round(error.retry_after,2)))
            return
        elif isinstance(error,(commands.BadArgument,commands.BadUnionArgument)):
            args = error.args[0].split('\"')
            if len(args)!=4:
                r = re.search(r'Could not convert \"([^\"]+)\" into ([^.]+)',str(error))
                if r == None:
                    r = re.search(r'Member \"([^\"]+)\" not found',str(error))
                    if r == None:
                        r = re.search(r'User \"([^\"]+)\" not found',str(error))
                        if r==None:
                            print('errors -',error)
                            return
                        else:
                            await ctx.send(str(await self.translate(ctx.guild,'errors','usernotfound')).format(r.group(1)))
                    else:
                        await ctx.send(str(await self.translate(ctx.guild,'errors','membernotfound')).format(r.group(1)))
                else:    
                    args = [None,r.group(2),None,r.group(1)]
            await ctx.send(str(await self.translate(ctx.guild,'errors','badarguments')).format(c=args))
            return
        elif isinstance(error,commands.MissingRequiredArgument):
            await ctx.send(str(await self.translate(ctx.guild,'errors','missingargument')).format(error.param.name,random.choice([':eyes:','',':confused:',':thinking:',''])))
            return
        elif isinstance(error,commands.DisabledCommand):
            await ctx.send(str(await self.translate(ctx.guild,'errors','disabled')).format(ctx.invoked_with))
            return
        else:
            try:
                await ctx.send("`ERROR:` "+str(error))
            except:
                print("[on_cmd_error] Can't send error on channel {}".format(ctx.channel.id))
        # All other Errors not returned come here... And we can just print the default TraceBack.
        print('Ignoring exception in command {}:'.format(ctx.command), file=sys.stderr)
        #traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await self.on_error(error,ctx)

    async def on_command_error(self, ctx, error):
        await self.on_cmd_error(ctx,error)

    async def on_error(self,error_msg,ctx):
        try:
            sysexc = sys.exc_info()
            s = str(sysexc[0]).split("<class '")
            if len(s)>1:
                s = s[1].split("'>")[0]
            else:
                s = "None"
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
            print("[on_error]",e)
        try:
            if sys.exc_info()[0] != None:
                S = str(sys.exc_info()[0]).split("<class '")[1].split("'>")[0]+' : '+str(sys.exc_info()[1])
            else:
                S = "None"
            print("""Traceback (most recent call last):
{T} {S}
""".format(T=" ".join(traceback.format_tb(sys.exc_info()[2])),S=S))
        except Exception as e:
            print("[on_error]",e)


    async def senf_err_msg(self,msg):
        """Envoie un message dans le salon d'erreur"""
        salon = self.bot.get_channel(491370492561981474)
        if salon == None:
            return False
        await salon.send(msg)
        return True


def setup(bot):
    bot.add_cog(ErrorsCog(bot))
