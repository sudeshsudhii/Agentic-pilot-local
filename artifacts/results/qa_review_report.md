# QA review: "Agentic Pilot" (paper/main.tex, PDF 13 pp.)

Reviewer: independent QA agent. No repository file was modified.

## 0. Summary

I recomputed every number in the abstract, introduction, Section 7b (simulation), Table hyp, discussion, limitations and conclusion from the data sources. I also recomputed the gate tables (gate_results.tex, ablation.tex) and the Wilson and McNemar statistics.

- **Numbers:** almost all are correct. All Wilson intervals, McNemar p-values, confusion counts, Monte Carlo (MC) means and sensitivity values match `gate_stats.txt`, `verification_gate_ablation.csv`, `results.json` and the inputs. Four small numeric or labelling slips were found (L1–L4).
- **Mixing of actual and synthetic results:** no simulated number is presented as measured. The abstract, introduction and conclusion label the simulation clearly, and every synthetic table caption says "Simulation-based (synthetic)". Remaining problems are framing and provenance:
  - a pre-registration ("freeze") claim that is factually wrong;
  - two "supported" hypothesis outcomes that follow by construction from PROPOSED parameters;
  - overstated claims about the evidence ledger and the independent validation.
- **Issue count:** 1 high, 6 medium, 15 low.

## 1. Issues

### HIGH

**H-1. The simulation freeze claim is false.** Location: `sections/06_methodology.tex` l.32 ("Parameters and code were committed (3a0aa8e) before the reported held-out set ... was generated").
- **What is wrong:** `git diff 3a0aa8e 41a6097 -- benchmarks/simulation/simulate.py` shows that `latency_study` was rewritten after the freeze commit. It switched to common random numbers with separate base and verification streams, moved the recovery draws, and added `mean_s`. The held-out outputs (`out/heldout/*`) were first committed in 41a6097, together with this code change.
- **Affected results:** all of Study F, which comes from post-freeze code. This includes the "+24 %" self-check overhead (7b l.35), which is computed from `mean_s`, a field that did not exist at the freeze.
- **Fix:** either re-run Study F from the code at 3a0aa8e, or disclose the change. Suggested wording: "the latency model of Study F was changed to common random numbers after the freeze (commit 41a6097); Studies A–E and H use the frozen code."

### MEDIUM

**M-1. Provenance of the egress (locality) evidence.** Locations: `07_results.tex` l.30, `09_safety.tex` l.6, abstract.
- **What is wrong:** `e2e_smoke_stub/run_meta.json` records `git_commit 1435fe9`, `git_dirty: true`. That commit predates 55ac1ea, where locality enforcement was committed, and predates bf0a8a5, the commit the paper says it describes (05_implementation l.4). So the 70-episode egress result was produced from an uncommitted working tree.
- **What is fine:** the backend is unchanged between bf0a8a5 and HEAD, and `tests/test_local_egress.py::test_agent_episode_opens_no_non_loopback_connection` passes in `pytest_revision.txt`.
- **Fix:** re-run the 70 episodes at bf0a8a5, or state that the run used a pre-commit working tree and that the committed test reproduces it.

**M-2. Hypotheses section contradicts the introduction about how H1 is tested.** Location: `05b_hypotheses.tex` l.4 says "Each is tested in this paper only by simulation ... none is confirmed empirically".
- **What is wrong:** the introduction (l.8, l.20) maps RQ1/G1 to the actual gate study. That study is component-level evidence for H1: held-out 2 withheld 9/22, p = 0.004.
- **Fix:** say "H1 and the gate's part of H2 have component-level ACTUAL evidence (Section 7.A–B); end-to-end tests of H1–H5 exist only in simulation."

**M-3. Two hypothesis outcomes are true by construction.** Location: Table hyp rows H2 ("enhanced: yes, p = .02") and H4 ("higher, 87 vs 69 of 93"); 7b l.11 and l.29.
- **H4:** the evidence-guided per-attempt success rates in `params.json` (`p_success_evidence_guided`, PROPOSED) are at least as high as the retry/replan rates in every mode. Its confirmation-detection rate is also higher (0.9 vs 0.62).
- **H2-enhanced:** `enhanced_extra_catch` = 0.5 is PROPOSED.
- **Why it matters:** the "supported" outcome and the synthetic p-values follow directly from the assumed parameters. Reporting a McNemar p for them reads as evidence.
- **Fix:** in Table hyp and 7b, state "by assumption (PROPOSED rates)" for these rows and drop the p-values, or show the break-even rate at which the advantage disappears.

