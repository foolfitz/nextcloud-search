#!/usr/bin/env python3
"""Draw the Traditional Chinese strip that the image probe of chi_tra reads.

``backend/tests/probe_image_ocr_chinese.py`` proves in the built image that the
Tesseract model ``chi_tra`` reads Traditional Chinese, the way
``probe_image_ocr_czech.py`` proves it for ``ces``. The Czech probe draws its
sentence at run time with DejaVu Sans out of ``testdata/fonts``, and that face
has no Han glyph. So the Chinese strip is drawn once, here, and committed as
``testdata/ocr-zh/probe-zh-tw.png``; the probe reads the file and draws only the
white control page itself.

**Why a picture and not a font.** A face with Han glyphs weighs 20 MB or more,
and a subset of one is a modified font under the SIL Open Font License 1.1, with
the renaming and licence obligations that come with it, for one CI step. The
picture carries none of that. The licence of the face says so in its fifth
condition: "The requirement for fonts to remain under this license does not
apply to any document created using the Font Software." (Debian
``/usr/share/doc/fonts-noto-cjk/copyright``). The face never enters the product
image or a dependency list: it is installed in a throwaway container of the
pinned base image, for the length of one run of this script.

**What is drawn, exactly.**

* the sentence ``SENTENCE`` below, self written test prose, no user data;
* in Noto Serif CJK TC Regular out of ``NotoSerifCJK-Regular.ttc`` of Debian
  ``fonts-noto-cjk`` 1:20240730+repack1-1, sha256 ``FONT_SHA256``, picked out
  of the collection by its family name and refused if the file has moved by one
  byte;
* 56 pixels high on a white strip of 2000 x 300 pixels, at (80, 110), the
  geometry of the Czech probe, which is about 13 pt at 300 dpi;
* grey levels (mode L), saved as PNG with 300 dpi in its header.

The result on 2026-11-15, in the base image
``python:3.13-slim-trixie@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a``
with Pillow 13.0.0 of ``backend/uv.lock``: ``PNG_SHA256``, written twice with
the same bytes. ``--check`` draws it again and compares it with the committed
file instead of writing.

Run it from the repository root:

    docker run --rm -v "$PWD:/repo" -w /repo \\
        python:3.13-slim-trixie@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a \\
        sh -c 'apt-get update -qq && apt-get install -y -qq --no-install-recommends \\
                   fonts-noto-cjk=1:20240730+repack1-1 >/dev/null \\
               && pip install -q pillow==13.0.0 \\
               && python scripts/dev/build_zh_ocr_probe.py --check'
"""

from __future__ import annotations

import hashlib
import io
import sys
from pathlib import Path
from typing import Final

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT: Final = Path(__file__).resolve().parents[2]
TARGET: Final = REPO_ROOT / "testdata" / "ocr-zh" / "probe-zh-tw.png"

FONT_PATH: Final = Path("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc")
FONT_FAMILY: Final = "Noto Serif CJK TC"
FONT_SHA256: Final = "5d9c31a059600193c9d7968a998bde886ccdc77e934006ad243b41794c496a7d"
PNG_SHA256: Final = "aba61bb4e62a9a6c771b8bbc9dfb0c1bde16d030a521eb18c98d84d7f2f73d18"

# Traditional forms on purpose: 會議記錄, 掃描, 檔案, 臺北, 辦公室 and 搜尋 are
# written 会议记录, 扫描, 档案, 台北, 办公室 and 搜寻 in Simplified Chinese, so a
# reading that carries them came out of a Traditional model.
SENTENCE: Final = "會議記錄已掃描成檔案，臺北辦公室可全文搜尋"  # noqa: RUF001 - a Chinese comma, on purpose

FONT_PIXELS: Final = 56
WIDTH: Final = 2000
HEIGHT: Final = 300
ORIGIN: Final = (80, 110)
DPI: Final = 300


def _font() -> ImageFont.FreeTypeFont:
    """The pinned face, out of its collection by name, refused if the file moved."""
    payload = FONT_PATH.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != FONT_SHA256:
        message = f"{FONT_PATH} is not the pinned font: expected {FONT_SHA256}, found {digest}"
        raise SystemExit(message)
    for index in range(16):
        font = ImageFont.truetype(io.BytesIO(payload), FONT_PIXELS, index=index)
        if font.getname()[0] == FONT_FAMILY:
            return font
    message = f"{FONT_FAMILY} is not in {FONT_PATH}"
    raise SystemExit(message)


def _glyph_bitmap(font: ImageFont.FreeTypeFont, character: str) -> bytes:
    tile = Image.new("L", (FONT_PIXELS * 2, FONT_PIXELS * 2), color=255)
    ImageDraw.Draw(tile).text((FONT_PIXELS // 4, FONT_PIXELS // 4), character, font=font, fill=0)
    return tile.tobytes()


def _assert_every_glyph_exists(font: ImageFont.FreeTypeFont) -> None:
    """Refuse to draw a character the face would draw as its missing glyph.

    The check of scripts/dev/build_corpus.py: U+E000 lies in the private use
    area and no sane face maps it, so its bitmap is the shape of "missing", and
    a character that draws the same bitmap, or nothing at all, stops the run.
    """
    missing = _glyph_bitmap(font, chr(0xE000))
    blank = Image.new("L", (FONT_PIXELS * 2, FONT_PIXELS * 2), color=255).tobytes()
    for character in sorted(set(SENTENCE)):
        bitmap = _glyph_bitmap(font, character)
        if bitmap in (missing, blank):
            message = f"the face has no glyph for U+{ord(character):04X}"
            raise SystemExit(message)


def render() -> bytes:
    """The strip as PNG bytes."""
    font = _font()
    _assert_every_glyph_exists(font)
    image = Image.new("L", (WIDTH, HEIGHT), color=255)
    ImageDraw.Draw(image).text(ORIGIN, SENTENCE, fill=0, font=font)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", dpi=(DPI, DPI))
    return buffer.getvalue()


def main(argv: list[str]) -> int:
    payload = render()
    digest = hashlib.sha256(payload).hexdigest()
    if "--check" in argv:
        # Both, because they can part company: the committed file may have been
        # replaced together with the constant, or the drawing may have moved
        # under a new Pillow while the file still carries the old bytes.
        same = TARGET.read_bytes() == payload and digest == PNG_SHA256
        print(f"{TARGET.name} bytes={len(payload)} sha256={digest} matches the committed file and PNG_SHA256: {same}")
        return 0 if same else 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_bytes(payload)
    print(f"{TARGET.name} bytes={len(payload)} sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
