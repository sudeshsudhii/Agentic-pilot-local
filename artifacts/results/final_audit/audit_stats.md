# Statistical audit of "Agentic Pilot" (paper/main.pdf)

Auditor scripts (own code, run with `.venv-eval/bin/python -I -B`, no repository file modified; `git status` clean before and after):

- `audit_gate.py` → `audit_gate.out`: gate study, ablation, latency, oracle validation (ACTUAL data)
- `audit_sim.py` → `audit_sim.out`: Studies A–H (SYNTHETIC). Counts come from `scenarios.csv` and `recovery_scenarios.csv` with my own code. For the Monte Carlo, sensitivity and latency values I imported the repository's `generate`/`episode`/`latency_study` functions without writing anything, and did the aggregation, percentiles and tests myself.
- `extra.py`: smoothing artefact, re-claim count, task set, egress episodes

All files are in `/tmp/claude-0/-home-user-Agentic-pilot-local/9002c3ac-134c-52d7-af0a-ddf50aa21ff5/scratchpad/`.

Conventions used in this audit:

- Wilson intervals use z = 1.96.
- McNemar p-values are exact, two-sided: p = min(1, 2·Σ_{i≤min(b,c)} C(b+c,i)/2^(b+c)).
- Cohen's h = 2·asin√p1 − 2·asin√p2.
- "OK" means the value agrees with my recomputation after rounding to the printed precision.

## 1. Summary

- **Numerical mismatches: 4**
  - 2 substantive: M1 and M2.
  - 2 minor: M3, an inconsistent "same quantity" pair, and M4, rounding/format.
- **Wording mismatch: 1** (W1, a misleading characterization of a correct number).
- **Statistically inappropriate or questionable analyses: 10** (A1–A10).
- **Reproduction:**
  - Every count, rate, Wilson interval, McNemar p, Cohen's h and the ΔFC bootstrap interval in Tables IV–X, and every number in Sections VIII and IX, was reproduced.
  - The bootstrap intervals of Table VII also reproduce **exactly**, both with the repository's algorithm (seed 7, 10,000 reps) and with an independent numpy bootstrap (seed 12345, 20,000 reps). The difference is on a 0.01 grid, so the percentile limits are stable.
  - The Monte Carlo summaries (Tables VII and VIII, `mc_paired_fc_diff.json`), the sensitivity results (Table XII, Fig. 3) and the synthetic latency (Table XI) reproduce exactly when the generator is re-run.
  - Regenerating the held-out per-scenario outcomes reproduces `scenarios.csv` with 0 mismatches.

## 2. Table of checked numbers

### 2.1 Table IV (gate study; source: `verification_gate_cases*.csv`)

**Categories (upper block)**

All 12 rows agree: Design and Held-out 2, each × 6 categories, on n−/n+, W and FR.

| Category | Design n−/n+, W, FR | Held-out 2 n−/n+, W, FR |
|---|---|---|
| Search | 4/3, 4, 0 | 3/3, 2, 0 |
| Navigation | 6/2, 5, 0 | 4/4, 1, 0 |
| Bot check (`captcha`) | 4/2, 3, 0 | 4/2, 3, 1 |
| Text entry | 3/3, 3, 0 | 3/3, 1, 0 |
| Extraction | 4/3, 4, 1 | 5/5, 0, 0 |
| Multi-step | 2/2, 1, 0 | 3/3, 2, 0 |

Category totals are 23/15 for Design and 22/20 for Held-out 2. Status: **OK**.

**Totals (lower block)**

