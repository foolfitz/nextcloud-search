# OCR of Traditional Chinese with `chi_tra` (issue #53), 2026-11-15

The figures that the pull request bringing the Tesseract model `chi_tra`
quotes, in `backend/Dockerfile`, in `backend/src/findling/config.py`
(`OCR_LANGUAGE_ALLOWLIST`), in `THIRD-PARTY.md` and in `docs/ocr.md`. Six
questions:

1. What does the pack cost in the image?
2. How well does `chi_tra` read Traditional Chinese pages through Findling's
   own OCR call, and how much of what it reads reaches the search through
   `body_zh`?
3. What does the order of `FINDLING_OCR_LANGUAGES` change?
4. Do German pages suffer when `chi_tra` is on the list?
5. What does a page cost in seconds, resident memory and address space?
6. What about vertical text, and the model `chi_tra_vert`?

Written in English, like `docs/measurements/2026-11-zh-kette`, by a
contributor who cannot vouch for German prose.

## The verdict, first

- Without `chi_tra`, a Chinese scan is unreadable for the index: the factory
  setting `deu+eng+fra` reads 63 pages with 38,844 Han characters and writes
  **not one Han character**. The Latin models cannot write them.
- With `chi_tra` first, the Han character error rate is **3.4 %**, and
  **96.1 %** of the distinct two character runs and **92.7 %** of the four
  character runs of the pages come back as the same consecutive tokens, the
  exact sequence a search term of that length needs in `body_zh` (the 臺/台
  expansion of the query side is not counted, it could only add hits).
- **The order matters.** Behind the Latin models (`deu+eng+fra+chi_tra`) the
  engine puts a space between most pairs of Han characters it reads (26,707
  times on these pages, against 370 with `chi_tra` alone). `body_zh` does not
  care, the stored text keeps them. On Chinese pages every Latin model added,
  in front or behind, costs time; `chi_tra` alone is the fastest list.
- **German pages barely notice.** The repository's DACH pages: 0 errors with
  `chi_tra` appended, 2 errors in 3,148 characters with `chi_tra` first
  (`für` and `Zürich` read as `fur` and `Zurich`; neither loses a search term,
  section 4).
- **Cost:** +2,383,872 bytes in the image layer. Over all 69 pages of this
  run none of the four lists asked needed more than 256 MB of address space, against the 512 MB the
  extraction child allows; at most 161 MiB resident on the two pages timed.
- **Vertical text** is unreadable for `chi_tra` (Han error rate 0.99 on one
  page) and readable for `chi_tra_vert` (0.05), which is not installed.

## Environment

| Item | Value |
|---|---|
| Date | 2026-11-15 |
| Machine | AMD Ryzen 5 8500G, 12 visible cores, Linux 7.0.0 x86_64, Docker 29.9.2 (a desktop, not the target box) |
| Base image | `python:3.13-slim-trixie@sha256:ffb752e1...c6e30a`, as pinned in `backend/Dockerfile`, Debian 13.6 |
| Engine | tesseract 5.5.0, leptonica 1.84.1 |
| Language data | the apt block of `backend/Dockerfile` plus `tesseract-ocr-chi-tra`, all `1:4.1.0-2` |
| Python packages | `pypdfium2` 5.14.0, `pillow` 13.0.0, `tantivy` 0.26.2, the versions of `backend/uv.lock`, installed with pip in the measuring stage |
| Code | `backend/src` of this branch, read only, on `PYTHONPATH`, with `chi_tra` in `OCR_LANGUAGE_ALLOWLIST` (see the note below) |
| Call form | `findling.extract.ocr.read_page` unchanged: `--oem 1 --psm 3 -c tessedit_do_invert=0`, `OMP_THREAD_LIMIT=1` |
| Raster | `findling.extract.raster.render_page_png` at 300 dpi, the default of `FINDLING_OCR_DPI` |
| Network | cut, `--network none`, for every run that reads a page |

The images are built from `skripte/Dockerfile.messung`: stage `ten` is the apt
block of `backend/Dockerfile` at `e5c1da7`, stage `eleven` is the same block
with `tesseract-ocr-chi-tra`, and stage `measure` adds the two font packages,
`tesseract-ocr-chi-tra-vert` and the three wheels to `eleven`. Fonts and wheels
are tools of the measurement and never part of the product image.

