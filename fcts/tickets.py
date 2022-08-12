import random
import time
from typing import Any, Callable, Literal, Optional, Union

import discord
from discord.ext import commands
from mysql.connector.errors import IntegrityError
from libs.classes import MyContext, Zbot

from fcts import checks
from fcts.args import UnicodeEmoji

def is_named_other(name: str, other_translated: str):
    "Check if a topic name corresponds to any 'other' variant"
    return name.lower() in {"other", "others", other_translated}

class TicketCreationEvent:
    "Represents a ticket being created"
    def __init__(self, topic: dict, name: str, interaction: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread]):
        self.topic = topic
        self.topic_name = topic["topic"]
        self.name = name
        self.guild = interaction.guild
        self.user = interaction.user
        self.channel = channel

class SelectView(discord.ui.View):
    "Used to ask what kind of ticket a user wants to open"
    def __init__(self, guild_id: int, topics: list[dict[str, Any]]):
        super().__init__(timeout=None)
        options = self.build_options(topics)
        custom_id = f"{guild_id}-tickets-{random.randint(1, 100):03}"
        self.select = discord.ui.Select(placeholder="Chose a topic", options=options, custom_id=custom_id)
        self.add_item(self.select)

    def build_options(self, topics: list[dict[str, Any]]):
        "Compute Select options from topics list"
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
        "When user clicks on the confirm button"
        self.confirmed = True
        self.interaction = interaction
        self.stop()

    async def cancel(self, interaction: discord.Interaction):
        "When user clicks on the cancel button"
        await interaction.response.defer()
        self.confirmed = False
        self.stop()
        await self.disable(interaction)
        await interaction.followup.send(self.text_cancel, ephemeral=True)

    async def disable(self, src: Union[discord.Interaction, discord.Message]):
        "When the view timeouts or is disabled"
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
            await self.callback(interaction, self.topic, self.name.value.strip())
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
            res.append(discord.SelectOption(label=topic['topic'], value=topic['id'], emoji=topic['topic_emoji']))
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
        self.cooldowns: dict[discord.User, float] = {}
        self.default_name_format = "{username}-{usertag}"
        self.max_format_length = 70

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Called when *any* interaction from the bot is created
        We use it to detect interactions with the tickets system"""
        if not interaction.guild:
            # DM : not interesting
            return
        if interaction.type != discord.InteractionType.component:
            # Not button : not interesting
            return
        try:
            custom_ids: list[str] = interaction.data["custom_id"].split('-')
            if len(custom_ids) != 3 or custom_ids[0] != str(interaction.guild_id) or custom_ids[1] != "tickets":
                # unknown custom id
                return
            topic_id: int = int(interaction.data['values'][0])
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            if topic is None:
                if topic_id == -1 and await self.db_get_guild_default_id(interaction.guild_id) is None:
                    await self.db_set_guild_default_id(interaction.guild_id)
                    topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            if topic is None:
                await interaction.response.send_message(await self.bot._(interaction.guild_id, "errors.unknown"), ephemeral=True)
                raise Exception(f"No topic found on guild {interaction.guild_id} with interaction {topic_id}")
            if topic['category'] is None:
                await interaction.response.send_message(await self.bot._(interaction.guild_id, "tickets.missing-category-config"), ephemeral=True)
                return
            if (cooldown := self.cooldowns.get(interaction.user)) and time.time() - cooldown < 120:
                await interaction.response.send_message(await self.bot._(interaction.guild_id, "tickets.too-quick"), ephemeral=True)
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
            self.bot.dispatch('error', err, f"when creating a ticket in guild {interaction.guild_id}")

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
            query = "SELECT t.id, t.guild_id, t.topic, COALESCE(t.topic_emoji, t2.topic_emoji) as topic_emoji, COALESCE(t.prompt, t2.prompt) as `prompt`, COALESCE(t.role, t2.role) as role, COALESCE(t.hint, t2.hint) as `hint`, COALESCE(t.category, t2.category) as `category`, COALESCE(t.name_format, t2.name_format) as name_format, t.beta FROM tickets t LEFT JOIN tickets t2 ON t2.guild_id = t.guild_id AND t2.beta = t.beta AND t2.topic is NULL WHERE t.id = %s AND t.guild_id = %s AND t.beta = %s"
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
    
    async def db_edit_topic_format(self, guild_id: int, topic_id: int, format: Optional[str]) -> bool:
        "Edit a topic channel/thread name format"
        query = "UPDATE `tickets` SET `name_format` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_query(query, (format, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_prompt(self, guild_id: int, message: str):
        "Edit the prompt displayed for a guild"
        query = "UPDATE tickets SET prompt = %s WHERE guild_id = %s AND topic is NULL AND beta = %s"
        async with self.bot.db_query(query, (message, guild_id, self.bot.beta)) as _:
            pass

    async def ask_user_topic(self, ctx: MyContext) -> Optional[int]:
        "Ask a user which topic they want to edit"
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
        desc = await self.bot._(interaction.guild_id, "tickets.ticket-introduction.description",
                                user=interaction.user.mention,
                                ticket_name=ticket_name, topic_name=topic['topic']
                                )
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
    
    async def get_channel_name(self, format: Optional[str], interaction: discord.Interaction, topic: dict, ticket_name: str) -> str:
        channel_name = format or self.default_name_format
        return channel_name.format_map(self.bot.SafeDict({
            "username": interaction.user.name,
            "usertag": interaction.user.discriminator,
            "userid": interaction.user.id,
            "topic": topic["topic"],
            "topic_emoji": topic["topic_emoji"],
            "ticket_name": ticket_name
        }))[:100]

    async def create_ticket(self, interaction: discord.Interaction, topic: dict, ticket_name: str):
        "Create the ticket once the user has provided every required info"
        # update cooldown
        self.cooldowns[interaction.user] = time.time()
        category = interaction.guild.get_channel(topic['category'])
        if category is None:
            raise Exception(f"No category configured for guild {interaction.guild_id} and topic {topic['topic']}")
        sent_error = False
        channel_name = await self.get_channel_name(topic["name_format"], interaction, topic, ticket_name)
        if isinstance(category, discord.CategoryChannel):
            try:
                channel = await category.create_text_channel(channel_name)
            except discord.Forbidden:
                await interaction.edit_original_message(content=await self.bot._(interaction.guild_id, "tickets.missing-perms-creation.channel"))
                return
            try:
                await self.setup_ticket_channel(channel, topic, interaction.user)
            except discord.Forbidden:
                await self.send_missing_permissions_err(interaction, category.name)
                sent_error = True
        elif isinstance(category, discord.TextChannel):
            try:
                if "PRIVATE_THREADS" in interaction.guild.features and category.permissions_for(interaction.guild.me).create_private_threads:
                    channel_type = discord.ChannelType.private_thread
                else:
                    channel_type = discord.ChannelType.public_thread
                channel = await category.create_thread(name=channel_name, type=channel_type)
            except discord.Forbidden:
                await interaction.edit_original_message(content=await self.bot._(interaction.guild_id, "tickets.missing-perms-creation.thread"))
                return
            await self.setup_ticket_thread(channel, topic, interaction.user)
        else:
            self.bot.log.error("[ticket] unknown category type: %s", type(category))
            return
        topic['topic'] = topic['topic'] or await self.bot._(interaction.guild_id, "tickets.other")
        txt: str = await self.bot._(interaction.guild_id, "tickets.ticket-created", channel=channel.mention, topic=topic['topic'])
        if sent_error:
            await interaction.followup.send(txt, ephemeral=True)
        else:
            await interaction.edit_original_message(content=txt)
        msg = await channel.send(embed=await self.create_channel_first_message(interaction, topic, ticket_name))
        if channel.permissions_for(channel.guild.me).manage_messages:
            await msg.pin()
        self.bot.dispatch("ticket_creation", TicketCreationEvent(topic, ticket_name, interaction, channel))



    @commands.group(name="ticket", aliases=["tickets"])
    @commands.guild_only()
    async def tickets_main(self, ctx: MyContext):
        """Manage your tickets system

        ..Doc tickets.html"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['tickets'])

    @tickets_main.group(name="portal")
    @commands.check(checks.has_manage_channels)
    async def tickets_portal(self, ctx: MyContext):
        """Handle how your members are able to open tickets

        ..Doc tickets.html"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['tickets', 'portal'])

    @tickets_portal.command()
    @commands.cooldown(2, 30, commands.BucketType.guild)
    async def summon(self, ctx: MyContext):
        """Ask the bot to send a message allowing people to open tickets

        ..Doc tickets.html#as-staff-send-the-prompt-message"""
        topics = await self.db_get_topics(ctx.guild.id)
        other = {"id": -1,
                 "topic": (await self.bot._(ctx.guild.id, "tickets.other")).capitalize(),
                 "topic_emoji": None
                 }
        defaults = await self.db_get_defaults(ctx.guild.id)
        prompt = defaults["prompt"] if defaults else await self.bot._(ctx.guild.id, "tickets.default-topic-prompt")
        await ctx.send(prompt, view=SelectView(ctx.guild.id, topics + [other]))

    @tickets_portal.command(name="set-hint")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def portal_set_hint(self, ctx: MyContext, *, message: str):
        """Set a default hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "none" for no hint message at all

        ..Example tickets set-hint Make sure to directly state your question when creating your tickets - Please do not use this form for raid-related issues

        ..Doc tickets.html#default-hint"""
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
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def portal_set_role(self, ctx: MyContext, role: Union[discord.Role, Literal["none"]]):
        """Edit a default staff role
        Anyone with this role will be able to read newly created tickets
        Type "None" to set admins only

        ..Example tickets set-role Moderators

        ..Doc tickets.html#default-staff-role"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        if role == "none":
            role = None
        await self.db_edit_topic_role(ctx.guild.id, row_id, role.id if role else None)
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.role-edited.default"))

    @tickets_portal.command(name="set-text")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def portal_set_text(self, ctx: MyContext, *, message: str):
        """Set a message to be displayed above the ticket topic selection

        ..Example tickets set-text Select a category below to start opening your ticket!

        ..Doc tickets.html#presentation-message"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            await self.db_set_guild_default_id(ctx.guild.id)
        await self.db_edit_prompt(ctx.guild.id, message)
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.text-edited"))

    @tickets_portal.command(name="set-category", aliases=["set-channel"])
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def portal_set_category(self, ctx: MyContext, category_or_channel: Union[discord.CategoryChannel, discord.TextChannel]):
        """Set the category or the channel in which tickets will be created

        If you select a channel, tickets will use the Discord threads system but allowed roles may not be applied

        ..Example tickets set-category \"Private channels\"

        ..Example tickets set-channels #tickets

        ..Doc tickets.html#tickets-category-channel"""
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        await self.db_edit_topic_category(ctx.guild.id, row_id, category_or_channel.id)
        embed = None
        if isinstance(category_or_channel, discord.CategoryChannel):
            message = await self.bot._(ctx.guild.id,
                                       "tickets.category-edited.default-category",
                                       category=category_or_channel.name)
            if not category_or_channel.permissions_for(ctx.guild.me).manage_channels:
                embed = discord.Embed(description=await self.bot._(ctx.guild.id,
                                                                   "tickets.category-edited.category-permission-warning"),
                                      colour=discord.Color.orange())
        else:
            message = await self.bot._(ctx.guild.id,
                                       "tickets.category-edited.default-channel",
                                       channel=category_or_channel.mention)
            if "PRIVATE_THREADS" not in ctx.guild.features or not category_or_channel.permissions_for(ctx.guild.me).create_private_threads:
                embed = discord.Embed(description=await self.bot._(ctx.guild.id,
                                                                   "tickets.category-edited.channel-privacy-warning"),
                                      colour=discord.Color.orange())
        await ctx.send(message, embed=embed)

    @tickets_portal.command(name="set-format")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def portal_set_format(self, ctx: MyContext, name_format: Union[Literal["none"], str]):
        """Set the format used to generate the channel/thread name
        You can use the following placeholders: username, usertag, userid, topic, topic_emoji, ticket_name
        Use "none" to reset the format to the default one
        Spaces and non-ascii characters will be removed or replaced by dashes

        ..Example tickets set-format {username}-tickets

        ..Example tickets set-format {username}-{topic}"""
        if len(name_format) > self.max_format_length:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.format.too-long", max=self.max_format_length))
            return
        row_id = await self.db_get_guild_default_id(ctx.guild.id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(ctx.guild.id)
        if name_format.lower() == "none":
            name_format = None
        await self.db_edit_topic_format(ctx.guild.id, row_id, name_format)
        await ctx.send(await self.bot._(ctx.guild.id, "tickets.format.edited.default"))


    @tickets_main.group(name="topic", aliases=["topics"])
    @commands.check(checks.has_manage_channels)
    async def tickets_topics(self, ctx: MyContext):
        """Handle the different ticket topics your members can select

        ..Doc tickets.html"""
        if ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['tickets', 'topic'])

    @tickets_topics.command(name="add")
    @commands.cooldown(3, 45, commands.BucketType.guild)
    async def topic_add(self, ctx: MyContext, emote: Union[discord.PartialEmoji, UnicodeEmoji, None]=None, *, name: str):
        """Create a new ticket topic
        A topic name is limited to 100 characters
        Only Discord emojis are accepted for now

        ..Example tickets topic add :diamonds: Economy issues

        ..Example tickets topic add Request a magician

        ..Doc tickets.html#create-a-new-topic"""
        if len(name) > 100:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.too-long"))
            return
        if is_named_other(name, await self.bot._(ctx.guild.id, "tickets.other")):
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.other-already-exists"))
            return
        if isinstance(emote, discord.PartialEmoji):
            emote = f"{emote.name}:{emote.id}"
        if await self.db_add_topic(ctx.guild.id, name, emote):
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.created", name=name))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.cant-create"))

    @tickets_topics.command(name="remove")
    @commands.cooldown(3, 45, commands.BucketType.guild)
    async def topic_remove(self, ctx: MyContext):
        """Permanently delete a topic by its name

        ..Doc tickets.html#delete-a-topic"""
        topic_id = await self.ask_user_topic(ctx)
        if topic_id is None:
            await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
            return
        topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
        if await self.db_delete_topic(ctx.guild.id, topic_id):
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.topic.deleted", name=topic["topic"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))

    @tickets_topics.command(name="set-emote", aliases=["set-emoji"])
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def topic_set_emote(self, ctx: MyContext, topic_id: Optional[int],
                              emote: Union[discord.PartialEmoji, UnicodeEmoji, Literal["none"]]):
        """Edit a topic emoji
        Type "None" to set no emoji for this topic

        ..Example tickets topic set-emote :money_with_wings:

        ..Doc tickets.html#edit-a-topic-emoji"""
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
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def topic_set_hint(self, ctx: MyContext, topic_id: Optional[int], *, message: str):
        """Edit a topic hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "None" to set the text to the default one (`tickets portal set-hint`)

        ..Example tickets topic set-hint When trying to join our Minecraft server, make sure to correctly enter our IP!
If that still doesn't work, please create your ticket

        ..Doc tickets.html#topic-specific-hint"""
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
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def topic_set_role(self, ctx: MyContext, topic_id: Optional[int], role: Union[discord.Role, Literal["none"]]):
        """Edit a topic staff role
        Anyone with this role will be able to read newly created tickets with this topic
        Type "None" to set the role to the default one (`tickets portal set-role`)

        ..Example tickets topic set-role @Staff

        ..Example tickets topic set-role 347 \"Minecraft moderators\"

        ..Doc tickets.html#topic-specific-staff-role"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
                return
        if role.lower() == "none":
            role = None
        if await self.db_edit_topic_role(ctx.guild.id, topic_id, role.id if role else None):
            topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.role-edited.topic", topic=topic["topic"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.nothing-to-edit"))

    @tickets_topics.command(name="set-format")
    @commands.cooldown(3, 30, commands.BucketType.guild)
    async def topic_set_role(self, ctx: MyContext, topic_id: Optional[int], name_format: Union[Literal["none"], str]):
        """Set the format used to generate the channel/thread name
        You can use the following placeholders: username, usertag, userid, topic, topic_emoji, ticket_name
        Use "none" to reset the format to the default one
        Spaces and non-ascii characters will be removed or replaced by dashes

        ..Example tickets set-format {username}-special

        ..Example tickets set-format 347 {username}-{topic}"""
        if not topic_id or not await self.db_topic_exists(ctx.guild.id, topic_id):
            topic_id = await self.ask_user_topic(ctx)
            if topic_id is None:
                await ctx.send(await self.bot._(ctx.guild.id, "errors.unknown"))
                return
        if len(name_format) > self.max_format_length:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.format.too-long", max=self.max_format_length))
            return
        if name_format.lower() == "none":
            name_format = None
        if await self.db_edit_topic_format(ctx.guild.id, topic_id, name_format):
            topic = await self.db_get_topic_with_defaults(ctx.guild.id, topic_id)
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.format.edited.topic", topic=topic["topic"]))
        else:
            await ctx.send(await self.bot._(ctx.guild.id, "tickets.nothing-to-edit"))


    @tickets_topics.command(name="list")
    @commands.cooldown(3, 20, commands.BucketType.guild)
    async def topic_set_roles(self, ctx: MyContext):
        "List every ticket topic used in your server"
        topics_repr: list[str] = []
        none_emoji: str = self.bot.emojis_manager.customs['nothing']
        topics = await self.db_get_topics(ctx.guild.id)
        topics.append(await self.db_get_defaults(ctx.guild.id))
        for topic in topics:
            name = topic['topic'] or await self.bot._(ctx.guild.id, "tickets.other")
            if topic['topic_emoji']:
                emoji = discord.PartialEmoji.from_str(topic['topic_emoji'])
                topics_repr.append(f"{emoji} {name}")
            else:
                topics_repr.append(f"{none_emoji} {name}")
            if topic['role']:
                topics_repr[-1] += f" - <@&{topic['role']}>"
        title = await ctx.bot._(ctx.guild.id, "tickets.topic.list")
        if ctx.can_send_embed:
            embed = discord.Embed(title=title, description="\n".join(topics_repr), color=discord.Color.blue())
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"**{title}**\n\n" + "\n".join(topics_repr))

async def setup(bot):
    await bot.add_cog(Tickets(bot))
