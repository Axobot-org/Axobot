from discord.ext import commands

class VerboseCommandError(commands.CommandError):
    "Base class for when a CommandError should be handled by the command_error event"

class NotDuringEventError(VerboseCommandError, commands.CheckFailure):
    "Raised when an event command is called but there is no active event."
