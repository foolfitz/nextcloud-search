#!/usr/bin/env python3
"""Read the rendered Traditional Chinese pages through Findling's OCR call and count.

Inside the measure image, with the source tree of the branch on PYTHONPATH, so
the engine call is findling.extract.ocr.read_page and the raster step is
findling.extract.raster.render_page_png at the configured DPI, unchanged.

Per page and language list it records:

* cer_ws: the character error rate after ocr_quality.normalise (whitespace runs
  collapsed to one space), the way the DACH report counts;
* cer_nows: the same with every whitespace character removed on both sides,
  because Chinese is written without spaces and an engine that puts a space
  between two Han characters has not misread either of them;
* han_out: Han characters in the reading (0 means the model cannot write Chinese);
* cer_han: the error rate over the Han characters alone, everything else dropped
  on both sides, which is the part of the page body_zh indexes character by
  character (punctuation and the width of a comma do not reach the index);
* spaces_between_han: how often the reading puts whitespace between two Han
  characters;
* recall2 / recall4: of the distinct runs of 2 and 4 Han characters in the truth,
  as the chain of body_zh tokenises it, the share that come back as consecutive
  tokens in the reading. A run of n consecutive tokens is exactly what a slop 0
  phrase query for an n character term matches, so this is the share of such
  search terms that would still find the page;
* latin_truth / latin_hit: the tokens of the truth that are not Han (Latin
  words and digit runs, as the body_zh chain cuts them), and how many of them
  stand among the tokens of the reading;
* seconds: wall clock of the engine call for the page.

Output is one JSON line per page with numbers and the page name, never
recognised text. Workers run pages in parallel; the seconds of a parallel run
are a relative figure, zh_ocr_cost.py measures time serially.

    PYTHONPATH=backend/src python zh_ocr_measure.py <pages dir> <languages> [<workers>]
"""

from __future__ import annotations

import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pypdfium2

from findling import config
from findling.extract import raster
from findling.extract.ocr import read_page
from findling.extract.ocr_quality import edit_distance, normalise
from findling.index.analyzer import chinese_analyzer

HAN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def _han_tokens(text: str) -> list[str]:
    return chinese_analyzer().analyze(text)


def _runs(tokens: list[str], n: int) -> set[tuple[str, ...]]:
    found: set[tuple[str, ...]] = set()
    for start in range(len(tokens) - n + 1):
        window = tuple(tokens[start : start + n])
        if all(HAN.fullmatch(token) for token in window):
            found.add(window)
    return found


def _page(job: tuple[str, str, str, int]) -> dict[str, object]:
    path, truth, languages, dpi = job
    document = pypdfium2.PdfDocument(path)
    try:
        png = raster.render_page_png(document, 0, dpi=dpi)
    finally:
        document.close()
    started = time.monotonic()
    reading = read_page(png, languages, 120)
    seconds = time.monotonic() - started

    truth_ws, reading_ws = normalise(truth), normalise(reading)
    truth_nows = "".join(truth.split())
    reading_nows = "".join(reading.split())
    truth_tokens, reading_tokens = _han_tokens(truth), _han_tokens(reading)
    result: dict[str, object] = {
        "name": Path(path).name,
        "chars_ws": len(truth_ws),
        "err_ws": edit_distance(truth_ws, reading_ws),
        "chars_nows": len(truth_nows),
        "err_nows": edit_distance(truth_nows, reading_nows),
        "han_truth": len(HAN.findall(truth)),
        "han_out": len(HAN.findall(reading)),
        # Han characters only, everything else dropped on both sides: the part
        # of the page body_zh indexes character by character.
        "err_han": edit_distance("".join(HAN.findall(truth)), "".join(HAN.findall(reading))),
        "spaces_between_han": len(re.findall(r"[\u4e00-\u9fff] +(?=[\u4e00-\u9fff])", reading)),
        "seconds": round(seconds, 3),
    }
    latin = [token for token in truth_tokens if not HAN.fullmatch(token)]
    read = set(reading_tokens)
    result["latin_truth"] = len(latin)
    result["latin_hit"] = sum(1 for token in latin if token in read)
    for n in (2, 4):
        wanted = _runs(truth_tokens, n)
        got = _runs(reading_tokens, n)
        result[f"runs{n}"] = len(wanted)
        result[f"hit{n}"] = len(wanted & got)
    return result


def main(pages: Path, languages: str, workers: int) -> None:
    truth = json.loads((pages / "truth.json").read_text(encoding="utf-8"))
    dpi = config.settings().ocr_dpi
    jobs = [(str(pages / entry["name"]), entry["pages"][0], languages, dpi) for entry in truth["documents"]]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_page, jobs))
    for result in results:
        print(json.dumps({"languages": languages, **result}, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1)