## The command

```bash
sh docs/measurements/2026-11-zh-ocr/skripte/zh_ocr_run.sh "$PWD" <laws dir> <scratch dir>
```

`<laws dir>` holds one text file per article of the statute corpus of
`docs/measurements/2026-11-zh-kette` (fetched with the loop in its README and
cut by its `skripte/zh_corpus.py`; 4306 files, `cat *.txt | sha256sum` gave
`920ea159...a3c7c6`). The driver writes every file of `rohdaten/`:

| File | Content |
|---|---|
| `abbild.txt` | package facts, layer sizes, the traineddata, the copyright files (`skripte/zh_ocr_image.sh`) |
| `seiten-schriften.txt`, `seiten-manifest.txt` | the fonts and their sha256, every page with its truth length and sha256 (`skripte/zh_ocr_pages.py`) |
| `seiten-<languages>.jsonl` | one line per page and language list (`skripte/zh_ocr_measure.py`) |
| `zusammenfassung.tsv` | those lines summed per list and group (`skripte/zh_ocr_summary.py`) |
| `dach.txt` | `findling.extract.ocr_quality` on the DACH pages of `testdata/` per list |
| `kosten.txt` | seconds, peak RSS and address space floor of two pages per list (`skripte/zh_ocr_cost.py`) |
| `adressraum.txt` | the address space floor of all 69 pages per list (`skripte/zh_ocr_floor.py`) |
| `fehler.txt` | the edit operations behind section 2 and section 4 (`skripte/zh_ocr_errors.py`) |
| `senkrecht.txt` | the vertical page (`skripte/zh_ocr_vertical.py`) |

The tools print numbers, names of pages and language lists, never what the
engine read, with one exception: `fehler.txt` carries the aligned differences
between truth and reading, so that the kinds of error named below can be
checked. Its text is the test data of this run and of the repository (the
statute text, the DACH prose of `testdata/corpus`) and nothing else.

**A note on the allowlist.** The Chinese pages are read through `read_page`
with the language list as an argument, which is how the OCR path calls it
after the settings have been resolved. The DACH runs go through
`findling.extract.ocr_quality`, which resolves `FINDLING_OCR_LANGUAGES` itself,
and that resolution drops every entry `OCR_LANGUAGE_ALLOWLIST` does not carry,
with a warning and without failing. A tree without `chi_tra` in the allowlist
therefore measures `deu+eng+fra` four times under four names. The first pass of
this run did exactly that and was thrown away; the figures below are from the
tree with the allowlist entry. `rohdaten/dach.txt` records the number of
languages each run really used (`languages=N` under each heading), and the
driver refuses a run whose number is not the number of its name.

## The pages

Seven texts, each drawn in three faces and three treatments, 63 image only
PDFs of one A4 page each, 12 pt, 38,844 Han characters in all.

- **Texts.** Six pages of Taiwanese statutes, each filled from a starting
  article until the page is full (Copyright Act from article 8, Labor
  Standards Act from article 25, Personal Data Protection Act from article
  1-1, Civil Code from article 1, Income Tax Act from article 2, Criminal Code
  from article 1), not protected by copyright (Copyright Act of Taiwan,
  article 9), and one
  self written office letter that mixes Chinese with Latin words, a URL, an
  e-mail address, dates and numbers, as test prose.
- **Faces.** Noto Serif CJK TC (Ming, the face of most printed matter), Noto
  Sans CJK TC (Hei) from Debian `fonts-noto-cjk` 1:20240730+repack1-1, and AR
  PL UKai TW (Kai, the face many Taiwanese official letters are set in) from
  `fonts-arphic-ukai` 0.2.20080216.2-5. The sha256 of the three files are in
  `rohdaten/seiten-schriften.txt`.
- **Treatments.** `clean`: drawn at 300 dpi, stored as Pillow stores a grey
  page in a PDF (JPEG at its default quality). `scan`: the same page turned by
  0.6 degrees, blurred with a radius of 1.1 pixels, blended with 15 % seeded
  uniform noise and stored as JPEG at quality 70. `fax`: drawn at 200 dpi and
  thresholded to black and white. All three are read back at 300 dpi, as the
  OCR path renders every PDF page.

