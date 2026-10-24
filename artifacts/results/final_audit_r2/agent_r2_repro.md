# Reproducibility audit (Agent 6, round 2)

Repository: /home/user/Agentic-pilot-local, branch `ccr-4b8200f0-5i3k5m`. I edited no repository files. All runs used fresh `git clone`s under <audit scratch>/r2_repro/ (`repo` = aee8c50, `repo2` = 48864e5, `repo3` = 59d53e0).

**The branch moved while I worked.** It went aee8c50 → 48864e5 → fd0ab87 → 3a357e3 → 59d53e0, and other agents committed while the audit ran. I ran the full chain at aee8c50 and again at **59d53e0, which is the state reported below** unless a row says otherwise. Some issues I found at aee8c50 or 48864e5 are already fixed at 59d53e0. They are marked "FIXED in 59d53e0".

Environment: Linux 6.18.44, 4 vCPU Xeon @ 2.80 GHz, Python 3.11.15, pdfTeX 3.141592653-2.6-1.40.25 (TeX Live 2023/Debian), IEEEtran.cls V1.8b, IEEEtran.bst. Given venv: playwright 1.63.0, langgraph 1.2.12, chromadb 1.5.9. I also built a second venv, `r2_repro/venv156`, from `backend/requirements.txt` plus `playwright==1.56.0` and `langgraph==1.2.12`, with `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`; its Chromium build is 1194, which is Chromium 141.

## 1. Reproducibility checklist

