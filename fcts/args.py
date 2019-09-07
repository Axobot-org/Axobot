import discord, re, string, typing
from discord.ext import commands
from urllib.parse import urlparse

class tempdelta(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument) -> int:
        d = 0
        found = False
        # ctx.invoked_with
        for x in [('y',86400*365),('d',86400),('h',3600),('m',60)]:
            r = re.search(r'(\d+)'+x[0],argument)
            if r!= None:
                d += int(r.group(1))*x[1]
                found = True
        if not found:
            raise commands.errors.BadArgument('Invalid duration: '+argument)
        return d

class user(commands.converter.UserConverter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument) -> discord.User:
        if argument.isnumeric():
            if ctx.guild != None:
                res = ctx.guild.get_member(int(argument))
            if res == None:
                res = ctx.bot.get_user(int(argument))
            if res == None:
                try:
                    res = await ctx.bot.fetch_user(int(argument))
                except:
                    pass
            return res
        try:
            return await commands.MemberConverter().convert(ctx,argument)
        except:
            return await commands.UserConverter().convert(ctx,argument)

class infoType(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument) -> str:
        if argument in ['member','role','user','textchannel','channel','invite','voicechannel','emoji','category','guild','server']:
            return argument
        else:
            raise commands.errors.BadArgument('Invalid type: '+argument)

class cardStyle(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument) -> str:
        if argument in await ctx.bot.cogs['UtilitiesCog'].allowed_card_styles(ctx.author):
            return argument
        else:
            raise commands.errors.BadArgument('Invalid card style: '+argument)

class LeaderboardType(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument) -> str:
        if argument in ['server','guild','serveur','local']:
            if ctx.guild==None:
                raise commands.errors.BadArgument('Cannot use {} leaderboard type outside a server'.format(argument))
            return 'guild'
        elif argument in ['all','global','tout']:
            return 'global'
        raise commands.errors.BadArgument('Invalid leaderboard type: {}'.format(argument))

class Invite(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.context,argument) -> typing.Union[str,int]:
        answer = None
        r = re.search(r'https://discordapp\.com/oauth2/authorize\?client_id=(\d{18})&scope=bot',argument)
        if r==None:
            r = re.search(r'(?:discord\.gg|discordapp\.com/invite)/([^\s/]+)',argument)
            if r!=None:
                answer = r.group(1)
        else:
            answer = int(r.group(1))
        if r==None or answer==None:
            raise commands.errors.BadArgument('Invalid invite: '+argument)
        return answer


class Guild(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument) -> discord.Guild:
        if argument.isnumeric():
            res = ctx.bot.get_guild(int(argument))
            if res != None:
                return res
        raise commands.errors.BadArgument('Invalid guild: '+argument)


class url(commands.Converter):
    def __init__(self):
        pass
    
    class Url:
        def __init__(self,regex_exp:re.Match):
            self.domain = regex_exp.group('domain')
            self.path = regex_exp.group('path')
            self.is_https = regex_exp.group('https') == 'https'
            self.url = regex_exp.group(0)
        
        def __str__(self):
            return f"Url(url='{self.url}', domain='{self.domain}', path='{self.path}', is_https={self.is_https})"

    async def convert(self,ctx:commands.Context,argument) -> Url:
        r = re.search(r'(?P<https>https?)://(?:www\.)?(?P<domain>[^/\s]+)(?:/(?P<path>[\S]+))?', argument)
        if r==None:
            raise commands.errors.BadArgument('Invalid url: '+argument)
        return self.Url(r)

class anyEmoji(commands.Converter):
    def __init__(self):
        pass

    async def convert(self,ctx:commands.Context,argument) -> typing.Union[str,discord.Emoji]:
        r = re.search(r'<a?:[^:]+:(\d+)>', argument)
        if r==None:
            if all([x not in string.printable for x in argument]):
                return argument
        else:
            try:
                return await commands.EmojiConverter().convert(ctx,r.group(1))
            except Exception as e:
                print(e)
                return r.group(1)
        print(len(argument))
        raise commands.errors.BadArgument('Invalid emoji: '+argument)

class guildMessage(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx:commands.Context,argument:str) -> discord.Message:
        if len(argument)!=18 or not argument.isnumeric():
            raise commands.errors.BadArgument('Invalid message ID: '+argument)
        if ctx.guild==None:
            channels = [ctx.channel]
        else:
            me = ctx.guild.me
            channels = [ctx.channel] + [x for x in ctx.guild.text_channels if x.id!=ctx.channel.id and x.permissions_for(me).read_message_history and x.permissions_for(me).read_messages]
            if len(channels)>50:
                raise commands.errors.BadArgument('Too many text channels')
        for channel in channels:
            try:
                msg = await channel.fetch_message(int(argument))
            except:
                pass
            else:
                return msg
        raise commands.errors.BadArgument('Message "{}" not found.'.format(argument))

class arguments(commands.Converter):
    def __init__(self):
        pass

    async def convert(self,ctx:commands.Context,argument:str) -> dict:
        answer = dict()
        for result in re.finditer(r'(\w+) ?= ?"((?:[^"\\]*|\\")*)"',argument):
            answer[result.group(1)] = result.group(2).replace('\\"','"')
        return answer

class Color(commands.Converter):
    def __init__(self):
        pass

    async def convert(self,ctx:commands.Context,argument:str) -> int:
        if argument.startswith('#') and len(argument)%3==1:
            arg = argument[1:]
            rgb = [int(arg[i:i+2], 16) for i in range(0,len(arg),len(arg)//3)]
            return discord.Colour(0).from_rgb(rgb[0], rgb[1], rgb[2]).value
        elif argument.isnumeric():
            return int(argument)
        else:
            return None
        