#!/bin/sh
# Package facts and the image size delta of tesseract-ocr-chi-tra, in the pinned
# base image of backend/Dockerfile. Builds the stages "ten" and "eleven" of
# Dockerfile.messung (the apt block without and with the pack) and compares
# their top layers, then reads the traineddata and the copyright files.
#
#     sh zh_ocr_image.sh <directory of Dockerfile.messung>
set -eu
here="$1"
base="python:3.13-slim-trixie@sha256:ffb752e139c0a19692a43af8d8523b274222dd68eebad5d583b45c2201c6e30a"
context="$(mktemp -d)"
docker build -q --target ten -t zhocr:ten -f "$here/Dockerfile.messung" "$context" >/dev/null
docker build -q --target eleven -t zhocr:eleven -f "$here/Dockerfile.messung" "$context" >/dev/null
rmdir "$context"

echo "== packages (apt-cache show in the base image)"
docker run --rm "$base" sh -c 'apt-get update -qq >/dev/null 2>&1
for p in tesseract-ocr-chi-tra tesseract-ocr-chi-tra-vert tesseract-ocr-ces; do
  apt-cache show "$p" | grep -E "^(Package|Version|Architecture|Source|Installed-Size|Size|SHA256):"
  echo
done
cat /etc/debian_version'

echo "== top layer of each stage, bytes"
for stage in ten eleven; do
  printf '%s\t%s\n' "$stage" "$(docker history --human=false --format '{{.Size}}' "zhocr:$stage" | head -n 1)"
done

echo "== inside the stage eleven"
docker run --rm zhocr:eleven sh -c 'tesseract --version 2>&1 | head -n 2
tesseract --list-langs 2>&1
stat -c "%s %n" /usr/share/tesseract-ocr/5/tessdata/chi_tra.traineddata
sha256sum /usr/share/tesseract-ocr/5/tessdata/chi_tra.traineddata
md5sum /usr/share/doc/tesseract-ocr-deu/copyright /usr/share/doc/tesseract-ocr-chi-tra/copyright'