| Artifact / command | Exists? | Regenerates identically? | Time | Notes |
|---|---|---|---|---|
| `python -m benchmarks.simulation.simulate_v2` → `out/heldout_v2/{results.json,scenarios.csv,recovery_scenarios.csv}` | yes | **yes, byte-identical** (aee8c50 and 59d53e0) | 35.8 s / 31.9 s | Needs the venv (imports `benchmarks.e2e.stats`). Deterministic: seed 202, 1000 MC replications. |
| `python -m benchmarks.simulation.make_tables` → 9 `paper/tables/sim/*.tex` + `out/heldout_v2/ledger_simulation.csv` | yes | **yes, byte-identical** (both commits) | 0.06 s | Also reads `artifacts/results/verification_gate_cases.csv` (gate timing), so re-running the gate study first changes `overhead.tex`. |
| `python artifacts/experiments/gate_stats.py` → `artifacts/results/gate_stats.csv` | yes | **yes, byte-identical** (system python and venv; both commits) | 0.12–0.16 s | Also byte-identical when fed freshly regenerated `verification_gate_cases.csv`. |
| `gate_stats.py` stdout vs `artifacts/results/gate_stats.txt` | yes | aee8c50/48864e5: **NO**. 9 lines differed and 3 were missing; the file dated from 2026-10-04 (55ac1ea) and lacked `p_correct_vs_dispatch`, `pre_*` and the `held_out_1+2` rows. **FIXED in 59d53e0** (now identical). | – | |
| LaTeX build (`pdflatex`, `bibtex`, `pdflatex` ×2 = `paper/build.sh`) | yes | aee8c50: PDF identical apart from `/CreationDate`, `/ModDate` and `/ID`; `main.bbl` byte-identical. **48864e5: committed `main.pdf` was stale**: sources changed, PDF not rebuilt (rebuilt 410,782 B vs committed 409,087 B). 59d53e0: identical apart from dates/ID (420,154 B, 17 pages). | 8.2 s cold, 3.7 s warm | 59d53e0 adds a new warning, **"Float too large for page by 50.0pt"**, from `tables/sim/params.tex` (line 41). aee8c50 had 0 LaTeX and 0 BibTeX warnings. With `SOURCE_DATE_EPOCH=$(git log -1 --format=%ct) FORCE_SOURCE_DATE=1`, two builds were bit-identical (sha256 4d750fe4…). |
| `python -m benchmarks.simulation.simulate --set heldout` (v1) → `out/heldout/` | yes | yes, byte-identical | 15.8 s | Writes `out/heldout/`, **not** `out/heldout_v1/`. |
| `python -m benchmarks.simulation.simulate --set dev` → `out/dev/` | yes | **NO**: `out/dev/results.json` latency block is stale (80 lines differ); `scenarios.csv` and `recovery_scenarios.csv` are identical | 15.1 s | `simulate.py`'s latency model changed (41a6097/1615ac5); held-out was regenerated, dev was not. Dev is not reported in the paper. |
| `python -m benchmarks.simulation.decision_analysis` → `out/heldout/decision_analysis.json` | yes | yes | 0.08 s | Reads and writes `out/heldout/` (v1). |
| `out/heldout/mc_paired_fc_diff.json`, `out/heldout{,_v1}/ledger_simulation.csv` | yes | **no generator in the repo** | – | Orphans from older script versions; `make_tables` now writes the ledger only to `heldout_v2`. |
| `python -m benchmarks.simulation.measure_inputs` → `inputs/m1..m4` | yes | Given venv: **FAILS** (Playwright 1.63 needs chromium-1243; container has 1194). venv156: m1, m3, m4 byte-identical; m2 (latency) differs, as expected for timings. | 43 s | Propagating the new m2 through simulate_v2 + make_tables changes only `overhead.tex` (e.g. "80%/4.1%" → "81%/3.0%"). M4 needs Chroma's ONNX embedding model in `~/.cache/chroma` (network on first use). |
| `python artifacts/experiments/verification_gate_study.py` → `verification_gate_cases.csv`, `_summary.csv` | yes | venv156: decisions in all 92 rows identical; only `gate_ms_median` differs (median 28.1 vs 26.7 ms); `_summary.csv` byte-identical; run log identical after timing lines are excluded | 74 s | Fails under the given venv (Playwright 1.63). |
| `... verification_gate_study.py --ablation` → `verification_gate_ablation.csv/.log` | yes | **yes, byte-identical** (csv and log) | 31 s | venv156 only. |
| `python -m benchmarks.e2e.validate_oracle` → `e2e_oracle_validation.{csv,txt}` | yes | txt byte-identical (114/114); csv differs only in the ephemeral port in final URLs | 34 s | `python benchmarks/e2e/validate_oracle.py` (script form) fails with ModuleNotFoundError; only `-m` works. |
| `benchmarks/e2e/egress/summarize_egress.py` → `egress_summary.json` | yes (59d53e0) | yes | <1 s | aee8c50/48864e5: raw `episodes.jsonl` and `egress_raw.jsonl` existed only in the working tree, ignored by `*.jsonl` in `.gitignore`, and had no generator. **FIXED in 59d53e0** (both committed and a summarizer added). I verified 555/555 connections to 127.0.0.1:11435, 8 pids, 70 episodes, 0 non-local page hosts. |
| `benchmarks/simulation/independent_validator.py` | yes | **not runnable elsewhere** | – | Hard-coded `BASE=/home/user/...` and `OUT=/tmp/claude-0/.../scratchpad/validation_report.md`. I did not run it here because it would overwrite a file in the shared scratchpad. |
| v2 recomputation scripts (`recompute_sim.py`, `recompute_gate.py`, `recompute_rates.py`, `wilson.py`), cited in `2_NUMERICAL_CONSISTENCY_REPORT.md`, `audit_final_independent_review.md` and §VI ("a final reviewer recomputed with separately written code") | **NO (scratchpad only)** | – | – | The paper's v2 validation claim cannot be re-checked from the repo. |
| `paper/tables/gate_results.tex`, `tables/ablation.tex` | yes | hand-transcribed, no generator | – | I spot-checked p = .021, .022, 1.0 and 20/23, 9/22, 11/27 against `gate_stats.csv`: they match. |
| `artifacts/results/gate_heldout2_freeze.txt` (SHA-256 of `gate_heldout2.py`) | yes | hash matches the file at HEAD and at b9d5088 | – | |
| pytest suite (paper: 144/147 pass) | `pytest_revision.txt` says "3 failed, 144 passed" | not rerun | – | |

