import discord
import i18n
from libs.classes import Zbot


class Languages(discord.ext.commands.Cog):

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "languages"
        self.languages = ('fr', 'en', 'lolcat', 'fi', 'de', 'fr2')
        self.serv_opts: dict[int, str] = dict()
        i18n.set('filename_format', '{locale}.{format}')
        i18n.set('file_format', 'json')
        i18n.translations.container.clear()
        i18n.load_path.clear()
        i18n.load_path.append('./fcts/lang2')

    async def tr(self, source, string_id: str, **args):
        """Renvoie le texte en fonction de la langue"""
        if isinstance(source, discord.Guild):
            # get ID from guild
            source = source.id
        elif isinstance(source, (discord.TextChannel, discord.Thread)):
            # get ID from text channel
            source = source.guild.id

        if isinstance(source, (discord.Member, discord.User)):
            # get lang from user
            used_langs = await self.bot.get_cog('Utilities').get_languages(source, limit=1)
            lang_opt = used_langs[0][0]
        elif source in self.serv_opts:
            # get lang from cache
            lang_opt = self.serv_opts[source]
        elif not self.bot.database_online or source is None:
            # get default lang
            lang_opt = self.bot.get_cog('Servers').default_language
        elif isinstance(source, discord.DMChannel):
            # get lang from DM channel
            recipient = await self.bot.get_recipient(source)
            if recipient is None:
                lang_opt = self.bot.get_cog('Servers').default_language
            else:
                used_langs = await self.bot.get_cog('Utilities').get_languages(recipient, limit=1)
                lang_opt = used_langs[0][0]
        else:
            # get lang from server ID
            if lang_id := await self.bot.get_config(source, "language"):
                lang_opt = self.languages[lang_id]
                self.serv_opts[source] = lang_opt
            else:
                lang_opt = self.bot.get_cog('Servers').default_language
        if lang_opt not in self.languages:
            # if lang not known: fallback to default
            lang_opt = self.bot.get_cog('Servers').default_language
        return await self._get_translation(lang_opt, string_id, **args)

    async def _get_translation(self, locale: str, string_id: str, **args):
        if string_id == '_used_locale':
            return locale
        translation = i18n.t(string_id, locale=locale, **args)
        if translation == string_id:
            await self.msg_not_found(string_id, locale)
        return translation

    async def msg_not_found(self, string_id: str, lang: str):
        "Signal to the dev that a translation is missing"
        try:
            await self.bot.get_cog('Errors').senf_err_msg(
                "Le message {} n'a pas été trouvé dans la base de donnée! (langue {})".format(string_id, lang))
        except: # pylint: disable=bare-except
            pass

    async def check_tr(self, channel: discord.TextChannel, lang: str, origin: str="fr"):
        """Check translations from a language to another"""
        if self.bot.zombie_mode:
            return
        liste = list()
        if lang not in self.languages:
            await channel.send("La langue `{}` n'est pas disponible".format(lang))
            return
        count = 0
        for k,v in dict(self.translations[origin]).items():
            if not k.startswith("__"):
                if k not in self.translations[lang].keys():
                    await channel.send("Le module {} n'existe pas en `{}`".format(k,lang))
                    count += len(v.keys())
                    continue
                for i in v.keys():
                    if i not in self.translations[lang][k].keys():
                        liste.append("module "+k+" - "+i)
                        count += 1
        if count == 0:
            await channel.send(("Tout les messages ont correctement été traduits en `{}` !" if origin=="fr" else "Tout les messages ont correctement été traduits en `{}` depuis la langue `{}` !").format(lang,origin))
        else:
            if len("\n- ".join(liste)) > 1900:
                temp = f"{count} messages non traduits en `{lang}` :" if origin=="fr" else f"{count} messages non traduits en `{lang}` depuis la langue `{origin}` :"
                for i in liste:
                    if len(temp+i)>2000:
                        await channel.send(temp)
                        temp = ""
                    temp += "\n"+i
                await channel.send(temp)
            elif len(liste) > 0:
                await channel.send(("{0} messages non traduits en `{1}` :\n- {2}" if origin=="fr" else "{0} messages non traduits en `{1}` depuis la langue `{o}` :\n- {2}").format(count,lang,"\n- ".join(liste),o=origin))
            else:
                await channel.send(">> {} messages non traduits en `{}`".format(count,lang))

    async def change_cache(self, server_id: int, new_lang: str):
        #print("change_cache:",new_lang)
        if new_lang in self.languages:
            #print("changement effectué")
            self.serv_opts[server_id] = new_lang


def setup(bot):
    bot.add_cog(Languages(bot))
