# R2 Experimental Evaluation Audit (Agent 3)

Repository: /home/user/Agentic-pilot-local, HEAD aee8c50, plus uncommitted paper edits that another agent was making while this audit ran (line numbers below refer to the working tree as of this audit). No repository file was edited.

## What I re-executed myself (scratch copy from `git archive HEAD`, venv with only pydantic and pydantic-settings)

| Re-run | Result |
|---|---|
| `python -m benchmarks.simulation.simulate_v2` (33 s) | `results.json`, `scenarios.csv`, `recovery_scenarios.csv` byte-identical to `benchmarks/simulation/out/heldout_v2/` |
| `python -m benchmarks.simulation.make_tables` | all 9 `paper/tables/sim/*.tex` and `ledger_simulation.csv` byte-identical |
| `python -m benchmarks.simulation.simulate --set heldout` (v1) | byte-identical to `out/heldout/`; `out/heldout` = `out/heldout_v1` (all 6 files) |
| `python benchmarks/simulation/independent_validator.py` (v1) | "DISCREPANCIES: 0" |
| `python artifacts/experiments/gate_stats.py` | `gate_stats.csv` byte-identical; stdout differs from committed `gate_stats.txt` (stale, see F7) |
| Recomputation from `verification_gate_cases.csv` | 92 states (38/12/42); 0 disagreements between the component, live-empty and live-verbose modes; Φ latency n=83, median 26.84, p90 29.47, p95 30.29, max 34.64 ms; pre-check-blocked n=9, max 13.36 ms. All match 07_results.tex:25 |
| Recomputation from `verification_gate_summary*_before_fixes.csv` | design before: withheld 15/14/13 (component/live-empty/live-verbose), FR 3; held-out-1 before 1/5, 1/7. Match 07_results.tex:11 and Table gate_results |
| Ablation table vs `gate_stats.csv` | every FC/FR cell and p value matches (H: 4 vs 0, p=0.125, shown as .13) |
| Freeze check | `sha256(artifacts/experiments/gate_heldout2.py)` = 15b85e6e… = value in `gate_heldout2_freeze.txt` = blob at b9d5088 (07:21:57); cases CSV written 07:25:33, so after the freeze |
| Stand-in run recomputation (`episodes.jsonl`, `egress_raw.jsonl`, both gitignored) | 70 episodes; 555 connections, all 127.0.0.1:11435, 8 PIDs; `browser_actions`=0 and `vision_called`=false in all 70; `knowledge_retrieved`=0; 54/60 memory-enabled episodes retrieved at least one memory; `non_local_page_hosts` empty in all |
| Oracle validation recomputation | 114 rows: golden 40 (35 intended 1, 5 unsatisfiable intended 0), idle 40 (2 intended 1: D01, T08), perturbed 34 (intended 0). 0 FN of 37, 0 FP of 77 |
| Simulation derived rates | Φ withhold: nav (2+.5)/7=.36, search 2.5/5=.50, text 1.5/4=.38, form (text+multi) 3.5/7=.50, extraction .5/7=.07, multi 2.5/4=.63; FR 0/24 → .02. Match params.tex |

Not re-run, because Playwright, Chromium and Chroma are not installed here: the gate study, `measure_inputs.py` (M1–M4), `validate_oracle.py`, the stand-in egress run and pytest. For these, executed? = Y rests on committed raw outputs, timestamps and commits.

## Experiment inventory

Class: ACTUAL = executed on the implementation; SYNTHETIC = simulation output; ANALYTIC = no execution.