## 2. Identifier extraction (paper, README_FOR_AUTHOR.md, AUTHOR_ACTIONS.md, final_audit/*.md)

Method: I extracted every `\texttt`/`\url` from `paper/sections/*.tex`, `tables/*.tex` and `tables/sim/*.tex`, plus every backtick span from the markdown files. 168 path-like tokens came from the markdown files; the full list is in `r2_repro/paths_md.txt`. Each was checked against `git ls-files`, git objects or a code grep.

**Commits:** all exist and are ancestors of HEAD: bf0a8a5, 2361d50, 08653e2, 3a0aa8e, 41a6097, 1435fe9, 55ac1ea, b9d5088, 5359458, eb3803e, 90e250b, 1615ac5, b55670b, dc5f2eb, e56c293, f3edacc. a474924 and 7654519 exist only on origin/main, as expected. Two claims also check out: `git diff bf0a8a5 HEAD -- backend` is empty ("agent code unchanged since bf0a8a5" holds), and `params.json` and `simulate.py` were committed in 3a0aa8e, 7 min before `out/heldout` was added in 41a6097.

**Seeds and configs:** dev seed 101, held-out seed 202, 100 scenarios and 1000 MC replications are in `params.json` and match the paper. E2E seed 7 is the default. All config names exist in the code: `full`, `no_verification`, `self_verification`, `no_memory`, `no_recovery`, `vision_only_grounding`, `single_model`, `no_evidence`, `recovery_{retry,vision,replan}_only`, and `gate_without_{E,H,Q,T,X,R,B}` (generated dynamically in `run_e2e.py:43`). The switches `verification_mode`, `enable_recovery`, `enable_memory`, `PILOT_LLM_TEMPERATURE`, `PILOT_LLM_SEED`, `PILOT_ALLOW_REMOTE_MODEL` and `PILOT_EGRESS_LOG` also exist. `action_gate` appears only as a proposed design ("would"), which is fine. All model tags exist in `backend/config.py`.

**Commands in AUTHOR_ACTIONS.md:** `run_e2e` (`--split/--trials/--configs/--out/--tasks`), `analyze_e2e` (`run_dir --split`), `python -m benchmarks.e2e.sites` (port 8800), `sites.snapshot_state`, `oracle.evaluate` and task D01 all exist. tasks.json has 40 tasks: 10 dev and 30 test.

**Missing or wrong references:**

| Reference | Where | Status |
|---|---|---|
| `paper/sections/04c_formal_model.tex` | README_FOR_AUTHOR §5 | missing |
| `results/junit_after_fixes.xml` | README_FOR_AUTHOR §1 | wrong path (actual: `artifacts/results/junit_after_fixes.xml`) |
| `coverage_after_fixes.txt` | README_FOR_AUTHOR | actual: `artifacts/results/` |
| "9 pages: 8 pages of body", "0 LaTeX warnings", "129 tests: 126 pass", "Median 30.6 ms", "38 design states", "each is a `\todo` … [Pending]" | README_FOR_AUTHOR §1–2 | stale: the PDF is 17 pages with 1 warning, 147/144 tests, 26.8 ms, 92 states, 0 `\todo`. The header warns that older notes may differ. |
| `gate_stats_corrected_tests.csv` | audit_final_independent_review.md #15 | missing; superseded by `gate_stats.py` columns, per the aee8c50 message |
| `recompute_*.py`, `wilson.py`, `rerun/`, `paper_build*/` | 2_NUMERICAL_CONSISTENCY_REPORT.md, audit_final_independent_review.md | scratchpad only |
| `audit_gate.py`, `audit_sim.py`, `extra.py`, `corrected.py`, `decision_acc.py`, `rerun.py`, `validator.py`, `egress.jsonl` | audit_stats/method/integrity/privacy.md | scratchpad only |
| `.venv-eval/bin/python` | audit_stats.md | ignored local venv |
| `analysis/*.csv/json/tex`, `episodes.jsonl` (e2e) | AUTHOR_ACTIONS A1 | future outputs (OK) |
| `backend/llm/gemini.py`, `hybrid.py` | audit_integrity.md | exist on origin/main only (OK, cited as divergence evidence) |

