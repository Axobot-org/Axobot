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

class SendHintText(discord.ui.View):
    "Used to send a hint and make sure the user actually needs help"
    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id
        self.confirmed: bool = None
    
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id
    
    @discord.ui.button(label='YES PLZ', style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message('CONFIRMING', ephemeral=True)
        self.value = True
        self.stop()

    @discord.ui.button(label='NO THX', style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.value = False
        self.stop()
        await self.disable(interaction)
        await interaction.followup.send("CANCELLING", ephemeral=True)
    
    async def disable(self, src: Union[discord.Interaction, discord.Message]):
        for child in self.children:
            child.disabled = True
        if isinstance(src, discord.Interaction):
            await src.edit_original_message(view=self)
        else:
            await src.edit(content=src.content, embeds=src.embeds, view=self)
        self.stop()


class AskTitleModal(discord.ui.Modal):
    name = discord.ui.TextInput(label="Your subject", placeholder="Type here a meaningful ticket name", style=discord.TextStyle.short, max_length=100)
    
    def __init__(self, guild_id: int, topic: int):
        super().__init__(title="Your ticket", timeout=600)
        self.guild_id = guild_id
        self.topic = topic

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("no")

class AskTopicSelect(discord.ui.View):
    "Ask a user what topic they want to edit/delete"
    def __init__(self, user_id: int, topics: list[dict[str, Any]], max_values: int):
        super().__init__()
        self.user_id = user_id
        options = self.build_options(topics)
        self.select = discord.ui.Select(placeholder='Choose a topic', min_values=1, max_values=max_values, options=options)
        self.select.callback = self.callback
        self.add_item(self.select)
        self.topics: list[str] = None
    
    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id

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
        topic_id: int = int(interaction.data['values'][0])
        topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
        if topic is None:
            await interaction.response.send_message("OOPS ERROR")
            return
        if topic['hint']:
            hint_view = SendHintText(interaction.user.id)
            embed = discord.Embed(color=discord.Color.green(), title=topic['topic'], description=topic['hint'])
            await interaction.response.send_message(embed=embed, view=hint_view, ephemeral=True)
            await hint_view.wait()
            if not hint_view.value:
                return
        await interaction.response.send_modal(AskTitleModal(interaction.guild.id, topic))
    
    async def db_get_topics(self, guild_id: int) -> list[dict[str, Any]]:
        "Fetch the topics associated to a guild"
        query = "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `topic` IS NOT NULL AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta)) as db_query:
            return db_query

    async def db_get_defaults(self, guild_id: int) -> Optional[dict[str, Any]]:
        "Get the default values for a guild"
        query = "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `topic` IS NULL AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta), fetchone=True) as db_query:
            return db_query or None

    async def db_get_topic_with_defaults(self, guild_id: int, topic_id: int) -> dict[str, Any]:
        "Fetch a topicfrom its guild and ID"
        if topic_id == -1:
            query = "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `topic` IS NULL AND `beta` = %s"
            args = (guild_id, self.bot.beta)
        else:
            query = "SELECT t.id, t.guild_id, t.topic, COALESCE(t.topic_emoji, t2.topic_emoji) as topic_emoji, COALESCE(t.prompt, t2.prompt) as `prompt`, COALESCE(t.role, t2.role) as role, COALESCE(t.hint, t2.hint) as `hint`, t.beta FROM tickets t LEFT JOIN tickets t2 ON t2.guild_id = t.guild_id AND t2.beta = t.beta AND t2.topic is NULL WHERE t.id = %s AND t.guild_id = %s AND t.beta = %s"
            args = (topic_id, guild_id, self.bot.beta)
        async with self.bot.db_query(query, args, fetchone=True) as db_query:
            return db_query or None

    async def db_get_guild_default_id(self, guild_id: int) -> Optional[int]:
        "Return the row ID corresponding to the default guild setup, or None"
        query = "SELECT id FROM `tickets` WHERE guild_id = %s AND topic IS NULL AND beta = %s"
        async with self.bot.db_query(query, (guild_id, self.bot.beta), fetchone=True) as db_query:
            if not db_query:
                return None
            return db_query['id']
    
    async def db_set_guild_default_id(self, guild_id: int) -> int:
        "Create a new row for default guild setup"
        # INSERT only if not exists
        query = "INSERT INTO `tickets` (guild_id, beta) SELECT %(g)s, %(b)s WHERE (SELECT 1 as `exists` FROM `tickets` WHERE guild_id = %(g)s AND topic IS NULL AND beta = %(b)s) IS NULL"
        async with self.bot.db_query(query, {'g': guild_id, 'b': self.bot.beta}) as db_query:
            return db_query
    
    async def db_add_topic(self, guild_id: int, name: str, emoji: Union[None, str]) -> bool:
        "Add a topic to a guild"
        query = "INSERT INTO `tickets` (`guild_id`, `topic`, `topic_emoji`, `beta`) VALUES (%s, %s, %s, %s)"
        try:
            async with self.bot.db_query(query, (guild_id, name, emoji, self.bot.beta), returnrowcount=True) as db_query:
                return db_query > 0
        except IntegrityError:
            return False

    async def db_delete_topic(self, guild_id: int, name: str) -> bool:
        "Delete a topic from a guild"
        query = "DELETE FROM `tickets` WHERE `guild_id` = %s AND LOWER(`topic`) = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, name.lower(), self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_topic_exists(self, guild_id: int, topic_id: int):
        "Check if a topic exists for a guild"
        query = "SELECT 1 FROM `tickets` WHERE `guild_id` = %s AND `id` = %s AND `topic` IS NOT NULL AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, topic_id, self.bot.beta)) as db_query:
            return len(db_query) > 0

    async def db_edit_topic_emoji(self, guild_id: int, topic_id: int, emoji: Optional[str]) -> bool:
        "Edit a topic emoji"
        query = "UPDATE `tickets` SET `topic_emoji` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (emoji, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_hint(self, guild_id: int, topic_id: int, hint: Optional[str]) -> bool:
        "Edit a topic emoji"
        query = "UPDATE `tickets` SET `hint` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (hint, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_role(self, guild_id: int, topic_id: int, role_id: Optional[int]) -> bool:
        "Edit a topic emoji"
        query = "UPDATE tickets SET role = %s WHERE guild_id = %s AND id = %s AND beta = %s"
        async with self.bot.db_query(query, (role_id, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_prompt(self, guild_id: int, message: str):
        query = "UPDATE tickets SET prompt = %s WHERE guild_id = %s AND topic is NULL AND beta = %s"
        async with self.bot.db_query(query, (message, guild_id, self.bot.beta)) as _:
            pass

    async def ask_user_topic(self, ctx: MyContext) -> Optional[int]:
        view = AskTopicSelect(ctx.author.id, await self.db_get_topics(ctx.guild.id), 1)
        await ctx.send("Choose which topic to edit", view=view)
        await view.wait()
        if view.topics is None:
            return None
        try:
            topic_id = int(view.topics[0])
        except (ValueError, IndexError):
            return None
        return topic_id

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
        defaults = await self.db_get_defaults(ctx.guild.id)
        prompt = defaults["prompt"] if defaults else "Select a ticket category"
        await ctx.send(prompt, view=SelectView(ctx.guild.id, topics + [other]))

    @tickets_portal.command(name="set-hint")
    async def portal_set_hint(self, ctx: MyContext, *, message: str):
        """Set a default hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "none" for no hint message at all"""
        if message.lower() == "none":
            message = None
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        if await self.db_edit_topic_hint(ctx.guild.id, row_id, message):
            await ctx.send("SUCCESS")
        else:
            await ctx.send("FAILURE")

    @tickets_portal.command(name="set-role")
    async def portal_set_role(self, ctx: MyContext, role: Union[discord.Role, Literal["none"]]):
        """Edit a default staff role
        Anyone with this role will be able to read newly created tickets
        Type "None" to set admins only"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        if role == "none":
            role = None
        await self.db_edit_topic_role(ctx.guild.id, row_id, role.id if role else None)
        await ctx.send("SUCCESS")

    @tickets_portal.command(name="set-text")
    async def portal_set_text(self, ctx: MyContext, *, message: str):
        """Set a message to be displayed above the ticket topic selection"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        await self.db_edit_prompt(ctx.guild.id, message)
        await ctx.send("SUCCESS")


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
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send("NOPE")
                return
        if emote == "none":
            emote = None
        if await self.db_edit_topic_emoji(ctx.guild.id, topic_id, f"{emote.name}:{emote.id}" if emote else None):
            await ctx.send("EDITED")
        else:
            await ctx.send("FAILURE")

    @tickets_topics.command(name="set-hint")
    async def topic_set_hint(self, ctx: MyContext, topic_id: Optional[int], *, message: str):
        """Edit a topic hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "None" to set the text to the default one (`tickets portal set-hint`)"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send("NOPE")
                return
        if message.lower() == "none":
            message = None
        if await self.db_edit_topic_hint(ctx.guild.id, topic_id, message):
            await ctx.send("EDITED")
        else:
            await ctx.send("FAILURE")

    @tickets_topics.command(name="set-role")
    async def topic_set_role(self, ctx: MyContext, topic_id: Optional[int], role: Union[discord.Role, Literal["none"]]):
        """Edit a topic staff role
        Anyone with this role will be able to read newly created tickets with this topic
        Type "None" to set the role to the default one (`tickets portal set-role`)"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send("NOPE")
                return
        if role == "none":
            role = None
        if await self.db_edit_topic_role(ctx.guild.id, topic_id, role.id if role else None):
            await ctx.send("EDITED")
        else:
            await ctx.send("FAILURE")


async def setup(bot):
    await bot.add_cog(Tickets(bot))
