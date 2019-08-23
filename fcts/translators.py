import discord
from discord.ext import commands
import json, os


async def is_translator(ctx:commands.Context) -> bool:
    return ctx.author.id in [279568324260528128, # Z_runner
        281404141841022976, # Awhikax
        552273019020771358, # Z_Jumper
        349899849937846273, # Jees1
        ]

class TranslatorsCog(commands.Cog):
    """Special cog for those who help with the translation of the bot"""

    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self.file = 'translators'
        if not os.path.exists('fcts/translation/'):
            os.makedirs('fcts/translation/')
        self.translations = {'en':self.load_translation('en'),
            'fi':self.load_translation('fi')}
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
        self.todo = {'fi':sorted([x for x in self.translations['en'].keys() if x not in self.translations['fi'].keys()])}
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
    
    def load_translation(self,lang:str):
        result = dict()
        if lang not in self.bot.cogs['LangCog'].languages:
            return result
        with open(f'fcts/lang/{lang}.json','r') as f:
            data = json.load(f)
        for module, mv in data.items():
            for key, value in mv.items():
                if isinstance(value,str):
                    result[module+'.'+key] = value
                elif isinstance(value,dict):
                    for minikey, minivalue in value.items():
                        if isinstance(minivalue,list):
                            for e,string in enumerate(minivalue):
                                result[module+'.'+key+'.'+minikey+'.'+str(e)] = string
                        else:
                            result[module+'.'+key+'.'+minikey] = minivalue
                elif isinstance(value,list):
                    for e,string in enumerate(value):
                        result[module+'.'+key+'.'+str(e)] = string
        try:
            temp = self.load_project(lang)
        except FileNotFoundError:
            pass
        else:
            did = result.keys()
            for k,v in temp.items():
                if k not in did:
                    result[k] = v
        return result
    
    def load_project(self,lang:str):
        result = dict()
        with open('fcts/translation/'+lang+'.txt','r',encoding='utf-8') as f:
            for line in f.readlines():
                temp = line.split(' ')
                result[temp[0]] = " ".join(temp[1:])
        return result

    async def modify_project(self,lang:str,key:str,new:str):
        """Modify a string inside the project file"""
        with open('fcts/translation/'+lang+'.txt','a',encoding='utf-8') as f:
            f.write(key+' '+new.replace('\n','\\n')+'\n')
        self.translations[lang][key] = new

    @commands.command(name='translate')
    @commands.check(is_translator)
    async def translate_smth(self,ctx,lang:str):
        """Translate a message of the bot
        Original message is in English
        The text is not immediatly added into the bot and need an update to be in"""
        if lang not in self.translations.keys():
            return await ctx.send("Invalid language")
        if len(self.todo[lang])==0:
            return await ctx.send("This language is already 100% translated :tada:")
        key = self.todo[lang][0]
        value = self.translations['en'].__getitem__(key)
        await ctx.send(value)
        await ctx.send(f"How would you translate it in {lang}?\n\n  *Key: {key}*\nType 'pass' to choose another one")
        msg = await self.bot.wait_for('message', check=lambda msg: msg.author.id==ctx.author.id and msg.channel.id==ctx.channel.id)
        if msg.content == 'pass':
            await ctx.send("This message will be ignored until the next reload of this command")
        else:
            await self.modify_project(lang,key,msg.content)
            await ctx.send(f"New translation:\n :arrow_right: {msg.content}")
        self.todo[lang].remove(key)
    
    @commands.command(name='tr-reload-todo')
    @commands.check(is_translator)
    async def reload_todo(self,ctx,lang:str):
        """Reload the to-do list of a language translation"""
        if lang not in self.todo.keys():
            return await ctx.send("Invalid language")
        self.todo = {'fi':sorted([x for x in self.translations['en'].keys() if x not in self.translations['fi'].keys()])}
        await ctx.send("ToDo list for {} has been reloaded".format(lang))

    @commands.command(name="tr-status")
    @commands.check(is_translator)
    async def status(self,ctx,lang:str=None):
        """Get the status of a translation project"""
        if lang==None:
            txt = "General status:"
            en_progress = len(self.translations['en'])
            for l in self.translations.keys():
                if l == 'en':
                    continue
                lang_progress = len(self.translations[l])
                c = lang_progress*100 / en_progress
                txt += f"\n- {l}: {round(c)}% ({lang_progress}/{en_progress})"
        elif lang not in self.todo.keys():
            return await ctx.send("Invalid language")
        else:
            lang_progress = len(self.translations[lang])
            en_progress = len(self.translations['en'])
            c = lang_progress*100 / en_progress
            txt = f"Translation of {lang}:\n {round(c,1)}%\n {lang_progress} messages on {en_progress}"
        await ctx.send(txt)


def setup(bot):
    bot.add_cog(TranslatorsCog(bot))