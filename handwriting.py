from PIL import Image, ImageDraw, ImageFont
import textwrap
import os

from networkx import draw


def generate_handwritten_notes(text, output_folder, filename):

    os.makedirs(output_folder, exist_ok=True)

    font = ImageFont.truetype(
        "static/fonts/Caveat-Regular.ttf",
        42
    )

    lines = textwrap.wrap(text, width=42)

    page = 1
    line_index = 0

    while line_index < len(lines):

        image = Image.new("RGB", (1240, 1754), "white")
        draw = ImageDraw.Draw(image)
       # Draw red margin
        draw.line(
            (120, 60, 120, 1690),
            fill=(255, 70, 70),
            width=3
        )

        x = 150
        y = 82

        while y < 1650 and line_index < len(lines):

    # Draw notebook line for this text
            draw.line(
                (80, y + 42, 1160, y + 42),
                fill=(180, 210, 255),
                width=2
            )

            draw.text(
                (x, y),
                lines[line_index],
                fill=(20, 20, 120),
                font=font
            )

            y += 52
            line_index += 1

        image.save(
            os.path.join(
                output_folder,
                f"{filename}_page{page}.png"
            )
        )

        page += 1