**M-4. The ledger and independent-validation claims are overstated.** Locations: `06_methodology.tex` l.28 ("an evidence ledger lists every simulated value with its source") and l.41 ("recomputed all confusion counts, rates, paired tests, memory and recovery statistics").
- **Ledger:** `out/heldout/ledger_simulation.csv` has 49 rows. It contains no MC values, sensitivity values (Table sim-sens, Fig. sim-sens), latency shares, recovery detection, FC or attempt counts, memory-simulation rows, ablation FCR/FRR/F1, Cohen's h or bootstrap CIs.
- **Validation:** `simulation_validation_report.md` did not check the recovery McNemar p (<0.001; I recomputed it as 18/0 discordant, p = 7.6e-6), the MC values, the sensitivity values, latency, or the bootstrap intervals. The report also points to a validator in a temporary scratchpad path rather than to `benchmarks/simulation/independent_validator.py`.
- **Fix:** narrow both sentences, or extend the ledger and the validator to cover these values.

**M-5. Derived simulation inputs rest on undisclosed mappings.** Location: `tables/sim/params.tex`, `06_methodology.tex` l.30.
- (a) "Missing-confirmation detection 0.62 DERIVED" is Φ's withheld share on the 3 unsatisfied held-out multi-step states (2/3, `params.json` recovery.missing_confirmation_detection). That is a proxy, and the text (7b l.29) says the real engine classifies missing confirmations as "unknown".
- (b) The detector category mapping is ASSUMED and not shown in the paper: `form` uses text_entry plus multi_step states (n = 6), so multi-step states are used twice, and the 5 unsatisfied held-out bot-check states are excluded.
- **Fix:** list the mapping and the proxy in Table sim-params, and label (a) "DERIVED (proxy) / ASSUMED".

**M-6. The H3 label conflicts between two tables.** Location: `tables/e2e_design.tex`, row `no_evidence` → "traceability (H3)".
- **What is wrong:** in Table hyp, H3 is memory. No hypothesis covers traceability.
- **Fix:** remove "(H3)", or relabel the row to point to the appropriate RQ.

### LOW

**L-1. MC TSR rounding mismatch.** `07b_simulation.tex` l.17 says "across replications, from 0.45 to 0.38". The full-system MC TSR is 0.44475, and Table sim-ablation shows 0.44. Use 0.44.

**L-2. Memory ablation changes two outcomes, not one.** `07b` l.17 says "Removing memory changes one outcome". `scenarios.csv` shows two scenarios change (S202-041 FN→FP, S202-053 TN→TP). Fix: "changes two outcomes (one FN→FP, one TN→TP)".

**L-3. Memory retrieval metrics use 9 queries, not 10.** `tables/sim/memory.tex`, header "10 queries". Precision@3 0.52, Recall@3 1.00 and MRR 0.93 are means over the 9 queries that have a relevant record. Over all 10, P@3 is 0.47 and MRR is 0.83. Fix: state "over the 9 queries with a relevant record".

**L-4. Realised permanent-failure split differs from the caption.** `tables/sim/recovery.tex` caption says "25 % permanent". The realised count is 27/120, and none of the 20 missing-confirmation scenarios is permanent, so all 20 are recoverable. This inflates the missing-confirmation pool (4/20 vs 17/20). Report the realised counts.

**L-5. Φ latency is reported inconsistently across sections.**
- Table sim-overhead's "ACTUAL ... local sites, 30 repetitions" block includes "Φ on gate states (83)". Those are 20 repetitions on request-intercepted pages, not on the local sites.
- 7b l.35 says "Measured on the self-hosted sites ... 26.8 ms on the gate states".
- 07_results l.25 reports P90 29.5 ms, while the table reports p95 30.3 ms. Both are correct, but they are different percentiles for the same quantity.
- Fix: harmonise the percentile and correct the provenance wording.

**L-6. Studies A–H are never defined.** The 7b heading says "Studies A and B", but Study A is never defined, and the list A–H is not introduced in Section 6. Add a one-line list.

