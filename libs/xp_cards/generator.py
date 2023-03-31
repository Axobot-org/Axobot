from PIL import Image, ImageDraw, ImageFont

from libs.xp_cards.card_types import CardData, RgbColor, TextData
from libs.xp_cards.cards_metadata import get_card_data

CARD_SIZE = (1021, 340)


def paste_avatar(avatar: Image.Image, dest: Image.Image, position: tuple[int, int]):
    """Paste the avatar onto the destination image"""
    mask = Image.open("./assets/card-models/mask_1_pfp.png")
    mask = mask.resize(CARD_SIZE, resample=Image.Resampling.LANCZOS)
    mask = mask.crop(mask.getbbox())
    avatar = avatar.resize(mask.size, resample=Image.Resampling.LANCZOS)
    dest.paste(avatar, position, mask=mask)

def add_text(dest: Image.Image, texts: dict[str, TextData]):
    """Add text to the destination image"""
    for text, data in texts.items():
        alignment = data['alignment']
        rect = data['position']
        font_name = "./assets/fonts/" + data['font']
        font_size = data['font_size']
        color = data['color']
        fonts_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        # Find idea font size
        while True:
            if (font_name, font_size) in fonts_cache:
                font = fonts_cache[(font_name, font_size)]
            else:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                except OSError:
                    raise ValueError(f"Font {font_name} not found") from None
                fonts_cache[(font_name, font_size)] = font
            # Measure the size of the text when rendered with the current font
            text_box = font.getbbox(text)
            text_width, text_height = text_box[2] - text_box[0], text_box[3] - text_box[1]
            # If the text fits within the rectangle, we're done
            if text_width <= (rect[1][0] - rect[0][0]) and text_height <= (rect[1][1] - rect[0][1]):
                break
            # Otherwise, reduce the font size and try again
            font_size = round(font_size*0.8)
        h_pos = round(rect[0][1] + (rect[1][1] - rect[0][1] - text_height)/2)
        if alignment == 'left':
            pos = rect[0][0], h_pos
        elif alignment == 'right':
            w_pow = rect[1][0] - text_width
            pos = w_pow, h_pos
        elif alignment == 'center':
            w_pow = round(rect[0][0] + (rect[1][0] - rect[0][0])/2 - text_width/2)
            pos = w_pow, h_pos
        else:
            continue
        draw = ImageDraw.Draw(dest)
        draw.text(pos, text, color, font=font, anchor="lt")


def draw_xp_bar_1(dest: Image.Image, full_bar_color: RgbColor, xp_percent: float):
    "Replace gray pixels in the xp bar with the full_bar_color"
    right_border = (967-302)*xp_percent + 302
    mask = Image.open("./assets/card-models/mask_1_xp_bar.png")
    mask = mask.crop((0, 0, round(right_border), 340))
    dest.paste(full_bar_color, mask=mask)
    return dest

def draw_xp_bar_2(dest: Image.Image, full_bar_color: RgbColor, xp_percent: float):
    "Replace gray pixels in the xp bar with the full_bar_color"
    # Bar starts at 29 and ends at 992
    right_border = (992-29)*xp_percent + 29
    mask = Image.open("./assets/card-models/mask_2_xp_bar.png")
    mask = mask.crop((0, 0, round(right_border), 340))
    dest.paste(full_bar_color, mask=mask)
    return dest

def draw_card(avatar: Image.Image, data: CardData):
    "Do the magic"
    background_img = Image.open("./assets/card-models/" + data['type'] + ".png").resize(CARD_SIZE)

    paste_avatar(avatar, background_img, data['avatar_position'])
    add_text(background_img, data['texts'])
    if data['xp_bar_type'] == 1:
        background_img = draw_xp_bar_1(background_img, data['xp_bar_color'], data['xp_percent'])
    else:
        background_img = draw_xp_bar_2(background_img, data["xp_bar_color"], data['xp_percent'])

    return background_img


def main():
    "Try it and see"
    try:
        data = get_card_data(
            card_name='christmas',
            translation_map={},  # Not used in this example
            username='Z_runner',
            level=1,
            rank=4,
            participants=12,
            current_xp=128,
            xp_to_next_level=355,
            total_xp=1364
        )
    except ValueError:
        print("Error: invalid card style")
        return
    background_img = draw_card("avatar.png", data)
    background_img.save("result-method2.png")

if __name__ == "__main__":
    main()
