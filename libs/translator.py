from typing import TYPE_CHECKING

from discord import Locale, app_commands
from discord.app_commands.translator import TranslationContextLocation

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
        elif locale in {Locale.british_english, Locale.american_english}:
            lang = "en"
        elif context.location == TranslationContextLocation.choice_name:
            lang = "en"
        else:
            return None
        try:
            result = await self.bot.get_cog("Languages").get_translation(lang, string.message)
        except KeyError:
            self.bot.log.warning(f"[translator] Missing translation for '{string.message}' in {locale} ({lang})")
            return string.extras.get("default")
        return result