**L-7. "27 held-out gate states" is imprecise.** `10_limitations.tex` l.10. The inputs use 54 held-out states: detection uses 22 unsatisfied states (bot-check excluded) and FRR uses 27 satisfied states. Correct the count.

**L-8. The self-verification baseline has not been run.** `08_discussion.tex` l.6 says "The self-verification baseline in our harness measures exactly this alternative". It has not been run (status table: IN, harness only). Change to "will measure".

**L-9. The abstract credits two findings to the simulation.** Abstract l.2 says the simulation "exposes memory retrieval without a relevance threshold and recovery that misses absent confirmations". Both findings come from ACTUAL measurements of the store and the engine (m4 and m3 inputs; code: `memory/provider.py` has no threshold), not from the simulation. Rephrase as "measurements of the components show ...; the simulation shows their effect under stated assumptions".

**L-10. Two identical p-values with different status.** The ACTUAL held-out p = 0.004 (abstract) and the SYNTHETIC H1 p = .004 (Table hyp) are numerically identical (both 9/0 discordant). Readers may conflate them. Add "(synthetic)" in the Table hyp cell.

**L-11. Mean and median overhead are mixed.** `07b` l.35 gives "model self-check 4.5 s (+24 %)", which is based on the mean (18.62 → 23.17 s). Table sim-overhead reports medians (17.0 → 21.7 s, +28 %). State which statistic is used.

**L-12. Separability argument uses marginal ranges.** `07b` l.11 says "their 95 % ranges overlap, so a single set of 100 tasks may not separate Φ from no verification". This uses marginal MC ranges. Separability depends on the paired difference, and the paired test on the same set gives p = 0.004. Report the MC distribution of the paired ΔFC instead.

**L-13. Measurement environment for the simulation inputs is missing.** Section 6 gives the environment for the 2026-10-04 runs only. The simulation inputs (m1–m4, committed 2026-10-23) have no date or hardware stated. Add both.

**L-14. Gate code did change after the held-out-2 freeze.** `06_methodology.tex` l.9 says "no gate code changed afterwards". `backend/verification/manager.py` did change after b9d5088: ablation switches were added in 55ac1ea. The change is behaviour-neutral by default. Say so ("only default-off ablation switches were added").

**L-15. The pytest failure cause is misstated.** `07_results.tex` l.30 says "the 3 failures need live websites". `tests/e2e/test_certification.py` fails because Ollama is not running ("Failed to connect to Ollama"). The two `test_task_runner` failures are network failures (ERR_TUNNEL_CONNECTION_FAILED). Fix: "need live websites or a running local model".

## 2. Number checks performed (all match unless listed above)

- **Gate study, actual:**
  - design 20/23 [.68, .95], FR 1/15, FC/R 3/17, before-fix 15/23 and 3/15, live modes 14 and 13, p_vs_pre 0.016 (7 fixed, 0 broken);
  - HO1 2/5, 1/7, 3/9, p .50;
  - HO2 9/22 [.23, .61], 1/20, 13/32, p 0.0039;
  - pooled 11/27 [.25, .59], 2/27, 16/41, p .001;
  - per-category block of Table gate;
  - all 21 ablation cells and p-values;
  - "at most three decisions" on the held-out sets.
- **Latency, actual:** median 26.8 ms over 83 decisions, P90 29.5, P95 30.3, max 34.6; pre-check max 13.4 ms over 9 decisions; m2 latencies 17.1 / 65.2 / 12.5 / 76.4 / 61.3 / 5.2 ms.
- **Egress, oracle and tests, actual:** 555 connections, all to 127.0.0.1, 70 episodes in 7 configs (6 with memory). Oracle 114 trajectories = 40 + 40 + 34, FN 0/37 [0, .09], FP 0/77 [0, .05]. Tests 144/147.
- **Code facts verified in `backend/`:**
  - 11 graph nodes, 5-min watchdog, 3 retries, 7 failure classes, 6 total attempts;
  - top-50 elements, 120-character text, 17 sanitizer patterns, >8-word decomposition, K = 15 model-call budget;
  - about 11,052 lines;
  - Φ reads the live `page`; memory `n_results` has no threshold; model calls are audit-logged with byte counts;
  - the desktop and code executors are not wired into the graph.
