# R2 Methodology Audit (Agent 1): Agentic Pilot paper

Audited: HEAD `aee8c50`. No repository file was edited. Code was checked in `backend/agent/{graph,nodes}.py`, `backend/verification/manager.py`, `backend/recovery/engine.py`, `backend/rag/router.py`, `backend/memory/provider.py`, `backend/llm/gateway.py`, `benchmarks/simulation/simulate_v2.py` (and the `derive_inputs` it uses from v1), `artifacts/experiments/verification_gate_study.py` and `benchmarks/e2e/`.

## Previous audits: what is resolved

These items are now fixed in the paper or tables:

- **Final-review findings:**
  - F1: the need_help and executor entry paths now follow the code (`ENTRY` in `simulate_v2.py`).
  - F2–F10 and F12.
  - F15–F19.
  - F21 and F23–F24.
- **Earlier methodology-audit findings:**
  - H-1: false-rejection rates now exclude bot-check pages.
  - H-2: "by construction" is now disclosed.
  - H-3: continuations are re-verified.
  - H-4: the continuation rate is now swept.
  - M-1: the basic detector now fails closed.
  - M-5: re-planning is now in the latency model.
  - M-7: Beta draws are now used.

The findings below are new, or are residual parts of items that were only partly resolved.

**Hardware (task 4).** No text in sections 00–14 or the tables lists physical hardware as pending or as a blocker. The machine descriptions (06:4, 06:30) are provenance only.

**Severity counts.** No Critical findings; 3 Major; 16 Minor.

---

## Major

### 1. Major: "completion claim" in the simulation, and baseline (a), do not match the code's evaluation trigger
- **Where:**
  - `06_methodology.tex:32` ("how often the planner claims completion of an unfinished task")
  - `07b_simulation.tex:11` ("the planner claims completion in 74 scenarios")
  - `tables/e2e_design.tex:12` (`no_verification`: "every completion claim accepted")
  - `05b` H1 ("vs. accepting every claim")
- **Evidence:**
  - `verify_node` evaluates the check whenever `should_verify_completion` holds (`nodes.py:1439-1443`). That is true for a `complete` action, **or** `cur_step_idx >= len(task_plan.steps)`, **or** an exact-text `type_text`.
  - `parse_intent_node` always creates a plan, with a one-step plan for requests that are not decomposed (`nodes.py:172-186`).
  - So for every request of eight words or fewer without a connective, Φ runs after **every** successful action. If Φ passes, the task ends as Completed whether or not the planner claimed completion.
  - Under `verification_mode="none"`, the same trigger returns `verified=True` (`nodes.py:1452-1455`). Baseline (a) therefore ends such a task after its first successful planned action, not "when the planner claims completion".
  - Algorithm 1, line 23, shows the trigger, but no prose explains it. The simulated "claim" is then an abstraction of this trigger that the paper never defines.
- **Fix:** Append to 06:32, after "...is assumed and listed with its class in Table~\ref{tab:sim-params} (Appendix~\ref{app:simparams})":
  > "A \emph{claim} in the simulation stands for any point at which the code evaluates $\Phi$: a \texttt{complete} action, any successful action on the last plan step (for a request that is not decomposed, every successful action), or the typing of requested exact text; $\pi$ is the probability that such a point is reached while the task is unfinished."
- **Also change `tables/e2e_design.tex:12`.** Replace "every completion claim accepted" with:
  > "completion accepted at every point where $\Phi$ would be evaluated (a \texttt{complete} action or a successful action on the last plan step)"

### 2. Major: retry counter and attempt limits are described as per action, but they are per task
- **Where:**
  - `04_architecture.tex:17` ("A failed action is retried through a fresh observation up to three times; later failures are ... assigned a strategy ..., with at most six attempts.")
  - `tables/sim/recovery.tex` caption ("Entry paths and strategy sequences follow the code")
