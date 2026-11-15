#!/usr/bin/env python3
"""Render Traditional Chinese statute text as image-only PDFs, the shape of a scan.

Every page is drawn from known text, so the text is the ground truth byte for
byte, the way scripts/dev/build_corpus.py builds the DACH pages. The output is a
directory of PDFs plus a truth file in the format findling.extract.ocr_quality
reads ({"documents": [{"name", "variant", "pages"}]}).

A variant is a font and a treatment:

* fonts: Noto Serif CJK TC (Ming, the body face of printed matter), Noto Sans
  CJK TC (Hei), AR PL UKai TW (Kai, the face of most Taiwanese official letters)
* treatments: clean (300 dpi raster, lossless), scan (rotated 0.6 degrees,
  blurred, noise, JPEG quality 70), fax (drawn at 200 dpi, bilevel)

The truth is the text as drawn, line breaks included; the measurement collapses
whitespace before comparing, as ocr_quality does.

The PDFs carry fixed dates, so the same fonts, Pillow and FreeType give the
same bytes, and the manifest it writes lists the sha256 of every page.

Run inside the image of Dockerfile.messung (stage measure), where the fonts are
installed; <laws dir> holds one text file per article as zh_corpus.py of
docs/measurements/2026-11-zh-kette writes them:

    python zh_ocr_pages.py <laws dir> <out dir>
"""

# The test prose and the closing punctuation below are Chinese on purpose, full
# width colons, commas and parentheses included.
# ruff: noqa: RUF001

from __future__ import annotations

import hashlib
import io
import json
import random
import sys
import time
import unicodedata
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = {
    "ming": ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", "Noto Serif CJK TC"),
    "hei": ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "Noto Sans CJK TC"),
    "kai": ("/usr/share/fonts/truetype/arphic/ukai.ttc", "AR PL UKai TW"),
}

# The date every PDF carries, instead of the moment it was written.
FIXED_DATE = time.strptime("2026-11-15", "%Y-%m-%d")

# A4 at the resolution the page is drawn at; 12 pt body text.
A4_INCHES = (8.27, 11.69)
POINT = 12
LINE_FACTOR = 1.6
MARGIN_INCHES = 0.9

# The page texts: the laws and article ranges that go on each page, chosen for
# variety (definitions, enumerations, numbers, the U+FE30 colon of article 9).
PAGES = (
    ("J0070017", range(9, 16)),  # Copyright Act, from article 8 until the page is full
    ("N0030001", range(30, 37)),  # Labor Standards Act, wages
    ("I0050021", range(2, 9)),  # Personal Data Protection Act, definitions
    ("B0000001", range(1, 9)),  # Civil Code, general principles
    ("G0340003", range(2, 7)),  # Income Tax Act
    ("C0000001", range(1, 8)),  # Criminal Code
)

# One self written page mixing Chinese with Latin words, digits and an address,
# the shape of a modern office letter rather than a statute. Test prose, no
# user data.
MIXED = (
    "Nextcloud 伺服器維護通知\n"
    "各位同仁好：資訊室預定於 2026 年 11 月 21 日（星期六）上午 9 時至 12 時，"
    "將檔案伺服器升級至 Nextcloud 34，並啟用 Findling 全文檢索。"
    "升級期間無法登入 https://cloud.example.org ，請提前下載工作所需的 PDF、DOCX 與 ODT 檔案。"
    "升級完成後，掃描的公文影像也能以關鍵字搜尋，例如輸入「採購契約」或「112 年度預算」即可找到內容。"
    "若有問題，請洽分機 2345 或寄信至 it-help@example.org 。"
    "此外，舊版 WebDAV 連線設定（含 Windows 網路磁碟機）不需要變更；"
    "行動裝置的 Nextcloud App 請更新至 4.0 以上版本。"
    "本次異動不影響臺北、台中、高雄三地辦公室的共用資料夾權限。\n"
    "資訊室 敬啟"
)


def _font(name: str, pixels: int) -> ImageFont.FreeTypeFont:
    """The face of the given family out of its collection, by name, never by index guess."""
    path, family = FONTS[name]
    for index in range(16):
        try:
            font = ImageFont.truetype(path, pixels, index=index)
        except OSError:
            break
        if font.getname()[0] == family:
            return font
    message = f"family {family} not in {path}"
    raise SystemExit(message)


def _width(font: ImageFont.FreeTypeFont, text: str) -> float:
    return font.getlength(text)


