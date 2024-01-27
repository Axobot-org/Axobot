import datetime

from asyncache import cached
from cachetools import Cache
from PIL import Image, ImageDraw, ImageFont

CARD_SIZE = (1000, 400)
AVATAR_SIZE = 256
AVATAR_POSITION = (35, 65)
QUOTE_FONT_SIZE = 50
QUOTE_RECT = ((330, 90), (950, 250))
AUTHOR_FONT_SIZE = 25
AUTHOR_RECT = ((350, 270), (930, 310))

class QuoteGeneration:
    "Generate a quote card from a message"

    def __init__(self, text: str, author_name: str, avatar: Image.Image, date: datetime.datetime):
        self.text = text
        self.author_name = author_name
        self.avatar = avatar
        self.date = date
        self.fonts_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        self.result = Image.new('RGBA', CARD_SIZE, (15, 0, 11, 255))
        self.last_quote_line_bottomheight = QUOTE_RECT[1][1]

    def _paste_avatar(self):
        "Paste the avatar onto the destination image"
        if self.avatar.size != (AVATAR_SIZE, AVATAR_SIZE):
            self.avatar = self.avatar.resize((AVATAR_SIZE, AVATAR_SIZE), resample=Image.Resampling.LANCZOS)
        mask_im = Image.new("L", self.avatar.size, 0)
        draw = ImageDraw.Draw(mask_im)
        draw.ellipse((0, 0, AVATAR_SIZE, AVATAR_SIZE), fill=255)
        self.result.paste(self.avatar, AVATAR_POSITION, mask_im)

    @cached(Cache(maxsize=1_000))
    def _find_max_text_size(self, text: str, rect: tuple[tuple[int, int], tuple[int, int]], font_name: str, font_size: str):
        while True:
            if (font_name, font_size) in self.fonts_cache:
                font = self.fonts_cache[(font_name, font_size)]
            else:
                try:
                    font = ImageFont.truetype(font_name, font_size)
                except OSError:
                    raise ValueError(f"Font {font_name} not found") from None
                self.fonts_cache[(font_name, font_size)] = font
            # Measure the size of the text when rendered with the current font
            text_box = font.getbbox(text)
            text_width, text_height = text_box[2] - text_box[0], text_box[3] - text_box[1]
            # If the text fits within the rectangle, we're done
            if text_width <= (rect[1][0] - rect[0][0]) and text_height <= (rect[1][1] - rect[0][1]):
                break
            # Otherwise, reduce the font size and try again
            font_size = round(font_size*0.8)
        return font, font_size

    def _generate_quote_text(self):
        text = '“' + self.text + '”'
        # calculate optimal font size
        font, _ = self._find_max_text_size(text, QUOTE_RECT, "Roboto-Medium.ttf", font_size=QUOTE_FONT_SIZE)
        print("quote", _)
        # calculate centered position
        h_pos = round(QUOTE_RECT[0][1] + (QUOTE_RECT[1][1] - QUOTE_RECT[0][1])/2)
        w_pow = round(QUOTE_RECT[0][0] + (QUOTE_RECT[1][0] - QUOTE_RECT[0][0])/2)
        pos = w_pow, h_pos
        # get text bottom bounding box (to align author text later)
        text_bbox = font.getbbox(text)
        text_height = text_bbox[3] - text_bbox[1]
        self.last_quote_line_bottomheight = h_pos + round(text_height/2)
        # return the result
        return [{
            "xy": pos,
            "text": text,
            "fill": (200, 200, 220),
            "font": font,
            "anchor": "mm",
        }]

    def _generate_author_text(self):
        date = self.date.strftime("%Y-%m-%d")
        text = f"@{self.author_name} — {date}"
        print(self.last_quote_line_bottomheight)
        rect = ((AUTHOR_RECT[0][0], self.last_quote_line_bottomheight), AUTHOR_RECT[1])
        font, _ = self._find_max_text_size(text, rect, "Roboto-Medium.ttf", font_size=AUTHOR_FONT_SIZE)
        print("author", _)
        h_pos = round(rect[0][1] + (rect[1][1] - rect[0][1])/2)
        pos = rect[1][0], h_pos
        return {
            "xy": pos,
            "text": text,
            "fill": (200, 200, 220),
            "font": font,
            "anchor": "rm",
        }

    def _add_texts(self):
        "Add text to the destination image"
        quote_text_lines = self._generate_quote_text()
        author_text = self._generate_author_text()
        draw = ImageDraw.Draw(self.result)
        for line in quote_text_lines:
            draw.text(**line)
        draw.text(**author_text)

    def draw_card(self):
        "Do the magic"
        self._paste_avatar()
        self._add_texts()
        return self.result