| Row | Reported | Recomputed | Status |
|---|---|---|---|
| Design before W | 15/23 [.45,.81] | 15/23 [0.449,0.812] | OK |
| Design before FR | 3/15 [.07,.45] | 3/15 [0.070,0.452] | OK |
| Design before FC/R | 8/20 | 8/20 | OK |
| Design before p | <.001 | 6.1e-5 (FC-only test, b=15, c=0) | OK (see A2) |
| Design after W | 20/23 [.68,.95] | 20/23 [0.679,0.955] | OK |
| Design after FR | 1/15 [.01,.30] | 1/15 [0.012,0.298] | OK |
| Design after FC/R | 3/17 | 3/17 | OK |
| Design after p | <.001 | 1.9e-6 | OK (A2, A3) |
| Held-out 1 before W | 1/5 [.04,.62] | 1/5 [0.036,0.624] | OK |
| Held-out 1 before FR | 1/7 [.03,.51] | 1/7 [0.026,0.513] | OK |
| Held-out 1 before FC/R | 4/10 | 4/10 | OK |
| Held-out 1 before p | 1.0 | 1.0 | OK |
| Held-out 1 after W | 2/5 [.12,.77] | 2/5 [0.118,0.769] | OK |
| Held-out 1 after FR | 1/7 [.03,.51] | 1/7 | OK |
| Held-out 1 after FC/R | 3/9 | 3/9 | OK |
| Held-out 1 after p | .50 | 0.50 (FC-only) | OK (A2: the correct-decision test gives 1.0) |
| Held-out 2 W | 9/22 [.23,.61] | 9/22 [0.233,0.613] | OK |
| Held-out 2 FR | 1/20 [.01,.24] | 1/20 [0.009,0.236] | OK |
| Held-out 2 FC/R | 13/32 | 13/32 | OK |
| Held-out 2 p | .004 | 0.0039 (FC-only) | OK (A2: the correct-decision test gives 0.021) |
| Held-out 1+2 W | 11/27 [.25,.59] | 11/27 [0.2451,0.593] | OK |
| Held-out 1+2 FR | 2/27 [.02,.23] | 2/27 [0.021,0.234] | OK |
| Held-out 1+2 FC/R | 16/41 | 16/41 | OK |
| Held-out 1+2 p | .001 | 0.00098 | Minor: should print "<.001" like the design rows (M4) |

Mode agreement after the fixes: in all 92 states the direct, live-empty and live-verbose modes agree, with 0 disagreements. **OK**. The oracle labels are identical before and after the fixes.

### 2.2 Section VIII-A narrative

| Claim | Recomputed | Status |
|---|---|---|
| Before fixes: withheld 15/23, rejected 3/15 | 15, 3 | OK |
| Live node before fixes withheld 14 (empty) / 13 (verbose) | 14 / 13 (disagreeing cases X2, P1) | OK |
| Design 20/23, p<0.001 | 1.9e-6 | OK |
| Corrects 7 states, breaks none, p=0.016 | fixed 7, broken 0, p=0.0156 (direct mode; live modes 8 or 9) | OK (A3) |
| HO2 9/22 (0.41; 0.23–0.61; p=0.004), rejects 1/20 | OK | OK |
| Pooled 11/27 (0.25–0.59), rejects 2/27 | OK | OK |
| None of the 5 unsatisfied extraction states withheld | 0/5 (HO2); HO1 H11 is also not withheld | OK |

The abstract repeats these figures (20/23, 0.68–0.95, 1/15, 9/22, 0.23–0.61, p=0.004, 42 states, 0/5) and the Conclusion's "41%" is the same 9/22. All **OK**.

### 2.3 Table V (ablation; source: `verification_gate_ablation.csv`)

`without_none` equals `gate_reports_complete` in every state.

| Removed | Design FC/FR | p (correct decisions, full better/ablated better) | HO1 FC/FR | HO2 FC/FR | Status |
|---|---|---|---|---|---|
| none | 3/1 | – | 3/1 | 13/1 | OK |
| E | 8/1 | 0.0625 (5/0) → ".06" | 4/1 | 14/1 | OK |
| H | 7/1 | 0.125 (4/0) → ".12" | 3/1 | 15/1 | OK (".13" under half-up rounding, M4) |
| Q | 4/1 | 1.0 (1/0) | 3/1 | 13/1 | OK |
| T | 6/1 | 0.25 (3/0) | 3/1 | 14/1 | OK |
| X | 6/0 | 0.625 (3/1) → ".62" | 3/1 | 13/1 | OK (".63" under half-up rounding, M4) |
| R | 4/1 | 1.0 (1/0) | 3/1 | 15/1 | OK |
| β | 5/1 | 0.5 (2/0) | 4/0 | 15/0 | OK |

Section VIII-B narrative:

- "p ≥ 0.06": OK.
- "each removal changes at most three decisions" on the held-out sets: OK per set. The maximum is β on HO2 with 3 changes. Pooled over HO1+HO2, β changes 5.
- "removing Q or X changes none": OK.
- β on HO2 13→15 FC, 1→0 FR: OK.
- X on design 3→6 FC, 1→0 FR: OK.

Pairing is valid: same states, same oracle label.

### 2.4 Section VIII-C and Table XI, Φ on gate states (latency)

| Claim | Recomputed | Status |
|---|---|---|
| 83 decisions evaluate Φ | 92 − 9 blocked = 83 | OK |
| median 26.8 ms | 26.84 | OK |
| 90th percentile 29.5 | 29.39–29.66 depending on method (linear 29.47) | OK |
| 95th percentile 30.3 | 30.12–30.45 (linear 30.29; nearest 30.31) | OK |
| max 34.6 | 34.64 | OK |
| pre-check-stopped decisions ≤ 13.4 ms | max 13.36 | OK |
| Abstract and Conclusion "median of 27 ms" | 26.84 | OK |