The generator refuses to draw a character a face would draw as its missing
glyph (compared with the bitmap of U+E000, the check of
`scripts/dev/build_corpus.py`), and before it draws anything it proves the
check on every face with a letter none of them has (Cherokee A, U+13A0). No
character of the seven texts is missing in any of the three faces.

The truth is the text as it was laid out on the page. The pages are not
checked in (about 50 MB); the generator writes the same bytes on every run
(two runs, identical manifests), and `rohdaten/seiten-manifest.txt` carries the
sha256 of each page.

## What is counted

Per page and language list:

- `cer_ws`: the character error rate after `ocr_quality.normalise` (whitespace
  runs collapsed to one space), the count of the DACH report.
- `cer_nows`: the same with all whitespace removed on both sides.
- `cer_han`: the same over the Han characters alone, everything else dropped
  on both sides. This is the part of the page `body_zh` indexes character by
  character; punctuation never reaches the index, and a full width comma that
  comes back as an ASCII comma is an error in `cer_ws` and none here.
- `recall2`, `recall4`: of the distinct runs of two and of four Han characters
  in the truth, as the chain of `body_zh` cuts it, the share that come back as
  consecutive tokens in the reading, token for token. A run of n consecutive
  tokens is what a search term of n Han characters matches (tantivy turns it
  into a phrase query with slop 0), so this is the share of such terms that
  would still find the page as typed. The query side of the lexical step also
  searches 臺 and 台 in both shapes (`findling.query.rewrite.han_variants`);
  a run the engine read with the other shape counts as a miss here and would
  be a hit there, so the search finds at least this share.
- `latin_recall`: of the tokens of the truth that are not Han (Latin words,
  digit runs), the share that stand among the tokens of the reading.
- `spaces_between_han`: how often the reading puts whitespace between two Han
  characters.
- `seconds`: the engine call per page, six pages in parallel, so a relative
  figure. The serial figures are in section 5.

Rates are summed errors over summed characters, weighted by characters, as
`ocr_quality.overall_rate` does.

## 1. The image

From `rohdaten/abbild.txt`:

| | Value |
|---|---|
| Package | `tesseract-ocr-chi-tra` 1:4.1.0-2, `Architecture: all`, source `tesseract-lang` |
| Download | 1,587,616 bytes, `SHA256: b4b08ba6...cb7d45d` |
| Installed size | 2327 kB |
| Top layer, stage `ten` | 130,871,296 bytes |
| Top layer, stage `eleven` | 133,255,168 bytes |
| **Delta** | **2,383,872 bytes** |
| `chi_tra.traineddata` | 2,366,642 bytes, sha256 `529c5b57...a829330b` |
| `copyright` of `-chi-tra` and of `-deu` | byte identical, md5 `63a049f5eeaf97ed32fcb2a61e01c016` |

`Architecture: all` means amd64 and arm64 install the same file. The arm64
build itself was not run here; the image workflow of the repository builds
both.

## 2. How well it reads

All 63 pages, from the lines of `rohdaten/seiten-*.jsonl` (summed in
`rohdaten/zusammenfassung.tsv`; the figures here are rounded once, from the
summed counts):

| `FINDLING_OCR_LANGUAGES` | Han read | `cer_han` | `recall2` | `recall4` | `latin_recall` | spaces between Han | s/page (parallel) |
|---|---|---|---|---|---|---|---|
| `deu+eng+fra` (factory setting) | 0 of 38,844 | 1.000 | 0.000 | 0.000 | 0.877 | 0 | 3.18 |
| `chi_tra` | 38,296 | **0.034** | **0.961** | **0.927** | 0.982 | 370 | **1.82** |
| `chi_tra+eng` | 37,746 | 0.040 | 0.952 | 0.919 | 0.986 | 332 | 2.67 |
| `chi_tra+deu+eng+fra` | 37,526 | 0.044 | 0.949 | 0.915 | 0.994 | 325 | 4.50 |
| `deu+eng+fra+chi_tra` | 37,480 | 0.045 | 0.948 | 0.914 | 0.994 | 26,707 | 4.27 |
| `chi_tra+chi_tra_vert` | 38,221 | 0.036 | 0.960 | 0.926 | 0.982 | 387 | 3.00 |

`chi_tra` alone, by face and by treatment:

