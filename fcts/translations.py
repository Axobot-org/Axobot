import asyncio
from io import BytesIO
import json
import os
import shutil
import time
import typing
from copy import deepcopy

import discord
from discord.ext import tasks, commands
from flatten_json import flatten, unflatten_list
from libs.bot_classes import MyContext, Axobot

from libs.checks.checks import is_translator, is_bot_admin

FlatennedTranslations = dict[str, typing.Optional[str]]
ModuleDict = dict[str, FlatennedTranslations]
LanguageId = typing.Literal['fr', 'en', 'lolcat', 'fr2', 'fi', 'de', 'tr', 'es', 'it', 'hi']
languages: set[str] = LanguageId.__args__
TranslationsDict = dict[LanguageId, ModuleDict]

TodoDict = dict[LanguageId, dict[str, set[str]]]

T = typing.TypeVar('T')
def first(of: typing.Union[list[T], set[T]]) -> T:
    "Return the first element of an iterable, or None if empty"
    item = None
    for item in of:
        break
    return item

class Translations(commands.Cog):
    """Special cog for those who help with the translation of the bot"""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'translations'
        self._translations: TranslationsDict = {}
        self._projects: TranslationsDict = {}
        self._todo: TodoDict = {}
        self.edited_languages: set[LanguageId] = set()

    async def cog_load(self):
        if self.bot.internal_loop_enabled:
            # pylint: disable=no-member
            self.save_projects_loop.start()
            self.backup_loop.start()

    async def cog_unload(self):
        "Stop loop when cog is unloaded"
        # pylint: disable=no-member
        if self.save_projects_loop.is_running():
            self.save_projects_loop.cancel()
        if self.backup_loop.is_running():
            self.backup_loop.cancel()

    @tasks.loop(hours=12)
    async def backup_loop(self):
        "Make a backup of every project every 12 hours"
        start = time.time()
        try:
            os.remove('translation-backup.tar')
        except FileNotFoundError:
            pass
        try:
            shutil.make_archive('translation-backup', 'tar', 'translation')
        except FileNotFoundError:
            await self.bot.get_cog('Errors').senf_err_msg("Translators backup: Unable to find backup folder")
            return
        txt = f'**Translations files backup** completed in {time.time()-start:.3f}s'
        self.bot.log.info(txt.replace('**', ''))
        emb = discord.Embed(
            description=txt,
            color=10197915, timestamp=self.bot.utcnow()
        )
        emb.set_author(name=self.bot.user, icon_url=self.bot.user.display_avatar)
        await self.bot.send_embed(emb, url="loop")

    async def load_translations(self):
        """Load current translations from their JSON files"""
        for root, _, files in os.walk("lang"):
            for file in files:
                if file.endswith(".json"):
                    lang = file.split('.', maxsplit=1)[0]
                    module = root.split('/')[-1]
                    if lang not in self._translations:
                        self._translations[lang] = {}
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as file:
                        translations = flatten(json.load(file)[lang], separator='.')
                        self._translations[lang][module] = translations

    async def load_project(self):
        "Load current edited translations from their JSON files"
        for root, _, files in os.walk("translation"):
            for file in files:
                if file.endswith("-project.json"):
                    lang = file.split('-', maxsplit=1)[0]
                    if lang not in self._projects:
                        self._projects[lang] = {}
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as file:
                        for module, translations in json.load(file).items():
                            self._projects[lang][module] = flatten(translations, separator='.')

    async def load_todo(self, lang: typing.Optional[str] = None) -> TodoDict:
        "Get the missing translations keys"
        translations = await self.get_original_translations()
        projects = await self.get_projects()
        if lang and self._todo:
            self._todo[lang] = {}
            targets = {lang}
        else:
            self._todo: TodoDict = {lang: {} for lang in languages}
            targets = languages
        for language in targets:
            for module, en_tr in translations['en'].items():
                for key in en_tr.keys():
                    if key in translations.get(language, {}).get(module, {}):
                        continue
                    if key in projects.get(language, {}).get(module, {}):
                        continue
                    if module not in self._todo[language]:
                        self._todo[language][module] = {key}
                    else:
                        self._todo[language][module].add(key)

    async def get_original_translations(self) -> TranslationsDict:
        "Returns the instanciated translations dictionary"
        if not self._translations:
            await self.load_translations()
        return self._translations

    async def get_projects(self) -> TranslationsDict:
        "Returns the instanciated projects dictionary"
        if not self._projects:
            await self.load_project()
        return self._projects

    async def get_todo(self) -> TodoDict:
        "Returns the instanciated todo dictionary"
        if not self._todo:
            await self.load_todo()
        return self._todo

    async def merge_project_translations(self, language: LanguageId):
        "Merge original translations and project translations for a language"
        translations = (await self.get_original_translations()).get(language, {})
        project = (await self.get_projects()).get(language, {})
        result = deepcopy(translations)
        for module, translation in project.items():
            if module not in result:
                result[module] = deepcopy(translation)
                continue
            for key, value in translation.items():
                result[module][key] = value
        return result

    async def get_translations_count(self, language: LanguageId) -> int:
        "Returns the number of translations for a given language, all modules and projects included"
        translations = await self.merge_project_translations(language)
        count = 0
        for module_tr in translations.values():
            count += len([tr for tr in module_tr.values() if tr])
        return count

    async def save_project(self, lang: LanguageId):
        "Save a translation project into its JSON file"
        if translations := (await self.get_projects()).get(lang):
            with open('translation/'+lang+'-project.json', 'w', encoding='utf-8') as file:
                translations = {module: {key: value for key, value in translation.items() if value}
                                for module, translation in translations.items()}
                json.dump(translations, file, ensure_ascii=False, indent=4, sort_keys=True)
            return True
        return False

    async def get_translation(self, lang: LanguageId, module: str, key: str):
        "Get a translation from either the project or the original translation"
        if lang not in languages:
            raise ValueError("Invalid language")
        projects = await self.get_projects()
        if value := projects.get(lang, {}).get(module, {}).get(key):
            return value
        translations = await self.get_original_translations()
        return translations.get(lang, {}).get(module, {}).get(key)

    async def get_todo_item(self, lang: LanguageId):
        "Get a tuple (module, key) to translate into a given language"
        if lang not in languages:
            raise ValueError("Invalid language")
        todo = (await self.get_todo())[lang]
        for module, translations in todo.items():
            if translations:
                return (module, first(translations))

    async def modify_project(self, lang: LanguageId, module: str, key: str, value: typing.Optional[str]):
        "Edit a translation for the given language, module and key, and edit the todo map"
        if lang not in languages:
            raise ValueError("Invalid language")
        if lang not in self._projects:
            self._projects[lang] = {}
        if module not in self._projects[lang]:
            self._projects[lang][module] = {}
        self._projects[lang][module][key] = value
        self.edited_languages.add(lang)
        # if the key was in the todo, remove it
        if self._todo.get(lang, {}).get(module):
            try:
                self._todo[lang][module].remove(key)
            except KeyError:
                pass
            # if the module is 100% translated, remove it
            if not self._todo[lang][module]:
                self._todo[lang].pop(module)
                # if the language is 100% translated, remove it
                if not self._todo[lang]:
                    self._todo.pop(lang)
        self.bot.dispatch("translation_added", lang)

    @tasks.loop(seconds=30)
    async def save_projects_loop(self):
        "Save every edited project into their JSON files every 30s"
        to_edit = set(self.edited_languages)
        for language in to_edit:
            await self.save_project(language)
            self.edited_languages.remove(language)
        if to_edit:
            self.bot.log.info("[translations] %s edited projects saved", len(to_edit))

    @commands.group(name='translators', aliases=['tr'])
    @commands.check(is_translator)
    async def translate_main(self, ctx: MyContext):
        "Manage the bot translations"
        if not ctx.invoked_subcommand and ctx.subcommand_passed:
            # it may be a shortcut for !translators translate
            cmd = self.bot.get_command("translators translate")
            await cmd(ctx, ctx.subcommand_passed)
        elif ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @translate_main.command(name="translate")
    async def translate_smth(self, ctx: MyContext, lang: typing.Optional[LanguageId] = None):
        """Translate a message of the bot
        Original message is in English
        The text is not immediatly added into the bot and need an update to be in

        Use no argument to get a help message"""
        if lang is None:
            await ctx.send_help(ctx.command)
            return
        if lang not in languages or lang == 'en':
            return await ctx.send("Invalid language")
        todo = await self.get_todo()
        if not todo.get(lang):
            return await ctx.send("This language is already 100% translated :tada:")
        await self.ask_a_translation(ctx, lang)

    async def ask_a_translation(self, ctx: MyContext, lang: LanguageId, isloop: bool = False):
        "Ask a user for a translation in a given language"
        module, key = await self.get_todo_item(lang)
        value = (await self.get_original_translations())['en'][module][key]
        await ctx.send(f"```\n{value}\n```")
        await ctx.send(f"How would you translate it in {lang}?\n\n  *Key: {module}.{key}*\nType 'pass' to choose another one")
        try:
            def check(msg: discord.Message):
                is_author = msg.author.id == ctx.author.id
                is_admin_stopping = (msg.author.id in {
                                     279568324260528128, 281404141841022976, 552273019020771358
                                     } and msg.content.lower() == 'stop' and isloop)
                is_channel = msg.channel.id == ctx.channel.id
                is_not_command = not msg.content.startswith(ctx.prefix)
                return (is_author or is_admin_stopping) and is_channel and is_not_command
            msg: discord.Message = await self.bot.wait_for('message', check=check, timeout=90)
        except asyncio.TimeoutError:
            await ctx.send("You were too slow. Try again.")
            return 'timeout'
        if msg.content.lower() == 'pass':
            await self.modify_project(lang, module, key, None)
            await ctx.send("This message will be ignored until the next reload of this command")
        elif msg.content.lower() == 'stop':
            if isloop:
                await ctx.send("Ok, let's stop here. Thanks for your help!")
            else:
                await ctx.send("You're not in a loop, you know? Anyway, I cancelled that")
            return 'break'
        else:
            await self.modify_project(lang, module, key, msg.content)
            await ctx.send(f"New translation:\n :arrow_right: {msg.content}")
        return 'pass'

    @translate_main.command(name='loop')
    async def translate_smth_loop(self, ctx: MyContext, lang: LanguageId):
        """Same that !translate, but in a loop so you don't need to type the command
Use `stop` to stop translating

..Example tr-loop fi"""
        if lang not in languages or lang == 'en':
            return await ctx.send("Invalid language")
        if not (await self.get_todo()).get(lang):
            return await ctx.send("This language is already 100% translated :tada:")
        timeouts_count = 0
        state = await self.ask_a_translation(ctx, lang, isloop=True)
        while state != 'break':
            if not (await self.get_todo()).get(lang):
                await ctx.send("This language is already 100% translated :tada:")
                break
            state = await self.ask_a_translation(ctx, lang, isloop=True)
            if state == 'timeout':
                timeouts_count += 1
            else:
                timeouts_count = 0
            if timeouts_count > 4:
                await ctx.send("Ok I stop here. Call me when you're back")
                break

    @translate_main.command(name='reload-todo')
    async def reload_todo(self, ctx: MyContext, lang: typing.Optional[LanguageId] = None):
        """Reload the to-do list of a language translation (or all languages if none specified)"""
        if lang is not None and (lang not in languages or lang == 'en'):
            return await ctx.send("Invalid language")
        await self.load_todo(lang=lang)
        if lang:
            await ctx.send(f"ToDo list for the language {lang} has been reloaded")
        else:
            await ctx.send("The whole ToDo list for every language has been reloaded!")

    @translate_main.command(name="status", aliases=["stats"])
    async def status(self, ctx: MyContext, lang: typing.Optional[LanguageId]=None):
        """Get the status of a translation project"""
        if lang is None:
            txt = "General status:"
            en_progress = await self.get_translations_count('en')
            results: list[tuple[str, float, int]] = []
            for language in languages:
                if language == 'en':
                    continue
                lang_progress = await self.get_translations_count(language)
                ratio = lang_progress*100 / en_progress
                results.append((language, ratio, lang_progress))
            for language, ratio, lang_progress in sorted(results, key=lambda x: x[1], reverse=True):
                txt += f"\n- {language}: {ratio:.1f}% ({lang_progress}/{en_progress})"
        elif lang not in languages or lang == 'en':
            return await ctx.send("Invalid language")
        else:
            lang_progress = await self.get_translations_count(lang)
            en_progress = await self.get_translations_count('en')
            ratio = lang_progress*100 / en_progress
            txt = f"Translation of {lang}:\n {ratio:.1f}%\n {lang_progress} messages on {en_progress}"
        await ctx.send(txt)

    @translate_main.command(name='edit')
    async def edit_tr(self, ctx: MyContext, lang: str, key: str, *, translation: typing.Optional[str]=None):
        """Edit a translation"""
        if lang not in languages or lang == 'en':
            return await ctx.send("Invalid language")
        if '.' not in key:
            return await ctx.send("Invalid key")
        module, key = key.split('.', maxsplit=1)
        try:
            value = (await self.get_original_translations())['en'][module][key]
        except KeyError:
            return await ctx.send("Invalid key")
        if translation is None:
            await ctx.send(f"```\n{value}\n```")
            try:
                def check(msg: discord.Message):
                    return msg.author.id == ctx.author.id and msg.channel.id == ctx.channel.id
                msg: discord.Message = await self.bot.wait_for('message',
                                                               check=check,
                                                               timeout=45)
            except asyncio.TimeoutError:
                return await ctx.send("You were too slow. Try again.")
            translation = msg.content
        await self.modify_project(lang, module, key, translation)
        await ctx.send(f"New translation:\n :arrow_right: {translation}")

    @translate_main.command(name="get-file")
    @commands.check(is_bot_admin)
    async def fuse_file(self, ctx: MyContext, lang: LanguageId, module: str):
        """Merge the current project file
        with the already-translated file"""
        if lang not in languages or lang == 'en':
            await ctx.send("Invalid language")
            return
        english = (await self.get_original_translations())["en"]
        try:
            project = (await self.get_projects())[lang]
        except KeyError:
            await ctx.send("This language has no translation project")
            return
        if module not in project:
            await ctx.send(f"Invalid module.\nExpected modules are: {', '.join(sorted(project.keys()))}")
            return
        project = project[module]
        original = deepcopy((await self.get_original_translations())[lang]).get(module, {})
        english_module = english[module]
        # Filter old translations (which are not in englisg anymore)
        merged_flattened = {key: translation for key, translation in (original | project).items() if key in english_module}
        # Unflatten to get the JSON maps structure
        merged = unflatten_list(merged_flattened, separator='.')
        # add language identifier
        merged = {lang: merged}
        # Save into a virtual file
        filename = f'translation/{lang}-{module}.json'
        data = json.dumps(merged, ensure_ascii=False, indent=4, sort_keys=True)
        file = discord.File(BytesIO(data.encode()), filename=filename)
        # Send and boom
        await ctx.send('Done!', file=file)

async def setup(bot):
    await bot.add_cog(Translations(bot))