- **Simulation, synthetic:**
  - Table sim-baseline: all cells and Wilson CIs;
  - Table sim-tests: b/c, p, ΔFC CIs, h, MC FCR ranges;
  - Table sim-ablation;
  - memory 18/44 vs 19/44, contextual accuracy 0.64 / 0.86, FCR values;
  - recovery 69/93, 87/93, 111/120, 118/120, FC 9/2, 162 unnecessary attempts, costs 10.9 / 10.0, per-mode counts;
  - latency medians, shares 84 % / 0.2 % / 2.5 %, 0.035 s, 0.46 s, sweep 8.9 / 32.6 s;
  - sensitivity table and figure (300 reps);
  - params table derived rates, (k+0.5)/(n+1);
  - E2E task distribution (40 tasks, 10/30, tiers).

## 3. Reviewer requirements (R1–R18)

| # | Requirement | Status | Reason |
|---|---|---|---|
| 1 | End-to-end LLM evaluation | Not met | Harness implemented but not run; stated openly (Sec. 7.E). |
| 2 | Realistic browser tasks | Partly | 40 tasks on five self-hosted fictional sites are designed but not run. Gate states are static constructed pages; no live web. |
| 3 | Baseline comparison | Partly | Actual: dispatch-only and pre-fix gate on 92 states. No-verification and self-verification baselines are only in the harness (not run) and in the simulation. No published-agent baseline. |
| 4 | Ablation | Partly/met | Actual per-conjunct ablation on 92 states. Architecture-level ablation (memory, recovery, evidence) is simulation only. |
| 5 | Independent held-out evaluation | Partly | HO2 was frozen by commit and hash before testing, but written and labelled by the author who knew the rules; no independent labels or κ. The simulation held-out seed is synthetic and its freeze claim is inaccurate (H-1). |
| 6 | Implemented vs proposed | Met | Table status, ‡ markers, Appendix A design-only, Table post status column. |
| 7 | Privacy and autonomy claims | Met (minor gap) | Scoped definitions, loopback enforcement, egress test, threats table with residual risks. Egress run provenance needs fixing (M-1). |
| 8 | No placeholders | Met | No TODO, Pending or "??" in the source or PDF; all \ref resolve; empty author block is intentional for double-blind review. |
| 9 | FCR/FRR statistics | Met | Counts with Wilson/Clopper-Pearson intervals and exact McNemar tests, in both actual and simulated parts. |
| 10 | Independent oracle | Partly | E2E oracle uses separate signals and code and was validated on 114 scripted trajectories. Gate labels are single-author, with no inter-annotator agreement. |
| 11 | Algorithm 1 | Met | Algorithm 1 matches the code (K = 15, 3 retries, β before Φ). |
| 12 | Verification figure | Met | Fig. 2 shows the conjuncts, β and evidence storage. |
| 13 | Memory/RAG evaluation | Partly | Actual retrieval on 10 queries over a 23-record synthetic corpus; effect simulated only. The RAG knowledge retriever (which has a threshold) is not evaluated. |
| 14 | Recovery evaluation | Partly | Actual classification of 6 messages; effectiveness simulated only. Evidence-guided gain holds by assumption (M-3). |
| 15 | Verification overhead | Met (component) | Actual ms-level latency and zero tokens. Episode-level overhead and extra steps after a rejection are simulated or unmeasured. |
| 16 | Related-work table | Met | Table with 12 systems and explicit dimensions. |
| 17 | Research gaps | Met | G1–G3, each tied to a test section. |
| 18 | Scientific vs engineering contributions | Met | Separated lists (1–3 vs 4–6). |

## 4. Submission readiness

The paper is honest about its scope. The actual component results (gate study, ablation, latency, egress, oracle validation) are correctly computed, have intervals and are traceable to the artifacts. Simulated results are consistently labelled and never substituted for measured ones in the abstract, introduction or conclusion.

It is not yet ready to submit:
- The false freeze statement (H-1) must be corrected.
- The by-construction hypothesis outcomes (M-3) and the ledger/validation overstatements (M-4) need rewording.
- The egress provenance (M-1) should be re-run or disclosed.
- The remaining low items are quick copy edits.

Even after these fixes, the main weakness is substantive: there is no end-to-end evaluation with a language model, and the held-out set was written by the gate's author. A journal is likely to treat the work as a well-documented component study plus a design, not as evidence that the agent works. After the fixes it fits a workshop or short-paper venue. A full journal submission would need the released E2E protocol to be run.
