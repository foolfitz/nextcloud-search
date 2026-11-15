#!/usr/bin/env python3
"""The address space floor of every rendered page, for the heaviest language lists.

zh_ocr_cost.py measures two pages. This asks the same question of all 63
Chinese pages of zh_ocr_pages.py and of the six DACH pages of testdata/corpus:
the smallest rung of the ulimit -v ladder of docs/ocr.md measurement 2 at which
tesseract, in the call form of findling.extract.ocr with OMP_THREAD_LIMIT=1,
still returns text. A rung is a limit on virtual address space, the same
kernel mechanism as the RLIMIT_AS of the extraction child (512 MB).

Output per language list: how many pages needed each rung, and the largest.
Numbers only.

    PYTHONPATH=backend/src python zh_ocr_floor.py <pages dir> <dach corpus dir> <dach truth> [<workers>]
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pypdfium2

from findling.extract import raster

CALL = ("--oem", "1", "--psm", "3", "-c", "tessedit_do_invert=0")
LISTS = ("chi_tra", "chi_tra+deu+eng+fra", "deu+eng+fra+chi_tra", "chi_tra+chi_tra_vert")
LADDER_MB = (128, 160, 192, 256, 320, 384, 448, 512)


def _floor(job: tuple[str, int, str]) -> tuple[str, int]:
    """The smallest rung for one page and one list, or 0 when even the top rung fails."""
    path, number, languages = job
    document = pypdfium2.PdfDocument(path)
    try:
        png = raster.render_page_png(document, number, dpi=300)
    finally:
        document.close()
    with tempfile.NamedTemporaryFile(suffix=".png") as handle:
        handle.write(png)
        handle.flush()
        for megabytes in LADDER_MB:
            command = (
                f"ulimit -v {megabytes * 1024}; exec tesseract - - -l {languages} "
                + " ".join(CALL)
                + f" < {handle.name}"
            )
            # A shell on purpose: ulimit is a shell builtin, and the command line
            # is built from the constants above and a file this script wrote.
            finished = subprocess.run(  # noqa: S603
                ["sh", "-c", command],  # noqa: S607 - sh from PATH, as docs/ocr.md runs it
                capture_output=True,
                check=False,
                env={**os.environ, "OMP_THREAD_LIMIT": "1"},
            )
            if finished.returncode == 0 and finished.stdout.strip():
                return languages, megabytes
    return languages, 0


def main(pages: Path, dach: Path, dach_truth: Path, workers: int) -> None:
    targets = [(str(path), 0) for path in sorted(pages.glob("*.pdf"))]
    truth = json.loads(dach_truth.read_text(encoding="utf-8"))
    for entry in truth["documents"]:
        targets.extend((str(dach / entry["name"]), number) for number in range(len(entry["pages"])))
    jobs = [(path, number, languages) for languages in LISTS for path, number in targets]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_floor, jobs))
    chinese = len(list(pages.glob("*.pdf")))
    print(f"pages {len(targets)} (Chinese {chinese}, DACH {len(targets) - chinese})")
    print("languages\t" + "\t".join(f"{rung}MB" for rung in LADDER_MB) + "\tfailed\tlargest")
    for languages in LISTS:
        counts = Counter(rung for listed, rung in results if listed == languages)
        largest = max(rung for listed, rung in results if listed == languages)
        cells = "\t".join(str(counts.get(rung, 0)) for rung in LADDER_MB)
        print(f"{languages}\t{cells}\t{counts.get(0, 0)}\t{largest}MB")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]) if len(sys.argv) > 4 else 1)
