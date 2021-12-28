import discord
import typing
from discord.ext import commands
from utils import Zbot, MyContext

class Perms(commands.Cog):
    """Cog with a single command, allowing you to see the permissions of a member or a role in a channel."""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "perms"
        chan_perms = [key for key,value in discord.Permissions().all_channel() if value]
        self.perms_name = {'general':[key for key,value in discord.Permissions().general() if value],
            'text':[key for key,value in discord.Permissions().text() if value],
            'voice':[key for key,value in discord.Permissions().voice() if value]}
        self.perms_name['common_channel'] = [x for x in chan_perms if x in self.perms_name['general']]


    @commands.command(name='perms', aliases=['permissions'])
    @commands.guild_only()
    async def check_permissions(self, ctx: MyContext, channel:typing.Optional[typing.Union[discord.TextChannel,discord.VoiceChannel, discord.CategoryChannel]]=None, *, target:typing.Union[discord.Member,discord.Role]=None):
        """Permissions assigned to a member/role (the user by default)
        The channel used to view permissions is the channel in which the command is entered.

        ..Example perms #announcements everyone

        ..Example perms Zbot
        
        ..Doc infos.html#permissions"""
        if target is None:
            target = ctx.author
        if isinstance(target, discord.Member):
            if channel is None:
                perms = target.guild_permissions
            else:
                perms = channel.permissions_for(target)
            col = target.color
            avatar = target.display_avatar.replace(static_format="png", size=256)
            name = str(target)
        elif isinstance(target, discord.Role):
            perms = target.permissions
            if channel is not None:
                perms.update(**{x[0]:x[1] for x in channel.overwrites_for(ctx.guild.default_role) if x[1] is not None})
                perms.update(**{x[0]:x[1] for x in channel.overwrites_for(target) if x[1] is not None})
            col = target.color
            avatar = ctx.guild.icon.replace(format='png', size=256)
            name = str(target)
        else:
            return
        permsl = list()

        if perms.administrator:
            # If the user is admin, we just say it
            perm_tr = await self.bot._(ctx.guild.id, "permissions.list.administrator")
            if "permissions.list." in perm_tr: # unsuccessful translation
                perm_tr = "Administrator"
            permsl.append(self.bot.get_cog('Emojis').customEmojis['green_check'] + perm_tr)
        else:
            # Here we check if the value of each permission is True.
            for perm_id, value in perms:
                if (perm_id not in self.perms_name['text']+self.perms_name['common_channel'] and isinstance(channel,discord.TextChannel)) or (perm_id not in self.perms_name['voice']+self.perms_name['common_channel'] and isinstance(channel,discord.VoiceChannel)):
                    continue
                #perm = perm.replace('_',' ').title()
                perm_tr = await self.bot._(ctx.guild.id, "permissions.list."+perm_id)
                if "permissions.list." in perm_tr: # unsuccessful translation
                    perm_tr = perm_id.replace('_',' ').title()
                if value:
                    permsl.append(self.bot.get_cog('Emojis').customEmojis['green_check'] + perm_tr)
                else:
                    permsl.append(self.bot.get_cog('Emojis').customEmojis['red_cross'] + perm_tr)
        if ctx.can_send_embed:
            # \uFEFF is a Zero-Width Space, which basically allows us to have an empty field name.
            # And to make it look nice, we wrap it in an Embed.
            if len(permsl) > 10:
                sep = int(len(permsl)/2)
                if len(permsl)%2 == 1:
                    sep+=1
                f1 = {'name':'\uFEFF', 'value':"\n".join(permsl[:sep]),'inline':True}
                f2 = {'name':'\uFEFF', 'value':"\n".join(permsl[sep:]),'inline':True}
                fields = [f1,f2]
            else:
                fields = [{'name':'\uFEFF', 'value':"\n".join(permsl),'inline':True}]
            if channel is None:
                desc = await self.bot._(ctx.guild.id, "permissions.general")
            else:
                desc = channel.mention
            _whatisthat = await self.bot._(ctx.guild.id, "permissions.whatisthat")
            fields.append({
                'name': '\uFEFF',
                'value': f'[{_whatisthat}](https://zbot.readthedocs.io/en/latest/perms.html)',
                'inline': False
            })
            embed = await ctx.bot.get_cog('Embeds').Embed(color=col, fields=fields, desc=desc).create_footer(ctx)
            embed.author_name = name
            embed.author_icon = avatar
            await ctx.send(embed=embed.discord_embed())
            # Thanks to Gio for the Command.
        else:
            try:
                txt = await self.bot._(ctx.guild.id,"permissions.title", name=name) + "\n".join(permsl)
                allowed_mentions = discord.AllowedMentions.none()
                await ctx.send(txt, allowed_mentions=allowed_mentions)
            except:
                pass


def setup(bot):
    bot.add_cog(Perms(bot))