| # | Experiment | Class | n | Script | Outputs | Regeneration command | Executed? (evidence) | Reproducible from text? |
|---|---|---|---|---|---|---|---|---|
| 1 | Gate study, current code: component mode plus live verify_node with empty and verbose reasoning | ACTUAL | 92 states (design 38, HO1 12, HO2 42) × 3 modes; latency = median of 20 reps per state | `artifacts/experiments/verification_gate_study.py` (+ `gate_heldout2.py`) | `artifacts/results/verification_gate_cases.csv`, `_summary.csv`, `_run.log` (2026-10-04 07:25, commit 55ac1ea) | `python artifacts/experiments/verification_gate_study.py --reps 20` | Y. Raw CSV with per-state decisions for all 3 modes; written after the HO2 freeze; every paper number recomputed | Partial. Counts, categories, oracle and statistics are described, but the states exist only in code and the paper gives no command |
| 1a | Gate study, code before the fixes | ACTUAL | 50 states (design + HO1) × 3 modes | same script (b55670b version) run against 08653e2 backend | `verification_gate_cases_before_fixes.csv`, `_summary_before_fixes.csv`, `_run_before_fixes.log` (2026-10-01, b55670b) | Not scripted. Roughly: `git worktree add /tmp/pre 08653e2`, copy in the b55670b study script, run it | Y. Design decisions identical to the 08653e2 committed output (38 states); HO1 run later on 2026-10-01 | Partial (see F10) |
| 1b | Ablation (E, H, Q, T, X, R, β) | ACTUAL | 92 states × 8 settings, component mode only | `verification_gate_study.py --ablation` | `verification_gate_ablation.csv`, `.log` (2026-10-04 07:26) | `python artifacts/experiments/verification_gate_study.py --ablation` | Y | Partial. Text does not say component-only, and β is removed by a script flag, not a configuration switch (F8) |
| 1c | Gate statistics (Wilson, Clopper-Pearson, exact McNemar) | DERIVED from 1, 1a, 1b | as above | `artifacts/experiments/gate_stats.py` | `gate_stats.csv` (2026-10-24, aee8c50); `gate_stats.txt` is stale | `python artifacts/experiments/gate_stats.py` | Y. Re-run is byte-identical | Y (with repo) |
| 2 | Component latency (M2): navigate, click, fill, DOM, screenshot, Φ on site pages | ACTUAL | 30 reps × 6 operations | `benchmarks/simulation/measure_inputs.py` (m2) | `benchmarks/simulation/inputs/m2_latency.json` (raw samples; 2026-10-23, 3a0aa8e) | `python -m benchmarks.simulation.measure_inputs` (runs M1–M4 together) | Y. Raw samples present; medians match Table sim-overhead | Partial. Pages and operations not specified; machine not recorded in the output (F11) |
| 2b | Φ latency on gate states | ACTUAL | 83 decisions (median of 20 reps each) | experiment 1 | `verification_gate_cases.csv:gate_ms_median` | as 1 | Y | Partial |
| 3 | Recovery classification (M3) | ACTUAL | 6 failure messages | `measure_inputs.py` (m3); also recomputed live in `simulate_v2.engine_sequences()` | `inputs/m3_recovery.csv` | as 2 | Y. The v2 re-run invokes the real `RecoveryEngine` and reproduces the sequences | Partial. The 6 messages are not given in the paper |
| 4 | Memory retrieval (M4) | ACTUAL on a synthetic corpus | 10 queries, 22 records, k=3 | `measure_inputs.py` (m4) | `inputs/m4_memory.csv` | as 2 | Y. P@3 .519, R@3 1.00, MRR .926 recomputed | Partial. Corpus and relevance-by-group rule are in code only |
| 4b | Basic-detector decisions (M1) | ACTUAL | 92 states | `measure_inputs.py` (m1) | `inputs/m1_gate_rules.csv` | as 2 | Y. `phi_accepts` and oracle identical to experiment 1 for all 92 states | Partial |
| 5 | Egress test with scripted stand-in Ollama | ACTUAL (harness, stand-in model) | 70 episodes (10 dev tasks × 7 configs), 555 connects | no script. Manual: `fake_ollama.py` + `egress/sitecustomize.py` + `run_e2e.py` | `e2e_smoke_stub/run_meta.json`, `egress_summary.json` (tracked); `episodes.jsonl`, `egress_raw.jsonl` (gitignored, not in repo; raw log mtime 2026-10-24 01:20, recovered from a session scratchpad per audit_privacy.md:23) | Not documented. Reconstructed: `python -m benchmarks.e2e.fake_ollama 11435 &` then `PYTHONPATH=benchmarks/e2e/egress:. PILOT_EGRESS_LOG=<f> PILOT_OLLAMA_BASE_URL=http://127.0.0.1:11435 PILOT_OLLAMA_MODEL=scripted-stub:latest python -m benchmarks.e2e.run_e2e --split dev --trials 1 --configs full,no_verification,self_verification,no_recovery,no_memory,gate_without_T,recovery_replan_only --out artifacts/results/e2e_smoke_stub`. No code produces `egress_summary.json` | Y, but on an unrecoverable dirty tree (git_dirty=true, base 1435fe9), and the raw evidence is not released (F1) | N. Not in the Methodology section; env vars and command appear nowhere in the paper (F2) |
| 5b | Reduced egress unit test | ACTUAL | 3 episodes, 1 config, memory/RAG off | `tests/test_local_egress.py::test_agent_episode_opens_no_non_loopback_connection` | `junit_revision.xml` (passed, 11.5 s) | `python -m pytest tests/test_local_egress.py` | Y | Y (test code) |
| 6 | Oracle validation | ACTUAL | 114 trajectories (40 golden, 40 idle, 34 near-miss) | `benchmarks/e2e/validate_oracle.py` | `e2e_oracle_validation.csv`, `.txt` (2026-10-04 07:30, bf0a8a5; oracle/tasks/sites unchanged since 55ac1ea) | `python -m benchmarks.e2e.validate_oracle` | Y | Y (with repo). Text overstates the false-positive test (F3) |
| 7 | Unit tests | ACTUAL | 147 tests: 144 pass, 3 fail | `pytest` (testpaths=tests) | `pytest_revision.txt`, `junit_revision.xml` (2026-10-04 07:31, after 55ac1ea; backend/ and tests/ unchanged to HEAD) | `python -m pytest` | Y | Partial. No command or date in the paper |
| 8 | Simulation v1 (frozen, archived) | SYNTHETIC | 100 scenarios, seed 202; MC 1000 | `benchmarks/simulation/simulate.py` | `out/heldout_v1/` = `out/heldout/` | `python -m benchmarks.simulation.simulate --set heldout` | Y. Re-run byte-identical | Y |
| 9 | Study A, scenario generation + completion metrics | SYNTHETIC | 100 scenarios, 74 claims | `simulate_v2.py` | `out/heldout_v2/scenarios.csv`, `results.json` | `python -m benchmarks.simulation.simulate_v2 && python -m benchmarks.simulation.make_tables` | Y (re-run identical) | Y |
| 10 | Study B, four completion rules, policy + decision level, McNemar, MC | SYNTHETIC | 100 / 74; MC 1000 | same | `results.json`, `tables/sim/baseline.tex`, `tests.tex` | same | Y | Y |
| 11 | Study C, ablation | SYNTHETIC | 100 | same | `tables/sim/ablation.tex` | same | Y | Y |
| 12 | Study D, memory | ACTUAL (M4) + SYNTHETIC (44 repeated workflows) | 10 queries / 44 | same | `tables/sim/memory.tex` | same | Y | Y |
| 13 | Study E, recovery | SYNTHETIC (sequences ACTUAL) | 120 failure scenarios (93 recoverable) | same | `recovery_scenarios.csv`, `tables/sim/recovery.tex` | same | Y | Y. Modelling defect F4 |
| 14 | Study F, overhead | ACTUAL components + SYNTHETIC totals | 100 scenarios, 3 inference medians | same | `tables/sim/overhead.tex` | same | Y | Partial. Latency structure not stated (F5, F13) |
| 15 | Study G, privacy | ANALYTIC (+ experiment 5) | – | – | `tables/threats.tex` | – | n/a. Correctly labelled analytical | n/a |
| 16 | Study H, sensitivity | SYNTHETIC | 300 sets per point | same | `tables/sim/sensitivity*.tex` | same | Y | Y |
| 17 | v1 recomputation check | DERIVED (AI arithmetic check) | – | `independent_validator.py` | `artifacts/results/simulation_validation_report.md` | `python benchmarks/simulation/independent_validator.py` | Y (0 discrepancies on re-run) | Y |
| – | End-to-end evaluation with an LLM | – | – | `run_e2e.py`, `analyze_e2e.py` | none | – | N. The paper correctly says not executed (07_results.tex:37) | – |

