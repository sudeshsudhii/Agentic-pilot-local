# R2: Statistical audit of "Agentic Pilot" (Agent 2, Statistical Auditor)

Repository state: HEAD `aee8c50`, working tree clean. No repository file was edited.
I wrote all the code myself and saved it in the scratchpad:
- `st.py`: Wilson, Clopper–Pearson by bisection on the exact binomial, exact two-sided McNemar using rational arithmetic, and type-7 percentile.
- `gate.py`: gate study, before-fix comparison and ablation.
- `lat_mem_egress.py`: latency, memory, egress and oracle checks.
- `sim.py`: the simulation, recomputed from `scenarios.csv` and `recovery_scenarios.csv`.
- `mc_check.py`: Monte Carlo check (see below).

How `mc_check.py` differs from the other scripts:
- **Why it calls project code.** The per-replication Monte Carlo values are not stored. To get them, the script calls the project's model functions `generate`, `run_set` and `sample_rates` read-only. It writes no files.
- **The stub.** `pydantic` is not installed, so the script stubs `backend.recovery.engine`. It passes the stored recovery probabilities (0.66 and 0.49 from `results.json`) explicitly, so the stub has no effect on the Monte Carlo outputs.
- **What is still my own code.** All percentiles, counts and tests are computed by my code.

**Bottom line: none of the checked printed numbers is numerically wrong.** All of the roughly 120 checked quantities match the raw files. The findings concern presentation and inference:
- p-values reported for discordant cells that are zero by construction;
- "significant" wording;
- tests that cannot reach significance at all;
- inconsistent p formatting;
- small gaps in the post-hoc disclosure;
- one Monte Carlo modelling artefact.

---

## 1. Recomputed values

Abbreviations:
- **W**: Wilson 95% interval. **CP**: Clopper–Pearson 95% interval.
- **McN**: exact two-sided McNemar test.
- **p-correct**: McNemar on paired decision correctness against the dispatch-only rule. The discordant pairs are b = withheld unsatisfied states and c = rejected satisfied states.

### 1a. Gate study (ACTUAL). Sources: verification_gate_cases.csv, verification_gate_cases_before_fixes.csv, verification_gate_ablation.csv

| Quantity | Recomputed | Printed | Location | Match |
|---|---|---|---|---|
| Design, after: W/n−, Wilson | 20/23, [0.679, 0.955] (CP 0.664–0.972) | 20/23 [.68,.95] | Abstract; Table IV; 07_results:11 | yes |
| Design, after: FR/n+ | 1/15, [0.012, 0.298] | 1/15 [.01,.30] | Table IV; Abstract | yes |
| Design, after: FC/R | 3/17 | 3/17 | Table IV | yes |
| Design, before (Φ direct / live empty / live verbose): W | 15 / 14 / 13 of 23 | 15 / 14 / 13 | 07_results:11; Table IV | yes |
| Design, before: W interval, FR, FC/R | [0.449, 0.812]; 3/15 [0.070, 0.452]; 8/20 | [.45,.81]; 3/15 [.07,.45]; 8/20 | Table IV | yes |
| Design: fixed / broken vs. before (Φ-direct mode) | 7 / 0 (live empty 8/0, live verbose 9/0) | "corrects 7 … without breaking any" | 07_results:11 | yes (the comparison is with the Φ-direct mode before the fixes) |
| All three modes agree after the fixes | 92/92 states agree | "all three modes agree on every state" | 07_results:11 | yes |
| Held-out 1, after: W, FR, FC/R, p | 2/5 [0.118, 0.769]; 1/7 [0.026, 0.513]; 3/9; p = 1.0 | same; p 1.0 | Table IV; 07:13 | yes |
| Held-out 1, before: W, FR, FC/R, p | 1/5 [0.036, 0.624]; 1/7; 4/10; p = 1.0 | same | Table IV | yes |
| **Held-out 2: W/n−** | **9/22 = 0.409, W [0.233, 0.613]** (CP 0.207–0.636) | 9/22 (0.41; 0.23–0.61) | Abstract; 07:13; Table IV; 08:4 (41%); 10:8 | yes |
| **Held-out 2: FR/n+** | **1/20 = 0.05, W [0.009, 0.236]** (CP 0.001–0.249) | 1/20 (0.05; 0.01–0.24); "upper bound 0.24" | Abstract; 07:13; 08:4 | yes |
| Held-out 2: FC/R | 13/32 | 13/32 | Table IV | yes |
| **Held-out 2: p-correct (9 vs 1)** | **0.021484375** | 0.021 / .021 | Abstract; 07:13; Table IV | yes |
| (For reference) Held-out 2: withheld-only test (9 vs 0), the earlier, degenerate test | 0.00390625 | not printed (correctly withdrawn) | n/a | n/a |
| **Pooled held-out 1+2: W, FR** | **11/27 [0.245, 0.593]; 2/27 [0.021, 0.234]** | 11/27 (0.25–0.59); 2/27 (0.02–0.23) | 07:13; Table IV | yes |
| **Pooled held-out 1+2: p-correct (11 vs 2)** | **0.0224609375** | 0.022 / .022 | 07:13; Table IV | yes |
| Pooled held-out 1+2: FC/R | 16/41 | 16/41 | Table IV | yes |
| Table IV per-category n−/n+, W, FR (design and held-out 2, 12 rows) | all 12 rows reproduced | n/a | Table IV upper block | yes |
| Held-out 2 extraction: W | 0 of 5 | "none of the 5 … is withheld" | 07:13 | yes |
| Ablation, design: FC/FR without E, H, Q, T, X, R, β | 8/1, 7/1, 4/1, 6/1, 6/0, 4/1, 5/1 | same | Table V | yes |
| Ablation, design: McN against the full gate | E 5/0 0.0625; H 4/0 0.125; Q 1/0 1; T 3/0 0.25; X 3/1 0.625; R 1/0 1; β 2/0 0.5 | .06, .13, 1.0, .25, .63, 1.0, .50 | Table V; 07:20 "p≥0.06" | yes (see F3, F5) |
| Ablation, held-out 1 and held-out 2: FC/FR | HO1: E 4/1, β 4/0, others 3/1. HO2: E 14/1, H 15/1, Q 13/1, T 14/1, X 13/1, R 15/1, β 15/0 | same | Table V | yes |
| Ablation, held-out: maximum decisions changed | 3 (HO2, without β); Q and X change 0 | "at most three"; "Q or X changes none" | 07:20; Table V caption | yes |
| Ablation "none" column equals gate_decision | 92/92 | (implicit) | n/a | yes |
| Gate latency: decisions that evaluate Φ | 83 (92 states minus 9 stopped by the pre-check) | 83 | 07:25; Table XI | yes |
| Gate latency: median | 26.84 ms | 26.8 ms; "27 ms" | 07:25; Abstract; 12; Table XI | yes |
| Gate latency: P90 / P95 / maximum | 29.49 (type 7: 29.47) / 30.31 (type 7: 30.29) / 34.64 ms | 29.5 / 30.3 / 34.6 | 07:25; Table XI | yes |
| Pre-check-stopped decisions: maximum | 13.36 ms (n = 9) | 13.4 ms | 07:25 | yes |

