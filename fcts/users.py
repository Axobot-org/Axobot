import discord, importlib, typing, datetime, json, time
from discord.ext import commands

from fcts import args, checks
importlib.reload(args)
importlib.reload(checks)

class UsersCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = 'users'
        self.table = 'timed'
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr

    @commands.group(name='profile')
    async def profile_main(self,ctx):
        """Get and change info about yourself"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['profile'])
    
    @profile_main.command(name='card')
    @commands.check(checks.database_connected)
    async def profile_card(self,ctx,style:typing.Optional[args.cardStyle]=None):
        """Change your xp card style"""
        if style==None and len(ctx.view.buffer.split(' '))>2:
            if ctx.view.buffer.split(' ')[2]=='list':
                await ctx.send(str(await self.translate(ctx.channel,'users','list-cards')).format(', '.join(await ctx.bot.cogs['UtilitiesCog'].allowed_card_styles(ctx.author))))
            else:
                await ctx.send(str(await self.translate(ctx.channel,'users','invalid-card')).format(', '.join(await ctx.bot.cogs['UtilitiesCog'].allowed_card_styles(ctx.author))))
            return
        elif style==None:
            if ctx.channel.permissions_for(ctx.me).attach_files:
                style = await self.bot.cogs['UtilitiesCog'].get_xp_style(ctx.author)
                txts = [await self.translate(ctx.channel,'xp','card-level'), await self.translate(ctx.channel,'xp','card-rank')]
                desc = await self.translate(ctx.channel,'users','card-desc')
                await ctx.send(desc,file=await self.bot.cogs['XPCog'].create_card(ctx.author,style,25,[1,0],txts,force_static=True))
            else:
                await ctx.send(await self.translate(ctx.channel,'users','missing-attach-files'))
        else:
            if await ctx.bot.cogs['UtilitiesCog'].change_db_userinfo(ctx.author.id,'xp_style',style):
                await ctx.send(str(await self.translate(ctx.channel,'users','changed-0')).format(style))
                last_update = self.get_last_rankcard_update(ctx.author.id)
                if last_update==None:
                    await self.bot.cogs["UtilitiesCog"].add_user_eventPoint(ctx.author.id,15)
                elif last_update < time.time()-86400:
                    await self.bot.cogs["UtilitiesCog"].add_user_eventPoint(ctx.author.id,2)
                self.set_last_rankcard_update(ctx.author.id)
            else:
                await ctx.send(await self.translate(ctx.channel,'users','changed-1'))

    @profile_main.command(name='animated_card')
    @commands.check(checks.database_connected)
    async def set_animated_card(self,ctx,allowed:bool=None):
        """DEPRECATED COMMAND
        Allow your rank card to be animated or not 
        This is only used if you have an animated pfp"""
        if allowed==None:
            allowed = await self.bot.cogs['UtilitiesCog'].get_db_userinfo(['animated_card'],[f'`userID`={ctx.author.id}'])
            if allowed==None:
                allowed = False
            else:
                allowed = allowed['animated_card']
            if allowed:
                await ctx.send(await self.translate(ctx.channel,'users','allow_animated_true'))
            else:
                await ctx.send(await self.translate(ctx.channel,'users','allow_animated_false'))
        else:
            if await self.bot.cogs['UtilitiesCog'].change_db_userinfo(ctx.author.id,'animated_card',allowed):
                await ctx.send(str(await self.translate(ctx.channel,'users','allow_animated_success')).format(allowed))
            else:
                await ctx.send(await self.translate(ctx.channel,'users','changed-1'))
    
    @profile_main.command(name='auto_unafk')
    @commands.check(checks.database_connected)
    async def set_auto_unafk(self,ctx,value:bool=None):
        """DEPRECATED COMMAND
        Automatically remove your AFK mode
        This system will remove your AFK tag as soon as you send a message, but only in the server you sent it"""
        if value==None:
            value = await self.bot.cogs['UtilitiesCog'].get_db_userinfo(['auto_unafk'],[f'`userID`={ctx.author.id}'])
            if value==None:
                value = False
            else:
                value = value['auto_unafk']
            if value:
                await ctx.send(await self.translate(ctx.channel,'users','allow_auto_unafk_true'))
            else:
                await ctx.send(await self.translate(ctx.channel,'users','allow_auto_unafk_false'))
        else:
            if await self.bot.cogs['UtilitiesCog'].change_db_userinfo(ctx.author.id,'auto_unafk',value):
                await ctx.send(str(await self.translate(ctx.channel,'users','allow_animated_success')).format(value))
            else:
                await ctx.send(await self.translate(ctx.channel,'users','changed-1'))
    
    @profile_main.command(name="config")
    @commands.check(checks.database_connected)
    async def user_config(self,ctx:commands.Context,option:str,allow:bool=None):
        """Modify any config option
        Here you can (dis)allow one of the users option that Zbot have, which are:
        - animated_card: Display an animated rank card if your pfp is a git (way slower rendering)
        - auto_unafk: Automatically remove your AFK mode
        - usernames_log: Record when you change your username/nickname
        
        Value can only be a boolean (true/false)
        Providing empty value will show you the current value and more details"""
        options = {"animated_card":"animated_card", "auto_unafk":"auto_unafk", "usernames_log":"allow_usernames_logs"}
        if option not in options.keys():
            await ctx.send("no u")
            return
        if allow==None:
            value = await self.bot.cogs['UtilitiesCog'].get_db_userinfo([options[option]],[f'`userID`={ctx.author.id}'])
            if value==None:
                value = False
            else:
                value = value[options[option]]
            if ctx.guild==None or ctx.channel.permissions_for(ctx.guild.me).external_emojis:
                emojis = self.bot.cogs['EmojiCog'].customEmojis['green_check'], self.bot.cogs['EmojiCog'].customEmojis['red_cross']
            else:
                emojis = ('✅','❎')
            if value:
                await ctx.send(emojis[0]+" "+await self.translate(ctx.channel,'users',option+'_true'))
            else:
                await ctx.send(emojis[1]+" "+await self.translate(ctx.channel,'users',option+'_false'))
        else:
            if await self.bot.cogs['UtilitiesCog'].change_db_userinfo(ctx.author.id,options[option],allow):
                await ctx.send(await self.translate(ctx.channel,'users','config_success',opt=option))
            else:
                await ctx.send(await self.translate(ctx.channel,'users','changed-1'))

    def get_last_rankcard_update(self,userID:int):
        with open("rankcards_update.json",'r') as f:
            r = json.load(f)
        if str(userID) in r.keys():
            return r[str(userID)]
        return None
    
    def set_last_rankcard_update(self,userID:int):
        with open("rankcards_update.json",'r') as f:
            old = json.load(f)
        old[str(userID)] = round(time.time())
        with open("rankcards_update.json",'w') as f:
            json.dump(old,f)

def setup(bot):
    bot.add_cog(UsersCog(bot))