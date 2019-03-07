import discord, typing
from discord.ext import commands

class PermsCog(commands.Cog):
    """Cog with a single command, allowing you to see the permissions of a member or a role in a channel."""

    def __init__(self,bot):
        self.bot = bot
        self.file = "perms"
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass

    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr

    @commands.command(name='perms', aliases=['permissions'])
    @commands.guild_only()
    async def check_permissions(self, ctx, *, target:typing.Union[discord.Member,discord.Role]=None):
        """Permissions assigned to a member/role (the user by default)
        The channel used to view permissions is the channel in which the command is entered."""
        if isinstance(target,discord.Member):
            perms = target.guild_permissions
            col = target.color
            avatar = await self.bot.user_avatar_as(target,size=256)
            name = str(target)
        elif target == None :
            perms = ctx.author.guild_permissions
            col = ctx.author.color
            avatar = await self.bot.user_avatar_as(ctx.author,size=256)
            name = str(ctx.author)
        elif isinstance(target,discord.Role):
            perms = target.permissions
            col = target.color
            avatar = ctx.guild.icon_url_as(format='png',size=256)
            name = str(target)
        permsl = list()
        # Here we check if the value of each permission is True.
        for perm, value in perms:
            perm = perm.replace('_',' ').title()
            if value:
                permsl.append(self.bot.cogs['EmojiCog'].customEmojis['green_check']+perm)
            else:
                permsl.append(self.bot.cogs['EmojiCog'].customEmojis['red_cross']+perm)
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            # \uFEFF is a Zero-Width Space, which basically allows us to have an empty field name.
            sep = int(len(permsl)/2)
            if len(permsl)%2 == 1:
                sep+=1
            # And to make it look nice, we wrap it in an Embed.
            f1 = {'name':'\uFEFF','value':"\n".join(permsl[:sep]),'inline':True}
            f2 = {'name':'\uFEFF','value':"\n".join(permsl[sep:]),'inline':True}
            embed = ctx.bot.cogs['EmbedCog'].Embed(color=col,fields=[f1,f2]).create_footer(ctx.author)
            embed.author_name = name
            embed.author_icon = avatar
            await ctx.send(embed=embed.discord_embed())
            # Thanks to Gio for the Command.
        else:
            try:
                await ctx.send(str(await self.translate(ctx.guild.id,"perms","perms-1")).format(name.replace('@','')) + "\n".join(permsl))
            except:
                pass


def setup(bot):
    bot.add_cog(PermsCog(bot))