import copy
import inspect
import json
from typing import List, Optional, TypedDict

import discord
from discord.ext import commands

from libs.bot_classes import Axobot, MyContext


class CommandsCategoryData(TypedDict):
    emoji: str
    commands: list[str]

class Help(commands.Cog):

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "aide"
        self.old_cmd = bot.remove_command("help")
        self.help_color = 8311585
        self.help_color_DM = 14090153
        with open('fcts/help.json', 'r', encoding="utf-8") as file:
            self.commands_data: dict[str, CommandsCategoryData] = json.load(file)

    @property
    def doc_url(self):
        return (
            "https://zbot.readthedocs.io/en/latest/",
            "https://zbot.readthedocs.io/en/develop/",
            "https://zbot.readthedocs.io/en/release-candidate/",
        )[self.bot.entity_id]

    async def cog_unload(self):
        self.bot.remove_command("help")
        self.bot.add_command(self.old_cmd)

    @commands.command(name="welcome", aliases=['bvn', 'bienvenue', 'leave'])
    @commands.cooldown(10, 30, commands.BucketType.channel)
    async def bvn_help(self, ctx: MyContext):
        """Help on setting up welcome / leave messages

..Doc infos.html#welcome-message"""
        config_cmd = await self.bot.get_command_mention("config set")
        await ctx.send(await self.bot._(ctx.guild, "welcome.help", config_cmd=config_cmd))

    @commands.hybrid_command(name="about", aliases=["botinfos", "botinfo"])
    @commands.cooldown(7, 30, commands.BucketType.user)
    async def about_cmd(self, ctx: MyContext):
        """Information about the bot

..Doc infos.html#about"""
        urls = ""
        bot_invite = "https://zrunner.me/" + ("invitezbot" if self.bot.entity_id == 0 else "invite-axobot")
        for i, url in enumerate(['http://discord.gg/N55zY88', bot_invite, 'https://zbot.rtfd.io/', 'https://twitter.com/z_runnerr', 'https://zrunner.me/zbot-faq', 'https://zrunner.me/zbot-privacy.pdf']):
            urls += "\n:arrow_forward: " + await self.bot._(ctx.channel, f"info.about-{i}") + " <" + url + ">"
        msg = await self.bot._(ctx.channel, "info.about-main", mention=ctx.bot.user.mention, links=urls)
        if ctx.can_send_embed:
            await ctx.send(embed=discord.Embed(description=msg, color=16298524))
        else:
            await ctx.send(msg)

    @commands.command(name="help")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.cooldown(10, 30, commands.BucketType.guild)
    async def help_cmd(self, ctx: MyContext, *args: str):
        """Shows this message
Enable "Embed Links" permission for better rendering

..Example help

..Example help info

..Example help rss embed

..Doc infos.html#help"""
        try:
            if len(args) == 0:
                await self.help_command(ctx)
            else:
                await self.help_command(ctx, args)
        except discord.errors.Forbidden:
            pass
        except Exception as err:
            self.bot.dispatch("error", err, ctx)
            if len(args) == 0:
                await self._default_help_command(ctx)
            else:
                await self._default_help_command(ctx, args)

    async def should_dm(self, context: MyContext) -> bool:
        "Check if the answer should be sent in DM or in current channel"
        if context.guild is None or not self.bot.database_online:
            return False
        return await self.bot.get_config(context.guild.id, 'help_in_dm')

    async def help_command(self, ctx: MyContext, commands: Optional[list[str]] = None):
        """Main command for the creation of the help message
If the bot can't send the new command format, it will try to send the old one."""
        async with ctx.channel.typing():
            destination: discord.abc.Messageable = None
            if ctx.guild is not None:
                if await self.should_dm(ctx):
                    destination = ctx.message.author.dm_channel
                    if ctx.guild:
                        await ctx.message.delete(delay=0)
                else:
                    destination = ctx.message.channel
            if destination is None:
                await ctx.message.author.create_dm()
                destination = ctx.message.author.dm_channel

            bot_usr = destination.me if isinstance(destination, discord.DMChannel) else destination.guild.me
            title = ""

            if commands is not None and " ".join(commands).lower() in self.commands_data:
                categ_name = [" ".join(commands).lower()]
            else:
                translated_categories = {
                    k: await self.bot._(ctx.channel, f"help.categories.{k}")
                    for k in self.commands_data.keys()
                }
                if commands is None:
                    categ_name = []
                else:
                    categ_name = [k for k, v in translated_categories.items() if v.lower() == " ".join(commands).lower()]

            if len(categ_name) == 1: # cog name
                if categ_name[0] == "unclassed":
                    referenced_commands = {x for v in self.commands_data.values() for x in v['commands']}
                    temp = [c for c in self.bot.commands if c.name not in referenced_commands]
                else:
                    temp = [c for c in self.bot.commands if c.name in self.commands_data[categ_name[0]]['commands']]
                pages = await self.all_commands(ctx, sorted(temp, key=self.sort_by_name))
                if len(pages) == 0 and ctx.guild is None:
                    pages = [await self.bot._(ctx.channel, "help.cog-empty-dm")]
            elif not commands:  # no command
                compress: bool = await self.bot.get_config(ctx.guild.id, 'compress_help') if ctx.guild else False
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
                    pages = await self.cmd_help(ctx, command, destination.permissions_for(bot_usr).embed_links)
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
                pages = await self.cmd_help(ctx, command, destination.permissions_for(bot_usr).embed_links)

            ft = await self.bot._(ctx.channel, "help.footer")
            prefix = await self.bot.prefix_manager.get_prefix(ctx.guild)
        if len(pages) == 0:
            self.bot.dispatch("error", ValueError(f"Unable to find help for the command {' '.join(commands)}"))
            await destination.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=" ".join(commands)))
            return
        if destination.permissions_for(bot_usr).embed_links:
            if ctx.guild is not None:
                embed_colour = ctx.guild.me.color if ctx.guild.me.color != discord.Colour.default() else discord.Colour(self.help_color)
            else:
                embed_colour = discord.Colour(self.help_color_DM)
            if isinstance(pages[0], str): # use description
                for page in pages:
                    embed = discord.Embed(title=title, description=page, color=embed_colour, timestamp=self.bot.utcnow())
                    embed.set_footer(text=ft.format(prefix))
                    title = ""
                    await destination.send(embed=embed)
            else: # use fields
                embed = discord.Embed(title=title, color=embed_colour, timestamp=self.bot.utcnow())
                embed.set_footer(text=ft.format(prefix))
                for page in pages:
                    if len(page) == 1:
                        embed.title = page[0]
                        continue
                    embed.add_field(name=page[0], value=page[1], inline=False)
                await destination.send(embed=embed)
        else:
            for page in pages:
                if isinstance(page, str):
                    await destination.send(page)
                else:
                    await destination.send("\n".join(page))

    async def display_cmd(self, cmd: commands.Command):
        return f"• **{cmd.name}**\t\t*{cmd.short_doc.strip()}*" if len(cmd.short_doc) > 0 else f"• **{cmd.name}**"

    def sort_by_name(self, cmd: commands.Command) -> str:
        return cmd.name

    async def all_commands(self, ctx: MyContext, cmds: List[commands.Command], compress: bool = False):
        """Create pages for every bot command"""
        categories = {x: [] for x in self.commands_data.keys()}
        for cmd in cmds:
            try:
                if cmd.hidden or not cmd.enabled:
                    continue
                if not await cmd.can_run(ctx):
                    continue
            except commands.CommandError:
                continue
            temp = await self.display_cmd(cmd)
            found = False
            for k, values in self.commands_data.items():
                if cmd.name in values['commands']:
                    categories[k].append(temp)
                    found = True
                    break
            if not found:
                categories['unclassed'].append(temp)
        answer = []
        prefix = await self.bot.prefix_manager.get_prefix(ctx.guild)
        if compress:
            for k, values in categories.items():
                if len(values) == 0:
                    continue
                tr_name = await self.bot._(ctx.channel, f"help.categories.{k}")
                emoji = self.commands_data[k]['emoji']
                title = f"{emoji}  __**{tr_name.capitalize()}**__"
                count = await self.bot._(ctx.channel, "help.cmd-count",
                                         count=len(values),
                                         p=prefix,
                                         cog=k)
                answer.append((title, count))
        else:
            for k, values in categories.items():
                if len(values) == 0:
                    continue
                emoji = self.commands_data[k]['emoji']
                tr_name = await self.bot._(ctx.channel, f"help.categories.{k}")
                if len("\n".join(values)) > 1020:
                    temp = list(values)
                    values = []
                    i = 1
                    for line in temp:
                        if len("\n".join(values+[line])) > 1020:
                            title = (tr_name+' - ' + str(i)) if 'help.' not in tr_name else (k+' - '+str(i))
                            answer.append((f"{emoji}  __**{title.capitalize()}**__", "\n".join(values)))
                            values.clear()
                            i += 1
                        values.append(line)
                    title = (tr_name+' - ' + str(i)) if 'help.' not in tr_name else (k+' - '+str(i))
                    answer.append((f"{emoji}  __**{title.capitalize()}**__", "\n".join(values)))
                else:
                    title = tr_name
                    answer.append((f"{emoji}  __**{title.capitalize()}**__", "\n".join(values)))
        return answer

    async def cog_commands(self, ctx: MyContext, cog: commands.Cog):
        """Create pages for every command of a cog"""
        description = inspect.getdoc(cog)
        page = ""
        form = "**{}**\n\n {} \n{}"
        pages = []
        cog_name = cog.__class__.__name__
        if description is None:
            description = await self.bot._(ctx.channel, "help.no-desc-cog")
        for cmd in sorted([c for c in self.bot.commands], key=self.sort_by_name):
            try:
                if (not await cmd.can_run(ctx)) or cmd.hidden or (not cmd.enabled) or cmd.cog_name != cog_name:
                    continue
            except commands.CommandError:
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
        "Split description, examples and documentation link from the given documentation"
        data = [x.strip() for x in desc.split("\n\n")]
        desc, example, doc = [], [], []
        for p in data:
            if p.startswith("..Example "):
                example.append(p.replace("..Example ", ""))
            elif p.startswith("..Doc "):
                doc.append(p.replace("..Doc ", ""))
            else:
                desc.append(p)
        return (x if len(x) > 0 else None for x in ("\n\n".join(desc), example, doc))

    async def cmd_help(self, ctx: MyContext, cmd: commands.core.Command, use_embed: bool = True):
        """Create pages for a command explanation"""
        desc = cmd.description.strip()
        if desc == '' and cmd.help is not None:
            desc = cmd.help.strip()
        desc, example, doc = await self.extract_info(desc)
        if desc is None:
            desc = await self.bot._(ctx.channel, "help.no-desc-cmd")
        # Prefix
        prefix = await self.bot.get_prefix(ctx.message)
        if isinstance(prefix, list):
            prefix = prefix[-1]
        # Syntax
        syntax = cmd.qualified_name + "** " + cmd.signature
        # Subcommands
        sublist = []
        subcmds = ""
        subs_cant_show = 0
        if isinstance(cmd, commands.core.Group):
            syntax += " ..."
            if not use_embed:
                subcmds = "__{}__".format(str(await self.bot._(ctx.channel, "help.subcmds")).capitalize())
            for x in sorted(cmd.all_commands.values(), key=self.sort_by_name):
                try:
                    if (not x.hidden) and x.enabled and x.name not in sublist and await x.can_run(ctx):
                        if len(subcmds) > 950:
                            subs_cant_show += 1
                        else:
                            subcmds += "\n• {} {}".format(x.name, "*({})*".format(
                                x.short_doc) if len(x.short_doc) > 0 else "")
                            sublist.append(x.name)
                except commands.CommandError:
                    pass
        if subs_cant_show > 0:
            subcmds += "\n" + await self.bot._(ctx.channel, f'help.more-subcmds', count=subs_cant_show)
        # Is enabled
        enabled: list[str] = []
        if not cmd.enabled:
            enabled.append(await self.bot._(ctx.channel, "help.not-enabled"))
        # Checks
        checks = []
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
                        except Exception:
                            pass_check = False
                        if pass_check:
                            checks.append(
                                "✅ "+check_msg_tr[0])
                        else:
                            checks.append('❌ '+check_msg_tr[1])
                    else:
                        self.bot.dispatch("error", ValueError(f"No description for help check {check_name} ({c})"))
                except Exception as err:
                    self.bot.dispatch("error", err, f"While checking {c} in help")
        # Module
        category = "unclassed"
        for key, data in self.commands_data.items():
            categ_commands = data['commands']
            if cmd.name in categ_commands or (cmd.full_parent_name and cmd.full_parent_name.split(" ")[0] in categ_commands):
                category = key
                break
        emoji = self.commands_data[category]['emoji']
        category = emoji + "  " + (await self.bot._(ctx.channel, f"help.categories.{category}")).capitalize()
        if use_embed:
            answer = []
            answer.append([f"**{prefix}{syntax}"])
            answer.append((await self.bot._(ctx.channel, 'help.description'), desc))
            if example is not None:
                answer.append((
                    (await self.bot._(ctx.channel, 'misc.example', count=len(example))).capitalize(),
                    "\n".join(example)
                ))
            if len(subcmds) > 0:
                answer.append((await self.bot._(ctx.channel, 'help.subcmds'), subcmds))
            if len(cmd.aliases) > 0:
                if cmd.full_parent_name:
                    answer.append((await self.bot._(ctx.channel, "help.aliases"), cmd.full_parent_name + " " + " - ".join(cmd.aliases)))
                else:
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
                title = (await self.bot._(ctx.channel, 'misc.example', count=len(example))).capitalize()
                f_examples = '\n'.join(example)
                answer += f"\n__{title}__\n{f_examples}\n"
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
        default_help = commands.DefaultHelpCommand()
        default_help.context = ctx
        default_help._command_impl = self.help_cmd
        # General help
        if command is None:
            mapping = default_help.get_bot_mapping()
            return await default_help.send_bot_help(mapping)
        # Check if it's a cog
        cog = self.bot.get_cog(" ".join(command))
        if cog is not None:
            return await default_help.send_cog_help(cog)
        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        maybe_coro = discord.utils.maybe_coroutine
        keys = command
        cmd = self.bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(default_help.command_not_found, default_help.remove_mentions(keys[0]))
            return await default_help.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(default_help.subcommand_not_found, cmd, default_help.remove_mentions(key))
                return await default_help.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(default_help.subcommand_not_found, cmd, default_help.remove_mentions(key))
                    return await default_help.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await default_help.send_group_help(cmd)
        else:
            return await default_help.send_command_help(cmd)


async def setup(bot):
    await bot.add_cog(Help(bot))
