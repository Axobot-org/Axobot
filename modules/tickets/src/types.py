from typing import TYPE_CHECKING, TypedDict, TypeGuard

import discord

from core.type_utils import GuildInteraction

if TYPE_CHECKING:
    from discord.types.interactions import \
        SelectMessageComponentInteractionData

    from core.bot_classes.axobot import Axobot

class DBTopicRowWithDefault(TypedDict):
    "Represents a row in the topics table in the database"
    id: int
    guild_id: int
    topic: str | None
    topic_emoji: str | None
    prompt: str | None
    role: int | None
    hint: str | None
    category: int | None
    name_format: str | None
    beta: bool

class DBTopicRow(TypedDict):
    "Represents a row in the topics table in the database"
    id: int
    guild_id: int
    topic: str
    topic_emoji: str | None
    prompt: str | None
    role: int | None
    hint: str | None
    category: int | None
    name_format: str | None
    beta: bool

class TopicAutocompletionData(TypedDict):
    "Represents a simplified view of a topic for autocompletion"
    id: int
    topic: str
    topic_emoji: str | None

class TicketCreationEvent:
    "Represents a ticket being created"
    def __init__(self, topic: DBTopicRowWithDefault, name: str, interaction: GuildInteraction,
                 channel: discord.TextChannel | discord.Thread):
        if topic["topic"] is None:
            raise ValueError("Topic must have a name")
        self.topic = topic
        self.topic_emoji: str | None = topic["topic_emoji"]
        self.topic_name: str = topic["topic"]
        self.name = name
        self.guild = interaction.guild
        self.user = interaction.user
        self.channel = channel

def interaction_is_ticket_creation(interaction: discord.Interaction) -> TypeGuard["TicketCreationInteraction"]:
    "Check if an interaction is a ticket creation interaction"
    if interaction.guild is None or interaction.guild_id is None:
        return False
    if interaction.type != discord.InteractionType.component or interaction.data is None:
        return False
    if interaction.data.get("component_type") != discord.ComponentType.select.value:
        return False
    if not (custom_id := interaction.data.get("custom_id")):
        return False
    custom_id_data = custom_id.split('-')
    if len(custom_id_data) != 3 or custom_id_data[0] != str(interaction.guild_id) or custom_id_data[1] != "tickets":
        return False
    return True


class TicketCreationInteraction(discord.Interaction):
    "A specific type for interactions that are guaranteed to be in a writable channel of a guild."
    client: "Axobot" # pyright: ignore[reportIncompatibleMethodOverride]
    guild: discord.Guild # pyright: ignore[reportIncompatibleMethodOverride]
    guild_id: int # pyright: ignore[reportIncompatibleVariableOverride]
    user: discord.Member # pyright: ignore[reportIncompatibleVariableOverride]
    data: "SelectMessageComponentInteractionData" # pyright: ignore[reportIncompatibleVariableOverride]
