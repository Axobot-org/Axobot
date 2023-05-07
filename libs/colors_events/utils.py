import asyncio
import io
import math
from typing import Annotated, Any, Callable, Optional, TypedDict, Union

import discord
from discord.ext import commands
from PIL import Image, ImageSequence

from libs.bot_classes import MyContext

ColorType = tuple[int, int, int]
ColorAlphaType = tuple[int, int, int, int]
VariationType = tuple[float, float, float, float]

class LinkConverter(str):
    "Represents a media link"

    @classmethod
    async def convert(cls, ctx: MyContext, argument: str):
        "Convert an argument into a media link, by using Discord CDN proxy and embed system"
        if not argument.startswith('https://'):
            raise commands.errors.BadArgument(f'Could not convert "{argument}" into URL')
        if argument.startswith('https://cdn.discordapp.com/attachments/'):
            return argument

        for _ in range(10):
            if ctx.message.embeds and ctx.message.embeds[0].thumbnail:
                return ctx.message.embeds[0].thumbnail.proxy_url

            await asyncio.sleep(1)

        raise commands.errors.BadArgument('Discord proxy image did not load in time.')

class TargetConverter:
    "Represents a target usable for color conversion"

    @classmethod
    async def convert(cls, ctx: MyContext, argument: str):
        "Convert an argument into a Discord Member, PartialEmoji, or to a media link"
        try:
            return await commands.MemberConverter().convert(ctx, argument)
        except commands.errors.BadArgument:
            pass

        try:
            return await commands.PartialEmojiConverter().convert(ctx, argument)
        except commands.errors.BadArgument:
            pass

        return await LinkConverter().convert(ctx, argument)

TargetConverterType = Annotated[Union[discord.Member, discord.PartialEmoji, LinkConverter], TargetConverter]

class ColorVariation(str):
    "Represents a usable color variation for color conversion algorithm"

    @classmethod
    async def convert(cls, _ctx: MyContext, argument: str):
        "Convert an argument into a color variation"
        if not argument.startswith('++'):
            raise commands.errors.BadArgument('Not a valid flag!')
        return argument

async def get_url_from_ctx(ctx: MyContext, who: Optional[TargetConverterType]):
    "Get the resource URL from either the who argument or the context"
    if ctx.message.attachments:
        url = ctx.message.attachments[0].proxy_url
    elif who is None:
        url = ctx.author.display_avatar.url
    else:
        if isinstance(who, str):  # LinkConverter
            url = who
        elif isinstance(who, discord.PartialEmoji):
            url = who.url
        else:
            url = who.display_avatar.url
    return url


# source: https://dev.to/enzoftware/how-to-build-amazing-image-filters-with-python-median-filter---sobel-filter---5h7
def edge_antialiasing(img: Image.Image):
    new_img = Image.new("RGB", img.size, "black")
    for x in range(1, img.width - 1):  # ignore the edge pixels for simplicity (1 to width-1)
        for y in range(1, img.height - 1):  # ignore edge pixels for simplicity (1 to height-1)

            # initialise Gx to 0 and Gy to 0 for every pixel
            Gx = 0
            Gy = 0

            # top left pixel
            p = img.getpixel((x - 1, y - 1))
            r = p[0]
            g = p[1]
            b = p[2]

            # intensity ranges from 0 to 765 (255 * 3)
            intensity = r + g + b

            # accumulate the value into Gx, and Gy
            Gx += -intensity
            Gy += -intensity

            # remaining left column
            p = img.getpixel((x - 1, y))
            r = p[0]
            g = p[1]
            b = p[2]

            Gx += -2 * (r + g + b)

            p = img.getpixel((x - 1, y + 1))
            r = p[0]
            g = p[1]
            b = p[2]

            Gx += -(r + g + b)
            Gy += (r + g + b)

            # middle pixels
            p = img.getpixel((x, y - 1))
            r = p[0]
            g = p[1]
            b = p[2]

            Gy += -2 * (r + g + b)

            p = img.getpixel((x, y + 1))
            r = p[0]
            g = p[1]
            b = p[2]

            Gy += 2 * (r + g + b)

            # right column
            p = img.getpixel((x + 1, y - 1))
            r = p[0]
            g = p[1]
            b = p[2]

            Gx += (r + g + b)
            Gy += -(r + g + b)

            p = img.getpixel((x + 1, y))
            r = p[0]
            g = p[1]
            b = p[2]

            Gx += 2 * (r + g + b)

            p = img.getpixel((x + 1, y + 1))
            r = p[0]
            g = p[1]
            b = p[2]

            Gx += (r + g + b)
            Gy += (r + g + b)

            # calculate the length of the gradient (Pythagorean theorem)
            length = math.sqrt((Gx * Gx) + (Gy * Gy))

            # normalise the length of gradient to the range 0 to 255
            length = length / 4328 * 255

            length = int(length)

            # draw the length in the edge image
            new_img.putpixel((x, y), (length, length, length))
    return new_img


