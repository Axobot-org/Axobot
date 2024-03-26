import datetime
import importlib
import random
import re
import urllib.parse
from math import ceil
from typing import Any, Literal, Optional, Union

import aiohttp
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
from libs.formatutils import FormatUtils
from libs.paginator import Paginator

importlib.reload(checks)
importlib.reload(args)


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
        self.nasa_pict: Optional[dict[str, Any]] = None

    @property
    def utilities(self):
        return self.bot.get_cog("Utilities")

    async def is_in_guild(self, user_id: int, guild_id: int):
        "Check if a user is part of a guild"
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
        if await self.is_in_guild(user_id, 391968999098810388): # fr-minecraft
            available_names += l2
        if await self.is_in_guild(user_id, SUPPORT_GUILD_ID.id): # Axobot server
            available_names += l3
        if await self.is_in_guild(user_id, 523525264517496834): # Benny Support
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
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.describe(
        text="The text to send",
        channel="The channel where the bot must send the message"
    )
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

    @fun_main.command(name="google")
    @app_commands.checks.cooldown(2, 10)
    async def lmgtfy(self, interaction: discord.Interaction, search: str):
        """How to use Google

        ..Doc fun.html#lmgtfy"""
        link = "https://lmgtfy2.com/query/?q=" + urllib.parse.quote_plus(search)
        await interaction.response.send_message('<'+link+'>')

    @fun_main.command(name="hour")
    @app_commands.checks.cooldown(4, 40)
    async def hour(self, interaction: discord.Interaction, city: app_commands.Range[str, 1, 100]):
        """Get the hour of a city

        ..Example hour Paris

        ..Doc miscellaneous.html#hour-weather"""
        await interaction.response.defer()
        g = geocoder.arcgis(city)
        if not g.ok:
            await interaction.followup.send(content=await self.bot._(interaction, "fun.invalid-city"))
            return
        tz_name: Optional[str] = self.tf.timezone_at_land(lat=g.json['lat'], lng=g.json['lng'])
        if tz_name is None:
            await interaction.followup.send(content=await self.bot._(interaction, "fun.uninhabited-city"))
            return
        tz_obj = timezone(tz_name)
        date = datetime.datetime.now(tz_obj)
        format_d = await FormatUtils.date(date, lang=await self.bot._(interaction, "_used_locale"))
        address = g.current_result.address
        latitude = round(g.json['lat'],2)
        longitude = round(g.json['lng'],2)
        text = await self.bot._(
            interaction, "fun.hour-result",
            date=format_d,
            tzname=date.tzname(),
            tzlocation=tz_name,
            lat=latitude,
            long=longitude
        )
        embed = discord.Embed(
            title=address,
            description=text,
            color=discord.Colour.blurple()
        )
        await interaction.followup.send(embed=embed)

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


    @fun_main.command(name="bubble-wrap")
    @app_commands.checks.cooldown(5, 30)
    async def bubblewrap(self, interaction: discord.Interaction,
                         width: app_commands.Range[int, 1, 150]=10,
                         height: app_commands.Range[int, 1, 50]=15):
        """Just bubble wrap. Which pops when you squeeze it. That's all.

        Width should be between 1 and 150, height between 1 and 50.

        ..Example bubble-wrap

        ..Example bw 7 20

        ..Doc fun.html#bubble-wrap
        """
        p = "||pop||"
        txt = "\n".join([p*width]*height)
        if len(txt) > 2000:
            await interaction.response.send_message(await self.bot._(interaction, "fun.bbw-too-many"))
            return
        await interaction.response.send_message(txt)

    @fun_main.command(name="nasa")
    @app_commands.checks.cooldown(1, 10)
    async def nasa(self, interaction: discord.Interaction):
        """Send the Picture of The Day by NASA

        ..Doc fun.html#nasa"""
        def get_date(raw_str: str):
            return datetime.datetime.strptime(raw_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)

        await interaction.response.defer()
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
            await interaction.followup.send(content=await self.bot._(interaction, "fun.nasa-none"))
            return
        emb = discord.Embed(
            title=self.nasa_pict["title"],
            url=self.nasa_pict["hdurl"] if self.nasa_pict["media_type"]=="image" else self.nasa_pict["url"],
            description=self.nasa_pict["explanation"],
            timestamp=get_date(self.nasa_pict["date"]),
            color=0x0033cc
        )
        emb.set_image(url=self.nasa_pict['url'])
        emb.set_footer(text="Credits: " + self.nasa_pict.get("copyright", "Not copyrighted"))
        await interaction.followup.send(embed=emb)

    @fun_main.command(name="discord-jobs")
    @app_commands.checks.cooldown(2, 20)
    @app_commands.rename(query="filter")
    async def discord_jobs(self, interaction: discord.Interaction, query: Optional[str] = None):
        """Get the list of available jobs in Discord

        ..Example discordjobs

        ..Example discordjobs marketing"""
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.greenhouse.io/v1/boards/discord/jobs") as r:
                data = await r.json()
        if query is None:
            jobs = data['jobs']
            desc = await self.bot._(interaction, "fun.discordjobs.all-count", count=len(jobs))
        else:
            query = query.lower()
            jobs = [
                x for x in data['jobs']
                if (
                    query in x['location']['name'].lower()
                    or query == x['id']
                    or query in x['title'].lower()
                )
            ]
            desc = await self.bot._(interaction, "fun.discordjobs.filtered-count", count=len(jobs))
        formatted_jobs = [
            f"[{x['title'] if len(x['title'])<50 else x['title'][:49]+'…'}]({x['absolute_url']})"
            for x in jobs
        ]
        _title = await self.bot._(interaction, "fun.discordjobs.title")
        class JobsPaginator(Paginator):
            "Paginator used to display jobs offers"
            async def get_page_count(self) -> int:
                return ceil(len(formatted_jobs)/30)

            async def get_page_content(self, interaction: discord.Interaction, page: int):
                "Create one page"
                emb = discord.Embed(
                    title=_title,
                    description=desc,
                    color=discord.Colour.blurple(),
                    url="https://dis.gd/jobs",
                )
                page_start, page_end = (page-1)*30, min(page*30, len(formatted_jobs))
                for i in range(page_start, page_end, 10):
                    column_start, column_end = i+1, min(i+10, len(formatted_jobs))
                    emb.add_field(name=f"{column_start}-{column_end}", value="\n".join(formatted_jobs[i:i+10]))
                footer = f"Page {page}/{await self.get_page_count()}"
                emb.set_footer(text=footer)
                return {
                    "embed": emb
                }

        if len(formatted_jobs) < 30:
            emb = discord.Embed(
                title=_title,
                description=desc,
                color=discord.Colour.blurple(),
                url="https://dis.gd/jobs"
            )
            for i in range(0, len(formatted_jobs), 10):
                emb.add_field(name=self.bot.zws, value="\n".join(formatted_jobs[i:i+10]))
            await interaction.followup.send(embed=emb)
        else:
            _quit = await self.bot._(interaction, "misc.quit")
            view = JobsPaginator(self.bot, interaction.user, stop_label=_quit.capitalize())
            await view.send_init(interaction)

    @fun_main.command(name="discord-links")
    async def discord_links(self, interaction: discord.Interaction):
        """Get some useful links about Discord"""
        links = {
            "server-status": "https://dis.gd/status",
            "tos": "https://dis.gd/tos",
            "bug-report": "https://dis.gd/report",
            "feedback": "https://dis.gd/feedback",
            "selfbot": "https://support.discord.com/hc/en-us/articles/115002192352",
            "dev-tos": "https://discord.com/developers/docs/legal",
            "how-id": "https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-",
            "age-requirement": "https://support.discord.com/hc/en-us/articles/360040724612",
            "betterdiscord": "https://twitter.com/discordapp/status/1060411427616444417",
            "downloads": "https://support.discord.com/hc/en-us/articles/360035675191",
        }
        translations_list: list[str] = []
        for url_id, link in links.items():
            name = await self.bot._(interaction, f"fun.discordlinks.{url_id}")
            translations_list.append(f"- [{name}]({link})")
        em = discord.Embed(
            title=await self.bot._(interaction, "fun.discordlinks.title"),
            description="\n".join(translations_list),
            color=discord.Colour.blurple()
        )
        await interaction.response.send_message(embed=em)

    @fun_main.command(name="discord-status")
    @app_commands.checks.cooldown(2, 60)
    async def discord_status(self, interaction: discord.Interaction):
        "Check if Discord is experiencing some technical issues"
        await interaction.response.defer()
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discordstatus.com/api/v2/incidents.json") as r:
                data = await r.json()
        last_incident = data['incidents'][0]
        if last_incident['resolved_at'] is None:
            impact = await self.bot._(interaction, "fun.discordstatus-impacts."+last_incident['impact'])
            title = f"**{last_incident['name']}** (<{last_incident['shortlink']}>)"
            await interaction.followup.send(await self.bot._(interaction, "fun.discordstatus-exists", impact=impact, title=title))
        else:
            last_date = datetime.datetime.strptime(last_incident['resolved_at'], '%Y-%m-%dT%H:%M:%S.%f%z')
            last_date = f"<t:{round(last_date.timestamp())}:F>"
            await interaction.followup.send(await self.bot._(interaction, "fun.discordstatus-nothing", date=last_date))

    @commands.command(name="avatar", aliases=['pfp'])
    @commands.cooldown(2, 10, commands.BucketType.user)
    async def avatar(self, ctx: MyContext, user: Optional[discord.User]):
        """Get the avatar of a user"""
        if user is None:
            user = ctx.author
        await ctx.send(user.display_avatar.url)


async def setup(bot):
    await bot.add_cog(Fun(bot))