def _wrap(text: str, font: ImageFont.FreeTypeFont, width: float) -> list[str]:
    """Break each paragraph into lines that fit, character by character (CJK has no spaces).

    A Latin run is kept together when it fits on a line of its own, so a URL is
    not broken in the middle where a reader would not break it either.
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        pieces: list[str] = []
        run = ""
        for char in paragraph:
            if char.isascii() and not char.isspace():
                run += char
                continue
            if run:
                pieces.append(run)
                run = ""
            pieces.append(char)
        if run:
            pieces.append(run)
        line = ""
        for piece in pieces:
            if _width(font, line + piece) <= width:
                line += piece
                continue
            # Keep closing punctuation on the line it closes, the way CJK layout does.
            if piece in "，。、；：︰」）！？" and line:
                line += piece
                continue
            lines.append(line.rstrip())
            line = piece.lstrip()
        if line:
            lines.append(line.rstrip())
    return lines


def _glyph_bitmap(font: ImageFont.FreeTypeFont, char: str) -> bytes:
    size = round(font.size * 2)
    tile = Image.new("L", (size, size), color=255)
    ImageDraw.Draw(tile).text((size // 8, size // 8), char, font=font, fill=0)
    return tile.tobytes()


def _missing_glyphs(font: ImageFont.FreeTypeFont, text: str) -> set[str]:
    """Characters the face would draw as its missing glyph, or as nothing.

    The check of scripts/dev/build_corpus.py: U+E000 lies in the private use
    area and no sane face maps it, so its bitmap is the shape of "missing". A
    pixel count alone would not do, because the missing glyph is a box and a
    box has pixels.
    """
    missing_shape = _glyph_bitmap(font, chr(0xE000))
    blank = _glyph_bitmap(font, " ")
    missing: set[str] = set()
    for char in set(text):
        if char.isspace() or unicodedata.category(char).startswith("C"):
            continue
        if _glyph_bitmap(font, char) in (missing_shape, blank):
            missing.add(char)
    return missing


def _draw(text: str, font_name: str, dpi: int) -> tuple[Image.Image, str]:
    """One page at the given resolution, and the text as it was laid out."""
    size = (round(A4_INCHES[0] * dpi), round(A4_INCHES[1] * dpi))
    pixels = round(POINT / 72 * dpi)
    font = _font(font_name, pixels)
    missing = _missing_glyphs(font, text)
    if missing:
        message = f"{font_name} lacks {''.join(sorted(missing))}"
        raise SystemExit(message)
    margin = round(MARGIN_INCHES * dpi)
    lines = _wrap(text, font, size[0] - 2 * margin)
    step = round(pixels * LINE_FACTOR)
    room = (size[1] - 2 * margin) // step
    lines = lines[:room]
    image = Image.new("L", size, color=255)
    draw = ImageDraw.Draw(image)
    for number, line in enumerate(lines):
        draw.text((margin, margin + number * step), line, fill=0, font=font)
    return image, "\n".join(lines)


def _scan(image: Image.Image, seed: int) -> Image.Image:
    """A flatbed scan, roughly: a small skew, soft focus, sensor noise, JPEG."""
    rng = random.Random(seed)  # noqa: S311 - noise for a test page, not a secret
    skewed = image.rotate(0.6, resample=Image.Resampling.BICUBIC, expand=False, fillcolor=255)
    soft = skewed.filter(ImageFilter.GaussianBlur(radius=1.1))
    # Uniform noise from a seeded generator, so the page is the same on every run.
    field = Image.frombytes("L", soft.size, rng.randbytes(soft.size[0] * soft.size[1]))
    noisy = Image.blend(soft, field, 0.15)
    buffer = io.BytesIO()
    noisy.save(buffer, format="JPEG", quality=70)
    return Image.open(io.BytesIO(buffer.getvalue())).convert("L")


def _fax(text: str, font_name: str) -> tuple[Image.Image, str]:
    """Drawn at 200 dpi and thresholded to black and white, the resolution of a fax."""
    image, laid_out = _draw(text, font_name, 200)
    return image.point(lambda value: 0 if value < 160 else 255).convert("1"), laid_out


def _page_text(laws: Path, pcode: str, articles: range) -> str:
    parts = []
    for number in articles:
        path = laws / f"{pcode}-{number:04d}.txt"
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8").strip())
    return "\n".join(parts)


def _pdf(image: Image.Image, dpi: int) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PDF", resolution=dpi, creationDate=FIXED_DATE, modDate=FIXED_DATE)
    return buffer.getvalue()


def main(laws: Path, out: Path) -> None:
    # The positive control of the glyph check, on every face: Cherokee letter A
    # (U+13A0) is in none of the three, so a check that does not report it
    # could not report anything. A private use character would not do, the
    # check skips the control and private use categories by design.
    for font_name in FONTS:
        control = chr(0x13A0)
        if _missing_glyphs(_font(font_name, 50), control) != {control}:
            message = f"the glyph check does not see a missing glyph on {font_name}"
            raise SystemExit(message)
    out.mkdir(parents=True, exist_ok=True)
    texts = [(f"{pcode}", _page_text(laws, pcode, articles)) for pcode, articles in PAGES]
    texts.append(("mixed", MIXED))
    documents = []
    manifest = []
    for font_name in FONTS:
        for treatment in ("clean", "scan", "fax"):
            for number, (label, text) in enumerate(texts):
                if treatment == "fax":
                    image, laid_out = _fax(text, font_name)
                    dpi = 200
                else:
                    image, laid_out = _draw(text, font_name, 300)
                    dpi = 300
                    if treatment == "scan":
                        image = _scan(image, seed=number)
                data = _pdf(image, dpi)
                name = f"{font_name}-{treatment}-{number:02d}-{label}.pdf"
                (out / name).write_bytes(data)
                documents.append({"name": name, "variant": f"{font_name}-{treatment}", "pages": [laid_out]})
                manifest.append(f"{name}\t{len(laid_out)}\t{hashlib.sha256(data).hexdigest()}")
    documents.sort(key=lambda entry: entry["name"])
    truth = json.dumps({"documents": documents}, ensure_ascii=False, indent=1)
    (out / "truth.json").write_text(truth, encoding="utf-8")
    (out / "manifest.txt").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    for path, family in FONTS.values():
        print(f"font\t{family}\t{hashlib.sha256(Path(path).read_bytes()).hexdigest()}")
    print(f"pages\t{len(documents)}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
