#!/bin/sh
# Build main.pdf and supplement.pdf (run from any directory); the two documents cross-reference each other.
set -e
cd "$(dirname "$0")"
# reproducible PDF: fixed dates and ID from the last commit (TeX Live 2023, IEEEtran 1.8b)
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct 2>/dev/null || echo 0)}
FORCE_SOURCE_DATE=1
export SOURCE_DATE_EPOCH FORCE_SOURCE_DATE
for d in main supplement; do pdflatex -interaction=nonstopmode -halt-on-error $d.tex >/dev/null; bibtex $d >/dev/null; done
for i in 1 2; do for d in main supplement; do pdflatex -interaction=nonstopmode -halt-on-error $d.tex >/dev/null; done; done
grep -E "Warning|Overfull|Output written" main.log supplement.log | grep -v "Font Warning" || true
