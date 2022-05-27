import re
import discord
from discord.ext import commands
import random
from typing import Any, Callable, Optional, Union, Literal
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
    def __init__(self, user_id: int, label_confirm: str, label_cancel: str, text_cancel: str):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.confirmed: Optional[bool] = None
        self.interaction: Optional[discord.Interaction] = None
        confirm_btn = discord.ui.Button(label=label_confirm, style=discord.ButtonStyle.green)
        confirm_btn.callback = self.confirm
        self.add_item(confirm_btn)
        self.text_cancel = text_cancel
        cancel_btn = discord.ui.Button(label=label_cancel, style=discord.ButtonStyle.red)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user_id

    async def confirm(self, interaction: discord.Interaction):
        self.confirmed = True
        self.interaction = interaction
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.confirmed = False
        self.stop()
        await self.disable(interaction)
        await interaction.followup.send(self.text_cancel, ephemeral=True)

    async def disable(self, src: Union[discord.Interaction, discord.Message]):
        for child in self.children:
            child.disabled = True
        if isinstance(src, discord.Interaction):
            await src.edit_original_message(view=self)
        else:
            await src.edit(content=src.content, embeds=src.embeds, view=self)
        self.stop()


class AskTitleModal(discord.ui.Modal):
    "Ask a user the name of their ticket"
    name = discord.ui.TextInput(label="", placeholder=None, style=discord.TextStyle.short, max_length=100)
    
    def __init__(self, guild_id: int, topic: dict, title: str, input_label: str, input_placeholder: str, callback: Callable):
        super().__init__(title=title, timeout=600)
        self.guild_id = guild_id
        self.topic = topic
        self.callback = callback
        self.name.label = input_label
        self.name.placeholder = input_placeholder

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
            await self.callback(interaction, self.topic, self.name.value)
        except Exception as err: # pylint: disable=broad-except
            interaction.client.dispatch("error", err)

