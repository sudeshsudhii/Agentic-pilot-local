#!/bin/sh
# Build report.pdf (needs TeX Live with latex-extra, fonts-extra, publishers, pictures, plain-generic).
set -e
cd "$(dirname "$0")"
export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1794700800}
pdflatex -interaction=nonstopmode report.tex >/dev/null || true
bibtex report >/dev/null
pdflatex -interaction=nonstopmode report.tex >/dev/null || true
pdflatex -interaction=nonstopmode report.tex >/dev/null