## 3. Machine-specific paths and environment assumptions

- **Scripts:** `benchmarks/simulation/independent_validator.py:6-7` hard-codes `/home/user/Agentic-pilot-local/...` and `/tmp/claude-0/-home-user-Agentic-pilot-local/9002c3ac-.../scratchpad/validation_report.md`. This is disclosed in §14_simparams but not fixed. No other `.py`, `.sh`, `Makefile` or `.tex` file has absolute paths.
- **Reports:** `artifacts/results/simulation_validation_report.md:3` and `final_audit/audit_stats.md:9` point readers to the scratchpad path. `audit_integrity.md:145` notes this. `artifacts/01_system_inventory.md:3` names `/home/user/Agentic-pilot-local` and `04_results_raw.md:22` names `/opt/pw-browsers/chromium-1194`; both are descriptive. About 700 occurrences of `/home/user/...` appear in raw logs (`pytest_*.txt`, `coverage_*.txt`, `junit*.xml`, `experiment_runner_probe/*`). These are acceptable as raw logs.
- **Environment assumptions:**
  - The gate study and `measure_inputs` require Playwright 1.56 with Chromium build 1194 at `PLAYWRIGHT_BROWSERS_PATH`. A fresh `pip install -r backend/requirements.txt` resolves Playwright 1.63, which looks for a different browser build, and LangGraph 1.2.17 rather than 1.2.12.
  - M4 needs Chroma's default ONNX embedding model in `~/.cache/chroma`.
  - `gate_stats.py:rows()` silently returns `[]` when an input CSV is missing, so a partial checkout yields a shorter `gate_stats.csv` without an error.
  - CI (`.github/workflows/ci.yml`) runs only on `main`, uses Python 3.11 and runs ruff plus the frontend build only. It never runs pytest or the paper chain on the evaluated branch.
  - Gate timings and M2 latencies are machine-dependent, and `m2_latency.json` records no host or software metadata.

## 4. Version consistency

| Item | Paper (06_methodology.tex:4, :32) | Requirements / lock | Other records |
|---|---|---|---|
| Python | 3.11.15 | none pinned; README "3.11+", `main.py` "3.10+", `setup.sh` tries 3.12 first, CI 3.11 | given venv 3.11.15 |
| Playwright | 1.56.0 | `playwright>=1.45.0` (resolves to 1.63.0 today) | `04_results_raw.md:40` documents the manual pin to 1.56.0; given venv has **1.63.0** |
| Chromium | 141 | not pinned (follows Playwright) | `/opt/pw-browsers/chromium-1194` = 141.0.7390.37 |
| LangGraph | 1.2.12 | `langgraph>=0.2.0` (fresh resolve gives 1.2.17) | given venv 1.2.12 |
| Chroma | not stated | `chromadb>=0.5.0` | 1.5.9 (04_results_raw). Telemetry behaviour, which the paper relies on, is version-dependent. |
| TeX | not stated | – | TeX Live 2023, IEEEtran 1.8b |
| CPU | 2.1 GHz (10-04 runs) and 2.8 GHz (10-23 runs) | – | CHANGE_LOG:76 explains the two containers. `07_claims_ledger.md` N7 still says 2.8 GHz for §VI. No `/proc/cpuinfo` record is committed for the 2.1 GHz run. |

There is no lock file: no `requirements.lock`, `pip freeze` output, `uv.lock` or `pyproject` pins. Freezes of both venvs are in `r2_repro/venv_given_freeze.txt` and `venv156_freeze.txt`. They already differ in fastapi, aiohttp, langchain-core and others.

## 5. Committed state of simulation inputs and outputs

