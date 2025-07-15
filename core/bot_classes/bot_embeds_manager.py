from typing import TYPE_CHECKING, Any, TypedDict

import aiohttp
import discord

if TYPE_CHECKING:
    from discord.types.embed import Embed as EmbedData

    from core.bot_classes import Axobot

class JSONEmbed(TypedDict):
    embed: "EmbedData"

BASE_URL = "https://discord.com/api/webhooks/"

async def send_log_embed(bot: "Axobot", embeds: list[discord.Embed | JSONEmbed], url: str | None=None):
    """Sensend_log_embedlist of embeds to a discord channel"""
    webhook_maps = bot.secrets["webhooks"]
    if url is None:
        url = BASE_URL + webhook_maps["beta" if bot.beta else "prod"]
    elif url in webhook_maps:
        url = BASE_URL + webhook_maps[url]
        assert isinstance(url, str), "Webhook URL must be a string"
    embeds_list = []
    for embed in embeds:
        if isinstance(embed, discord.Embed):
            embeds_list.append(embed.to_dict())
        else:
            embeds_list.append(embed["embed"])
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"embeds": embeds_list}) as resp:
            try:
                msg: dict[Any, Any] = await resp.json()
            except aiohttp.ContentTypeError:
                return
            if "error" in msg:
                err_msg = f"`Webhook error {url}:` [{resp.status}] {msg}"
                if (cog := bot.get_cog("Errors")):
                    await cog.send_err_msg(err_msg)