def place_edges(img: Image.Image, edge_img: Image.Image, modifier: dict[str, Any]):
    edge_img_minimum = 10
    edge_img_maximum = edge_img.crop().getextrema()[0][1]
    for x in range(1, img.width - 1):
        for y in range(1, img.height - 1):
            p = img.getpixel((x, y))
            ep = edge_img.getpixel((x, y))
            if (ep[0] > edge_img_minimum):
                img.putpixel((x, y), edge_colorify((ep[0] - edge_img_minimum) / (edge_img_maximum - edge_img_minimum),
                                                   modifier['colors'], p))
    return img


def resized_img(x: float, n: int, d: ColorType, m: tuple[float, float, float], l: ColorType):
    return round(((l[n] - d[n]) / 255) * (255 ** m[n] - (255 - x) ** m[n]) ** (1 / m[n]) + d[n])

def edge_detect(img: Image.Image, modifier: dict[str, Any], variation: VariationType, maximum: int, minimum: int):
    img = img.convert('RGBA')
    edge_img = edge_antialiasing(img)
    img = colorify_image(img, modifier, variation, maximum, minimum)
    new_img = place_edges(img, edge_img, modifier)
    return new_img


def interpolate(color1, color2, percent):
    return round((color2 - color1) * percent + color1)


def f2(x, n, colors, variation):
    if x < variation[0]:
        return colors[0][n]
    elif x < variation[1]:
        if variation[0] == variation[2]:
            return interpolate(colors[0][n], colors[2][n], (x - variation[0]) / (variation[1] - variation[0]))
        else:
            return interpolate(colors[0][n], colors[1][n], (x - variation[0]) / (variation[1] - variation[0]))
    elif x < variation[2]:
        return colors[1][n]
    elif x < variation[3]:
        return interpolate(colors[1][n], colors[2][n], (x - variation[2]) / (variation[3] - variation[2]))
    else:
        return colors[2][n]


def f3(x, n, colors, cur_color):
    array = []

    for i in range(len(colors)):
        array.append(distance_to_color(colors[i], cur_color))

    closest_color = find_max_index(array)
    if closest_color == 0:
        return interpolate(colors[0][n], colors[1][n], x)
    elif closest_color == 1:
        return interpolate(colors[1][n], colors[2][n], x)
    else:
        return interpolate(colors[2][n], colors[1][n], x)


def _colorify(x, colors, variation):
    return tuple(f2(x, i, colors, variation) for i in range(3))


def edge_colorify(x, colors, cur_color):
    return tuple(f3(x, i, colors, cur_color) for i in range(3))


def remove_alpha(img: Image.Image, bg: ColorType):
    alpha = img.convert('RGBA').getchannel('A')
    background = Image.new("RGBA", img.size, bg)
    background.paste(img, mask=alpha)
    return background

def variations_filter(img: Image.Image, modifier: dict[str, Any], _variation: VariationType, _maximum: int, minimum: int):
    img = img.convert('LA')
    pixels = img.getdata()
    img = img.convert('RGBA')
    results = [modifier['func']((x - minimum) * 255 / (255 - minimum)) if x >= minimum else 0 for x in range(256)]

    img.putdata((*map(lambda x: results[x[0]] + (x[1],), pixels),))
    return img