- **Committed:** `params.json`, `inputs/m1..m4`, `out/heldout_v2/{scenarios,recovery_scenarios,results,ledger_simulation}`, `out/heldout_v1/*`, `out/heldout/*`, `out/dev/*`, `artifacts/results/simulation_validation_report.md` (v1) and `final_audit/*`.
- **Duplicates:** all 6 files in `out/heldout/` are byte-identical to `out/heldout_v1/`. They can diverge silently, because `simulate.py --set heldout` and `decision_analysis.py` write to `out/heldout/` while the paper cites `out/heldout_v1/` as the archive. `out/heldout_v2/` has no `decision_analysis.json` or `mc_paired_fc_diff.json` (the v2 equivalents are inside `results.json`), so a reader comparing directories sees v1-only files and may take them as current.
- `out/dev/results.json` is stale (see checklist).
- `results/README.md` (the index README_FOR_AUTHOR points to) has **no simulation entry** and lists `gate_stats.txt` as an output of `gate_stats.py`, which only prints to stdout.
- §14_simparams says "All are regenerated by `simulate_v2` and `make_tables`". That covers v2 outputs and tables only. It does not cover the v1 validation report, `out/heldout_v1`, the measured inputs (`measure_inputs`) or the gate cases (`verification_gate_study.py`).

## 6. Tags, release and branch divergence

- `git tag` is empty and `git ls-remote --tags origin` returns no tags.
- Remote heads: `main` = 7654519 (2026-10-09) and `ccr-4b8200f0-5i3k5m` = 59d53e0. The merge base with main is 2361d50. The branch is 47 commits ahead of main and 2 behind. The 2 main-only commits (a474924, 7654519) add a Gemini provider, hybrid LLM routing and Windows desktop automation: 42 files, +6,200 lines, 30 files under `backend/`.
- §V correctly says the default branch has diverged and that no tag exists. However, every cited hash lives only on an auto-generated session branch. Deleting or force-pushing that branch would orphan them.

## 7. Findings and exact fixes

1. **No immutable release (High).** Freeze the paper, rebuild the PDF, then run `git tag -a paper-ieee-v1.0 -m "Agentic Pilot paper, evaluated version (agent code bf0a8a5)" <final-commit> && git push origin paper-ieee-v1.0`. Create a GitHub release from the tag and enable Zenodo for a DOI. The tag should contain:
   - `paper/` (sources, `main.pdf`, `main.bbl`);
   - `benchmarks/` (simulation inputs, params and all `out/`, plus the e2e harness, tasks and oracle);
   - `artifacts/experiments/` and `artifacts/results/` (including `final_audit/` and `e2e_smoke_stub/*.jsonl`);
   - `backend/` at bf0a8a5 content;
   - a new `requirements-paper.lock` (`pip freeze` of the run environment, with `playwright==1.56.0`, `langgraph==1.2.12`, `chromadb==1.5.9`);
   - a short `REPRODUCE.md` (finding 4).
   
   Then replace "branch `ccr-4b8200f0-5i3k5m`" in `05_implementation.tex` with the tag name and DOI, and rename or protect the session branch.
2. **Unpinned dependencies; the shipped venv cannot run the measurement scripts (High).** Add `requirements-paper.lock` (see above) and state in §VI that installing it plus `PLAYWRIGHT_BROWSERS_PATH` containing chromium-1194 (or `playwright install chromium` under 1.56.0) is required. Record Chroma 1.5.9 and TeX Live 2023 / IEEEtran 1.8b in §VI or the README.
3. **Oversized float at 59d53e0 (Medium, new).** `tables/sim/params.tex` is 50 pt too tall for the page. Shorten rows or move them to a `table*`, then rebuild and confirm `grep -c "Float too large" main.log` is 0.
4. **No single regeneration entry point (Medium).** Add a `Makefile` target (or `scripts/reproduce_paper.sh`) that runs, in order:
   - `python -m benchmarks.simulation.simulate_v2`
   - `python -m benchmarks.simulation.make_tables`
   - `python artifacts/experiments/gate_stats.py > artifacts/results/gate_stats.txt`
   - `python benchmarks/e2e/egress/summarize_egress.py artifacts/results/e2e_smoke_stub`
   - `SOURCE_DATE_EPOCH=$(git log -1 --format=%ct) FORCE_SOURCE_DATE=1 sh paper/build.sh`
   - `git diff --exit-code`
   
   Add an optional `measure` target for `measure_inputs` and `verification_gate_study.py`, plus `--ablation` and `validate_oracle`, documenting that their timings differ by machine. Run it in CI on the paper branch.
