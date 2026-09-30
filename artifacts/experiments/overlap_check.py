"""Find word 6-grams shared between the paper draft and the repository's prose.

Sources compared: README.md, ARCHITECTURE.md, the other top-level *.md reports,
docs/*.md and wiki/*.md, plus the abstracts/notes in artifacts/03_literature_matrix.md.
LaTeX commands are stripped from the paper before comparison.

Usage: python artifacts/experiments/overlap_check.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
N = 6


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:['\-][a-z0-9]+)*", text.lower())


def strip_latex(t: str) -> str:
    t = re.sub(r"(?m)%.*$", "", t)
    t = re.sub(r"\\(cite|ref|label|input|url|todo)\{[^}]*\}", " ", t)
    t = re.sub(r"\\[a-zA-Z]+\*?", " ", t)
    return t.replace("{", " ").replace("}", " ").replace("~", " ")


def grams(ws: list[str]) -> set[tuple[str, ...]]:
    return {tuple(ws[i:i + N]) for i in range(len(ws) - N + 1)}


def main() -> None:
    sources = [REPO / "README.md", REPO / "ARCHITECTURE.md"]
    sources += sorted(REPO.glob("*.md")) + sorted((REPO / "docs").glob("*.md")) + sorted((REPO / "wiki").glob("*.md"))
    sources += [REPO / "artifacts" / "03_literature_matrix.md"]
    src_grams: dict[tuple[str, ...], str] = {}
    for s in dict.fromkeys(sources):
        if s.exists():
            for g in grams(words(s.read_text(encoding="utf-8", errors="ignore"))):
                src_grams.setdefault(g, s.relative_to(REPO).as_posix())

    paper = sorted((REPO / "paper").rglob("*.tex"))
    total = 0
    for p in paper:
        ws = words(strip_latex(p.read_text(encoding="utf-8")))
        hits = []
        i = 0
        while i <= len(ws) - N:
            g = tuple(ws[i:i + N])
            if g in src_grams:
                j = i + N
                while j < len(ws) and tuple(ws[j - N + 1:j + 1]) in src_grams:
                    j += 1
                hits.append((" ".join(ws[i:j]), src_grams[g]))
                i = j
            else:
                i += 1
        for h, src in hits:
            print(f"{p.relative_to(REPO)}: [{src}] {h}")
        total += len(hits)
    print(f"TOTAL overlapping spans (>= {N} words): {total}")


if __name__ == "__main__":
    main()