Executed but not described in the paper (acceptable, listed for completeness): the routing default-install study (`routing_resolution*.csv`, 2026-10-01; tables moved to `artifacts/*_unused.tex`), the coverage runs, the `experiment_runner_probe` (2026-09-30; every run failed with `ImportError: create_agent_graph`), `main.py --eval` (no-op), the v1 dev set (disclosed as debug-only), and incidental Φ rejections inside the stand-in run (15 Φ-enabled episodes ended `failed` after 13–19 rejections; not a result, correctly unreported). Nothing in the paper cites them.

Described as done but not done: none found. The end-to-end LLM evaluation is correctly reported as not executed.

## ASSUMED-value coverage of the parameter table (paper/tables/sim/params.tex, generated by make_tables.py:265-289)

Listed with a class (OK): category mix, outcome mix, P(complete | class), claim rates 0.92/0.65, ambiguous factor 0.5, missing-evidence reject 0.8, enhanced 0.5/0.05/0.7 (PROPOSED), continuation 0.35, action failure 0.25, repeated share 0.4, memory gain/loss 0.08/0.1, filtered misleading 0.1 (PROPOSED), permanent share 0.25, max attempts 6, per-attempt recovery rates (ranges verified: replan .10–.45, vision .05–.35, guided .35–.55), guided confirmation detection 0.9, steps per category, inference median 3.0 s and log-sd 0.5, derived rates.

