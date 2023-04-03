from enum import Enum
from typing import Optional

import discord


class RankCardsFlag:
    "Flags used for unlocked rank cards"
    FLAGS = {
        1 << 0: "rainbow",
        1 << 1: "blurple19",
        1 << 2: "blurple20",
        1 << 3: "christmas19",
        1 << 4: "christmas20",
        1 << 5: "halloween20",
        1 << 6: "blurple21",
        1 << 7: "halloween21",
        1 << 8: "april22",
        1 << 9: "blurple22",
        1 << 10: "halloween22",
        1 << 11: "christmas22",
    }

    def flags_to_int(self, flags: list) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def int_to_flags(self, i: int) -> list:
        "Convert an integer value to its list of flags"
        return [v for k, v in self.FLAGS.items() if i & k == k]

class UserFlag:
    "Flags used for user permissions/roles"
    FLAGS = {
        1 << 0: "support",
        1 << 1: "contributor",
        1 << 2: "premium",
        1 << 3: "partner",
        1 << 4: "translator",
        1 << 5: "cookie"
    }

    def flags_to_int(self, flags: list) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def int_to_flags(self, i: int) -> list:
        "Convert an integer value to its list of flags"
        return [v for k, v in self.FLAGS.items() if i & k == k]

class ServerWarningType(Enum):
    "Type of emitted server warning, mainly used for logs"

    # channel, is_join
    WELCOME_MISSING_TXT_PERMISSIONS = 1
    # channel, feed_id
    RSS_MISSING_TXT_PERMISSION = 2
    # channel, feed_id
    RSS_MISSING_EMBED_PERMISSION = 3
    # channel_id, feed_id
    RSS_UNKNOWN_CHANNEL = 4
    # channel_id, feed_id
    RSS_DISABLED_FEED = 5
    # channel_id, topic_name
    TICKET_CREATION_UNKNOWN_TARGET = 6
    # channel, topic_name
    TICKET_CREATION_FAILED = 7
    # channel, topic_name
    TICKET_INIT_FAILED = 8

class UsernameChangeRecord:
    "Record of a username change, mainly used for logs"

    def __init__(self, before: Optional[str], after: Optional[str], is_in_guild: bool, user: Optional[discord.User]=None):
        self.user = user
        self.before = before
        self.after = after
        self.is_in_guild = is_in_guild
