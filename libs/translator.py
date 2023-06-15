from typing import TYPE_CHECKING, Optional, Union

from discord import Locale, app_commands
from discord.app_commands import locale_str
from discord.app_commands.translator import TranslationContextLocation

if TYPE_CHECKING:
    from libs.bot_classes import Axobot


LOCALES_MAP = {
    Locale.french: "fr",
    Locale.german: "de",
    Locale.finnish: "fi",
    Locale.british_english: "en",
    Locale.american_english: "en",
    Locale.czech: "cs",
}


IGNORED_COMMANDS = {"admin", "find"}

async def is_ignored_command(cmd: Union[app_commands.Command, app_commands.Group, app_commands.ContextMenu]):
    "Check if the given command should be ignored by the translator"
    if isinstance(cmd, app_commands.ContextMenu):
        root = cmd
    else:
        root = cmd.root_parent or cmd
    return root.name in IGNORED_COMMANDS


class AxobotTranslator(app_commands.Translator):
    "Subclass of discord.app_commands.Translator to add custom app-commands-related translations"

    def __init__(self, bot: "Axobot"):
        self.bot = bot

    async def translate(self, string, locale, context):
        if (lang := LOCALES_MAP.get(locale)) is None:
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
        elif context.location == TranslationContextLocation.group_description:
            if await is_ignored_command(context.data):
                return None
            cmd_name = context.data.qualified_name
            return await self._translate_cmd(lang, f"commands.group_description.{cmd_name}", locale)
        elif context.location == TranslationContextLocation.command_description:
            if await is_ignored_command(context.data):
                return None
            cmd_name = context.data.qualified_name
            return await self._translate_cmd(lang, f"commands.command_short_description.{cmd_name}", locale)
        elif context.location == TranslationContextLocation.choice_name and "default" not in string.extras:
            return
        elif context.location in {
            TranslationContextLocation.parameter_description,
        }:
            return
        else:
            return await self._translate_custom(lang, string, locale)

    async def _translate_cmd(self, lang: str, string: str, locale: Locale) -> Optional[str]:
        try:
            return await self.bot.get_cog("Languages").get_translation(lang, string)
        except KeyError:
            if locale in {Locale.american_english, Locale.french}:
                self.bot.log.warning(f"[translator] Missing translation for '{string}' in {locale} ({lang})")

    async def _translate_custom(self, lang: str, string: locale_str, locale: Locale) -> Optional[str]:
        try:
            return await self.bot.get_cog("Languages").get_translation(lang, string.message)
        except KeyError:
            self.bot.log.warning(f"[translator] Missing translation for '{string.message}' in {locale} ({lang})")
            return string.extras.get("default")
