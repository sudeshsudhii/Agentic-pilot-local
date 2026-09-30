# Agentic Pilot IEEE paper — notes for the author

This branch has a first complete draft of the paper, `paper/main.pdf` (IEEEtran conference format). Every supporting artifact is in `artifacts/`. **The draft is yours to verify, revise and own.** An AI system wrote it from the code, from experiments it ran in a cloud container, and from references it checked. The Acknowledgment says so, as IEEE policy requires.

Build it with `paper/build.sh`, which runs pdflatex, bibtex, pdflatex, pdflatex. The build currently gives 0 LaTeX warnings and 0 BibTeX warnings.

---

## 1. Read this first: what the code review found

The paper describes the system **as the code actually behaves**, not as the README describes it. Wherever the two disagreed, the code wins. `artifacts/01_system_inventory.md` §0 and §14 have full `file:line` evidence. The headline findings:

1. **`python main.py --eval` does nothing.** It runs `scratch/*.py` scripts, but `scratch/` is gitignored and absent. `backend/experiment/runner.py:82` imports `create_agent_graph`, which does not exist. As a result, every ablation task fails immediately (A4 ran all 15 presets and got 120 of 120 failed).
2. **Recovery strategies are labels only.** `alternative_selector`, `vision_fallback` and `replan` are recorded but never executed. The `recovery_strategy` key is not in `AgentState`, so LangGraph drops it, and every retry re-observes the page and re-plans.
3. **Memory is written but never read on the live path.** `runner.py:265-266` seeds `retrieved_*=[]`, and `rag/router.py:71-77` treats that as already retrieved. Knowledge RAG therefore never runs in production either.
4. **`enable_verification` is never read** by the agent, so the "no verification" ablation changes nothing.
5. **The routing cool-down (`model_switch_cooldown_steps`) is never read.** With a full model set installed, stickiness means the planner model is never used in a normal run (see Table V of the paper).
6. **The privacy auditor logs only Ollama calls.** `record_external_request` is never called, and the keyring `CredentialStore` is unused. "Zero exfiltration" is not a claim the paper can make; §VIII states a narrow, true property instead.
7. **⚠ Extraction is hard-coded to one case study** (`backend/agent/nodes.py:1100-1142`). Every `extract` action produces a "Kattankulathur campus" answer. When fewer than 3 matching lines are found, it returns **three fixed campus facts**. The click fallback also matches the literal `"srm"` (`nodes.py:1052`). **You must remove or generalize this before running any end-to-end evaluation**; otherwise extraction results are invalid. The paper carries a visible `\todo` about it in §IX.
8. **Repository "results" are not usable as evidence:**
   - `CERTIFICATION_REPORT.md` was committed as 1 PASS / 4 FAIL (`6a47c8b`), then as 5/5 PASS (`e812a71`) with no run log. Its PASS rule is only "status completed plus any PNG plus `trace.json`".
   - `VISION_VALIDATION.md` prints its success text unconditionally.
   - `benchmarks/run.py` hard-codes "Simulated" and "Estimated" figures.
   - `MEMORY_VALIDATION.md` retrieves 1 document from a 1-document store.

   None of these appears in the paper.
9. **The desktop capability is a prototype that is not connected.** `backend/desktop/executor.py` exists (PyAutoGUI and psutil), but no node, action type or API route calls it. Its only test checks that its methods exist. `code_executor._resolve_safe_path` does not confine paths (`../` escapes). The paper presents the local-system extension as a **design** (§IV-G, Table II), with the current status stated exactly.
10. **Test hygiene problems:**
    - `tests/test_task_runner.py` fails to collect on Python 3.11 (`NameError: Database`), which makes a plain `pytest -q` run 0 tests.
    - `test_action_failure_never_marks_completed` hangs in headless mode.
    - No test runs the compiled graph.

## 2. What was measured in this session (real numbers)

Environment: Linux container, 4 vCPU Xeon @ 2.8 GHz, 15 GiB, no GPU, Python 3.11.15, Playwright 1.56.0 / Chromium 141, LangGraph 1.2.12, **no Ollama and no live web**.

| What | Result | Source |
|---|---|---|
| Completion-gate study, 35 constructed end states (no LLM; offline pages via request interception) | Gate withheld 15 of 22 unsatisfied states. Dispatch-only accepts all 22. 1 of 13 satisfied states rejected. 7 misses, each traced to a missing check. Median 33.8 ms per decision. | `artifacts/experiments/verification_gate_study.py` → `results/verification_gate_{cases,summary}.csv` |
| Router resolution (no LLM) | Default install: every text role resolves to `qwen2.5:1.5b`, 3 of them via fallback. Full install, in agent call order: stickiness keeps `deepseek-r1:1.5b` for planning. | `artifacts/experiments/routing_default_install.py` → `results/routing_resolution.csv` |
| Test suite | 108 collected: 104 pass, 4 fail, 1 collection error. Observatory 20/20. Line coverage 62.0%. | `results/junit.xml`, `tests_by_file.csv`, `coverage_by_subsystem.csv` |