### 1b. Component inputs (ACTUAL). Sources: m2_latency.json, m4_memory.csv, e2e_smoke_stub/, e2e_oracle_validation.csv

| Quantity | Recomputed | Printed | Location | Match |
|---|---|---|---|---|
| Latency medians / p95 (rank round(0.95(n−1))+1), n = 30 each | navigate 17.14/24.94; click 65.215/106.22; fill 12.515/17.43; DOM 76.385/105.63; screenshot 61.26/93.57; Φ on site page 5.165/6.93 | 17.1/24.9; 65.2/106.2; 12.5/17.4; 76.4/105.6; 61.3/93.6; 5.2/6.9 | Table XI; 07b:39 | yes |
| Memory: queries; queries with a relevant record | 10; 9 | 10; 9 | Table IX; 07b:27 | yes |
| P@3 over the 9 queries | 0.5185 (equal to its ceiling, mean of min(3, n_rel)/3 = 0.5185) | 0.52 | Table IX | yes (see F10) |
| R@3 over the 9 queries | 1.00 | 1.00 | Table IX; 07b:27 | yes |
| MRR over the 9 queries | 0.9259 (0.833 over all 10) | 0.93 "over those 9" | Table IX; 07b:27 | yes |
| Top-1 irrelevant or failed | 3/10 (desk_contact failed; shop_price and unrelated irrelevant) | 3/10 | Table IX; 07b:27; Table XVI 0.30 | yes |
| Egress: episodes; connect calls | 70; 555, all 127.0.0.1:11435; 8 PIDs | 70; 555 | Abstract; 07:30; 12 | yes |
| Egress: non-local page hosts | 0 of 70 episodes | "every page request … 127.0.0.1" | 07:30 | yes |
| Egress: memory-enabled episodes with ≥1 record | 54/60 (6 configurations × 10; no_memory 0/10) | 54 of 60 | 07:30 | yes |
| Egress: browser actions; vision; knowledge | all 0 | "no browser action … never called the vision model … never retrieved documents" | 07:30 | yes |
| Oracle validation | 114/114 agree; 0/37 FN, Wilson upper 0.094; 0/77 FP, Wilson upper 0.048 | 0–0.09; 0–0.05 | 07:32 | yes |