def colorify_image(img: Image.Image, modifier: dict[str, Any], variation: VariationType, maximum: int, minimum: int):
    img = img.convert('LA')
    pixels = img.getdata()
    img = img.convert('RGBA')
    results = [
        _colorify((x - minimum) / (maximum - minimum), modifier['colors'], variation)
        if x >= minimum
        else 0
        for x in range(256)
    ]
    img.putdata((*map(lambda x: results[x[0]] + (x[1],), pixels),))
    return img

def variation_maker(base: VariationType, var: VariationType):
    if var[0] <= -100:
        base1 = base2 = 0
        base3 = (base[2] + base[0]) / 2 * .75
        base4 = (base[3] + base[1]) / 2 * 1.5
    elif var[1] >= 100:
        base2 = base4 = (base[1] + base[3]) / 2 * 1.5
        base1 = base3 = (base[0] + base[2]) / 2 * .75
    elif var[3] >= 100:
        base3 = base4 = 1
        base1 = (base[0] + base[2]) / 2 * .75
        base2 = (base[1] + base[3]) / 2 * 1.5
    else:
        base1 = max(min(base[0] + var[0], 1), 0)
        base2 = max(min(base[1] + var[1], 1), 0)
        base3 = max(min(base[2] + var[2], 1), 0)
        base4 = max(min(base[3] + var[3], 1), 0)
    return base1, base2, base3, base4


def invert_colors(colors: list[ColorType]):
    return list(reversed(colors))


def shift_colors(colors: list[ColorType]):
    return [colors[2], colors[0], colors[1]]


def interpolate_colors(color1: ColorType, color2: ColorType, ratio: float) -> ColorType:
    "Get a mix between two colors, based on the given ratio"
    new_color = [0, 0, 0]
    for i in range(3):
        new_color[i] = round((color2[i] - color1[i]) * ratio + color1[i])
    return tuple(new_color)


def distance_to_color(color1: ColorType, color2: ColorType):
    "Calculate the distance between two colors, on a RGB base"
    total = 0
    for i in range(3):
        total += (255 - abs(color1[i] - color2[i])) / 255
    return total / 3

def find_max_index(array: list[float]):
    "Find the index of the maximum value in an array"
    maximum = 0
    closest = None
    for i, value in enumerate(array):
        if value > maximum:
            maximum = value
            closest = i
    return closest

def color_ratios(img: Image.Image, colors: list[ColorType]):
    "Calculate the ratio of present colors in the given image (between 0.0 and 1.0)"
    img = img.convert('RGBA')
    total_pixels = img.width * img.height # number of pixels in the image
    color_pixels = [0 for _ in range(len(colors)+1)] # count number of pixels close to each color
    close_colors = []
    for i, color in enumerate(colors):
        close_colors.append(interpolate_colors(color, colors[min(i + 1, len(colors)-1)], 1/len(colors)))
        close_colors.append(interpolate_colors(color, colors[max(i - 1, 0)], 1/len(colors)))

    for x in range(0, img.width):
        for y in range(0, img.height):
            p = img.getpixel((x, y))
            if p[3] == 0:
                total_pixels -= 1
                continue
            values = [0 for _ in range(len(colors))]
            for i, color in enumerate(colors):
                values[i] = max(
                    distance_to_color(p, color),
                    distance_to_color(p, close_colors[2 * i]),
                    distance_to_color(p, close_colors[2 * i + 1])
                )
            index = find_max_index(values)
            if values[index] > .93:
                color_pixels[index] += 1
            else:
                color_pixels[-1] += 1

    percent: list[float] = []
    for i, count in enumerate(color_pixels):
        percent.append(count / total_pixels)
    return percent


