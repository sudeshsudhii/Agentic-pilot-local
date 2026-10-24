# Change log: revision for R1–R18 (2026-10-04)

**Commits on branch `ccr-4b8200f0-5i3k5m`, in order:**
1. `1435fe9`: audit and plan (`artifacts/12_revision_audit.md`).
2. `b9d5088`: freeze of held-out set 2.
3. `55ac1ea`: code, harness and statistics.
4. `bf0a8a5`: oracle validation (the code commit the paper describes).
5. `a86183a`: revised paper.
6. The commit that adds this file.

## 1. Code (`backend/`)

| File | Change | Behaviour in normal use |
|---|---|---|
| `security/locality.py` (new) | `is_loopback_url`, `require_local_endpoint`, `local_chroma_settings` | — |
| `config.py` | `allow_remote_model` (default False); `verification_mode` (`rule`/`self`/`none`); `verification_disabled_checks`; `recovery_fixed_strategy` | Defaults reproduce the previous behaviour, except that a non-loopback model endpoint is now refused |
| `llm/gateway.py` | Endpoint check before the client is created; process-wide `usage` counters (calls, prompt/completion tokens from Ollama, latency) | Unchanged, apart from the refusal |
| `rag/store.py`, `memory/provider.py` | Chroma clients created with `anonymized_telemetry=False` | No telemetry |
| `security/audit.py` | Locality decided by the parsed host, not a substring test. Before, `http://example.com/?h=127.0.0.1` counted as local. | Bug fix |
| `verification/manager.py` | Per-conjunct switches (E, H, Q, T, X, R); `self_verify_completion` (self-verification baseline) with `SelfCheck` schema | Unchanged when no switch is set |
| `agent/nodes.py` | `verify_node`: β switch (B); `verification_mode` dispatch; check latency and self-check model calls recorded in the `VERIFICATION_RESULT` event; self-check calls count towards the 15-call budget | Unchanged in `rule` mode |
| `recovery/engine.py` | Optional pinned strategy | Unchanged by default |

**Bug introduced and fixed during this revision:** the first version of the E switch still left E's expected value in the final comparison, so "without E" still rejected error pages. This was found in the first ablation run and fixed before the reported run. The normal path was not affected. Both logs exist only in this session's history; the reported log is `verification_gate_ablation.log`.

## 2. New experiment code and data

| Path | Content |
|---|---|
| `benchmarks/e2e/sites.py` | Five self-hosted sites with fictional content; server-side state for oracles |
| `benchmarks/e2e/tasks.json` | 40 tasks (10 dev / 30 test), categories, tiers, oracles |
| `benchmarks/e2e/oracle.py` | Independent oracle Φ* |
| `benchmarks/e2e/run_e2e.py` | Runner: one process per configuration, environment record, per-episode JSONL |
| `benchmarks/e2e/analyze_e2e.py`, `stats.py` | Wilson and Clopper–Pearson intervals, exact McNemar, cluster bootstrap; LaTeX tables |
| `benchmarks/e2e/validate_oracle.py` | Golden, idle and perturbed scripted trajectories |
| `benchmarks/e2e/fake_ollama.py` | Scripted stand-in for the Ollama API (pipeline and egress tests only) |
| `benchmarks/e2e/egress/sitecustomize.py` | Socket-connection logger |
| `artifacts/experiments/gate_heldout2.py` | Held-out set 2 (42 states), frozen in `b9d5088` |
| `artifacts/experiments/verification_gate_study.py` | Adds held-out 2 and `--ablation` |
| `artifacts/experiments/gate_stats.py` | Intervals and paired tests |
| `tests/test_local_egress.py` | 18 tests, including a full agent episode with no non-loopback connection |

## 3. Results produced in this revision (`artifacts/results/`)

| File | Content |
|---|---|
| `verification_gate_cases.csv`, `_summary.csv`, `_run.log` | Re-run on current code. All 50 earlier states have identical decisions to the earlier run (checked); adds held-out 2. |
| `verification_gate_ablation.csv`, `.log` | Per-conjunct ablation, 92 states × 8 settings |
| `gate_stats.csv`, `.txt` | All intervals and p-values in Tables IV and V |
| `gate_heldout2_freeze.txt` | SHA-256 of the frozen held-out file |
| `e2e_oracle_validation.csv`, `.txt` | 114 trajectories, 0 FN / 0 FP |
| `e2e_smoke_stub/` | 70 stand-in episodes. **Not results**, except `egress_summary.json` (555/555 connections to 127.0.0.1). |
| `pytest_revision.txt`, `junit_revision.xml` | 147 tests: 144 pass, 3 fail (need live web) |