**Missing from the table (ASSUMED or design choices that set results):**
1. `detector_category_map` (params.json, tag ASSUMED). The paper text now calls it assumed (06_methodology.tex:30), but it has no table row.
2. Executor-path retries use the re-plan per-attempt success rate (simulate_v2.py:57-58, 125). ASSUMED.
3. Engine strategies `retry` and `alternative_selector` are modelled with the re-plan success rate (simulate_v2.py:130). ASSUMED.
4. Attempt cap `max_attempts + 3` = 9 on the executor path (simulate_v2.py:165), against the table's "max attempts 6". Attempts 7–9 reuse draws (F4).
5. A missing-confirmation continuation is one attempt, with no re-verification (simulate_v2.py:160-162). ASSUMED structure.
6. Latency structure (simulate_v2.py:412-432), all ASSUMED or taken from code inspection:
   - one planning call plus one inference call per step;
   - first step navigate, later steps click or fill at 50/50;
   - 3 screenshots per step plus 2 at completion;
   - each rejection costs 1 inference + DOM + click + 3 screenshots;
   - each failed-action scenario costs round(mean retry-based attempts) = 3 × (inference + DOM + click), whatever the configuration or outcome;
   - self-verification costs one inference draw per check and never rejects (lines 419-420).
7. Φ latency in the simulation is resampled from the gate-state medians (simulate.py:51-52; 26.8 ms on the 2.1 GHz machine), not from the 5.2 ms site-page measurement. The table says only "resampled from measurements".
8. Sensitivity grid: detection ×0.5/1.0/1.5; continuation 0.1/0.35/0.6; action failure 0.1/0.25/0.4; missing-evidence share 0/0.08/0.20 with successful = 0.48 − share; 300 sets per point (simulate_v2.py:363-380). Partly in the sensitivity caption.
9. Monte Carlo keeps the recovery probabilities 0.66/0.49 fixed and does not resample them (simulate_v2.py:316).
10. params.json still contains v1-only values `p_recovered_with_recovery` 0.55 and `p_reclaim_after_false_reject` 0.3 with no "v1 only / unused in v2" tag.