### 2.5 Section VIII-D (egress, tests, oracle)

| Claim | Recomputed | Status |
|---|---|---|
| 70 episodes, 10 dev tasks × 7 configs, 6 with memory | 70; configs full, no_verification, self_verification, no_recovery, no_memory, gate_without_T, recovery_replan_only | OK |
| 555 attempts all to 127.0.0.1 | `egress_summary.json`: {"127.0.0.1": 555}; `non_local_page_hosts` empty in all 70 | OK |
| 144 of 147 tests pass, 3 failures | `junit_revision.xml`: tests=147, failures=3, errors=0 | OK |
| 114 trajectories (40 golden, 40 idle, 34 near-miss) | 40/40/34 | OK |
| 0 FN among 37 achieved (0–0.09) | 0/37, Wilson upper 0.094 | OK |
| 0 FP among 77 unachieved (0–0.05) | 0/77, Wilson upper 0.0475 | OK |

### 2.6 Table VI (Study B; source: `scenarios.csv`)

| Config | TP/FP/FN/TN | TSR [Wilson] | FCR [Wilson] | FRR [Wilson] | F1 | Acc | Status |
|---|---|---|---|---|---|---|---|
| No verification | 43/28/3/26 | 43/100 [0.337,0.528] | 28/71 [0.289,0.511] | 3/46 [0.0224,0.1750] | .7350 | .690 | OK |
| Basic | 42/24/4/30 | 42/100 [0.328,0.518] | 24/66 [0.258,0.484] | 4/46 [0.034,0.203] | .7500 | .720 | OK |
| Φ | 37/19/10/34 | 37/100 [0.282,0.468] | 19/56 [0.229,0.470] | 10/47 [0.120,0.349] | .7184 | .710 | OK |
| Enhanced | 39/8/12/41 | 39/100 [0.300,0.488] | 8/47 [0.089,0.301] | 12/51 [0.140,0.368] | .7959 | .800 | OK |

### 2.7 Table VII (paired tests against Φ)

| Config | Reported b/c, p, ΔFC [CI], h, MC FCR | Recomputed | Status |
|---|---|---|---|
| No verification | 9/0, 0.004, +0.09 [+0.04,+0.15], −0.12, 0.36 [0.25,0.48] | 9/0, 0.00391, +0.09 [+0.04,+0.15], −0.1226, 0.3635 [0.250,0.478] | OK |
| Basic | 5/0, 0.062, +0.05 [+0.01,+0.10], −0.10, 0.33 [0.22,0.44] | 5/0, 0.0625, +0.05 [+0.01,+0.10], −0.1023, 0.3285 [0.217,0.440] | OK |
| Φ | MC 0.25 [0.15,0.37] | 0.2533 [0.150,0.365] | OK |
| Enhanced | 0/11, 0.001, −0.11 [−0.18,−0.05], −0.04, 0.14 [0.05,0.24] | 0/11, 0.00098, −0.11 [−0.18,−0.05], −0.0412, 0.1380 [0.051,0.241] | OK |

Bootstrap reproducibility:

- The repository's scenario-level percentile bootstrap (seed 7, 10,000 reps) gives exactly the same limits as the paper.
- My independent numpy bootstrap (20,000 reps, a different seed) gives the same limits to 2 decimals.

Pairing for the FC test is valid: same scenarios, and the FP indicator depends on the shared pre-verification label (see A1).

### 2.8 Section IX-A narrative

| Claim | Recomputed | Status |
|---|---|---|
| 19 vs 28 FC; 9 only without, 0 only with; p=0.004 | OK | OK (A4) |
| Basic removes 4 | 28→24 | OK (A6: 1 of the 4 comes only from estimator smoothing) |
| FRR 0.21 vs 0.07 | 0.2128 / 0.0652 | OK |
| TSR 0.37 vs 0.43 | OK | OK |
| Accuracy not significantly different (p=0.80) | discordant 9/7, p=0.8036 | Number OK; test questionable (A1) |
| Enhanced accuracy 0.80 vs 0.71, higher FRR (0.235 vs 0.213) | OK | OK |
| MC mean FCR 0.36 / 0.25 / 0.14 | 0.3635 / 0.2533 / 0.1380 | OK |
| Paired FC reduction 0.11 (0.05–0.17); p<0.05 in 96% | 0.1068 (0.05–0.17); 0.961 | OK (`mc_paired_fc_diff.json` reproduced exactly) |
| Table III: "19 vs 28 FC; synthetic p=.004", "18 vs 19 of 44", "87 vs 69 of 93", "+0.2%" | all OK | OK |
| Abstract: "19 against 28 per 100" | OK | OK |

