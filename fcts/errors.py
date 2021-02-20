import discord
import sys
import traceback
import random
import re
from discord.ext import commands
from utils import zbot, MyContext


class Errors(commands.Cog):
    """General cog for error management."""

    def __init__(self, bot: zbot):
        self.bot = bot
        self.file = "errors"

    async def search_err(self, form:list, sentence:str):
        for x in form:
            r = re.search(x,sentence)
            if r!= None:
                return r

    @commands.Cog.listener()
    async def on_command_error(self, ctx: MyContext, error: Exception):
        """The event triggered when an error is raised while invoking a command."""
        # This prevents any commands with local handlers being handled here in on_command_error.
        if hasattr(ctx.command, 'on_error'):
            return
        
        ignored = (commands.errors.CommandNotFound,commands.errors.CheckFailure,commands.errors.ConversionError,discord.errors.Forbidden)
        actually_not_ignored = (commands.errors.NoPrivateMessage)
        
        # Allows us to check for original exceptions raised and sent to CommandInvokeError.
        # If nothing is found. We keep the exception passed to on_command_error.
        error = getattr(error, 'original', error)

        # Anything in ignored will return and prevent anything happening.
        if isinstance(error, ignored) and not isinstance(error,actually_not_ignored):
            if self.bot.beta and ctx.guild:
                c = str(type(error)).replace("<class '",'').replace("'>",'')
                await ctx.send('`Ignored error:` [{}] {}'.format(c,error))
            return
        elif isinstance(error, commands.CommandError) and str(error) == "User doesn't have required roles":
            await ctx.send(await self.bot._(ctx.channel, 'errors', 'notrightroles'))
            return
        elif isinstance(error, commands.ExpectedClosingQuoteError):
            await ctx.send(await self.bot._(ctx.channel, 'errors', 'quoteserror'))
            return
        elif isinstance(error,commands.errors.CommandOnCooldown):
            if await self.bot.get_cog('Admin').check_if_admin(ctx):
                await ctx.reinvoke()
                return
            d = round(error.retry_after, 2 if error.retry_after < 60 else 0)
            await ctx.send(await self.bot._(ctx.channel,'errors','cooldown',d=round(error.retry_after,2)))
            return
        elif isinstance(error,(commands.BadArgument,commands.BadUnionArgument)):
            ALLOWED = discord.AllowedMentions(everyone=False, users=False, roles=False)
            raw_error = str(error)
            # Could not convert "limit" into int. OR Converting to "int" failed for parameter "number".
            r = re.search(r'Could not convert \"(?P<arg>[^\"]+)\" into (?P<type>[^.\n]+)',raw_error)
            if r is None:
                r = re.search(r'Converting to \"(?P<type>[^\"]+)\" failed for parameter \"(?P<arg>[^.\n]+)\"',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','badarguments',p=r.group('arg'),t=r.group('type')), allowed_mentions=ALLOWED)
            # zzz is not a recognised boolean option
            r = re.search(r'(?P<arg>[^\"]+) is not a recognised (?P<type>[^.\n]+) option',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','badarguments-2',p=r.group('arg'),t=r.group('type')), allowed_mentions=ALLOWED)
            # Member "Z_runner" not found
            r = re.search(r'(?<=Member \")(.+)(?=\" not found)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','membernotfound',m=r.group(1)), allowed_mentions=ALLOWED)
            # User "Z_runner" not found
            r = re.search(r'(?<=User \")(.+)(?=\" not found)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','usernotfound',u=r.group(1)), allowed_mentions=ALLOWED)
            # Role "Admin" not found
            r = re.search(r'(?<=Role \")(.+)(?=\" not found)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','rolenotfound',r=r.group(1)), allowed_mentions=ALLOWED)
            # Emoji ":shock:" not found
            r = re.search(r'(?<=Emoji \")(.+)(?=\" not found)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','emojinotfound',e=r.group(1)), allowed_mentions=ALLOWED)
             # Colour "blue" is invalid
            r = re.search(r'(?<=Colour \")(.+)(?=\" is invalid)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidcolor',c=r.group(1)), allowed_mentions=ALLOWED)
            # Channel "twitter" not found.
            r = re.search(r'(?<=Channel \")(.+)(?=\" not found)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','channotfound',c=r.group(1)), allowed_mentions=ALLOWED)
            # Message "1243" not found.
            r = re.search(r'(?<=Message \")(.+)(?=\" not found)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','msgnotfound',msg=r.group(1)), allowed_mentions=ALLOWED)
            # Too many text channels
            if raw_error=='Too many text channels':
                return await ctx.send(await self.bot._(ctx.channel,'errors','toomanytxtchan'), allowed_mentions=ALLOWED)
            # Invalid duration: 2d
            r = re.search(r'Invalid duration: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','duration',d=r.group(1)), allowed_mentions=ALLOWED)
            # Invalid invite: nope
            r = re.search(r'Invalid invite: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidinvite',i=r.group(1)), allowed_mentions=ALLOWED)
            # Invalid guild: test
            r = re.search(r'Invalid guild: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidguild',g=r.group(1)), allowed_mentions=ALLOWED)
            # Invalid url: nou
            r = re.search(r'Invalid url: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidurl',u=r.group(1)), allowed_mentions=ALLOWED)
            # Invalid leaderboard type: lol
            r = re.search(r'Invalid leaderboard type: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidleaderboard'), allowed_mentions=ALLOWED)
            # Invalid ISBN: lol
            r = re.search(r'Invalid ISBN: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidisbn'), allowed_mentions=ALLOWED)
            # Invalid emoji: lmao
            r = re.search(r'Invalid emoji: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidemoji'), allowed_mentions=ALLOWED)
            # Invalid message ID: 007
            r = re.search(r'Invalid message ID: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidmsgid'), allowed_mentions=ALLOWED)
            # Invalid card style: aqua
            r = re.search(r'Invalid card style: (\S+)',raw_error)
            if r is not None:
                return await ctx.send(await self.bot._(ctx.channel,'errors','invalidcardstyle', s=r.group(1)), allowed_mentions=ALLOWED)
            self.bot.log.warn('Unknown error type -',error)
        elif isinstance(error,commands.errors.MissingRequiredArgument):
            await ctx.send(await self.bot._(ctx.channel,'errors','missingargument',a=error.param.name,e=random.choice([':eyes:','',':confused:',':thinking:',''])))
            return
        elif isinstance(error,commands.errors.DisabledCommand):
            await ctx.send(await self.bot._(ctx.channel,'errors','disabled',c=ctx.invoked_with))
            return
        elif isinstance(error,commands.errors.NoPrivateMessage):
            await ctx.send(await self.bot._(ctx.channel,'errors','DM'))
            return
        else:
            try:
                await ctx.send(await self.bot._(ctx.channel,'errors','unknown'))
            except Exception as newerror:
                self.bot.log.info("[on_cmd_error] Can't send error on channel {}: {}".format(ctx.channel.id,newerror))
        # All other Errors not returned come here... And we can just print the default TraceBack.
        self.bot.log.warning('Ignoring exception in command {}:'.format(
            ctx.message.content), exc_info=(type(error), error, error.__traceback__))      
        await self.on_error(error,ctx)

    @commands.Cog.listener()
    async def on_error(self, error: Exception, ctx=None):
        try:
            if isinstance(ctx, discord.Message):
                ctx = await self.bot.get_context(ctx)
            tr = traceback.format_exception(type(error), error, error.__traceback__)
            msg = "```python\n{}\n```".format(" ".join(tr))
            if ctx is None:
                await self.senf_err_msg(f"Internal Error\n{msg}")
            elif ctx.guild is None:
                await self.senf_err_msg(f"DM | {ctx.channel.recipient.name}\n{msg}")
            elif ctx.channel.id == 625319425465384960:
                return await ctx.send(ctx.guild.name+" | "+ctx.channel.name+"\n"+msg)
            else:
                await self.senf_err_msg(ctx.guild.name+" | "+ctx.channel.name+"\n"+msg)
        except Exception as e:
            self.bot.log.warn(f"[on_error] {e}", exc_info=True)
        try:
            traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        except Exception as e:
            self.bot.log.warning(f"[on_error] {e}", exc_info=True)


    async def senf_err_msg(self, msg: str):
        """Envoie un message dans le salon d'erreur"""
        salon = self.bot.get_channel(626039503714254858)
        if salon is None:
            return False
        if len(msg) > 2000:
            if msg.endswith("```"):
                msg = msg[:1997]+"```"
            else:
                msg = msg[:2000]
        await salon.send(msg)
        return True


def setup(bot):
    bot.add_cog(Errors(bot))
