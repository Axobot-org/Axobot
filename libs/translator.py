from typing import TYPE_CHECKING, Optional, Union

from discord import Locale, app_commands
from discord.app_commands import locale_str
from discord.app_commands.translator import TranslationContextLocation

if TYPE_CHECKING:
    from libs.bot_classes import Axobot

IGNORED_COMMANDS = {"admin", "find"}

async def is_ignored_command(cmd: Union[app_commands.Command, app_commands.Group, app_commands.ContextMenu]):
    if isinstance(cmd, app_commands.ContextMenu):
        root = cmd
    else:
        root = cmd.root_parent or cmd
    return root.name in IGNORED_COMMANDS


class AxobotTranslator(app_commands.Translator):

    def __init__(self, bot: "Axobot"):
        self.bot = bot

    async def get_lang_from_locale(self, locale: Locale):
        if locale == Locale.french:
            return "fr"
        if locale == Locale.german:
            return "en"
        if locale == Locale.finnish:
            return "fi"
        if locale in {Locale.british_english, Locale.american_english}:
            return "en"
        # elif context.location == TranslationContextLocation.choice_name:
            # lang = "en"
        return None

    async def translate(self, string, locale, context):
        if (lang := await self.get_lang_from_locale(locale)) is None:
            return
        if context.location == TranslationContextLocation.group_name:
            if await is_ignored_command(context.data):
                return None
            cmd_name = context.data.qualified_name
            return await self._translate_cmd(lang, f"commands.group_name.{cmd_name}", locale)
        elif context.location == TranslationContextLocation.command_name:
            if await is_ignored_command(context.data):
                return None
            cmd_name = context.data.qualified_name
            return await self._translate_cmd(lang, f"commands.command_name.{cmd_name}", locale)
        elif context.location == TranslationContextLocation.parameter_name:
            if await is_ignored_command(context.data.command):
                return None
            cmd_name = context.data.command.qualified_name
            return await self._translate_cmd(lang, f"commands.param_name.{cmd_name}.{string.message}", locale)
        elif context.location in {
            TranslationContextLocation.command_description,
            TranslationContextLocation.group_description,
            TranslationContextLocation.parameter_description,
            TranslationContextLocation.choice_name,
        }:
            return
        else:
            return await self._translate_custom(lang, string, locale)

    async def _translate_cmd(self, lang: str, string: str, locale: Locale) -> Optional[str]:
        try:
            return await self.bot.get_cog("Languages").get_translation(lang, string)
        except KeyError:
            if locale == Locale.american_english:
                self.bot.log.warning(f"[translator] Missing translation for '{string}' in {locale} ({lang})")

    async def _translate_custom(self, lang: str, string: locale_str, locale: Locale) -> Optional[str]:
        try:
            return await self.bot.get_cog("Languages").get_translation(lang, string.message)
        except KeyError:
            self.bot.log.warning(f"[translator] Missing translation for '{string.message}' in {locale} ({lang})")
            return string.extras.get("default")
