from typing import Literal, Optional

import discord
from discord.ext import commands
from cachingutils import Cache

from libs.bot_classes import Axobot
from libs.enums import ServerWarningType
from libs.serverconfig.options_list import options


class Welcomer(commands.Cog):
    """Cog which manages the departure and arrival of members in the servers"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "welcomer"
        # List of users who won't receive welcome/leave messages :
        #   someone, Awhikax's alt, Z_Jumper
        self.no_message = {392766377078816789, 504269440872087564, 552273019020771358}
        self.join_cache = Cache[tuple[int, int], int](timeout=60)


    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        """Main function called when a member joins a server"""
        if self.bot.database_online:
            # If axobot is already there, let it handle it
            if await self.bot.check_axobot_presence(guild=member.guild):
                return
            await self.bot.get_cog("ServerConfig").update_memberChannel(member.guild)
            if "MEMBER_VERIFICATION_GATE_ENABLED" not in member.guild.features:
                await self.send_msg(member, "welcome")
                self.bot.loop.create_task(self.give_roles(member))
                await self.give_roles_back(member)
                await self.check_muted(member)
                if member.guild.id==356067272730607628:
                    await self.check_owner_server(member)
                    await self.check_support(member)
                    await self.check_contributor(member)

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        """Main function called when a member got verified in a community server"""
        # If axobot is already there, let it handle it
        if await self.bot.check_axobot_presence(guild=before.guild):
            return
        if before.pending and not after.pending:
            if "MEMBER_VERIFICATION_GATE_ENABLED" in after.guild.features:
                await self.send_msg(after, "welcome")
                self.bot.loop.create_task(self.give_roles(after))
                await self.give_roles_back(after)
                await self.check_muted(after)


    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        """Fonction principale appelée lorsqu'un membre quitte un serveur"""
        if self.bot.database_online:
            # If axobot is already there, let it handle it
            if await self.bot.check_axobot_presence(guild=member.guild):
                return
            await self.bot.get_cog("ServerConfig").update_memberChannel(member.guild)
            if "MEMBER_VERIFICATION_GATE_ENABLED" not in member.guild.features or not member.pending:
                await self.send_msg(member, "leave")
            await self.bot.get_cog('Events').check_user_left(member)

    async def send_msg(self, member: discord.Member, event_type: Literal["welcome", "leave"]):
        """Envoie un message de bienvenue/départ dans le serveur"""
        if self.bot.zombie_mode:
            return
        text: Optional[str] = await self.bot.get_config(member.guild.id, event_type)
        if member.id in self.no_message or (event_type == "welcome" and await self.raid_check(member)):
            return
        if self.bot.get_cog('Utilities').sync_check_any_link(member.name) is not None:
            return
        if text:
            channel: Optional[discord.TextChannel] = await self.bot.get_config(member.guild.id, 'welcome_channel')
            if channel is None:
                return
            if event_type == "leave" and (msg_id := self.join_cache.get((member.guild.id, member.id))):
                # if the user just joined, delete the welcome message and abort
                if await self.delete_cached_welcome_message(channel, msg_id):
                    # if the welcome message was deleted, don't send the leave message
                    return
            text = await self.bot.get_cog('Utilities').clear_msg(text, ctx=None)
            botormember = await self.bot._(member.guild, "misc.bot" if member.bot else "misc.member")
            try:
                text = text.format_map(self.bot.SafeDict(
                    user=member.mention if event_type=='welcome' else member.name,
                    user_idname=str(member),
                    user_id=str(member.id),
                    server=member.guild.name,
                    owner=member.guild.owner.name,
                    member_count=member.guild.member_count,
                    type=botormember))
                text = await self.bot.get_cog("Utilities").clear_msg(text, everyone=False)
                msg = await channel.send(text)
                if event_type == "welcome":
                    self.join_cache[member.guild.id, member.id] = msg.id
            except discord.Forbidden:
                self.bot.dispatch("server_warning",
                                    ServerWarningType.WELCOME_MISSING_TXT_PERMISSIONS,
                                    member.guild,
                                    channel=channel,
                                    is_join=event_type == "welcome")
            except Exception as err:
                self.bot.dispatch("error", err, f"{member.guild} | {channel.name}")

    async def delete_cached_welcome_message(self, channel: discord.TextChannel, message_id: int):
        "Try to delete a cached welcome message"
        # Check if the guild has enabled this feature
        if not await self.bot.get_config(channel.guild.id, "delete_welcome_on_quick_leave"):
            return False
        try:
            msg = await channel.fetch_message(message_id)
            await msg.delete()
            return True
        except discord.HTTPException as err:
            self.bot.log.debug(f"Failed to delete welcome message {message_id} in {channel.guild.id} | {channel.id}: {err}")
        except Exception as err:
            self.bot.dispatch("error", err, f"While deleting welcome message in {channel.guild.id} | {channel.id}")
        return False

    async def check_owner_server(self, member: discord.Member):
        """Vérifie si un nouvel arrivant est un propriétaire de serveur"""
        servers = [x for x in self.bot.guilds if x.owner == member and x.member_count > 10]
        if len(servers) > 0:
            role = member.guild.get_role(486905171738361876)
            if role is None:
                self.bot.log.warning('[check_owner_server] Owner role not found')
                return
            if role not in member.roles:
                await member.add_roles(role,reason="This user support me")

    async def check_support(self, member: discord.Member):
        """Vérifie si un nouvel arrivant fait partie du support"""
        if await self.bot.get_cog('Users').has_userflag(member, 'support'):
            role = member.guild.get_role(412340503229497361)
            if role is not None:
                await member.add_roles(role)
            else:
                self.bot.log.warning('[check_support] Support role not found')

    async def check_contributor(self, member: discord.Member):
        """Vérifie si un nouvel arrivant est un contributeur"""
        if await self.bot.get_cog('Users').has_userflag(member, 'contributor'):
            role = member.guild.get_role(552428810562437126)
            if role is not None:
                await member.add_roles(role)
            else:
                self.bot.log.warning('[check_contributor] Contributor role not found')

    async def give_roles_back(self, member: discord.Member):
        """Give roles rewards/muted role to new users"""
        if not self.bot.database_online:
            return
        used_xp_type: str = await self.bot.get_config(member.guild.id, "xp_type")
        if used_xp_type == "global":
            xp = await self.bot.get_cog('Xp').bdd_get_xp(member.id, None)
        else:
            xp = await self.bot.get_cog('Xp').bdd_get_xp(member.id, member.guild.id)
        if xp is not None and len(xp) == 1:
            await self.bot.get_cog('Xp').give_rr(
                member,
                (await self.bot.get_cog('Xp').calc_level(xp[0]['xp'],used_xp_type))[0],
                await self.bot.get_cog('Xp').rr_list_role(member.guild.id)
            )

    async def check_muted(self, member: discord.Member):
        """Give the muted role to that user if needed"""
        modCog = self.bot.get_cog("Moderation")
        if not modCog or not self.bot.database_online:
            return
        if await modCog.is_muted(member.guild, member, None):
            role = await modCog.get_muted_role(member.guild)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass


    async def kick(self, member: discord.Member, reason: str):
        # if user is too high
        if member.roles[-1].position >= member.guild.me.roles[-1].position:
            return False
        # try to send a DM but don't mind if we can't
        try:
            await member.send(await self.bot._(member, "moderation.raid-kicked", guild=member.guild.name))
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await member.guild.kick(member, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            return False
        else:
            await self.bot.get_cog("Moderation").send_modlogs("kick", member, self.bot.user, member.guild, reason=reason)
            return True

    async def ban(self, member: discord.Member, reason: str, duration: int = None):
        # if user is too high
        if member.roles[-1].position >= member.guild.me.roles[-1].position:
            return False
        # try to send a DM but don't mind if we can't
        try:
            await member.send(await self.bot._(member, "moderation.raid-banned", guild=member.guild.name))
        except (discord.Forbidden, discord.HTTPException):
            pass
        try:
            await member.guild.ban(member, reason=reason)
        except (discord.Forbidden, discord.HTTPException):
            return False
        else:
            if duration:
                await self.bot.task_handler.add_task('ban', duration, member.id, member.guild.id)
            log = str(await self.bot._(member.guild.id,"logs.ban")).format(member=member,reason=reason,case=None)
            await self.bot.get_cog("Events").send_logs_per_server(member.guild,"ban",log,member.guild.me)
            return True

    async def raid_check(self, member: discord.Member):
        # if guild is unavailable or the bot left the guild
        if member.guild is None or member.guild.me is None:
            return False
        level_name: str = await self.bot.get_config(member.guild.id, "anti_raid")
        # if level is unreadable or bot can't kick
        if level_name != "none" or not member.guild.channels[0].permissions_for(member.guild.me).kick_members:
            return
        level: int = options["anti_raid"]["values"].index(level_name)
        can_ban = member.guild.get_member(self.bot.user.id).guild_permissions.ban_members
        account_created_since = (self.bot.utcnow() - member.created_at).total_seconds()
        # Level 4
        if level >= 4:
            if account_created_since <= 86400: # kick accounts created less than 1d before
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 86400})
                    return True
            if account_created_since <= 3600 and can_ban: # ban (2w) members created less than 1h before
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), 86400*14):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600,
                        "duration": 86400*14
                    })
                    return True
            elif account_created_since <= 3600*3 and can_ban: # ban (1w) members created less than 3h before
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.young"), 86400*7):
                    self.bot.dispatch("antiraid_ban", member, {
                        "account_creation_treshold": 3600*3,
                        "duration": 86400*7
                    })
                    return True
        # Level 3 or more
        if level >= 3 and can_ban:
            # ban (1w) members with invitations in their nickname
            if self.bot.get_cog('Utilities').sync_check_discord_invite(member.name) is not None:
                if await self.ban(member, await self.bot._(member.guild.id,"logs.reason.invite"), 86400*7):
                    self.bot.dispatch("antiraid_ban", member, {
                        "discord_invite": True,
                        "duration": 86400*7
                    })
                    return True
            if account_created_since <= 3600*12: # kick accounts created less than 45min before
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 3600*12})
                    return True
        # Level 2 or more
        if level >= 2: # kick accounts created less than 15min before
            if account_created_since <= 3600*2:
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.young")):
                    self.bot.dispatch("antiraid_kick", member, {"account_creation_treshold": 3600*2})
                    return True
        # Level 1 or more
        if level >= 1: # kick members with invitations in their nickname
            if self.bot.get_cog('Utilities').sync_check_discord_invite(member.name) is not None:
                if await self.kick(member,await self.bot._(member.guild.id,"logs.reason.invite")):
                    self.bot.dispatch("antiraid_kick", member, {"discord_invite": True})
                    return True
        # Nothing got triggered
        return False


    async def give_roles(self, member: discord.Member):
        """Give new roles to new users"""
        try:
            roles: Optional[list[discord.Role]] = await self.bot.get_config(member.guild.id, "welcome_roles")
            if roles is None:
                return
            for role in roles:
                try:
                    await member.add_roles(role,reason=await self.bot._(member.guild.id,"logs.reason.welcome_roles"))
                except discord.errors.Forbidden:
                    await self.bot.get_cog('Events').send_logs_per_server(
                        member.guild,
                        "error",
                        await self.bot._(member.guild, "welcome.error-give-roles", r=role.name, u=str(member)),
                        member.guild.me
                    )
        except discord.errors.NotFound:
            pass
        except Exception as err:
            self.bot.dispatch("error", err)


async def setup(bot):
    await bot.add_cog(Welcomer(bot))