## 4. Paper

| Element | Change |
|---|---|
| Abstract | Rewritten with the new evidence and an explicit "no end-to-end run" statement |
| §I | Gaps G1–G3 (R17); scope and terms for autonomy and privacy (R7); contributions split into scientific and engineering (R18) |
| §II, Table I | Trimmed. Table I rebuilt (R16); VisualWebArena and WorkArena added; 3 uncited references removed |
| §III | Browser-focused formulation; FCR/FRR with explicit counts; withheld share; no-threshold statement (R9) |
| §IV | Algorithm 1 (R11); Fig. 2, the verification pipeline (R12), replacing the state-machine figure; computer backend moved to Appendix A |
| §V, Table II | Status table with an Eval column and the claim restriction (R6); locality enforcement and experiment switches |
| §VI | Gate study with three splits, oracle definition and statistics (R5, R9, R10); end-to-end harness, tasks, oracle and protocol (R1–R3); Table III, the design (replaces the old protocol table) |
| §VII | Table IV (CIs, p, categories); Table V (ablation); overhead; locality and oracle validity; end-to-end "not run" statement |
| §VIII–XII | Rewritten to match the evidence; §IX threat model, privacy property, autonomy; §X adds statistical power |
| Appendix A, B | Computer-backend design with the postcondition table; task-set summary |
| `main.tex` | `algorithm`/`algpseudocode`; `\todo` macro removed; `\author{}` left for the author |

## 5. Changed or corrected values

| Earlier statement | Now | Reason |
|---|---|---|
| Gate latency median 30.6 ms (max 39.5) over 35 design decisions | 26.8 ms (p90 29.5, max 34.6) over 83 decisions in all sets; design only 27.9 ms | Re-measured on this container (Xeon 2.1 GHz) with the same code. Not an error; timing differs between machines. |
| "4-core Intel Xeon at 2.8 GHz" | 2.1 GHz for the current-code runs | The current runs used a different container (`/proc/cpuinfo`) |
| 129 tests, 126 pass | 147 tests, 144 pass, 3 fail (need web) | 18 new tests |
| 10,867 lines | about 11,000 | New code |
| Held-out evidence: 12 states | 12 + 42 states | R5 |

**Errors in original numbers:** none found. All 50 earlier states give the same decisions on re-run. The before-fix counts in Table IV (design 15/23 withheld, 3/15 rejected; live 13–14) match the earlier CSVs.

## 6. Sources of every number in the revised paper

| Claim | Source |
|---|---|
| 20/23, 1/15, 15/23 before, 3/15 before, 9/22, 1/20, 11/27, 2/27, 2/5, 1/7; FC/R; Wilson CIs; McNemar p (<.001, .50, .004, .001, .016) | `gate_stats.txt` |
| Per-category W/FR (Table IV) | `verification_gate_summary.csv` |
| Ablation counts and p (Table V) | `verification_gate_ablation.log`, `gate_stats.txt` |
| Live modes agree on every state; live before-fix withheld 14/13 | `verification_gate_cases.csv`, `_before_fixes.csv` |
| Latency 26.8 / 29.5 / 34.6 ms over 83 decisions; pre-check at most 13.4 ms | `verification_gate_cases.csv` (`gate_ms_median`) |
| 70 episodes, 555 connections, all to 127.0.0.1 | `e2e_smoke_stub/egress_summary.json` |
| Oracle 0/37 FN, 0/77 FP, 114 trajectories | `e2e_oracle_validation.txt` |
| 144/147 tests | `pytest_revision.txt` |
| 40 tasks, 10/30, 5 unsatisfiable, tier and category counts | `benchmarks/e2e/tasks.json` |
| Held-out 2 frozen before testing | commit `b9d5088` precedes `55ac1ea`; SHA-256 in `gate_heldout2_freeze.txt` |
| 17 sanitizer patterns, approval triggers, recovery behaviour, router models | code (unchanged from the earlier audit, `artifacts/07_claims_ledger.md`) |

---

# Addendum (2026-10-23): research hypotheses and illustrative evaluation