async def convert_image_general(image: Image.Image, modifier: str, method: str, selected_variations: list[str],
                        modifiers: dict[str, dict], base_color_var: VariationType, methods: dict[str, Callable],
                        variations: dict[str, VariationType]):
    "Change an image colors into orange-black colors by using given modifier, method and variations"
    try:
        modifier_converter = dict(modifiers[modifier])
    except KeyError:
        raise RuntimeError('Invalid image modifier', modifier) from None

    try:
        method_converter = methods[method]
    except KeyError:
        raise RuntimeError('Invalid image method', method) from None

    if image == b'':
        raise RuntimeError('Invalid image')

    selected_variations.sort()
    background_color = None
    variation_converter = (0, 0, 0, 0)
    for var in selected_variations:
        try:
            variation_converter = variations[var]
        except KeyError:
            try:
                variation_converter = variations[modifier + var]
            except KeyError:
                try:
                    variation_converter = variations[modifier + 'bg' + var]
                    background_color = variation_converter
                    continue
                except KeyError:
                    raise RuntimeError('Invalid image variation') from None
        if not isinstance(variation_converter, tuple):
            modifier_converter['colors'] = variation_converter(modifier_converter['colors'])
        elif method != "--filter":
            base_color_var = variation_maker(base_color_var, variation_converter)
    if method != "--filter":
        variation_converter = base_color_var

    with Image.open(io.BytesIO(image)) as img:
        if img.format == "GIF":
            frames = []
            durations = []
            try:
                loop = img.info['loop']
            except KeyError:
                loop = None

            minimum = 256
            maximum = 0

            for img_frame in ImageSequence.Iterator(img):
                frame = img_frame.convert('LA')

                if frame.getextrema()[0][0] < minimum:
                    minimum = frame.getextrema()[0][0]

                if frame.getextrema()[0][1] > maximum:
                    maximum = frame.getextrema()[0][1]

            for frame in ImageSequence.Iterator(img):
                new_frame = method_converter(frame, modifier_converter, variation_converter, maximum, minimum)
                if background_color is not None:
                    new_frame = remove_alpha(new_frame, background_color)

                durations.append(frame.info.get('duration',100))
                frames.append(new_frame)

            out = io.BytesIO()
            try:
                frames[0].save(out, format='GIF', append_images=frames[1:], save_all=True, loop=loop,
                               duration=durations)
            except TypeError as err:
                print(err)
                raise RuntimeError('Invalid GIF') from None

            filename = f'{modifier}.gif'

        else:
            img = img.convert('LA')

            minimum = img.getextrema()[0][0]
            maximum = img.getextrema()[0][1]

            img = method_converter(img, modifier_converter, variation_converter, maximum, minimum)
            if background_color is not None:
                img = remove_alpha(img, background_color)
            out = io.BytesIO()
            img.save(out, format='png')
            filename = f'{modifier}.png'

    out.seek(0)
    return discord.File(out, filename=filename)


class CheckResultColor(TypedDict):
    name: str
    ratio: float

class CheckResult(TypedDict):
    passed: bool
    colors: list[CheckResultColor]

async def check_image_general(image: Image.Image, colors_refs: list[ColorType], colors_names: list[ColorType]) -> CheckResult:
    "Check if an image has enough of the event colors, and return the analyse data"
    with Image.open(io.BytesIO(image)) as img:
        if img.format == "GIF":
            total = [0, 0, 0, 0, 0]
            count = 0

            for frame in ImageSequence.Iterator(img):
                resized = frame.resize((round(img.width / 3), round(img.height / 3)))
                values = color_ratios(resized, colors_refs)
                for i, value in enumerate(values):
                    total[i] += value
                count += 1

            ratios = [0 for _ in range(len(total))]
            for i, value_color in enumerate(total):
                ratios[i] = round(100 * value_color / count, 2)

            passed = ratios[-1] <= 10

        else:
            img = img.resize((round(img.width / 3), round(img.height / 3)))
            values = color_ratios(img, colors_refs)

            ratios = [0 for _ in range(len(values))]
            for i, value_color in enumerate(values):
                ratios[i] = round(100 * value_color, 2)

            passed = ratios[-1] <= 10

    colors = []
    for name, ratio in zip(colors_names, ratios):
        colors.append({
            'name': name,
            'ratio': ratio
        })
    colors.append({
        'name': 'Non-Color',
        'ratio': ratios[-1]
    })
    data = {
        'passed': passed,
        'colors': colors
    }
    return data