5. **Non-deterministic PDF (Low).** Add `export SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-$(git log -1 --format=%ct)}; export FORCE_SOURCE_DATE=1` to `paper/build.sh`. Two builds were then bit-identical in my test.
6. **Stale PDF risk (Medium; happened at 48864e5).** Add a pre-commit or CI check that rebuilds and compares the PDF with dates and ID masked. Never commit `paper/sections` changes without `main.pdf`.
7. **`independent_validator.py` hard-coded paths (Medium).** Replace lines 6–7 with `BASE = Path(__file__).parent / "out" / "heldout_v1"` and an `--out` argument defaulting to `artifacts/results/simulation_validation_report.md`. Then drop "contains absolute paths" from §14_simparams.
8. **v2 recomputation code not committed (Medium).** Commit `recompute_sim.py`, `recompute_gate.py`, `recompute_rates.py` and `wilson.py` under `artifacts/results/final_audit/scripts/` with relative paths. Otherwise reword §VI ("a final reviewer recomputed…") and the final-audit reports to say the code is not archived. Also remove the scratchpad paths from `simulation_validation_report.md:3` and `audit_stats.md:9`.
9. **Duplicate v1 outputs (Low).** Keep only one v1 directory. Either `git rm -r benchmarks/simulation/out/heldout` and change `simulate.py` (`out = HERE/"out"/("heldout_v1" if set_name=="heldout" else set_name)`) and `decision_analysis.py:74,77` to `heldout_v1`, or add `out/README.md` saying `heldout` is the v1 working copy, `heldout_v1` its frozen archive and `heldout_v2` the reported model. Remove or annotate the generator-less orphans `out/heldout*/mc_paired_fc_diff.json` and `ledger_simulation.csv`.
10. **Stale `out/dev/results.json` (Low).** Regenerate it with `python -m benchmarks.simulation.simulate --set dev` and commit.
11. **Silent missing-input handling in `gate_stats.py` (Low).** Change `rows()` to raise `FileNotFoundError` for `verification_gate_cases.csv` and `verification_gate_ablation.csv`, keeping the soft fallback only for `*_before_fixes.csv` if it is optional.
12. **Index and docs drift (Low).**
    - Add a simulation row to `results/README.md`: `benchmarks/simulation/{measure_inputs,simulate_v2,make_tables}.py` → `inputs/`, `out/heldout_v2/`, `paper/tables/sim/`, seeds 101/202.
    - In README_FOR_AUTHOR, correct `results/junit_after_fixes.xml` → `artifacts/results/...`, remove the `paper/sections/04c_formal_model.tex` reference, and update the page count, test counts, gate latency and the `\todo` section, or mark them historical.
    - Update `07_claims_ledger.md` N7 to the 2.1 GHz / 2.8 GHz split.
    - Fix `validate_oracle.py` usage to `python -m benchmarks.e2e.validate_oracle`, or add a `sys.path` insert as in `gate_stats.py`.
13. **Overclaim in §14_simparams (Low).** Change "All are regenerated by … `simulate_v2` and `make_tables`" to "The v2 outputs and the simulation tables are regenerated by …; the measured inputs by `measure_inputs` (timings machine-dependent); v1 outputs by `simulate --set heldout`".
14. **Hand-transcribed gate tables (Low).** `tables/gate_results.tex` and `tables/ablation.tex` have no generator. Values match `gate_stats.csv` today, but add a `gate_tables.py` that writes them from `gate_stats.csv`, as `make_tables` does for the simulation tables.
15. **Already fixed during this audit (in 59d53e0):** `gate_stats.txt` regenerated; raw egress logs committed with a `.gitignore` exception and a summarizer; `main.pdf` rebuilt after 48864e5.
