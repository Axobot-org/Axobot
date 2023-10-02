from discord.ext import commands

class VerboseBadArgumentError(commands.BadArgument):
    "Base class for when a BadArgument should be handled by the command_error event"

class InvalidDurationError(VerboseBadArgumentError):
    "Raised when the duration argument is invalid"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid duration: {argument}")

class InvalidBotOrGuildInviteError(VerboseBadArgumentError):
    "Raised when the bot or guild invite is invalid"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid bot or guild invite: {argument}")

class InvalidUrlError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid url"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid url: {argument}")

class InvalidUnicodeEmojiError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid unicode emoji"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid unicode emoji: {argument}")

class InvalidISBNError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid ISBN"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid ISBN: {argument}")

class InvalidCardStyleError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid XP card style"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid card style: {argument}")

class InvalidServerLogError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid server log"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid server log: {argument}")

class InvalidRawPermissionError(VerboseBadArgumentError):
    "Raised when the user argument is not a valid raw permission"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid raw permission: {argument}")

class InvalidPermissionTargetError(VerboseBadArgumentError):
    "Raised when the 'target' argument of the permissions command is not valid"
    def __init__(self, argument: str):
        self.argument = argument
        super().__init__(f"Invalid member, role or permission: {argument}")