class AskTopicSelect(discord.ui.View):
    "Ask a user what topic they want to edit/delete"
    def __init__(self, user_id: int, topics: list[dict[str, Any]], placeholder: str, max_values: int):
        super().__init__()
        self.user_id = user_id
        options = self.build_options(topics)
        self.select = discord.ui.Select(placeholder=placeholder, min_values=1, max_values=max_values, options=options)
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
        try:
            custom_ids: list[str] = interaction.data["custom_id"].split('-')
            if len(custom_ids) != 3 or custom_ids[0] != str(interaction.guild_id) or custom_ids[1] != "tickets":
                # unknown custom id
                return
            topic_id: int = int(interaction.data['values'][0])
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            if topic is None:
                await interaction.response.send_message(await self.bot._(interaction.guild_id, "errors.unknown"))
                return
            if topic['hint']:
                hint_view = SendHintText(interaction.user.id,
                    await self.bot._(interaction.guild_id, "tickets.hint-useless"),
                    await self.bot._(interaction.guild_id, "tickets.hint-useful"),
                    await self.bot._(interaction.guild_id, "tickets.cancelled"))
                embed = discord.Embed(color=discord.Color.green(), title=topic['topic'], description=topic['hint'])
                await interaction.response.send_message(embed=embed, view=hint_view, ephemeral=True)
                await hint_view.wait()
                if hint_view.confirmed is None:
                    # timeout
                    await hint_view.disable(interaction)
                    return
                if not hint_view.confirmed:
                    # cancelled
                    return
                if hint_view.interaction:
                    interaction = hint_view.interaction
            modal_title = await self.bot._(interaction.guild_id, "tickets.title-modal.title")
            modal_label = await self.bot._(interaction.guild_id, "tickets.title-modal.label")
            modal_placeholder = await self.bot._(interaction.guild_id, "tickets.title-modal.placeholder")
            await interaction.response.send_modal(AskTitleModal(interaction.guild.id, topic, modal_title, modal_label, modal_placeholder, self.create_ticket))
        except Exception as err: # pylint: disable=broad-except
            self.bot.dispatch('error', err)
    
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
            query = "SELECT t.id, t.guild_id, t.topic, COALESCE(t.topic_emoji, t2.topic_emoji) as topic_emoji, COALESCE(t.prompt, t2.prompt) as `prompt`, COALESCE(t.role, t2.role) as role, COALESCE(t.hint, t2.hint) as `hint`, COALESCE(t.category, t2.category) as `category`, t.beta FROM tickets t LEFT JOIN tickets t2 ON t2.guild_id = t.guild_id AND t2.beta = t.beta AND t2.topic is NULL WHERE t.id = %s AND t.guild_id = %s AND t.beta = %s"
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

    async def db_delete_topic(self, guild_id: int, topic_id: int) -> bool:
        "Delete a topic from a guild"
        query = "DELETE FROM `tickets` WHERE `guild_id` = %s AND id = %s AND `beta` = %s"
        async with self.bot.db_query(query, (guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
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

    async def db_edit_topic_category(self, guild_id: int, topic_id: int, category: Optional[int]) -> bool:
        "Edit a topic category or channel in which tickets will be created"
        query = "UPDATE `tickets` SET `category` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (category, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_prompt(self, guild_id: int, message: str):
        query = "UPDATE tickets SET prompt = %s WHERE guild_id = %s AND topic is NULL AND beta = %s"
        async with self.bot.db_query(query, (message, guild_id, self.bot.beta)) as _:
            pass

    async def ask_user_topic(self, ctx: MyContext) -> Optional[int]:
        placeholder = await self.bot._(ctx.guild.id, "tickets.selection-placeholder")
        view = AskTopicSelect(ctx.author.id, await self.db_get_topics(ctx.guild.id), placeholder, 1)
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.choose-topic-edition"), view=view)
        await view.wait()
        if view.topics is None:
            return None
        try:
            topic_id = int(view.topics[0])
        except (ValueError, IndexError):
            return None
        return topic_id

    async def create_channel_first_message(self, interaction: discord.Interaction, topic: dict, ticket_name: str) -> discord.Embed:
        "Create the introduction message at the beginning of the ticket"
        title = await self.bot._(interaction.guild_id, "tickets.ticket-introduction.title")
        topic_name = topic['topic'] or await self.bot._(interaction.guild_id, "tickets.other")
        desc = await self.bot._(interaction.guild_id, "tickets.ticket-introduction.description", user=interaction.user.mention, ticket_name=ticket_name, topic_name=topic_name)
        return discord.Embed(title=title, description=desc, color=discord.Color.green())
    
    async def setup_ticket_channel(self, channel: discord.TextChannel, topic: dict, user: discord.Member):
        "Setup the required permissions for a channel ticket"
        permissions = {}
        # set for everyone
        permissions[channel.guild.default_role] = discord.PermissionOverwrite(read_messages=False)
        # set for the user and the bot
        permissions[user] = discord.PermissionOverwrite(send_messages=True, read_messages=True)
        permissions[channel.guild.me] = discord.PermissionOverwrite(send_messages=True, read_messages=True)
        # set for the staff
        if (role_id := topic.get('role')) and (role := channel.guild.get_role(role_id)):
            permissions[role] = discord.PermissionOverwrite(
                send_messages=True,
                read_messages=True,
                manage_messages=True,
                manage_channels=True
            )
        # apply everything
        await channel.edit(overwrites=permissions)

    async def setup_ticket_thread(self, thread: discord.Thread, topic: dict, user: discord.Member):
        "Add the required members to a Discord thread ticket"
        mentions = [thread.guild.me.mention, user.mention]
        if (role_id := topic.get('role')) and (role := thread.guild.get_role(role_id)):
            mentions.append(role.mention)
        # sneaky tactic to add a lot of people:
        # send an empty message (to avoid notifying them)
        msg = await thread.send("...")
        # then mention them in the previous message to add them to the thread
        await msg.edit(content=" ".join(mentions), allowed_mentions=discord.AllowedMentions.all())
        # then delete to cleanup things
        await msg.delete()

    async def send_missing_permissions_err(self, interaction: discord.Interaction, category: str):
        "Send an error when the bot couldn't set up the channel permissions"
        if interaction.user.guild_permissions.manage_roles:
            msg = await self.bot._(interaction.guild_id, "tickets.missing-perms-setup.to-staff", category=category)
        else:
            msg = await self.bot._(interaction.guild_id, "tickets.missing-perms-setup.to-member")
        await interaction.edit_original_message(content=msg)

    async def create_ticket(self, interaction: discord.Interaction, topic: dict, ticket_name: str):
        "Create the ticket once the user has provided every required info"
        category = interaction.guild.get_channel(topic['category'])
        if category is None:
            return
        if isinstance(category, discord.CategoryChannel):
            try:
                channel = await category.create_text_channel(str(interaction.user))
            except discord.Forbidden:
                await interaction.edit_original_message(content=await self.bot._(interaction.guild_id, "tickets.missing-perms-creation.channel"))
                return
            try:
                await self.setup_ticket_channel(channel, topic, interaction.user)
            except discord.Forbidden:
                await self.send_missing_permissions_err(interaction, category.name)
        elif isinstance(category, discord.TextChannel):
            try:
                if "PRIVATE_THREADS" in interaction.guild.features and category.permissions_for(interaction.guild.me).create_private_threads:
                    channel_type = discord.ChannelType.private_thread
                else:
                    channel_type = discord.ChannelType.public_thread
                channel = await category.create_thread(name=str(interaction.user), type=channel_type)
            except discord.Forbidden:
                await interaction.edit_original_message(content=await self.bot._(interaction.guild_id, "tickets.missing-perms-creation.thread"))
                return
            await self.setup_ticket_thread(channel, topic, interaction.user)
        else:
            self.bot.log.error("[ticket] unknown category type: %s", type(category))
            return
        await interaction.edit_original_message(content=await self.bot._(interaction.guild_id, "tickets.ticket-created", channel=channel.mention, topic=topic['topic']))
        await channel.send(embed=await self.create_channel_first_message(interaction, topic, ticket_name))


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
        other = {"id": -1,
                 "topic": (await self.bot._(ctx.guild.id, "tickets.other")).capitalize(),
                 "topic_emoji": None
                 }
        defaults = await self.db_get_defaults(ctx.guild.id)
        prompt = defaults["prompt"] if defaults else await self.bot._(ctx.guild.id, "tickets.default-topic-prompt")
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
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.hint-edited.default"))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))

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
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.role-edited.default"))

    @tickets_portal.command(name="set-text")
    async def portal_set_text(self, ctx: MyContext, *, message: str):
        """Set a message to be displayed above the ticket topic selection"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        await self.db_edit_prompt(ctx.guild.id, message)
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.text-edited"))

    @tickets_portal.command(name="set-category", aliases=["set-channel"])
    async def portal_set_category(self, ctx: MyContext, category_or_channel: Union[discord.CategoryChannel, discord.TextChannel]):
        """Set the category or the channel in which tickets will be created
        
        If you select a channel, tickets will use the Discord threads system but allowed roles may not be applied"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        await self.db_edit_topic_category(ctx.guild.id, row_id, category_or_channel.id)
        embed = None
        if isinstance(category_or_channel, discord.CategoryChannel):
            message = await self.bot._(ctx.guild.id, "tickets.category-edited.default-category", category=category_or_channel.name)
            if not category_or_channel.permissions_for(ctx.guild.me).manage_channels:
                embed = discord.Embed(description=await self.bot._(ctx.guild.id, "tickets.category-edited.category-permission-warning"), colour=discord.Color.orange())
        else:
            message = await self.bot._(ctx.guild.id, "tickets.category-edited.default-channel", channel=category_or_channel.mention)
            if "PRIVATE_THREADS" not in ctx.guild.features or not category_or_channel.permissions_for(ctx.guild.me).create_private_threads:
                embed = discord.Embed(description=await self.bot._(ctx.guild.id, "tickets.category-edited.channel-privacy-warning"), colour=discord.Color.orange())
        await ctx.send(message, embed=embed)


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
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.too-long"))
            return
        if await self.db_add_topic(ctx.guild.id, name, f"{emote.name}:{emote.id}" if emote else None):
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.created", name=name))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.cant-create"))

    @tickets_topics.command(name="remove")
    async def topic_remove(self, ctx: MyContext, topic_id: Optional[int]):
        "Permanently delete a topic by its name"
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
                return
        topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
        if await self.db_delete_topic(ctx.guild.id, topic_id):
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.deleted", name=topic["topic"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))

    @tickets_topics.command(name="set-emote")
    async def topic_set_emote(self, ctx: MyContext, topic_id: Optional[int], emote: Union[discord.PartialEmoji, Literal["none"]]):
        """Edit a topic emoji
        Type "None" to set no emoji for this topic"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
                return
        if emote == "none":
            emote = None
        if await self.db_edit_topic_emoji(ctx.guild.id, topic_id, f"{emote.name}:{emote.id}" if emote else None):
            topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.emote-edited", topic=topic["topic"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.nothing-to-edit"))

    @tickets_topics.command(name="set-hint")
    async def topic_set_hint(self, ctx: MyContext, topic_id: Optional[int], *, message: str):
        """Edit a topic hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "None" to set the text to the default one (`tickets portal set-hint`)"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
                return
        if message.lower() == "none":
            message = None
        await self.db_edit_topic_hint(ctx.guild.id, topic_id, message)
        topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.hint-edited.topic", topic=topic["topic"]))

    @tickets_topics.command(name="set-role")
    async def topic_set_role(self, ctx: MyContext, topic_id: Optional[int], role: Union[discord.Role, Literal["none"]]):
        """Edit a topic staff role
        Anyone with this role will be able to read newly created tickets with this topic
        Type "None" to set the role to the default one (`tickets portal set-role`)"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
                return
        if role == "none":
            role = None
        if await self.db_edit_topic_role(ctx.guild.id, topic_id, role.id if role else None):
            topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.role-edited.topic", topic=topic["topic"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.nothing-to-edit"))


async def setup(bot):
    await bot.add_cog(Tickets(bot))