**Class mislabels in the table:**
- "recovered with / without engine 0.66 / 0.49 — ASSUMED; from Study E". These values are SYNTHETIC outputs of Study E (from ASSUMED per-attempt rates).
- "Recovery entry paths and strategy sequences — ACTUAL". The sequences are ACTUAL (engine invoked). The entry paths come from code inspection, and v2 first had them wrong (corrected in aee8c50).

## Findings

**F1 — High — paper/sections/07_results.tex:30; .gitignore:43; artifacts/results/e2e_smoke_stub/egress_summary.json ("note").**
- The issue: the paper now says "the released raw log of the 70-episode run shows only the stand-in's port", and the summary note points to `egress_raw.jsonl`. But `*.jsonl` is gitignored, so neither `egress_raw.jsonl` nor `episodes.jsonl` is in the repository.
- What cannot be checked from a clone: the per-port claim, "54 of 60 memory-enabled episodes", "every page request … 127.0.0.1", and "no browser action / no vision / no retrieval".
- Provenance: the raw log's mtime is 2026-10-24 01:20, twenty days after the run. audit_privacy.md:23 says it "survives only in the session scratchpad". Its copy chain is undocumented.
- Fix:
  - Add `!artifacts/results/e2e_smoke_stub/*.jsonl` after .gitignore:43 and `git add -f` both files.
  - In `e2e_smoke_stub/README.md`, record their SHA-256 and the fact that the raw log was recovered from the run session's scratchpad on 2026-10-24.
  - If they are not committed, change the 07_results.tex:30 wording to "the raw log of the 70-episode run, which is not in the repository, shows …".

**F2 — Medium — paper/sections/06_methodology.tex (no egress paragraph); no script.**
- The issue: the egress experiment is described only in Results. No script reproduces it, and the command, environment variables (`PYTHONPATH=benchmarks/e2e/egress`, `PILOT_EGRESS_LOG`, `PILOT_OLLAMA_BASE_URL`) and the 7-configuration list are recorded nowhere except `run_meta.json`. No code produces `egress_summary.json` (`grep connections_by_host` finds no producer).
- Fix:
  - Add a "Locality test" paragraph to §VI-B giving the command reconstructed in the inventory (row 5).
  - Add `benchmarks/e2e/summarize_egress.py`, which aggregates host:port and PIDs from the raw log into `egress_summary.json`.
  - Make `run_e2e.py` record `sys.argv` and `PILOT_EGRESS_LOG` in `run_meta.json`.

**F3 — Medium — paper/sections/07_results.tex:32 and 06_methodology.tex:20 (oracle validation overstated).**
- The issue: "no false positive among 77 unachieved ones (0–0.05)" counts trajectories whose negative verdict is fixed by construction:
  - 5 golden trajectories of unsatisfiable tasks, which the oracle hard-codes as never achieved (06:20);
  - 38 idle trajectories (open the goal URL, no answer, no action). Their intended labels are computed by code (validate_oracle.py:170-172).
- Only the 34 near misses test false positives in a meaningful way: 0/34, Wilson upper bound about 0.10.
- On the achieved side, 2 of the 37 "achieved" trajectories (idle D01 and T08) are identical to their golden trajectories, so 35 are distinct.
- Fix: replace with "no false negative among 35 golden solutions of satisfiable tasks (plus 2 idle trajectories identical to them; 95% interval 0–0.10) and no false positive among 34 near misses (0–0.10); the 38 idle and 5 unsatisfiable-golden trajectories are negative by construction".

**F4 — Medium — benchmarks/simulation/simulate_v2.py:142, 165, 171 (Study E modelling defect).**
- The issue: each recovery scenario draws `max_attempts` = 6 uniforms, but the executor path for navigation failures plans 9 attempts (3 executor + 6 engine) and indexes `s["u"][k % 6]`. Attempts 7–9 reuse u0–u2:
  - attempt 7 (re-plan, p=.40) reuses the u0 that already failed at p=.40;
  - attempts 8–9 (vision, p=.05) reuse u1 and u2, which are ≥ .40.
  - So attempts 7–9 can never succeed.
