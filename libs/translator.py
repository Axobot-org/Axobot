from typing import TYPE_CHECKING

from discord import Locale, app_commands

if TYPE_CHECKING:
    from libs.bot_classes import Axobot

class AxobotTranslator(app_commands.Translator):

    def __init__(self, bot: "Axobot"):
        self.bot = bot

    async def translate(self, string, locale, context):
        if locale == Locale.french:
            lang = "fr"
        elif locale == Locale.german:
            lang = "en"
        elif locale == Locale.finnish:
            lang = "fi"
        else:
            lang = "en"
        result = await self.bot.get_cog("Languages")._get_translation(lang, string.message)
        if result == string.message and "." in result:
            return string.extras.get("default")
        return result
