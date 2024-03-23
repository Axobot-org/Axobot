import datetime
import importlib
import random
import re
from math import ceil
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

import aiohttp
import autopep8
import discord
import geocoder
from asyncache import cached
from cachetools import TTLCache
from discord import app_commands
from discord.ext import commands
from pytz import timezone
from timezonefinder import TimezoneFinder

from libs.arguments import args
from libs.bot_classes import SUPPORT_GUILD_ID, Axobot, MyContext
from libs.checks import checks
from libs.checks.checks import is_fun_enabled
from libs.formatutils import FormatUtils
from libs.paginator import Paginator

importlib.reload(checks)
importlib.reload(args)

if TYPE_CHECKING:
    from fcts.utilities import Utilities

cmds_list = ['count_msg', 'ragequit', 'pong', 'run', 'nope', 'blame', 'party', 'bigtext', 'shrug', 'gg', 'money', 'pibkac',
             'osekour', 'me', 'kill', 'cat', 'happy-birthday', 'rekt', 'thanos', 'nuke', 'pikachu', 'pizza', 'google',
             'loading', 'piece', 'roll', 'afk', 'bubble-wrap', 'reverse', 'wink']


def flatten_list(first_list: list) -> list:
    return [item for sublist in first_list for item in sublist]

async def can_say(ctx: MyContext):
    "Check if a user can use the 'say' cmd"
    if not ctx.bot.database_online:
        return ctx.channel.permissions_for(ctx.author).administrator
    return await ctx.bot.get_cog("ServerConfig").check_member_config_permission(ctx.author, "say_allowed_roles")

async def can_use_cookie(ctx: MyContext) -> bool:
    "Check if a user can use the 'cookie' cmd"
    async with ctx.bot.db_query("SELECT userID FROM `axobot`.`users` WHERE user_flags & 32 = 32", astuple=True) as query_results:
        allowed_users = flatten_list(query_results)
    return ctx.author.id in allowed_users

