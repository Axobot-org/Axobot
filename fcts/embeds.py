import aiohttp
import discord
from discord.ext import commands

from libs.bot_classes import Axobot

BASE_URL = 'https://discord.com/api/webhooks/'

class Embeds(commands.Cog):
    """Cog for the management of the embeds. No more, no less."""

    def __init__(self, bot: Axobot):
        self.bot = bot
        self.logs = {'classic':"625369482587537408/uGh5fJWD6S1XAddNKOGohvyfXWOxPmsodQQPcp7iasagi5kJm8DKfbzmf7-UFb5u3gnd",
            'loop':'625369730127101964/04KUvJxdb-Dl-BIkIdBydqZIoziBn5qy06YugIO3T4uOUYqMIT4YgoP6C0kv6CrrA8h8',
            'members':'625369820145123328/6XENir2vqOBpGLIplX96AILOVIW4V_YVyqV8QhbtvVZ7Mcj9gKZpty8aaYF5JrkUCfl-',
            'beta':'625369903389736960/9xvl-UiQg5_QEekMReMVjf8BtvULzWT1BsU7gG0EulhtPQGc8EoAcc2QoHyVAYKmwlsv'
        }
        self.file = "embeds"

    async def send(self, embeds, url: str=None):
        """Send a list of embeds to a discord channel"""
        if url is None:
            url = BASE_URL + self.logs['beta'] if self.bot.beta else BASE_URL + self.logs['classic']
        else:
            if url in self.logs:
                url = BASE_URL + self.logs[url]
        embeds_list = []
        for embed in embeds:
            if isinstance(embed, discord.Embed):
                embeds_list.append(embed.to_dict())
            else:
                embeds_list.append(embed["embed"])
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={"embeds": embeds_list}) as resp:
                try:
                    msg: dict = await resp.json()
                except aiohttp.ContentTypeError:
                    return
                else:
                    if "error" in msg:
                        err_msg = f"`Webhook error {url}:` [{resp.status}] {msg}"
                        await self.bot.get_cog('Errors').senf_err_msg(err_msg)


async def setup(bot):
    await bot.add_cog(Embeds(bot))