### 2.9 Table VIII (Study C) and Section IX-B

| Row | Reported TSR / FCR / FRR / F1 / Evid / MC TSR / MC FCR | Recomputed | Status |
|---|---|---|---|
| Full | 37/100 [.28,.47] / .339 / .213 / .718 / 0.89 / 0.44 / 0.25 | identical (MC 0.4447 / 0.2533) | OK |
| − evid. collection | same as Full, Evid 0.00 | OK | OK |
| − Φ | 43/100 [.34,.53] / .394 / .065 / .735 / 0.89 / 0.45 / 0.36 | MC 0.4512 / 0.3635 | OK |
| − memory, RAG | 38/100 [.29,.48] / .345 / .191 / .724 / 0.89 / 0.44 / 0.26 | Wilson [0.291,0.478]; MC 0.4424 / 0.2553 | OK |
| − recovery | 30/100 [.22,.40] / .348 / .250 / .698 / 0.90 / 0.38 / 0.25 | Wilson [0.219,0.396]; MC 0.3765 / 0.2530 | OK |

Section IX-B narrative:

- "0% instead of 89%": OK.
- "TSR 0.37→0.30, across replications 0.44→0.38": OK.
- "Removing memory changes two outcomes": 2 scenarios differ. OK.
- "nothing on average": MC TSR 0.442 vs 0.445. OK.

### 2.10 Table IX (Study D) and Section IX-C

| Item | Reported | Recomputed | Status |
|---|---|---|---|
| Precision@3 / Recall@3 / MRR over 9 queries | 0.52 / 1.00 / 0.93 | 0.5186 / 1.000 / 0.9259 | OK |
| Top-1 irrelevant or failed | 3/10 | 3/10 (desk_contact failed, shop_price RR 0.333, unrelated) | OK |
| Corpus size, Table IX header and Section VII-C(b) | **23** records | **22** (14 group records + 8 distractors in `measure_inputs.py`) | **MISMATCH (M1)** |
| Memory disabled | 19/44 [0.30,0.58], .387 | 19/44 [0.297,0.578], 12/31 = .3871 | OK |
| Memory enabled | 18/44 [0.28,0.56], .379, 0.64 | 18/44 [0.277,0.556], 11/29 = .3793, 28/44 = .636 | OK |
| Relevance-filtered | 19/44 [0.30,0.58], .367, 0.86 | 11/30 = .3667, 38/44 = .864 | OK |
| "18 against 19 of 44" | – | discordant on/off = 0/1 | OK |

### 2.11 Table X (Study E) and Section IX-D

| Item | Reported | Recomputed | Status |
|---|---|---|---|
| 120 scenarios, 20 per mode; 27 permanent; none a missing confirmation | – | 27 (timeout 6, invalid 6, unexpected 6, missing element 5, navigation 4); 0 missing confirmation | OK |
| No recovery | 111/120 [.86,.96]; 0/93 [.00,.04]; FC 9; 0; 0.0 | identical | OK |
| Retry-based | 111/120; 69/93 [.64,.82]; 9; 162; 10.9 | 69/93 [0.645,0.820]; 162; 10.890 | OK |
| Evidence-guided | 118/120 [.94,1.00]; 87/93 [.87,.97]; 2; 162; 10.0 | [0.941,0.995]; [0.866,0.970]; 9.973 | OK |
| By mode | nav 14/16;16, timeout 12/14;13, missing el. 13/15;14, invalid 13/14;14, unexpected 13/14;13, missing conf. 4/20;17 | identical | OK |
| Narrative | 69 of 93, 4 of 20, 9 undetected → FC, 87 recovered, 2 FC, 162 attempts | identical | OK |

Of the 20 missing confirmations, 11 were detected under retry-based recovery and 4 of those 11 were recovered.

### 2.12 Table XI (Study F) and Section IX-E

**ACTUAL block** (`m2_latency.json`, 30 samples each)

| Operation | Median (reported / recomputed) | p95 (reported / recomputed) | Status |
|---|---|---|---|
| navigate | 17.1 / 17.14 | 24.9 / 24.94 | OK |
| click + load | 65.2 / 65.215 | 106.2 / 106.22 | OK |
| fill | 12.5 / 12.515 | 17.4 / 17.43 | OK |
| DOM extraction | 76.4 / 76.385 | 105.6 / 105.63 | OK |
| screenshot | 61.3 / 61.26 | 93.6 / 93.57 | OK |
| Φ on a site page | 5.2 / 5.165 | 6.9 / 6.93 | OK |
| Φ on gate states | 26.8 / 26.84 | 30.3 / 30.29–30.31 | OK |

