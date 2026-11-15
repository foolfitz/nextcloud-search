#!/usr/bin/env python3
"""What the errors are: the edit operations behind two figures of the README.

Unlike the other scripts of this run, this one prints text: the aligned
differences between the truth and the reading. The text is the test data of
this run and of this repository and nothing else, the statute text of the
Copyright Act (not protected, Taiwan Copyright Act, article 9) and the DACH
prose of testdata/corpus, so no user content can reach it.

1. The clean Ming page of the Copyright Act, read with chi_tra, whitespace
   removed on both sides: every edit operation with its count.
2. The six DACH pages, read with chi_tra+deu+eng+fra and normalised as
   findling.extract.ocr_quality does: every differing segment with context,
   and the whole words around it through the shipped German and English
   chains of findling.index.analyzer, to show which terms the search loses or
   gains. The German chain is built with an empty constituent list: the word
   list of the image is not in the measuring image, and the split step only
   cuts compounds, which none of these words is.

    PYTHONPATH=backend/src python zh_ocr_errors.py <pages dir> <dach corpus dir> <dach truth>
"""

from __future__ import annotations

import difflib
import json
import sys
from collections import Counter
from pathlib import Path

import pypdfium2

from findling.extract import raster
from findling.extract.ocr import read_page
from findling.extract.ocr_quality import normalise, rendered_pages
from findling.index.analyzer import english_analyzer, german_analyzer

CHINESE_PAGE = "ming-clean-00-J0070017.pdf"
CONTEXT = 12


def _render(path: Path) -> bytes:
    document = pypdfium2.PdfDocument(str(path))
    try:
        return raster.render_page_png(document, 0, dpi=300)
    finally:
        document.close()


def _chinese(pages: Path) -> None:
    truth = json.loads((pages / "truth.json").read_text(encoding="utf-8"))
    text = next(entry["pages"][0] for entry in truth["documents"] if entry["name"] == CHINESE_PAGE)
    expected = "".join(text.split())
    reading = "".join(read_page(_render(pages / CHINESE_PAGE), "chi_tra", 120).split())
    operations: Counter[tuple[str, str, str]] = Counter()
    matcher = difflib.SequenceMatcher(None, expected, reading, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            operations[(tag, expected[i1:i2], reading[j1:j2])] += 1
    print(f"== {CHINESE_PAGE}, chi_tra, whitespace removed")
    for (tag, was, became), count in sorted(operations.items(), key=lambda item: (-item[1], item[0])):
        print(f"{count}\t{tag}\t{was!r}\t{became!r}")


def _word(text: str, start: int, end: int) -> str:
    """The whole word or words the span [start, end) touches."""
    while start > 0 and not text[start - 1].isspace():
        start -= 1
    while end < len(text) and not text[end].isspace():
        end += 1
    return text[start:end]


def _dach(corpus: Path, truth_path: Path) -> None:
    truth = json.loads(truth_path.read_text(encoding="utf-8"))
    german = german_analyzer([])
    english = english_analyzer()
    print("== DACH pages, chi_tra+deu+eng+fra, ocr_quality.normalise")
    for number, page in enumerate(rendered_pages(corpus, truth, 300), start=1):
        expected = normalise(page.truth)
        reading = normalise(read_page(page.image, "chi_tra+deu+eng+fra", 120))
        matcher = difflib.SequenceMatcher(None, expected, reading, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                before = expected[max(0, i1 - CONTEXT) : i2 + CONTEXT]
                after = reading[max(0, j1 - CONTEXT) : j2 + CONTEXT]
                print(f"page {number}\t{tag}\t{before!r}\t{after!r}")
                was, became = _word(expected, i1, i2), _word(reading, j1, j2)
                print(f"  de\t{was!r} -> {german.analyze(was)}\t{became!r} -> {german.analyze(became)}")
                print(f"  en\t{was!r} -> {english.analyze(was)}\t{became!r} -> {english.analyze(became)}")


def main(pages: Path, corpus: Path, truth: Path) -> None:
    _chinese(pages)
    _dach(corpus, truth)


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