- **Evidence:**
  - `retry_count` is incremented by the inline retries (`nodes.py:1376-1377`) and by the engine (`engine.py:188,201`). It is never reset; `grep retry_count backend/` shows no reset.
  - `max_total_retries=6` counts both kinds of retry (`engine.py:61,98,142`).
  - Consequences: the three inline retries are a per-task budget, not a per-action one. After them the engine gets at most three attempts. Once the counter reaches 3, a later action error goes to the engine without inline retries, and at 6 the task fails.
  - Study E models one failure per scenario, which happens to match the code for a first failure. That assumption is not stated.
- **Fix:** Replace 04:17's first sentence with:
  > "A failed action is retried through a fresh observation while the task's retry counter is below three; the counter is shared with the recovery engine and never reset, so these inline retries are a per-task budget. After them, failures are classified into seven types and assigned a strategy (retry, alternative selector, vision fallback, replan) until the counter reaches six, i.e.\ at most three engine attempts after the inline retries."
- **Also add to the `tables/sim/recovery.tex` caption**, after "follow the code":
  > "for the first failure of a task (each scenario has one failure; in the code later failures find the shared retry counter partly used)"

### 3. Major: the H2 conclusion does not reconcile the ACTUAL component test with the SYNTHETIC "not supported", which rests on assumed inputs
- **Where:**
  - `05b_hypotheses.tex:4,17` (H2: "not supported for Φ at n=74 claims")
  - `07b_simulation.tex:15`
- **The actual component result:**
  - The gate study tests paired decision correctness against a dispatch-only rule. On held-out 2 the gate is correct on 28 of 42 states (0.67, Wilson 0.52–0.79) against 20 of 42 (0.48, 0.33–0.62), with p = 0.021. Pooled over held-out 1 and 2 it is 36/54 against 27/54, with p = 0.022.
  - This is the component-level analogue of H2's dependent variable. It is significant, yet neither the hypothesis table nor 07b states it.
- **Why the synthetic result is "not supported":**
  - I recomputed from `out/heldout_v2/scenarios.csv`. Two of Φ's three decision-level false rejections come from the `missing_evidence` outcome class, which is rejected with the ASSUMED rate 0.8 (the outcome-class share 0.08 is also ASSUMED). The third comes from an `ambiguous` scenario.
  - The measured false-rejection rate is 0/24, which the estimator turns into 0.02.
  - So the synthetic non-significance at n = 74 rests largely on ASSUMED parameters.
- **Fix 1 (05b:4).** Replace "H1 and H2 also have \textsc{actual} component-level evidence from the gate study (Section~\ref{sec:res-gate})" with:
  > "H1 and H2 also have \textsc{actual} component-level evidence from the gate study: on held-out~2 the gate withholds 9 of 22 premature completions and is correct on 28 of 42 states against 20 of 42 for a dispatch-only rule ($p=0.021$; Section~\ref{sec:res-gate}). H5 has \textsc{actual} latency evidence, and the inputs of H3 and H4 are \textsc{actual} measurements of the memory store and the recovery engine."
- **Fix 2 (`tab:hyp`, H2 cell).** Replace it with:
  > "component (\textsc{actual}): 28 vs 20 of 42 correct, $p{=}.021$; simulation: not significant at $n{=}74$ (.70 vs .62, $p{=}.15$ cond.), 2 of 3 false rejections from assumed missing evidence; enhanced: yes by assumption"
- **Fix 3 (07b:15).** After "wrong alone in 3, all false rejections", insert:
  > "(two of them on scenarios with missing evidence, which $\Phi$ rejects at an \textsc{assumed} rate of 0.8; the measured false-rejection rate is 0 of 24)"

---

## Minor

### 4. Minor: Algorithm 1 and 06:34 differ from the code on the budget and on blocking
- **Where:**
  - `figures/algorithm.tex:19` ("exhausted or blocked → Return Failed")
  - `figures/algorithm.tex:27` ("model calls ≥ K → Return Failed")
  - `06_methodology.tex:34` ("a missing confirmation never reaches the recovery engine")
  - `06_methodology.tex:22` ("the same budget of 15 planner calls")
- **Evidence:**
  - Blocked recovery returns `blocked`, which ends the task as Blocked (`engine.py:174-180`, `graph.py:76-80`).
  - A rejection at 15 or more calls returns `failed`, and `verify_router` sends it to `error_recovery` (`nodes.py:1502-1503`, `graph.py:64-71`). The engine can return `running`, so up to 6 − `retry_count` further planner calls can follow. The budget is therefore soft.
  - A missing confirmation reaches the engine through this path ("Max iterations exceeded without satisfying goal ...").
