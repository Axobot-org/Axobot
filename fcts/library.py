import discord, aiohttp, re, typing
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
        try:
            self.translate = bot.cogs['LangCog'].tr
        except:
            pass
    
    async def on_ready(self):
        self.translate = self.bot.cogs['LangCog'].tr


    async def search_book(self,isbn:int,keywords:str) -> dict:
        """Search a book from its ISBN"""
        keywords = keywords.replace(' ','+')
        url = f'https://www.googleapis.com/books/v1/volumes?q={keywords}'
        if isbn != None:
            url += f'+isbn:{isbn}' if len(keywords)>0 else f'_isbn:{isbn}'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                print(url)
                resp = await resp.json()
        if 'items' in resp.keys():
            return resp['items'][0]
        return None



    @commands.group(name="book",aliases=['bookstore'])
    async def book_main(self,ctx):
        """Search for a book and manage your library"""
        pass
    
    @book_main.command(name="search",aliases=["book"])
    async def book_search(self,ctx,ISBN:typing.Optional[ISBN],*,keywords:str=''):
        """Search from a book from its ISBN or search terms"""
        keywords = keywords.replace('-','')
        while '  ' in keywords:
            keywords = keywords.replace('  ',' ')
        book = await self.search_book(ISBN,keywords)
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
            author=' - '.join(vinfo['authors']),
            publisher=vinfo['publisher'],
            publication=vinfo['publishedDate'],
            language=vinfo['language'],
            pages=vinfo['pageCount'],
            isbn=real_isbn
            )
        try:
            thumb = vinfo['imageLinks']['thumbnail']
        except:
            thumb = ''
        if ctx.guild == None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            emb = self.bot.cogs['EmbedCog'].Embed(title=vinfo['title'],desc=txt,url=vinfo['infoLink'],thumbnail=thumb,color=5301186).create_footer(ctx.author)
            await ctx.send(embed=emb.discord_embed())
        else:
            await ctx.send(txt)





def setup(bot):
    bot.add_cog(LibCog(bot))