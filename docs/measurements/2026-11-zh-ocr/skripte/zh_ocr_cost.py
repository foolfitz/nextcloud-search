#!/usr/bin/env python3
"""Seconds, peak resident memory and the address space floor of one page per language list.

Two pages: page 1 of testdata/corpus/13-ratsvorlage-scan.pdf (German, a page
of the DACH corpus; not the page of measurement 3 in docs/ocr.md, which a
throwaway script drew) and the clean Ming page of the Copyright Act from the
Chinese set. Two pages, so the address space floor here is a statement about
two pages; zh_ocr_floor.py asks it of every page. Both are rendered through findling.extract.raster at 300 dpi, then
handed to tesseract in the call form of findling.extract.ocr with
OMP_THREAD_LIMIT=1, three runs each, serial. The address space floor is the
ulimit -v ladder of docs/ocr.md measurement 2.

    PYTHONPATH=backend/src python zh_ocr_cost.py <german pdf> <chinese pdf>
"""

from __future__ import annotations

import os
import statistics
import subprocess
import sys
import tempfile

import pypdfium2

from findling.extract import raster

CALL = ("--oem", "1", "--psm", "3", "-c", "tessedit_do_invert=0")
LISTS = ("deu+eng+fra", "chi_tra", "chi_tra+eng", "chi_tra+deu+eng+fra", "deu+eng+fra+chi_tra")
LADDER_MB = (128, 192, 256, 320, 384, 448, 512)


def _png(path: str) -> bytes:
    document = pypdfium2.PdfDocument(path)
    try:
        return raster.render_page_png(document, 0, dpi=300)
    finally:
        document.close()


def _run(png: bytes, languages: str) -> tuple[float, int]:
    """Seconds and the peak RSS in kB of one engine call, measured in a fresh child."""
    script = (
        "import resource,subprocess,sys,time;"
        "data=sys.stdin.buffer.read();t=time.monotonic();"
        f"subprocess.run(['tesseract','-','-','-l','{languages}',*{CALL!r}],input=data,capture_output=True,check=True);"
        "print(time.monotonic()-t, resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)"
    )
    finished = subprocess.run(  # noqa: S603 - our own interpreter and a fixed script, no shell
        [sys.executable, "-I", "-c", script],
        input=png,
        capture_output=True,
        check=True,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    )
    seconds, rss = finished.stdout.decode().split()
    return float(seconds), int(rss)


def _floor(path: str, languages: str) -> str:
    """The smallest rung of the ladder at which the page still comes back with text."""
    for megabytes in LADDER_MB:
        command = f"ulimit -v {megabytes * 1024}; exec tesseract - - -l {languages} " + " ".join(CALL) + f" < {path}"
        # A shell on purpose: ulimit is a shell builtin, and the command line is
        # built from the constants above and a path this script wrote itself.
        finished = subprocess.run(  # noqa: S603
            ["sh", "-c", command],  # noqa: S607 - sh from PATH, as docs/ocr.md runs it
            capture_output=True,
            check=False,
            env={**os.environ, "OMP_THREAD_LIMIT": "1"},
        )
        if finished.returncode == 0 and len(finished.stdout.strip()) > 0:
            return f"{megabytes} MB (rc 0, {len(finished.stdout)} bytes)"
    return f"above {LADDER_MB[-1]} MB"


def main(german: str, chinese: str) -> None:
    pages = {"german": _png(german), "chinese": _png(chinese)}
    with tempfile.TemporaryDirectory() as scratch:
        files = {}
        for label, data in pages.items():
            files[label] = os.path.join(scratch, f"{label}.png")
            with open(files[label], "wb") as handle:
                handle.write(data)
        print("page\tlanguages\tseconds(3 runs)\tmedian\tpeak_rss_kB(max)\tas_floor")
        for label, data in pages.items():
            for languages in LISTS:
                runs = [_run(data, languages) for _ in range(3)]
                seconds = [round(run[0], 2) for run in runs]
                rss = max(run[1] for run in runs)
                floor = _floor(files[label], languages)
                print(f"{label}\t{languages}\t{seconds}\t{statistics.median(seconds):.2f}\t{rss}\t{floor}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
