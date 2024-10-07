import asyncio
import logging
from typing import Literal

import discord
from cachetools import TTLCache
from discord.ext import commands

from core.bot_classes import SUPPORT_GUILD_ID, Axobot
from core.enums import ServerWarningType
from core.safedict import SafeDict


class Welcomer(commands.Cog):
    """Cog which manages the departure and arrival of members in the servers"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "welcomer"
        self.log = logging.getLogger("bot.welcomer")
        # List of users who won't receive welcome/leave messages :
        #   someone, Awhikax's alt, Z_Jumper
        self.no_message = {392766377078816789, 504269440872087564, 552273019020771358}
        self.join_cache = TTLCache[tuple[int, int], int](maxsize=50_000, ttl=90)


    @commands.Cog.listener()
    async def on_member_join(self, member:discord.Member):
        """Main function called when a member joins a server"""
        if not self.bot.database_online:
            return
        await self.bot.get_cog("ServerConfig").update_memberchannel(member.guild)
        if "MEMBER_VERIFICATION_GATE_ENABLED" not in member.guild.features:
            await self.send_msg(member, "welcome")
            self.bot.loop.create_task(self.give_roles(member))
            await self.give_roles_back(member)
            await self.check_muted(member)
            if member.guild.id == SUPPORT_GUILD_ID.id:
                await self.check_owner_server(member)
                await self.check_support(member)
                await self.check_contributor(member)

    @commands.Cog.listener()
    async def on_member_update(self, before:discord.Member, after:discord.Member):
        """Main function called when a member got verified in a community server"""
        if before.pending and not after.pending:
            if "MEMBER_VERIFICATION_GATE_ENABLED" in after.guild.features:
                await self.send_msg(after, "welcome")
                self.bot.loop.create_task(self.give_roles(after))
                await self.give_roles_back(after)
                await self.check_muted(after)


    @commands.Cog.listener()
    async def on_member_remove(self, member:discord.Member):
        """Fonction principale appelée lorsqu'un membre quitte un serveur"""
        if not self.bot.database_online:
            return
        await self.bot.get_cog("ServerConfig").update_memberchannel(member.guild)
        if "MEMBER_VERIFICATION_GATE_ENABLED" not in member.guild.features or not member.pending:
            await self.send_msg(member, "leave")
        await self.bot.get_cog("Events").check_user_left(member)

    async def _is_raider(self, member: discord.Member):
        "Use the AntiRaid cog to check if a member has just been detected as a potential raider"
        if raid_cog := self.bot.get_cog("AntiRaid"):
            if (self.bot.utcnow() - member.joined_at).total_seconds() < 3:
                # wait a few seconds to let the cog do its job
                await asyncio.sleep(2)
            return await raid_cog.is_raider(member)
        return False

    async def send_msg(self, member: discord.Member, event_type: Literal["welcome", "leave"]):
        """Envoie un message de bienvenue/départ dans le serveur"""
        if self.bot.zombie_mode:
            return
        text: str | None = await self.bot.get_config(member.guild.id, event_type)
        if member.id in self.no_message or (event_type == "welcome" and await self._is_raider(member)):
            return
        if self.bot.get_cog("Utilities").sync_check_any_link(member.display_name) is not None:
            return
        if text:
            channel: discord.TextChannel | None = await self.bot.get_config(member.guild.id, "welcome_channel")
            if channel is None:
                return
            if event_type == "leave" and (msg_id := self.join_cache.get((member.guild.id, member.id))):
                # if the user just joined, delete the welcome message and abort
                if await self.delete_cached_welcome_message(channel, msg_id):
                    # if the welcome message was deleted, don't send the leave message
                    return
            botormember = await self.bot._(member.guild, "misc.bot" if member.bot else "misc.member")
            try:
                text = text.format_map(SafeDict(
                    user=member.mention if event_type=="welcome" else member.display_name,
                    user_idname=str(member),
                    user_id=str(member.id),
                    server=member.guild.name,
                    owner=member.guild.owner.display_name if member.guild.owner else "",
                    member_count=member.guild.member_count,
                    type=botormember
                ))
                silent: bool = (
                    False if event_type == "leave"
                    else await self.bot.get_config(member.guild.id, "welcome_silent_mention")
                )
                msg = await channel.send(text, silent=silent)
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
            self.log.warning("Failed to delete welcome message %s in %s | %s: %s", message_id, channel.guild.id, channel.id, err)
        except Exception as err:
            self.bot.dispatch("error", err, f"While deleting welcome message in {channel.guild.id} | {channel.id}")
        return False

    async def check_owner_server(self, member: discord.Member):
        """Check if a newscommer of the support server is the owner of a server"""
        servers = [x for x in self.bot.guilds if x.owner == member and x.member_count > 10]
        if len(servers) > 0:
            role = member.guild.get_role(486905171738361876)
            if role is None:
                self.log.warning("Owner role not found in support server")
                return
            if role not in member.roles:
                await member.add_roles(role, reason="This user support me")

    async def check_support(self, member: discord.Member):
        """Check if a newscommer of the support server is part of the bot support team"""
        if await self.bot.get_cog("Users").has_userflag(member, "support"):
            role = member.guild.get_role(412340503229497361)
            if role is not None:
                await member.add_roles(role)
            else:
                self.log.warning("Support role not found in support server")

    async def check_contributor(self, member: discord.Member):
        """Check if a newscommer of the support server is a contributor"""
        if await self.bot.get_cog("Users").has_userflag(member, "contributor"):
            role = member.guild.get_role(552428810562437126)
            if role is not None:
                await member.add_roles(role)
            else:
                self.log.warning("Contributor role not found in support server")

    async def give_roles_back(self, member: discord.Member):
        """Give roles rewards/muted role to new users"""
        if not self.bot.database_online:
            return
        used_xp_type: str = await self.bot.get_config(member.guild.id, "xp_type")
        if used_xp_type == "global":
            xp = await self.bot.get_cog("Xp").db_get_xp(member.id, None)
        else:
            xp = await self.bot.get_cog("Xp").db_get_xp(member.id, member.guild.id)
        if xp is not None:
            await self.bot.get_cog("Xp").give_rr(
                member,
                (await self.bot.get_cog("Xp").calc_level(xp, used_xp_type))[0],
                await self.bot.get_cog("Xp").rr_list_role(member.guild.id)
            )

    async def check_muted(self, member: discord.Member):
        """Give the muted role to that user if needed"""
        mod_cog = self.bot.get_cog("Moderation")
        if not mod_cog or not self.bot.database_online:
            return
        if await mod_cog.is_muted(member.guild, member, None):
            role = await mod_cog.get_muted_role(member.guild)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass

    async def give_roles(self, member: discord.Member):
        """Give new roles to new users"""
        try:
            roles: list[discord.Role] | None = await self.bot.get_config(member.guild.id, "welcome_roles")
            if roles is None:
                return
            for role in roles:
                try:
                    await member.add_roles(role, reason=await self.bot._(member.guild.id,"logs.reason.welcome_roles"))
                except discord.errors.Forbidden:
                    self.bot.dispatch(
                        "server_warning",
                        ServerWarningType.WELCOME_ROLE_MISSING_PERMISSIONS,
                        member.guild,
                        role=role,
                        user=member
                    )
        except discord.errors.NotFound:
            pass
        except Exception as err:
            self.bot.dispatch("error", err)


async def setup(bot):
    await bot.add_cog(Welcomer(bot))
