# Methodology audit: simulation study (Studies A–H) and hypotheses H1–H5

Audited state: HEAD `1615ac5` ("Audit fixes A-D, F, I ..."), which landed while this audit was running.
The commit already splits decision level from policy level (Table B, H2, `decision_analysis.py`) and
relabels the evidence ablation row. Findings below refer to the current files. Items fixed by 1615ac5
are listed at the end. All numbers were recomputed with the repository code. Scratch scripts are
`decision_acc.py`, `rerun.py` and `corrected.py` in the scratchpad directory. No repository file was modified.

---

## 1. Scenario pairing and where the ground truth y differs

**What is shared.** `generate()` draws 13 uniforms per scenario once (`u_claim`, `u_detect`, `u_fr`, `u_cont`,
`u_reclaim`, `u_actfail`, `u_recov`, `u_mem`, `u_mem_eff`, …). Every configuration reuses them (common random
numbers), so comparisons are paired by scenario. Study F uses per-scenario seeded streams. Study E uses its own
scenario set, shared across its three recovery modes.

**Where the final y differs for the same scenario** (`episode()`, simulate.py:102–152):

| Mechanism | Code | Held-out effect (scenarios whose final y differs from no-verification) |
|---|---|---|
| Continuation after a correct rejection (y 0→1 with p=.35) | l.146–148 | Φ 1, enhanced 5 |
| Memory on/off/filtered flips y on repeated workflows | l.109–116 | no-memory 3 (2 up, 1 down), filtered 2 |
| Action failure, no recovery → y forced to 0 | l.106–107 | no-recovery 8 (7 down) |
| False rejection: y stays 1, reported may be 0 | l.150 | changes `reported`, not y |

**Disclosure.** 06_methodology says "memory and continuation after a rejection change the final state". It does not
mention action failure and recovery. That omission matters most for Study C: the "-- recovery" row compares against a
different truth in 8 of 100 scenarios.

**Fix.** Add "and unrecovered action failures" to the sentence. In the Study C caption, say that the FCR, FRR and F1 of
the memory and recovery rows are computed against configuration-specific truths. Also report the number of scenarios
whose y differs, as in the table above.

---

## 2. Ground-truth definitions: decision level vs policy level

- **Decision level** = the verifier's first accept/withhold decision at the claim, against `y_claim`.
  Now used by: Table `tab:sim-baseline` (last two columns), `tab:sim-tests` "Decision b/c", H2 in `tab:hyp`, and the
  abstract ("45 against 43 of 71 claims"). I recomputed this independently and it is correct
  (Φ 36/19/7/9, accuracy 45/71; no verification 43/71; McNemar 9/7, p=.80).
- **Policy level** = final `reported` against final `y`. Used by: TSR, FCR, FRR, F1 and policy accuracy in Table B;
  "FC b/c" and "Success b/c" in `tab:sim-tests`; MC FCR; all of `tab:sim-ablation`; `tab:sim-memory`; Fig. `fig:sim-sens`
  and `tab:sim-sens`; H1, H3 and H5.

**Remaining mixing (Medium, M-2).**
1. **The policy-level "FRR" is not a false-rejection rate.** FRR = FN/(TP+FN) counts complete tasks that the planner never
   claimed. That is why *no verification* has "FRR" 3/46 = 0.065 although it rejects nothing.
   Eq. (`eq:fcr`) in 03_problem defines FRR as N_FR / |{Φ*=1}|, which is a property of the verifier's decisions.
   06_methodology says "FCR and FRR as in Eq. (fcr)", which is not true of the simulated policy FRR.
2. **H5's claim is measured with the wrong metric.** H5 ("makes decisions more conservative") is a decision-level claim,
   but it is reported with the policy-level FRR ("FRR higher"). The matching decision-level false-rejection rate is
   7/43 for Φ, 1/43 for basic detection and 0/43 for no verification.
