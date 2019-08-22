#!/usr/bin/env python
#coding=utf-8

from importlib import reload as m_reload
from fcts.lang import fr, lolcat
import discord, json
m_reload(fr)
m_reload(lolcat)
fr = {x: getattr(fr,x) for x in dir(fr) if not x.startswith('_')}
lolcat = {x: getattr(lolcat,x) for x in dir(lolcat) if not x.startswith('_')}

en = None
fi = None


class LangCog(discord.ext.commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = "language"
        self.languages = ['fr','en','lolcat','fi']
        self.serv_opts = dict()
        self.translations = {'fr':fr,
            'lolcat':lolcat}
        with open('fcts/lang/en.json','r') as f:
            self.translations['en'] = json.load(f)
        with open('fcts/lang/fi.json','r') as f:
            self.translations['fi'] = json.load(f)


    async def tr(self,serverID,moduleID,messageID,**args):
        """Renvoie le texte en fonction de la langue"""
        if type(serverID) == discord.Guild:
            serverID = serverID.id
        elif isinstance(serverID,discord.TextChannel):
            serverID = serverID.guild.id
        if str(serverID) in self.serv_opts.keys():
            lang_opt = self.serv_opts[str(serverID)]
            #print("Ex langage:",lang_opt)
            #print(self.serv_opts)
        elif not self.bot.database_online:
            lang_opt = self.bot.cogs['ServerCog'].default_language
        elif isinstance(serverID,(discord.DMChannel,type(None))):
            used_langs = await self.bot.cogs['UtilitiesCog'].get_languages(serverID.recipient,limit=1)
            lang_opt = used_langs[0][0]
        else:
            conf_lang = self.bot.cogs["ServerCog"].conf_lang
            lang_opt = await conf_lang(serverID,"language","scret-desc")
            self.serv_opts[str(serverID)] = lang_opt
            #print("New langage:",lang_opt)
        if lang_opt not in self.languages:
            lang_opt = self.bot.cogs['ServerCog'].default_language
        if lang_opt == 'fi':
            try:
                result = self.translations['fi'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"fi")
                lang_opt = 'en'
        if lang_opt == 'lolcat':
            try:
                result = lolcat[moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"lolcat")
                lang_opt = 'en'
        if lang_opt == 'en':
            try:
                result = self.translations['en'][moduleID][messageID]
            except:
                await self.msg_not_found(moduleID,messageID,"en")
                lang_opt = 'fr'
        if lang_opt == 'fr':
            try:
                result = fr[moduleID][messageID]
            except KeyError:
                await self.msg_not_found(moduleID,messageID,"fr")
                result = ""
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_error(e,None)
                result = ""
        if isinstance(result,str):
            try:
                return result.format_map(self.bot.SafeDict(args))
            except ValueError:
                return result
        else:
            return result

    async def msg_not_found(self,moduleID,messageID,lang):
        try:
            await self.bot.cogs['ErrorsCog'].senf_err_msg("Le message {}.{} n'a pas été trouvé dans la base de donnée! (langue {})".format(moduleID,messageID,lang))
        except:
            pass

    async def check_tr(self,channel,lang):
        liste = list()
        if lang not in self.languages:
            await channel.send("La langue `{}` n'est pas disponible".format(lang))
            return
        count = 0
        for k,v in dict(self.translations['fr']).items():
            if not k.startswith("__"):
                if k not in self.translations[lang].keys():
                    await channel.send("Le module {} n'existe pas en `{}`".format(k,lang))
                    count += len(v.keys())
                    continue
                for i in v.keys():
                    if i not in self.translations[lang][k].keys():
                        liste.append("module "+k+" - "+i)
                        count += 1
        if count==0:
            await channel.send("Tout les messages ont correctement été traduits en `{}` !".format(lang))
        else:
            if len("\n- ".join(liste))>1900:
                temp = f"{count} messages non traduits en `{lang}` :"
                for i in liste:
                    if len(temp+i)>2000:
                        await channel.send(temp)
                        temp = ""
                    temp += "\n"+i
                await channel.send(temp)
            elif len(liste)>0:
                await channel.send("{} messages non traduits en `{}` :\n- {}".format(count,lang,"\n- ".join(liste)))
            else:
                await channel.send(">> {} messages non traduits en `{}`".format(count,lang))

    async def change_cache(self,serverID,new_lang):
        #print("change_cache:",new_lang)
        if new_lang in self.languages:
            #print("changement effectué")
            self.serv_opts[str(serverID)] = new_lang


def setup(bot):
    bot.add_cog(LangCog(bot))
