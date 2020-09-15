import discord, aiohttp, re, typing, datetime, isbnlib
from discord.ext import commands


class ISBN(commands.Converter):
    
    async def convert(self,ctx:commands.Context,argument:str) -> int:
        # if argument.isnumeric() and (len(argument)==10 or len(argument)==13):
        #     return int(argument)
        if isbnlib.notisbn(argument):
            raise commands.errors.BadArgument('Invalid ISBN: '+argument)
        return isbnlib.get_canonical_isbn(argument)


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


    async def db_add_search(self, ISBN:int, name:str):
        # name = name.replace('"','\\\"')
        cnx = self.bot.cnx_frm
        cursor = cnx.cursor()
        current_timestamp = datetime.datetime.utcnow()
        # query = "INSERT INTO `{t}` (`ISBN`,`name`,`count`,`last_update`) VALUES ('{i}',\"{n}\",1) ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = '{l}';".format(t=self.tables[0],i=ISBN,n=name,l=current_timestamp)
        query = "INSERT INTO `{}` (`ISBN`,`name`,`count`) VALUES (%(i)s, %(n)s, 1) ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = %(l)s;".format(self.tables[0])
        cursor.execute(query, { 'i': ISBN, 'n': name, 'l': current_timestamp })
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

    async def search_book_2(self, isbn:str, keywords:str) -> dict:
        if isbn is None:
            if keywords is None:
                raise ValueError
            isbn = isbnlib.isbn_from_words(keywords)
        info = dict()
        for key in ['wiki', 'default', 'openl', 'goob']:
            try:
                i = isbnlib.meta(isbn, service=key)
            except (isbnlib.dev._exceptions.DataNotFoundAtServiceError, isbnlib.dev._exceptions.ISBNLibHTTPError):
                continue
            if i is not None and len(i) > 0:
                info.update({
                    'title': i['Title'],
                    'authors': i['Authors']
                })
                if i['Year']:
                    info['publication'] = i['Year']
                if i['Publisher']:
                    info['publisher'] = i['Publisher']
                if 'language' not in info and len(i['Language']) > 0:
                    info['language'] = i['Language']
        if len(info) > 0:
            co = isbnlib.cover(isbn)
            if 'thumbnail' in co:
                info['cover'] = co['thumbnail']
            info['isbn'] = isbn
        return None if len(info) == 0 else info


    @commands.group(name="book",aliases=['bookstore'])
    async def book_main(self,ctx):
        """Search for a book and manage your library"""
        if ctx.subcommand_passed==None:
            await self.bot.cogs['HelpCog'].help_command(ctx,['book'])
    
    @book_main.command(name="search",aliases=["book"])
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def book_search(self, ctx:commands.Context, ISBN:typing.Optional[ISBN], *, keywords:str=''):
        """Search from a book from its ISBN or search terms"""
        keywords = keywords.replace('-','')
        while '  ' in keywords:
            keywords = keywords.replace('  ',' ')
        try:
            book = await self.search_book_2(ISBN, keywords)
        except isbnlib.dev._exceptions.ISBNLibHTTPError:
            await ctx.send(await self.translate(ctx.channel, "library", "rate-limited") + " :confused:")
            return
        if book is None:
            return await ctx.send(await self.translate(ctx.channel,'library','no-found'))
        unknown = await self.translate(ctx.channel, 'library', 'unknown')
        if ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).embed_links:
            thumb = book.get('cover', '')
            emb = await self.bot.get_cog('EmbedCog').Embed(title=book['title'], thumbnail=thumb, color=5301186).create_footer(ctx)
            if 'authors' in book:
                t = await self.translate(ctx.channel, 'library', 'author' if len(book['authors']) <= 1 else 'authors')
                t = t.capitalize()
                emb.add_field(t, '\n'.join(book['authors']))
            # Publisher
            publisher = (await self.translate(ctx.channel, 'library', 'publisher')).capitalize()
            emb.add_field(publisher, book.get('publisher', unknown))
            # ISBN
            emb.add_field('ISBN', book['isbn'], True)
            # Publication year
            publication = (await self.translate(ctx.channel, 'library', 'year')).capitalize()
            emb.add_field(publication, book.get('publication', unknown), True)
            # Language
            if 'language' in book:
                lang = (await self.translate(ctx.channel, 'library', 'language')).capitalize()
                emb.add_field(lang, book['language'], True)
            await ctx.send(embed=emb)
        else:
            auth = '\n'.join(book['authors']) if 'authors' in book else unknown
            authors = (await self.translate(ctx.channel, 'library', 'author' if len(book['authors']) <= 1 else 'authors')).capitalize()
            title = (await self.translate(ctx.channel, 'library', 'title')).capitalize()
            publisher = (await self.translate(ctx.channel, 'library', 'publisher')).capitalize()
            publication = (await self.translate(ctx.channel, 'library', 'year')).capitalize()
            lang = (await self.translate(ctx.channel, 'library', 'language')).capitalize()
            txt = f"**{title}:** {book.get('title', unknown)}\n**{authors}:** {auth}\n**ISBN:** {book['isbn']}\n**{publisher}:** {book.get('publisher', unknown)}\n**{publication}:** {book.get('publication', unknown)}\n**{lang}:** {book.get('language', unknown)}"
            await ctx.send(txt)
        await self.db_add_search(book['isbn'], book['title'])





def setup(bot):
    bot.add_cog(LibCog(bot))