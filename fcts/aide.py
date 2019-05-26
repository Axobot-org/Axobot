import discord, re, inspect
from discord.ext import commands

class HelpCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = "aide"
        bot.remove_command("help")
        self._mentions_transforms = {
    '@everyone': '@\u200beveryone',
    '@here': '@\u200bhere'}
        self._mention_pattern = re.compile('|'.join(self._mentions_transforms.keys()))
        self.help_color = 8311585
        try:
            self.translate = bot.cogs["LangCog"].tr
        except:
            pass
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr

    @commands.command(name="welcome",aliases=['bvn','bienvenue','leave'])
    @commands.cooldown(10,30,commands.BucketType.channel)
    async def bvn_help(self,ctx):
        """Help on setting up welcome / leave messages"""
        await ctx.send(await self.bot.cogs['LangCog'].tr(ctx.guild,'bvn','aide'))


    @commands.command(name="about",aliases=["botinfos","botinfo"])
    @commands.cooldown(7,30,commands.BucketType.user)
    async def infos(self,ctx):
        """Information about the bot"""
        msg = await self.bot.cogs['LangCog'].tr(ctx.guild,'infos','text-0')
        await ctx.send(msg.format(ctx.guild.me.mention if ctx.guild!=None else ctx.bot.user.mention))

    

    @commands.command(name="help")
    @commands.cooldown(1,5,commands.BucketType.user)
    async def help_cmd(self,ctx,*commands : str):
        """Shows this message
        Enable "Embed Links" permission for better rendering"""
        try:
            if len(commands) == 0:
                await self.help_command(ctx)
            else:
                await self.help_command(ctx,commands)
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            await self.bot.cogs["ErrorsCog"].on_error(e,ctx)
            if len(commands) == 0:
                await self._default_help_command(ctx)
            else:
                await self._default_help_command(ctx,commands)


    async def help_command(self,ctx, commands=()):
        """Main command for the creation of the help message
If the bot can't send the new command format, it will try to send the old one."""
        async with ctx.channel.typing():
            destination = None
            if ctx.guild!=None:
                if await self.bot.cogs["ServerCog"].find_staff(ctx.guild,'help_in_dm') == 1:
                    destination = ctx.message.author.dm_channel
                    await self.bot.cogs["UtilitiesCog"].suppr(ctx.message)
                else:
                    destination = ctx.message.channel
            if destination == None:
                await ctx.message.author.create_dm()
                destination = ctx.message.author.dm_channel
        
            def repl(obj):
                return self._mentions_transforms.get(obj.group(0), '')

            if len(commands) == 0:  #aucune commande
                pages = await self.all_commands(ctx)
            elif len(commands) == 1:    #Nom de cog/commande unique ?
                name = self._mention_pattern.sub(repl, commands[0])
                command = None
                if name in self.bot.cogs:
                    cog = self.bot.cogs[name]
                    pages = await self.cog_commands(ctx,cog)
                else:
                    command = self.bot.all_commands.get(name)
                    if command is None:
                        await destination.send(str(await self.translate(ctx.channel,"aide","cmd-not-found")).format(name))
                        return
                    pages = await self.cmd_help(ctx,command)
            else:  #nom de sous-commande ?
                name = self._mention_pattern.sub(repl, commands[0])
                command = self.bot.all_commands.get(name)
                if command is None:
                    await destination.send(str(await self.translate(ctx.channel,"aide","cmd-not-found")).format(name))
                    return
                for key in commands[1:]:
                    try:
                        key = self._mention_pattern.sub(repl, key)
                        command = command.all_commands.get(key)
                        if command is None:
                            await destination.send(str(await self.translate(ctx.channel,"aide","subcmd-not-found")).format(key))
                            return
                    except AttributeError:
                        await destination.send(str(await self.translate(ctx.channel,"aide","no-subcmd")).format(command))
                        return
                pages = await self.cmd_help(ctx,command)

            me = destination.me if type(destination)==discord.DMChannel else destination.guild.me
            ft = await self.translate(ctx.channel,"aide","footer")
            prefix = await self.bot.get_prefix(ctx.message)
            if type(prefix)==list:
                prefix = prefix[0]
        if destination.permissions_for(me).embed_links:
            for page in pages:
                embed = self.bot.cogs["EmbedCog"].Embed(desc=page,footer_text=ft.format(prefix)).update_timestamp().discord_embed()
                if ctx.guild != None:
                    embed.colour = ctx.guild.me.color if ctx.guild.me.color != discord.Colour(self.help_color).default() else discord.Colour(self.help_color)
                await destination.send(embed=embed)
        else:
            for page in pages:
                await destination.send(page)

    async def display_cmd(self,cmd):
        #return "**{}**\n\t\t*{}*".format(cmd.name,cmd.short_doc.strip()) if len(cmd.short_doc)>0 else "**{}**".format(cmd.name)
        return "• **{}**\t\t*{}*".format(cmd.name,cmd.short_doc.strip()) if len(cmd.short_doc)>0 else "• **{}**".format(cmd.name)

    def sort_by_name(self,cmd):
            return cmd.name

    async def all_commands(self,ctx):
        """Create pages for every bot command"""
        def category(cmd):
            cog = cmd.cog_name
            # we insert the zero width space there to give it approximate
            # last place sorting position.
            return cog + ':' if cog is not None else '\u200bNo Category:'
        
        cmds = sorted([c for c in self.bot.commands],key=self.sort_by_name)
        modhelp = ""
        otherhelp = ""
        for cmd in cmds:
            try:
                if cmd.hidden==True or cmd.enabled==False:
                    continue
                if (await cmd.can_run(ctx))==False:
                    continue
            except Exception as e:
                if not "discord.ext.commands.errors" in str(type(e)):
                    await ctx.send("`Error:` {}".format(e))
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    return []
                else:
                    continue
            temp = await self.display_cmd(cmd)
            if cmd.cog_name in ['AdminCog','ServerCog','ModeratorCog','CasesCog','ReloadsCog','TimedCog']:
                modhelp += "\n"+temp
            else:
                otherhelp += "\n"+temp
        tr = await self.translate(ctx.channel,"aide","mods")
        if len(modhelp+otherhelp)<1900:
            return ["__• **{}**__\n{}".format(tr[0],modhelp) + "\n\n__• **{}**__\n{}".format(tr[1],otherhelp)]
        else:
            return ["__• **{}**__\n{}".format(tr[0],modhelp) , "\n\n__• **{}**__\n{}".format(tr[1],otherhelp)]

    async def cog_commands(self,ctx,cog):
        """Create pages for every command of a cog"""
        description = inspect.getdoc(cog)
        page = ""
        form = "**{}**\n\n {} \n{}"
        pages = list()
        cog_name = cog.__class__.__name__
        if description == None:
            description = await self.translate(ctx.channel,"aide","no-desc-cog")
        for cmd in sorted([c for c in self.bot.commands],key=self.sort_by_name):
            try:
                if (await cmd.can_run(ctx))==False or cmd.hidden==True or cmd.enabled==False or cmd.cog_name != cog_name:
                    continue
            except Exception as e:
                if not "discord.ext.commands.errors" in str(type(e)):
                    await ctx.send("`Error:` {}".format(e))
                    await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                    return []
                else:
                    continue
            text = await self.display_cmd(cmd)
            if len(page+text)>1900:
                pages.append(form.format(cog_name,description,page))
                page = text
            else:
                page += "\n"+text
        pages.append(form.format(cog_name,description,page))
        return pages
    
    async def cmd_help(self,ctx,cmd):
        """Create pages for a command explanation"""
        desc = cmd.description if cmd.description!=None else str(await self.translate(ctx.channel,"aide","no-desc-cmd"))
        if desc=='':
            desc = cmd.help
        prefix = await self.bot.get_prefix(ctx.message)
        if type(prefix)==list:
            prefix = prefix[0]
        syntax = cmd.qualified_name + "** " + cmd.signature
        if type(cmd)==commands.core.Group:
            subcmds = "\n\n__{}__".format(str(await self.translate(ctx.channel,"keywords","subcmds")).capitalize())
            sublist = list()
            for x in sorted(cmd.all_commands.values(),key=self.sort_by_name):
                try:
                    if x.hidden==False and x.enabled==True and x.name not in sublist and await x.can_run(ctx):
                        subcmds += "\n- {} {}".format(x.name,"*({})*".format(x.short_doc) if len(x.short_doc)>0 else "")
                        sublist.append(x.name)
                except Exception as e:
                    if not "discord.ext.commands.errors" in str(type(e)):
                        await ctx.send("`Error:` {}".format(e))
                        await self.bot.cogs['ErrorsCog'].on_error(e,ctx)
                        return []
                    else:
                        continue
        else:
            subcmds = ""
        return ["**{}{}\n\n{}\n\n*Cog: {}*{}".format(prefix,syntax,desc,cmd.cog_name,subcmds)]


    async def _default_help_command(self,ctx, commands=()):
        bot = ctx.bot
        if await self.bot.cogs["ServerCog"].find_staff(ctx.guild,'help_in_dm') == 1:
            destination = ctx.message.author
            await bot.cogs["UtilitiesCog"].suppr(ctx.message)
        else :
            destination = ctx.message.channel
        def repl(obj):
            return self._mentions_transforms.get(obj.group(0), '')

            # help by itself just lists our own commands.
        if len(commands) == 0:
            pages = await bot.formatter.format_help_for(ctx, bot)
        elif len(commands) == 1:
            # try to see if it is a cog name
            name = self._mention_pattern.sub(repl, commands[0])
            command = None
            if name in bot.cogs:
                command = bot.cogs[name]
            else:
                command = bot.all_commands.get(name)
                if command is None:
                    await destination.send(bot.command_not_found.format(name))
                    return

            pages = await bot.formatter.format_help_for(ctx, command)
        else:
            name = self._mention_pattern.sub(repl, commands[0])
            command = bot.all_commands.get(name)
            if command is None:
                await destination.send(bot.command_not_found.format(name))
                return

            for key in commands[1:]:
                try:
                    key = self._mention_pattern.sub(repl, key)
                    command = command.all_commands.get(key)
                    if command is None:
                        await destination.send(bot.command_not_found.format(key))
                        return
                except AttributeError:
                    await destination.send(str(await self.translate(ctx.channel,"aide","no-subcmd")).format(command))
                    return

            pages = await bot.formatter.format_help_for(ctx, command)

        if bot.pm_help is None:
            characters = sum(map(len, pages))
            # modify destination based on length of pages.
            if characters > 1000:
                destination = ctx.message.author

        for page in pages:
            await destination.send(page)


def setup(bot):
    bot.add_cog(HelpCog(bot))