### 1c. Simulation v2 (SYNTHETIC). Sources: out/heldout_v2/scenarios.csv, recovery_scenarios.csv, results.json

| Quantity | Recomputed | Printed | Location | Match |
|---|---|---|---|---|
| Claims; truly complete at the claim | 74; 46 (claimed set and y_claim identical across the 4 verifiers, asserted) | 74; 46 | 07b:11; Table VI | yes |
| Policy TP/FP/FN/TN: none, basic, Φ, enhanced | 46/28/3/23; 43/24/6/27; 44/19/6/31; 46/8/8/38 | same | Table VI | yes |
| TSR, FCR, FRR with Wilson (all 4 rows) | e.g. Φ: 44/100 [0.35, 0.54]; 19/63 [0.20, 0.42]; 6/50 [0.06, 0.24]. None: 28/74 [0.28, 0.49]; 3/49 [0.02, 0.17] | same | Table VI | yes (all 12 cells) |
| Decision TP/FP/FN/TN | 46/28/0/0; 43/24/3/4; 43/19/3/9; 41/8/5/20 | same | Table VI | yes |
| Decision accuracy with Wilson | 46/74 [0.51, 0.72]; 47/74 [0.52, 0.74]; 52/74 = 0.703 [0.59, 0.79]; 61/74 = 0.824 [0.72, 0.89] | same; 0.70, 0.62, 0.82 | Table VI; 07b:15; Abstract; Table III | yes |
| **Decision level: Φ vs none, b/c and p** | **3/9, p = 0.14599609375**. The 9 Φ-only-correct claims are all rejections with y = 0; the 3 none-only-correct claims are all false rejections | 3/9; 0.146 / 0.15 / .15 | Table VII; 07b:15; Abstract; Table III | yes |
| **Policy level: FC Φ vs none** | **19 vs 28; b/c = 9/0; p = 0.00390625** | 19 vs 28; 9/0; 0.00391 / 0.004 | Abstract; 07b:13; Table VII; Table III | yes (but see F1) |
| FC: basic vs Φ; enhanced vs Φ | 5/0, p = 0.0625; 0/11, p = 0.0009766 | 5/0 0.0625; 0/11 <0.001 | Table VII | yes (see F1) |
| Decision level: basic vs Φ; enhanced vs Φ | 0/5, p = 0.0625; 11/2, p = 0.0224609 | 0/5 0.0625; 11/2 0.0225 / "p=0.02" | Table VII; 07b:16 | yes (see F1, F5) |
| Success: none, basic, enhanced vs Φ | 3/1, p = 0.625; 0/1, p = 1; 4/2, p = 0.6875 | 3/1 0.625 / "p=0.63"; 0/1 1; 4/2 0.688 | Table VII; 07b:16 | yes |
| FCR 0.30 vs 0.38; basic FC count | 0.3016 vs 0.3784; 24 | 0.30 vs 0.38; 24 | 07b:13 | yes |
| MC FC reduction, Φ vs none (1000 sets) | mean 0.1106; v[25] = 0.05, v[974] = 0.18 (type 7: 0.05, 0.18) | 0.11 (0.05–0.18) | 07b:14 | yes |
| MC share of sets with FC p < 0.05 | 0.941; equal to the share of sets with b ≥ 6 (0.941); min b = 2 | not printed in the paper (ledger only) | n/a | n/a |
| MC share with decision accuracy Φ better at p < 0.05 | 0.419 (recomputed by re-driving the model) | 42% | 07b:15 | yes |
| MC mean FCR [2.5, 97.5]; mean decision accuracy | none .364 [.25, .479]; .636. Basic .325 [.213, .448]; .657. Φ .249 [.136, .369]; .739. Enhanced .139 [.042, .245]; .791 | .36 [.25,.48]; .64. .33 [.21,.45]; .66. .25 [.14,.37]; .74. .14 [.04,.24]; .79 | Table VII; 07b:15 | yes |
| Ablation (Table VIII): TP, FCR, FRR, F1 | Φ 44, .302, .120, .779; −Φ 46, .378, .061, .748; −memory 44, .312, .120, .772; −recovery 41, .305, .128, .774 | same | Table VIII | yes |
| Ablation (Table VIII): success b/c and p | −Φ 3/1, 0.625; −memory 1/1, 1; −recovery 0/3, 0.25 | same; 07b:21 "p=0.25" | Table VIII; 07b:21 | yes |
| Ablation (Table VIII): MC TSR / FCR | .468/.249; .465/.364; .466/.251; .446/.249 | 0.47/0.25; 0.47/0.36; 0.47/0.25; 0.45/0.25 | Table VIII; 07b:21 | yes |
| Memory subset (n = 44): TSR, FCR | off 19/44 [0.30, 0.58], .387; on 19/44, .367; filtered 20/44 [0.32, 0.60], .355 | same | Table IX; 07b:27; Table III | yes |
| **Recovery: failures; permanent; recoverable** | **120; 27 (0 of them missing confirmation); 93** | 120; 27; 93 | Table X caption | yes |
| Recovery: recovered (off / engine / guided) | 51/93 [0.45, 0.65]; 68/93 [0.63, 0.81]; 87/93 [0.87, 0.97] | same | Table X; 07b:33; Table III | yes |
| Recovery: detected; FC; unnecessary attempts; mean attempts | 111/120 [0.86, 0.96], 9, 81, 2.083. 111/120, 9, 174, 3.25. 118/120 [0.94, 1.00], 2, 162, 3.175 | same (3.17) | Table X; 07b:33 | yes |
| Recovery by mode (18 cells) | all reproduced | n/a | Table X lower block | yes |
| Recovery: guided-only vs engine-only | 19/0 | "19 … none only by the engine" | 07b:33 | yes |
| Latency (synthetic): median / mean (s); verification share; inference share | none 18.1/19.7, 0%. Φ 18.9/20.2, 0.11%, 79.6%. Self 21.2/22.4, 12.21%. Φ + model 22.6/24.0, 14.13%. Screenshots 4.1% | same; "80%", "0.1%", "+2.6%", "14% (22.4 s)" | Table XI; 07b:39; Table III | yes (+2.56%, +13.9%) |
| Latency sweep | 10.03 / 36.81 s | 10.0 / 36.8 | 07b:39 | yes |
| Sensitivity (Table XII, 12 rows; Fig. 3, 40 coordinates; 07b:46 text) | all reproduced from results.json | n/a | Table XII; Fig. 3; 07b:46 | yes |
| Derived rates (Table XVI) | navigation 2/6 → 0.357; search 2/4 → 0.50; form 3/6 → 0.50; data entry 1/3 → 0.375; extraction 0/6 → 0.071; multi-step 2/3 → 0.625; FR 0/24 → 0.02; missing confirmation 2/3 → 0.625. Independently tallied from the gate CSV (HO1 + HO2, bot-check excluded: 22 unsatisfied = 18 + 4; 24 satisfied) | same | Table XVI; 06:30 | yes |

