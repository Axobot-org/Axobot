import discord
import re
import inspect
import json
import copy
from typing import List
from discord.ext import commands
from utils import Zbot, MyContext


class Help(commands.Cog):

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "aide"
        self.old_cmd = bot.remove_command("help")
        self.help_color = 8311585
        self.help_color_DM = 14090153
        self.doc_url = "https://zbot.readthedocs.io/en/latest/"
        with open('fcts/help.json', 'r') as file:
            self.commands_list = json.load(file)

    def cog_unload(self):
        self.bot.remove_command("help")
        self.bot.add_command(self.old_cmd)

    @commands.command(name="welcome", aliases=['bvn', 'bienvenue', 'leave'])
    @commands.cooldown(10, 30, commands.BucketType.channel)
    async def bvn_help(self, ctx: MyContext):
        """Help on setting up welcome / leave messages

..Doc infos.html#welcome-message"""
        prefix = await self.bot.get_prefix(ctx.message)
        if type(prefix) == list:
            prefix = prefix[-1]
        await ctx.send(await self.bot._(ctx.guild, "welcome.help", p=prefix))

    @commands.command(name="about", aliases=["botinfos", "botinfo"])
    @commands.cooldown(7, 30, commands.BucketType.user)
    async def infos(self, ctx: MyContext):
        """Information about the bot

..Doc infos.html#about"""
        urls = ""
        for e, url in enumerate(['http://discord.gg/N55zY88', 'https://zrunner.me/invitezbot', 'https://zbot.rtfd.io/', 'https://twitter.com/z_runnerr', 'https://zrunner.me/zbot-faq', 'https://zrunner.me/zbot-privacy.pdf']):
            urls += "\n:arrow_forward: " + await self.bot._(ctx.channel, f"info.about-{e}") + " <" + url + ">"
        msg = await self.bot._(ctx.channel, "info.about-main", mention=ctx.bot.user.mention, links=urls)
        if ctx.can_send_embed:
            await ctx.send(embed=self.bot.get_cog("Embeds").Embed(desc=msg, color=16298524))
        else:
            await ctx.send(msg)

    @commands.command(name="help")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help_cmd(self, ctx: MyContext, *commands: str):
        """Shows this message
Enable "Embed Links" permission for better rendering

..Example help

..Example help info

..Example help rss embed

..Doc infos.html#help"""
        try:
            # commands = [x.replace('@everyone','@​everyone').replace('@here','@​here') for x in commands]
            if len(commands) == 0:
                await self.help_command(ctx)
            else:
                await self.help_command(ctx, commands)
        except discord.errors.Forbidden:
            pass
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e, ctx)
            if len(commands) == 0:
                await self._default_help_command(ctx)
            else:
                await self._default_help_command(ctx, commands)

    async def help_command(self, ctx: MyContext, commands=()):
        """Main command for the creation of the help message
If the bot can't send the new command format, it will try to send the old one."""
        async with ctx.channel.typing():
            destination: discord.TextChannel = None
            if ctx.guild is not None:
                send_in_dm = False if self.bot.database_online == False else await self.bot.get_config(ctx.guild, 'help_in_dm')
                if send_in_dm is not None and send_in_dm == 1:
                    destination = ctx.message.author.dm_channel
                    await self.bot.get_cog("Utilities").suppr(ctx.message)
                else:
                    destination = ctx.message.channel
            if destination is None:
                await ctx.message.author.create_dm()
                destination = ctx.message.author.dm_channel

            me = destination.me if type(
                destination) == discord.DMChannel else destination.guild.me
            title = ""

            if " ".join(commands).lower() in self.commands_list.keys():
                categ_name = [" ".join(commands).lower()]
            else:
                translated_categories = {k: await self.bot._(ctx.channel, f"help.categories.{k}") for k in self.commands_list.keys()}
                categ_name = [k for k, v in translated_categories.items() if v.lower() == " ".join(commands).lower()]

            if len(categ_name) == 1: # cog name
                if categ_name[0] == "unclassed":
                    referenced_commands = {x for v in self.commands_list.values() for x in v}
                    temp = [c for c in self.bot.commands if c.name not in referenced_commands]
                else:
                    temp = [c for c in self.bot.commands if c.name in self.commands_list[categ_name[0]]]
                pages = await self.all_commands(ctx, sorted(temp, key=self.sort_by_name))
                if len(pages) == 0 and ctx.guild is None:
                    pages = [await self.bot._(ctx.channel, "help.cog-empty-dm")]
            elif len(commands) == 0:  # no command
                compress = await self.bot.get_config(ctx.guild, 'compress_help')
                pages = await self.all_commands(ctx, sorted([c for c in self.bot.commands], key=self.sort_by_name), compress=compress)
                if ctx.guild is None:
                    title = await self.bot._(ctx.channel, "help.embed_title_dm")
                else:
                    title = await self.bot._(ctx.channel, "help.embed_title", u=str(ctx.author))
            elif len(commands) == 1:  # Unique command name?
                name = commands[0]
                command = None
                if name in self.bot.cogs:
                    cog = self.bot.get_cog(name)
                    pages = await self.cog_commands(ctx, cog)
                else:
                    command = self.bot.all_commands.get(name)
                    if command is None:
                        ctx2 = copy.copy(ctx)
                        ctx2.message.content = name
                        name = await discord.ext.commands.clean_content().convert(ctx2, name)
                        await destination.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                        return
                    pages = await self.cmd_help(ctx, command, destination.permissions_for(me).embed_links)
            else:  # sub-command name?
                name = commands[0]
                command = self.bot.all_commands.get(name)
                if command is None:
                    await destination.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                    return
                for key in commands[1:]:
                    try:
                        command = command.all_commands.get(key)
                        if command is None:
                            await destination.send(await self.bot._(ctx.channel, "help.subcmd-not-found", name=key))
                            return
                    except AttributeError:
                        await destination.send(await self.bot._(ctx.channel, "help.no-subcmd", cmd=command.name))
                        return
                pages = await self.cmd_help(ctx, command, destination.permissions_for(me).embed_links)

            ft = await self.bot._(ctx.channel, "help.footer")
            prefix = await self.bot.get_prefix(ctx.message)
            if type(prefix) == list:
                prefix = prefix[-1]
        if len(pages) == 0:
            await self.bot.get_cog("Errors").senf_err_msg("Impossible de trouver d'aide pour la commande " + " ".join(commands))
            await destination.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=" ".join(commands)))
            return
        if destination.permissions_for(me).embed_links:
            if ctx.guild is not None:
                embed_colour = ctx.guild.me.color if ctx.guild.me.color != discord.Colour.default() else discord.Colour(self.help_color)
            else:
                embed_colour = discord.Colour(self.help_color_DM)
            if isinstance(pages[0], str): # use description
                for page in pages:
                    embed = self.bot.get_cog("Embeds").Embed(title=title, desc=page, footer_text=ft.format(
                        prefix), color=embed_colour).update_timestamp()
                    title = ""
                    await destination.send(embed=embed)
            else: # use fields
                fields = list()
                for page in pages:
                    if len(page) == 1:
                        title = page[0]
                        continue
                    fields.append({'name': page[0], 'value': page[1], 'inline': False})
                embed = self.bot.get_cog("Embeds").Embed(title=title, footer_text=ft.format(
                    prefix), fields=fields, color=embed_colour).update_timestamp()
                await destination.send(embed=embed)
        else:
            for page in pages:
                if isinstance(page, str):
                    await destination.send(page)
                else:
                    await destination.send("\n".join(page))

    async def display_cmd(self, cmd: commands.Command):
        return "• **{}**\t\t*{}*".format(cmd.name, cmd.short_doc.strip()) if len(cmd.short_doc) > 0 else "• **{}**".format(cmd.name)

    def sort_by_name(self, cmd: commands.Command) -> str:
        return cmd.name

    async def all_commands(self, ctx: MyContext, cmds: List[commands.Command], compress: bool = False):
        """Create pages for every bot command"""
        categories = {x: list() for x in self.commands_list.keys()}
        for cmd in cmds:
            try:
                if cmd.hidden == True or cmd.enabled == False:
                    continue
                if (await cmd.can_run(ctx)) == False:
                    continue
            except Exception as e:
                if not "discord.ext.commands.errors" in str(type(e)):
                    raise e
                else:
                    continue
            temp = await self.display_cmd(cmd)
            found = False
            for k, v in self.commands_list.items():
                if cmd.name in v:
                    categories[k].append(temp)
                    found = True
                    break
            if not found:
                categories['unclassed'].append(temp)
        answer = list()
        if compress:
            pass
            for k, v in categories.items():
                if len(v) == 0:
                    continue
                tr = await self.bot._(ctx.channel, f"help.categories.{k}")
                title = "__**"+tr.capitalize()+"**__"
                count = await self.bot._(ctx.channel, "help.cmd-count",
                                         nbr=len(v),
                                         p=ctx.prefix,
                                         cog=k)
                answer.append((title, count))
        else:
            for k, v in categories.items():
                if len(v) == 0:
                    continue
                tr = await self.bot._(ctx.channel, f"help.categories.{k}")
                if len("\n".join(v)) > 1020:
                    temp = list(v)
                    v = list()
                    i = 1
                    for line in temp:
                        if len("\n".join(v+[line])) > 1020:
                            title = (tr+' - ' + str(i)) if 'help.' not in tr else (k+' - '+str(i))
                            answer.append(("__**"+title.capitalize()+"**__", "\n".join(v)))
                            v = list()
                            i += 1
                        v.append(line)
                    title = (tr+' - ' + str(i)) if 'help.' not in tr else (k+' - '+str(i))
                    answer.append(("__**"+title.capitalize()+"**__", "\n".join(v)))
                else:
                    title = tr
                    answer.append(("__**"+title.capitalize()+"**__", "\n".join(v)))
        return answer

    async def cog_commands(self, ctx: MyContext, cog: commands.Cog):
        """Create pages for every command of a cog"""
        description = inspect.getdoc(cog)
        page = ""
        form = "**{}**\n\n {} \n{}"
        pages = list()
        cog_name = cog.__class__.__name__
        if description is None:
            description = await self.bot._(ctx.channel, "help.no-desc-cog")
        for cmd in sorted([c for c in self.bot.commands], key=self.sort_by_name):
            try:
                if (await cmd.can_run(ctx)) == False or cmd.hidden == True or cmd.enabled == False or cmd.cog_name != cog_name:
                    continue
            except Exception as e:
                if not "discord.ext.commands.errors" in str(type(e)):
                    raise e
                else:
                    continue
            text = await self.display_cmd(cmd)
            if len(page+text) > 1900:
                pages.append(form.format(cog_name, description, page))
                page = text
            else:
                page += "\n"+text
        pages.append(form.format(cog_name, description, page))
        return pages

    async def extract_info(self, desc: str):
        data = [x.strip() for x in desc.split("\n\n")]
        desc, example, doc = list(), list(), list()
        for p in data:
            if p.startswith("..Example "):
                example.append(p.replace("..Example ", ""))
            elif p.startswith("..Doc "):
                doc.append(p.replace("..Doc ", ""))
            else:
                desc.append(p)
        return (x if len(x) > 0 else None for x in ("\n\n".join(desc), example, doc))

    async def cmd_help(self, ctx: MyContext, cmd: commands.core.Command, useEmbed: bool = True):
        """Create pages for a command explanation"""
        desc = cmd.description.strip()
        if desc == '' and cmd.help is not None:
            desc = cmd.help.strip()
        desc, example, doc = await self.extract_info(desc)
        if desc is None:
            desc = await self.bot._(ctx.channel, "help.no-desc-cmd")
        # Prefix
        prefix = await self.bot.get_prefix(ctx.message)
        if type(prefix) == list:
            prefix = prefix[-1]
        # Syntax
        syntax = cmd.qualified_name + "** " + cmd.signature
        # Subcommands
        sublist = list()
        subcmds = ""
        if type(cmd) == commands.core.Group:
            syntax += " ..."
            if not useEmbed:
                subcmds = "__{}__".format(str(await self.bot._(ctx.channel, "help.subcmds")).capitalize())
            for x in sorted(cmd.all_commands.values(), key=self.sort_by_name):
                try:
                    if x.hidden == False and x.enabled == True and x.name not in sublist and await x.can_run(ctx):
                        subcmds += "\n• {} {}".format(x.name, "*({})*".format(
                            x.short_doc) if len(x.short_doc) > 0 else "")
                        sublist.append(x.name)
                except Exception as e:
                    if not "discord.ext.commands.errors" in str(type(e)):
                        raise e
                    else:
                        continue
        # Is enabled
        enabled = list()
        if not cmd.enabled:
            enabled.append(await self.bot._(ctx.channel, "help.not-enabled"))
        # Checks
        checks = list()
        if len(cmd.checks) > 0:
            maybe_coro = discord.utils.maybe_coroutine
            for c in cmd.checks:
                try:
                    if 'guild_only.<locals>.predicate' in str(c):
                        check_name = 'guild_only'
                    elif 'is_owner.<locals>.predicate' in str(c):
                        check_name = 'is_owner'
                    elif 'bot_has_permissions.<locals>.predicate' in str(c):
                        check_name = 'bot_has_permissions'
                    elif '_has_permissions.<locals>.predicate' in str(c):
                        check_name = 'has_permissions'
                    else:
                        check_name = c.__name__
                    check_msg_tr = await self.bot._(ctx.channel, f'help.check-desc.{check_name}')
                    if 'help.check-desc' not in check_msg_tr:
                        try:
                            pass_check = await maybe_coro(c, ctx)
                        except:
                            pass_check = False
                        if pass_check:
                            checks.append(
                                ":small_blue_diamond: "+check_msg_tr[0])
                        else:
                            pass
                            checks.append('❌ '+check_msg_tr[1])
                    else:
                        self.bot.log.warning(f"No description for help check {check_name} ({c})")
                except Exception as e:
                    await self.bot.get_cog("Errors").on_error(e, ctx)
        # Module
        category = "unclassed"
        for k, v in self.commands_list.items():
            if cmd.name in v or cmd.full_parent_name in v:
                category = k
                break
        category = (await self.bot._(ctx.channel, f"help.categories.{category}")).capitalize()
        if useEmbed:
            answer = list()
            answer.append([f"**{prefix}{syntax}"])
            answer.append((await self.bot._(ctx.channel, 'help.description'), desc))
            if example is not None:
                answer.append(((await self.bot._(ctx.channel, 'misc.example')).capitalize(), "\n".join(example)))
            if len(subcmds) > 0:
                answer.append((await self.bot._(ctx.channel, 'help.subcmds'), subcmds))
            if len(cmd.aliases) > 0:
                answer.append((await self.bot._(ctx.channel, "help.aliases"), " - ".join(cmd.aliases)))
            if len(enabled+checks) > 0:
                t = await self.bot._(ctx.channel, "help.warning")
                answer.append((t, '\n'.join(enabled+checks)))
            if doc is not None:
                doc = "\n".join([self.doc_url+x for x in doc])
                answer.append(((await self.bot._(ctx.channel, 'misc.doc')).capitalize(), "[{0}]({0})".format(doc)))
            answer.append(((await self.bot._(ctx.channel, 'misc.category')).capitalize(), category))
            return answer
        else:
            answer = f"**{prefix}{syntax}\n\n{desc}\n\n"
            if example is not None:
                answer += "\n__"+(await self.bot._(ctx.channel, 'misc.example')).capitalize()+"__\n"+"\n".join(example)+"\n"
            if len(subcmds) > 0:
                answer += "\n"+subcmds+"\n"
            if len(cmd.aliases) > 0:
                answer += "\n"+"__" + await self.bot._(ctx.channel, "help.aliases") + "__ " + (" - ".join(cmd.aliases)) + "\n"
            if len(enabled) > 0:
                answer += enabled[0]
            if len(checks) > 0:
                answer += "\n" + "__" + await self.bot._(ctx.channel, "help.warning") + "__\n" + '\n'.join(checks) + "\n"
            if doc is not None:
                answer += "\n__" + (await self.bot._(ctx.channel, 'misc.doc')).capitalize() + "__\n" + "\n".join([f"<{self.doc_url+x}>" for x in doc])+"\n"
            answer += "\n\n__{}:__ {}".format((await self.bot._(ctx.channel, 'misc.category')).capitalize(), category)
            while "\n\n\n" in answer:
                answer = answer.replace("\n\n\n", "\n\n")
            return [answer]

    async def _default_help_command(self, ctx: MyContext, command: str = None):
        truc = commands.DefaultHelpCommand()
        truc.context = ctx
        truc._command_impl = self.help_cmd
        # General help
        if command is None:
            mapping = truc.get_bot_mapping()
            return await truc.send_bot_help(mapping)
        # Check if it's a cog
        cog = self.bot.get_cog(" ".join(command))
        if cog is not None:
            return await truc.send_cog_help(cog)
        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        maybe_coro = discord.utils.maybe_coroutine
        keys = command
        cmd = self.bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(truc.command_not_found, truc.remove_mentions(keys[0]))
            return await truc.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(truc.subcommand_not_found, cmd, truc.remove_mentions(key))
                return await truc.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(truc.subcommand_not_found, cmd, truc.remove_mentions(key))
                    return await truc.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await truc.send_group_help(cmd)
        else:
            return await truc.send_command_help(cmd)


def setup(bot):
    bot.add_cog(Help(bot))
