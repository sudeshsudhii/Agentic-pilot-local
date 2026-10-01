# Agentic Pilot IEEE paper — notes for the author

> **Reframed (2026-10-01).** Title restored at the author's request to "Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation". The Introduction now defines *autonomous* (no step-by-step instructions; high-risk tasks and CAPTCHAs still go to the user) and *privacy-preserving* (by default no prompt or screenshot leaves the machine for a model provider), and §IX lists what this does not cover. Expect reviewers to probe both words. The browser is the implemented backend; the computer backend (desktop, files, processes, windows) is a design with an unintegrated prototype. See `artifacts/11_reframing_report.md` for what changed, what is implemented, missing evidence and reviewer risks, and `artifacts/10_computer_use_audit.md` for the capability audit. The proposed computer-use protocol is Table V; only its browser family can run with the current code.

This branch holds a complete draft paper, `paper/main.pdf` (IEEEtran conference, 9 pages: 8 pages of body plus references). It also holds the code fixes the paper describes and all supporting artifacts in `artifacts/`.

**The draft is yours to verify, revise and own.** An AI system wrote it, and the Acknowledgment says so, as IEEE policy requires. Build it with `paper/build.sh`; it currently builds with 0 LaTeX and 0 BibTeX warnings.

## 1. Status: what is done and what is not

**Not ready to submit.** One result is missing: **end-to-end runs with local models on real websites.** The drafting container had neither Ollama nor web access. Everything else that can be done without them is done.

### Fixed in code (commits `5359458` and `eb3803e`; paper §V)

| Problem found by the audit | Fix |
|---|---|
| Extraction fabricated SRM "campus facts" (`nodes.py:1100-1142`), and a click rule matched `"srm"` | Removed. Extraction now keeps only page lines that share terms with the goal, and invents nothing. |
| The gate accepted any action's reasoning as an answer, and a bare `complete` marked a pending step done | Fixed in `verify_node` |
| Gate gaps: wrong-query results, soft 404s, login walls, superset text, long irrelevant answers | New checks in `verify_task_completion`: Q, E, T, X, R |
| CAPTCHA false positives (a "Robot" article, hidden or invisible reCAPTCHA) | Title wording made specific; frames must be visible and not invisible-reCAPTCHA |
| The exact-text regex hijacked "blood type of…" and "Enter Sandman" | The verb must start a clause |
| `enable_verification` was ignored | Honoured; the "no gate" ablation now works |
| Recovery strategies were dropped | Kept in state. `vision_fallback` now acts when a vision model is installed. `alternative_selector` and `replan` are still labels only. |
| Memory and RAG retrieval never ran | The runner seeds `None`, so retrieval runs. Its effect is **not measured**. |
| Routing matched substrings ("guide" counted as "gui") | Whole-word matching |
| Routing stickiness leaked across tasks and into recovery | Stickiness is task-local; recovery is not routed |
| `main.py --eval` did nothing, and `ExperimentRunner` imported a missing function | `--eval` runs the presets: full, no_verification, no_recovery, vision_only_grounding, single_model, no_memory |
| No sampling control | `PILOT_LLM_TEMPERATURE`, `PILOT_LLM_SEED` |
| Tests: a collection error, a headless hang, a broken mock, a missing directory | All fixed; 19 regression tests added in `tests/test_verification_fixes.py` |

### Measured in this session

Environment: 4 vCPU Xeon, Python 3.11, Playwright 1.56 / Chromium 141, LangGraph 1.2.12. No Ollama, no web.

| What | Result | Source |
|---|---|---|
| Gate study, 38 design states (23 unsatisfied) | **Before fixes:** 15 caught by the predicate alone, 13–14 inside the live node; 3 of 15 satisfied states rejected. **After:** 20 of 23 caught and 1 of 15 rejected, the same in every mode. | `artifacts/results/verification_gate_cases{,_before_fixes}.csv` |
| Gate study, 12 held-out states, written after the fixes | Before: 1 of 5 caught. After: **2 of 5** caught. 1 of 7 rejected both times. **Rule fixes generalize only partially.** | same files, `split=held_out` |
| Gate latency | Median 30.6 ms per decision | `verification_gate_run.log` |
| Routing | Fixes confirmed. One trade-off remains: with all models installed, the planner model is never used within a normal task, because of within-task stickiness. | `routing_resolution*.csv` |
| Tests | 129 tests: 126 pass. The 3 failures need live web (one also needs Ollama). 0 collection errors. Observatory 20/20. Coverage 65.0% (was 62.0%). | `results/junit_after_fixes.xml`, `coverage_after_fixes.txt` |

