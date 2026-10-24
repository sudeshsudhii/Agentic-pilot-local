# Numerical consistency report: Tables VI–XII vs. narrative and datasets

**Scope.** This report checks the simulation tables (Tables VI–XII) and the gate tables (IV–V) against:

- the per-scenario datasets;
- `results.json`;
- the prose of §VIII, §IX, the abstract, Table III and the discussion.

Table numbers follow the current PDF:

| Table | Content |
|---|---|
| VI | sim-baseline |
| VII | sim-tests |
| VIII | sim-ablation |
| IX | sim-memory |
| X | sim-recovery |
| XI | sim-overhead |
| XII | sim-sens |
| XVI | sim-params |

**How it was checked.** Three methods were used:

1. **Recomputation with separately written code.** The final reviewer wrote `recompute_sim.py`, `recompute_gate.py`, `recompute_rates.py` and `wilson.py`, with no project imports. They were re-run after the last model correction, and every value below was recomputed from `scenarios.csv` / `recovery_scenarios.csv` / `verification_gate_cases*.csv`.
2. **Byte-for-byte rerun.** `simulate_v2` → `make_tables` was rerun and reproduces all nine `paper/tables/sim/*.tex` files and the ledger. `gate_stats.py` reproduces `gate_stats.csv`.
3. **Text check.** Every number in the prose was checked against the tables.

## Results

| Table | Quantity | Dataset value (recomputed) | Table | Narrative | Status |
|---|---|---|---|---|---|
| VI | Policy TP/FP/FN/TN, none / basic / Φ / enhanced | 46/28/3/23; 43/24/6/27; 44/19/6/31; 46/8/8/38 | same | §IX-A: 19 vs 28 FC; 44 vs 46 tasks | ✔ |
| VI | TSR, FCR, FRR (Wilson) | e.g. Φ 44/100 [.35,.54], FCR .302, FRR .120 | same | §IX-A: FCR 0.30 vs 0.38 | ✔ |
| VI | Decision TP/FP/FN/TN, accuracy (74 claims, 46 true) | none 46/28/0/0 (.62); basic 43/24/3/4 (.64); Φ 43/19/3/9 (.70); enh 41/8/5/20 (.82) | same | §IX-A H2; abstract "52 against 46 of 74"; Table III | ✔ |
| VII | FC b/c, p vs Φ | none 9/0 .0039; basic 5/0 .0625; enh 0/11 <.001 | same | §IX-A H1 | ✔ |
| VII | Decision b/c, p | none 3/9 .146; basic 0/5 .0625; enh 11/2 .0225 | same | abstract p=0.15; §IX-A | ✔ |
| VII | Success b/c, p | none 3/1 .625; basic 0/1 1; enh 4/2 .688 | same | §IX-A "3 … 1 … p=0.63" | ✔ |
| VII | MC FCR [2.5, 97.5]; decision accuracy | Φ .25 [.14,.37], .74; none .36 [.25,.48], .64 | same | §IX-A "0.74 against 0.64", "42%" | ✔ (rerun only) |
| VIII | Full / −Φ / −memory / −recovery engine | 44; 46 (3/1, .625); 44 (1/1, 1); 41 (0/3, .25) | same | §IX-B "0.44 to 0.41 … p=0.25 … 0.47 to 0.45" | ✔ |
| IX | Retrieval P@3 / R@3 / MRR; misleading top-1 | .52 / 1.00 / .93; 3/10 (ACTUAL) | same | §IX-C | ✔ |
| IX | Repeated workflows off / on / filtered | 19, 19, 20 of 44 | same | §IX-C; Table III H3 | ✔ |
| X | Recovered of 93: engine off / on / guided | 51, 68, 87 | same | §IX-D | ✔ |
| X | Detected; FC; unnecessary attempts; mean attempts | 111, 111, 118 of 120; 9, 9, 2; 81, 174, 162; 2.08, 3.25, 3.17 | same | §IX-D "174 … 162" | ✔ |
| X | By mode (18 cells); guided vs engine paired | as printed; 19/0, p=3.8e-6 | same | §IX-D "19 … none" | ✔ |
| XI | ACTUAL component latency (ms) | navigate … Φ 5.2; gate states 26.8 (83 decisions) | same | §IX-E; §VIII-C | ✔ |
| XI | SYNTHETIC medians: none / Φ / self / enhanced | 18.1 / 18.9 / 21.2 / 22.6 s; mean 19.7 / 20.2 / 22.4 / 24.0 | same | §IX-E "+2.6%", "14%", "80%", "0.1%" | ✔ (rerun only) |
| XII | Sensitivity rows | e.g. ×0.5 → FCR .30; missing evidence FRR .09/.14/.22; continuation TSR .45/.47/.50 | same | §IX-F | ✔ (rerun only) |
| Fig. 3 (sim-sens) | FCR/FRR vs π | Φ .14→.32; none .21→.45; FRR ≈ .14 vs .08 | same | §IX-F | ✔ (rerun only) |
| XVI | Derived rates; P(recover) 0.66/0.49 | from `m1_gate_rules.csv`, Study E | same | §VII-C | ✔ |
| IV | W, FR, FC/R per set; corrected McNemar | HO2 9/22, 1/20, 13/32, p=.0215; pooled 11/27, 2/27, p=.0225 | same | abstract; §VIII-A; §X | ✔ |
| V | Ablation FC/FR and design-state p | as printed (p rounded half-up) | same | §VIII-B | ✔ |

## Inconsistencies found and resolved in this audit

| Problem | Resolution |
|---|---|
| Memory corpus stated as "23 records" | 22 records (14 group records + 8 distractors). |
| Parameter table omitted 7 parameters | Added. |
| Two random streams (Table VII Monte Carlo, Table XII sensitivity) gave slightly different values for the same configuration | Disclosed in the caption. |
| Half-even rounding (0.125 → .12, 0.625 → .62) | Now half-up (.13, .63). p-values are printed to 3 significant figures. |
| "Close to no verification" | Now "about halfway". |
| Discordant-pair order in §IX-A differed from Table VII | Aligned. |
| "Continuation recovers about as many" | Now "costs 3, recovers 1". |
| Recovery entry paths for need_help and the initial navigation contradicted the code (final review F1) | Model corrected. Tables VIII, X and XVI and the §IX-B/D text regenerated. |
| The latency table mixed two machines | Disclosed in the caption. |

## Flagged, not resolvable from the available data

1. **Studies A–E and H before commit `41a6097`.** The claim that this latency fix left them unchanged cannot be re-verified: the outputs from before that commit were not kept.
2. **Gate decisions of the pre-fix code (`08653e2`).** They were not re-executed in this audit.
3. **Monte Carlo, sensitivity and latency-model values.** They are confirmed by the deterministic rerun only, not by separately written code.
