import asyncio
from copy import copy, deepcopy
import json
import os
import typing

import discord
from discord.ext import commands
from flatten_json import flatten
from libs.classes import MyContext, Zbot
from fcts.checks import is_translator

FlatennedTranslations = dict[str, typing.Optional[str]]
ModuleDict = dict[str, FlatennedTranslations]
LanguageId = typing.Literal['fr', 'en', 'lolcat', 'fr2', 'fi', 'de', 'tr', 'es', 'it']
languages: set[str] = LanguageId.__args__
TranslationsDict = dict[LanguageId, ModuleDict]

TodoDict = dict[LanguageId, dict[str, set[str]]]

T = typing.TypeVar('T')
def first(of: typing.Union[list[T], set[T]]) -> T:
    "Return the first element of an iterable, or None if empty"
    for e in of:
        break
    return e

class Translations(commands.Cog):
    """Special cog for those who help with the translation of the bot"""

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = 'translations'
        self._translations: TranslationsDict = {}
        self._projects: TranslationsDict = {}
        self._todo: TodoDict = {}

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
        for module, tr in project.items():
            if module not in result:
                result[module] = deepcopy(tr)
                continue
            for key, value in tr.items():
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
                # TODO: ignore "None" values
                json.dump(translations, file, ensure_ascii=False, indent=4, sort_keys=True)

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
        # if the key was in the todo, remove it
        if self._todo.get(lang, {}).get(module):
            self._todo[lang][module].remove(key)
            # if the module is 100% translated, remove it
            if not self._todo[lang][module]:
                self._todo[lang].pop(module)
                # if the language is 100% translated, remove it
                if not self._todo[lang]:
                    self._todo.pop(lang)

    @commands.group(name='translators', aliases=['tr'])
    @commands.check(is_translator)
    async def translate_main(self, ctx: MyContext):
        "Manage the bot translations"
        if not ctx.invoked_subcommand and ctx.subcommand_passed:
            # it may be a shortcut for !translators translate
            cmd = self.bot.get_command("translators translate")
            await cmd(ctx, ctx.subcommand_passed)
        elif ctx.subcommand_passed is None:
            await self.bot.get_cog('Help').help_command(ctx, ['tr'])

    @translate_main.command(name="translate")
    async def translate_smth(self, ctx: MyContext, lang: typing.Optional[LanguageId] = None):
        """Translate a message of the bot
        Original message is in English
        The text is not immediatly added into the bot and need an update to be in

        Use no argument to get a help message"""
        if lang is None:
            await self.bot.get_cog('Help').help_command(ctx, ['translators'])
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
        await ctx.send(f"How would you translate it in {lang}?\n\n  *Key: {key}*\nType 'pass' to choose another one")
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

    @translate_main.command(name="status")
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
            lang_progress = await self.get_translations_count(language)
            en_progress = await self.get_translations_count('en')
            ratio = lang_progress*100 / en_progress
            txt = f"Translation of {lang}:\n {ratio:.1f}%\n {lang_progress} messages on {en_progress}"
        await ctx.send(txt)

    # @translate_main.command(name='edit')
    # async def edit_tr(self, ctx: MyContext, lang: str, key: str, *, translation: str=None):
    #     """Edit a translation"""
    #     if lang not in self.translations.keys():
    #         return await ctx.send("Invalid language")
    #     if not key in self.translations['en'].keys():
    #         return await ctx.send("Invalid key")
    #     if translation is None:
    #         await ctx.send("```\n"+self.translations['en'][key]+"\n```")
    #         try:
    #             msg = await self.bot.wait_for('message', check=lambda msg: msg.author.id==ctx.author.id and msg.channel.id==ctx.channel.id, timeout=90)
    #         except asyncio.TimeoutError:
    #             return await ctx.send("You were too slow. Try again.")
    #         translation = msg.content
    #     await self.modify_project(lang,key,translation)
    #     await ctx.send(f"New translation:\n :arrow_right: {translation}")

    # @translate_main.command(name="get-file")
    # @commands.check(check_admin)
    # async def fuse_file(self, ctx: MyContext, lang: str):
    #     """Merge the current project file
    #     with the already-translated file"""
    #     if lang not in self.todo.keys():
    #         return await ctx.send("Invalid language")
    #     try:
    #         with open(f'fcts/lang/{lang}.json','r',encoding='utf-8') as old_f:
    #             with open(f'translation/{lang}-project.json','r',encoding='utf-8') as new_f:
    #                 new = {k:v for k,v in json.load(new_f).items() if v is not None}
    #                 new = await self._fuse_file(json.load(old_f),new)
    #     except FileNotFoundError:
    #         return await ctx.send("There is no current project with this language")
    #     with open(f'translation/{lang}.json','w',encoding='utf-8') as f:
    #         json.dump(new,f, ensure_ascii=False, indent=4, sort_keys=True)
    #     await ctx.send('Done!',file=discord.File(f'translation/{lang}.json'))

    # @translate_main.command(name="merge")
    # @commands.check(check_admin)
    # async def merge_files(self, ctx: MyContext, lang: str="en"):
    #     """Merge a file with the english version"""
    #     if not lang in self.project_list:
    #         return await ctx.send("Invalid language")
    #     if len(ctx.message.attachments) == 0:
    #         return await ctx.send("Missing a file")
    #     from io import BytesIO
    #     with open(f'fcts/lang/{lang}.json','r',encoding='utf-8') as old_f:
    #         en_map = self.create_txt_map(json.load(old_f))
    #     io = BytesIO()
    #     await ctx.message.attachments[0].save(io)
    #     data_lang = json.load(io)
    #     en_map = await self._fuse_file(data_lang,en_map)
    #     await ctx.send(file= discord.File(BytesIO(json.dumps(en_map,ensure_ascii=False,indent=4,sort_keys=True).encode('utf-8')),filename=ctx.message.attachments[0].filename))


async def setup(bot):
    await bot.add_cog(Translations(bot))
