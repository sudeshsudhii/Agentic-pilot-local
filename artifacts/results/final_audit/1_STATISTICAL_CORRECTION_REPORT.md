# Statistical correction report

Paper: *Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation*.

Branch `ccr-4b8200f0-5i3k5m`. This report covers audit items A, B and C and the corrections made in response to the statistics and methodology audits (`audit_stats.md`, `audit_method.md` in this folder). Every changed number, with its source and calculation, is listed in `changed_numbers_ledger.csv`.

**Evidence classes:**
- **ACTUAL**: measured on the implementation.
- **DERIVED**: computed from ACTUAL measurements.
- **SYNTHETIC**: produced by the simulation.
- **PROPOSED**: the assumed behaviour of a component that is not implemented.

---

## A. The p = 0.80 accuracy comparison (Φ vs. no verification)

### What was reported (v1)

- Claim: "Φ … accuracy 0.63 … and accepting every claim … 0.61 … exact McNemar p = 0.80."
- In an earlier draft, this was a policy-level indicator, `correct = (reported == y)`, computed over 100 scenarios.

### Paired 2×2 behind the withdrawn test

Source: `out/heldout_v1/results.json`, `paired_tests_vs_evidence_gated.no_verification`.

| | No-verif correct | No-verif wrong |
|---|---|---|
| **Φ correct** | 62 | **9** |
| **Φ wrong** | **7** | 22 |

- Discordant pairs: b = 9, c = 7.
- Exact two-sided McNemar: p = 2 · P(X ≤ 7 | X ~ Bin(16, 0.5)) = 0.8036.

### Why it is wrong

- The label `y` is evaluated **per configuration**, after the verifier has acted.
- A premature claim that Φ rejects leads to a continuation branch. There, `reported = y` by construction.
- So the test compares each arm against a different ground truth.

### Correction

The comparison is now made at the **decision level**:
- **Units:** the scenarios in which the planner claims completion.
- **Ground truth:** the true state at the moment of the claim (`y_claim`). This is identical across the four verifiers; the code asserts it.
- **Outcome:** whether the verifier's first decision is correct.

**v1 (same model, decision level).** Source: `out/heldout_v1/decision_analysis.json`.
- 71 claims, 43 of them true.
- Φ was correct on 45 claims and no verification on 43.
- Discordant pairs 9/7, p = 0.804. The number is unchanged, but the test is now well defined.

**v2 (reported model).** Source: `out/heldout_v2/results.json`.
- 74 claims, 46 of them true.

| Verifier | TP/FP/FN/TN | Accuracy | Wilson 95% |
|---|---|---|---|
| No verification | 46/28/0/0 | 46/74 = 0.62 | 0.51–0.72 |
| Basic detection | 43/24/3/4 | 47/74 = 0.64 | 0.52–0.74 |
| Φ | 43/19/3/9 | 52/74 = 0.70 | 0.59–0.79 |
| Enhanced (proposed) | 41/8/5/20 | 61/74 = 0.82 | 0.72–0.89 |

**Paired tests against Φ**, exact two-sided McNemar on first-decision correctness:

| Comparison | b (only other correct) | c (only Φ correct) | p |
|---|---|---|---|
| None vs Φ | 3 | 9 | 0.146 = 2·Σ_{i≤3} C(12,i)/2¹² |
| Basic vs Φ | 0 | 5 | 0.0625 |
| Enhanced vs Φ | 11 | 2 | 0.0225 (by assumption) |

- **Monte Carlo** over 1,000 regenerated sets, with derived rates drawn from Beta posteriors:
  - mean decision accuracy is 0.74 for Φ and 0.64 for no verification;
  - Φ is better at p < 0.05 in 42.1% of sets.
- **Conclusion in the paper:** "the difference has the hypothesized direction but is not significant in this set … H2 is not supported for Φ at this sample size."

## B. Policy-level task success vs. decision-level accuracy

- **Methodology §VII-C, "Metrics":** defines the two levels and states that the final ground truth may differ between configurations.
- **§IX-A:** repeats this before any number.
- **Table VI:** shows both levels side by side, with policy TP/FP/FN/TN, TSR, FCR and FRR next to decision TP/FP/FN/TN and accuracy.
- **Table VII:** gives paired tests separately for each indicator:
  - episode false completion (100 scenarios);
  - decision correctness (74 claims);
  - task success (100 scenarios).

**Policy-level success (v2), Φ vs none:**
- 44 vs 46 successes.
- Discordant pairs 1/3, p = 0.625.
- In v1 this was 37 vs 43 (1/7, p = 0.070). The difference is due to the model corrections in Section D below.

## C. Synthetic p-values and intervals are conditional

The conditional wording now appears in each of these places:
- the boxed notice at the top of §IX;
- every simulation table caption ("Synthetic p-values and intervals are conditional on the simulation assumptions; they are not empirical tests of the agent");
- the Metrics paragraph of §VII-C;
- the Table III caption and the "(cond.)" cells;
- Limitations ("Simulation validity").

**Structural results are now stated as such:**
- **H1:** Φ can only withhold a claim, so no scenario ends in a false completion with Φ alone. One discordant cell is always 0, and only the size of the reduction is informative. The Table III cell now reads "lower by construction".
- **H4 and enhanced H2:** these follow directly from the assumed rates of unimplemented components and are labelled "by assumption".
- **H3:** with 44 repeated workflows, the study cannot detect the assumed effect. It is labelled "underpowered", not evidence against the hypothesis.
- **Sample size:** N = 100 is a design choice, so synthetic significance partly reflects that choice. This is stated in the Limitations.

