from enum import Enum
from typing import Optional, Union

import discord


class RankCardsFlag:
    "Flags used for unlocked rank cards"
    FLAGS = {
        1 << 0: "rainbow",
        1 << 1: "blurple_19",
        1 << 2: "blurple_20",
        1 << 3: "christmas_19",
        1 << 4: "christmas_20",
        1 << 5: "halloween_20",
        1 << 6: "blurple_21",
        1 << 7: "halloween_21",
        1 << 8: "april_22",
        1 << 9: "blurple_22"
    }

    def flagsToInt(self, flags: list) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def intToFlags(self, i: int) -> list:
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

    def flagsToInt(self, flags: list) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def intToFlags(self, i: int) -> list:
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

class UsernameChangeRecord:
    def __init__(self, before: Optional[str], after: Optional[str], user: Union[discord.Member, discord.User]):
        self.user = user
        self.before = before
        self.after = after
        self.is_guild = isinstance(user, discord.Member)