3. **The sensitivity results are policy-level but not labelled as such.** Fig. `fig:sim-sens` ("FRR constant at about
   0.16 against 0.08") and `tab:sim-sens` report policy FCR/FRR without saying so.
4. **Policy-level FC under Φ equals decision-level FP by construction** (19 = 19). After a rejection the model cannot
   produce a false completion (see H-3). So "episode-level FC" for gated configurations is not an independent quantity.

**Fix.** Rename the policy metric to "unreported-success rate" (or "policy FRR") and keep "FRR" for the decision level,
as in Eq. (fcr). Report decision-level FRR in Table B, H5 and the sensitivity figure. Label every FCR/FRR in
Fig./Tab. sens and in `tab:sim-ablation` "(policy level)".

---

## 3. Hypothesis alignment; outcomes true by construction

| H | Metric/test in design | Assessment |
|---|---|---|
| H1 | Policy FC, McNemar | **The direction is true by construction (H-2).** |
| H2 | Decision accuracy, McNemar on 71 claims | The metric is now right. **The result depends on an inconsistent derivation (H-1).** The enhanced variant is assumption-driven (disclosed). |
| H3 | TSR and "ctx. accuracy" on 44 repeated workflows | **No power. ctx. accuracy is tautological (M-6).** |
| H4 | Recovered share | Assumption-driven (disclosed). The retry baseline does not match the implementation (M-4). |
| H5 | Time and FRR | **Time omits the rejection-loop cost (M-5). FRR is the policy metric (M-2) and is inflated by H-1 and M-1.** |

### H-1 (High): Φ's false-rejection rate comes only from bot-check states, which are excluded everywhere else
`derive_inputs()` computes detection on the held-out unsatisfied states of the six mapped categories
(captcha is excluded through `detector_category_map`). It computes false rejection on **all** 27 held-out satisfied
states, **including 3 captcha states**. Φ's two held-out false rejections (k=2/27 → 0.089) are both captcha states:
`H7` and `B4` in `inputs/m1_gate_rules.csv`. The basic detector skips the bot check, so it has k=0.

No simulated scenario belongs to a bot-check category. The simulation therefore applies a rejection rate that the
gate never showed on the six task categories it simulates. If the 3 captcha states are excluded, as they are for
detection, then k=0/24 for both rules (rate 0.02 each). Recomputed on the held-out set:

| | published | FR excl. captcha | + symmetric fail-closed (M-1) |
|---|---|---|---|
| Φ decision false rejections | 7/43 | 3/43 | 3/43 |
| Φ decision accuracy | 45/71 | 49/71 | 49/71 |
| Φ vs no verification (b/c, p) | 9/7, .80 | 9/3, .15 | 9/3, .15 |
| basic decision accuracy | 46/71 | 46/71 | 44/71 |
| Φ policy TSR (held-out) / MC policy FRR | 37 / .158 | 41 / .120 | – |

The abstract's "without improving decision accuracy (45 against 43)", H2 "not supported", H5 "FRR higher" and the
policy TSR drop (37 vs 43) all depend materially on this choice. The direction stays the same (p=.15 is still not
significant), but the size of the effect and the ordering of Φ against basic detection change.

**Fix.** Derive false rejection from the same category set as detection, or map captcha explicitly and add a bot-check
scenario category. Re-run, and report both variants in the sensitivity study.

### H-2 (High): H1 (and Φ vs basic, enhanced vs Φ) holds by construction; this is not disclosed
For two configurations with the same memory and recovery settings, y, the claim and `y_claim` are identical.
A gated configuration can only (a) accept, giving the same outcome as no verification, or (b) withhold. Withholding a
false claim ends in TP or TN (l.146–148), never in FP.

So the "other only" FC count against no verification is ≥0 and the "Φ only" count is **always 0**. The same holds for
basic vs no verification and enhanced vs Φ (enhanced = Φ withhold OR extra). The discordance pattern 9/0 and the
"p<.05 in 96% of sets" are therefore a power calculation for (derived detection rate × assumed π). They do not test
whether Φ lowers false completions. 05b discloses "by assumption" only for H4 and enhanced H2.

**Fix.** In 05b/`tab:hyp` and 07b, state that the direction of H1 follows from the model structure (a withheld false
claim cannot become a false completion). Only the magnitude depends on the measured detection rates and the assumed π.
Report the expected FC reduction analytically, Σ π·q_c·P(y=0, c), alongside the McNemar test.

### H-3 (High): the post-rejection policy does not match the implemented loop, and the bias favours Φ
`verify_node` (nodes.py:1484–1491) returns `status=running` on a rejection. The loop re-plans, and **every later claim is
checked by Φ again**; at 15 planner calls the episode fails. The simulation instead assumes:
1. After a correct rejection, the episode finishes correctly with p=.35 and is reported **without a second check**,
   and it is otherwise never reported. A renewed premature claim, which Φ accepts with probability 1−q, cannot occur,
   so policy FC under Φ is a lower bound.
2. After a false rejection, a re-claim (p=.3) is **accepted unconditionally**. But Φ is a deterministic function of
   (page, goal, plan, answer) (manager.py:198–358), so it would reject an unchanged page again. Policy FN is therefore
   understated.
3. The 15-call budget is not modelled.

**Fix.** Model the loop explicitly: after a rejection, each extra attempt (up to the budget) produces a new claim that is
verified again. For a deterministic Φ, re-verification of an unchanged state repeats the decision. Alternatively,
restrict H1/H2/H5 to decision level and present policy-level numbers as an illustration under these extra assumptions.

### H-4 (High): a sensitivity claim is false
14_simparams: "the assumed premature-claim rate (0.65) **and finish-after-rejection rate (0.35) are swept in Study H**".
`simulate.py` sweeps only π, the Φ detection multiplier, the missing-evidence share and the action-failure rate.
`p_continue_success_after_reject` and `p_reclaim_after_false_reject` are never swept, yet they drive the policy-level
TSR, Success b/c and FC results.

**Fix.** Add sweeps of both parameters (e.g. 0, .35, .7 and 0, .3, .6) to `sens`, or delete the claim.

### M-6 (Medium): H3 is an underpowered null result plus a tautology
- **The effect is too small to detect.** Expected net effect per repeated workflow ≈ 0.7·0.08·P(y=0) − 0.3·0.1·P(y=1)
  ≈ +0.013. That is about +0.6 successes in 44 workflows, which cannot be detected. "Not supported" reflects the
  assumed gain and loss (both ASSUMED), not the measured store. The measured misleading rate enters only through 0.3.
- **ctx. accuracy is not a measurement.** "ctx. accuracy" = share with `u_mem ≥ p_mis`, i.e. 1 − (misleading rate)
  sampled. The filtered 0.86 follows from the PROPOSED 0.10. The text ("raises contextual accuracy from 0.64 to 0.86")
  does not say "by assumption", unlike H4.
- **The DV is not what H3 names.** H3 names "contextual consistency", but nothing measures consistency across repeats.

**Fix.** Report H3 as "not testable at n=44 under the assumed effect sizes" and give an MDE or power figure. Mark the
0.86 as by assumption. Rename the DV "non-misleading retrieval share" or define consistency.

---

## 4. Ablation labels (`tab:sim-ablation`) vs switches in the code

| Row | Simulation | Implementation | Verdict |
|---|---|---|---|
| -- stored evidence§ | `evidence=False` changes only the `evidence` output field. `episode()` never reads it in the decision path, so decisions are identical (verified on all 100 scenarios). | `enable_evidence` (config.py:37) gates only `ExecutionRecord` JSON in `execute_action_node` (nodes.py:1251–1297). These are still saved unconditionally: before/after/dom_observation/final_completion/completion_proof screenshots, DOM snapshots (l.968, 1007), and **every Φ result via `save_verification`** (l.1247, 1481). | Not realisable by any switch (the caption now says so). But the text "it removes the audit trail" is wrong for the code: the Φ audit trail remains. The "Evid." column is tautological: `evidence = outcome ≠ missing_evidence`, so 0.89 ≈ 1 − 0.08; the 0.90 in "-- recovery" arises because failed episodes return `evidence=1`. Screenshot latency is unchanged in the code but would be zero in the simulated row. |
| -- Φ | config identical to `no_verification` | `verification_mode="none"` / `enable_verification=False` (nodes.py:1447–1455) | Matches. The row duplicates Table B. |
| -- memory, RAG | only episodic memory on repeated workflows (`memory="off"`) | `enable_memory` (provider.py, rag/router.py:119, nodes.py:1647); `enable_rag` gates knowledge retrieval (rag/retriever.py:98, router.py:39) | **RAG is not modelled.** Label it "-- memory" and cite only `enable_memory` (the caption cites `enable_memory`/`enable_rag`). |
| -- recovery | p(recovered)=0: an action failure ends the episode | `enable_recovery=False` makes `RecoveryEngine.handle_failure` fail immediately (engine.py:133). But `verify_node` still does **up to 3 inline retries** (nodes.py:1376–1377: `retry_count<3 → running`) before routing to `error_recovery`. | The implemented switch removes less than the simulated row. State this, or add a switch for the inline retries. |

**Proposed components.** Enhanced validation, evidence-guided recovery and the relevance filter are marked ‡ in every
table. Self-verification exists (`verification_mode="self"`, manager.py:383). I found no proposed component presented as
implemented in the simulation sections. Appendix A labels the computer backend "Design, Not Implemented".

---

## 5. Other methodological flaws

### M-1 (Medium): fail-closed on missing evidence is applied asymmetrically
`phi_missing_evidence_reject` (0.8) is applied only when `verifier in ("phi","enhanced")` (l.132). The basic detector
(error check E only, `verification_disabled_checks=[H,Q,T,X,R]` in measure_inputs.py:64) contains the same fail-closed
path: an exception in step 1 sets `has_error_state=True` (manager.py:249–253).

The basic detector should therefore also reject when the page cannot be read. The asymmetry raises Φ's FRR and lowers
its FC relative to basic detection; see the third column of the H-1 table. **Fix:** apply the rule to `basic` as well.

### M-4 (Medium): Study E's retry baseline does not reflect the graph
- **The real strategy sequence is different.** `m3_recovery` records `select_strategy(ftype, r)` for r=0..6. In the
  graph, action errors first pass through `verify_node`'s 3 inline retries, which increment the shared `retry_count`.
  The engine is therefore entered at `retry_count=3`. Navigation failures are the exception: they go straight to
  `error_recovery`. The executed sequence is roughly: 3 plain re-plans, then alternative_selector, vision, vision,
  exhausted.
- **Only one strategy changes behaviour.** Only `vision_fallback` changes behaviour (nodes.py:688). "retry",
  "alternative_selector" and "replan" all loop to `extract_dom` → `plan_action`.
- **Missing-confirmation recovery is not reachable.** The missing-confirmation message ("Max iterations exceeded …") is
  produced only when the 15-call budget is used up (nodes.py:1489). Any recovery attempt reaches `verify_node` with
  `llm_calls ≥ 15` and fails again, so the 4/20 retry-based recoveries cannot happen in the implementation.
- **Other assumptions.** Detection of the five other failure modes is assumed to be 1. Evidence-guided recovery uses a
  constant per-attempt p over 6 independent attempts.

**Fix.** Measure the sequence through the graph, by driving `verify_node` → `error_recovery` with stubbed failures,
and model missing-confirmation recovery as 0 under the budget, or disclose these points.

### M-5 (Medium): the latency model omits the main cost of a rejection
`latency_study` does not use `episode()` results:
- **No rejection loop.** No replanning after a rejection is added. Φ withholds 16 of 71 claims, and each withheld claim
  costs at least one more planner call (mean of the lognormal ≈ 3.4 s), DOM extraction and screenshots. That adds
  ≈ 0.54 s per episode, about 2.9% of the 18.6 s mean, against the reported +0.035 s (0.2%). Continuation successes are
  credited in TSR at no time cost.
- **The number of checks is wrong.** `checks` depends on the outcome class (incomplete/incorrect → 2), not on actual
  rejections or claims. Φ also runs when the plan ends without a claim (nodes.py:1437–1441), and `detect_captcha` runs
  on every verify.
- **Screenshots are undercounted.** The code takes 3 per step (dom_observation, before, after) plus `final_completion`
  and `completion_proof`; the model takes 2 per step.
- **Recovery cost is the same for all configurations.** It is fixed at 2 attempts whenever `u_actfail<p`, regardless of
  the recovery configuration or outcome.

**Fix.** Drive time from the episode trace: add (planner + DOM + screenshots) × number of extra loops per rejection,
count Φ calls per actual verification event, and use 3 screenshots per step plus the completion screenshots.
Restate H5 as "+x% including re-planning after rejections".

### M-7 (Medium): derived parameters rest on tiny samples, and their uncertainty is not propagated
- **Detection rates.** Per-category detection uses n=3–6 unsatisfied states (multi_step 2/3 → 0.625; data_entry 1/3).
- **Missing-confirmation detection.** Study E's missing-confirmation detection reuses multi_step n=3 (disclosed).
- **Memory misleading rate.** It is 3/10 raw, without the (k+.5)/(n+1) estimator used elsewhere, so the estimators are
  inconsistent. Relevance was judged by the author: "Create a note titled Groceries" counts as relevant to "Call
  plumber", and `shop_price` counts as misleading only because of its rank.
- **The MC intervals are too narrow.** The 1,000 MC replications regenerate scenarios only. Parameters stay at their
  point estimates, so the MC percentiles (e.g. FC reduction 0.05–0.17, "96% of sets") understate uncertainty.

**Fix.** In each replication, draw every derived rate from Beta(k+.5, n−k+.5) (parametric bootstrap). Use the same
estimator for the memory rate. Report how much of the MC spread comes from parameter uncertainty.

### L-1 (Low): the "held-out" framing and the freeze disclosure
- **The seed is not held-out data.** Seed 202 is another draw from the same generator. It protects against nothing that
  seed 101 could not, and any tuning on dev outputs carries over in full.
- **The freeze cannot be verified.** The freeze commit `3a0aa8e` (16:52:31) was followed 7 minutes later by the outputs
  (`41a6097`). Dev outputs were not committed at the freeze, so it cannot be verified that the parameters were set
  before any simulation output was seen.
- **The "one function was changed" sentence is out of date.** 06_methodology says one function was changed after the
  freeze. `1615ac5` has since changed `episode()` as well, adding `claimed`/`y_claim`/`accepted`. Outputs are unchanged:
  `scenarios.csv` and `results.json` are not in that diff.

**Fix.** Call it a "reporting seed", state that the meaningful variability is the MC distribution, and update the
freeze sentence to list both post-freeze changes.

### L-2 (Low): independent validation and minor points
- **The validation is narrow.** It recomputes the arithmetic from the per-scenario files and does not check `episode()`
  against the implementation. That is now disclosed; it would catch none of H-1 to H-3 or M-1 to M-5.
- **Wilson intervals look like sampling error.** Wilson intervals on synthetic counts read like sampling uncertainty of
  the agent. The "conditional" wording mitigates this; consider dropping them from policy-level synthetic rows.
- **Other outcome classes have no measured Φ behaviour.** "stale"/"contradictory" outcomes have no measured Φ behaviour.
  They inherit the category rate, and "ambiguous" is assumed ×0.5.

---

## Already fixed by 1615ac5 (verified)
- **Accuracy indicator.** The mixed "reported == y" accuracy indicator (p=.80) was withdrawn. The decision-level analysis
  (`decision_analysis.py`) is correct; the asserts confirm identical claims and `y_claim` across the four verifiers.
- **Table B and tests.** Table B and the tests table now separate the decision, FC and success levels. H2's DV is
  decision accuracy.
- **Evidence ablation row.** The row was relabelled "-- stored evidence§" with the caption caveat. The body text still
  says "it removes the audit trail", which is not true of `enable_evidence` (see §4).
