from typing import Any

import discord

AnyTuple = tuple[Any, ...]
AnyList = list[Any]
AnyDict = dict[Any, Any]
AnyStrDict = dict[str, Any]
UserOrMember = discord.User | discord.Member

__all__ = (
    "AnyTuple",
    "AnyList",
    "AnyDict",
    "AnyStrDict",
    "UserOrMember",
)