- **Fix (algorithm, line 19):**
  > `\If{$\textit{st}$ is blocked} \Return \textsc{Blocked} \EndIf \If{$\textit{st}$ is exhausted} \Return \textsc{Failed} \EndIf`
- **Fix (algorithm, line 27):**
  > `\If{model calls $\geq K$} go to line~\ref{alg:recover} \Comment{budget failure enters recovery} \EndIf`
- **Fix (06:34).** Replace "a missing confirmation never reaches the recovery engine" with:
  > "a missing confirmation reaches the recovery engine only as a budget failure after 15 model calls"
- **Fix (06:22).** Replace "the same budget of 15 planner calls" with:
  > "the same budget of 15 planner calls (after which the recovery engine may grant its remaining attempts)"

### 5. Minor: the definition of E is incomplete
- **Where:** `03_problem.tex:11`.
- **Evidence:**
  - E also rejects bot-check markers: a URL containing `sorry/index` or `recaptcha`, or a title containing "unusual traffic" (`manager.py:238`). This is why removing β changes few decisions.
  - The sign-in check applies only when the request contains an explicit URL (`manager.py:240-245`).
- **Fix.** Replace "or redirect to a sign-in page the request did not name ($E$)" with:
  > "bot-check URL or title, or redirect to a sign-in page when the request names a URL that is not one ($E$)"

### 6. Minor: the recovery strategy count is inconsistent
- **Where:** `10_limitations.tex:14`, "two of the four recovery strategies have no distinct behavior". This contradicts 04:17 ("the other strategies repeat ordinary planning").
- **Evidence:** Only `vision_fallback` is read anywhere outside the engine (`nodes.py:688`). Retry, alternative selector and replan all route to `extract_dom` and then `plan_action`.
- **Fix:**
  > "three of the four recovery strategies (retry, alternative selector, replan) behave identically, as ordinary re-planning"

### 7. Minor: the dependent variables of H3 and H5 do not match the reported outcomes
- **Where:** `05b_hypotheses.tex:18,20`.
- **Evidence:**
  - H3's DV is "TSR, ctx. accuracy", but ctx. accuracy is no longer reported anywhere (`tables/sim/memory.tex` has TSR, FCR and P(misleading)). "Contextual consistency" is not measured.
  - H5 says "decisions more conservative" but cites the policy-level FRR, which includes complete tasks that were never claimed. The decision-level count is 3/46 for Φ against 0/46 with no verification (Table sim-baseline).
- **Fix (H3 DV cell):**
  > "TSR on repeated workflows"
- **Fix (H5 outcome cell):**
  > "$\Phi$ 5.2--26.8\,ms (\textsc{actual}); episode +2.6\% mean; decision FRR 3/46 vs 0/46 (cond.)"

### 8. Minor: the evidence-class list omits ASSUMED
- **Where:** `06_methodology.tex:28` ("every number in this paper carries one of five classes"). ASSUMED is used throughout Table sim-params and in captions.
- **Fix:** Replace "one of five classes: ... or \textsc{proposed} (behaviour of an unimplemented component)" with:
  > "one of six classes: \textsc{actual} (measured on the implementation), \textsc{derived} (computed from actual measurements), \textsc{assumed} (chosen input), \textsc{synthetic} (produced by the simulation), \textsc{literature}, or \textsc{proposed} (behaviour of an unimplemented component)"

### 9. Minor: the paper never says why simulation is appropriate, and the scope of each evaluation is not stated in one place (task 3)
- **Where:**
  - `06_methodology.tex:4` ("The experiments need no language model.")
  - `06_methodology.tex:28` ("...could not be installed... before those runs exist")
  - `07_results.tex:37` ("could not download model weights"), which gives a different reason.
- **Problem:**
  - The paper justifies the simulation only as a stop-gap, never on its merits.
  - Component-level, simulation and not-executed scopes are stated only in the abstract and conclusion.
