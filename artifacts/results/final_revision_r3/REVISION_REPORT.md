# Main-manuscript revision: wording, consistency audit and readiness

Scope: main manuscript only (`paper/main.pdf`). The supplement was not modified.

## 1. Change log (important wording changes)

| Location | Before | After |
|---|---|---|
| Abstract, last sentence | "No end-to-end evaluation with a language model was executed; its harness is released." | "The evaluation covers component-level validation and simulation-based analysis under controlled conditions; an evaluation harness for task-level studies is released." |
| Abstract, sentences 1 and 9 | Longer phrasing | Shortened, to keep the abstract at 247 words (IEEE limit 250); content unchanged |
| §I, closing sentence | "We do not claim that the agent completes tasks: the end-to-end evaluation is implemented but not run." | "Claims are confined to the evaluated components and simulation conditions; task-level success of the full agent with a language-model planner is outside the scope of this study." |
| §VI, hypotheses intro | "None is confirmed end to end" | "None is tested at task level in this study" |
| §VII, opening | "Three evaluations … (iii) an end-to-end protocol …, implemented but not executed. Only (iii) would validate the full agent" | "The evaluation comprises two completed studies: (i) component-level ACTUAL experiments … (ii) seeded SYNTHETIC computational experiments …" |
| §VII-B, title and text | "End-to-End Harness … The protocol that would validate the full agent is implemented but not executed." | "End-to-End Evaluation Harness … For task-level evaluation of the full agent, which lies outside the present study, we release a harness." |
| §VII-C, "Why simulation" | "…model weights, which the environment used for this paper could not download." | "The evaluation focuses on component-level validation and simulation-based analysis under controlled experimental conditions. Simulation is appropriate because…" (the scientific justification is kept) |
| §VII-C, evidence classes | PROPOSED: "a component or evaluation that does not exist yet" | "a designed component that is not implemented" |
| §V, component audit | "implemented but unevaluated" | "implemented and unit-tested but not separately evaluated" |
| §VIII-E, title and text | "End-to-End Evaluation: We have not run the end-to-end evaluation … could not download model weights. Consequently this paper makes no claim …" | "Scope of the Measurements: These measurements characterize the gate, browser and memory components, locality and the oracle under controlled conditions. Task success of the full agent and the task-level effects of the gate, memory and recovery are examined in simulation; the released harness supports their direct measurement." |
| §X, Discussion | "The evidence does not show that the agent completes tasks." | "The evidence characterizes the gate's decisions, not task-level success of the full agent." |
| §XI, privacy property | "It is not a privacy guarantee." | "It is a property of data locality under the default configuration, not a formal privacy guarantee." |
| §XI, security | "We make no security claim" | "Security hardening is outside the scope of this work" |
| §XIII, Conclusion | "*Not executed*: the end-to-end evaluation …" | "These findings characterize the framework's behaviour within the evaluated components and simulation conditions; task-level evaluation with a language-model planner, supported by the released harness, and per-step postconditions derived from the plan are natural extensions." |

**Unchanged:**
- every number, test, table, figure, citation and technical description;
- all evidence labels (ACTUAL / SYNTHETIC / ASSUMED / DERIVED / PROPOSED);
- the post-hoc disclosure of the simulation and the comparison of the gate against its error check alone (p = 0.070).

No sentence claims that experiments with a language-model planner were conducted.

## 2. Statistical and numerical consistency audit

| Check | Result |
|---|---|
| Held-out-2 gate: 9/22 withheld, 1/20 false rejections; McNemar against dispatch-only, 9 vs 1 | Recomputed p = 0.0215 → printed 0.021 ✔ |
| Gate against the error check E alone: held-out 2, 7 vs 1; pooled, 8 vs 2 | Recomputed p = 0.0703 / 0.1094 → printed 0.070 / 0.11 ✔ |
| Pooled held-out gate against dispatch-only, 11 vs 2 | Recomputed p = 0.0225 → printed 0.022 ✔ |
| Decision level (SYNTHETIC): 52/74 vs 46/74, discordant 9 vs 3 | Recomputed p = 0.146 → printed 0.15 ✔ |
| Gate latency | Recomputed median 26.84 ms over 83 decisions → printed 27 ms / 26.8 ms ✔ |
| Egress (clean rerun) | 70 episodes, 555 connections, all to 127.0.0.1 ✔ |
| Simulation policy and decision counts, paired tests, recovery and memory | Separately written recomputation script (`final_audit/scripts/recompute_sim.py`): 17/17 checks match ✔ |
| Table regeneration (`make_tables`, `gate_stats.py`) | Byte-identical to the committed tables ✔ |
| Build | 0 errors, 0 undefined references, 0 overfull boxes. Main text 8 pages plus 1 page of references; abstract 247 words ✔ |

## 3. Title: is "Privacy-Preserving" supported?

**Partly.** The evidence supports a narrow claim of model locality:
- in the default configuration the model client refuses non-loopback endpoints (unit-tested);
- the instrumented Python processes connected only to loopback in 70 episodes run on a clean commit.

The evidence does not cover:
- a real model server's traffic;
- Chromium's own traffic;
- encryption of stored data;
- a formal privacy guarantee.

The abstract (§I) and §XI define the term narrowly, and every privacy statement stays within that definition. On that basis, keeping the title is defensible.

**Recommendation.** No change is required, provided the narrow definition stays in the abstract. If reviewers object, the most accurate alternative is "…for **Local-First**, Privacy-Aware Intelligent Task Automation" or "…with **Local Inference**…", which describes what was tested without implying a formal guarantee.

## 4. Submission-readiness assessment

**Verdict:** ready for submission as a component-level and simulation-based study.

**Before upload (author actions):**
1. Fill in the author block, or leave it anonymous for double-blind review and replace the GitHub URL with an anonymized link.
2. Confirm that the acknowledgment describes your role correctly.
3. Optionally, create a release tag and cite it in §V.

**Expected reviewer points** (the paper already answers each):
- **Novelty relative to execution monitoring:** answered in §II.
- **Gate not significantly better than its error check alone on held-out states:** reported transparently.
- **No task-level LLM evaluation:** stated once as the study's scope.
