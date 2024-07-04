import logging
import time

import discord
from discord import app_commands
from discord.ext import commands
from mysql.connector.errors import IntegrityError

from core.arguments import PartialorUnicodeEmojiArgument
from core.bot_classes import Axobot
from core.enums import ServerWarningType

from .src.types import DBTopicRow, TicketCreationEvent
from .src.views import AskTitleModal, AskTopicSelect, SelectView, SendHintText


def is_named_other(name: str, other_translated: str):
    "Check if a topic name corresponds to any 'other' variant"
    return name.lower() in {"other", "others", other_translated}

TopicNameArgument = app_commands.Range[str, 1, 100]
ChannelNameFormatArgument = app_commands.Range[str, 1, 70]
HintTextArgument = app_commands.Range[str, 1, 2000]
MAX_TOPICS_PER_GUILD = 25

class Tickets(commands.Cog):
    "Handle the bot tickets system"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "tickets"
        self.log = logging.getLogger("bot.tickets")
        self.cooldowns: dict[discord.User, float] = {}
        self.default_name_format = "{username}-{topic}"

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
            topic_id: int = int(interaction.data["values"][0])
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            if topic is None:
                if topic_id == -1 and await self.db_get_guild_default_id(interaction.guild_id) is None:
                    await self.db_set_guild_default_id(interaction.guild_id)
                    topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            if topic is None:
                await interaction.response.send_message(await self.bot._(interaction.guild_id, "errors.unknown"), ephemeral=True)
                raise RuntimeError(f"No topic found on guild {interaction.guild_id} with ID {topic_id}")
            if topic["category"] is None:
                cmd = await self.bot.get_command_mention("tickets portal set-category")
                await interaction.response.send_message(
                    await self.bot._(interaction.guild_id, "tickets.missing-category-config", set_category=cmd),
                    ephemeral=True
                )
                return
            if topic["hint"]:
                hint_view = SendHintText(interaction.user.id,
                    await self.bot._(interaction.guild_id, "tickets.hint-useless"),
                    await self.bot._(interaction.guild_id, "tickets.hint-useful"),
                    await self.bot._(interaction.guild_id, "tickets.cancelled"))
                embed = discord.Embed(color=discord.Color.green(), title=topic["topic"], description=topic["hint"])
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
            if (cooldown := self.cooldowns.get(interaction.user)) and time.time() - cooldown < 120:
                await interaction.response.send_message(
                    await self.bot._(interaction.guild_id, "tickets.too-quick"),
                    ephemeral=True
                )
                return
            modal_title = await self.bot._(interaction.guild_id, "tickets.title-modal.title")
            modal_label = await self.bot._(interaction.guild_id, "tickets.title-modal.label")
            modal_placeholder = await self.bot._(interaction.guild_id, "tickets.title-modal.placeholder")
            await interaction.response.send_modal(
                AskTitleModal(interaction.guild.id, topic, modal_title, modal_label, modal_placeholder, self.create_ticket)
            )
        except Exception as err: # pylint: disable=broad-except
            self.bot.dispatch("error", err, f"when creating a ticket in guild {interaction.guild_id}")

    async def db_get_topics(self, guild_id: int) -> list[DBTopicRow]:
        "Fetch the topics associated to a guild"
        query = "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `topic` IS NOT NULL AND `beta` = %s"
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta)) as db_query:
            return db_query

    async def db_get_defaults(self, guild_id: int) -> DBTopicRow | None:
        "Get the default values for a guild"
        query = "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `topic` IS NULL AND `beta` = %s"
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta), fetchone=True) as db_query:
            return db_query or None

    async def db_get_topic_with_defaults(self, guild_id: int, topic_id: int) -> DBTopicRow:
        "Fetch a topicfrom its guild and ID"
        if topic_id == -1:
            query = "SELECT * FROM `tickets` WHERE `guild_id` = %s AND `topic` IS NULL AND `beta` = %s"
            args = (guild_id, self.bot.beta)
        else:
            query = """
            SELECT t.id, t.guild_id, t.topic,
                COALESCE(t.topic_emoji, t2.topic_emoji) as topic_emoji,
                COALESCE(t.prompt, t2.prompt) as `prompt`,
                COALESCE(t.role, t2.role) as role,
                COALESCE(t.hint, t2.hint) as `hint`,
                COALESCE(t.category, t2.category) as `category`,
                COALESCE(t.name_format, t2.name_format) as name_format,
                t.beta
            FROM tickets t
            LEFT JOIN tickets t2 ON t2.guild_id = t.guild_id AND t2.beta = t.beta AND t2.topic is NULL
            WHERE t.id = %s AND t.guild_id = %s AND t.beta = %s"""
            args = (topic_id, guild_id, self.bot.beta)
        async with self.bot.db_main.read(query, args, fetchone=True) as db_query:
            return db_query or None

    async def db_get_guild_default_id(self, guild_id: int) -> int | None:
        "Return the row ID corresponding to the default guild setup, or None"
        query = "SELECT id FROM `tickets` WHERE guild_id = %s AND topic IS NULL AND beta = %s"
        async with self.bot.db_main.read(query, (guild_id, self.bot.beta), fetchone=True) as db_query:
            if not db_query:
                return None
            return db_query["id"]

    async def db_set_guild_default_id(self, guild_id: int) -> int:
        "Create a new row for default guild setup"
        # INSERT only if not exists
        query = "INSERT INTO `tickets` (guild_id, beta) SELECT %(g)s, %(b)s WHERE (SELECT 1 as `exists` FROM `tickets` WHERE guild_id = %(g)s AND topic IS NULL AND beta = %(b)s) IS NULL"
        async with self.bot.db_main.write(query, {'g': guild_id, 'b': self.bot.beta}) as db_query:
            return db_query

    async def db_add_topic(self, guild_id: int, name: str, emoji: str | None) -> bool:
        "Add a topic to a guild"
        query = "INSERT INTO `tickets` (`guild_id`, `topic`, `topic_emoji`, `beta`) VALUES (%s, %s, %s, %s)"
        try:
            async with self.bot.db_main.write(query, (guild_id, name, emoji, self.bot.beta), returnrowcount=True) as db_query:
                return db_query > 0
        except IntegrityError:
            return False

    async def db_delete_topics(self, guild_id: int, topic_ids: list[int]) -> int:
        "Delete multiple topics from a guild"
        topic_ids = ", ".join(map(str, topic_ids))
        query = f"DELETE FROM `tickets` WHERE `guild_id` = %s AND id IN ({topic_ids}) AND `beta` = %s"
        async with self.bot.db_main.write(query, (guild_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query

    async def db_topic_exists(self, guild_id: int, topic_id: int):
        "Check if a topic exists for a guild"
        query = "SELECT 1 FROM `tickets` WHERE `guild_id` = %s AND `id` = %s AND `topic` IS NOT NULL AND `beta` = %s"
        async with self.bot.db_main.read(query, (guild_id, topic_id, self.bot.beta)) as db_query:
            return len(db_query) > 0

    async def db_edit_topic_name(self, guild_id: int, topic_id: int, name: str) -> bool:
        "Edit a topic name"
        query = "UPDATE `tickets` SET `topic` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (name, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_emoji(self, guild_id: int, topic_id: int, emoji: str | None) -> bool:
        "Edit a topic emoji"
        query = "UPDATE `tickets` SET `topic_emoji` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (emoji, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_hint(self, guild_id: int, topic_id: int, hint: str | None) -> bool:
        "Edit a topic emoji"
        query = "UPDATE `tickets` SET `hint` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (hint, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_role(self, guild_id: int, topic_id: int, role_id: int | None) -> bool:
        "Edit a topic emoji"
        query = "UPDATE tickets SET role = %s WHERE guild_id = %s AND id = %s AND beta = %s"
        async with self.bot.db_main.write(query, (role_id, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_category(self, guild_id: int, topic_id: int, category: int | None) -> bool:
        "Edit a topic category or channel in which tickets will be created"
        query = "UPDATE `tickets` SET `category` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (category, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_topic_format(self, guild_id: int, topic_id: int, name_format: str | None) -> bool:
        "Edit a topic channel/thread name format"
        query = "UPDATE `tickets` SET `name_format` = %s WHERE `guild_id` = %s AND `id` = %s AND `beta` = %s"
        async with self.bot.db_main.write(query, (name_format, guild_id, topic_id, self.bot.beta), returnrowcount=True) as db_query:
            return db_query > 0

    async def db_edit_prompt(self, guild_id: int, message: str):
        "Edit the prompt displayed for a guild"
        query = "UPDATE tickets SET prompt = %s WHERE guild_id = %s AND topic is NULL AND beta = %s"
        async with self.bot.db_main.write(query, (message, guild_id, self.bot.beta)) as _:
            pass

    async def ask_user_topic(self, interaction: discord.Interaction, multiple = False, message: str | None = None):
        "Ask a user which topic they want to edit"
        placeholder = await self.bot._(interaction, "tickets.selection-placeholder")
        topics = await self.db_get_topics(interaction.guild_id)
        if not topics:
            await interaction.followup.send(await self.bot._(interaction, "tickets.topic.no-server-topic"), ephemeral=True)
            return None
        view = AskTopicSelect(interaction.user.id, topics, placeholder, max_values=25 if multiple else 1)
        msg = await interaction.followup.send(message or await self.bot._(interaction, "tickets.choose-topic-edition"), view=view)
        await view.wait()
        if view.topics is None:
            # timeout
            await view.disable(msg)
            return None
        try:
            if multiple:
                return [int(topic) for topic in view.topics]
            return int(view.topics[0])
        except (ValueError, IndexError):
            return None

    async def create_channel_first_message(self, interaction: discord.Interaction, topic: dict, ticket_name: str):
        "Create the introduction message at the beginning of the ticket"
        title = await self.bot._(interaction.guild_id, "tickets.ticket-introduction.title")
        desc = await self.bot._(interaction.guild_id, "tickets.ticket-introduction.description",
                                user=interaction.user.mention,
                                ticket_name=ticket_name, topic_name=topic["topic"]
                                )
        return discord.Embed(title=title, description=desc, color=discord.Color.green())

    async def get_ticket_channel_perms(self, channel: discord.TextChannel, topic: dict, user: discord.Member):
        "Setup the required permissions for a channel ticket"
        permissions = {}
        # set for everyone
        permissions[channel.guild.default_role] = discord.PermissionOverwrite(read_messages=False)
        # set for the user and the bot
        permissions[user] = discord.PermissionOverwrite(send_messages=True, read_messages=True)
        permissions[channel.guild.me] = discord.PermissionOverwrite(send_messages=True, read_messages=True)
        # set for the staff
        if (role_id := topic.get("role")) and (role := channel.guild.get_role(role_id)):
            permissions[role] = discord.PermissionOverwrite(
                send_messages=True,
                read_messages=True,
                manage_messages=True,
                manage_channels=True
            )
        return permissions

    async def setup_ticket_thread(self, thread: discord.Thread, topic: dict, user: discord.Member):
        "Add the required members to a Discord thread ticket"
        mentions = [thread.guild.me.mention, user.mention]
        if (role_id := topic.get("role")) and (role := thread.guild.get_role(role_id)):
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
        await interaction.edit_original_response(content=msg)

    async def get_channel_name(self, name_format: str | None, interaction: discord.Interaction,
                               topic: dict, ticket_name: str) -> str:
        "Build the correct channel name for a new ticket"
        channel_name = name_format or self.default_name_format
        if isinstance(topic["topic_emoji"], str) and ':' in topic["topic_emoji"]:
            emoji: str = topic["topic_emoji"].split(':')[0]
        else:
            emoji = topic["topic_emoji"]
        if topic["topic"] is None:
            topic_name = await self.bot._(interaction.guild_id, "tickets.other")
        else:
            topic_name = topic["topic"]
        return channel_name.format_map(self.bot.SafeDict({
            "username": interaction.user.global_name or interaction.user.name,
            "userid": interaction.user.id,
            "topic": topic_name,
            "topic_emoji": emoji,
            "ticket_name": ticket_name
        }))[:100]

    async def create_ticket(self, interaction: discord.Interaction, topic: dict, ticket_name: str):
        "Create the ticket once the user has provided every required info"
        # update cooldown
        self.cooldowns[interaction.user] = time.time()
        category = interaction.guild.get_channel(topic["category"])
        if category is None:
            self.bot.dispatch("server_warning", ServerWarningType.TICKET_CREATION_UNKNOWN_TARGET,
                interaction.guild,
                channel_id=topic["category"],
                topic_name=topic["topic"]
            )
            raise RuntimeError(f"No category configured for guild {interaction.guild_id} and topic {topic['topic']}")
        sent_error = False
        channel_name = await self.get_channel_name(topic["name_format"], interaction, topic, ticket_name)
        if isinstance(category, discord.CategoryChannel):
            perms = await self.get_ticket_channel_perms(category, topic, interaction.user)
            try:
                channel = await category.create_text_channel(channel_name, overwrites=perms)
            except discord.Forbidden:
                self.log.info("Missing perms to create channel in %s", category.id)
                await interaction.edit_original_response(
                    content=await self.bot._(interaction.guild_id, "tickets.missing-perms-creation.channel",
                                             category=category.name)
                )
                self.bot.dispatch("server_warning", ServerWarningType.TICKET_CREATION_FAILED,
                    interaction.guild,
                    channel=category,
                    topic_name=topic["topic"]
                )
                return
        elif isinstance(category, discord.TextChannel):
            try:
                if (
                    "PRIVATE_THREADS" in interaction.guild.features
                        and category.permissions_for(interaction.guild.me).create_private_threads):
                    channel_type = discord.ChannelType.private_thread
                else:
                    channel_type = discord.ChannelType.public_thread
                channel = await category.create_thread(name=channel_name, type=channel_type)
            except discord.Forbidden:
                self.log.info("Missing perms to create thread in %s", category.id)
                await interaction.edit_original_response(
                    content=await self.bot._(interaction.guild_id, "tickets.missing-perms-creation.thread",
                                             channel=category.mention)
                )
                self.bot.dispatch("server_warning", ServerWarningType.TICKET_CREATION_FAILED,
                    interaction.guild,
                    channel=category,
                    topic_name=topic["topic"]
                )
                return
            await self.setup_ticket_thread(channel, topic, interaction.user)
        else:
            self.log.error("Unknown channel or category type: %s", type(category))
            return
        self.log.debug("Created channel/thread %s", channel.id)
        topic["topic"] = topic["topic"] or await self.bot._(interaction.guild_id, "tickets.other")
        txt: str = await self.bot._(interaction.guild_id, "tickets.ticket-created", channel=channel.mention, topic=topic["topic"])
        if sent_error:
            await interaction.followup.send(txt, ephemeral=True)
        else:
            await interaction.edit_original_response(content=txt)
        msg = await channel.send(embed=await self.create_channel_first_message(interaction, topic, ticket_name))
        if channel.permissions_for(channel.guild.me).manage_messages:
            await msg.pin()
        self.bot.dispatch("ticket_creation", TicketCreationEvent(topic, ticket_name, interaction, channel))

    async def topic_id_autocompletion(self, interaction: discord.Interaction, current: str, allow_other: bool=True):
        "Autocompletion to select a topic in an app command"
        current = current.lower()
        topics = await self.db_get_topics(interaction.guild_id)
        if allow_other:
            topics.append({
                "id": -1,
                "topic": (await self.bot._(interaction.guild_id, "tickets.other")).capitalize(),
                "topic_emoji": None
            })
        filtered = sorted([
            (not topic["topic"].lower().startswith(current), topic["topic"], topic["id"])
            for topic in topics
            if current in topic["topic"].lower()
        ])
        return [
            app_commands.Choice(name=name, value=topic_id)
            for _, name, topic_id in filtered
        ]

    async def send_error_message(self, interaction: discord.Interaction):
        "Send a generic error message when something went wrong"
        about = await self.bot.get_command_mention("about")
        send = interaction.followup.send if interaction.response.is_done() else interaction.response.send_message
        await send(await self.bot._(interaction, "errors.unknown", about=about))

    tickets_main = app_commands.Group(
        name="tickets",
        description="Manage your tickets system",
        default_permissions=discord.Permissions(manage_channels=True),
        guild_only=True,
    )

    tickets_portal = app_commands.Group(
        name="portal",
        description="Handle how your members are able to open tickets",
        parent=tickets_main,
    )

    @tickets_portal.command()
    @app_commands.checks.cooldown(2, 30)
    async def summon(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
        """Ask the bot to send a message allowing people to open tickets

        ..Doc tickets.html#as-staff-send-the-prompt-message"""
        destination_channel = channel or interaction.channel
        if not destination_channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                await self.bot._(interaction, "tickets.missing-perms-send", channel=destination_channel.mention),
                ephemeral=True
            )
            return
        await interaction.response.defer(ephemeral=True)
        topics = await self.db_get_topics(interaction.guild_id)
        other = {
            "id": -1,
            "topic": (await self.bot._(interaction, "tickets.other")).capitalize(),
            "topic_emoji": None
        }
        defaults = await self.db_get_defaults(interaction.guild_id)
        prompt = defaults["prompt"] if defaults else await self.bot._(interaction, "tickets.default-topic-prompt")
        await destination_channel.send(prompt, view=SelectView(interaction.guild_id, topics + [other]))
        await interaction.followup.send(await self.bot._(interaction, "misc.done!"))

    @tickets_portal.command(name="set-hint")
    @app_commands.describe(message="The hint to display for this topic - set 'none' for no hint")
    @app_commands.checks.cooldown(3, 30)
    async def portal_set_hint(self, interaction: discord.Interaction, *, message: HintTextArgument):
        """Set a default hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "none" for no hint message at all

        ..Example tickets set-hint Make sure to directly state your question when creating your tickets - Please do not use this form for raid-related issues

        ..Doc tickets.html#default-hint"""
        if message.lower() == "none":
            message = None
        await interaction.response.defer()
        row_id = await self.db_get_guild_default_id(interaction.guild_id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(interaction.guild_id)
        if await self.db_edit_topic_hint(interaction.guild_id, row_id, message):
            await interaction.followup.send(await self.bot._(interaction, "tickets.hint-edited.default"))
        else:
            await self.send_error_message(interaction)

    @tickets_portal.command(name="set-role")
    @app_commands.describe(role="The role allowed to see tickets from this topic - do not set to allow anyone")
    @app_commands.checks.cooldown(3, 30)
    async def portal_set_role(self, interaction: discord.Interaction, role: discord.Role | None):
        """Edit a default staff role
        Anyone with this role will be able to read newly created tickets
        Type "None" to set admins only

        ..Example tickets set-role Moderators

        ..Doc tickets.html#default-staff-role"""
        await interaction.response.defer()
        row_id = await self.db_get_guild_default_id(interaction.guild_id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(interaction.guild_id)
        await self.db_edit_topic_role(interaction.guild_id, row_id, role.id if role else None)
        key = "tickets.role-edited.default-reset" if role is None else "tickets.role-edited.default"
        await interaction.followup.send(await self.bot._(interaction, key))

    @tickets_portal.command(name="set-text")
    @app_commands.checks.cooldown(3, 30)
    async def portal_set_text(self, interaction: discord.Interaction, *, message: str):
        """Set a message to be displayed above the ticket topic selection

        ..Example tickets set-text Select a category below to start opening your ticket!

        ..Doc tickets.html#presentation-message"""
        await interaction.response.defer()
        row_id = await self.db_get_guild_default_id(interaction.guild_id)
        if row_id is None:
            await self.db_set_guild_default_id(interaction.guild_id)
        await self.db_edit_prompt(interaction.guild_id, message)
        await interaction.followup.send(await self.bot._(interaction, "tickets.text-edited"))

    @tickets_portal.command(name="set-category")
    @app_commands.checks.cooldown(3, 30)
    async def portal_set_category(self, interaction: discord.Interaction,
                                  category_or_channel: discord.CategoryChannel | discord.TextChannel):
        """Set the category or the channel in which tickets will be created

        If you select a channel, tickets will use the Discord threads system but allowed roles may not be applied

        ..Example tickets set-category \"Private channels\"

        ..Example tickets set-channels #tickets

        ..Doc tickets.html#tickets-category-channel"""
        await interaction.response.defer()
        row_id = await self.db_get_guild_default_id(interaction.guild_id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(interaction.guild_id)
        await self.db_edit_topic_category(interaction.guild_id, row_id, category_or_channel.id)
        embed = None
        if isinstance(category_or_channel, discord.CategoryChannel):
            message = await self.bot._(interaction,
                                       "tickets.category-edited.default-category",
                                       category=category_or_channel.name)
            if not category_or_channel.permissions_for(interaction.guild.me).manage_channels:
                embed = discord.Embed(description=await self.bot._(interaction,
                                                                   "tickets.category-edited.category-permission-warning"),
                                      colour=discord.Color.orange())
        else:
            message = await self.bot._(interaction,
                                       "tickets.category-edited.default-channel",
                                       channel=category_or_channel.mention)
            if (
                "PRIVATE_THREADS" not in interaction.guild.features
                or not category_or_channel.permissions_for(interaction.guild.me).create_private_threads
            ):
                embed = discord.Embed(description=await self.bot._(interaction,
                                                                   "tickets.category-edited.channel-privacy-warning"),
                                      colour=discord.Color.orange())
        await interaction.followup.send(message, embed=embed)

    @tickets_portal.command(name="set-format")
    @app_commands.describe(name_format="The channel format for this topic - set 'none' to use the default one")
    @app_commands.checks.cooldown(3, 30)
    async def portal_set_format(self, interaction: discord.Interaction, name_format: ChannelNameFormatArgument):
        """Set the format used to generate the channel/thread name
        You can use the following placeholders: username, userid, topic, topic_emoji, ticket_name
        Use "none" to reset the format to the default one
        Spaces and non-ascii characters will be removed or replaced by dashes

        ..Example tickets set-format {username}-tickets

        ..Example tickets set-format {username}-{topic}"""
        await interaction.response.defer()
        row_id = await self.db_get_guild_default_id(interaction.guild_id)
        if row_id is None:
            row_id = await self.db_set_guild_default_id(interaction.guild_id)
        if name_format.lower() == "none":
            name_format = None
        await self.db_edit_topic_format(interaction.guild_id, row_id, name_format)
        await interaction.followup.send(await self.bot._(interaction, "tickets.format.edited.default"))

    tickets_topics = app_commands.Group(
        name="topic",
        description="Handle the different ticket topics your members can select",
        parent=tickets_main,
    )

    @tickets_topics.command(name="add")
    @app_commands.checks.cooldown(3, 45)
    async def topic_add(self, interaction: discord.Interaction, name: TopicNameArgument,
                        emote: PartialorUnicodeEmojiArgument | None = None):
        """Create a new ticket topic
        A topic name is limited to 100 characters
        Only Discord emojis are accepted for now

        ..Example tickets topic add :diamonds: Economy issues

        ..Example tickets topic add Request a magician

        ..Doc tickets.html#create-a-new-topic"""
        await interaction.response.defer()
        if is_named_other(name, await self.bot._(interaction, "tickets.other")):
            await interaction.followup.send(
                await self.bot._(interaction, "tickets.topic.other-already-exists"), ephemeral=True
            )
            return
        if len(await self.db_get_topics(interaction.guild_id)) >= MAX_TOPICS_PER_GUILD:
            await interaction.followup.send(
                await self.bot._(interaction, "tickets.topic.too-many", max=MAX_TOPICS_PER_GUILD), ephemeral=True
            )
            return
        if isinstance(emote, discord.PartialEmoji):
            emote = f"{emote.name}:{emote.id}"
        if await self.db_add_topic(interaction.guild_id, name, emote):
            await interaction.followup.send(await self.bot._(interaction, "tickets.topic.created", name=name))
        else:
            await interaction.followup.send(await self.bot._(interaction, "tickets.topic.cant-create"), ephemeral=True)

    @tickets_topics.command(name="remove")
    @app_commands.checks.cooldown(3, 45)
    async def topic_remove(self, interaction: discord.Interaction, topic_id: int | None = None):
        """Permanently delete a topic by its name

        ..Doc tickets.html#delete-a-topic"""
        await interaction.response.defer()
        if not topic_id or not await self.db_topic_exists(interaction.guild_id, topic_id):
            topic_id = await self.ask_user_topic(
                interaction, True,
                await self.bot._(interaction, "tickets.choose-topics-deletion")
            )
            if topic_id is None:
                # timeout
                return
        topic_ids: list[int] | None = [topic_id]
        if topic_ids is None:
            # timeout
            return
        if len(topic_ids) == 1:
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_ids[0])
            topic_name = topic["topic"] if topic else ""
        else:
            topic_name = ""
        counter = await self.db_delete_topics(interaction.guild_id, topic_ids)
        if counter > 0:
            await interaction.followup.send(
                await self.bot._(interaction, "tickets.topic.deleted", count=counter, name=topic_name)
            )
        else:
            await self.send_error_message(interaction)

    @topic_remove.autocomplete("topic_id")
    async def topic_remove_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.topic_id_autocompletion(interaction, current, allow_other=False)

    @tickets_topics.command(name="set-name")
    @app_commands.checks.cooldown(3, 30)
    async def topic_edit_name(self, interaction: discord.Interaction, topic_id: int | None, *, name: TopicNameArgument):
        """Edit a topic name
        A topic name is limited to 100 characters

        ..Example tickets topic set-name 5 "Minecraft issues"

        ..Doc tickets.html#edit-a-topic-name"""
        await interaction.response.defer()
        if not topic_id or not await self.db_topic_exists(interaction.guild_id, topic_id):
            topic_id = await self.ask_user_topic(interaction)
            if topic_id is None:
                # timeout
                return
        if await self.db_edit_topic_name(interaction.guild_id, topic_id, name):
            await interaction.followup.send(await self.bot._(interaction, "tickets.name-edited", name=name))
        else:
            await interaction.followup.send(await self.bot._(interaction, "tickets.nothing-to-edit"), ephemeral=True)

    @tickets_topics.command(name="set-emote")
    @app_commands.checks.cooldown(3, 30)
    async def topic_set_emote(self, interaction: discord.Interaction, topic_id: int | None,
                              emote: PartialorUnicodeEmojiArgument | None = None):
        """Edit a topic emoji
        Type "None" to set no emoji for this topic

        ..Example tickets topic set-emote :money_with_wings:

        ..Doc tickets.html#edit-a-topic-emoji"""
        await interaction.response.defer()
        if not topic_id or not await self.db_topic_exists(interaction.guild_id, topic_id):
            topic_id = await self.ask_user_topic(interaction)
            if topic_id is None:
                # timeout
                return
        elif isinstance(emote, discord.PartialEmoji):
            emote = f"{emote.name}:{emote.id}"
        if await self.db_edit_topic_emoji(interaction.guild_id, topic_id, emote):
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            await interaction.followup.send(await self.bot._(interaction, "tickets.emote-edited", topic=topic["topic"]))
        else:
            await interaction.followup.send(await self.bot._(interaction, "tickets.nothing-to-edit"), ephemeral=True)

    @topic_set_emote.autocomplete("topic_id")
    async def topic_set_emote_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.topic_id_autocompletion(interaction, current, allow_other=False)

    @tickets_topics.command(name="set-hint")
    @app_commands.describe(message="The hint to display for this topic - set 'none' to use the default one")
    @app_commands.checks.cooldown(3, 30)
    async def topic_set_hint(self, interaction: discord.Interaction, topic_id: int | None=None, *, message: HintTextArgument):
        """Edit a topic hint message
        The message will be displayed when a user tries to open a ticket, before user confirmation
        Type "None" to set the text to the default one (`tickets portal set-hint`)

        ..Example tickets topic set-hint When trying to join our Minecraft server, make sure to correctly enter our IP!
If that still doesn't work, please create your ticket

        ..Doc tickets.html#topic-specific-hint"""
        await interaction.response.defer()
        if not topic_id or not await self.db_topic_exists(interaction.guild_id, topic_id):
            topic_id = await self.ask_user_topic(interaction)
            if topic_id is None:
                # timeout
                return
        if message.lower() == "none":
            message = None
        await self.db_edit_topic_hint(interaction.guild_id, topic_id, message)
        topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
        await interaction.followup.send(await self.bot._(interaction, "tickets.hint-edited.topic", topic=topic["topic"]))

    @topic_set_hint.autocomplete("topic_id")
    async def topic_set_hint_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.topic_id_autocompletion(interaction, current)

    @tickets_topics.command(name="set-role")
    @app_commands.describe(role="The role allowed to see tickets from this topic - do not set to use the default one")
    @app_commands.checks.cooldown(3, 30)
    async def topic_set_role(self, interaction: discord.Interaction, topic_id: int | None=None, role: discord.Role | None=None):
        """Edit a topic staff role
        Anyone with this role will be able to read newly created tickets with this topic
        Type "None" to set the role to the default one (`tickets portal set-role`)

        ..Example tickets topic set-role @Staff

        ..Example tickets topic set-role 347 \"Minecraft moderators\"

        ..Doc tickets.html#topic-specific-staff-role"""
        await interaction.response.defer()
        if not topic_id or not await self.db_topic_exists(interaction.guild_id, topic_id):
            topic_id = await self.ask_user_topic(interaction)
            if topic_id is None:
                # timeout
                return
        if await self.db_edit_topic_role(interaction.guild_id, topic_id, role.id if role else None):
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            key = "tickets.role-edited.topic-reset" if role is None else "tickets.role-edited.topic"
            await interaction.followup.send(await self.bot._(interaction, key, topic=topic["topic"]))
        else:
            await interaction.followup.send(await self.bot._(interaction, "tickets.nothing-to-edit"), ephemeral=True)

    @topic_set_role.autocomplete("topic_id")
    async def topic_set_role_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.topic_id_autocompletion(interaction, current)

    @tickets_topics.command(name="set-format")
    @app_commands.describe(name_format="The channel format for this topic - set 'none' to use the default one")
    @app_commands.checks.cooldown(3, 30)
    async def topic_set_format(self, interaction: discord.Interaction, topic_id: int | None,
                               name_format: ChannelNameFormatArgument):
        """Set the format used to generate the channel/thread name
        You can use the following placeholders: username, userid, topic, topic_emoji, ticket_name
        Use "none" to reset the format to the default one
        Spaces and non-ascii characters will be removed or replaced by dashes

        ..Example tickets set-format {username}-special

        ..Example tickets set-format 347 {username}-{topic}"""
        if not topic_id or not await self.db_topic_exists(interaction.guild_id, topic_id):
            topic_id = await self.ask_user_topic(interaction)
            if topic_id is None:
                # timeout
                return
        if name_format.lower() == "none":
            name_format = None
        if await self.db_edit_topic_format(interaction.guild_id, topic_id, name_format):
            topic = await self.db_get_topic_with_defaults(interaction.guild_id, topic_id)
            await interaction.followup.send(await self.bot._(interaction, "tickets.format.edited.topic", topic=topic["topic"]))
        else:
            await interaction.followup.send(await self.bot._(interaction, "tickets.nothing-to-edit"), ephemeral=True)

    @topic_set_format.autocomplete("topic_id")
    async def topic_set_format_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.topic_id_autocompletion(interaction, current)

    @tickets_topics.command(name="list")
    @app_commands.checks.cooldown(3, 20)
    async def topic_list(self, interaction: discord.Interaction):
        "List every ticket topic used in your server"
        await interaction.response.defer()
        topics_repr: list[str] = []
        none_emoji: str = self.bot.emojis_manager.customs["nothing"]
        topics = await self.db_get_topics(interaction.guild_id)
        # make sure an "other" topic exists
        if await self.db_get_guild_default_id(interaction.guild_id) is None:
            await self.db_set_guild_default_id(interaction.guild_id)
        topics.append(await self.db_get_defaults(interaction.guild_id))
        for topic in topics:
            name = topic["topic"] or await self.bot._(interaction, "tickets.other")
            if topic["topic_emoji"]:
                emoji = discord.PartialEmoji.from_str(topic["topic_emoji"])
                topics_repr.append(f"{emoji} {name}")
            else:
                topics_repr.append(f"{none_emoji} {name}")
            if topic["role"]:
                topics_repr[-1] += f" - <@&{topic['role']}>"
        title = await self.bot._(interaction, "tickets.topic.list")
        embed = discord.Embed(title=title, description="\n".join(topics_repr), color=discord.Color.blue())
        await interaction.followup.send(embed=embed)


    @tickets_main.command(name="review-config")
    @app_commands.describe(topic_id="The topic to review - set none to review them all")
    @app_commands.checks.cooldown(3, 40)
    async def portal_review_config(self, interaction: discord.Interaction, *, topic_id: int | None=None):
        """Review the configuration of a topic or all topics

        ..Example tickets review-config

        ..Example tickets review-config Economy issues

        ..Doc tickets.html#review-the-configuration"""
        await interaction.response.defer()
        if topic_id is None:
            await self.review_all(interaction)
        else:
            await self.review_topic(interaction, topic_id)


    @portal_review_config.autocomplete("topic_id")
    async def portal_review_autocomplete(self, interaction: discord.Interaction, current: str):
        return await self.topic_id_autocompletion(interaction, current, allow_other=False)

    async def review_all(self, interaction: discord.Interaction):
        "Send a global recap of a guild settings"
        topics = await self.db_get_topics(interaction.guild_id)
        if defaults := await self.db_get_defaults(interaction.guild_id):
            topics.append(defaults)
        emb = discord.Embed(
            title=await self.bot._(interaction, "tickets.review.embed.title-global"),
            description=await self.bot._(interaction, "tickets.review.embed.desc-global"),
            color=discord.Color.blue(),
        )
        inline = len(topics) <= 6

        language = await self.bot._(interaction, "_used_locale")
        async def field_value(key: str, value: str):
            key_tr = await self.bot._(interaction, f"tickets.review.{key}")
            if "fr" in language:
                return f"**{key_tr}** : {value}"
            return f"**{key_tr}**: {value}"

        for topic in topics:
            text: list[str] = []
            name = topic["topic"] if topic["topic"] else await self.bot._(interaction, "tickets.review.default")
            if topic["topic_emoji"]:
                name = str(discord.PartialEmoji.from_str(topic["topic_emoji"])) + " " + name
            if topic["role"]:
                if role := interaction.guild.get_role(topic["role"]):
                    text.append(await field_value("role", role.mention))
                else:
                    text.append(
                        await field_value("role", await self.bot._(interaction, "tickets.review.deleted-role", id=topic["role"]))
                    )
            if topic["category"]:
                if channel := interaction.guild.get_channel(topic["category"]):
                    if isinstance(channel, discord.CategoryChannel):
                        text.append(await field_value("category", channel.name))
                    else:
                        text.append(await field_value("channel", channel.mention))
                else:
                    text.append(
                        await field_value(
                            "category",
                            await self.bot._(interaction, "tickets.review.deleted-category", id=topic["category"])
                        )
                    )
            if topic["name_format"]:
                name_format = topic["name_format"] if len(topic["name_format"]) < 100 else topic["name_format"][:100] + "…"
                text.append(await field_value("format", name_format))
            if topic["hint"]:
                hint = topic["hint"] if len(topic["hint"]) < 100 else topic["hint"][:100] + "…"
                text.append(await field_value("hint", hint))
            if topic["prompt"]:
                prompt = topic["prompt"] if len(topic["prompt"]) < 200 else topic["prompt"][:200] + "…"
                text.append(await field_value("prompt", prompt))
            if len(text) == 0:
                text.append(await self.bot._(interaction, "tickets.review.topic-no-config"))
            emb.add_field(
                name=name,
                value="\n".join(text),
                inline=inline
            )
        if len(emb.fields) == 0:
            emb.description += "\n\n**" + await self.bot._(interaction, "tickets.review.no-config") + "**"
        await interaction.followup.send(embed=emb)

    async def review_topic(self, interaction: discord.Interaction, topic_id: int):
        "Send a global recap of a guild settings"
        topics = await self.db_get_topics(interaction.guild_id)
        topics_filtered = [t for t in topics if t["id"] == topic_id]
        if len(topics_filtered) == 0:
            await interaction.followup.send(await self.bot._(interaction, "tickets.review.topic-not-found"), ephemeral=True)
            return
        topic = topics_filtered[0]
        emb = discord.Embed(
            title=await self.bot._(interaction, "tickets.review.embed.title-topic", topic=topic["topic"]),
            description=await self.bot._(interaction, "tickets.review.embed.desc-topic", topic=topic["topic"]),
            color=discord.Color.blue(),
        )
        if topic["topic_emoji"]:
            emb.add_field(
                name=await self.bot._(interaction, "tickets.review.emoji"),
                value=discord.PartialEmoji.from_str(topic["topic_emoji"]),
            )
        if topic["role"]:
            if role := interaction.guild.get_role(topic["role"]):
                emb.add_field(
                    name=await self.bot._(interaction, "tickets.review.role"),
                    value=role.mention,
                )
            else:
                emb.add_field(
                    name=await self.bot._(interaction, "tickets.review.role"),
                    value=await self.bot._(interaction, "tickets.review.deleted-role", id=topic["role"]),
                )
        if topic["category"]:
            if channel := interaction.guild.get_channel(topic["category"]):
                if isinstance(channel, discord.CategoryChannel):
                    emb.add_field(
                        name=await self.bot._(interaction, "tickets.review.category"),
                        value=channel.name,
                    )
                else:
                    emb.add_field(
                        name=await self.bot._(interaction, "tickets.review.category"),
                        value=channel.mention,
                    )
            else:
                emb.add_field(
                    name=await self.bot._(interaction, "tickets.review.category"),
                    value=await self.bot._(interaction, "tickets.review.deleted-category", id=topic["category"]),
                )
        if topic["name_format"]:
            emb.add_field(
                name=await self.bot._(interaction, "tickets.review.format"),
                value=topic["name_format"],
                inline=len(topic["name_format"]) < 60
            )
        if topic["hint"]:
            emb.add_field(
                name=await self.bot._(interaction, "tickets.review.hint"),
                value=topic["hint"] if len(topic["hint"]) < 1000 else topic["hint"][:1000] + "…",
                inline=len(topic["hint"]) < 60
            )
        if len(emb.fields) == 0:
            emb.description += "\n\n**" + await self.bot._(interaction, "tickets.review.topic-no-config") + "**"
        await interaction.followup.send(embed=emb)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
