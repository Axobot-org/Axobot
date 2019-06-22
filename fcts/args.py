import discord, re
from discord.ext import commands

class tempdelta(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx,argument):
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
    
    async def convert(self,ctx,argument):
        if argument.isnumeric():
            res = ctx.bot.get_user(int(argument))
            if res == None:
                try:
                    res = await ctx.bot.fetch_user(int(argument))
                except:
                    pass
            return res
        return await commands.UserConverter().convert(ctx,argument)

class infoType(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx,argument):
        if argument in ['member','role','user','textchannel','channel','invite','voicechannel','emoji','category','guild','server']:
            return argument
        else:
            raise commands.errors.BadArgument('Invalid type: '+argument)

class cardStyle(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx,argument):
        if argument in await ctx.bot.cogs['UtilitiesCog'].allowed_card_styles(ctx.author):
            return argument
        else:
            raise commands.errors.BadArgument('Invalid card style: '+argument)

class LeaderboardType(commands.Converter):
    def __init__(self):
        pass
    
    async def convert(self,ctx,argument):
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
    
    async def convert(self,ctx:commands.context,argument):
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
    
    async def convert(self,ctx:commands.context,argument):
        if argument.isnumeric():
            res = ctx.bot.get_guild(int(argument))
            if res != None:
                return res
        raise commands.errors.BadArgument('Invalid guild: '+argument)