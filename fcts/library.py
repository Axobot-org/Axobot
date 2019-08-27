import discord, aiohttp, re, typing, datetime
from discord.ext import commands


class ISBN(commands.Converter):
    
    async def convert(self,ctx:commands.Context,argument:str) -> int:
        if argument.isnumeric() and (len(argument)==10 or len(argument)==13):
            return int(argument)
        else:
            raise commands.errors.BadArgument('Invalid ISBN: '+argument)


class LibCog(commands.Cog):

    def __init__(self,bot:commands.Bot):
        self.bot = bot
        self.file = 'library'
        self.tables = ['librarystats_beta','library_beta'] if bot.beta else ['librarystats','library']
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    async def on_ready(self):
        self.tables = ['librarystats_beta','library_beta'] if self.bot.beta else ['librarystats','library']
        self.translate = self.bot.cogs['LangCog'].tr


    async def db_add_search(self,ISBN:int,name:str):
        name = name.replace('"','\\\"')
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        current_timestamp = datetime.datetime.utcnow()
        query = "INSERT INTO `{t}` (`ISBN`,`name`,`count`,`last_update`) VALUES ('{i}',\"{n}\",1,'{l}') ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = '{l}';".format(t=self.tables[0],i=ISBN,n=name,l=current_timestamp)
        cursor.execute(query)
        cnx.commit()
        cursor.close()



    async def search_book(self,isbn:int,keywords:str,language:str=None) -> dict:
        """Search a book from its ISBN"""
        keywords = keywords.replace(' ','+')
        if language=='fr':
            language = None
        url = f'https://www.googleapis.com/books/v1/volumes?q={keywords}'
        if isbn != None:
            url += f'+isbn:{isbn}' if len(keywords)>0 else f'_isbn:{isbn}'
        if language != None:
            url += f'&langRestrict={language}'
        url += '&country=FR'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp = await resp.json()
        if 'items' in resp.keys():
            return resp['items'][0]
        if language != None:
            return await self.search_book(isbn,keywords)
        return None



    @commands.group(name="book",aliases=['bookstore'])
    async def book_main(self,ctx):
        """Search for a book and manage your library"""
        pass
    
    @book_main.command(name="search",aliases=["book"])
    async def book_search(self,ctx:commands.Context,ISBN:typing.Optional[ISBN],*,keywords:str=''):
        """Search from a book from its ISBN or search terms"""
        keywords = keywords.replace('-','')
        while '  ' in keywords:
            keywords = keywords.replace('  ',' ')
        book = await self.search_book(ISBN,keywords,language = await self.translate(ctx.channel,'current_lang','current'))
        if book==None:
            return await ctx.send(await self.translate(ctx.channel,'library','no-found'))
        vinfo = book['volumeInfo']
        real_isbn = "".join([x['identifier'] for x in vinfo['industryIdentifiers'] if x['type']=="ISBN_13"])
        if len(real_isbn)==0:
            real_isbn = "".join([x['identifier'] for x in vinfo['industryIdentifiers'] if x['type']=="ISBN_10"])
        if len(real_isbn)==0:
            real_isbn = '?'
        txt = await self.translate(ctx.channel,'library','book_pres',
            title=vinfo['title'],
            subtitle=vinfo['subtitle'] if 'subtitle' in vinfo.keys() else '',
            author=' - '.join(vinfo['authors'] if 'authors' in vinfo.keys() else '?'),
            publisher=vinfo['publisher'] if 'publisher' in vinfo.keys() else '?',
            publication=vinfo['publishedDate'] if 'publishedDate' in vinfo.keys() else '?',
            language=vinfo['language'],
            pages=vinfo['pageCount'] if 'pageCount' in vinfo.keys() else '?',
            isbn=real_isbn
            )
        try:
            thumb = vinfo['imageLinks']['thumbnail']
        except:
            thumb = ''
        if ctx.guild == None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            emb = self.bot.cogs['EmbedCog'].Embed(title=vinfo['title'],desc=txt,url=vinfo['infoLink'],thumbnail=thumb,color=5301186).create_footer(ctx.author)
            try:
                price = [f"{k}: {x['amount']} {x['currencyCode']}" for k,x in book['saleInfo'].items() if k in ['listPrice','retailPrice']]
                if len(price)>0:
                    emb.add_field(await self.translate(ctx.channel,'library','price'),"\n".join(price))
            except Exception as e:
                await self.bot.cogs['ErrorsCog'].on_cmd_error(ctx,e)
                pass
            await ctx.send(embed=emb.discord_embed())
            del emb
        else:
            await ctx.send(txt)
        await self.db_add_search(int(real_isbn),vinfo['title'])





def setup(bot):
    bot.add_cog(LibCog(bot))