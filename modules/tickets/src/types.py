from typing import TypedDict

import discord


class TicketCreationEvent:
    "Represents a ticket being created"
    def __init__(self, topic: dict, name: str, interaction: discord.Interaction, channel: discord.TextChannel | discord.Thread):
        self.topic = topic
        self.topic_emoji: str | None = topic["topic_emoji"]
        self.topic_name: str = topic["topic"]
        self.name = name
        self.guild = interaction.guild
        self.user = interaction.user
        self.channel = channel


class DBTopicRow(TypedDict):
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