## D. Simulation model corrected (v1 → v2, post hoc)

The methodology audit (`audit_method.md`, H-1 to H-4) found four places where the frozen v1 model contradicted the code. The fixes are in `benchmarks/simulation/simulate_v2.py`:

| # | v1 behaviour | Code behaviour | v2 |
|---|---|---|---|
| C1 | Φ false-rejection rate 0.089, from 2/27 satisfied states. Both rejections were bot-check pages, a category the scenarios do not contain. | — | 0/24 satisfied states of the mapped categories gives 0.02 for both Φ and basic. |
| C2 | Basic detector ignored unreadable pages. | It shares the error check E, so it fails closed. | Fails closed. |
| C3 | Continuation after a rejection was accepted without re-checking. A re-claim after a false rejection was accepted with probability 0.3. | `verify_node` checks every claim. | A continuation is verified again. A false rejection of an unchanged page is repeated, because the rule is deterministic. |
| C4 | Recovery applied to every action failure with an assumed P = 0.55. | Action errors get 3 inline retries before the engine. Navigation failures and need_help go to the engine directly. A missing confirmation raises no error. | Entry paths from the code: 3 inline retries for action errors (including need_help), 3 executor retries for a failed initial navigation, then the engine. P(recover) = 0.66 / 0.49, taken from Study E. "No recovery" keeps the retries before the engine. (The first v2 draft sent need_help and navigation failures straight to the engine; the independent final review found this and it was corrected.) |
| C5 | Monte Carlo treated derived rates as known. | — | Rates drawn from Beta(k + 0.5, n − k + 0.5) in each replication. |
| C6 | Latency omitted re-planning after a rejection. | — | Re-planning, 3 screenshots per step plus 2 at completion, and recovery attempts are included. |
| C7 | The text claimed the continuation rate was swept, but it was not. | — | The continuation rate is swept. |

**Status and disclosure:**
- v2 is **not pre-registered**. It was written after the v1 results and the audit were known. This is disclosed in §VII-C ("Corrected model (v2, post hoc)") and in the Limitations.
- v2 reuses v1's generator, seeds (202 held-out, 101 development) and assumed values.
- v1 outputs are archived in `benchmarks/simulation/out/heldout_v1/`.
- `simulate.py` (v1) gained three additive output fields (`claimed`, `y_claim`, `accepted`). Its other outputs were verified byte-identical with `cmp`. This is disclosed.

## E. Gate study: degenerate McNemar test (ACTUAL data)

### The problem

- The dispatch-only rule accepts every state, so the old test (`p_fc_vs_dispatch`) had c = 0 by construction.
- Its p-value was 2^(1−W), which ignores false rejections.

### The correction

- The test is now an exact McNemar on paired decision correctness:
  - b = W, the unsatisfied states only the gate decides correctly;
  - c = FR, the satisfied states only dispatch decides correctly.
- It is computed by `artifacts/experiments/gate_stats.py` (new columns `gate_only_correct`, `dispatch_only_correct`, `p_correct_vs_dispatch`, `pre_*` for the gate before the fixes, and a pooled `held_out_1+2` split).
- All 84 previous rows of `gate_stats.csv` are byte-for-byte unchanged in value.

| Set | W / FR | Old p | Corrected p | In paper |
|---|---|---|---|---|
| Design, after fixes | 20 / 1 | 1.9e-6 | 2.1e-5 | "--" (circular, not tested) |
| Design, before fixes | 15 / 3 | 6.1e-5 | 0.0075 | "--" |
| Held-out 1, after | 2 / 1 | 0.50 | 1.0 | 1.0 |
| Held-out 1, before | 1 / 1 | 1.0 | 1.0 | 1.0 |
| **Held-out 2, after** | 9 / 1 | 0.0039 | **0.0215** | .021 (abstract, Table IV, §VIII-A) |
| Held-out 1+2, after | 11 / 2 | 0.00098 | **0.0225** | .022 |

**Related corrections:**
- **Design-set tests** (gate vs dispatch, and gate vs earlier gate with p = 0.016) were removed. The fixes were designed on those states, so testing them there is circular (audit A3). Counts are reported instead.
- **"Low false-rejection rate"** is now "1 of 20 … upper 95% bound 0.24".
- **FC/R in Table IV** is flagged as prevalence-dependent.
- **Latency percentiles:**
  - §VIII-C states that the 83-decision percentiles are taken over per-state medians.
  - The Table XI caption states the order-statistic rule used for p95.
- **Ablation non-significance:** "no single removal reaches p < 0.05 … which with so few states is not evidence that a conjunct is unnecessary."

## F. Other statistical points

| Audit item | Action |
|---|---|
| A5: Wilson intervals on synthetic counts | Kept for descriptive scale, with the "conditional" note. Monte Carlo intervals now include rate uncertainty (C5). |
| A6: (k+0.5)/(n+1) gives a nonzero rate where none was observed | Stated in §VII-C (rates 0.07–0.13 for basic detection in five categories and for Φ on extraction). |
| A7: Cohen's h | No longer printed. |
| A10: memory | "Contextual accuracy" (true by construction) was removed. The loose relevance labels and the precision bound are stated. H3 is called underpowered. |
| M3: separate random streams | Stated in the Table XII caption. |
| M4: half-even rounding | The parameter table uses half-up rounding. p-values are printed to 3 significant figures (0.0625, not 0.062). |

## What was not changed

These were not changed:
- ACTUAL measurements: the gate decisions, latency, recovery classification, retrieval ranks and egress log;
- the v1 data;
- the scenario set.

The model corrections change only how synthetic outcomes are generated from the same scenarios.
