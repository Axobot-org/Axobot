from cachingutils import cached
from PIL import Image, ImageDraw, ImageFont, ImageSequence

from libs.xp_cards.cards_metadata import get_card_data

CARD_SIZE = (1021, 340)


class CardGeneration:
    "Generate a card from a card type and a user avatar"

    def __init__(self, card_name: str,
                 translation_map: dict[str, str],
                 username: str,
                 avatar: Image.Image,
                 level: int,
                 rank: int,
                 participants: int,
                 xp_to_current_level: int,
                 xp_to_next_level: int,
                 total_xp: int):
        self.card_name = card_name
        self.avatar = avatar
        self.data = get_card_data(card_name, translation_map, username,
                                  level, rank, participants, xp_to_current_level, xp_to_next_level, total_xp)
        if self.avatar.format == "GIF":
            self.skip_second_frames = self.avatar.n_frames > 60 and self.avatar.info['duration'] < 30
            self.result = [
                Image.new('RGBA', CARD_SIZE, (255, 255, 255, 0))
                for i in range(self.avatar.n_frames)
                if not self.skip_second_frames or i%2==0
            ]
        else:
            self.result = Image.new('RGBA', CARD_SIZE, (255, 255, 255, 0))
            self.skip_second_frames = False


    def _paste_avatar(self):
        """Paste the avatar onto the destination image"""
        should_resize = self.avatar.size != self.data["avatar_size"]
        avatar_iterator = ImageSequence.Iterator(self.avatar)
        if isinstance(self.result, list):
            for i, result_frame in enumerate(self.result):
                avatar_frame = next(avatar_iterator)
                if self.skip_second_frames and i%2 == 1:
                    avatar_frame = next(avatar_iterator)
                if should_resize:
                    avatar_frame = avatar_frame.resize(self.data["avatar_size"], resample=Image.Resampling.LANCZOS)
                result_frame.paste(avatar_frame, self.data["avatar_position"])
        else:
            if should_resize:
                self.avatar = self.avatar.resize(self.data["avatar_size"], resample=Image.Resampling.LANCZOS)
            self.result.paste(self.avatar, self.data["avatar_position"])

    @cached(include_posargs=[0, 1, 3, 4])
    def _find_max_text_size(self, text: str, rect: tuple[tuple[int, int], tuple[int, int]], font_name: str, font_size: str):
        fonts_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
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
        return font, font_size

    def _add_text(self):
        """Add text to the destination image"""
        rendered_texts = []
        for data in self.data["texts"].values():
            text = data['label']
            alignment = data['alignment']
            rect = data['position']
            font_name = "./assets/fonts/" + data['font']
            font_size = data['font_size']
            color = data['color']
            # Find idea font size
            font, font_size = self._find_max_text_size(text, rect, font_name, font_size)
            h_pos = round(rect[0][1] + (rect[1][1] - rect[0][1])/2)
            if alignment == 'left':
                pos = rect[0][0], h_pos
                anchor = "lm"
            elif alignment == 'right':
                pos = rect[1][0], h_pos
                anchor = "rm"
            elif alignment == 'center':
                w_pow = round(rect[0][0] + (rect[1][0] - rect[0][0])/2)
                pos = w_pow, h_pos
                anchor = "mm"
            else:
                continue
            rendered_texts.append({
                "xy": pos,
                "text": text,
                "fill": color,
                "font": font,
                "anchor": anchor,
            })
        if isinstance(self.result, list):
            for frame in self.result:
                draw = ImageDraw.Draw(frame)
                for text in rendered_texts:
                    draw.text(**text)
        else:
            draw = ImageDraw.Draw(self.result)
            for text in rendered_texts:
                draw.text(**text)

    def _draw_xp_bar(self):
        "Place the xp bar on the card"
        min_width = 28
        bar_pos_1, bar_pos_2 = self.data["xp_bar_position"]
        bar_x = bar_pos_1[0]
        bar_y = bar_pos_1[1]
        max_width = bar_pos_2[0] - bar_pos_1[0]
        width = max(min_width, round(max_width*self.data["xp_percent"]))
        height = bar_pos_2[1] - bar_pos_1[1]
        radius = min(width, height) // 2
        if isinstance(self.result, list):
            for frame in self.result:
                draw = ImageDraw.Draw(frame)
                draw.rounded_rectangle(
                    ((bar_x, bar_y), (bar_x + width, bar_y + height)),
                    radius,
                    fill=self.data['xp_bar_color']
                )
        else:
            draw = ImageDraw.Draw(self.result)
            draw.rounded_rectangle(
                ((bar_x, bar_y), (bar_x + width, bar_y + height)),
                radius,
                fill=self.data['xp_bar_color']
            )

    def draw_card(self):
        "Do the magic"
        background_img = Image.open("./assets/card-models/" + self.data['type'] + ".png").resize(CARD_SIZE)

        self._paste_avatar()
        if isinstance(self.result, list):
            for frame in self.result:
                frame.paste(background_img, (0, 0), background_img)
        else:
            self.result.paste(background_img, (0, 0), background_img)
        self._add_text()
        self._draw_xp_bar()

        return self.result


def main():
    "Try it and see"
    try:
        generator = CardGeneration(
            card_name='christmas',
            translation_map={},  # Not used in this example
            username='Z_runner',
            avatar=Image.open("avatar.png"),
            level=1,
            rank=4,
            participants=12,
            xp_to_current_level=128,
            xp_to_next_level=355,
            total_xp=1364
        )
    except ValueError:
        print("Error: invalid card style")
        return
    background_img = generator.draw_card()
    if isinstance(background_img, list):
        background_img[0].save("result-method2.gif", save_all=True, append_images=background_img[1:])
    else:
        background_img.save("result-method2.png")

if __name__ == "__main__":
    main()