- **Fix 1 (06:4).** Replace the first sentence with:
  > "Three evaluations are reported, with different scope: (i) component-level \textsc{actual} measurements on the implementation without a language model (gate study, ablation, latency, retrieval ranks, recovery classification, 70 control-loop episodes with a scripted stand-in model for the egress test, and 114 scripted trajectories for oracle validation); (ii) a seeded \textsc{synthetic} simulation of the full agent built on those measurements and stated assumptions; (iii) an end-to-end protocol with a language model, implemented but not executed. Only (iii) would validate the full agent; (i) validates components and (ii) shows what the components imply under the assumptions."
- **Fix 2 (06:28).** Replace the first two sentences of "Why simulation" with:
  > "The end-to-end protocol needs local model weights, which the environment used for this paper could not download. A simulation is appropriate for the remaining questions because the quantities they depend on separate into component behaviour that we can measure without a model (detection and false-rejection rates of $\Phi$, latencies, the engine's classification, retrieval ranks) and planner behaviour that we cannot; propagating the first through the control flow of the loop, while sweeping the second, shows which unmeasured parameters decide H1--H5. We built such a seeded simulation (\texttt{benchmarks/simulation})."

### 10. Minor: inputs of the latency model are not specified
- **Where:** `06_methodology.tex:41` and `07b_simulation.tex:39`.
- **Evidence:**
  - The simulated Φ time is resampled from the 83 gate-state latencies (`derive_inputs`: `phi_ms` from `verification_gate_cases.csv`, measured on the 2.1 GHz machine), not from the 5.2 ms site measurement.
  - Each rejection adds exactly one planner call, one DOM extraction, one click and three screenshots (`simulate_v2.py:428-431`).
- **Fix (07b:39).** Replace "because a rejected claim costs further planning steps" with:
  > "because each rejected claim costs one further planning step (planner call, DOM extraction, click, three screenshots; assumed); $\Phi$ times are resampled from the slower gate-state measurements"

### 11. Minor: "by construction" is a property of the model and should say so
- **Where:** `07b_simulation.tex:13`.
- **Evidence:** In the code, a false rejection followed by further actions can be accepted later on a changed page, and that page may be unsatisfied (Finding 1: Φ is re-evaluated after every successful last-step action). The model omits this, so the "structural 0" holds only in the model.
- **Fix.** Replace "The direction is fixed by construction: $\Phi$ can only withhold" with:
  > "In the model the direction is fixed by construction (in the code, a continuation after a false rejection could later be accepted on a changed page, which the model omits): $\Phi$ can only withhold"

### 12. Minor: "significant share" misdescribes the test
- **Where:**
  - `07_results.tex:13` ("the gate withholds a significant share of premature completions")
  - `08_discussion.tex:4` ("withholds a significant share of premature completions")
- **Evidence:** The p-value tests paired decision correctness against dispatch-only. It does not test whether the withheld share is greater than zero, which holds trivially.
- **Fix (07:13):**
  > "the gate is correct on significantly more held-out states than a dispatch-only rule and withholds 41\% of premature completions"
- **Fix (08:4):**
  > "withholds 41\% of unsatisfied held-out states and is correct on significantly more held-out states than a dispatch-only rule"

### 13. Minor: "live loop" overstates the gate-study setting
- **Where:**
  - `12_conclusion.tex:4` ("inside the live loop the predicate withheld")
  - `08_discussion.tex:4` ("evaluated inside the agent loop")
- **Evidence:** The real `verify_node` was called on a constructed state, with I/O stubbed (`verification_gate_study.py:244-288`). It was not run inside an executing loop.
- **Fix:** Use "inside the live verification node" in both places.

### 14. Minor: evidence classes are conflated in a contribution and in the conclusion
- **Where:**
  - `01_introduction.tex:21` ("which indicates ... where the implementation falls short---memory without a relevance threshold, recovery blind to missing confirmations")
  - `12_conclusion.tex:4` ("memory and recovery would need a relevance filter and an explicit confirmation check")