**Caveat for the gate study.** The fixtures and oracle labels were written by the AI editor. **Review every case and its label** in `verification_gate_study.py` (the `CASES` list). The FCR values depend on that case mix; the paper says so explicitly.

## 3. Every `\todo{}` in the PDF (all shown in red)

| Where | What you must do |
|---|---|
| Title block | Author names, affiliation, email |
| §V | Confirm the license; archive the evaluated version (tagged release, ideally with a DOI) |
| §VI Hardware | Record CPU, GPU/VRAM, RAM, OS, Ollama version and model digests for the end-to-end runs |
| §VI Task suite | Finalize the 30 tasks and their independent oracles; publish them |
| §VII End-to-end | Run the protocol. Report success rate, FCR, model calls, wall-clock time, recovery success, vision rate and evidence completeness per configuration, with Wilson 95% CIs |
| §VII Case study | Add before/after screenshots of one task where the gate rejected a premature completion and the agent then finished |
| §IX | Remove or generalize the case-study extraction code (see §1 item 7), or disclose it |
| Acknowledgment | Review the AI-assistance disclosure wording |

## 4. Before running the end-to-end protocol (§VI), make these code changes

1. Fix `experiment/runner.py` to use `build_graph()` and to connect the database. Alternatively, drive `TaskRunner` directly.
2. Make `verify_node` honor `enable_verification`: when it is False, accept at `should_verify_completion`.
3. Pass `options={"temperature": 0, "seed": <n>}` in `llm/gateway.py`.
4. Add a vision-only switch that withholds the DOM manifest.
5. Remove the case-study extraction code (item 7 above).
6. Optional, but needed before any memory or recovery ablation means anything:
   - initialize `retrieved_*` to `None` in `runner.py`;
   - add `recovery_strategy` to `AgentState` and act on it.
   - If you make these changes, update Table III and §IV-D/F of the paper so that they stay truthful.

`artifacts/04_results_raw.md` has the full protocol: `ollama pull` commands, the task-suite proposal, a CSV schema and metric definitions.

## 5. Things to verify yourself

- **References.** All 35 were verified to exist via search-index records of primary pages and the authors' own BibTeX; the sandbox blocked direct DOI and arXiv fetches.
  - Spot-check the ~10 DOIs listed in `artifacts/03_literature_matrix.md`.
  - Re-read the PDFs for the four claims marked ◐ in `artifacts/06_citation_audit.md` (Voyager, UFO, SeeAct and Table I cells).
- **Table I (related-work comparison).** Cells come only from what each paper reports, as read from abstracts and venue pages. "–" means not found there.
- **Chroma default embedding download** (§III): confirm that your installed chromadb version fetches its default embedding model on first use.
- **Similarity check.** Automatic 6-gram overlap against README/docs/wiki is clean (`artifacts/08_style_report.md`), but cited abstracts could not be compared offline. Run the conference's similarity checker.

## 6. Sections that most need your own rewriting

1. **Introduction:** the motivation and contribution list should be in your voice, and should reflect whatever you implement from §4 above.
2. **§VII Results:** once end-to-end data exist, restructure around them. The gate study then becomes a component analysis.
3. **§IV-G Local-system extension:** if you implement part of it before submission, change the status labels and tense.
4. **§VIII Ethics:** decide your position on the anti-detection browser settings (`pool.py:90-93,127,138`). Consider removing them, since the paper discloses them.
5. **Page budget:** the body is now about 8.1 pages including the red TODO text. End-to-end results will need space; candidates to move to an appendix or supplement are Table II (desktop predicates) and Table III (status).

## 7. Files

```
paper/            main.tex, sections/, figures/ (TikZ), tables/, references.bib, main.pdf, build.sh
artifacts/
  01_system_inventory.md        code-verified module map and discrepancies (A1)
  02_local_system_extension.md  desktop audit and extension design (A2)
  03_literature_matrix.md       35 verified references and comparison table (A3)
  04_results_raw.md             environment, test runs, eval status, protocol (A4)
  05_formal_model.tex           formal model (B1; also paper/sections/04c_formal_model.tex)
  06_citation_audit.md          C1
  07_claims_ledger.md           C2: every claim and its source
  08_style_report.md            C3
  09_mock_review.md             C5: hostile review, and how it was addressed
  experiments/                  gate study, routing study, overlap checker (all runnable)
  results/                      CSVs, logs, junit, coverage
```