| Location | Change |
|---|---|
| New §VI "Research Hypotheses" (`05b_hypotheses.tex`) | H1–H5 with rationale; Table III gives the independent variable, dependent variables, expected direction and comparison configuration for each. All are marked untested. |
| §VII-C "Hypothesis Evaluation Design" (`06_methodology.tex`) | Objectives; scenarios (30 test tasks × 3 trials, N = 90); metric formulas TCR, VA, ETR, MCS and AER (Eq. 3), plus FCR/FRR; McNemar and bootstrap decision rule; approaches 4 and 5 stated as not implemented |
| New Appendix C "Illustrative Evaluation and Discussion" (`14_illustrative.tex`) | Boxed disclaimer; Tables VIII–IX with **hypothetical** values (each caption says so); illustrative interpretation, failure scenarios and validation requirements |
| Abstract, §I | One sentence on the hypotheses; §I points to Appendix C as hypothetical. No illustrative number appears outside Appendix C. |
| Table VII (experiment design) | Moved to Appendix B to keep the body at 8 pages; `no_evidence` row added |
| §IX Discussion | "Auditing an agent" paragraph removed (space) |
| `benchmarks/e2e/run_e2e.py` | `no_evidence` configuration (code only; nothing was run) |

**Integrity audit:**
- H1–H5 match the code, with these mismatches flagged in the text:
  - There is no `MemoryManager`; memory is `ChromaProvider` over Chroma plus SQLite.
  - There is no multi-agent orchestration; it is a single LangGraph state machine (H5).
  - `enable_evidence` turns off only per-action execution records (H3).
  - The unstructured baseline (H5), per-step evidence-based verification (approach 4) and combined verification (approach 5) are not implemented.
- Every hypothesis maps to a metric with a formula (Eq. 3 or Eq. 2).
- The illustrative counts are internally consistent: each approach sums to 90 episodes; full-system TCR is 44/90 in Tables VIII and IX; the reported-completion denominator for ETR is 52, equal to TP + FC of approach 3.
- No illustrative value is called significant or measured. The one measured value reused (27 ms) is labelled as such.
- Genuine results (§VIII) are unchanged.
- No new references; all 47 are unchanged. The build has 0 LaTeX errors, 0 undefined references and 0 BibTeX warnings. The body takes pages 1–8, the appendices pages 9–10 and the references pages 10–11.

**Recommendation:** remove Appendix C, or replace its values, once the end-to-end runs (AUTHOR_ACTIONS A1) produce measured data. Many IEEE venues count appendices toward the page limit.

---

# Addendum (2026-10-23, later): simulation-based evaluation

**Why:** no language model can be installed in the drafting environment. The missing evaluations are therefore studied by a seeded simulation, labelled SYNTHETIC everywhere. The illustrative Appendix C, which used hand-chosen values, was removed and replaced by this.

**Commits:**
- `3a0aa8e`: measured inputs and frozen parameters, committed before the held-out set was generated.
- `41a6097`: simulation results and paper integration.

| Path | Change |
|---|---|
| `benchmarks/simulation/measure_inputs.py` | ACTUAL measurements with no model:<br>M1, decisions of Φ and of basic error-only detection on 92 gate states;<br>M2, latency of browser operations, DOM extraction, screenshots and Φ on the local sites (30 repetitions);<br>M3, the real recovery engine's classification and strategy sequence for 6 failure messages;<br>M4, real Chroma retrieval over a 23-record synthetic memory corpus with 10 queries |
| `benchmarks/simulation/params.json` | Every assumption, tagged ACTUAL, DERIVED, ASSUMED or PROPOSED |
| `benchmarks/simulation/simulate.py` | Studies A–F and H. Dev seed 101 (debugging only), held-out seed 202 (reported), 1,000 Monte Carlo replications, sensitivity sweeps, per-scenario CSVs |
| `benchmarks/simulation/make_tables.py` | Writes every simulation table in `paper/tables/sim/`, plus the ledger `out/heldout/ledger_simulation.csv` |
| `benchmarks/simulation/independent_validator.py`, `artifacts/results/simulation_validation_report.md` | Independent recomputation by a separate validation agent: **0 discrepancies** |
| Paper | §VI Research Questions and Hypotheses (H0/H1, simulated outcomes); §VII-C Simulation-Based Evaluation and Data Provenance; new §IX Simulation-Based Evaluation (Tables VI–XII, Fig. 3); privacy threat table (Study G); implementation audit with classes IE/IS/IN/PI/PR; Table I with the requested dimensions; Appendix C (simulation parameters) |

**Bug found and fixed after the freeze:** the latency study did not use common random numbers, so Φ appeared faster than no verification. Only the latency function changed; Studies A–E and H were unaffected (their outputs were identical before and after).

**Findings from the ACTUAL measurements:**
- Basic error-only detection withholds 3 of 27 held-out false completions (Φ: 11 of 27).
- The recovery engine classifies a missing confirmation as "unknown".
- Memory retrieval has no relevance threshold: 3 of 10 queries return an irrelevant record or a failed attempt first.

