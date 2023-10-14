import io
import typing

import discord
from PIL import Image

from .utils import (ColorType, check_image_general, colorify_image,
                    convert_image_general, convert_image_with_background,
                    edge_detect, invert_colors, resized_img, shift_colors,
                    variations_filter)

DARK_ORANGE = (205, 100, 10)
ORANGE = (255, 140, 26)
WHITE = (255, 255, 255)
NOT_QUITE_BLACK = (35, 39, 42)


HalloweenVariationFlagType = typing.Literal["hallowify", "edge-detect", "filter"]


def light(x: float) -> ColorType:
    return tuple(resized_img(x, i, DARK_ORANGE, (1.2, 0.75, 0.42), WHITE) for i in range(3))


def dark(x: float) -> ColorType:
    return tuple(resized_img(x, i, NOT_QUITE_BLACK, (1.2, 1.07, 1.04), ORANGE) for i in range(3))



MODIFIERS = {
    'light': {
        'func': light,
        'colors': [DARK_ORANGE, ORANGE, WHITE],
        'bg_colors': [WHITE, ORANGE],
        'color_names': ['Dark Orange', 'Orange', 'White']
    },
    'dark': {
        'func': dark,
        'colors': [NOT_QUITE_BLACK, DARK_ORANGE, ORANGE],
        'bg_colors': [NOT_QUITE_BLACK, DARK_ORANGE],
        'color_names': ['Not Quite Black', 'Dark Orange', 'Orange']
    },
    'all': {
        'colors': [NOT_QUITE_BLACK, DARK_ORANGE, ORANGE, WHITE],
        'color_names': ['Not Quite Black', 'Dark Orange', 'Orange', 'White']
    }
}
METHODS = {
    'hallowify': colorify_image,
    'edge-detect': edge_detect,
    'filter': variations_filter
}
VARIATIONS = {
    None: (0, 0, 0, 0),
    'light++more-white': (0, 0, -.05, -.05),
    'light++more-halloween': (-.05, -.05, .05, .05),
    'light++more-dark-halloween': (.05, .05, 0, 0),
    'dark++more-halloween': (0, 0, -.05, -.05),
    'dark++more-dark-halloween': (-.05, -.05, .05, .05),
    'dark++more-not-quite-black': (.05, .05, 0, 0),
    'light++less-white': (0, 0, .05, .05),
    'light++less-halloween': (.05, .05, -.05, -.05),
    'light++less-dark-halloween': (-.05, -.05, 0, 0),
    'dark++less-halloween': (0, 0, .05, .05),
    'dark++less-dark-halloween': (.05, .05, -.05, -.05),
    'dark++less-not-quite-black': (-.05, -.05, 0, 0),
    'light++no-white': (0, 0, 500, 500),
    'light++no-halloween': (0, 500, -500, 0),
    'light++no-dark-halloween': (-500, -500, 0, 0),
    'dark++no-halloween': (0, 0, 500, 500),
    'dark++no-dark-halloween': (0, 500, -500, 0),
    'dark++no-not-quite-black': (-500, -500, 0, 0),
    '++classic': (.15, -.15, .15, -.15),
    '++less-gradient': (.05, -.05, .05, -.05),
    '++more-gradient': (-.05, .05, -.05, .05),
    '++invert': invert_colors,
    '++shift': shift_colors,
    'lightbg++white-bg': WHITE+(255,),
    'lightbg++halloween-bg': ORANGE+(255,),
    'lightbg++dark-halloween-bg': DARK_ORANGE+(255,),
    'darkbg++halloween-bg': ORANGE+(255,),
    'darkbg++dark-halloween-bg': DARK_ORANGE+(255,),
    'darkbg++not-quite-black-bg': NOT_QUITE_BLACK+(255,),
}


async def convert_image(image: bytes, modifier: str, method: str, selected_variations: list[str], replace_background: bool):
    "Change an image colors into orange-black colors by using given modifier, method and variations"
    if image == b'':
        raise RuntimeError('Invalid image')
    base_color_var = (.7, .42, .14, .85)
    with Image.open(io.BytesIO(image)) as img:
        if replace_background:
            io_out = await convert_image_with_background(
                img, modifier, method, selected_variations,
                MODIFIERS, base_color_var, METHODS, VARIATIONS
            )
        else:
            io_out = await convert_image_general(
                img, modifier, method, selected_variations,
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
            color['name'] = "Not-Halloween"
    return data
