# 08 — Originality and Style Report (C3)

## Overlap with repository prose

**Method.** `artifacts/experiments/overlap_check.py` extracts every run of 6 or more words that appears both in the paper and in the repository's own prose. LaTeX commands are stripped first. The repository prose compared was:
- README.md, ARCHITECTURE.md and the other top-level `*.md` reports;
- `docs/*.md` and `wiki/*.md`;
- the agent-written literature matrix.

**Result on the current draft.** 4 overlapping spans (from `python3 artifacts/experiments/overlap_check.py`), all acceptable:

| Span | Source | Disposition |
|---|---|---|
| Paper title | FINAL_IMPLEMENTATION_REPORT.md | The author's own title, kept by instruction |
| Failure-type identifiers `captcha transient element_not_found …` | wiki/Architecture.md | Code identifiers, which cannot be paraphrased |
| Strategy identifiers `retry alternative_selector vision_fallback replan` | wiki/Agent-Execution-Lifecycle.md | Code identifiers |
| "on open or locally hostable models web" | literature matrix | Our own sub-agent's wording in a table caption; not external text |

**Rewritten.** One span from the matrix in §II-G, "whether small local models can complete verified GUI tasks", has been reworded.

**Not checked automatically.** Cited-paper abstracts could not be compared, because the sandbox blocked arXiv and ACL/NeurIPS pages. The prose was written without copying from them; Related Work paraphrases each work's contribution in one clause. The author should run a commercial similarity check (e.g., iThenticate via the conference) before submission.

## Style rules

| Rule | Check | Result |
|---|---|---|
| Banned words: delve, pivotal, seamless(ly), robust, leverage, furthermore, moreover, "today's", cutting-edge, revolutionary, state-of-the-art, novel | `grep -i` over `sections/`, `tables/`, `figures/` | 0 hits |
| No rhetorical questions | `grep "?"` | 0 hits |
| No bold in prose | `grep textbf sections/` | 0 hits (bold appears only in table legends) |
| Repeated sentence openings | count of ". This / It / We / The" | "The" 33, "We" 7, "This" 1, "It" 1; no runs of three identical openings found on read-through |
| Acronyms defined once | LLM (§I), DOM (abstract and §I), FCR (§I), PID (Tab. II caption); CAPTCHA, API, HTTP, JSON, URL, GPU treated as common | done |
| SI units and consistent numbers | ms, s, GiB, GHz with thin space; thousands separator `{,}` | done |
| Figures and tables referenced before they appear | every `\ref{fig:*}` / `\ref{tab:*}` precedes or accompanies its float | done |
| Marketing claims restated as scoped properties | "zero exfiltration" appears nowhere; privacy is stated as a narrow property in §VIII | done |
| Present tense only for implemented features | desktop extension labelled Proposed; strategies and memory retrieval described as "recorded but not executed" / "written but not read" | done |

## Tightening done for the page budget

- Architecture reduced to 3 paragraphs.
- The routing-configuration table was folded into the text; the file was moved to `artifacts/table_routing_config_unused.tex`.
- Results bullets converted to running text.
- Security, Setup and Implementation paragraphs shortened.

**Result.** The body is about 8.1 pages with the visible `\todo` markers and ends a quarter of the way down page 9; references take roughly 1.6 pages.
