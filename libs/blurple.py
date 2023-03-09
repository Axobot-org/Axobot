# -*- coding: utf-8 -*-

import io
import math

import discord
from PIL import Image, ImageSequence


# source: https://dev.to/enzoftware/how-to-build-amazing-image-filters-with-python-median-filter---sobel-filter---5h7
def edge_antialiasing(img):
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


def place_edges(img, edge_img, modifiers):
    edge_img_minimum = 10
    edge_img_maximum = edge_img.crop().getextrema()[0][1]
    for x in range(1, img.width - 1):
        for y in range(1, img.height - 1):
            p = img.getpixel((x, y))
            ep = edge_img.getpixel((x, y))
            if (ep[0] > edge_img_minimum):
                img.putpixel((x, y), edge_colorify((ep[0] - edge_img_minimum) / (edge_img_maximum - edge_img_minimum),
                                                   modifiers['colors'], p))
    return img


def f(x, n, d, m, l):
    return round(((l[n] - d[n]) / 255) * (255 ** m[n] - (255 - x) ** m[n]) ** (1 / m[n]) + d[n])


def light(x):
    return tuple(f(x, i, (78, 93, 148), (0.641, 0.716, 1.262), (255, 255, 255)) for i in range(3))


def dark(x):
    return tuple(f(x, i, (35, 39, 42), (1.064, 1.074, 1.162), (114, 137, 218)) for i in range(3))


def edge_detect(img, modifier, variation, maximum, minimum):
    img = img.convert('RGBA')
    edge_img = edge_antialiasing(img)
    img = blurplefy(img, modifier, variation, maximum, minimum)
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


def colorify(x, colors, variation):
    return tuple(f2(x, i, colors, variation) for i in range(3))


def edge_colorify(x, colors, cur_color):
    return tuple(f3(x, i, colors, cur_color) for i in range(3))


def remove_alpha(img, bg):
    alpha = img.convert('RGBA').getchannel('A')
    background = Image.new("RGBA", img.size, bg)
    background.paste(img, mask=alpha)
    return background


def blurple_filter(img, modifier, variation, maximum, minimum):
    img = img.convert('LA')
    pixels = img.getdata()
    img = img.convert('RGBA')
    results = [modifier['func']((x - minimum) * 255 / (255 - minimum)) if x >= minimum else 0 for x in range(256)]

    img.putdata((*map(lambda x: results[x[0]] + (x[1],), pixels),))
    return img


def blurplefy(img, modifier, variation, maximum, minimum):
    img = img.convert('LA')
    pixels = img.getdata()
    img = img.convert('RGBA')
    results = [colorify((x - minimum) / (maximum - minimum), modifier['colors'], variation) if x >= minimum else 0 for x
               in range(256)]
    img.putdata((*map(lambda x: results[x[0]] + (x[1],), pixels),))
    return img


def variation_maker(base, var):
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


def invert_colors(colors):
    return list(reversed(colors))


def shift_colors(colors):
    return [colors[2], colors[0], colors[1]]


def interpolate_colors(color1, color2, x):
    new_color = [0, 0, 0]
    for i in range(3):
        new_color[i] = round((color2[i] - color1[i]) * x + color1[i])
    return tuple(new_color)


def distance_to_color(color1, color2):
    total = 0
    for i in range(3):
        total += (255 - abs(color1[i] - color2[i])) / 255
    return total / 3


def find_max_index(array):
    maximum = 0
    closest = None
    for i in range(len(array)):
        if array[i] > maximum:
            maximum = array[i]
            closest = i
    return closest


def color_ratios(img, colors):
    img = img.convert('RGBA')
    total_pixels = img.width * img.height
    color_pixels = [0, 0, 0, 0]
    close_colors = []
    for i in range(3):
        close_colors.append(interpolate_colors(colors[i], colors[min(i + 1, 2)], .33))
        close_colors.append(interpolate_colors(colors[i], colors[max(i - 1, 0)], .33))

    for x in range(0, img.width):
        for y in range(0, img.height):
            p = img.getpixel((x, y))
            if p[3] == 0:
                total_pixels -= 1
                continue
            values = [0, 0, 0]
            for i in range(3):
                values[i] = max(
                    distance_to_color(p, colors[i]),
                    distance_to_color(p, close_colors[2 * i]),
                    distance_to_color(p, close_colors[2 * i + 1])
                )
            index = find_max_index(values)
            if values[index] > .93:
                color_pixels[index] += 1
            else:
                color_pixels[3] += 1

    percent = [0, 0, 0, 0]
    for i in range(4):
        percent[i] = color_pixels[i] / total_pixels
    return percent


