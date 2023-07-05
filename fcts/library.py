import html
from typing import Optional
import aiohttp
import discord
import isbnlib
from discord.ext import commands

from libs.arguments import args
from libs.bot_classes import Axobot, MyContext


class Library(commands.Cog):

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.file = 'library'
        self.tables = ['librarystats_beta', 'library_beta'] if bot.beta else ['librarystats', 'library']
        self.cache = dict()

    async def on_ready(self):
        self.tables = ['librarystats_beta', 'library_beta'] if self.bot.beta else ['librarystats', 'library']

    async def db_add_search(self, isbn: int, name: str):
        current_timestamp = self.bot.utcnow()
        query = "INSERT INTO `{}` (`ISBN`,`name`,`count`) VALUES (%(i)s, %(n)s, 1) ON DUPLICATE KEY UPDATE count = `count` + 1, last_update = %(l)s;".format(self.tables[0])
        async with self.bot.db_query(query, {'i': isbn, 'n': name, 'l': current_timestamp}):
            pass

    async def search_book(self, isbn: int, keywords: str, language: str = None) -> dict:
        """Search a book from its ISBN"""
        keywords = keywords.replace(' ', '+')
        if language == 'fr':
            language = None
        url = f'https://www.googleapis.com/books/v1/volumes?q={keywords}'
        if isbn is not None:
            url += f'+isbn:{isbn}' if len(keywords) > 0 else f'_isbn:{isbn}'
        if language is not None:
            url += f'&langRestrict={language}'
        url += '&country=FR'
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp = await resp.json()
        if 'items' in resp.keys():
            return resp['items'][0]
        if language is not None:
            return await self.search_book(isbn, keywords)
        return None

    async def isbn_from_words(self, keywords: str) -> Optional[str]:
        """Get the ISBN of a book from some keywords"""
        url = "https://www.googleapis.com/books/v1/volumes?maxResults=1&q=" + html.escape(keywords.replace(' ', '+'))
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp = await resp.json()
        if 'items' in resp.keys():
            return resp['items'][0]['volumeInfo']['industryIdentifiers'][-1]['identifier']
        return None

    async def search_book_2(self, isbn: Optional[str], keywords: str) -> dict:
        if isbn is None:
            if keywords is None:
                raise ValueError
            info = self.cache.get(keywords, None)
            if info is not None:
                return info
            try:
                isbn = isbnlib.isbn_from_words(keywords)
            except isbnlib.ISBNLibException:
                isbn = await self.isbn_from_words(keywords)
            if isbn is None:
                return
        info = {}
        for key in ['wiki', 'default', 'openl', 'goob']:
            try:
                i = isbnlib.meta(isbn, service=key)
            except isbnlib.ISBNLibException:
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
        info = None if len(info) == 0 else info
        self.cache[keywords] = info
        return info

    @commands.group(name="book", aliases=['bookstore'])
    async def book_main(self, ctx: MyContext):
        """Search for a book and manage your library

        ..Doc miscellaneous.html#book"""
        if ctx.subcommand_passed is None:
            await ctx.send_help(ctx.command)

    @book_main.command(name="search", aliases=["book"])
    @commands.cooldown(5, 60, commands.BucketType.guild)
    async def book_search(self, ctx: MyContext, isbn: Optional[args.ISBN], *, keywords: str = ''):
        """Search from a book from its ISBN or search terms

        ..Example book search Percy Jackson

        ..Example book search 9781119688037

        ..Doc miscellaneous.html#search-by-isbn"""
        keywords = keywords.replace('-', '')
        while '  ' in keywords:
            keywords = keywords.replace('  ', ' ')
        try:
            book = await self.search_book_2(isbn, keywords)
        except isbnlib.dev.ISBNLibHTTPError:
            await ctx.send(await self.bot._(ctx.channel, "library.rate-limited") + " :confused:")
            return
        if book is None:
            return await ctx.send(await self.bot._(ctx.channel, 'library.none-found'))
        unknown = await self.bot._(ctx.channel, 'library.unknown')
        authors = [x for x in book.get('authors', list()) if x] # filter empty string and other weird things
        if ctx.can_send_embed:
            emb = discord.Embed(title=book['title'], color=5301186)
            emb.set_thumbnail(url=book.get('cover', ''))
            emb.set_footer(text=ctx.author, icon_url=ctx.author.display_avatar)

            if authors:
                t = await self.bot._(ctx.channel, 'library.author' if len(authors) <= 1 else 'authors')
                t = t.capitalize()
                emb.add_field(name=t, value='\n'.join(authors)  )
            # Publisher
            publisher = (await self.bot._(ctx.channel, 'library.publisher')).capitalize()
            emb.add_field(name=publisher, value=book.get('publisher', unknown))
            # ISBN
            emb.add_field(name='ISBN', value=book['isbn'], inline=False)
            # Publication year
            publication = (await self.bot._(ctx.channel, 'library.year')).capitalize()
            emb.add_field(name=publication, value=book.get('publication', unknown))
            # Language
            if 'language' in book:
                lang = (await self.bot._(ctx.channel, 'library.language')).capitalize()
                emb.add_field(name=lang, value=book['language'])
            await ctx.send(embed=emb)
        else:
            auth = '\n'.join(authors) if authors else unknown
            authors = (await self.bot._(ctx.channel, 'library.author' if len(authors) <= 1 else 'authors')).capitalize()
            title = (await self.bot._(ctx.channel, 'library.title')).capitalize()
            publisher = (await self.bot._(ctx.channel, 'library.publisher')).capitalize()
            publication = (await self.bot._(ctx.channel, 'library.year')).capitalize()
            lang = (await self.bot._(ctx.channel, 'library.language')).capitalize()
            txt = f"**{title}:** {book.get('title', unknown)}\n**{authors}:** {auth}\n**ISBN:** {book['isbn']}\n**{publisher}:** {book.get('publisher', unknown)}\n**{publication}:** {book.get('publication', unknown)}\n**{lang}:** {book.get('language', unknown)}"
            await ctx.send(txt)
        await self.db_add_search(book['isbn'], book['title'])


async def setup(bot):
    await bot.add_cog(Library(bot))
