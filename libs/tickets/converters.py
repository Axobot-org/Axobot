from typing import Annotated, Optional, Union

import discord
from discord.ext import commands

from fcts.args import UnicodeEmoji
from libs.bot_classes import MyContext


class AnyEmojiConverter:
    "Represents any unicode or Discord emoji"

    @classmethod
    async def convert(cls, ctx: MyContext, argument: str):
        "Convert an argument into a PartialEmoji or Unicode emoji"
        try:
            return await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.errors.BadArgument:
            return await UnicodeEmoji().convert(ctx, argument)

EmojiConverterType = Annotated[Union[discord.PartialEmoji, UnicodeEmoji], AnyEmojiConverter]