- Effects: navigation recovery is understated, unnecessary attempts are inflated (permanent navigation failures count 9 attempts), and the table's "max attempts 6" is wrong for this path.
- Fix:
  - Draw the extra uniforms from the separate v2 stream so v1 identities are kept, e.g. `u_extra = random.Random(f"{s['id']}-v2rec")`, using `u_extra.random()` for k ≥ 6.
  - Rerun `simulate_v2` and `make_tables`, and log the changed numbers in `final_audit/changed_numbers_ledger.csv`.
  - Alternatively, disclose in the recovery caption (make_tables.py:189) that "on the executor path attempts 7–9 reuse earlier draws and cannot succeed".
  - Change the params row to "max attempts 6 (engine), 9 with executor retries".

**F5 — Medium — paper/sections/14_simparams.tex:4 ("lists every parameter of the simulation with its class") vs paper/tables/sim/params.tex.**
- The issue: items 1–10 in the coverage section above are absent, among them structural ASSUMED choices that set Study E and Study F values.
- Fix: in make_tables.py (after line 286), add rows for:
  - category map (ASSUMED);
  - executor and selector retries at the re-plan rate (ASSUMED);
  - attempt cap 9 on the executor path;
  - missing-confirmation continuation = 1 attempt (ASSUMED);
  - latency structure (calls per step, 3+2 screenshots, re-plan cost, recovery cost = 3 attempts; ASSUMED or code inspection);
  - self-check never rejects (ASSUMED);
  - Φ latency samples = gate-state medians (ACTUAL, 2026-10-04);
  - sensitivity grid and 300 sets (design);
  - recovery probabilities fixed in MC (design).
- Then regenerate. Or weaken 14_simparams.tex:4 to "lists the parameters in params.json; structural assumptions of simulate_v2.py are listed in its docstring" (only acceptable if the docstring is also completed).

**F6 — Low — params.tex rows "Action failure; recovered with / without engine" and "Recovery entry paths …"; make_tables.py:278, 282, 287.**
- The issue: class mislabels, as listed above.
- Fix:
  - Line 278 class → "ASSUMED (0.25); SYNTHETIC from Study E (0.66/0.49)".
  - Line 282 → "code inspection (entry paths); ACTUAL (engine sequences, M3)".
  - Line 287 value → "resampled from M2 samples; Φ from the 83 gate-state medians".

**F7 — Low — artifacts/results/gate_stats.txt (2026-10-04) and CHANGE_LOG.md:63 ("gate_stats.csv, .txt: All intervals and p-values").**
- The issue: the .txt is stale. It lacks `p_correct_vs_dispatch` (the test the paper now reports) and the HO1+2 pooled rows, and it shows only the superseded `p_fc_vs_dispatch` (HO2 0.0039).
- Fix: `python artifacts/experiments/gate_stats.py > artifacts/results/gate_stats.txt`. I verified that the output differs only by the added fields and rows.

**F8 — Low — paper/sections/06_methodology.tex:13 ("each conjunct of Φ and the pre-check β is removed in turn by a configuration switch").**
- The issue: the ablation runs only in component mode. β is removed by the study's own `skip_bot_check` argument (verification_gate_study.py:412) applied to its re-implemented pre-check (line 232), not by the `B` configuration switch in verify_node.
- Fix: "For the ablation (component mode only), each conjunct of Φ is removed by its configuration switch and the pre-check β by skipping it in the study harness".