**Mismatch count: 0 numerical mismatches out of roughly 120 checked quantities.**

---

## 2. Pairing and outcome-definition check

- **Gate vs dispatch-only.** Both are compared on the same states against the same oracle. "Correct" means (decision == completed) == oracle_satisfied. The pooled held-out 1+2 comparison is matched by state. Valid.
- **Gate before vs after.** Same 50 states, same oracle. Valid. It is correctly left untested on the design set.
- **Ablation.** Same states. Correctness is defined against the oracle. Valid.
- **Simulation, decision level.** I asserted that the 74 claimed scenarios and `y_claim` are identical for all four verifiers. The decisions therefore share one ground truth. Valid.
- **Simulation, policy level, FC and success.** Each configuration's indicator is defined on that configuration's own final state (`reported ∧ ¬y`, `reported ∧ y`). The indicators are paired by scenario with a common definition, but not on one shared truth. The paper states this correctly (07b:11; 06:41).
- **FCR is not the paired quantity.** The text at 07b:13 juxtaposes FCR (0.30 vs 0.38, with denominators 63 vs 74) with the paired test. The paired test is on FC per scenario (denominator 100). The text does say "Episodes end in a false completion 19 times", so this is acceptable.

---

## 3. Findings

**F1. Moderate.** Table VII (`paper/tables/sim/tests.tex:11-14`, generated by `benchmarks/simulation/make_tables.py:100-118`) prints McNemar p for discordant cells that are zero by construction. The text explains only one of them.

*What the code guarantees.* I derived this from `simulate_v2.py:episode()` (lines 194-247) and confirmed it over the 1000 Monte Carlo sets.

- **None vs Φ, FC 9/0.** This is structural. Under no verification every claim is accepted. Under Φ an unsatisfied claim is either accepted (FC in both configurations) or withheld. A withheld claim either continues to y = 1, where the re-check can only false-reject, so no FC is possible, or is not reported. So FC_Φ ⊆ FC_none and c ≡ 0. Φ-only FC occurred in 0 of 1000 sets.
- **Enhanced vs Φ, FC 0/11.** This is structural. Enhanced uses the same detection draw `u_detect` and rate as Φ, plus an extra catch and a contradiction reject. Its withheld set therefore contains Φ's, and its continuation re-check only adds rejections. So b ≡ 0: enhanced-only FC occurred in 0 of 1000 sets. The printed "<0.001" is entirely a consequence of the assumed extra catch rate and this nesting.
- **Basic vs Φ: FC 5/0, Decision 0/5, Success 0/1.** These are zero by construction in the reported set only. The point-estimate withhold rate of basic is ≤ Φ's in every category (equal for navigation and extraction). Both rules use the same `u_detect`, and their false-rejection rates are identical (0.02, same `u_fr` and `u_fr2`). Basic's decisions are therefore a weak subset of Φ's. The nesting matches the implementation: on all 92 measured gate states, no state is rejected by basic and accepted by Φ (`m1_gate_rules.csv`). It does not hold in the Monte Carlo sets, because the two rates are drawn independently there (see F6). Consequently Decision 0/5 (p = 0.0625) and Success 0/1 (p = 1) are also single-cell results.