The p95 values are nearest-rank (index round(0.95·29) = 28, the second-largest sample). Linear interpolation would give navigate 23.3, click 94.0, fill 16.6, DOM 101.0, screenshot 92.5 and Φ 6.9. The method should be stated (A9).

**SYNTHETIC block**

| Config | Median / p95 / verification share | Status |
|---|---|---|
| No verification | 17.006 / 34.127 / 0.0% | OK |
| Φ | 17.042 / 34.156 / 0.19% | OK |
| LLM self-verification | 21.703 / 38.691 / 19.64% | OK |
| Φ + model check | 21.729 / 38.717 / 19.76% | OK |

Caption and Section IX-E:

| Claim | Recomputed | Status |
|---|---|---|
| Inference is 84% under Φ | 0.836 | OK |
| Screenshots 2.5% | 0.0246 | OK |
| Φ adds 0.035 s (0.2%) | 0.0347 s; +0.19% of mean | OK |
| Evidence 0.46 s | 0.458 | OK |
| Self-check 4.5 s | 4.55 | OK |
| +24% mean | +24.4% vs none; +24.2% vs Φ | OK |
| +28% median | +27.6% | OK |
| 1.5 s → 8.9 s; 6 s → 32.6 s | 8.943 / 32.649 | OK |

### 2.13 Table XII, Fig. 3 and Section IX-F (Study H)

Re-running with 300 replications on the same seeds reproduces every value.

| Row | FCR / FRR / TSR (recomputed) | Status |
|---|---|---|
| Detection ×0.5 | 0.3087 / 0.1637 / 0.4324 | OK |
| Detection ×1.0 | 0.2520 / 0.1593 / 0.4468 | OK (but see M3) |
| Detection ×1.5 | 0.1890 / 0.1549 / 0.4619 | OK |
| Missing evidence 0% | 0.2348 / 0.1305 / 0.4850 | OK |
| Missing evidence 8% | same as ×1.0 | OK |
| Missing evidence 20% | 0.2860 / 0.2101 / 0.3861 | OK |
| Action failure 0.1 | 0.2508 / 0.1578 / 0.4826 | OK |
| Action failure 0.25 | same as ×1.0 | OK |
| Action failure 0.4 | 0.2548 / 0.1595 / 0.4116 | OK |

Fig. 3: all 40 plotted coordinates match, to 3 decimals, the FCR and FRR of the four rules at π ∈ {0.3, 0.5, 0.65, 0.8, 0.95}. **OK**.

Section IX-F narrative:

- "π=0.3: 0.14 vs 0.21; π=0.95: 0.32 vs 0.45; FRR ≈0.16 vs 0.08": OK.
- "Halving detection raises FCR to 0.31": number OK. The phrase "close to no verification" is **misleading (W1)**: no verification is 0.358 at π=0.65 (Table VII: 0.36), and 0.31 lies about halfway between Φ (0.25) and no verification.

### 2.14 Table XVI (parameters) and Section VII-C(b)

The derived rates were recomputed from `m1_gate_rules.csv`. That file agrees with `verification_gate_cases.csv` on all 92 states (Φ decisions and oracle labels).

| Rate | (k, n) → (k+0.5)/(n+1) | Status |
|---|---|---|
| Φ: navigation | (2,6) → 0.357 | OK |
| Φ: search | (2,4) → 0.50 | OK |
| Φ: form | (3,6) → 0.50 | OK |
| Φ: data entry | (1,3) → 0.375 | Printed 0.38 |
| Φ: extraction | (0,6) → 0.071 | OK |
| Φ: multi-step | (2,3) → 0.625 | Printed 0.62 (M4) |
| Basic: navigation | (2,6) → 0.357 | OK |
| Basic: search | (0,4) → 0.10 | OK |
| Basic: form | (0,6) → 0.071 | OK |
| Basic: data entry | (0,3) → 0.125 | Printed 0.12 |
| Basic: extraction | (0,6) → 0.071 | OK |
| Basic: multi-step | (0,3) → 0.125 | Printed 0.12 |
| False rejection Φ / basic | (2,27) → 0.089; (0,27) → 0.018 | OK |
| Missing-confirmation detection | 0.625 | Printed 0.62 |
| Misleading retrieval | 3/10 = 0.30 | OK |