**F9 — Low — paper/sections/06_methodology.tex:9 ("afterwards only configuration switches for the ablation were added to the gate code").**
- The issue:
  - The gate run (07:25) used an uncommitted tree later committed as 55ac1ea.
  - Relative to the freeze commit (b9d5088), that tree also added the self-verification baseline mode, the loopback endpoint check, the latency and model-call logging in verify_node, and the call-budget accounting (`git diff b9d5088 55ac1ea -- backend`).
  - These existed before the freeze: the stand-in run at 07:20:38 already used them.
  - All of them are default-off or behaviour-preserving, so the result is unaffected.
- Fix: "The gate was run on the working tree later committed as 55ac1ea, whose gate code differs from the freeze commit only by default-off switches (ablation, self-verification baseline), the loopback endpoint check and logging".

**F10 — Low — paper/sections/06_methodology.tex:4 ("the decisions of the code before the fixes come from an earlier run … (commit 08653e2)").**
- The issue: the 08653e2 commit's own output covers only the 38 design states. The held-out-1 "before" decisions were produced on 2026-10-01 (b55670b) by running the later study script against the 08653e2 backend. The procedure is not scripted.
- Fix: "… were obtained on 2026-10-01 by running the study script of b55670b against the backend of commit 08653e2 (the design decisions equal those committed in 08653e2)", and add the worktree command to the results index.

**F11 — Low — benchmarks/simulation/measure_inputs.py; inputs/m2_latency.json; verification_gate_cases.csv.**
- The issue: no output records the machine, date or software versions. The paper's "2.1 GHz" (06:4) and "2.8 GHz" (06:30) rest on CHANGE_LOG.md:75-76 and artifacts/07_claims_ledger.md, not on the outputs.
- Fix: write an `environment` block (`platform.platform()`, `/proc/cpuinfo` model name and MHz, Playwright and Chromium versions, UTC date, git commit and dirty flag) into m2_latency.json and the gate-study CSV header or log. Or cite CHANGE_LOG.md:75-76 as the source.

**F12 — Low — benchmarks/simulation/simulate_v2.py:15-17 (docstring).**
- The issue: the docstring still says "navigation failures and need_help go to the engine directly". The code (ENTRY, lines 61-62) and the paper (07b:34) say need_help is retried inline and navigation goes through executor retries.
- Fix: rewrite C4 in the docstring to match ENTRY.

**F13 — Low — paper/sections/07b_simulation.tex:39 ("a model self-check adds 14% (22.4 s)").**
- The issue: in the latency model the self-check costs one assumed-distribution inference per claim and never rejects (simulate_v2.py:419-420). So 14% is a pure cost figure under an accept-all assumption.
- Fix: add "(cost only; the simulated self-check is assumed to accept every claim and to take one model call per claim)".

**F14 — Low — paper/sections/06_methodology.tex:34 / 07b:10 (MC percentiles).**
- The issue: the MC draws the derived gate and memory rates from Beta posteriors, but keeps the recovery probabilities (0.66/0.49) and every ASSUMED value fixed (simulate_v2.py:316). The interval 0.05–0.18 therefore excludes that uncertainty.
- Fix: add "assumed values and the recovery probabilities are held fixed across replications" after "draws derived rates from their Beta posteriors".

**F15 — Low — paper/sections/07_results.tex:30 (unit tests).**
- The issue: "144 of its 147 tests pass" comes from the 2026-10-04 07:31 run (`pytest_revision.txt`). backend/ and tests/ are unchanged from 55ac1ea to HEAD (git diff empty), so the figure still holds, but the paper gives no date or command.
- Fix: add "(`python -m pytest`, 2026-10-04, `artifacts/results/pytest_revision.txt`)".

**F16 — Info — gate-study and simulation integrity (positive).**
- Every number in Tables gate_results and ablation, in 07_results.tex:11-25 and in the simulation tables was traced to committed outputs.
- The HO2 freeze is verified by hash and timing.
- `simulate_v2`, `make_tables`, v1 and `gate_stats.py` regenerate byte-identically from the committed tree.
- No reported experiment was found to be fabricated or unexecuted.
- The LLM end-to-end evaluation is correctly reported as not executed, and physical/hardware testing is not claimed.
