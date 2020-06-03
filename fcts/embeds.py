import datetime, discord, requests, typing
from discord.ext import commands

url_base = 'https://discord.com/api/webhooks/'

class EmbedCog(commands.Cog):
    """Cog for the management of the embeds. No more, no less."""

    def __init__(self,bot):
        self.bot = bot
        self.logs = {'classic':"625369482587537408/uGh5fJWD6S1XAddNKOGohvyfXWOxPmsodQQPcp7iasagi5kJm8DKfbzmf7-UFb5u3gnd",
            'loop':'625369730127101964/04KUvJxdb-Dl-BIkIdBydqZIoziBn5qy06YugIO3T4uOUYqMIT4YgoP6C0kv6CrrA8h8',
            'members':'625369820145123328/6XENir2vqOBpGLIplX96AILOVIW4V_YVyqV8QhbtvVZ7Mcj9gKZpty8aaYF5JrkUCfl-',
            'beta':'625369903389736960/9xvl-UiQg5_QEekMReMVjf8BtvULzWT1BsU7gG0EulhtPQGc8EoAcc2QoHyVAYKmwlsv'
        }
        self.file = "embeds"


    class Embed:
        def __init__(self,title="",desc="",url="",color=None,time=discord.Embed.Empty,footer_url="",footer_text="",thumbnail="",image="",author_name="",author_url="",author_icon="",fields=None):
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
            if fields==None:
                fields = list()
            for e,x in enumerate(fields):
                if "inline" not in x.keys():
                    fields[e]['inline'] = False
                if "name" not in x.keys():
                    fields[e]["name"] = "No name"
                if "value" not in x.keys():
                    fields[e]["value"] = "No value"
            self.fields = fields
        
        def add_field(self,name="No name",value="No value",inline=False):
            self.fields.append({'name':name,'value':value,'inline':inline})
        
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
            if self.color != None:
                if isinstance(self.color,discord.Colour):
                    emb["color"] = self.color.value
                else:
                    emb["color"] = self.color
            if self.timestamp != discord.Embed.Empty:
                emb["timestamp"] = str(self.timestamp)
            if self.footer_text != "" or self.footer_url != "":
                emb["footer"] = {"icon_url":str(self.footer_url),"text":self.footer_text}
            if self.thumbnail != "":
                emb["thumbnail"] = {"url":self.thumbnail}
            if self.image != "":
                emb["image"]  = {"url":self.image}
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
        
        def to_dict(self):
            return self.json()['embed']

        def set_author(self,user):
            self.author_name = user.name
            self.author_icon = str(user.avatar_url_as(format='gif',size=256)) if user.is_avatar_animated() else str(user.avatar_url_as(format='png',size=256))
            return self
        
        async def create_footer(self, ctx:commands.Context, user: typing.Union[discord.User,discord.Member]=None):
            # self.footer_text = "Requested by {}".format(user.name)
            if user==None:
                user = ctx.author
            self.footer_text = await ctx.bot.get_cog("LangCog").tr(ctx.channel,"keywords", "request_by", user=user.name)
            self.footer_url = user.avatar_url_as(format='png',size=256)
            return self

        def discord_embed(self):
            if type(self.color)==discord.Colour:
                color = self.color
            elif self.color is None:
                color = discord.Embed.Empty
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
        if url is None:
            url = url_base + self.logs['beta'] if self.bot.beta else url_base + self.logs['classic']
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