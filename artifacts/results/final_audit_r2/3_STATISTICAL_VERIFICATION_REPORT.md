# Statistical verification report (round 2)

**How the numbers were checked.**
- About 120 printed quantities were recomputed by the statistical auditor (Agent 2). The auditor wrote its own code with no imports from the project's analysis scripts, working from the raw files: `verification_gate_cases*.csv`, `verification_gate_ablation.csv`, `m2_latency.json`, `m4_memory.csv`, the egress logs, `out/heldout_v2/scenarios.csv`, `recovery_scenarios.csv` and `results.json`.
- The archived scripts are in `artifacts/results/final_audit/scripts/` and run from a clone.
- The reproducibility auditor (Agent 6) reran `simulate_v2`, `make_tables`, `gate_stats.py` and the LaTeX build in fresh clones; all outputs were byte-identical.

**Result:** 0 numerical mismatches. The findings concerned presentation and inference, and all are now corrected (see Section 4).

## 1. Verification of the eight findings named in the request

| # | Finding | Recomputed | Class | Verdict |
|---|---|---|---|---|
| 1 | Held-out gate test: unsatisfied withheld; satisfied rejected | 9/22 = 0.41 (Wilson 0.23–0.61); 1/20 = 0.05 (Wilson 0.01–0.24) | ACTUAL | ✔ |
| 2 | Exact McNemar, gate vs dispatch-only | Discordant 9 / 1 → p = 2·Σ_{i≤1}C(10,i)/2¹⁰ = 0.021484 (printed 0.021). Pooled HO1+2: 11/2 → 0.022461 (printed 0.022). | ACTUAL / DERIVED | ✔ |
| 3 | Decision level, Φ vs accept-all | 52/74 (0.70, Wilson 0.59–0.79) vs 46/74 (0.62, 0.51–0.72). Discordant 3 / 9 → p = 0.14600 (printed 0.15). | SYNTHETIC | ✔ |
| 4 | Policy-level false completions | 19 vs 28 of 100; discordant 9 / 0. See Section 2 for why no p is now printed. | SYNTHETIC | ✔ (presentation corrected) |
| 5 | Recovery evaluation | 120 failures (20 per mode); 27 permanent (none a missing confirmation); 93 recoverable. Recovered 51 / 68 / 87 of 93 (engine off / engine on / guided, proposed). | SYNTHETIC (strategy sequences ACTUAL) | ✔ |
| 6 | Memory retrieval | 10 queries, 9 with a relevant record. P@3 = 0.519 (the largest value attainable on this corpus). R@3 = 1.00. MRR = 0.926 over 9 queries (0.833 over all 10). Top-1 irrelevant or failed: 3/10. | ACTUAL (synthetic corpus) | ✔ |
| 7 | Gate decision latency | n = 83 decisions; median 26.84 ms. P90 29.49, P95 30.31, maximum 34.64 ms (percentiles of per-state medians of 20 repetitions). Pre-check maximum 13.36 ms. | ACTUAL | ✔ |
| 8 | Privacy egress test | 70 episodes; 555 connects, all to 127.0.0.1:11435; 8 Python PIDs; 0 non-local page hosts. Memory returned records in 54 of the 60 memory-enabled episodes. | ACTUAL (stand-in model server) | ✔ (scope stated, see the provenance matrix) |

## 2. The zero discordant cells in Table VII

The paired false-completion comparisons have zero cells:

| Comparison | b / c | Why the zero |
|---|---|---|
| None vs Φ | 9 / **0** | **Structural.** In `episode()`, Φ can only withhold a claim that no verification would accept. No scenario can end in a false completion with Φ alone. Over 1,000 regenerated sets the cell is always 0. |
| Enhanced vs Φ | **0** / 11 | **Structural.** Enhanced validation withholds every claim Φ withholds. |
| Basic vs Φ | 5 / **0** (Dec. 0/5, Succ. 0/1) | **Not structural.** It comes from basic detection being nested within Φ at the point-estimate rates. In the regenerated sets, where the two rates are drawn independently, Φ-only false completions occur in 39% of sets. |

**What the McNemar test can and cannot mean here.** When one cell is structurally zero, the null hypothesis of symmetric discordance can hold only if there is no discordance at all, so the binomial reference distribution describes no state of the model. The exact p is then 2^(1−b): 0.0039 just restates b = 9, and "<0.001" restates b = 11. The share of Monte Carlo sets with p < 0.05 (94.1%) equals the share with b ≥ 6. The p-value therefore adds no evidence about direction.

