from typing import TYPE_CHECKING
from PIL import Image, ImageDraw, ImageFilter
from rembg import new_session, remove

if TYPE_CHECKING:
    from libs.colors_events.utils import ColorType


async def get_background_mask(image: Image.Image) -> Image.Image:
    "Detect the image background and return the corresponding mask"
    return remove(
        image,
        session=new_session("u2netp"),
        alpha_matting=True,
        only_mask=True
    )

async def apply_gradient(image: Image.Image, mask: Image.Image, inner_color: "ColorType", outer_color: "ColorType"):
    "Apply a gradient to the image background"
    inner_color_hex = "#%02x%02x%02x" % inner_color
    outer_color_hex = "#%02x%02x%02x" % outer_color
    width, height = image.size
    gradient = Image.new("RGBA", (width, height), color=0)
    gradient_draw = ImageDraw.Draw(gradient)
    gradient_draw.ellipse((0, 0, width, height), fill=inner_color_hex, outline=outer_color_hex, width=width//12)
    gradient = gradient.filter(ImageFilter.GaussianBlur(radius=width//4))
    return Image.composite(image, gradient, mask)
