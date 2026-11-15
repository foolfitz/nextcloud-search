#!/usr/bin/env python3
"""One page of vertical Traditional Chinese, read with the horizontal and the vertical model.

The text is the Han characters of articles 8 to 11 of the Copyright Act from
the statute corpus (the files 0009 to 0013, 10-1 included), drawn in columns from top to bottom and from right to left
in Noto Serif CJK TC at 12 pt and 300 dpi, the way a vertically set book or an
older official document runs. The page goes to tesseract in the call form of
findling.extract.ocr, with its fixed --psm 3, once per language list.

Per list: Han characters drawn and read, the character error rate over the Han
characters alone, and the share of the distinct runs of four Han characters
(as the body_zh chain tokenises them) that come back as consecutive tokens.
One page, so these are an indication and not a rate.

    PYTHONPATH=backend/src python zh_ocr_vertical.py <laws dir>
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from findling.extract.ocr import read_page
from findling.extract.ocr_quality import edit_distance
from findling.index.analyzer import chinese_analyzer

HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc"
FAMILY = "Noto Serif CJK TC"
DPI = 300
PIXELS = 50  # 12 pt at 300 dpi
MARGIN = 270
COLUMN_STEP = 80  # 1.6 times the glyph size, as in the horizontal pages
MAX_CHARACTERS = 600
LISTS = ("chi_tra", "chi_tra_vert", "chi_tra+chi_tra_vert", "chi_tra_vert+chi_tra")


def _font() -> ImageFont.FreeTypeFont:
    for index in range(16):
        font = ImageFont.truetype(FONT_PATH, PIXELS, index=index)
        if font.getname()[0] == FAMILY:
            return font
    message = f"{FAMILY} not found"
    raise SystemExit(message)


def _page(laws: Path) -> tuple[bytes, str]:
    """The vertical page as PNG bytes, and the Han characters it carries, in reading order."""
    text = "".join(
        (laws / f"J0070017-{number:04d}.txt").read_text(encoding="utf-8").split("\n", 1)[1] for number in range(9, 14)
    )
    han = "".join(HAN.findall(text))[:MAX_CHARACTERS]
    width, height = round(8.27 * DPI), round(11.69 * DPI)
    per_column = (height - 2 * MARGIN) // PIXELS
    image = Image.new("L", (width, height), color=255)
    draw = ImageDraw.Draw(image)
    font = _font()
    x = width - MARGIN - PIXELS
    drawn = ""
    start = 0
    while start < len(han) and x > MARGIN:
        column = han[start : start + per_column]
        for row, char in enumerate(column):
            draw.text((x, MARGIN + row * PIXELS), char, fill=0, font=font)
        drawn += column
        start += per_column
        x -= COLUMN_STEP
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(DPI, DPI))
    return buffer.getvalue(), drawn


def _runs(text: str, n: int) -> set[tuple[str, ...]]:
    """The runs of n consecutive tokens that are all Han, as zh_ocr_measure.py counts them.

    The window goes over every token and a run counts only when all of its
    tokens are Han, so a Latin token the engine put between two characters
    breaks the run, as it breaks a phrase query.
    """
    tokens = chinese_analyzer().analyze(text)
    found: set[tuple[str, ...]] = set()
    for start in range(len(tokens) - n + 1):
        window = tuple(tokens[start : start + n])
        if all(HAN.fullmatch(token) for token in window):
            found.add(window)
    return found


def main(laws: Path) -> None:
    png, drawn = _page(laws)
    wanted = _runs(drawn, 4)
    print("languages\than_drawn\than_read\tcer_han\trecall4")
    for languages in LISTS:
        reading = read_page(png, languages, 120)
        read_han = "".join(HAN.findall(reading))
        rate = edit_distance(drawn, read_han) / len(drawn)
        recall = len(wanted & _runs(reading, 4)) / len(wanted)
        print(f"{languages}\t{len(drawn)}\t{len(read_han)}\t{rate:.4f}\t{recall:.4f}")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
