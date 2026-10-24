#!/bin/sh
# Build main.pdf (run from any directory).
set -e
cd "$(dirname "$0")"
# reproducible PDF: fixed dates and ID from the last commit (TeX Live 2023, IEEEtran 1.8b)
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct 2>/dev/null || echo 0)}
FORCE_SOURCE_DATE=1
export SOURCE_DATE_EPOCH FORCE_SOURCE_DATE
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
bibtex main >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
pdflatex -interaction=nonstopmode -halt-on-error main.tex >/dev/null
grep -E "Warning|Overfull|Output written" main.log || true
