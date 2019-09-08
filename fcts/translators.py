import discord, asyncio
from discord.ext import commands
import json, os


async def is_translator(ctx:commands.Context) -> bool:
    return await ctx.bot.cogs['UtilitiesCog'].is_translator(ctx.author)

async def check_admin(ctx):
    return await ctx.bot.cogs['AdminCog'].check_if_admin(ctx)

class TranslatorsCog(commands.Cog):
    """Special cog for those who help with the translation of the bot"""

    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self.file = 'translators'
        if not os.path.exists('translation/'):
            os.makedirs('translation/')
        self.project_list = ['fr','en','lolcat','fi','de','es','it','br','tr']
        self.translations = {'en':self.load_translation('en'),
            'fi':self.load_translation('fi'),
            'de':self.load_translation('de'),
            'es':self.load_translation('es'),
            'it':self.load_translation('it'),
            'br':self.load_translation('br'),
            'tr':self.load_translation('tr')}
        try:
            self.translate = self.bot.cogs["LangCog"].tr
        except:
            pass
        self.todo = {'fi':sorted([x for x in self.translations['en'].keys() if x not in self.translations['fi'].keys()]),
                'de':sorted([x for x in self.translations['en'].keys() if x not in self.translations['de'].keys()]),
                'es':sorted([x for x in self.translations['en'].keys() if x not in self.translations['es'].keys()]),
                'it':sorted([x for x in self.translations['en'].keys() if x not in self.translations['it'].keys()]),
                'br':sorted([x for x in self.translations['en'].keys() if x not in self.translations['br'].keys()]),
                'tr':sorted([x for x in self.translations['en'].keys() if x not in self.translations['tr'].keys()])}
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.translate = self.bot.cogs["LangCog"].tr
    
    def load_translation(self,lang:str):
        result = dict()
        if lang not in self.project_list:
            return result
        try:
            with open(f'fcts/lang/{lang}.json','r') as f:
                data = json.load(f)
        except FileNotFoundError:
            pass
        else:
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
        with open('translation/'+lang+'.txt','r',encoding='utf-8') as f:
            for line in f.readlines():
                temp = line.split(' ')
                result[temp[0]] = " ".join(temp[1:])
        return result

    async def modify_project(self,lang:str,key:str,new:str):
        """Modify a string inside the project file"""
        with open('translation/'+lang+'.txt','a',encoding='utf-8') as f:
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
        await ctx.send("```\n"+value+"\n```")
        await ctx.send(f"How would you translate it in {lang}?\n\n  *Key: {key}*\nType 'pass' to choose another one")
        try:
            msg = await self.bot.wait_for('message', check=lambda msg: msg.author.id==ctx.author.id and msg.channel.id==ctx.channel.id, timeout=90)
        except asyncio.TimeoutError:
            return await ctx.send("You were too slow. Try again.")
        if msg.content.lower() == 'pass':
            await ctx.send("This message will be ignored until the next reload of this command")
        else:
            await self.modify_project(lang,key,msg.content)
            await ctx.send(f"New translation:\n :arrow_right: {msg.content}")
        try:
            self.todo[lang].remove(key)
        except ValueError:
            pass
    
    @commands.command(name='tr-reload-todo')
    @commands.check(is_translator)
    async def reload_todo(self,ctx,lang:str):
        """Reload the to-do list of a language translation"""
        if lang not in self.todo.keys():
            return await ctx.send("Invalid language")
        langs = self.todo.keys()
        self.todo = {lang:sorted([x for x in self.translations['en'].keys() if x not in self.translations[lang].keys()]) for lang in langs}
        await ctx.send("ToDo list for {} has been reloaded".format(lang))

    @commands.command(name="tr-status")
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
    
    async def _fuse_file(self,old:dict,new:str):
        async def readpath(path:list,o,msg:str):
            if len(path)==0:
                return msg
            else:
                if len(path)>1:
                    if path[1].isnumeric():
                        temp = list()
                    else:
                        temp = dict()
                else:
                    temp = None
                if path[0].isnumeric():
                    if len(o)>int(path[0]):
                        await readpath(path[1:],o[int(path[0])],msg)
                    else:
                        t = await readpath(path[1:],temp,msg)
                        o.insert(int(path[0]), t)
                else:
                    if path[0] in o.keys():
                        await readpath(path[1:],o[path[0]],msg)
                    else:
                        o[path[0]] = await readpath(path[1:],temp,msg)
                return o
        for line in new.split('\n'):
            if len(line.strip())==0:
                continue
            await readpath(line.split(' ')[0].split('.'),old,' '.join(line.split(' ')[1:]))
        return old


    @commands.command(name='tr-edit')
    @commands.check(is_translator)
    async def edit_tr(self,ctx,lang:str,key:str,*,translation:str=None):
        """Edit a translation"""
        if lang not in self.translations.keys():
            return await ctx.send("Invalid language")
        if not key in self.translations['en'].keys():
            return await ctx.send("Invalid key")
        if translation==None:
            await ctx.send("```\n"+self.translations['en'][key]+"\n```")
            try:
                msg = await self.bot.wait_for('message', check=lambda msg: msg.author.id==ctx.author.id and msg.channel.id==ctx.channel.id, timeout=90)
            except asyncio.TimeoutError:
                return await ctx.send("You were too slow. Try again.")
            translation = msg.content
        await self.modify_project(lang,key,translation)
        await ctx.send(f"New translation:\n :arrow_right: {translation}")
            

    @commands.command(name="tr-file")
    @commands.check(check_admin)
    async def fuse_file(self,ctx,lang:str):
        """Merge the current project file
        with the already-translated file"""
        if lang not in self.todo.keys():
            return await ctx.send("Invalid language")
        try:
            with open(f'fcts/lang/{lang}.json','r',encoding='utf-8') as old_f:
                with open(f'translation/{lang}.txt','r',encoding='utf-8') as new_f:
                    new = await self._fuse_file(json.load(old_f),new_f.read())
        except FileNotFoundError:
            return await ctx.send("There is no current project with this language")
        with open(f'translation/{lang}.json','w',encoding='utf-8') as f:
            json.dump(new,f, ensure_ascii=False, indent=4, sort_keys=True)
        await ctx.send('Done!',file=discord.File(f'translation/{lang}.json'))


def setup(bot):
    bot.add_cog(TranslatorsCog(bot))