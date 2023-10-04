from typing import Union

import discord
import i18n

from libs.bot_classes import Axobot, MyContext
from libs.serverconfig.options_list import options
from libs.translator import AxobotTranslator

SourceType = Union[None, int, discord.Guild, discord.TextChannel, discord.Thread,
                   discord.Member, discord.User, discord.DMChannel, discord.Interaction,
                   discord.PartialMessageable, MyContext]


class Languages(discord.ext.commands.Cog):
    "Translations module"

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = "languages"
        self.languages: tuple[str] = options["language"]["values"]
        i18n.set('filename_format', '{locale}.{format}')
        i18n.set('file_format', 'json')
        i18n.set('fallback', None)
        i18n.set('on_missing_translation', 'error')
        i18n.set('skip_locale_root_data', True)
        i18n.unload_everything()
        i18n.load_path.clear()
        i18n.load_path.append('./lang')

    async def cog_load(self):
        await self.bot.tree.set_translator(AxobotTranslator(self.bot))

    async def cog_unload(self):
        await self.bot.tree.set_translator(None)

    @property
    def default_language(self) -> str:
        return options["language"]["default"]

    async def tr(self, source: SourceType, string_id: str, **kwargs):
        """Renvoie le texte en fonction de la langue"""
        if isinstance(source, discord.PartialMessageable):
            if source.guild_id:
                source = source.guild_id
            else:
                source = await self.bot.fetch_channel(source.id)
        if isinstance(source, discord.Guild):
            # get ID from guild
            source = source.id
        elif isinstance(source, (discord.abc.GuildChannel, discord.Thread)):
            # get ID from text channel
            source = source.guild.id
        elif isinstance(source, discord.Interaction):
            # get ID from guild
            if source.guild:
                source = source.guild.id
            elif source.user:
                source = source.user
            else:
                source = None
        elif isinstance(source, MyContext):
            # get ID from guild
            if source.guild:
                source = source.guild.id
            else:
                source = source.author

        if isinstance(source, (discord.Member, discord.User)):
            # get lang from user
            used_langs = await self.bot.get_cog('Utilities').get_languages(source, limit=1)
            lang_opt = used_langs[0][0] if len(used_langs) > 0 else self.default_language
        elif not self.bot.database_online or source is None:
            # get default lang
            lang_opt = self.default_language
        elif isinstance(source, discord.DMChannel):
            # get lang from DM channel
            recipient = await self.bot.get_recipient(source)
            if recipient is None:
                lang_opt = self.default_language
            else:
                used_langs = await self.bot.get_cog('Utilities').get_languages(recipient, limit=1)
                lang_opt = used_langs[0][0] if len(used_langs) > 0 else self.default_language
        elif isinstance(source, int):
            # get lang from server ID
            lang_opt: str = await self.bot.get_config(source, "language")
            if lang_opt is None:
                lang_opt = self.default_language
        else:
            raise TypeError(f"Unknown type for translation source: {type(source)}")
        if lang_opt not in self.languages:
            # if lang not known: fallback to default
            lang_opt = self.default_language
        return await self._recursive_get_translation(lang_opt, string_id, **kwargs)

    async def _recursive_get_translation(self, locale: str, string_id: str, **kwargs):
        "Find the translation in the given locale, or fallback to another locale"
        try:
            return await self.get_translation(locale, string_id, **kwargs)
        except KeyError:
            await self.msg_not_found(string_id, locale)
            if locale == "en":
                return string_id
            fallback = "fr" if locale == "fr2" else "en"
            return await self._recursive_get_translation(fallback, string_id, **kwargs)

    async def get_translation(self, locale: str, string_id: str, **kwargs) -> Union[str, list]:
        "Get a translation from the i18n files directly"
        if string_id == '_used_locale':
            return locale
        return i18n.t(string_id, locale=locale, **kwargs)

    async def msg_not_found(self, string_id: str, lang: str):
        "Signal to the dev that a translation is missing"
        try:
            err = f"Message `{string_id}` not found in JSON files (language {lang})"
            await self.bot.get_cog('Errors').senf_err_msg(err)
            self.bot.log.warning(err)
        except Exception: # pylint: disable=broad-except
            self.bot.log.error("Something went wrong while reporting a translation as missing", exc_info=True)


async def setup(bot):
    await bot.add_cog(Languages(bot))
