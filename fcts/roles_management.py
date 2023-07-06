from typing import Literal, Union

import discord
from discord import app_commands
from discord.ext import commands

from libs.arguments import args
from libs.bot_classes import Axobot, MyContext
from libs.checks import checks
from libs.formatutils import FormatUtils


class RolesManagement(commands.Cog):
    "A few commands to manage roles"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "roles_management"
        # maximum of roles granted/revoked by query
        self.max_roles_modifications = 300

    @commands.hybrid_group(name="role", aliases=["roles"])
    @app_commands.default_permissions(manage_roles=True)
    @commands.guild_only()
    async def main_role(self, ctx: MyContext):
        """A few commands to manage roles

        ..Doc moderator.html#emoji-manager"""
        if ctx.subcommand_passed is None and ctx.interaction is None:
            await ctx.send_help(ctx.command)

    @main_role.command(name="set-color", aliases=['set-colour'])
    @app_commands.describe(color="The new color role, preferably in hex format (#ff6699)")
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def role_color(self, ctx: MyContext, role: discord.Role, color: discord.Color):
        """Change a color of a role

        ..Example role set-color "Admin team" red

        ..Doc moderator.html#role-manager"""
        if not ctx.guild.me.guild_permissions.manage_roles:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
            return
        if role.position >= ctx.guild.me.roles[-1].position:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.too-high",r=role.name))
            return
        await role.edit(colour=color,reason=f"Asked by {ctx.author}")
        await ctx.send(await self.bot._(ctx.guild.id,"moderation.role.color-success", role=role.name))

    @main_role.command(name="members-list")
    @commands.cooldown(5, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def role_list(self, ctx: MyContext, *, role: discord.Role):
        """Send the list of members in a role

        ..Example role members-list "Technical team"

        ..Doc moderator.html#role-manager"""
        if not (await checks.has_manage_roles(ctx) or await checks.has_manage_guild(ctx) or await checks.has_manage_msg(ctx)):
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.missing-user-perms"))
            return
        if not ctx.can_send_embed:
            return await ctx.send(await self.bot._(ctx.guild.id,"fun.no-embed-perm"))
        tr_nbr = await self.bot._(ctx.guild.id,'info.info.role-3')
        tr_mbr = await self.bot._(ctx.guild.id,"misc.membres")
        txt = ""
        emb = discord.Embed(title=role.name, color=role.color, timestamp=ctx.message.created_at)
        emb.add_field(name=tr_nbr.capitalize(), value=len(role.members), inline=False)
        nbr = len(role.members)
        if nbr <= 200:
            for i in range(nbr):
                txt += role.members[i].mention+" "
                if i<nbr-1 and len(txt+role.members[i+1].mention) > 1000:
                    emb.add_field(name=tr_mbr.capitalize(), value=txt)
                    txt = ""
            if len(txt) > 0:
                emb.add_field(name=tr_mbr.capitalize(), value=txt)
        emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
        await ctx.send(embed=emb)

    @main_role.command(name="temporary-grant")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def roles_temp_grant(self, ctx: MyContext, role: discord.Role, user: discord.Member,
                               time: commands.Greedy[args.Duration]):
        """Temporary give a role to a member

        ..Example role temporary-grant Slime Theo 1h

        ..Doc moderator.html#role-manager"""
        duration = sum(time)
        if duration == 0:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['time'])
        if duration > 60*60*24*31: # max 31 days
            await ctx.send(await self.bot._(ctx.guild.id, "timers.rmd.too-long"))
            return
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-too-high", r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-roles-higher"))
        await user.add_roles(role, reason=f"Asked by {ctx.author}")
        await self.bot.task_handler.add_task('role-grant', duration, user.id, ctx.guild.id, data={'role': role.id})
        f_duration = await FormatUtils.time_delta(duration, lang=await self.bot._(ctx.guild,'_used_locale'))
        await ctx.send(
            await self.bot._(ctx.guild.id, "moderation.role.temp-grant-success",
                             role=role.name, user=user.mention, time=f_duration),
            allowed_mentions=discord.AllowedMentions.none()
        )


    @main_role.command(name="grant", aliases=["add", "give"])
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def roles_grant(self, ctx: MyContext, role: discord.Role,
                         users: commands.Greedy[Union[discord.Role, discord.Member, Literal['everyone']]]):
        """Give a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role grant Elders everyone

        ..Example role grant Slime Theo AsiliS

        ..Doc moderator.html#role-manager"""
        if len(users) == 0:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['users'])
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-too-high", r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-roles-higher"))
        n_users: set[discord.Member] = set()
        for item in users:
            if item == "everyone":
                item = ctx.guild.default_role
            if isinstance(item, discord.Member):
                if role not in item.roles:
                    n_users.add(item)
            else:
                for member in item.members:
                    if role not in member.roles:
                        n_users.add(member)
        if len(n_users) > 15:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-pending", n=len(n_users)))
        else:
            await ctx.defer()
        count = 0
        for user in n_users:
            if count >= self.max_roles_modifications:
                break
            await user.add_roles(role, reason=f"Asked by {ctx.author}")
            count += 1
        answer = await self.bot._(ctx.guild.id, "moderation.role.give-success", count=count, m=len(n_users))
        if count == self.max_roles_modifications and len(n_users) > count:
            answer += f'\n⚠️ *{await self.bot._(ctx.guild.id, "moderation.role.limit-hit", limit=self.max_roles_modifications)}*'
        if len(n_users) > 50:
            await ctx.reply(answer)
        else:
            await ctx.send(answer)

    @main_role.command(name="revoke", aliases=["remove"])
    @commands.cooldown(1, 30, commands.BucketType.guild)
    @commands.guild_only()
    @commands.check(checks.has_manage_roles)
    async def roles_revoke(self, ctx: MyContext, role: discord.Role,
                           users: commands.Greedy[Union[discord.Role, discord.Member, Literal['everyone']]]):
        """Remove a role to a list of roles/members
        Users list may be either members or roles, or even only one member

        ..Example role revoke VIP @muted

        ..Doc moderator.html#role-manager"""
        if len(users) == 0:
            raise commands.MissingRequiredArgument(ctx.command.clean_params['users'])
        if not ctx.guild.me.guild_permissions.manage_roles:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.mute.cant-mute"))
        my_position = ctx.guild.me.roles[-1].position
        if role.position >= my_position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-too-high",r=role.name))
        if role.position >= ctx.author.roles[-1].position:
            return await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.give-roles-higher"))
        n_users: set[discord.Member] = set()
        for item in users:
            if item == "everyone":
                item = ctx.guild.default_role
            if isinstance(item, discord.Member):
                if role in item.roles:
                    n_users.add(item)
            else:
                for member in item.members:
                    if role in member.roles:
                        n_users.add(member)
        if len(n_users) > 15:
            await ctx.send(await self.bot._(ctx.guild.id, "moderation.role.remove-pending", n=len(n_users)))
        else:
            await ctx.defer()
        count = 0
        for user in n_users:
            if count >= self.max_roles_modifications:
                break
            await user.remove_roles(role,reason="Asked by {ctx.author}")
            count += 1
        answer = await self.bot._(ctx.guild.id, "moderation.role.remove-success",count=count,m=len(n_users))
        if count == self.max_roles_modifications and len(n_users) > count:
            answer += f'\n⚠️ *{await self.bot._(ctx.guild.id, "moderation.role.limit-hit", limit=self.max_roles_modifications)}*'
        if len(n_users) > 50:
            await ctx.reply(answer)
        else:
            await ctx.send(answer)


async def setup(bot: Axobot):
    await bot.add_cog(RolesManagement(bot))