The text says "22 and 5 unsatisfied states, without bot-check": the detection rates use 22 unsatisfied states once bot-check is excluded (27 − 5 captcha). OK. "multi-step rests on 3 states": OK. Section XII-d "54 held-out states, 27/27": OK.

The other values in Table XVI match `params.json`: outcome mix, 0.92/0.65, 0.8, 0.5/0.05, 0.35/0.3, 0.25/0.55, 0.4/0.08/0.1, 0.1, the per-attempt ranges 0.10–0.45 and 0.05–0.35, and 3.0 s/0.5.

Appendix C says "Table XVI lists every parameter". This is **false (M2)**. See the mismatch list.

### 2.15 Other numbers checked

- **Appendix B task set** (`tasks.json`): the dev/test splits are extraction 2/8, form 2/7, multi-step 1/5, navigation 2/2, search 1/2, text 1/2 and unsatisfiable 1/4. Tiers are 3/6, 4/11, 3/12 and 0/1. All **OK**.
- **Table XIII and Section XI** "17-pattern sanitizer": `INJECTION_PATTERNS` has 17 entries. **OK**.
- **Table II** "92 states", "70 episodes", "114 trajectories", "6 failure modes", "10 queries": **OK**.

## 3. Mismatches and suggested corrections

**M1 – memory corpus size (Section VII-C(b), "23-record synthetic memory corpus"; Table IX header, "23 synthetic records").**
- `benchmarks/simulation/measure_inputs.py` stores 14 records from `MEMORY_GROUPS`: 2+2+2+1+2+1+1+2+1+0.
- It also stores 8 `DISTRACTORS`, for **22** records in all.
- Correction: "22-record" in both places, unless another record is stored by code I did not find.

**M2 – Appendix C claims that Table XVI lists every simulation parameter.** It omits the following parameters, all of which affect the results:
- category mix (0.15/0.15/0.20/0.15/0.20/0.15);
- P(goal met | outcome class) (1/0/0/0.5/0.5/0.3/0.5);
- ambiguous-detection factor 0.5;
- enhanced contradiction-reject 0.7;
- permanent-failure share 0.25 (this one is mentioned only in the Table X caption);
- evidence-guided per-attempt success rates 0.35–0.55;
- steps per category (2/3/5/3/3/6).

Correction: add these rows, or change the text to "the main parameters".

**M3 – the same quantity appears with two values (minor).**
- The full Φ configuration has TSR 0.45 in Table XII (row ×1.0: 0.4468, 300 replications, seeds 202·7919+r).
- It has MC TSR 0.44 in Table VIII (0.4447, 1000 replications, seeds 202·1000+r).
- Correction: note in the Table XII caption that it uses a separate 300-replication stream, or use one stream for both tables.

**M4 – rounding and format (minor).**
- Table IV, Held-out 1+2: p = 0.00098 is printed ".001" while the design rows use "<.001". Use "<.001".
- Table V: p = 0.125 → ".12" and 0.625 → ".62". Table XVI: 0.625 → 0.62 and 0.125 → 0.12, but 0.375 → 0.38.
- These ties are rounded half-to-even (Python formatting), so readers see an inconsistent convention. Use half-up rounding (.13, .63, 0.63, 0.13) or print 3 decimals.

**W1 – wording (Section IX-F).** "Halving the measured detection rate of Φ raises FCR to 0.31, close to no verification" should become "…to 0.31, about halfway between Φ (0.25) and no verification (0.36)".

## 4. Statistically inappropriate or questionable analyses

### A1. "Overall accuracy is not significantly different (p = 0.80)" (Section IX-A, Φ vs no verification)

**The paired 2×2 behind it** (100 scenarios; "correct" means `<cfg>_reported == <cfg>_y`):

| | No-verif correct | No-verif wrong | Total |
|---|---|---|---|
| Φ correct | 62 | **9** | 71 |
| Φ wrong | **7** | 22 | 29 |
| Total | 69 | 31 | 100 |

The discordant cells are b = 9 and c = 7, giving exact McNemar p = 0.8036. The accuracy difference is +0.02, with scenario-bootstrap 95% CI [−0.06, +0.10].