*What an exact McNemar test can and cannot mean when one cell is structurally 0.*

- **How the test works.** The exact test conditions on n = b + c and refers b to Bin(n, ½), the distribution under H0: P(only A) = P(only B).
- **Why it says nothing here.** If P(c-type discordance) = 0 by construction, H0 holds only when there is no discordance at all. One discordant pair already refutes it with certainty, and the binomial reference distribution describes no possible sampling distribution of the model.
- **What the printed p reduces to.** It is a deterministic function of the non-zero count, p = 2^(1−b): 0.0039 just re-expresses b = 9, 0.0625 re-expresses b = 5, and "<0.001" re-expresses b = 11.
- **The share statistic is the same function.** The Monte Carlo "share of sets with FC p < 0.05" (0.941) is exactly the share of sets with b ≥ 6 (0.941).
- **The direction is not tested.** The model fixes it in advance, so the test contributes nothing to H1's direction. Nor can it support "Φ significantly reduces false completions."
- **What it can mean, at most.** It is a descriptive restatement that the count b is not small.
- **What is informative.** The size of the paired reduction:
  - in the reported set, b/N = 9/100 = 0.09 (Wilson 0.05–0.16, conditional on the assumptions);
  - its Monte Carlo distribution, 0.11 [0.05, 0.18];
  - its dependence on the premature-claim rate (Study H).

*Is the current wording correct?* 07b:14 is correct and adequate for the None row. It says "one discordant cell is always 0, and only the size of the reduction is informative", and that the interval, not the p-value, is the informative result. Table III row H1 ("lower by construction") is correct. The text still prints "exact McNemar p = 0.004" (07b:13), however. Table VII's caption does not flag any structural zero, and Enhanced "0/11, <0.001" and Basic "5/0", "0/5", "0/1" are not explained anywhere.

*Fix (preferred).*
- In Table VII, replace the FC p column with "FC reduction" (the single-set reduction (b − c)/100 and the Monte Carlo mean [2.5, 97.5]).
- Print "--$^{\S}$" for every p whose b/c has a cell that is zero by construction.

The Monte Carlo paired reductions for basic and enhanced are not in `results.json`. Re-driving the model (summary only, no parameter change), I obtain basic 0.060 [0.000, 0.120] and enhanced −0.083 [−0.140, −0.030]. These would have to be added to `simulate_v2.py`'s output before being printed. Proposed rows:

```
Config. & FC $b/c$ & FC red.\ (MC) & Dec.\ $b/c$ & $p$ & Succ.\ $b/c$ & $p$ & MC FCR; dec.\ acc. \\
None & 9/0$^{\S}$ & .09 (.11 [.05,.18]) & 3/9 & 0.15 & 3/1 & 0.63 & .36 [.25,.48]; .64 \\
Basic & 5/0$^{\S}$ & .05 (.06 [.00,.12]) & 0/5$^{\S}$ & -- & 0/1$^{\S}$ & -- & .33 [.21,.45]; .66 \\
Enhanced$^{\ddagger}$ & 0/11$^{\S}$ & $-$.11 ($-$.08 [$-$.14,$-$.03]) & 11/2 & 0.022 & 4/2 & 0.69 & .14 [.04,.24]; .79 \\
```

Caption sentence to add: "$^{\S}$One discordant cell is 0 by construction of the model: $\Phi$ withholds every claim that no verification withholds and enhanced validation every claim that $\Phi$ withholds; at the point-estimate rates basic detection withholds a subset of $\Phi$'s claims (its rate is no higher in any category and both use the same random draws). With one cell fixed at 0 the exact McNemar $p$ equals $2^{1-b}$, a function of the non-zero count alone, so it is not reported; the paired reduction and its Monte Carlo interval are the informative quantities."

*Fix (minimal, if the table is not regenerated).* Keep the table and add the caption sentence above, with "is reported only descriptively" in place of "is not reported".

*Text fix, 07b:13.* Replace "(FCR 0.30 against 0.38; discordant pairs 9 and 0, exact McNemar $p=0.004$; Table~\ref{tab:sim-tests})" with: "(FCR 0.30 against 0.38; 9 scenarios end in a false completion only without verification and, by construction, none only with $\Phi$; Table~\ref{tab:sim-tests})".

