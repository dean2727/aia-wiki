#!/bin/bash
# Usage: ./pdf-to-slides.sh "/path/to/file.pdf"
# Renders PDF pages as compressed JPEGs in /tmp/pdf_slides/

set -e

PDF="$1"
OUT="/tmp/pdf_slides"

if [ -z "$PDF" ]; then
  echo "Usage: $0 \"/path/to/file.pdf\""
  exit 1
fi

rm -rf "$OUT" && mkdir -p "$OUT"

pdftoppm -r 150 "$PDF" "$OUT/slide"

for f in "$OUT"/slide-*.ppm; do
  base="${f%.ppm}"
  sips -s format jpeg -s formatOptions 60 "$f" --out "${base}.jpg" 2>/dev/null
  rm "$f"
done

echo "Done. Slides written to $OUT:"
ls "$OUT"
