import re
import discord
from discord.ext import commands
import random
from typing import Any, Optional, Union, Literal
from mysql.connector.errors import IntegrityError

from libs.classes import MyContext, Zbot


class SelectView(discord.ui.View):
    "Used to ask what kind of ticket a user wants to open"
    def __init__(self, guild_id: int, topics: list[dict[str, Any]]):
        super().__init__(timeout=None)
        options = self.build_options(topics)
        custom_id = f"{guild_id}-tickets-{random.randint(1, 100):03}"
        self.select = discord.ui.Select(placeholder="Chose a topic", options=options, custom_id=custom_id)
        self.add_item(self.select)
    
    def build_options(self, topics: list[dict[str, Any]]):
        res = []
        for topic in topics:
            res.append(discord.SelectOption(label=topic['topic'], value=topic['id'], emoji=topic['topic_emoji']))
        return res

class AskTitleModal(discord.ui.Modal):
    name = discord.ui.TextInput(label="Your subject", placeholder="Type here a meaningful ticket name", style=discord.TextStyle.short, max_length=100)
    
    def __init__(self, guild_id: int, topic: str):
        super().__init__(title="Your ticket", timeout=600)
        self.guild_id = guild_id
        self.topic = topic

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("no")

class AskTopicSelect(discord.ui.View):
    "Ask a user what topic they want to edit/delete"
    def __init__(self, topics: list[dict[str, Any]], max_values: int):
        super().__init__()
        options = self.build_options(topics)
        self.select = discord.ui.Select(placeholder='Choose a topic', min_values=1, max_values=max_values, options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
        self.topics: list[str] = None

    def build_options(self, topics: list[dict[str, Any]]) -> list[discord.SelectOption]:
        "Build the options list for Discord"
        res = []
        for topic in topics:
            res.append(discord.SelectOption(value=topic['id'], label=topic['topic']))
        return res

    async def callback(self, interaction: discord.Interaction):
        "Called when the dropdown menu has been validated by the user"
        self.topics = self.select.values
        await interaction.response.defer()
        self.select.disabled = True
        await interaction.edit_original_message(view=self)
        self.stop()


class Tickets(commands.Cog):
    "Handle the bot tickets system"

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "tickets"
        self.bot.add_view
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Called when *any* interaction from the bot is created
        We use it to detect interactions with the tickets system"""
        if not interaction.guild:
            # DM : not interesting
            return
        custom_ids: list[str] = interaction.data["custom_id"].split('-')
        if len(custom_ids) != 3 or custom_ids[0] != str(interaction.guild_id) or custom_ids[1] != "tickets":
            # unknown custom id
            return
        topic: str = interaction.data['values'][0]
        await interaction.response.send_modal(AskTitleModal(interaction.guild.id, topic))
    
    async def db_get_topics(self, guild_id: int) -> list[dict[str, Any]]:
        "Fetch the topics associated to a guild"
        query = "SELECT * FROM tickets WHERE guild_id = %s AND topic IS NOT NULL AND beta=%s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta)) as db_query:
            return db_query
    
    async def db_add_topic(self, guild_id: int, name: str, emoji: Union[None, str]) -> bool:
        "Add a topic to a guild"
        query = "INSERT INTO tickets (guild_id, topic, topic_emoji, beta) VALUES (%s, %s, %s, %s)"
        try:
            async with self.bot.db_query(query, (guild_id, name, emoji, self.bot.beta), returnrowcount=True) as db_query:
                return db_query > 0
        except IntegrityError:
            return False

    async def db_delete_topic(self, guild_id: int, name: str) -> bool:
        "Delete a topic from a guild"
        query = "DELETE FROM tickets WHERE guild_id = %s AND LOWER(topic) = %s AND beta = %s"
        async with self.bot.db_query(query, (guild_id, name.lower(), self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_topic_exists(self, guild_id: int, topic_id: int):
        "Check if a topic exists for a guild"
        query = "SELECT 1 FROM tickets WHERE guild_id = %s AND id = %s AND beta = %s"
        async with self.bot.db_query(query, (guild_id, topic_id, self.bot.beta)) as db_query:
            return len(db_query) > 0

    async def db_edit_topic_emoji(self, guild_id: int, topic_id: int, emoji: Optional[str]) -> bool:
        "Edit a topic emoji"
        query = "UPDATE tickets SET topic_emoji = %s WHERE guild_id = %s AND id = %s AND beta = %s"
        async with self.bot.db_query(query, (emoji, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0


    @commands.group(name="ticket", aliases=["tickets"])
    @commands.guild_only()
    async def tickets_main(self, ctx: MyContext):
        "Manage your tickets system"
        pass

    @tickets_main.group(name="portal")
    async def tickets_portal(self, ctx: MyContext):
        "Handle how your members are able to open tickets"
        pass

    @tickets_portal.command()
    async def summon(self, ctx: MyContext):
        "Ask the bot to send a message allowing people to open tickets"
        topics = await self.db_get_topics(ctx.guild.id)
        for topic in topics:
            # if emoji is a discord emoji, convert it
            if re.match(r'[A-Za-z0-9\_]+:[0-9]{13,20}', topic['topic_emoji']):
                topic['topic_emoji'] = discord.PartialEmoji.from_str(topic['topic_emoji'])
        other = {"id": -1, "topic": "Other", "topic_emoji": None}
        await ctx.send("Select a ticket category", view=SelectView(ctx.guild.id, topics + [other]))


    @tickets_main.group(name="topic")
    async def tickets_topics(self, ctx: MyContext):
        "Handle the different ticket topics your members can select"
        pass

    @tickets_topics.command(name="add")
    async def topic_add(self, ctx: MyContext, emote: Optional[discord.PartialEmoji]=None, *, name: str):
        """Create a new ticket topic
        A topic name is limited to 100 characters
        Only Discord emojis are accepted for now"""
        if len(name) > 100:
            await ctx.send("NOPE")
            return
        if await self.db_add_topic(ctx.guild.id, name, f"{emote.name}:{emote.id}" if emote else None):
            await ctx.send("SUCCESS!")
        else:
            await ctx.send("FAILURE!")

    @tickets_topics.command(name="remove")
    async def topic_remove(self, ctx: MyContext, *, name: str):
        "Permanently delete a topic by its name"
        if await self.db_delete_topic(ctx.guild.id, name):
            await ctx.send("SUCCESS")
        else:
            await ctx.send("DOES NOT EXIST")

    @tickets_topics.command(name="set-emote")
    async def topic_set_emote(self, ctx: MyContext, topic_id: Optional[int], emote: Union[discord.PartialEmoji, Literal["none"]]):
        """Edit a topic emoji
        Type "None" to set no emoji for this topic"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            view = AskTopicSelect(await self.db_get_topics(ctx.guild.id), 1)
            await ctx.send("Choose which topic to edit", view=view)
            await view.wait()
            if view.topics is None:
                return
            try:
                topic_id = int(view.topics[0])
            except (ValueError, IndexError):
                await ctx.send("NOPE")
                return
        if emote == "none":
            emote = None
        if await self.db_edit_topic_emoji(ctx.guild.id, topic_id, f"{emote.name}:{emote.id}"):
            await ctx.send("EDITED")
        else:
            await ctx.send("FAILURE")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