**The pairing of units is valid but the outcome definition is not common.**
- The scenarios share their random numbers (common random numbers), so the units are paired.
- The label y is evaluated per configuration after the verifier has acted. In `simulate.episode()`, a premature claim that Φ rejects goes to a "continuation" branch with `reported = y = done`, where done ~ Bernoulli(0.35).
- So every rejected premature claim is counted as "correct" **by construction**, whether or not the task was then completed.
- All 9 Φ-only-correct scenarios are rejected premature claims. 8 of them end as TN (the task failed and was not reported). 1 ends as TP, because its label changed from y = 0 to y = 1 (scenario S202-033).
- The 7 no-verif-only-correct scenarios are Φ false rejections. None of them was re-claimed (re-claim probability 0.3).
- The test therefore compares accuracy against a different target in each arm. Part of what it measures is the assumed continuation process, not decision reliability.
- Across configurations y differs in:
  - 1 of 100 scenarios for Φ vs no verification;
  - 4 for Φ vs enhanced;
  - 7 for Φ vs no-recovery;
  - 2 for Φ vs no-memory.

**Is the conclusion robust?** For this pair, yes, by coincidence.
- Decision level, at the first completion claim, with the common pre-verification label `y_claim`:
  - 71 claims: 43 true, 28 premature.
  - Φ is right on 45 and no verification on 43. Discordant 9/7, p = 0.80.
- Final report against the common pre-verification truth over all 100 scenarios: 70 vs 69, discordant 8/7, p = 1.0.

**Why it is still inappropriate:**
1. The outcome is not defined identically across the paired arms.
2. Accuracy weights FC and FR equally and depends on the simulated prevalence (46–51% true). H2 ("decision reliability") is better addressed by the decision-level FC/FR pair at a common label.
3. "Not significant" with 16 discordant pairs is not evidence of no difference. The CI [−0.06, +0.10] should be reported instead of the p-value.
4. As for every synthetic p-value, N = 100 is chosen by the authors, so significance is controllable (see A4).

**Recommendation:** report the decision-level comparison, with a label common to both arms, as a 2×2 plus CI. Do not call the policy-level accuracy test a paired test of decision reliability.

### A2. Gate study, McNemar "against the dispatch-only rule" (Table IV; abstract p = 0.004)

- Pairing is valid (same states).
- The test is degenerate. The dispatch-only rule accepts every state, so c = 0 by construction and p = 2^(1−W): a sign test of "W > 0" that ignores false rejections. Any gate that withholds 9 states gets p = 0.004, however many satisfied states it rejects.
- It is also inconsistent with Table V, whose p uses correct decisions on all states.
- With the correct-decision McNemar on all states, the p-values become:

| Set | Reported p | Correct-decision p |
|---|---|---|
| Design after | <.001 | 2.1e-5 |
| Design before | <.001 | 0.0075 |
| HO1 after | .50 | 1.0 |
| HO2 | .004 | **0.021** |
| HO1+2 | .001 | **0.022** |

- Recommendation: state precisely in the caption and text that p tests the withheld count on unsatisfied states only. Better, report the exact binomial or Wilson CI of W/n− (already given) together with the correct-decision McNemar.

### A3. P-values on the design set

The design-set results (p < 0.001 against dispatch-only; "corrects 7 … p = 0.016" against the earlier gate) come from the same states the fixes were designed on. The paper acknowledges the optimism, but a significance test of a post-hoc fix on its own training states is circular and has no inferential meaning. Report the counts only.

### A4. Synthetic p-values (H1 p = 0.004, Table VII, "p < 0.05 in 96% of the sets")

- In `episode()`, Φ can never create a false completion that no verification lacks, and enhanced validation can never create one that Φ lacks. So c = 0 (or b = 0) is structural.
- The p-value is therefore a function of the assumed π (0.65), the smoothed detection rates and the author-chosen N = 100.
- "96% of sets" is a power figure under these assumptions, not evidence.
- The paper says this for H4 and enhanced H2 (Section VI; Section VII-C(d)), but the same applies to H1. The p-values should be presented as illustrative only, or replaced by the Monte Carlo distribution of ΔFC.

### A5. Wilson intervals on synthetic counts (Tables VI, VIII, IX, X)

- These describe binomial sampling from a population that does not exist. The only variability is the generator's, which the Monte Carlo percentiles already show.
- The Monte Carlo itself treats the derived inputs as known. Examples:
  - multi-step detection 0.625 rests on 3 states;
  - extraction rests on 0/6;
  - the false-rejection rate rests on 2/27.
- So the Monte Carlo intervals understate the uncertainty.
- Recommendation: drop the Wilson intervals for synthetic rows, and propagate input uncertainty (for example, draw each derived rate from Beta(k+0.5, n−k+0.5) per replication).

### A6. The (k+0.5)/(n+1) estimator gives nonzero detection where none was measured