*Text fix, 07b:14.* Replace "because one discordant cell is structurally 0, this interval, not the $p$-value, is the informative result" with "this interval is the informative result (in this set, 9 of 100 scenarios; Wilson 0.05--0.16)".

*Text fix, 07b:16.* After "$p=0.02$" add: "; its 11 false completions fewer than $\Phi$ are, as for $\Phi$ against no verification, fixed in direction by construction".

**F2. Moderate.** "Significant share" (`paper/sections/07_results.tex:13`, `paper/sections/08_discussion.tex:4`). The only test is McNemar on decision correctness against dispatch-only (9 vs 1, p = 0.021). It tests whether the gate decides more states correctly than accepting everything. It does not test the withheld share: that share is trivially > 0, since dispatch-only withholds none. In addition, both discordant counts scale with the constructed n−/n+ = 22/20, so the p-value depends on the chosen composition. Prior audit item O2 flagged this; it is unresolved.

- Fix, 07:13: replace "the gate withholds a significant share of premature completions, with a false-rejection rate whose 95\% upper bound is 0.24, but far fewer than on the states it was designed on." with "the gate decides more held-out states correctly than a dispatch-only rule (9 against 1 discordant states, $p=0.021$), withholding 41\% of unsatisfied states (95\% interval 0.23--0.61) with a false-rejection rate whose 95\% upper bound is 0.24, far fewer than on the states it was designed on."
- Fix, 08:4: replace "withholds a significant share of premature completions on constructed browser states (41\% of unsatisfied held-out states)" with "withholds 9 of 22 premature completions on constructed held-out browser states (41\%; 95\% interval 0.23--0.61) and decides more of them correctly than a dispatch-only rule (exact McNemar $p=0.021$)".
- Optional, Table IV caption (`paper/tables/gate_results.tex:3`), after "(discordant pairs: … does)": "; because both counts scale with $n^{-}$ and $n^{+}$, $p$ depends on the constructed balance of the set."

**F3. Minor.** The ablation sentence implies a test that could have succeeded (`paper/sections/07_results.tex:20`). The largest number of discordant states for any removal is 5 (E: 5/0). With 5 discordant pairs the smallest attainable exact two-sided p is 0.0625. No removal could therefore have reached p < 0.05, regardless of the effect.

- Fix: replace "but with 23 unsatisfied states no single removal reaches $p<0.05$ ($p\geq0.06$), which with so few states is not evidence that a conjunct is unnecessary" with "but no removal changes more than five decisions, so none could reach $p<0.05$ (with five discordant states the smallest attainable exact $p$ is 0.063); this is not evidence that a conjunct is unnecessary".

**F4. Minor.** "No power" for held-out 1 (`paper/sections/07_results.tex:13`).

- Fix: replace "On held-out~1 alone (2 against 1) the test has no power ($p=1.0$)." with "On held-out~1 alone (2 against 1) the test cannot reach significance: with three discordant states the smallest attainable $p$ is 0.25 (observed $p=1.0$)."

**F5. Minor.** p-value formatting is inconsistent across the paper. Two table generators use different conventions: the simulation tables use `make_tables.py:48`, `f"{p:.3g}"`; the gate tables use two decimals without a leading zero. The text uses yet another mix. The same value is printed differently:

| Exact value | Printed as |
|---|---|
| 0.0224609 | ".022" (Table IV), "0.022" (07:13), "0.0225" (Table VII, Enhanced decision), "0.02" (07b:16) |
| 0.00390625 | "0.00391" (Table VII), "0.004" (07b:13) |
| 0.1459961 | "0.146" (Table VII), "0.15" (Abstract; 07b:15), ".15" (Table III) |
| 0.0625 | ".06" (Table V), "0.0625" (Table VII), "$p\geq0.06$" (07:20) |
| 0.625 | "0.625" (Tables VII, VIII), "0.63" (07b:16), ".63" (Table V) |
| 0.6875 | "0.688" (Table VII) |
| 1 | "1" (Tables VII, VIII), "1.0" (Tables IV, V; 07:13) |
| 0.0009766 | "<0.001" (Table VII) |

*Proposed single convention:* exact p to two significant figures, leading zero, round half up. Print values below 0.001 as "<0.001" and p = 1 as "1.0". Print the same value identically in text and tables.

*Resulting changes:*

