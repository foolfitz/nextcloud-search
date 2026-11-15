#!/bin/sh
# The whole run of docs/measurements/2026-11-zh-ocr, in the order the README
# reports it, writing every raw file of rohdaten/.
#
#     sh zh_ocr_run.sh <repository root> <laws dir> <scratch dir>
#
# <laws dir> holds one text file per article, as zh_corpus.py of
# docs/measurements/2026-11-zh-kette writes them out of the saved statute pages.
# <scratch dir> receives the rendered pages (about 50 MB), which are not
# checked in; their sha256 are, in rohdaten/seiten-manifest.txt.
set -eu
repo="$1"
laws="$2"
scratch="$3"
here="$repo/docs/measurements/2026-11-zh-ocr"
raw="$here/rohdaten"

sh "$here/skripte/zh_ocr_image.sh" "$here/skripte" > "$raw/abbild.txt"

context="$(mktemp -d)"
docker build -q --target measure -t zhocr:measure -f "$here/skripte/Dockerfile.messung" "$context" >/dev/null
rmdir "$context"

# Network cut, the source tree of the branch read only, OMP_THREAD_LIMIT=1 as
# findling.extract.ocr sets it for every engine call anyway, and the user of
# the caller, so that the pages in <scratch dir> can be removed again.
run() {
    docker run --rm --network none --user "$(id -u):$(id -g)" \
        -e OMP_THREAD_LIMIT=1 -e PYTHONPATH=/src \
        -v "$repo/backend/src:/src:ro" -v "$repo/testdata:/testdata:ro" \
        -v "$here/skripte:/skripte:ro" -v "$laws:/laws:ro" -v "$scratch:/scratch" \
        -w /tmp zhocr:measure "$@"
}

rm -rf "$scratch/pages"
run python /skripte/zh_ocr_pages.py /laws /scratch/pages > "$raw/seiten-schriften.txt"
cp "$scratch/pages/manifest.txt" "$raw/seiten-manifest.txt"

for languages in deu+eng+fra chi_tra chi_tra+eng chi_tra+deu+eng+fra deu+eng+fra+chi_tra chi_tra+chi_tra_vert; do
    run python /skripte/zh_ocr_measure.py /scratch/pages "$languages" 6 > "$raw/seiten-$languages.jsonl"
done
python3 "$here/skripte/zh_ocr_summary.py" "$raw"/seiten-*.jsonl > "$raw/zusammenfassung.tsv"

for languages in deu+eng+fra deu+eng+fra+chi_tra chi_tra+deu+eng+fra chi_tra+eng; do
    echo "== FINDLING_OCR_LANGUAGES=$languages"
    run env FINDLING_OCR_LANGUAGES="$languages" python -m findling.extract.ocr_quality \
        --corpus /testdata/corpus --truth /testdata/corpus-truth.json || true
done > "$raw/dach.txt"

# The allowlist drops an entry it does not carry with a warning and goes on, so
# a list can be measured under a name it did not run with. The tool prints how
# many languages it really used; every count has to be the count of the name.
for languages in deu+eng+fra deu+eng+fra+chi_tra chi_tra+deu+eng+fra chi_tra+eng; do
    wanted=$(echo "$languages" | tr '+' '\n' | wc -l)
    grep -A 1 -x "== FINDLING_OCR_LANGUAGES=$languages" "$raw/dach.txt" | grep -q "languages=$wanted\$" || {
        echo "the DACH run of $languages did not use $wanted languages" >&2
        exit 1
    }
done

run python /skripte/zh_ocr_cost.py /testdata/corpus/13-ratsvorlage-scan.pdf \
    /scratch/pages/ming-clean-00-J0070017.pdf > "$raw/kosten.txt"

run python /skripte/zh_ocr_floor.py /scratch/pages /testdata/corpus \
    /testdata/corpus-truth.json 6 > "$raw/adressraum.txt"

run python /skripte/zh_ocr_errors.py /scratch/pages /testdata/corpus \
    /testdata/corpus-truth.json > "$raw/fehler.txt"

run python /skripte/zh_ocr_vertical.py /laws > "$raw/senkrecht.txt"
