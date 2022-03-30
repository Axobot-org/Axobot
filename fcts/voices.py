import discord
import aiohttp
from discord.ext import commands

from fcts import checks
from utils import Zbot, MyContext


class VoiceChannels(commands.Cog):

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "voices"
        self.names = list()
        self.channels = dict()
        self.table = 'voices_chats'
        self.db_get_channels()
    
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.bot.database_online:
            self.bot.unload_extension("fcts.voices")

    def db_get_channels(self):
        if not self.bot.database_online:
            return
        cnx = self.bot.cnx_frm
        c = cnx.cursor(dictionary = True)
        t = '' if self.bot.beta else 'NOT '
        c.execute(f'SELECT * FROM {self.table} WHERE {t}BETA')
        for row in c:
            guild = int(row['guild'])
            ch = int(row['channel'])
            self.channels[guild] = self.channels.get(guild, list()) + [ch]
        c.close()

    def db_add_channel(self, channel: discord.VoiceChannel):
        cnx = self.bot.cnx_frm
        c = cnx.cursor(dictionary = True)
        arg = (channel.guild.id, channel.id, self.bot.beta)
        c.execute(f"INSERT INTO `{self.table}` (`guild`,`channel`,`beta`) VALUES (%s, %s, %s)", arg)
        cnx.commit()
        c.close()
        prev = self.channels.get(channel.guild.id, list())
        self.channels[channel.guild.id] = prev + [channel.id]

    def db_delete_channel(self, channel: discord.VoiceChannel):
        cnx = self.bot.cnx_frm
        c = cnx.cursor(dictionary = True)
        arg = (channel.guild.id, channel.id)
        c.execute(f"DELETE FROM {self.table} WHERE guild=%s AND channel=%s", arg)
        cnx.commit()
        c.close()
        try:
            self.channels[channel.guild.id].remove(channel.id)
        except KeyError:
            return

    async def give_roles(self, member: discord.Member, remove=False):
        if not self.bot.database_online:
            return
        if not member.guild.me.guild_permissions.manage_roles:
            self.bot.log.info(f"[Voice] Missing \"manage_roles\" permission on guild \"{member.guild.name}\"")
            return
        g = member.guild
        rolesID = await self.bot.get_config(member.guild.id, 'voice_roles')
        if not rolesID:
            return
        rolesID = list(map(int, rolesID.split(';')))
        roles = [g.get_role(x) for x in rolesID]
        pos = g.me.top_role.position
        roles = filter(lambda x: (x is not None) and (x.position < pos), roles)
        if remove:
            await member.remove_roles(*roles, reason="Left the voice chat")
        else:
            await member.add_roles(*roles, reason="Joined a voice chat")
    
    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Deletes a voice channel in the database when deleted in Discord"""
        try:
            if isinstance(channel, discord.VoiceChannel):
                self.db_delete_channel(channel)
            # other cases are not interesting
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e)
        

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Check if a member joined/left a voice channel"""
        try:
            if before.channel == after.channel:
                return
            if not self.bot.database_online:
                return
            config = await self.bot.get_config(member.guild.id, 'voice_channel')
            if config is None:  # if nothing was setup
                return
            config = [int(x) for x in config.split(';') if x.isnumeric() and len(x)>5]
            if len(config) == 0:
                return
            if after.channel is not None and after.channel.id in config:
                if before.channel is not None and len(before.channel.members) == 0: # move from another channel which is now empty
                    if (member.guild.id in self.channels.keys()) and (before.channel.id in self.channels[member.guild.id]):
                        # if they come from an automated channel, we move them back if the channel is now empty
                        await member.move_to(before.channel)
                        return
                await self.create_channel(member)
            if (before.channel is not None) and (member.guild.id in self.channels.keys()) and (before.channel.id in self.channels[member.guild.id]):
                await self.delete_channel(before.channel)
            if after.channel is None:
                await self.give_roles(member, remove=True)
            if before.channel is None:
                await self.give_roles(member)
        except Exception as e:
            await self.bot.get_cog("Errors").on_error(e)

    async def create_channel(self, member: discord.Member):
        """Create a new voice channel
        The member will get "Manage channel" permissions automatically"""
        category = await self.bot.get_config(member.guild.id, 'voice_category')
        if category is None:  # if nothing was setup
            return
        category = [int(x) for x in category.split(';') if x.isnumeric() and len(x)>5]
        if len(category) == 0:
            return
        voice_category: discord.CategoryChannel = member.guild.get_channel(category[0])
        if not isinstance(voice_category, discord.CategoryChannel):
            return
        perms = voice_category.permissions_for(member.guild.me)
        # if bot is missing perms: abort
        if not (perms.manage_channels and perms.move_members):
            self.bot.log.info(f"[Voice] Missing \"manage_channels, move_members\" permission on guild \"{member.guild.id}\"")
            return
        if not (member.voice.channel.permissions_for(member.guild.me)).move_members:
            self.bot.log.info(f"[Voice] Missing \"move_members\" permission on channel \"{member.voice.channel}\"")
            return
        p = len(voice_category.channels)
        # try to calculate the correct permissions
        d = member.guild.me.guild_permissions
        d = {k: v for k, v in dict(d).items() if v}
        over = {
            member: discord.PermissionOverwrite(**d),
            member.guild.me: discord.PermissionOverwrite(**d)}
        # remove manage roles cuz DISCOOOOOOOOOOORD
        over[member].manage_roles = None
        over[member.guild.me].manage_roles = None
        # build channel name from config and random
        chan_name = await self.bot.get_config(member.guild.id, 'voice_channel_format')
        args = {'user': str(member)}
        if "{random}" in chan_name:
            args['random'] = await self.get_names()
        chan_name = chan_name.format_map(self.bot.SafeDict(args))
        # actually create the channel
        new_channel = await voice_category.create_voice_channel(name=chan_name, position=p, overwrites=over)
        # move user
        await member.move_to(new_channel)
        # add to database
        self.db_add_channel(new_channel)

    async def delete_channel(self, channel: discord.VoiceChannel):
        """Delete an unusued channel if no one is in"""
        if len(channel.members) == 0 and channel.permissions_for(channel.guild.me).manage_channels:
            await channel.delete(reason="Unusued")
            self.db_delete_channel(channel)

    async def get_names(self):
        if len(self.names) != 0:
            return self.names.pop()
        async with aiohttp.ClientSession() as session:
            h = {'X-Api-Key': self.bot.others['random_api_token']}
            async with session.get('https://randommer.io/api/Name?nameType=surname&quantity=20', headers=h) as resp:
                self.names = await resp.json()
        return self.names.pop()

    @commands.command(name="voice-clean")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_channels=True)
    @commands.check(checks.database_connected)
    async def voice_clean(self, ctx: MyContext):
        """Delete every unusued voice channels previously generated by the bot
        
        ..Doc server.html#voice-channels-managment"""
        if not ctx.guild.id in self.channels.keys() or len(self.channels[ctx.guild.id]) == 0:
            await ctx.send(await self.bot._(ctx.guild.id, "voices", "no-channel"))
            return
        i = 0
        temp = list()
        for chan in self.channels[ctx.guild.id]:
            d_chan = ctx.guild.get_channel(chan)
            if d_chan is not None and len(d_chan.members) == 0:
                await d_chan.delete(reason="unusued")
                temp.append(d_chan)
                i += 1
        for chan in temp:
            self.db_delete_channel(chan)
        await ctx.send(await self.bot._(ctx.guild.id, "voices", "deleted", i=i))


def setup(bot):
    if bot.database_online:
        bot.add_cog(VoiceChannels(bot))