| Location | Current | New |
|---|---|---|
| Table IV | .021, .022 | 0.021, 0.022 |
| Table V | .06, .13, .25, .63, .50 | 0.063, 0.13, 0.25, 0.63, 0.50 |
| Table III | $p{=}.15$ | $p{=}0.15$ |
| Table VII | 0.146; 0.0225; 0.625; 0.688; "1" | 0.15; 0.022; 0.63; 0.69; 1.0 (FC and structural p per F1) |
| Table VIII | 0.625; 1 | 0.63; 1.0 |
| 07b:13 | 0.004 | removed per F1 (otherwise 0.0039) |
| 07b:16 | $p=0.02$ | $p=0.022$ |
| 07:20 | $p\geq0.06$ | removed per F3 (otherwise 0.063) |

*Generator note.* `.2g` with Python formatting rounds 0.0625 half-even, to 0.062. Use `decimal.Decimal(...).quantize(..., ROUND_HALF_UP)` on the significant digits. The prior audit (M4) adopted half-up for ties.

**F6. Minor.** The Monte Carlo breaks the basic ⊆ Φ nesting (`benchmarks/simulation/simulate_v2.py:83-92`, `sample_rates`). Basic's and Φ's per-category rates are drawn from independent Beta posteriors. This includes navigation and extraction, where both rules have identical k/n because Φ contains E. The implementation and all 92 measured states imply that basic never withholds a claim Φ accepts. In the regenerated sets, however:

- Φ alone ends in a false completion against basic in 394 of 1000 sets;
- basic alone decides correctly in 542 of 1000 sets.

The Table VII "Basic" Monte Carlo cells (.33 [.21,.45]; .66) therefore include outcomes that are impossible in the implementation. This is a disclosure issue, not a request to change parameters.

- Fix: add to the Table VII caption: "In the Monte Carlo sets the rates of basic detection and $\Phi$ are drawn independently, so the nesting of basic detection within $\Phi$ that holds in the implementation is not enforced there."

**F7. Minor.** Gaps in the post-hoc disclosure. Most of it is present:

- 07b box "(v2, post hoc)";
- 06:34 "not pre-registered";
- 10:10 "not pre-registered … choice of what to correct was made with the results in view";
- Abstract "a model corrected after an audit".

Three gaps remain:

(a) The v1 freeze sentence at `paper/sections/06_methodology.tex:32`, "Parameters and code were committed (\texttt{3a0aa8e}) before the reported held-out set … was generated", can be read as applying to the reported (v2) numbers.
- Fix: replace "Parameters and code were committed" with "For the original model (v1), parameters and code were committed", and "the reported held-out set" with "the held-out set".

(b) The decision-level analysis, and decision accuracy as the dependent variable of H2, were introduced after the v1 results were known (prior audit O4). The paper discloses the code change but not that the outcome definition is post hoc.
- Fix, at the end of "…for the decision-level analysis; outputs were otherwise byte-identical." (06:32), add: " This decision-level analysis, and decision accuracy as the dependent variable of H2, were defined after the v1 results were known."

(c) Table III and Table VII captions do not say "post hoc".
- Fix, Table III (`paper/sections/05b_hypotheses.tex:8`): replace "Last column: outcome in the \textsc{simulation} (Section~\ref{sec:sim-results})" with "Last column: outcome in the \textsc{simulation} (corrected model v2, post hoc; Section~\ref{sec:sim-results})".
- Fix, Table VII: after "Paired comparisons with $\Phi$" insert " (corrected model v2, post hoc)".

**F8. Minor.** The abstract does not say that the FC reduction is guaranteed in direction (`paper/sections/00_abstract.tex:2`). "the gate reduced episode-level false completions (19 against 28 of 100 synthetic scenarios)" reads as a finding, but the model makes an increase impossible.

- Fix: replace with "the gate reduced episode-level false completions (19 against 28 of 100 synthetic scenarios, a direction the model guarantees, so only the size is informative)".

**F9. Info.** Conditional interpretation of synthetic significance. I checked every synthetic p and interval:

- the 07b box;
- Table III "(cond.)";
- the captions of Tables VI, VII, VIII and IX;
- 05b:4 (H4 and enhanced carry no information beyond assumptions);
- 07b:16 ("follows from its assumed detection rates");
- 07b:27 (underpowered);
- 07b:33 ("consequence of its assumed success rates");
- 06:41;
- 10:10 (100 scenarios is chosen, so synthetic significance is partly a matter of that choice);
- Abstract ("conditional on the assumptions").

All are interpreted conditionally. No unconditional claim of synthetic significance was found. The design-set gate results are correctly left untested (Table IV "--"; 07:11), and the Table V p is labelled descriptive.

**F10. Info.** P@3 = 0.52 is exactly its ceiling, given 1–2 relevant records per query. 07b:27 says "precision@3 is bounded by the number of relevant records per query".

- Optional: replace with "precision@3 (0.52) equals the maximum attainable given one or two relevant records per query".

