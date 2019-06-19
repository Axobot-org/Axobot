import datetime, discord, requests
from discord.ext import commands

url_base = 'https://discordapp.com/api/webhooks/'

class EmbedCog(commands.Cog):
    """Cog for the management of the embeds. No more, no less."""

    def __init__(self,bot):
        self.bot = bot
        self.logs = {'classic':"589806375366950913/Vy1Toc--s9MKLwz0S6g0khMgxIJcNO06KvRccpwrSTrTUXXeXkZavYgLhCZ3OuRONKfq",
            'loop':'589807300546527245/EqhdboEF8H0ysUr7X77ty6NUBNkJa-_nfcNw22aPX9MqvTtvIrvDi88wSFX3IiII0sIE',
            'members':'584381991919550474/7ocQuqPNPN4n1OlHjNyG8eBeABL9XD-AGbHCk9oURTCL4a9kFb596biFGNNI-A5qzkHt',
            'beta':'590966608063758365/89JAR_BWffLlMMzNnpwtbcRR8Rp4y0xIB3pCfP724bG5Y65OY02Xy_QvUsgw57kpqv-d'
        }
        self.file = "embeds"


    class Embed:
        def __init__(self,title="",desc="",url="",color=0,time=discord.Embed.Empty,footer_url="",footer_text="",thumbnail="",image="",author_name="",author_url="",author_icon="",fields=[]):
            self.title = title
            self.description = desc
            self.url = url
            self.color = color
            self.timestamp = time
            self.footer_text = footer_text
            self.footer_url = footer_url
            self.thumbnail = thumbnail
            self.image = image
            self.author_name = author_name
            self.author_url = author_url
            self.author_icon = author_icon
            self.fields = fields
            for x in self.fields:
                if "inline" not in x.keys():
                    x['inline'] = False
                if "name" not in x.keys():
                    x["name"] = "No name"
                if "value" not in x.keys():
                    x["value"] = "No value"
        
        def update_timestamp(self):
            self.timestamp = datetime.datetime.utcnow()
            return self

        def json(self):
            j = dict()
            emb = dict()
            if self.title != "":
                emb["title"] = self.title
            if self.description != "":
                emb["description"] = self.description
            if self.url != "":
                emb["url"] = self.url
            if self.color != 0:
                emb["color"] = self.color
            if str(self.timestamp) != "":
                emb["timestamp"] = str(self.timestamp)
            if self.footer_text != "" and self.footer_url != "":
                emb["footer"] = {"icon_url":str(self.footer_url),"icon_text":self.footer_text}
            if self.thumbnail != "":
                emb["thumbnail"] = {"url":self.thumbnail}
            if self.image != "":
                emb["image"]  = {"url":"self.image"}
            if self.author_icon != "" or self.author_name != "" or self.author_url != "":
                auth = dict()
                if self.author_name != "":
                    auth["name"] = self.author_name
                if self.author_url != "":
                    auth["url"] = self.author_url
                if self.author_icon != "":
                    auth["icon_url"] = str(self.author_icon)
                emb["author"] = auth
            if self.fields != []:
                emb["fields"] = self.fields
            if emb != {}:
                j["embed"] = emb
            return j

        def set_author(self,user):
            self.author_name = user.name
            self.author_icon = str(user.avatar_url_as(format='gif',size=256)) if user.is_avatar_animated() else str(user.avatar_url_as(format='png',size=256))
            return self
        
        def create_footer(self,user):
            self.footer_text = "Requested by {}".format(user.name)
            self.footer_url = user.avatar_url_as(format='png',size=256)
            return self

        def discord_embed(self):
            if type(self.color)==discord.Colour:
                color = self.color
            else:
                color = discord.Color(self.color)
            emb = discord.Embed(title=self.title, colour=color, url=self.url, description=self.description, timestamp=self.timestamp)
            emb.set_image(url=self.image)
            emb.set_thumbnail(url=self.thumbnail)
            emb.set_author(name=self.author_name, url=self.author_url, icon_url=str(self.author_icon))
            emb.set_footer(text=self.footer_text, icon_url=str(self.footer_url))
            for x in self.fields:
                emb.add_field(name=x["name"],value=x["value"],inline=x["inline"])
            return emb
    

    async def send(self,embeds,url=None,ctx=None):
        if url == None:
            url = url_base + self.logs['beta'] if self.bot.beta else self.logs['classic']
        else:
            if url in self.logs.keys():
                url = url_base + self.logs[url]
        liste = list()
        for x in embeds:
            if type(x) == self.Embed:
                liste.append(x.json()["embed"])
            else:
                liste.append(x["embed"])
        r = requests.post(url,json={"embeds":liste})
        try:
            msg = r.json()
            if "error" in msg.keys():
                await self.bot.cogs['ErrorsCog'].senf_err_msg("`Erreur webhook {}:` [code {}] {}".format(url,r.status_code,msg))
        except:
            return
        

def setup(bot):
    bot.add_cog(EmbedCog(bot))