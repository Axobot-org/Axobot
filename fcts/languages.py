import discord
import json
from utils import Zbot

class Languages(discord.ext.commands.Cog):

    def __init__(self, bot: Zbot):
        self.bot = bot
        self.file = "languages"
        self.languages = ['fr', 'en', 'lolcat', 'fi', 'de', 'fr2']
        self.serv_opts = dict()
        self.translations = {}
        for lang in self.languages:
            with open(f'fcts/lang/{lang}.json','r') as f:
                self.translations[lang] = json.load(f)


    async def tr(self, serverID, moduleID: str, messageID: str, **args):
        """Renvoie le texte en fonction de la langue"""
        if isinstance(serverID,discord.Guild):
            serverID = serverID.id
        elif hasattr(serverID, "guild") and isinstance(serverID.guild, discord.Guild): # guild channels and threads
            serverID = serverID.guild.id
        if str(serverID) in self.serv_opts.keys():
            lang_opt = self.serv_opts[str(serverID)]
            #print("Ex langage:",lang_opt)
            #print(self.serv_opts)
        elif not self.bot.database_online:
            lang_opt = self.bot.get_cog('Servers').default_language
        elif serverID is None:
            lang_opt = self.bot.get_cog('Servers').default_language
        elif isinstance(serverID,discord.DMChannel):
            if serverID.recipient is None:
                # recipient couldn't be loaded
                serverID: discord.DMChannel = await self.bot.fetch_channel(serverID.id)
                if serverID.recipient is None:
                    lang_opt = self.bot.get_cog('Servers').default_language
            if serverID.recipient is not None:
                used_langs = await self.bot.get_cog('Utilities').get_languages(serverID.recipient,limit=1)
                lang_opt = used_langs[0][0]
        else:
            conf_lang = self.bot.get_cog("Servers").conf_lang
            lang_opt = await conf_lang(serverID,"language","scret-desc")
            self.serv_opts[str(serverID)] = lang_opt
            #print("New langage:",lang_opt)
        if lang_opt not in self.languages:
            lang_opt = self.bot.get_cog('Servers').default_language
        return await self._get_translation(lang_opt, moduleID, messageID, **args)

    async def _get_translation(self, lang:str, moduleID:str, messageID:str, **args):
        result = None
        if lang == 'de':
            try:
                result = self.translations['de'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"de")
                lang = 'en'
        if lang == 'fi':
            try:
                result = self.translations['fi'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"fi")
                lang = 'en'
        if lang == 'lolcat':
            try:
                result = self.translations['lolcat'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"lolcat")
                lang = 'en'
        if lang == 'en':
            try:
                result = self.translations['en'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"en")
                lang = 'fr'
        if lang == 'fr2':
            try:
                result = self.translations['fr2'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"fr2")
                lang = 'fr'
        if lang == 'fr':
            try:
                result = self.translations['fr'][moduleID][messageID]
            except KeyError:
                await self.msg_not_found(moduleID,messageID,"fr")
                result = ""
            except Exception as e:
                await self.bot.get_cog('Errors').on_error(e,None)
                result = ""
        if isinstance(result,str):
            try:
                return result.format_map(self.bot.SafeDict(args))
            except ValueError:
                return result
        else:
            return result

    async def msg_not_found(self, moduleID: str, messageID: str, lang: str):
        try:
            await self.bot.get_cog('Errors').senf_err_msg("Le message {}.{} n'a pas été trouvé dans la base de donnée! (langue {})".format(moduleID,messageID,lang))
        except:
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

    async def change_cache(self,serverID,new_lang):
        #print("change_cache:",new_lang)
        if new_lang in self.languages:
            #print("changement effectué")
            self.serv_opts[str(serverID)] = new_lang


def setup(bot):
    bot.add_cog(Languages(bot))