- Basic detection withheld 0 of the held-out search (0/4), form (0/6), data-entry (0/3), extraction (0/6) and multi-step (0/3) states, yet it is simulated with rates of 0.07–0.125.
- Φ extraction (0/6) is simulated at 0.07.
- In the reported set, 1 of the 4 false completions that "basic success detection removes" (Section IX-A) is a search scenario, so it comes only from smoothing. The basic-vs-Φ contrast (b/c = 5/0) is correspondingly affected.
- Recommendation: state this, or use k/n with a sensitivity check.

### A7. Cohen's h on paired proportions (Table VII)

h treats the two TSRs as independent and ignores the pairing. It is acceptable as a descriptive effect size but should not be read alongside the paired tests. The ΔTSR with a paired bootstrap CI would be more informative. Minor.

### A8. Independence assumption and prevalence in the gate study

- Wilson and Clopper–Pearson intervals assume exchangeable, independent states. The 92 states were written by one author from templates, with near-duplicates within categories, and pooled HO1+HO2 sets built under different protocols.
- FC/R (FCR) depends on the constructed prevalence: 23/38, 5/12 and 22/42 unsatisfied. It is not an estimate of an FCR in use. Only W/n− and FR/n+ are prevalence-free, so FCR in Table IV should be flagged as prevalence-dependent.

### A9. Latency percentiles

- The p90, p95 and maximum over the 83 gate decisions are percentiles of per-state medians, each the median of 20 repetitions. They understate the tail of single-decision latency.
- The p95 values in Table XI with n = 30 are nearest-rank, equal to the second-largest sample. For example, click is 106.2 nearest-rank and 94.0 by linear interpolation.
- Recommendation: state both methods, or report the maximum.

### A10. Memory study (Study D, H3)

- "Not supported (18 vs 19 of 44)" has no test (discordant 0/1). The outcome follows directly from the assumed gain and loss (0.08/0.10) and the derived misleading rate.
- "Contextual accuracy" 0.64 → 0.86 is just the share of u_mem draws above the assumed threshold (expected 0.70 vs 0.90). It carries no information about the system.
- Precision@3 is bounded by n_relevant/3 (at most 0.33 for the 4 queries with one relevant record), so 0.52 mostly reflects how the corpus was built.
- Relevance labels are by group and loose. For example, records about "Halden Bridge" and "glacial lakes" count as relevant to the query "Search Findr for the observatory", which inflates recall@3 = 1.00.

**Related note on H2 and the ablation:** "no single removal is significant (p ≥ 0.06)" with 23 unsatisfied states, and H2 "not supported" (p = 0.80), both treat non-significance in small samples as a finding. Report effect sizes with CIs instead.

## 5. Pairing validity of every paired test

| Test | Units | Outcome definition | Valid? |
|---|---|---|---|
| Table IV, gate vs dispatch-only | same states | same oracle label | Valid pairing; degenerate test (A2) |
| Table IV and VIII-A, gate vs earlier gate (p = 0.016) | same design states, labels unchanged | same | Valid pairing; circular (A3) |
| Table V, ablation vs full gate (correct decisions) | same states | same | Valid |
| Table VII, FC indicator vs Φ (none, basic, enhanced) | same scenarios (common random numbers) | FP = reported ∧ ¬y. For an accepted claim y equals the shared pre-verification label, so an FP is defined on a common label | Valid pairing; structural c = 0 (A4) |
| Section IX-A accuracy, Φ vs none (p = 0.80) | same scenarios | correctness against a **per-configuration** y (differs in 1/100 scenarios; rejected claims correct by construction) | **Not a like-for-like outcome** (A1); conclusion unchanged with a common label (p = 0.80 or 1.0) |
| `results.json` accuracy vs enhanced (p = 0.022, not in paper), vs no-recovery | same scenarios | y differs in 4 and 7 scenarios | Same issue as A1; not reported in the paper |
| Table VII ΔFC bootstrap | scenario-level resampling of paired differences | common FP definition | Valid; reproducible exactly |
| MC "p < 0.05 in 96%" | paired within each regenerated set | same as Table VII | Valid as a power figure under the assumptions (A4) |

## 6. Note on concurrent edits

During this audit (about 01:20 UTC), someone else modified files in the working tree: `paper/sections/{00,01,07,09,12}*.tex`, `paper/tables/{status,threats}.tex` and `artifacts/results/e2e_smoke_stub/egress_summary.json`. That file gained `connections_by_host_port` {127.0.0.1:11435: 555} and `python_processes`: 8. None of these changes came from this audit, whose scripts only read files and wrote to the scratchpad.

This audit checks `paper/main.pdf` as it was built when the audit started. The edits change wording in the egress and privacy passages, not the numbers checked here (70 episodes, 555 connections, still all to loopback).
