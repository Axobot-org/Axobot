from discord.ext import commands

class VerboseBadArgumentError(commands.BadArgument):
    "Base class for when a BadArgument should be handled by the command_error event"