**Correction made:**
- **Table VII** no longer prints a McNemar p for the structural cells (marked §). In its place is the paired difference in false completions per scenario, with Monte Carlo 2.5–97.5th percentiles:
  - None − Φ: +0.11 [+0.05, +0.18];
  - Basic − Φ: +0.06 [+0.00, +0.12];
  - Enhanced − Φ: −0.08 [−0.14, −0.03].
- **New outputs:** these come from new output keys in `simulate_v2.py`, which draw no extra random numbers. All other outputs were verified byte-identical before and after.
- **Basic row:** the non-structural zeros are marked ¶ and explained in the caption.
- **Section IX-A:** reports the 9/0 discordance and the Monte Carlo interval, not a p-value, and states that the "by construction" property holds in the model, not necessarily in the code.
- **Abstract and Table III** say "a direction fixed by construction".

## 3. p-value convention

Rules (applied in the text, Tables IV, V and VII, the ablation table and Table III):
- two significant figures, rounded half up;
- leading zero;
- "<0.001" below 0.001;
- 1 printed as "1.0".

| Exact p | Printed |
|---|---|
| 0.021484 | 0.021 |
| 0.022461 | 0.022 |
| 0.146 | 0.15 |
| 0.0625 | 0.063 |
| 0.625 | 0.63 |
| 0.6875 | 0.69 |

## 4. Other statistical corrections (round 2)

| Issue | Correction |
|---|---|
| "Withholds a significant share" (the only test is paired correctness vs dispatch-only) | "is correct on significantly more held-out states than a dispatch-only rule and withholds 41%". |
| Ablation "no removal reaches p < 0.05" | Restated as attainability: with ≤5 discordant states the smallest attainable p is 0.063. |
| Held-out 1 "has no power" | Restated: with 3 discordant states the smallest attainable p is 0.25. |
| H2 reconciliation (ACTUAL p = 0.021 vs SYNTHETIC p = 0.15) | Both are stated in Table III and §VI. 2 of Φ's 3 synthetic false rejections come from missing-evidence scenarios rejected at an ASSUMED rate of 0.8; the measured false-rejection rate is 0/24. |
| Post-hoc v2 | Disclosure added in four places: (a) the v1 freeze sentence now names v1; (b) the direction of the changes (all in Φ's favour) is stated; (c) the decision-level outcome was defined after the v1 results; (d) the second revision (recovery paths) is in the Limitations. Table III and Table VII captions say "post hoc". |
| Monte Carlo independence of the basic and Φ rates | Disclosed in the Table VII caption (¶). |
| Monte Carlo omits uncertainty of the ASSUMED values and of the recovery probabilities | Stated in §VII-C. |
| Oracle validation intervals | Restated on the informative cases. Of the 37 "achieved" trajectories, 35 are correct solutions: 0 false negatives (Wilson upper bound 0.10). Of the 77 "unachieved", 34 are near misses: 0 false positives (0.10). The rest are negative by construction. |
| Study E random-number reuse (attempts 7–9 of the navigation path reused draws 1–3 and could not succeed) | Fixed with a separate per-scenario stream. **No output changed**, because every navigation failure that reached attempt 7 was already recovered or permanent. |

## 5. Assumptions on which every synthetic statistic is conditional

These assumptions are listed in Table XVI. Every synthetic p-value and interval in the paper is labelled as conditional on them.

| Quantity | Value | Class |
|---|---|---|
| Premature-claim rate π | 0.65 (swept 0.3–0.95) | ASSUMED |
| P(claim \| complete) | 0.92 | ASSUMED |
| Outcome-class mix | as in Table XVI | ASSUMED |
| P(goal met \| class) | as in Table XVI | ASSUMED |
| Rejection on missing evidence | 0.8 | ASSUMED |
| Finish after rejection | 0.35 (swept) | ASSUMED |
| Action failure | 0.25 (swept) | ASSUMED |
| Memory gain / loss | 0.08 / 0.10 | ASSUMED |
| Per-attempt recovery rates | as in Table XVI | ASSUMED |
| Inference time | 3 s median (swept 1.5–6 s) | ASSUMED |
| Category mapping | as in Table XVI | ASSUMED |
| Missing-confirmation proxy | as in Table XVI | ASSUMED |
| Detection and false-rejection rates | from held-out gate counts via (k + 0.5)/(n + 1); Beta posterior in the Monte Carlo | DERIVED |
| Enhanced validation, guided recovery, relevance filter | their rates | PROPOSED |

**Seeds and sample sizes:**

| Setting | Value |
|---|---|
| Development seed | 101 |
| Held-out seed | 202 |
| Scenarios | 100 |
| Monte Carlo sets | 1,000 (seed 202·31 for rates; 202·1000 + r for scenarios) |
| Sensitivity sets per point | 300 |
| Recovery failures | 120 |
| Repeated workflows | 44 |
