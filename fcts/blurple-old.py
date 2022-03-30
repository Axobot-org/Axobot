import datetime
import io
import math
import time
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands.cooldowns import BucketType
from PIL import Image, ImageEnhance, ImageSequence
from resizeimage import resizeimage
from libs.classes import MyContext

BLURPLE = (114, 137, 218, 255)
DARK_BLURPLE = (78, 93, 148, 255)
WHITE = (255, 255, 255, 255)
DARK = (1,1,35,255)

class BlurpleCog(commands.Cog):

    def __init__(self,bot):
        self.bot = bot
        self.file = 'blurple'


    @commands.command(name="isblurple",aliases=['blurple'])
    @commands.cooldown(rate=1, per=60, type=BucketType.user)
    async def blurple_cmd(self, ctx: MyContext, url: str = None):
        """Be part of the best birthday of the WORLD, and check if you're enough blurple to be cool!
        You can either give a user or an image URL in argument, or attach an image to your message. Plz don't forget to be cool."""
        if not (ctx.guild is None or ctx.channel.permissions_for(ctx.guild.me).attach_files):
            return await ctx.send(await self.bot._(ctx.channel,"blurple","missing-attachment-perm"))

        picture = None

        if url is not None:
            try:
                user = await commands.UserConverter().convert(ctx,url)
                picture = user.display_avatar.url
            except Exception:
                picture = url
        else:
            link = ctx.message.attachments
            if len(link) != 0:
                for image in link:
                    picture = image.url

        if picture is None:
            picture = ctx.author.display_avatar.url

        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(picture) as r:
                    response = await r.read()
        except ValueError:
            await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_invalid")).format(ctx.message.author.mention))
            return

        colourbuffer = 25

        try:
            im = Image.open(BytesIO(response))
        except Exception:
            await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_invalid")).format(ctx.message.author.mention))
            return

        await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_intro")).format(ctx.message.author.mention))

        im = im.convert('RGBA')
        imsize = list(im.size)
        impixels = imsize[0]*imsize[1]
        maxpixelcount = 1562500

        start = time.time()
        if impixels > maxpixelcount:
            downsizefraction = math.sqrt(maxpixelcount/impixels)
            im = resizeimage.resize_width(im, (imsize[0]*downsizefraction))
            imsize = list(im.size)
            impixels = imsize[0]*imsize[1]
            end = time.time()
            await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_resized")).format(ctx.message.author.mention,round(end-start,2)))

        def imager(im):
            global noofblurplepixels
            noofblurplepixels = 0
            global noofwhitepixels
            noofwhitepixels = 0
            global noofdarkblurplepixels
            noofdarkblurplepixels = 0
            global nooftotalpixels
            nooftotalpixels = 0
            global noofpixels
            noofpixels = 0

            img = im.load()

            for x in range(imsize[0]):
                for y in range(imsize[1]):
                    pixel = img[x,y]
                    check = 1
                    checkblurple = 1
                    checkwhite = 1
                    checkdarkblurple = 1
                    checkblack = 1
                    if pixel[3]<200:
                        noofpixels += 1
                        nooftotalpixels += 1
                        img[x,y] = (pixel[0], pixel[1], pixel[2], 0)
                        continue
                    for i in range(3):
                        if not(BLURPLE[i]+colourbuffer > pixel[i] > BLURPLE[i]-colourbuffer):
                            checkblurple = 0
                        if not(DARK_BLURPLE[i]+colourbuffer > pixel[i] > DARK_BLURPLE[i]-colourbuffer):
                            checkdarkblurple = 0
                        if not(WHITE[i]+colourbuffer > pixel[i] > WHITE[i]-colourbuffer):
                            checkwhite = 0
                        if not(DARK[i]+colourbuffer > pixel[i] > DARK[i]-colourbuffer):
                            checkblack = 0
                        if checkblurple == 0 and checkdarkblurple == 0 and checkwhite == 0 and checkblack == 0:
                            check = 0
                    if check == 0:
                        img[x,y] = (0, 0, 0, 255)
                    if check == 1:
                        nooftotalpixels += 1
                    if checkblurple == 1:
                        noofblurplepixels += 1
                    if checkdarkblurple == 1:
                        noofdarkblurplepixels += 1
                    if checkwhite == 1:
                        noofwhitepixels += 1
                    noofpixels += 1

            image_file_object = io.BytesIO()
            im.save(image_file_object, format='png')
            image_file_object.seek(0)
            return image_file_object

        async with aiohttp.ClientSession() as _:
            image = await self.bot.loop.run_in_executor(None, imager, im)
            image = discord.File(fp=image, filename='image.png')

            blurplenesspercentage = round(((nooftotalpixels/noofpixels)*100), 2)
            percentblurple = round(((noofblurplepixels/noofpixels)*100), 2)
            percentdblurple = round(((noofdarkblurplepixels/noofpixels)*100), 2)
            percentwhite = round(((noofwhitepixels/noofpixels)*100), 2)

            fields_txt = await self.bot._(ctx.guild,"blurple","check_fields")
            embed = discord.Embed(title = "", colour = 0x7289DA, description=fields_txt[5])
            if blurplenesspercentage>=99.99:
                embed.add_field(name=fields_txt[0], value=f"{blurplenesspercentage}% :tada:", inline=False)
            else:
                embed.add_field(name=fields_txt[0], value=f"{blurplenesspercentage}%", inline=False)
            embed.add_field(name=fields_txt[1], value=f"{percentblurple}%", inline=True)
            embed.add_field(name=fields_txt[2], value=f"{percentwhite}%", inline=True)
            embed.add_field(name=fields_txt[3], value=f"{percentdblurple}%", inline=True)
            embed.add_field(name="Guide", value=fields_txt[4], inline=False)
            embed.set_footer(text=fields_txt[6].format(ctx.author))
            embed.set_image(url="attachment://image.png")
            embed.set_thumbnail(url=picture)
            await ctx.send(embed=embed, file=image)
        if blurplenesspercentage>95 and str(picture)==str(ctx.author.display_avatar):
            date = datetime.datetime.today()
            if not await ctx.bot.get_cog('Utilities').has_blurple_card(ctx.author) and 6<date.day<20 and date.month==5:
                pr = await self.bot.prefix_manager.get_prefix(ctx.guild)
                em = ':tada:'
                if ctx.guild is not None and ctx.channel.permissions_for(ctx.guild.me).external_emojis:
                    em = '<:blurpletada:575696286905401345>'
                await ctx.bot.get_cog('Utilities').change_db_userinfo(ctx.author.id,'unlocked_blurple',True)
                await ctx.send(str(await self.bot._(ctx.channel,'blurple','won-card')).format(ctx.author.mention,pr[-1],em))

    @commands.command(aliases=['blurplfy', 'blurplefier'])
    @commands.cooldown(rate=3, per=90, type=BucketType.user)
    async def blurplefy(self,ctx, url = None):
        """Be even more cool, and blurpelize your avatar for this coolest birthday of the century.
        You can either give a user or an image URL in argument, or attach an image to your message. Plz don't forget to be cool."""
        await self.create(ctx,url)


    async def create(self,ctx,url):
        picture = None

        if url is not None:
            try:
                user = await commands.UserConverter().convert(ctx,url)
                picture = str(user.display_avatar)
            except Exception:
                picture = url
        else:
            link = ctx.message.attachments
            if len(link) != 0:
                for image in link:
                    picture = image.url

        if picture is None:
            picture = ctx.author.display_avatar

        try:
            async with aiohttp.ClientSession() as cs:
                async with cs.get(str(picture)) as r:
                    response = await r.read()
        except ValueError:
            await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_invalid")).format(ctx.message.author.mention))
            return


        try:
            im = Image.open(BytesIO(response))
        except Exception:
            await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_invalid")).format(ctx.message.author.mention))
            return

        imsize = list(im.size)
        impixels = imsize[0]*imsize[1]
        maxpixelcount = 1562500

        await ctx.send(str(await self.bot._(ctx.guild,"blurple","check_intro")).format(ctx.message.author.mention))

        try:
            _ = im.info["version"]
            isgif = True
            gifloop = int(im.info["loop"])
        except Exception:
            isgif = False

        if impixels > maxpixelcount:
            downsizefraction = math.sqrt(maxpixelcount/impixels)
            im = resizeimage.resize_width(im, (imsize[0]*downsizefraction))
            imsize = list(im.size)
            impixels = imsize[0]*imsize[1]

        def imager(im):
            im = im.convert(mode='RGBA')
            im = ImageEnhance.Contrast(im).enhance(1000)
            #im = ImageEnhance.Contrast(im).enhance(2.2)
            im = im.convert(mode='RGBA')

            img = im.load()
            for x in range(imsize[0]):
                for y in range(imsize[1]):
                    pixel = img[x, y]

                    if pixel[3] > 220:
                        if sum(pixel[:3])/3 > 222:
                            img[x,y] = WHITE
                        elif sum(pixel[:3])/3 > 100:
                            img[x,y] = BLURPLE
                        elif sum(pixel[:3])/3 > 0.01:
                            img[x,y] = DARK_BLURPLE
                        else:
                            img[x,y] = DARK
                    else:
                        img[x,y] = BLURPLE[:3]+tuple([pixel[3]])

            image_file_object = io.BytesIO()
            im.save(image_file_object, format='png')
            image_file_object.seek(0)
            return image_file_object

        def gifimager(im, _gifloop):
            frames = [frame.copy() for frame in ImageSequence.Iterator(im)]
            newgif = []

            for frame in frames:
                frame = frame.convert(mode='RGBA')
                frame = ImageEnhance.Contrast(frame).enhance(1.7)
                frame = frame.convert(mode='RGBA')

                img = frame.load()

                for x in range(imsize[0]):
                    for y in range(imsize[1]):
                        pixel = img[x, y]

                        if pixel[3] > 230:
                            if sum(pixel[:3])/3 > 222:
                                img[x,y] = WHITE
                            elif sum(pixel[:3])/3 > 100:
                                img[x,y] = BLURPLE
                            elif sum(pixel[:3])/3 > 0.01:
                                img[x,y] = DARK_BLURPLE
                            else:
                                img[x,y] = DARK
                        else:
                            img[x,y] = BLURPLE[:3]+tuple([pixel[3]])
                # for x in range(imsize[0]):
                #     for y in range(imsize[1]):
                #         pixel = img[x, y]

                #         if pixel != (255, 255, 255):
                #             img[x, y] = (114, 137, 218)

                newgif.append(frame)

            image_file_object = io.BytesIO()

            gif = newgif[0]
            gif.save(image_file_object, format='gif', save_all=True, append_images=newgif[1:], loop=0)

            image_file_object.seek(0)
            return image_file_object

        async with aiohttp.ClientSession() as _:
            if not isgif:
                image = await self.bot.loop.run_in_executor(None, imager, im)
            else:
                image = await self.bot.loop.run_in_executor(None, gifimager, im, gifloop)
            if not isgif:
                image = discord.File(fp=image, filename='image.png')
            else:
                image = discord.File(fp=image, filename='image.gif')
            try:
                fields_txt = await self.bot._(ctx.guild,"blurple","check_fields")
                embed = discord.Embed(title = "", colour = 0x7289DA, description=fields_txt[5])
                embed.set_author(name=await self.bot._(ctx.guild,'blurple','create_title'))
                if not isgif:
                    embed.set_image(url="attachment://image.png")
                    embed.set_footer(text=str(await self.bot._(ctx.guild,'blurple','create_footer_1')).format(ctx.author))
                else:
                    embed.set_image(url="attachment://image.gif")
                    embed.set_footer(text=str(await self.bot._(ctx.guild,'blurple','create_footer_2')).format(ctx.author))
                embed.set_thumbnail(url=picture)
                await ctx.send(embed=embed, file=image)
            except Exception:
                await ctx.send(str(await self.bot._(ctx.guild,'blurple','create_footer_2')).format(ctx.author.mention))

def setup(bot):
    bot.add_cog(BlurpleCog(bot))
