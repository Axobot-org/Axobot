from PIL import Image, ImageDraw

def main():
    # get a 1021x340 image
    img = Image.new('RGB', (20, 20), color=(255, 255, 255))
    # draw a rounded rectangle on it
    draw = ImageDraw.Draw(img)
    coordinates = (
        (5, 0),
        (15, 7)
    )
    # here's the bug:
    # on ImageDraw.py line 383, y1 from "left" will be 1px less than y0
    draw.rounded_rectangle(coordinates, radius=3, fill=(0, 0, 0))

if __name__ == '__main__':
    main()
