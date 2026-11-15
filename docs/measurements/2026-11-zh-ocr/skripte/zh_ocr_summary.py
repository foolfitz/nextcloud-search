#!/usr/bin/env python3
"""Sum the JSON lines of zh_ocr_measure.py per language list and per group of pages.

Rates are summed errors over summed characters, weighted by characters and not
by page, as findling.extract.ocr_quality.overall_rate does. Groups: all pages,
each treatment (clean, scan, fax), each font (ming, hei, kai), and statute pages
against the mixed page.

    python zh_ocr_summary.py <jsonl> [<jsonl> ...]
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ORDER = ("deu+eng+fra", "chi_tra", "chi_tra+eng", "chi_tra+deu+eng+fra", "deu+eng+fra+chi_tra", "chi_tra+chi_tra_vert")
COLUMNS = (
    "languages",
    "group",
    "pages",
    "cer_ws",
    "cer_nows",
    "cer_han",
    "han_read",
    "recall2",
    "recall4",
    "latin_recall",
    "seconds_median",
    "spaces_between_han",
)


def main(paths: list[str]) -> None:
    rows = [json.loads(line) for path in paths for line in Path(path).read_text(encoding="utf-8").splitlines()]
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        font, treatment = row["name"].split("-")[:2]
        kind = "mixed" if row["name"].endswith("mixed.pdf") else "statute"
        for group in ("all", treatment, font, kind):
            groups[(row["languages"], group)].append(row)
    print("\t".join(COLUMNS))
    for (languages, group), members in sorted(
        groups.items(), key=lambda item: (ORDER.index(item[0][0]) if item[0][0] in ORDER else 99, item[0][1])
    ):

        def total(key: str, members: list[dict] = members) -> int:
            return sum(member[key] for member in members)

        print(
            "\t".join(
                (
                    languages,
                    group,
                    str(len(members)),
                    f"{total('err_ws') / total('chars_ws'):.4f}",
                    f"{total('err_nows') / total('chars_nows'):.4f}",
                    f"{total('err_han') / total('han_truth'):.4f}",
                    f"{total('han_out')}/{total('han_truth')}",
                    f"{total('hit2') / total('runs2'):.4f}",
                    f"{total('hit4') / total('runs4'):.4f}",
                    f"{total('latin_hit') / total('latin_truth'):.4f}",
                    f"{statistics.median(member['seconds'] for member in members):.2f}",
                    str(total("spaces_between_han")),
                )
            )
        )


if __name__ == "__main__":
    main(sys.argv[1:])
