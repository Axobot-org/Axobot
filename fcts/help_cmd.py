import copy
import inspect
import json
from typing import List, Optional, TypedDict

import discord
from discord.ext import commands

from libs.bot_classes import Axobot, MyContext
from libs.help_cmd import (get_command_desc_translation,
                           get_command_description,
                           get_command_name_translation, get_command_signature)


class CommandsCategoryData(TypedDict):
    emoji: str
    commands: list[str]

class Help(commands.Cog):
    "Help commands"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "help_cmd"
        self.old_cmd = bot.remove_command("help")
        self.help_color = 0x7ED321
        self.help_color_dm = 0xD6FFA9
        with open('fcts/help.json', 'r', encoding="utf-8") as file:
            self.commands_data: dict[str, CommandsCategoryData] = json.load(file)

    @property
    def doc_url(self):
        return (
            "https://axobot.readthedocs.io/en/main/",
            "https://axobot.readthedocs.io/en/develop/",
            "https://axobot.readthedocs.io/en/latest/",
        )[self.bot.entity_id]

    async def cog_unload(self):
        self.bot.remove_command("help")
        self.bot.add_command(self.old_cmd)

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

    async def help_command(self, ctx: MyContext, commands_arg: Optional[list[str]] = None):
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

            if commands_arg is not None and " ".join(commands_arg).lower() in self.commands_data:
                categ_name = [" ".join(commands_arg).lower()]
            else:
                translated_categories = {
                    k: await self.bot._(ctx.channel, f"help.categories.{k}")
                    for k in self.commands_data.keys()
                }
                if commands_arg is None:
                    categ_name = []
                else:
                    categ_name = [k for k, v in translated_categories.items() if v.lower() == " ".join(commands_arg).lower()]

            if len(categ_name) == 1: # cog name
                if categ_name[0] == "unclassed":
                    referenced_commands = {x for v in self.commands_data.values() for x in v['commands']}
                    temp = [c for c in self.bot.commands if c.name not in referenced_commands]
                else:
                    temp = [c for c in self.bot.commands if c.name in self.commands_data[categ_name[0]]['commands']]
                pages = await self.all_commands(ctx, sorted(temp, key=self.sort_by_name))
                if len(pages) == 0 and ctx.guild is None:
                    pages = [await self.bot._(ctx.channel, "help.cog-empty-dm")]
            elif not commands_arg:  # no command
                compress: bool = await self.bot.get_config(ctx.guild.id, 'compress_help') if ctx.guild else False
                pages = await self.all_commands(ctx, sorted(
                    [c for c in self.bot.commands],
                    key=self.sort_by_name), compress=compress)
                if ctx.guild is None:
                    title = await self.bot._(ctx.channel, "help.embed_title_dm")
                else:
                    title = await self.bot._(ctx.channel, "help.embed_title", u=ctx.author.display_name)
            elif len(commands_arg) == 1:  # Unique command name?
                name = commands_arg[0]
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
                        await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                        return
                    pages = await self.cmd_help(ctx, command, destination.permissions_for(bot_usr).embed_links)
            else:  # sub-command name?
                name = commands_arg[0]
                command = self.bot.all_commands.get(name)
                if command is None:
                    await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=name))
                    return
                for key in commands_arg[1:]:
                    try:
                        command = command.all_commands.get(key)
                        if command is None:
                            await ctx.send(await self.bot._(ctx.channel, "help.subcmd-not-found", name=key))
                            return
                    except AttributeError:
                        await ctx.send(await self.bot._(ctx.channel, "help.no-subcmd", cmd=command.name))
                        return
                pages = await self.cmd_help(ctx, command, destination.permissions_for(bot_usr).embed_links)

            ft = await self.bot._(ctx.channel, "help.footer")
            prefix = await self.bot.prefix_manager.get_prefix(ctx.guild)
        if len(pages) == 0:
            self.bot.dispatch("error", ValueError(f"Unable to find help for the command {' '.join(commands_arg)}"))
            await ctx.send(await self.bot._(ctx.channel, "help.cmd-not-found", cmd=" ".join(commands_arg)))
            return
        if destination.permissions_for(bot_usr).embed_links:
            if ctx.guild is not None:
                embed_colour = ctx.guild.me.color if ctx.guild.me.color != discord.Colour.default() else discord.Colour(self.help_color)
            else:
                embed_colour = discord.Colour(self.help_color_dm)
            if isinstance(pages[0], str): # use description
                for page in pages:
                    embed = discord.Embed(title=title, description=page, color=embed_colour, timestamp=self.bot.utcnow())
                    embed.set_footer(text=ft.format(prefix))
                    title = ""
                    await ctx.send(embed=embed)
            else: # use fields
                embed = discord.Embed(title=title, color=embed_colour, timestamp=self.bot.utcnow())
                embed.set_footer(text=ft.format(prefix))
                for page in pages:
                    if len(page) == 1:
                        embed.title = page[0]
                        continue
                    embed.add_field(name=page[0], value=page[1], inline=False)
                await ctx.send(embed=embed)
        else:
            for page in pages:
                if isinstance(page, str):
                    await ctx.send(page)
                else:
                    await ctx.send("\n".join(page))

    async def _display_cmd(self, ctx: MyContext, cmd: commands.Command):
        name = await get_command_name_translation(ctx, cmd)
        short = await get_command_desc_translation(ctx, cmd) or cmd.short_doc.strip()
        return f"• **{name}**\t\t*{short}*" if short else f"• **{name}**"

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
            temp = await self._display_cmd(ctx, cmd)
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
            text = await self._display_cmd(ctx, cmd)
            if len(page+text) > 1900:
                pages.append(form.format(cog_name, description, page))
                page = text
            else:
                page += "\n"+text
        pages.append(form.format(cog_name, description, page))
        return pages

    async def _get_subcommands(self, ctx: MyContext, cmd: commands.Group):
        ""
        subcmds = ""
        subs_cant_show = 0
        sublist = []
        for subcommand in sorted(cmd.all_commands.values(), key=self.sort_by_name):
            try:
                if (not subcommand.hidden) and subcommand.enabled and subcommand.name not in sublist and await subcommand.can_run(ctx):
                    if len(subcmds) > 950:
                        subs_cant_show += 1
                    else:
                        name = await get_command_name_translation(ctx, subcommand)
                        if (description := await get_command_desc_translation(ctx, subcommand)) is None:
                            description = subcommand.short_doc
                        desc = f"*({description})*" if len(description) > 0 else ""
                        subcmds += f"\n• {name} {desc}"
                        sublist.append(subcommand.name)
            except commands.CommandError:
                pass
        return subcmds, subs_cant_show

    async def cmd_help(self, ctx: MyContext, cmd: commands.Command, use_embed: bool = True):
        """Create pages for a command explanation"""
        desc, examples, doc = await get_command_description(ctx, cmd)
        # Syntax
        syntax = await get_command_signature(ctx, cmd)
        # Subcommands
        if isinstance(cmd, commands.Group):
            syntax += " ..."
            subcmds, subs_cant_show = await self._get_subcommands(ctx, cmd)
            if not use_embed:
                subcmds = "__" + (await self.bot._(ctx.channel, "help.subcmds")).capitalize() + "__\n" + subcmds
            if subs_cant_show > 0:
                subcmds += "\n" + await self.bot._(ctx.channel, 'help.more-subcmds', count=subs_cant_show)
        else:
            subcmds = ""
        # Is enabled
        enabled: list[str] = []
        if not cmd.enabled:
            enabled.append(await self.bot._(ctx.channel, "help.not-enabled"))
        # Checks
        checks = []
        if len(cmd.checks) > 0:
            maybe_coro = discord.utils.maybe_coroutine
            for check in cmd.checks:
                try:
                    if 'guild_only.<locals>.predicate' in str(check):
                        check_name = 'guild_only'
                    elif 'is_owner.<locals>.predicate' in str(check):
                        check_name = 'is_owner'
                    elif 'bot_has_permissions.<locals>.predicate' in str(check):
                        check_name = 'bot_has_permissions'
                    elif '_has_permissions.<locals>.predicate' in str(check):
                        check_name = 'has_permissions'
                    else:
                        check_name = check.__name__
                    check_msg_tr = await self.bot._(ctx.channel, f'help.check-desc.{check_name}')
                    if 'help.check-desc' not in check_msg_tr:
                        try:
                            pass_check = await maybe_coro(check, ctx)
                        except Exception:
                            pass_check = False
                        if pass_check:
                            checks.append(
                                "✅ "+check_msg_tr[0])
                        else:
                            checks.append('❌ '+check_msg_tr[1])
                    else:
                        self.bot.dispatch("error", ValueError(f"No description for help check {check_name} ({check})"))
                except Exception as err:
                    self.bot.dispatch("error", err, f"While checking {check} in help")
        # Module
        category = "unclassed"
        for key, data in self.commands_data.items():
            categ_commands = data['commands']
            if cmd.name in categ_commands or (cmd.full_parent_name and cmd.full_parent_name.split(" ")[0] in categ_commands):
                category = key
                break
        emoji = self.commands_data[category]['emoji']
        category = emoji + "  " + (await self.bot._(ctx.channel, f"help.categories.{category}")).capitalize()
        # format the final embed/message
        if use_embed:
            answer = []
            answer.append([f"{syntax}"])
            answer.append((await self.bot._(ctx.channel, 'help.description'), desc))
            if examples is not None:
                answer.append((
                    (await self.bot._(ctx.channel, 'misc.example', count=len(examples))).capitalize(),
                    "\n".join(examples)
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
                doc_url = self.doc_url + doc
                answer.append(((await self.bot._(ctx.channel, 'misc.doc')).capitalize(), doc_url))
            answer.append(((await self.bot._(ctx.channel, 'misc.category')).capitalize(), category))
            return answer
        else:
            answer = f"{syntax}\n\n{desc}\n\n"
            if examples is not None:
                title = (await self.bot._(ctx.channel, 'misc.example', count=len(examples))).capitalize()
                f_examples = '\n'.join(examples)
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
                doc_url = self.doc_url + doc
                answer.append(((await self.bot._(ctx.channel, 'misc.doc')).capitalize(), doc_url))
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