class Fun(commands.Cog):
    """Add some fun commands, no obvious use. You can disable this module with the 'enable_fun' option (command 'config')"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "fun"
        self.tf = TimezoneFinder()
        self.afk_guys: dict[int, str] = {}
        self.nasa_pict: Optional[dict[str, Any]] = None

    @property
    def utilities(self) -> 'Utilities':
        return self.bot.get_cog("Utilities")

    async def is_on_guild(self, user_id: int, guild_id: int):
        "Check if a member is part of a guild"
        if self.bot.beta:
            return True
        # Zrunner, someone, Awhikax
        if user_id in {279568324260528128, 392766377078816789, 281404141841022976}:
            return True
        guild = self.bot.get_guild(guild_id)
        if guild is not None:
            return (await guild.fetch_member(user_id)) is not None
        return False

    @commands.command(name="cookie", aliases=['cookies', 'crustulum'], hidden=True)
    @commands.check(can_use_cookie)
    @commands.check(is_fun_enabled)
    async def cookie(self, ctx: MyContext):
        """COOKIE !!!"""
        if ctx.author.id == 375598088850505728:
            await ctx.send(file=await self.utilities.find_img("cookie-target.gif"))
        else:
            emoji = self.bot.emojis_manager.customs['cookies_eat']
            if ctx.invoked_with == "crustulum":
                msg = f"Pyxidem oft {ctx.author.mention} crustularum <@375598088850505728>! {emoji}"
            else:
                msg = await self.bot._(ctx.guild, "fun.cookie", user=ctx.author.mention, emoji=emoji)
            await ctx.send(msg)


    fun_main = app_commands.Group(
        name="fun",
        description="A collection of useless commands",
    )

    @fun_main.command(name="roll")
    @app_commands.describe(options="A comma-separated list of possibilities")
    async def roll(self, interaction: discord.Interaction, *, options: str):
        """Selects an option randomly from a given list.
        The options must be separated by a comma `,`

        ..Example fun roll Play Minecraft, play Star Citizens, do homeworks

        ..Doc fun.html#roll"""
        possibilities = list({x for x in [x.strip() for x in options.split(',')] if len(x) > 0})
        if len(possibilities) == 0:
            return await interaction.response.send_message(await self.bot._(interaction, "fun.no-roll"))
        if len(possibilities) == 1:
            return await interaction.response.send_message(await self.bot._(interaction, "fun.not-enough-roll"))
        choosen = random.choice(possibilities)
        await interaction.response.send_message(choosen)

    @fun_main.command(name="count-messages")
    @app_commands.checks.cooldown(3, 30)
    async def count(self, interaction: discord.Interaction, limit: Optional[app_commands.Range[int, 10, 1_000]]=100,
                    user: Optional[discord.User]=None, channel: Optional[discord.TextChannel]=None):
        """Count the number of messages sent by the user in one channel
You can specify a verification limit by adding a number in argument (up to 1.000.000)

        ..Example fun count-messages

        ..Example fun count-messages Z_runner #announcements

        ..Example fun count-messages 300 someone

        ..Doc fun.html#count-messages"""
        if channel is None:
            channel = interaction.channel
        if not channel.permissions_for(interaction.user).read_message_history:
            await interaction.response.send_message(await self.bot._(interaction, "fun.count.forbidden"))
            return
        if interaction.guild is not None and not channel.permissions_for(interaction.guild.me).read_message_history:
            await interaction.response.send_message(await self.bot._(interaction, "fun.count.missing-perms"))
            return
        if user is None:
            user = interaction.user
        counter = 0
        await interaction.response.send_message(await self.bot._(interaction,"fun.count.counting"))
        total_count = 0
        async for log in channel.history(limit=limit):
            total_count += 1
            if log.author == user:
                counter += 1
        result = round(counter*100/total_count,2)
        if user == interaction.user:
            await interaction.edit_original_response(
                content=await self.bot._(interaction, "fun.count.result-you", limit=total_count, x=counter, p=result)
            )
        else:
            await interaction.edit_original_response(
                content=await self.bot._(interaction, "fun.count.result-user", limit=total_count, user=user.display_name,
                                         x=counter, p=result)
            )

    @fun_main.command(name="blame")
    async def blame(self, interaction: discord.Interaction, name: str):
        """Blame someone
        Use 'blame list' command to see every available name *for you*

        ..Example fun blame discord

        ..Doc fun.html#blame"""
        name = name.lower()
        await interaction.response.defer()
        available_names = await self._get_blame_available_names(interaction.user.id)
        if name in available_names:
            await interaction.followup.send(file=await self.utilities.find_img(f'blame-{name}.png'))
            return
        if name not in available_names:
            txt = "- "+"\n- ".join(sorted(available_names))
            title = await self.bot._(interaction, "fun.blame-0", user=interaction.user)
            emb = discord.Embed(title=title, description=txt, color=self.bot.get_cog("Help").help_color)
            await interaction.followup.send(embed=emb)

    @cached(TTLCache(1_000, 3600))
    async def _get_blame_available_names(self, user_id: int):
        l1 = ['discord','mojang','zbot','google','youtube', 'twitter'] # everyone
        l2 = ['tronics','patate','neil','reddemoon','aragorn1202','platon'] # fr-minecraft semi-public server
        l3 = ['awhikax','aragorn','adri','zrunner'] # Axobot official server
        l4 = ['benny'] # benny server
        available_names = l1
        if await self.is_on_guild(user_id, 391968999098810388): # fr-minecraft
            available_names += l2
        if await self.is_on_guild(user_id, SUPPORT_GUILD_ID.id): # Axobot server
            available_names += l3
        if await self.is_on_guild(user_id, 523525264517496834): # Benny Support
            available_names += l4
        return available_names

    @blame.autocomplete("name")
    async def blame_autocomplete(self, interaction: discord.Interaction, current: str):
        "Autocomplete for the blame command"
        current = current.lower()
        available_names = await self._get_blame_available_names(interaction.user.id)
        filtered = [
            (not name.startswith(current), name)
            for name in available_names
            if current in name
        ]
        filtered.sort()
        return [
            app_commands.Choice(name=name, value=name)
            for _, name in filtered
        ]

    @fun_main.command(name="kill")
    async def kill(self, interaction: discord.Interaction, *, name: Optional[str]=None):
        """Just try to kill someone with a fun message

        ..Example kill herobrine

        ..Doc fun.html#kill"""
        if name is None:
            victime = interaction.user.display_name
        else:
            victime = name
        ex = victime.replace(" ", "_")
        author = interaction.user.mention
        possibilities = await self.bot._(interaction, "fun.kills-list")
        msg = random.choice(possibilities)
        tries = 0
        while '{attacker}' in msg and name is None and tries < 50:
            msg = random.choice(possibilities)
            tries += 1
        await interaction.response.send_message(msg.format(attacker=author, victim=victime, ex=ex))

    @fun_main.command(name="helpme")
    async def osekour(self, interaction: discord.Interaction):
        """Does anyone need help?

        ..Doc fun.html#heeelp"""
        messages = await self.bot._(interaction,"fun.osekour")
        await interaction.response.send_message(random.choice(messages))

    @fun_main.command(name="gif")
    async def gif(self, interaction: discord.Interaction, category: Literal["cat", "birthday", "wink"]):
        "Send a random gif from a category!"
        if category == "cat":
            gif = random.choice([
                # pylint: disable=line-too-long
                'https://images6.fanpop.com/image/photos/40800000/tummy-rub-kitten-animated-gif-cute-kittens-40838484-380-227.gif',
                'https://25.media.tumblr.com/7774fd7794d99b5998318ebd5438ba21/tumblr_n2r7h35U211rudcwro1_400.gif',
                'https://tenor.com/view/seriously-seriously-cat-cat-really-cat-really-look-cat-look-gif-22182662',
                'http://coquelico.c.o.pic.centerblog.net/chat-peur.gif',
                'https://tenor.com/view/nope-bye-cat-leave-done-gif-12387359',
                'https://tenor.com/view/cute-cat-kitten-kitty-pussy-cat-gif-16577050',
                'https://tenor.com/view/cat-box-gif-18395469',
                'https://tenor.com/view/pile-cats-cute-silly-meowtain-gif-5791255',
                'https://tenor.com/view/cat-fight-cats-cat-love-pet-lover-pelea-gif-13002823369159732311',
                'https://tenor.com/view/cat-disapear-cat-snow-cat-jump-fail-cat-fun-jump-cats-gif-17569677',
                'https://tenor.com/view/black-cat-tiny-cat-smol-kitten-airplane-ears-cutie-pie-gif-23391953',
                'https://tenor.com/view/cat-cats-catsoftheinternet-biting-tale-cat-bite-gif-23554005',
                'https://tenor.com/view/on-my-way-cat-run-cat-on-my-way-cat-cat-on-my-way-gif-26471384',
                'https://tenor.com/view/cat-cat-activity-goober-goober-cat-silly-cat-gif-186256394908832033',
                'https://tenor.com/view/cat-stacked-kittens-kitty-pussy-cats-gif-16220908',
                'https://tenor.com/view/cute-cat-cats-cats-of-the-internet-cattitude-gif-17600906',
                'https://tenor.com/view/cat-scared-hide-terrified-frightened-gif-17023981',
                'https://tenor.com/view/cat-running-away-escape-getaway-bye-gif-16631286',
                'https://tenor.com/view/bye-cat-box-tight-face-bored-cat-gif-7986182'
            ])
        elif category == "birthday":
            gif = random.choice([
                'https://tenor.com/view/happy-birthday-cat-cute-birthday-cake-second-birthday-gif-16100991',
                'https://tenor.com/view/happy-birthday-birthday-cake-goat-licking-lick-gif-15968273',
                'https://tenor.com/view/celebracion-gif-4928008',
                'https://tenor.com/view/kitty-birthday-birthday-kitty-happy-birthday-happy-birthday-to-you-hbd-gif-13929089',
                'https://tenor.com/view/happy-birthday-happy-birthday-to-you-hbd-birthday-celebrate-gif-13366300'
            ])
        elif category == "wink":
            gif = random.choice([
                'https://tenor.com/view/dr-strange-wink-smirk-trust-me-gif-24332472',
                'https://tenor.com/view/wink-smile-laugh-wandavision-gif-20321476',
                'https://tenor.com/view/rowan-atkinson-mr-bean-trying-to-flirt-wink-gif-16439423',
                'https://tenor.com/view/winking-james-franco-actor-wink-handsome-gif-17801047',
                'https://tenor.com/view/clin-doeil-wink-playboy-wink-funny-wink-clin-oeil-gif-24871407',
                'https://tenor.com/view/wink-got-it-dude-rocket-raccoon-hint-gotcha-gif-23822337'
            ])
        else:
            raise ValueError("Invalid category: "+category)
        await interaction.response.send_message(gif)

    @fun_main.command(name="pibkac")
    async def pibkac(self, interaction: discord.Interaction):
        """Where does that bug come from?

        ..Doc fun.html#pibkac"""
        await interaction.response.send_message(file=await self.utilities.find_img('pibkac.png'))

    @fun_main.command(name="flip")
    async def piece(self, interaction: discord.Interaction):
        """Heads or tails?

        ..Doc fun.html#piece"""
        if random.random() < 0.04:
            result = "fun.flip.edge"
        elif random.random() < 0.5:
            result = "fun.flip.heads"
        else:
            result = "fun.flip.tails"
        await interaction.response.send_message(await self.bot._(interaction, result))

    @app_commands.command(name="say")
    @app_commands.guild_only()
    async def say(self, interaction: discord.Interaction, text: str,
                  channel: Union[discord.TextChannel, discord.Thread, None] = None):
        """Let the bot say something for you
        You can specify a channel where the bot must send this message. If channel is None, the current channel will be used

        ..Example say Hi I'm invading Earth #chat

        ..Example say Booh!

        ..Doc miscellaneous.html#say"""
        if channel is None:
            channel = interaction.channel
        if not (
            channel.permissions_for(interaction.user).read_messages and
            channel.permissions_for(interaction.user).send_messages and
            channel.guild == interaction.guild
        ):
            await interaction.response.send_message(await self.bot._(interaction, "fun.say-no-perm", channel=channel.mention))
            return
        if not channel.permissions_for(interaction.guild.me).send_messages:
            error = await self.bot._(interaction, "fun.no-say")
            error += random.choice([' :confused:', '', '', ''])
            await interaction.response.send_message(error)
            return
        if self.bot.zombie_mode:
            return
        await channel.send(text)
        await interaction.response.send_message(await self.bot._(interaction, "fun.say-done"), ephemeral=True)

    @app_commands.command(name="react")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(
        message="The URL of the message to react to",
        reactions="A space-separated list of custom or unicode emojis to react with"
    )
    async def react(self, interaction: discord.Interaction, message: args.MessageArgument, reactions: str):
        """Add reaction(s) to a message. Server emojis also work.

        ..Example react 375246790301057024-790177026232811531 :ok:

        ..Example react https://discord.com/channels/125723125685026816/375246790301057024/790177026232811531 :party: :money:

        ..Doc fun.html#react"""
        channel = message.channel
        if not (
            channel.permissions_for(interaction.user).read_messages
            and channel.permissions_for(interaction.user).add_reactions
            and (channel.guild is None or channel.guild==interaction.guild)
        ):
            await interaction.response.send_message(await self.bot._(interaction, "fun.say-no-perm", channel=channel.mention))
            return
        await interaction.response.defer(ephemeral=True)
        ctx = await MyContext.from_interaction(interaction)
        count = 0
        for reaction in reactions.split():
            try:
                emoji = await args.DiscordOrUnicodeEmojiConverter.convert(ctx, reaction)
                await message.add_reaction(emoji)
            except (discord.Forbidden, commands.BadArgument):
                try:
                    await message.add_reaction(reaction)
                except discord.errors.HTTPException:
                    await interaction.followup.send(content=await self.bot._(interaction, "fun.no-emoji"))
                    return
            count += 1
        await interaction.followup.send(content=await self.bot._(interaction, "fun.react-done", count=count))

    @commands.command(name="google", hidden=True, aliases=['lmgtfy'])
    @commands.check(is_fun_enabled)
    async def lmgtfy(self,ctx,*,search):
        """How to use Google

        ..Doc fun.html#lmgtfy"""
        link = "https://lmgtfy.com/?q="+search.replace("\n","+").replace(" ","+")
        await ctx.send('<'+link+'>')
        await ctx.message.delete(delay=0)

    @commands.command(name="weather", aliases=['météo'])
    @commands.cooldown(4, 30, type=commands.BucketType.guild)
    async def weather(self, ctx:MyContext, *, city:str):
        """Get the weather of a city
        You need to provide the city name in english

        ..Example weather Tokyo

        ..Doc miscellaneous.html#hour-weather"""
        city = city.replace(" ","%20")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.get("https://welcomer.glitch.me/weather?city="+city) as resp:
                if resp.status == 200:
                    if resp.content_type == 'image/png':
                        if ctx.channel.permissions_for(ctx.me).embed_links:
                            emb = discord.Embed()
                            emb.set_image(url="https://welcomer.glitch.me/weather?city="+city)
                            emb.set_footer(text="From https://welcomer.glitch.me/weather")
                            return await ctx.send(embed=emb)
                        else:
                            return await ctx.send("https://welcomer.glitch.me/weather?city="+city)
        await ctx.send(await self.bot._(ctx.channel,"fun.invalid-city"))

    @commands.command(name="hour")
    @commands.cooldown(4, 50, type=commands.BucketType.guild)
    async def hour(self, ctx: MyContext, *, city: str):
        """Get the hour of a city

        ..Example hour Paris

        ..Doc miscellaneous.html#hour-weather"""
        g = geocoder.arcgis(city)
        if not g.ok:
            return await ctx.send(await self.bot._(ctx.channel, "fun.invalid-city"))
        tz_name: Optional[str] = self.tf.timezone_at_land(lat=g.json['lat'], lng=g.json['lng'])
        if tz_name is None:
            return await ctx.send(await self.bot._(ctx.channel, "fun.uninhabited-city"))
        tz_obj = timezone(tz_name)
        date = datetime.datetime.now(tz_obj)
        format_d = await FormatUtils.date(date,lang=await self.bot._(ctx.channel, "_used_locale"))
        address = g.current_result.address
        latitude = round(g.json['lat'],2)
        longitude = round(g.json['lng'],2)
        await ctx.send(f"**{tz_name}**:\n{format_d} ({date.tzname()})\n ({address} - lat: {latitude} - long: {longitude})")

    @commands.command(name='afk')
    @commands.check(is_fun_enabled)
    @commands.guild_only()
    async def afk(self, ctx: MyContext, *, reason=""):
        """Mark you AFK
        You'll get a nice nickname, because nicknames are cool, aren't they?

        ..Doc fun.html#afk"""
        try:
            self.afk_guys[ctx.author.id] = reason
            if (not ctx.author.display_name.endswith(' [AFK]')) and len(ctx.author.display_name)<26:
                await ctx.author.edit(nick=ctx.author.display_name+" [AFK]")
            await ctx.send(await self.bot._(ctx.guild.id,"fun.afk.afk-done"))
        except discord.errors.Forbidden:
            return await ctx.send(await self.bot._(ctx.guild.id,"fun.afk.no-perm"))

    async def user_is_afk(self, user: discord.User) -> bool:
        "Check if a user is currently afk"
        cond = user.id in self.afk_guys
        if cond:
            return True
        return isinstance(user, discord.Member) and user.nick and user.nick.endswith(' [AFK]')

    @commands.command(name='unafk')
    @commands.check(is_fun_enabled)
    @commands.guild_only()
    async def unafk(self, ctx: MyContext):
        """Remove you from the AFK system
        Welcome back dude

        ..Doc fun.html#afk"""
        if await self.user_is_afk(ctx.author):
            del self.afk_guys[ctx.author.id]
            await ctx.send(await self.bot._(ctx.guild.id,"fun.afk.unafk-done"))
            if ctx.author.nick and ctx.author.nick.endswith(" [AFK]"):
                try:
                    await ctx.author.edit(nick=ctx.author.display_name.replace(" [AFK]",''))
                except discord.errors.Forbidden:
                    pass
        else:
            await ctx.send(await self.bot._(ctx.guild.id,"fun.afk.unafk-cant"))

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        "Run the AFK check when a message is sent"
        if msg.guild:
            await self.check_afk(msg)

    async def check_afk(self, msg: discord.Message):
        """Check if someone pinged is afk"""
        if msg.author.bot:
            return
        ctx = await self.bot.get_context(msg)
        if not await is_fun_enabled(ctx):
            return
        if self.bot.zombie_mode:
            return
        # send a message if someone is afk and the bot can speak
        if msg.channel.permissions_for(msg.guild.me).send_messages:
            for member in msg.mentions:
                if await self.user_is_afk(member) and member != msg.author:
                    if member.id not in self.afk_guys or len(self.afk_guys[member.id]) == 0:
                        await msg.channel.send(await self.bot._(msg.guild.id,"fun.afk.afk-user-noreason"))
                    else:
                        await msg.channel.send(
                            await self.bot._(msg.guild.id,"fun.afk.afk-user-reason",reason=self.afk_guys[member.id])
                        )
        # auto unafk if the author was afk and has enabled it
        if isinstance(ctx.author, discord.Member) and not await checks.is_a_cmd(msg, self.bot):
            if (ctx.author.nick and ctx.author.nick.endswith(' [AFK]')) or ctx.author.id in self.afk_guys:
                user_config = await self.bot.get_cog("Users").db_get_user_config(ctx.author.id, "auto_unafk")
                if user_config is False:
                    return
                await self.unafk(ctx)


    @commands.command(name="embed",hidden=False)
    @commands.check(checks.has_embed_links)
    @commands.check(can_say)
    @commands.guild_only()
    async def send_embed(self, ctx: MyContext, *, arguments):
        """Send an embed
        Syntax: !embed [channel] key1=\"value 1\" key2=\"value 2\"

        Available keys:
            - title: the title of the embed [256 characters]
            - content: the text inside the box [2048 characters]
            - url: a well-formed url clickable via the title
            - footer: a little text at the bottom of the box [90 characters]
            - image: a well-formed url redirects to an image
            - color: the color of the embed bar (#hex or int)
        If you want to use quotation marks in the texts, it is possible to escape them thanks to the backslash (`\\"`)

        You can send the embed to a specific channel by mentionning it at the beginning of the arguments

        ..Example embed #announcements title="Special update!" content="We got an amazing thing for you!\\nPlease check blah blah..." color="#FF0022"

        ..Doc miscellaneous.html#embed
        """
        channel = None
        r = re.search(r'<#(\d+)>', arguments.split(" ")[0])
        if r is not None:
            arguments = " ".join(arguments.split(" ")[1:])
            channel = ctx.guild.get_channel_or_thread(int(r.group(1)))
        arguments = await args.arguments().convert(ctx, arguments)
        if len(arguments) == 0:
            raise commands.errors.MissingRequiredArgument(ctx.command.clean_params['arguments'])
        destination = ctx.channel if channel is None else channel
        if not (destination.permissions_for(ctx.author).read_messages and destination.permissions_for(ctx.author).send_messages):
            await ctx.send(await self.bot._(ctx.guild,"fun.say-no-perm",channel=destination.mention))
            return
        if not destination.permissions_for(ctx.guild.me).send_messages:
            return await ctx.send(await self.bot._(ctx.channel,"fun.embed-invalid-channel"))
        if not destination.permissions_for(ctx.guild.me).embed_links:
            return await ctx.send(await self.bot._(ctx.channel,"fun.no-embed-perm"))
        embed_color = ctx.bot.get_cog('ServerConfig').embed_color
        k = {'title': "", 'content': "", 'url': '',
             'footer': "", 'image': '', 'color': embed_color}
        for key, value in arguments.items():
            # replace description and colour fields
            if key == "description":
                key = "content"
            elif key == "colour":
                key = "color"
            # limit title length
            if key == 'title':
                k['title'] = value[:255]
            # limit footer length
            elif key == 'footer':
                k['footer'] = value[:90]
            # replace \n with real newlines in content
            elif key == "content":
                k[key] = value.replace("\\n", "\n")
            # eval embed color
            elif key == "color":
                if color := await commands.ColourConverter().convert(ctx, value):
                    k['color'] = color
            # add url and image links
            elif key in {'url', 'image'} and value.startswith("http"):
                k[key] = value
        emb = discord.Embed(title=k['title'], description=k['content'], url=k['url'], color=k['color'])
        emb.set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
        if "image" in k:
            emb.set_thumbnail(url=k['image'])
        if "footer" in k:
            emb.set_footer(text=k['footer'])
        try:
            await destination.send(embed=emb)
        except Exception as err:
            if isinstance(err,discord.errors.HTTPException) and "In embed.thumbnail.url: Not a well formed URL" in str(err):
                return await ctx.send(await self.bot._(ctx.channel, "fun.embed-invalid-image"))
            await ctx.send(await self.bot._(ctx.channel,"fun.error", err=err))
        if channel is not None:
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass


    @commands.command(name="markdown")
    async def markdown(self, ctx: MyContext):
        """Get help about markdown in Discord

        ..Doc miscellaneous.html#markdown"""
        txt = await self.bot._(ctx.channel,"fun.markdown")
        if ctx.can_send_embed:
            await ctx.send(embed=discord.Embed(description=txt))
        else:
            await ctx.send(txt)


    @commands.command(name="bubble-wrap", aliases=["papier-bulle", "bw"], hidden=True)
    @commands.cooldown(5,30,commands.BucketType.channel)
    @commands.cooldown(5,60,commands.BucketType.user)
    async def bubblewrap(self, ctx:MyContext, width:int=10, height:int=15):
        """Just bubble wrap. Which pops when you squeeze it. That's all.

        Width should be between 1 and 150, height between 1 and 50.

        ..Example bubble-wrap

        ..Example bw 7 20

        ..Doc fun.html#bubble-wrap
        """
        width = min(max(1, width), 150)
        height = min(max(1, height), 50)
        p = "||pop||"
        txt = "\n".join([p*width]*height)
        if len(txt) > 2000:
            await ctx.send(await self.bot._(ctx.channel, "fun.bbw-too-many"))
            return
        await ctx.send(txt)

    @commands.command(name="nasa")
    @commands.check(checks.bot_can_embed)
    @commands.cooldown(5, 60, commands.BucketType.channel)
    async def nasa(self, ctx: MyContext):
        """Send the Picture of The Day by NASA

        ..Doc fun.html#nasa"""
        def get_date(raw_str: str):
            return datetime.datetime.strptime(raw_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)
        if self.nasa_pict is None \
                or 'date' not in self.nasa_pict \
                or (self.bot.utcnow()-get_date(self.nasa_pict["date"])).total_seconds() > 86400:
            async with aiohttp.ClientSession() as session:
                key = self.bot.others["nasa"]
                async with session.get(f"https://api.nasa.gov/planetary/apod?api_key={key}") as r:
                    data = await r.json()
            if all(field in data for field in ['title', 'url', 'explanation', 'date']):
                self.nasa_pict = data
        if self.nasa_pict is None:
            await ctx.send(await self.bot._(ctx.channel, "fun.nasa-none"))
            return
        emb = discord.Embed(
            title=self.nasa_pict["title"],
            url=self.nasa_pict["hdurl"] if self.nasa_pict["media_type"]=="image" else self.nasa_pict["url"],
            description=self.nasa_pict["explanation"],
            timestamp=get_date(self.nasa_pict["date"]))
        emb.set_image(url=self.nasa_pict['url'])
        emb.set_footer(text="Credits: " + self.nasa_pict.get("copyright", "Not copyrighted"))
        await ctx.send(embed=emb)

    @commands.command(name="discordjobs", aliases=['discord_jobs', 'jobs.gg'])
    @commands.cooldown(2, 60, commands.BucketType.channel)
    async def discord_jobs(self, ctx: MyContext, *, query: str = None):
        """Get the list of available jobs in Discord

        ..Example discordjobs

        ..Example discordjobs marketing"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.greenhouse.io/v1/boards/discord/jobs") as r:
                data = await r.json()
        if query is not None:
            query = query.lower()
            jobs = [
                x for x in data['jobs']
                if query in x['location']['name'].lower() or query == x['id'] or query in x['title'].lower()
            ]
        else:
            jobs = data['jobs']
        f_jobs = [
            f"[{x['title'] if len(x['title'])<50 else x['title'][:49]+'…'}]({x['absolute_url']})" for x in jobs
        ]
        if ctx.can_send_embed:
            _title = await self.bot._(ctx.channel, "fun.discordjobs-title")
            class JobsPaginator(Paginator):
                "Paginator used to display jobs offers"
                async def get_page_count(self) -> int:
                    return ceil(len(f_jobs)/30)

                async def get_page_content(self, interaction: discord.Interaction, page: int):
                    "Create one page"
                    # to_display = f_jobs[(page-1)*30:page*30]
                    desc = await self.client._(ctx.channel, "fun.discordjobs-count", c=len(f_jobs))
                    emb = discord.Embed(title=_title, color=7506394, url="https://dis.gd/jobs", description=desc)
                    page_start, page_end = (page-1)*30, min(page*30, len(f_jobs))
                    for i in range(page_start, page_end, 10):
                        column_start, column_end = i+1, min(i+10, len(f_jobs))
                        emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(f_jobs[i:i+10]))
                    footer = f"Page {page}/{await self.get_page_count()}"
                    emb.set_footer(text=footer)
                    return {
                        "embed": emb
                    }

            if len(f_jobs) < 30:
                emb = discord.Embed(title=_title, color=7506394, url="https://dis.gd/jobs")
                emb.description = await self.bot._(ctx.channel, "fun.discordjobs-count", c=len(f_jobs))
                for i in range(0, len(f_jobs), 10):
                    emb.add_field(name=self.bot.zws, value="\n".join(f_jobs[i:i+10]))
                await ctx.send(embed=emb)
            else:
                _quit = await self.bot._(ctx.guild, "misc.quit")
                view = JobsPaginator(self.bot, ctx.author, stop_label=_quit.capitalize())
                await view.send_init(ctx)
        else:
            await ctx.send("\n".join(f_jobs[:20]))

    @commands.command(name="discordlinks",aliases=['discord','discordurls'])
    async def discord_links(self, ctx: MyContext):
        """Get some useful links about Discord"""
        l = await self.bot._(ctx.channel,'info.discordlinks')
        links = ["https://dis.gd/status","https://dis.gd/tos","https://dis.gd/report","https://dis.gd/feedback","https://support.discord.com/hc/en-us/articles/115002192352","https://discord.com/developers/docs/legal","https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-","https://support.discord.com/hc/en-us/articles/360040724612", " https://twitter.com/discordapp/status/1060411427616444417", "https://support.discord.com/hc/en-us/articles/360035675191"]
        if ctx.can_send_embed:
            txt = "\n".join(['['+l[i]+']('+links[i]+')' for i in range(len(l))])
            em = discord.Embed(description=txt)
            em.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)
            await ctx.send(embed=em)
        else:
            txt = "\n".join([f'• {l[i]}: <{links[i]}>' for i in range(len(l))])
            await ctx.send(txt)

    @commands.command(name="discordstatus", aliases=['discord_status', 'status.gg'])
    @commands.cooldown(2, 60, commands.BucketType.channel)
    async def discord_status(self, ctx: MyContext):
        """Know if Discord currently has a technical issue"""
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discordstatus.com/api/v2/incidents.json") as r:
                data = await r.json()
        last_incident = data['incidents'][0]
        if last_incident['resolved_at'] is None:
            impact = await self.bot._(ctx.channel, "fun.discordstatus-impacts."+last_incident['impact'])
            title = f"**{last_incident['name']}** (<{last_incident['shortlink']}>)"
            await ctx.send(await self.bot._(ctx.channel, "fun.discordstatus-exists", impact=impact, title=title))
        else:
            last_date = datetime.datetime.strptime(last_incident['resolved_at'], '%Y-%m-%dT%H:%M:%S.%f%z')
            last_date = f"<t:{round(last_date.timestamp())}:F>"
            await ctx.send(await self.bot._(ctx.channel, "fun.discordstatus-nothing", date=last_date))

    @commands.command(name="pep8", aliases=['autopep8'])
    @commands.cooldown(3, 30, commands.BucketType.user)
    async def autopep8_cmd(self, ctx: MyContext, *, code: str):
        """Auto format your Python code according to PEP8 guidelines"""
        if code.startswith('```') and code.endswith('```'):
            code = '\n'.join(code.split('\n')[1:-1])
        elif code.startswith('`') and code.endswith('`'):
            code = code[1:-1]
        code = autopep8.fix_code(code, {
            "aggressive": 3,
            "ignore": set()
        }).strip()
        await ctx.send(f"```py\n{code}\n```")

    @commands.command(name="avatar", aliases=['pfp'])
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def avatar(self, ctx: MyContext, user: Optional[discord.User]):
        """Get the avatar of a user"""
        if user is None:
            user = ctx.author
        await ctx.send(user.display_avatar.url)


async def setup(bot):
    await bot.add_cog(Fun(bot))
