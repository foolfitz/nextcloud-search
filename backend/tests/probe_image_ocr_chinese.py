"""Traditional Chinese OCR in the built image (issue #53), run as a plain script.

Not named ``test_*`` on purpose: pytest must not collect it. It needs the
tesseract engine and the ``chi_tra`` traineddata, which exist in the image and
on no development machine. The file lives under ``tests`` because that is the
directory ``.github/workflows/docker.yml`` bind mounts into the container, the
same way ``probe_image_ocr_czech.py`` travels in.

What it proves: the package ``tesseract-ocr-chi-tra`` is in the image
(``tesseract --list-langs`` names ``chi_tra``), and a strip of Traditional
Chinese read with ``-l chi_tra`` comes back as text whose tokens, through the
chain of ``body_zh`` (``findling.index.analyzer.chinese_analyzer``), carry the
expected words as consecutive tokens. A word of n Han characters that stands as
n consecutive tokens is what a search for it matches, because the parser turns
it into a phrase query; so this is the chain from a scan to search terms, minus
the index itself.

Why the Chinese model and nothing else can be green here: none of the Latin
models of the image can write a Han character at all. So the same strip is
read once more with ``eng`` and has to yield no Han character, which is the
positive control that this check tells the models apart on this very page.
And the expected words are Traditional forms (``會議記錄``, ``掃描``, ``檔案``,
``臺北``, ``搜尋``), written differently in Simplified Chinese, so a reading that
carries them came out of a Traditional model.

The strip is not drawn here, unlike the Czech one: DejaVu Sans of
``testdata/fonts`` has no Han glyph, so it is drawn once by
``scripts/dev/build_zh_ocr_probe.py`` and committed as
``testdata/ocr-zh/probe-zh-tw.png``; that script names the face, the geometry
and the sha256 the picture has to have. The white control page is drawn here,
at the same size.

What it does not prove: character accuracy. Four of the five expected words are
enough, so that a point release of the engine or of the traineddata that
misreads one character does not turn the step red; the measured accuracy is in
``docs/measurements/2026-11-zh-ocr``.

The empty answer is the trap of every OCR proof (T-06-49): a verdict that only
looks for words would be green on an engine that returns nothing as long as the
check is wrong. So the same call is made on a white page of the same size, and
that one has to yield zero tokens. The script is green only if every check holds.

Nothing recognised is printed except counts and the expected words found.

Run it like this:

    docker run --rm --network none -v "$PWD/backend/tests:/probe:ro" \\
        -v "$PWD/testdata/ocr-zh:/strip:ro" \\
        --entrypoint python IMAGE /probe/probe_image_ocr_chinese.py /strip/probe-zh-tw.png
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

from PIL import Image

from findling.extract.ocr import read_page
from findling.index.analyzer import chinese_analyzer

# The words of the strip a search would be made for, as drawn by
# scripts/dev/build_zh_ocr_probe.py.
EXPECTED: Final = ("會議記錄", "掃描", "檔案", "臺北", "搜尋")
REQUIRED_HITS: Final = 4

# The Han characters of the basic block and the two extension and
# compatibility blocks a traineddata could write.
HAN: Final = re.compile(r"[㐀-䶿一-鿿豈-﫿]")

PAGE_SECONDS: Final = 30
DEFAULT_STRIP: Final = "/strip/probe-zh-tw.png"


def _chi_tra_is_listed() -> bool:
    """True when the installed engine names chi_tra as one of its languages."""
    finished = subprocess.run(
        ["tesseract", "--list-langs"],  # noqa: S607 - the engine is on PATH in the image
        capture_output=True,
        check=False,
        timeout=PAGE_SECONDS,
    )
    listing = (finished.stdout + finished.stderr).decode("utf-8", errors="replace")
    return "chi_tra" in {line.strip() for line in listing.splitlines()}


def _white(strip: bytes) -> bytes:
    """A white page of the size of the strip."""
    size = Image.open(io.BytesIO(strip)).size
    buffer = io.BytesIO()
    Image.new("L", size, color=255).save(buffer, format="PNG", dpi=(300, 300))
    return buffer.getvalue()


def _found(tokens: list[str], word: str) -> bool:
    """True when the characters of the word stand as consecutive tokens."""
    wanted = list(word)
    return any(tokens[start : start + len(wanted)] == wanted for start in range(len(tokens) - len(wanted) + 1))


def main(argv: list[str]) -> int:
    """Run all four checks and return the exit code."""
    strip_path = Path(argv[1] if len(argv) > 1 else DEFAULT_STRIP)
    if not strip_path.is_file():
        print(f"strip missing: {strip_path}")
        return 2
    strip = strip_path.read_bytes()

    listed = _chi_tra_is_listed()
    print(f"tesseract --list-langs names chi_tra: {listed}")
    if not listed:
        # The engine would refuse every call below; say so instead of a trace.
        print("traditional chinese ocr in the image: FAILED")
        return 1

    chain = chinese_analyzer()
    tokens = chain.analyze(read_page(strip, "chi_tra", PAGE_SECONDS))
    found = [word for word in EXPECTED if _found(tokens, word)]
    print(f"chinese strip: {len(tokens)} tokens, {len(found)} of {len(EXPECTED)} expected: {', '.join(found)}")

    control = len(HAN.findall(read_page(strip, "eng", PAGE_SECONDS)))
    print(f"same strip read with eng: {control} Han characters (must be 0)")

    blank = chain.analyze(read_page(_white(strip), "chi_tra", PAGE_SECONDS))
    print(f"white page: {len(blank)} tokens")

    ok = len(found) >= REQUIRED_HITS and control == 0 and not blank
    print("traditional chinese ocr in the image: " + ("ok" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
