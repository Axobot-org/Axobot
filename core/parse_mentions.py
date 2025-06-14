from collections.abc import Sequence
import re

import discord


def parse_allowed_mentions(text: str, *, base: discord.AllowedMentions | None = None) -> discord.AllowedMentions:
    "Parse a list of mentions based of the mentions contained in a string"
    allowed_mentions = base or discord.AllowedMentions.none()
    if not text:
        return allowed_mentions
    # Parse everyone and here mentions from the text
    if "@everyone" in text or "@here" in text:
        allowed_mentions.everyone = True
    # Parse role mentions from the text
    if allowed_mentions.roles is not True:
        for role_match in re.finditer(r"<@&(\d+)>", text):
            role_id = role_match.group(1)
            if not allowed_mentions.roles:
                allowed_mentions.roles = []
            allowed_mentions.roles.append(discord.Object(id=int(role_id)))
    # Parse user mentions from text
    if allowed_mentions.users is not True:
        for user_match in re.finditer(r"<@!?(\d+)>", text):
            user_id = user_match.group(1)
            if not allowed_mentions.users:
                allowed_mentions.users = []
            allowed_mentions.users.append(discord.Object(id=int(user_id)))
    # Remove duplicates from roles and users
    if isinstance(allowed_mentions.roles, Sequence):
        allowed_mentions.roles = list(set(allowed_mentions.roles))
    if isinstance(allowed_mentions.users, Sequence):
        allowed_mentions.users = list(set(allowed_mentions.users))
    return allowed_mentions
