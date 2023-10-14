import io
import typing

import discord
from PIL import Image

from .utils import (ColorType, check_image_general, colorify_image,
                    convert_image_general, convert_image_with_background,
                    edge_detect, invert_colors, resized_img, shift_colors,
                    variations_filter)

DARK_BLURPLE = (69, 79, 191)
BLURPLE = (88, 101, 242)
WHITE = (255, 255, 255)
NOT_QUITE_BLACK = (35, 39, 42)


BlurpleVariationFlagType = typing.Literal["blurplefy", "edge-detect", "filter"]


def light(x: float) -> ColorType:
    return tuple(resized_img(x, i, DARK_BLURPLE, (0.641, 0.716, 1.262), WHITE) for i in range(3))


def dark(x: float) -> ColorType:
    return tuple(resized_img(x, i, NOT_QUITE_BLACK, (1.064, 1.074, 1.162), BLURPLE) for i in range(3))


MODIFIERS = {
    'light': {
        'func': light,
        'colors': [DARK_BLURPLE, BLURPLE, WHITE],
        'bg_colors': [WHITE, BLURPLE],
        'color_names': ['Dark Blurple', 'Blurple', 'White']
    },
    'dark': {
        'func': dark,
        'colors': [NOT_QUITE_BLACK, DARK_BLURPLE, BLURPLE],
        'bg_colors': [NOT_QUITE_BLACK, DARK_BLURPLE],
        'color_names': ['Not Quite Black', 'Dark Blurple', 'Blurple']
    },
    'all': {
        'colors': [NOT_QUITE_BLACK, DARK_BLURPLE, BLURPLE, WHITE],
        'color_names': ['Not Quite Black', 'Dark Blurple', 'Blurple', 'White']
    }

}
METHODS = {
    'blurplefy': colorify_image,
    'edge-detect': edge_detect,
    'filter': variations_filter
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
    'lightbg++white-bg': WHITE+(255,),
    'lightbg++blurple-bg': BLURPLE+(255,),
    'lightbg++dark-blurple-bg': DARK_BLURPLE+(255,),
    'darkbg++blurple-bg': BLURPLE+(255,),
    'darkbg++dark-blurple-bg': DARK_BLURPLE+(255,),
    'darkbg++not-quite-black-bg': NOT_QUITE_BLACK+(255,),
}


async def convert_image(image: bytes, modifier: str, method: str, selected_variations: list[str], replace_background: bool):
    "Change an image colors into orange-black colors by using given modifier, method and variations"
    if image == b'':
        raise RuntimeError("Invalid image")
    base_color_var = (.15, .3, .7, .85)
    with Image.open(io.BytesIO(image)) as img:
        if replace_background:
            io_out = await convert_image_with_background(
                image, modifier, method, selected_variations,
                MODIFIERS, base_color_var, METHODS, VARIATIONS
            )
        else:
            io_out = await convert_image_general(
                image, modifier, method, selected_variations,
                MODIFIERS, base_color_var, METHODS, VARIATIONS
            )
        if img.format == "GIF":
            filename = f'{modifier}.gif'
        else:
            filename = f'{modifier}.png'
    return discord.File(io_out, filename=filename)


async def check_image(image: bytes):
    "Check if an image has enough of the event colors, and return the analyse data"
    if image == b'':
        raise RuntimeError('Invalid image')
    colors_refs: list[tuple[int, int, int]] = MODIFIERS["all"]["colors"]
    colors_names: list[tuple[int, int, int]] = MODIFIERS["all"]["color_names"]

    data = await check_image_general(image, colors_refs, colors_names)
    for color in data["colors"]:
        if color['name'] == "Non-Color":
            color['name'] = "Not-Blurple"
    return data