**Caveat:** I wrote all fixtures and labels, and designed the fixes on the design states. Treat the post-fix design numbers as optimistic; the held-out row is the honest one. Review every case in `artifacts/experiments/verification_gate_study.py`.

## 2. What you must do (all shown as red `\todo` in the PDF)

| Where | Action |
|---|---|
| Title block | Author names, affiliation, email |
| §V | Confirm the license; archive this version (tagged release with a DOI) |
| §VI | Record hardware, OS, Ollama version and model digests |
| §VI | Finalize and publish the 30 tasks and their independent oracles |
| §VII-D | **Run the end-to-end protocol** (below) and report the metrics with 95% CIs |
| §VII-D | Add a screenshot case study from `~/.pilot/logs/evidence/<task_id>/` |
| Acknowledgment | Review the AI-assistance wording |

### Running the end-to-end protocol on your machine

```bash
ollama pull qwen2.5:1.5b && ollama pull moondream        # default configuration
# optional full role set: qwen2.5:7b qwen3.5:2b deepseek-r1:1.5b qwen3-vl:2b qwen2.5-coder:3b
export PILOT_LLM_TEMPERATURE=0 PILOT_LLM_SEED=7 PILOT_HEADLESS_BROWSER=true
python main.py --eval                 # all presets; or PILOT_EVAL_PRESETS="full_framework,no_verification"
```

The runner writes per-task status, duration and step counts to `~/.pilot/experiments/`. Set `runs_per_task=3` in the presets (`backend/experiment/config.py`) for three trials. Pass the 30-task list via `run_ablation_comparison(tasks=...)`. **FCR needs your independent oracle** applied to the final screenshots; the agent's own status is not the ground truth. `artifacts/04_results_raw.md` has the CSV schema and metric definitions.

## 3. Things to verify yourself

- **References:**
  - Spot-check the ~10 DOIs listed in `artifacts/03_literature_matrix.md`.
  - Re-read the PDFs for the four claims marked ◐ in `artifacts/06_citation_audit.md`.
- **Chroma:** confirm the default embedding download and the telemetry behaviour of your installed version (§III).
- **Similarity check:** run the conference's similarity checker. The local 6-gram check against README/docs/wiki is clean.
- **Code review:** read the code diff (`git show 5359458`). In particular, check the new checks in `backend/verification/manager.py` against tasks you care about. They are still hand-written rules; see §IX.

## 4. Sections that most need your own voice

1. **Introduction:** motivation and contributions.
2. **§VII:** restructure around end-to-end results once you have them.
3. **§VIII Ethics:** the stance on the anti-detection browser settings (`pool.py:90-93,127,138`) must be yours. Consider removing them.
4. **Page budget:** end-to-end results need space. Move Table II (desktop) or Table III (status) to a supplement.

## 5. Files

```
paper/            main.tex, sections/, figures/ (TikZ), tables/, references.bib, main.pdf, build.sh
artifacts/
  01_system_inventory.md        code-verified module map and discrepancies at 2361d50 (A1)
  02_local_system_extension.md  desktop audit and extension design (A2)
  03_literature_matrix.md       35 verified references and comparison table (A3)
  04_results_raw.md             environment, original test runs, eval protocol (A4)
  05_formal_model.tex           formal model (also paper/sections/04c_formal_model.tex)
  06_citation_audit.md          C1
  07_claims_ledger.md           C2: every claim and its source
  08_style_report.md            C3
  09_mock_review.md             C5: hostile review and responses
  experiments/                  gate study, routing study, overlap checker (all runnable)
  results/                      CSVs, logs, junit, coverage (before and after the fixes)
```