MODIFIERS = {
    'light': {
        'func': light,
        'colors': [(78, 93, 148), (114, 137, 218), (255, 255, 255)],
        'color_names': ['Dark Blurple', 'Blurple', 'White']
    },
    'dark': {
        'func': dark,
        'colors': [(35, 39, 42), (78, 93, 148), (114, 137, 218)],
        'color_names': ['Not Quite Black', 'Dark Blurple', 'Blurple']
    }

}
METHODS = {
    '--blurplefy': blurplefy,
    '--edge-detect': edge_detect,
    '--filter': blurple_filter
}
VARIATIONS = {
    None: (0, 0, 0, 0),
    'light++more-white': (0, 0, -.05, -.05),
    'light++more-blurple': (-.05, -.05, .05, .05),
    'light++more-dark-blurple': (.05, .05, 0, 0),
    'dark++more-blurple': (0, 0, -.05, -.05),
    'dark++more-dark-blurple': (-.05, -.05, .05, .05),
    'dark++more-not-quite-black': (.05, .05, 0, 0),
    'light++less-white': (0, 0, .05, .05),
    'light++less-blurple': (.05, .05, -.05, -.05),
    'light++less-dark-blurple': (-.05, -.05, 0, 0),
    'dark++less-blurple': (0, 0, .05, .05),
    'dark++less-dark-blurple': (.05, .05, -.05, -.05),
    'dark++less-not-quite-black': (-.05, -.05, 0, 0),
    'light++no-white': (0, 0, 500, 500),
    'light++no-blurple': (0, 500, -500, 0),
    'light++no-dark-blurple': (-500, -500, 0, 0),
    'dark++no-blurple': (0, 0, 500, 500),
    'dark++no-dark-blurple': (0, 500, -500, 0),
    'dark++no-not-quite-black': (-500, -500, 0, 0),
    '++classic': (.15, -.15, .15, -.15),
    '++less-gradient': (.05, -.05, .05, -.05),
    '++more-gradient': (-.05, .05, -.05, .05),
    '++invert': invert_colors,
    '++shift': shift_colors,
    'lightbg++white-bg': (255, 255, 255, 255),
    'lightbg++blurple-bg': (114, 137, 218, 255),
    'lightbg++dark-blurple-bg': (78, 93, 148, 255),
    'darkbg++blurple-bg': (114, 137, 218, 255),
    'darkbg++dark-blurple-bg': (78, 93, 148, 255),
    'darkbg++not-quite-black-bg': (35, 39, 42, 255),
}


async def convert_image(image, modifier, method, variations):
    try:
        modifier_converter = dict(MODIFIERS[modifier])
    except KeyError:
        raise RuntimeError('Invalid image modifier.')

    try:
        method_converter = METHODS[method]
    except KeyError:
        raise RuntimeError('Invalid image method.')

    if image == b'':
        raise RuntimeError('Invalid image')

    variations.sort()
    background_color = None
    base_color_var = (.15, .3, .7, .85)
    for var in variations:
        try:
            variation_converter = VARIATIONS[var]
        except KeyError:
            try:
                variation_converter = VARIATIONS[modifier + var]
            except KeyError:
                try:
                    variation_converter = VARIATIONS[modifier + 'bg' + var]
                    background_color = variation_converter
                    continue
                except KeyError:
                    raise RuntimeError('Invalid image variation.')
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
            except TypeError as e:
                print(e)
                raise RuntimeError('Invalid GIF.')

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


async def check_image(image, modifier, method):
    try:
        modifier_converter = MODIFIERS[modifier]
    except KeyError:
        raise RuntimeError('Invalid image modifier.')

    with Image.open(io.BytesIO(image)) as img:
        if img.format == "GIF":
            total = [0, 0, 0, 0]
            count = 0

            for frame in ImageSequence.Iterator(img):
                f = frame.resize((round(img.width / 3), round(img.height / 3)))
                values = color_ratios(f, modifier_converter['colors'])
                for i in range(4):
                    total[i] += values[i]
                count += 1

            ratios = [0, 0, 0, 0]
            for i in range(4):
                ratios[i] = round(10000 * total[i] / count) / 100

            passed = ratios[3] <= 10

        else:
            img = img.resize((round(img.width / 3), round(img.height / 3)))
            values = color_ratios(img, modifier_converter['colors'])

            ratios = [0, 0, 0, 0]
            for i in range(4):
                ratios[i] = round(10000 * values[i]) / 100

            passed = ratios[3] <= 10

    colors = []
    for i in range(3):
        colors.append({
            'name': modifier_converter['color_names'][i],
            'ratio': ratios[i]
        })
    colors.append({
        'name': 'Non-Blurple',
        'ratio': ratios[3]
    })
    data = {
        'passed': passed,
        'colors': colors
    }
    return data
