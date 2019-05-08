#!/usr/bin/env python
#coding=utf-8

from importlib import reload as m_reload
from fcts.lang import fr, en, lolcat, fi
import discord
m_reload(fr)
m_reload(en)
m_reload(lolcat)
m_reload(fi)


class LangCog(discord.ext.commands.Cog):

    def __init__(self,bot):
        m_reload(fr)
        m_reload(en)
        self.bot = bot
        self.file = "language"
        self.languages = ['fr','en','lolcat','fi']
        self.serv_opts = dict()


    async def tr(self,serverID,moduleID,messageID):
        """Renvoie le texte en fonction de la langue"""
        if type(serverID) == discord.Guild:
            serverID = serverID.id
        elif isinstance(serverID,discord.TextChannel):
            serverID = serverID.guild
        if not self.bot.database_online or serverID==None or isinstance(serverID,discord.DMChannel):
            lang_opt = self.bot.cogs['ServerCog'].default_language
        elif isinstance(serverID,discord.GroupChannel):
            used_langs = await self.bot.cogs['UtilitiesCog'].get_languages(serverID.recipient,limit=1)
            lang_opt = used_langs[0][0]
        elif str(serverID) in self.serv_opts.keys():
            lang_opt = self.serv_opts[str(serverID)]
            #print("Ex langage:",lang_opt)
            #print(self.serv_opts)
        else:
            conf_lang = self.bot.cogs["ServerCog"].conf_lang
            lang_opt = await conf_lang(serverID,"language","scret-desc")
            self.serv_opts[str(serverID)] = lang_opt
            #print("New langage:",lang_opt)
        if lang_opt not in self.languages:
            lang_opt = self.bot.cogs['ServerCog'].default_language
        if lang_opt == 'fi':
            try:
                return eval("fi."+moduleID+"[\""+messageID+"\"]")
            except:
                await self.msg_not_found(moduleID,messageID,"fi")
                lang_opt = 'en'
        if lang_opt == 'lolcat':
            try:
                return eval("lolcat."+moduleID+"[\""+messageID+"\"]")
            except:
                await self.msg_not_found(moduleID,messageID,"lolcat")
                lang_opt = 'en'
        if lang_opt == 'en':
            try:
                return eval("en."+moduleID+"[\""+messageID+"\"]")
            except:
                await self.msg_not_found(moduleID,messageID,"en")
                lang_opt = 'fr'
        if lang_opt == 'fr':
            try:
                return eval("fr."+moduleID+"[\""+messageID+"\"]")
            except:
                await self.msg_not_found(moduleID,messageID,"fr")
                return ""

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
        for dic in fr.__dict__:
            if not dic.startswith("__"):
                for i in eval("fr."+dic).keys():
                    try:
                        eval(lang+"."+str(dic)+"[\""+str(i)+"\"]")
                    except KeyError:
                        liste.append("module "+dic+" - "+i)
                        count += 1
                    except AttributeError:
                        await channel.send("Le module {} n'existe pas en `{}`".format(str(dic),lang))
                        count += len(eval("fr."+dic).keys())
                        break
        if count==0:
            await channel.send("Tout les messages ont correctement été traduits en `{}` !".format(lang))
        else:
            if len(liste)>0:
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
