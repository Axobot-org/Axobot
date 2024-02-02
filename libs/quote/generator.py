import datetime
import math
from typing import Literal

from PIL import Image, ImageDraw, ImageFont

QuoteStyle = Literal["modern", "classic"]

CARD_SIZE = (1000, 400)
CARD_OUTER_COLOR = (8, 0, 7, 255)
CARD_INNER_COLOR = (23, 0, 20, 255)
AVATAR_SIZE = 256
AVATAR_POSITION = (35, 65)
QUOTE_FONT_SIZE = 50
QUOTE_RECT = ((330, 90), (950, 270))
QUOTE_LINE_SPACING = 12
AUTHOR_FONT_SIZE = 25
AUTHOR_RECT = ((350, 290), (930, 310))
MIN_FONT_SIZE = 17
WATERMARK_SIZE = (85, 15)
WATERMARK_POSITION = (CARD_SIZE[0] - WATERMARK_SIZE[0] - 20, CARD_SIZE[1] - WATERMARK_SIZE[1] - 20)

class QuoteGeneration:
    "Generate a quote card from a message"

    def __init__(self, text: str, author_name: str, avatar: Image.Image, date: datetime.datetime,
                 style: QuoteStyle = "classic"):
        self.text = text
        self.author_name = author_name
        self.avatar = avatar
        self.date = date
        self.style = style
        if self.style == "modern":
            self.max_characters_per_line = 60
            self.quote_font_name = "./assets/fonts/Roboto-Medium.ttf"
            self.author_font_name = "./assets/fonts/RobotoSlab-Regular.ttf"
        else:
            self.max_characters_per_line = 75
            self.quote_font_name = "./assets/fonts/DancingScript-Medium.ttf"
            self.author_font_name = "./assets/fonts/Metropolis-Thin.otf"
        self.fonts_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        with open("./assets/images/quote_background.png", "rb") as f:
            self.result = Image.open(f).convert("RGBA")
        self.last_quote_line_bottomheight = QUOTE_RECT[1][1]

    def _generate_background_gradient(self):
        "Edit the background to add a round gradient"
        imgsize = self.result.size
        for y in range(imgsize[1]):
            for x in range(imgsize[0]):
                # Find the distance to the center
                distance = math.sqrt((x - imgsize[0]/2) ** 2 + (y - imgsize[1]/2) ** 2)
                # Make it on a scale from 0 to 1
                distance = float(distance) / (math.sqrt(2) * imgsize[0]/2)
                # Calculate rgb values
                r = CARD_OUTER_COLOR[0] * distance + CARD_INNER_COLOR[0] * (1 - distance)
                g = CARD_OUTER_COLOR[1] * distance + CARD_INNER_COLOR[1] * (1 - distance)
                b = CARD_OUTER_COLOR[2] * distance + CARD_INNER_COLOR[2] * (1 - distance)
                # Place the pixel
                self.result.putpixel((x, y), (int(r), int(g), int(b), 255))

    def _avatar_transform_classic_style(self):
        "Apply a grayscale and an opacity gradient to the avatar"
        avatar = self.avatar.convert("L")
        gradient = Image.new('L', (AVATAR_SIZE, AVATAR_SIZE), 0)
        draw = ImageDraw.Draw(gradient)
        for i in range(AVATAR_SIZE):
            alpha = round((AVATAR_SIZE - i) ** 0.9)
            draw.line((0, i, AVATAR_SIZE, i), fill=alpha)
        gradient = gradient.rotate(-30)
        avatar.putalpha(gradient)
        return avatar

    def _paste_avatar(self):
        "Paste the avatar onto the destination image"
        # resize avatar if needed
        if self.avatar.size != (AVATAR_SIZE, AVATAR_SIZE):
            self.avatar = self.avatar.resize((AVATAR_SIZE, AVATAR_SIZE), resample=Image.Resampling.LANCZOS)
        # convert avatar to RGBA if needed
        if self.avatar.mode != "RGBA":
            self.avatar = self.avatar.convert("RGBA")
        # apply avatar style
        if self.style == "classic":
            avatar = self._avatar_transform_classic_style()
        else:
            avatar = self.avatar
        # create a mask to crop the avatar into a circle
        mask_im = Image.new("L", avatar.size, 0)
        draw = ImageDraw.Draw(mask_im)
        draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        # apply the mask to a copy of the avatar (to avoid issues with transparency)
        avatar_with_mask = Image.new('RGBA', avatar.size, (0, 0, 0, 0))
        avatar_with_mask.paste(avatar, mask=mask_im)
        # paste the avatar onto the destination image
        self.result.paste(avatar_with_mask, AVATAR_POSITION, avatar_with_mask)

    def _paste_watermark(self):
        "Paste the watermark onto the destination image, in the bottom right corner"
        watermark = Image.open("./assets/images/axobot_gray.png")
        watermark = watermark.resize(WATERMARK_SIZE, resample=Image.Resampling.LANCZOS)
        self.result.paste(watermark, WATERMARK_POSITION, watermark)

    def _find_max_text_size(self, text: str, rect: tuple[tuple[int, int], tuple[int, int]], font_name: str, font_size: str):
        draw = ImageDraw.Draw(self.result)
        while True:
            if (font_name, font_size) in self.fonts_cache:
                font = self.fonts_cache[(font_name, font_size)]
            else:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                except OSError:
                    raise ValueError(f"Font {font_name} not found") from None
                self.fonts_cache[(font_name, font_size)] = font
            # If font size is too small, abort
                if font_size < MIN_FONT_SIZE:
                    break
            # Measure the size of the text when rendered with the current font
            text_box = draw.multiline_textbbox((0, 0), text, font=font, spacing=QUOTE_LINE_SPACING)
            text_width, text_height = text_box[2] - text_box[0], text_box[3] - text_box[1]
            # If the text fits within the rectangle, we're done
            if text_width <= (rect[1][0] - rect[0][0]) and text_height <= (rect[1][1] - rect[0][1]):
                break
            # Otherwise, reduce the font size and try again
            font_size = round(font_size*0.8)
        return font

    def _split_text(self, text: str):
        """Split the text into multiple lines of max MAX_CHARACTERS_PER_LINE characters
        The method also takes into account existing lines break"""
        lines: list[list[str]] = []
        line: list[str] = []
        for word in text.split(' '):
            if '\n' in word:
                word, *rest = word.split('\n', 1)
                if word:
                    line.append(word)
                lines.append(line)
                line = rest
                continue
            new_line = ' '.join(line + [word])
            if len(new_line) > self.max_characters_per_line:
                lines.append(line)
                line = [word]
            else:
                line.append(word)
        if line:
            lines.append(line)
        return '\n'.join(' '.join(line) for line in lines if line)

    def _generate_quote_text(self):
        text = self._split_text('“' + self.text.strip() + '”')
        # calculate optimal font size
        font = self._find_max_text_size(text, QUOTE_RECT, self.quote_font_name, font_size=QUOTE_FONT_SIZE)
        # calculate centered position
        h_pos = round(QUOTE_RECT[0][1] + (QUOTE_RECT[1][1] - QUOTE_RECT[0][1])/2)
        w_pow = round(QUOTE_RECT[0][0] + (QUOTE_RECT[1][0] - QUOTE_RECT[0][0])/2)
        pos = w_pow, h_pos
        # get text bottom bounding box (to align author text later)
        text_bbox = font.getbbox(text)
        text_height = text_bbox[3] - text_bbox[1]
        if (lines_count := text.count("\n")) > 0:
            text_height += (text_bbox[3] + QUOTE_LINE_SPACING) * lines_count
        self.last_quote_line_bottomheight = h_pos + round(text_height/2)
        # return the result
        return {
            "xy": pos,
            "text": text,
            "fill": (230, 230, 250),
            "font": font,
            "anchor": "mm",
            "spacing": QUOTE_LINE_SPACING,
        }

    def _generate_author_text(self):
        date = self.date.strftime("%Y-%m-%d")
        text = f"@{self.author_name} — {date}"
        # calculate box height based on quote text height
        rect = ((AUTHOR_RECT[0][0], self.last_quote_line_bottomheight), AUTHOR_RECT[1])
        # calculate optimal font size
        font = self._find_max_text_size(text, rect, self.author_font_name, font_size=AUTHOR_FONT_SIZE)
        # calculate right-aligned position
        h_pos = round(rect[0][1] + (rect[1][1] - rect[0][1])/2)
        pos = rect[1][0], h_pos
        # return the result
        return {
            "xy": pos,
            "text": text,
            "fill": (205, 200, 208),
            "font": font,
            "anchor": "rm",
        }

    def _add_texts(self):
        "Add text to the destination image"
        quote_text = self._generate_quote_text()
        author_text = self._generate_author_text()
        draw = ImageDraw.Draw(self.result)
        draw.multiline_text(**quote_text)
        draw.text(**author_text)

    def draw_card(self):
        "Do the magic"
        # self._generate_background_gradient()
        self._paste_avatar()
        # self._paste_watermark()
        self._add_texts()
        return self.result