| Group | `cer_han` | `recall4` |
|---|---|---|
| Ming | 0.042 | 0.908 |
| Hei | 0.019 | 0.940 |
| Kai | 0.040 | 0.933 |
| clean | 0.044 | 0.920 |
| scan | 0.019 | 0.947 |
| fax | 0.038 | 0.914 |
| statutes (54 pages) | 0.035 | 0.925 |
| office letter (9 pages) | 0.019 | 0.969 |

Three readings of these tables:

- **Every model added to `chi_tra` costs a little Chinese**: from 0.034 to
  0.040 with `eng` and to 0.044 with the three Latin models. What it buys is
  Latin text: on the office letter alone, the share of Latin tokens read goes
  from 0.956 (`chi_tra`) to 0.972 (`chi_tra+eng`) and 0.992 (with the three).
  The misses are pieces of the URL and of the e-mail address.
- **The simulated scan reads better than the clean page.** The blur thickens
  the thin horizontal strokes of the Ming and Kai faces. This says something
  about these faces at 12 pt, not that bad scans are good; no real scan was
  read.
- **What the errors are**, on the clean Ming page of the Copyright Act, 65
  errors without whitespace (`rohdaten/fehler.txt`): 24 full width commas read
  as ASCII commas, three line opening enumerators (`三`, `四`, `五`) and one
  whole line of article 9 lost, and look-alike characters (`雇` read as `選`,
  `屋`, `座` or `殿`; `契` as `奉`, `替` or `鴨`). The commas never reach the
  index; the lost line and the look-alikes are what `recall4` counts.

## 3. The order of the list

Two effects, both in the table above:

- **Spaces between Han characters.** With `chi_tra` first, the engine writes
  Chinese the way it is written, with 325 to 370 inserted spaces in 38,844
  characters. With `chi_tra` behind the Latin models it inserts one between
  most pairs: 26,707 times, which is why `cer_ws` jumps to 0.776 while
  `cer_nows` stays at 0.092. The chain of `body_zh` gives consecutive Han
  characters consecutive positions whatever stands between them, so the
  spaces cost the search nothing (`recall4` 0.915 with `chi_tra` first and
  0.914 behind the Latin models, the difference being the characters read). The stored text
  (`body_de`, which feeds the excerpts, the re-analysis rebuild and the
  embeddings) keeps the spaces. What they do to the semantic search is not
  measured here.
- **Time.** On Chinese pages every Latin model in front of `chi_tra` or behind
  it costs time; `chi_tra` alone is the fastest list, faster than the factory
  setting that reads nothing. Section 5 has the serial figures.

## 4. German pages

`findling.extract.ocr_quality` over the six DACH pages of `testdata/` (3,148
characters), the tool and corpus of `docs/measurements/2026-09-06-ocr-dach`,
from `rohdaten/dach.txt`:

| `FINDLING_OCR_LANGUAGES` | Errors | Rate |
|---|---|---|
| `deu+eng+fra` | 0 | 0.000000 |
| `deu+eng+fra+chi_tra` | 0 | 0.000000 |
| `chi_tra+deu+eng+fra` | 2 | 0.000635 |
| `chi_tra+eng` | 63 | 0.020013 |

The two errors of `chi_tra` first are `für` and `Zürich` read as `fur` and
`Zurich`. Neither loses a search term: `skripte/zh_ocr_errors.py` puts the
whole words of each error through the shipped chains of
`findling.index.analyzer` (the German one with an empty constituent list,
which does not matter for words that are no compounds), and
`rohdaten/fehler.txt` shows `Zürich` and `Zurich` as the one term `zurich` in
both chains, `für` as no term at all in the German chain (a stop word) and the
misread `fur` as an extra term `fur`, and both as `fur` in the English chain.
`chi_tra+eng` loses the umlauts throughout: 63 errors, against 64 with `eng`
alone in the DACH report, so the run did use `chi_tra` (and `dach.txt` says
`languages=2`).

## 5. Seconds, memory, address space

One German page (page 1 of `testdata/corpus/13-ratsvorlage-scan.pdf`, a page
of the DACH corpus; not the page of measurement 3 in `docs/ocr.md`, which a
throwaway script drew) and one Chinese page (the clean Ming page of the
Copyright Act), each through the engine three times, serially. Peak resident
memory is the largest `ru_maxrss` of the engine over the three runs; the
address space floor is the smallest rung of the `ulimit -v` ladder of
`docs/ocr.md` measurement 2 at which the page still comes back with text.
From `rohdaten/kosten.txt`:

| Page | `FINDLING_OCR_LANGUAGES` | Median s | Peak RSS | Floor of this page |
|---|---|---|---|---|
| German | `deu+eng+fra` | 0.54 | 88 MiB | 128 MB |
| German | `deu+eng+fra+chi_tra` | 0.60 | 136 MiB | 192 MB |
| German | `chi_tra+deu+eng+fra` | 0.67 | 140 MiB | 192 MB |
| German | `chi_tra+eng` | 0.84 | 119 MiB | 192 MB |
| German | `chi_tra` | 0.75 | 100 MiB | 128 MB |
| Chinese | `deu+eng+fra` | 2.32 | 103 MiB | 128 MB |
| Chinese | `chi_tra` | 1.27 | 108 MiB | 192 MB |
| Chinese | `chi_tra+eng` | 1.91 | 127 MiB | 192 MB |
| Chinese | `deu+eng+fra+chi_tra` | 2.91 | 161 MiB | 192 MB |
| Chinese | `chi_tra+deu+eng+fra` | 3.12 | 160 MiB | 192 MB |

(Peak RSS from the KiB that `ru_maxrss` reports.) Two pages say little about
the address space, so `skripte/zh_ocr_floor.py` asks the same ladder, with a
rung at 160 MB added, of every page of this run: the 63 Chinese pages and the
six DACH pages. From `rohdaten/adressraum.txt`, pages per smallest rung that
still returns text:

| `FINDLING_OCR_LANGUAGES` | 128 MB | 160 MB | 192 MB | 256 MB | more | largest |
|---|---|---|---|---|---|---|
| `chi_tra` | 18 | 51 | 0 | 0 | 0 | 160 MB |
| `chi_tra+deu+eng+fra` | 0 | 2 | 59 | 8 | 0 | 256 MB |
| `deu+eng+fra+chi_tra` | 0 | 6 | 55 | 8 | 0 | 256 MB |
| `chi_tra+chi_tra_vert` | 0 | 1 | 52 | 16 | 0 | 256 MB |

The extraction child runs under `RLIMIT_AS` of 512 MB
(`EXTRACT_ADDRESS_SPACE_BYTES`), twice the largest floor measured here, so the
cap needs no change for these pages; a denser page may need more, and a page
that bursts the cap fails as `ocr_failed` like any other. The 30 s page budget
is about ten times the slowest median above; the target box is slower, and
nothing about ARM was measured.

## 6. Vertical text

Articles 8 to 11 of the Copyright Act set vertically (one page, columns from top to bottom, right
to left, Noto Serif CJK TC, 12 pt, 344 Han characters), read with the fixed
`--psm 3` of the call form. From `rohdaten/senkrecht.txt`:

| `FINDLING_OCR_LANGUAGES` | Han read | `cer_han` | `recall4` |
|---|---|---|---|
| `chi_tra` | 325 | 0.988 | 0.000 |
| `chi_tra_vert` | 342 | 0.049 | 0.807 |
| `chi_tra+chi_tra_vert` | 342 | 0.049 | 0.807 |
| `chi_tra_vert+chi_tra` | 342 | 0.049 | 0.807 |

n = 1 page, an indication and not a rate. On the 63 horizontal pages,
`chi_tra+chi_tra_vert` reads as well as `chi_tra` alone (`cer_han` 0.036
against 0.034) and takes about 1.6 times as long (3.00 s against 1.82 s, in
parallel). `tesseract-ocr-chi-tra-vert` 1:4.1.0-2 would add 1797 kB installed
(download 1,092,616 bytes).

## What these numbers do not say

- **No real scan was read.** The pages are drawn and then degraded on
  purpose; a photographed receipt, a stamp over text, a table or a form is a
  different case.
- **One machine, amd64.** The seconds are a desktop's; the language data are
  the same bytes on arm64, the speed is not.
- **Simplified Chinese** is not covered: `chi_sim` is not installed and was not
  measured.
- **Handwriting** is not covered.
- **The effect of inserted spaces on the semantic search** is not measured.
- **Vertical text** rests on one page.
- **The recall figures** count exact token sequences; the 臺/台 expansion of
  the query side is left out, so the search finds at least as much.
