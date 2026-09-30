class _BaseFlagClass:
    FLAGS: dict[int, str]

    def flags_to_int(self, flags: list[str]) -> int:
        "Convert a list of flags to its integer value"
        result = 0
        for flag, value in self.FLAGS.items():
            if value in flags:
                result |= flag
        return result

    def int_to_flags(self, i: int) -> list[str]:
        "Convert an integer value to its list of flags"
        return [v for k, v in self.FLAGS.items() if i & k == k]

class RankCardsFlag(_BaseFlagClass):
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
        1 << 12: "blurple23",
        1 << 13: "halloween23",
        1 << 14: "christmas23",
        1 << 15: "april24",
        1 << 16: "halloween24",
        1 << 17: "christmas24",
        1 << 18: "april25",
        1 << 19: "christmas25",
        1 << 20: "april26",
    }

class UserFlag(_BaseFlagClass):
    "Flags used for user permissions/roles"
    FLAGS = {
        1 << 0: "support",
        1 << 1: "contributor",
        1 << 2: "premium",
        1 << 3: "partner",
        1 << 4: "translator",
        1 << 5: "cookie"
    }