**Independent QA review** (`artifacts/results/qa_review_report.md`, by a separate reviewer agent) found 22 issues (1 high, 6 medium, 15 low). All are fixed:
- **H-1:** the latency correction made after the freeze is now disclosed in §VII-C.
- **M-1:** the provenance of the egress run is given.
- **M-2:** the hypotheses section now names the actual component evidence for H1 and H2.
- **M-3:** the outcomes for H4 and for enhanced H2 are marked "by assumption", and their synthetic p-values are removed from the text.
- **M-4:** the scope of the ledger and of the independent validation is now stated precisely.
- **M-5:** the category mapping and the missing-confirmation proxy (3 states) are stated.
- **M-6:** the `no_evidence` row is no longer labelled H3.
- **L-1 to L-15:**
  - Rounding fixed: Monte Carlo TSR is 0.44.
  - Memory ablation changes two outcomes, not one.
  - Retrieval metrics are now stated as over 9 queries.
  - The realised count of permanent failures is given: 27/120, none of them a missing confirmation.
  - Φ latency now has consistent provenance and percentiles.
  - Studies A–H are defined.
  - Measurement environment for the inputs is stated: 2026-10-23, Xeon 2.8 GHz.
  - Held-out count corrected to 54.
  - The self-verification baseline is described as "will measure", since it has not been run.
  - The abstract now credits the memory and recovery findings to measurements, not to the simulation.
  - The synthetic p-value in the hypotheses table is labelled synthetic.
  - Mean vs median self-check overhead is stated.
  - The paired Monte Carlo ΔFC replaces the overlapping marginal ranges: mean 0.11 [0.05, 0.17]; p < 0.05 in 96% of sets.
  - The gate-code change after the held-out-2 freeze is described (default-off switches).
  - The pytest failure cause is corrected: the failures need live web or a running local model.

# Addendum (2026-10-24): final technical and statistical audit

Four audits fed this round: statistics, methodology, research integrity and privacy. An independent final review followed them. The full reports and the deliverables are in `artifacts/results/final_audit/`; every changed number is in `changed_numbers_ledger.csv`.

## Statistics (ACTUAL gate data)

- **Gate vs dispatch-only.** The McNemar test now uses paired decision correctness; the old test was degenerate. Implemented in `artifacts/experiments/gate_stats.py`, which adds the column `p_correct_vs_dispatch` and a pooled split. The 84 existing rows of `gate_stats.csv` are unchanged.

  | Set | Old p | New p |
  |---|---|---|
  | Held-out 2 | 0.004 | 0.021 |
  | Pooled | 0.001 | 0.022 |

- **Design-set significance tests removed.** They were circular; the paper reports counts only.

## Simulation

- **Decision level vs policy level.** `decision_analysis.py` separates the two. The p = 0.80 mixed indicator is withdrawn.
- **Additive output fields in v1.** `simulate.py` (v1) gained three fields; its outputs are otherwise byte-identical.
- **Corrected model v2 (`simulate_v2.py`, post hoc, not pre-registered)** fixes the following:
  - false-rejection rates from the mapped categories;
  - fail-closed basic detection;
  - re-verification after continuation;
  - recovery entry paths taken from the code;
  - rate uncertainty in the Monte Carlo;
  - re-planning in the latency model;
  - a sweep of the continuation rate.
- **Outputs.** v2 outputs are in `out/heldout_v2/`; v1 is archived in `out/heldout_v1/`.
- **Table generation.** `make_tables.py` now reads v2.

## Paper

- **Abstract and conclusion.** Three-way framing: measured, simulated, not executed.
- **Privacy claims narrowed.** Default loopback endpoint; Python processes only; scripted stand-in model server; a list of what the claim does not cover.
- **Section IX.** Rewritten with the v2 numbers.
- **H1 result.** Stated as true by construction.
- **H2 result.** Not supported: decision accuracy 52/74 vs 46/74, p = 0.15.
- **H3 result.** Underpowered.
- **H4 result and the enhanced variant of H2.** Hold only by assumption.
- **Ablation table.** The stored-evidence row is removed; the labels match the code switches.
- **Table I.** Five cells corrected.
- **Bibliography.** CogAgent authors and OS-Harm volume.
- **Repository reference.** The branch and the agent-code commit are named, and the paper notes that the default branch has diverged.
- **Memory corpus.** 22 records.
- **Parameter table.** Completed.
- **Rounding.** Half-up rounding throughout.
