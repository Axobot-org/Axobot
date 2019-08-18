import discord, time, importlib
from discord.ext import commands
from fcts import checks, args
importlib.reload(checks)
importlib.reload(args)


class RolesReact(commands.Cog):
    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self.file = 'roles_react'
        self.table = 'roles_react_beta' if bot.beta else 'roles_react'
        self.guilds_which_have_roles = set()
        self.cache_initialized = False
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr
        self.table = 'roles_react_beta' if self.bot.beta else 'roles_react'
    
    async def prepare_react(self,payload:discord.RawReactionActionEvent):
        if payload.guild_id==None:
            return
        if not self.cache_initialized:
            await self.rr_get_guilds()
        if payload.guild_id not in self.guilds_which_have_roles:
            return
        chan = self.bot.get_channel(payload.channel_id)
        if chan == None:
            return
        try:
            msg = await chan.fetch_message(payload.message_id)
        except:
            return
        if len(msg.embeds)==0 or msg.embeds[0].footer.text!='ZBot roles reactions':
            return
        return msg


    @commands.Cog.listener('on_raw_reaction_add')
    # @commands.Cog.listener('on_raw_reaction_remove')
    async def on_raw_reaction(self,payload:discord.RawReactionActionEvent):
        msg = await self.prepare_react(payload)
        if msg != None:
            await msg.channel.send('`added` '+msg.content)
    
    @commands.Cog.listener('on_raw_reaction_remove')
    async def on_raw_reaction_2(self,payload:discord.RawReactionActionEvent):
        msg = await self.prepare_react(payload)
        if msg != None:
            await msg.channel.send('`removed` '+msg.content)
    
    async def gen_id(self):
        return round(time.time()/2)
    
    async def rr_get_guilds(self) -> set:
        """Get the list of guilds which have roles reactions"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = "SELECT `guild` FROM `{}`;".format(self.table)
        cursor.execute(query)
        self.guilds_which_have_roles = set([x['guild'] for x in cursor])
        cursor.close()
        self.cache_initialized = True
        return self.guilds_which_have_roles

    async def rr_add_role(self,guild:int,role:int,emoji:str,desc:str):
        """Add a role reaction in the database"""
        cnx = self.bot.cnx_frm
        if isinstance(emoji,discord.Emoji):
            emoji = emoji.id
        cursor = cnx.cursor(dictionary = True)
        ID = await self.gen_id()
        query = ("INSERT INTO `{}` (`ID`,`guild`,`role`,`emoji`,`description`) VALUES ('{i}','{g}','{r}','{e}','{d}');".format(self.table,i=ID,g=guild,r=role,e=emoji,d=desc))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True
    
    async def rr_list_role(self,guild:int,emoji:str=None):
        """List role reaction in the database"""
        cnx = self.bot.cnx_frm
        if isinstance(emoji,discord.Emoji):
            emoji = emoji.id
        cursor = cnx.cursor(dictionary = True)
        query = "SELECT * FROM `{}` WHERE guild={} ORDER BY added_at;".format(self.table,guild) if emoji==None else "SELECT * FROM `{}` WHERE guild={} AND emoji='{}' ORDER BY added_at;".format(self.table,guild,emoji)
        cursor.execute(query)
        liste = list()
        for x in cursor:
            liste.append(x)
        cursor.close()
        return liste
    
    async def rr_remove_role(self,ID:int):
        """Remove a role reaction from the database"""
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor(dictionary = True)
        query = ("DELETE FROM `{}` WHERE `ID`={};".format(self.table,ID))
        cursor.execute(query)
        cnx.commit()
        cursor.close()
        return True

    @commands.group(name="roles_react")
    @commands.guild_only()
    async def rr_main(self,ctx):
        """Manage your roles reactions"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['roles_react'])
    
    @rr_main.command(name="add")
    @commands.check(checks.has_manage_guild)
    async def rr_add(self,ctx,emoji:args.anyEmoji,role:discord.Role,*,description:str=None):
        """Add a role reaction
        This role will be given when a membre click on a specific reaction"""
        try:
            if role.name == '@everyone':
                raise commands.BadArgument(f'Role "{role.name}" not found')
            l = await self.rr_list_role(ctx.guild.id,emoji)
            if len(l)>0:
                return await ctx.send(await self.translate(ctx.guild.id,'roles_react','already-1-rr'))
            max_rr = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'roles_react_max_number')
            max_rr = self.bot.cogs["ServerCog"].default_opt['roles_react_max_number'] if max_rr==None else max_rr
            if len(l) >= max_rr:
                return await ctx.send(await self.translate(ctx.guild.id,'roles_react','too-many-rr',l=max_rr))
            await self.rr_add_role(ctx.guild.id,role.id,emoji,description)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            await ctx.send(await self.translate(ctx.guild.id,'roles_react','rr-added',r=role.name,e=emoji))
            self.guilds_which_have_roles.add(ctx.guild.id)
    
    @rr_main.command(name="remove")
    @commands.check(checks.has_manage_guild)
    async def rr_remove(self,ctx,emoji:args.anyEmoji):
        """Remove a role react"""
        try:
            l = await self.rr_list_role(ctx.guild.id,emoji)
            if len(l)==0:
                return await ctx.send(await self.translate(ctx.guild.id,'roles_react','no-rr'))
            await self.rr_remove_role(l[0]['ID'])
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            role = ctx.guild.get_role(l[0]['role'])
            await ctx.send(await self.translate(ctx.guild.id,'roles_react','rr-removed',r=role,e=emoji))
            if len(l)<2:
                self.guilds_which_have_roles.remove(ctx.guild.id)
        
    @rr_main.command(name="list")
    async def rr_list(self,ctx):
        """List every roles reactions of your server"""
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.translate(ctx.guild.id,"fun","no-embed-perm"))
        try:
            l = await self.rr_list_role(ctx.guild.id)
        except Exception as e:
            await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
        else:
            for k in l:
                if len(k['emoji'])>5 and k['emoji'].isnumeric():
                    temp = await ctx.guild.fetch_emoji(int(k['emoji']))
                    if temp != None:
                        k['emoji'] = str(temp)
            des = '\n'.join(["{}   <@&{}> ".format(x['emoji'], x['role']) for x in l])
            max_rr = await self.bot.cogs['ServerCog'].find_staff(ctx.guild.id,'roles_react_max_number')
            max_rr = self.bot.cogs["ServerCog"].default_opt['roles_react_max_number'] if max_rr==None else max_rr
            title = await self.translate(ctx.guild.id,"roles_react",'rr-list',n=len(l),m=max_rr)
            emb = self.bot.cogs['EmbedCog'].Embed(title=title,desc=des).update_timestamp().create_footer(ctx.author)
            await ctx.send(embed=emb.discord_embed())




def setup(bot):
    bot.add_cog(RolesReact(bot))