- **Evidence:** Both shortfalls are ACTUAL component findings, and the simulated benefit of the fixes follows from PROPOSED rates.
- **Fix (01:21).** Replace the phrase after "false rejections" with:
  > "; the shortfalls it builds on---memory without a relevance threshold, recovery blind to missing confirmations---are \textsc{actual} component findings"
- **Fix (12:4).** Replace the memory clause with:
  > "the measured memory store has no relevance threshold and the recovery engine does not recognize a missing confirmation; the simulated benefit of fixing either follows from assumed rates"

### 15. Minor: the abstract leads with the optimistic design-state estimate
- **Where:** `00_abstract.tex:2`, "the gate withheld 20 of 23 unsatisfied design states (95% interval 0.68--0.95)". The fixes were designed on these states, and 07:11 refuses to test them.
- **Fix:**
  > "on 42 held-out states frozen before testing, the gate withheld 9 of 22 unsatisfied states (0.23--0.61) and rejected 1 of 20 satisfied ones (exact McNemar on paired correct decisions $p=0.021$ against a dispatch-only rule), against 20 of 23 on the states its rules were fixed on, because its checks are keyed to request wording."

### 16. Minor: the released e2e harness cannot exercise conjunct H
- **Where:** `06_methodology.tex:18`; `tables/e2e_design.tex` (`gate_without_`c).
- **Evidence:** H fires only on google, bing or duckduckgo home pages (`manager.py:268`). The harness search engine is `{base}/findr` on 127.0.0.1 (`benchmarks/e2e/tasks.json`). So `gate_without_H` cannot change any decision in the harness.
- **Fix.** Append to 06:18:
  > "Because the search-home check $H$ recognizes only public search engines, it never fires on these sites; its ablation in the harness is uninformative."

### 17. Minor: pending items in the text (none concern hardware)
- **Where:**
  - `05_implementation.tex:4` ("a release tag for the evaluated version has not yet been created")
  - `06_methodology.tex:22` ("is left to the authors' runs")
- **Fix (05:4).** Replace the clause with:
  > "the evaluated paper version is commit \texttt{aee8c50}"

  Or cite the tag once it has been created.
- **Fix (06:22):**
  > "A published agent framework as a third baseline would need its own model and prompts and is outside the scope of this paper."

### 18. Minor: stale code comment
- **Where:** `benchmarks/simulation/simulate_v2.py:15-17`, docstring C4: "navigation failures and need_help go to the engine directly". This contradicts the corrected `ENTRY` (lines 53-62) that produces the reported numbers.
- **Fix:**
  > "C4 Recovery follows the implemented path per failure mode: three inline retries in verify_node for action errors, including need_help, then the recovery engine from retry count 3; a failed initial navigation is retried three times by the executor and then enters the engine at retry count 0; ..."

### 19. Minor: repetition that could be cut (task 5)
- **(a) "No end-to-end evaluation" appears eight times:**
  - 00:2, 01:13 ("and no end-to-end task with a language model is evaluated in this paper"), 01:32, 05b:4, 07:4, 07:37, 10:6 (second sentence) and 12:4.
  - Keep it in 00, 01:32, 07:37 and 12.
  - Delete the 01:13 clause, 07:4's second sentence and 10:6's "No result involves a language model or a live website, so the agent is not shown to complete tasks."
- **(b) Egress-scope caveats are repeated:**
  - 09:6, last two sentences ("The egress test observed ... not by the egress test."), restates 07:30.
  - Replace them with: "The scope of the egress test is given in Section~\ref{sec:res-privacy}; local file storage is established by code inspection."
- **(c) The research-question list is repeated:**
  - 01:15 and 05b:4 list RQ1–RQ5 almost word for word.
  - Replace 01:15 with: "\paragraph{Research questions} The gaps lead to five research questions and hypotheses H1--H5 (Section~\ref{sec:hypotheses})."
- **(d) Gate results are repeated:**
  - 08:4 ("What the evidence supports") repeats 07:13's closing sentence and 12:4.
  - Reduce 08:4 to: "\paragraph{What the evidence supports} The gate's coverage of new phrasings, not its cost, is its binding limit, and some of its defects appeared only inside the live verification node; the evidence does not show that the agent completes tasks."