**F11. Info.** Monte Carlo percentile indexing (`simulate_v2.py:338`) uses v[int(0.025n)] = v[25], the 26th order statistic, and v[int(0.975n)−1] = v[974], the 975th. The two are off by one asymmetrically. For the printed FC-reduction interval, v[24]/v[25] and type-7 interpolation all give 0.05 and 0.18, so no printed value changes.

---

## 4. Summary

- **Numerical mismatches: 0 of roughly 120 recomputed quantities.** All targets in the brief are confirmed:
  - held-out 2: 9/22 withheld [0.23, 0.61], 1/20 false rejections [0.01, 0.24], p = 0.021484;
  - pooled held-out 1+2: 11/27 and 2/27, p = 0.022461;
  - decision level: 52/74 vs 46/74, p = 0.14600;
  - policy-level false completions: 19 vs 28 of 100, 9/0, p = 0.0039063;
  - recovery: 120 failures, 27 permanent, 93 recoverable;
  - memory: 10 queries, 9 with a relevant record, P@3 = 0.519, R@3 = 1.00, MRR = 0.926;
  - gate latency: median 26.84 ms over 83 decisions;
  - egress: 70 episodes, 555 connects, all to 127.0.0.1:11435.
- **Findings:** 2 Moderate (F1 Table VII structural zeros; F2 "significant share"), 6 Minor (F3–F8), 3 Info (F9–F11).

---

## 5. Addendum: working-tree edits made by other agents during this audit

Sections 1–4 audit HEAD `aee8c50`. While I was working, other agents modified 24 files in the working tree. I did not touch any of them. I re-checked the passages that bear on my findings.

### Status of findings in the current working tree

| Finding | Status | What the working tree now says |
|---|---|---|
| F2 | **Resolved** | 07:13 now reads "the gate is correct on significantly more held-out states than a dispatch-only rule and withholds 41\% of premature completions". 08:4 has equivalent wording. |
| F7(a) | **Resolved** | 06 now begins "For v1, parameters …" and adds that the reported results come from the post-hoc v2. |
| F8 | **Resolved** | The abstract now adds "a direction fixed by construction" and "revised post hoc, after its first results were known". |
| F1 | **Partly resolved** | See below. |
| F3, F4 | Open | 07:20 still says "$p\geq0.06$". 07:13 still says "no power". |
| F5 | Open | Formatting is now also inconsistent within Table III: "$p{=}.021$" and "$p{=}.15$" vs "$p=0.021$" in the abstract. |
| F6 | Open | Not addressed. |
| F7(b), F7(c) | Open | Not addressed. |

### F1 in the current working tree

The Table VII caption now says: "For FC against None and Basic, $c=0$ by construction ($\Phi$ only withholds claims; for Enhanced, $b=0$likewise), so those $p$-values carry no information about direction". Three problems remain:

1. **The reason given is wrong for Basic.** Basic also only withholds claims. Its c = 0 comes from basic's withheld set being nested in Φ's at the point-estimate rates (same random draws, rate ≤ Φ's in every category, identical FR rate). It is not structural in the Monte Carlo sets, where Φ-only FC against basic occurs in 394 of 1000.
2. **Two Basic zeros are not covered.** Decision 0/5 (p = 0.0625) and Success 0/1 are not mentioned.
3. **The p-values are still printed.** They remain in the table and in 07b:13 ("$p=0.004$"). They are not only uninformative about direction: each equals 2^(1−b), a function of the count alone.

Fix: replace the parenthesis with "($\Phi$ withholds every claim that no verification withholds and enhanced validation every claim that $\Phi$ withholds; at the point-estimate rates basic detection withholds a subset of $\Phi$'s claims, which also makes its Dec.\ and Succ.\ cells 0/5 and 0/1)". Then add: "with one cell fixed at 0, $p=2^{1-b}$ depends on the count alone". Apply the 07b:13 replacement from F1.

### New numbers in the working tree, recomputed

| Quantity | Recomputed | Location | Match |
|---|---|---|---|
| Φ's 3 decision-level false rejections: outcomes | S202-012 and S202-060 missing_evidence, S202-087 ambiguous | 07b:15 "two of them on scenarios with missing evidence"; Table III "2 of 3" | yes |
| Gate correct vs dispatch-only correct, held-out 2 | 28 (9 + 19) vs 20 of 42 | Table III, H2 | yes |
| Decision FRR, Φ vs none | 3/46 vs 0/46 | Table III, H5 | yes |
| v1 success, Φ vs none | 37 vs 43 (1/7, p = 0.0703) | 06 (v2 paragraph) "p=0.07" | yes |
| v1 decision accuracy, Φ vs none | 45/71 vs 43/71 (decision_analysis.json) | 06 | yes |
| v1 Φ false-rejection rate | 0.0893 (2/27 → (2+0.5)/28) | 06 | yes |
