# Response to reviewers

**Manuscript:** "Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation" (revised `paper/main.pdf`, 9 pages: body and appendices on pp. 1–8, references on pp. 8–9).

We thank the reviewers. We address each point below.

One constraint shaped this revision: the environment in which it was prepared could not download language-model weights or reach live websites. We therefore ran every requested experiment that needs no model. For the experiments that do need one, we built and validated the full harness. Where data is still missing, we scoped the paper's claims down rather than leaving placeholders. Those runs are specified step by step in `AUTHOR_ACTIONS.md`.

**Key:**
- Option (a): experiment run in this revision.
- Option (b): claim scoped down.
- Option (c): protocol in `AUTHOR_ACTIONS.md`.

---

**R1. End-to-end LLM agent experiments.**
- **Action:** (b) + (c). We built a harness that runs the full loop (LLM planner → browser → Φ → recovery) on self-hosted sites and records success, steps, model calls, tokens, latency, verification decisions and recovery strategies (`benchmarks/e2e/run_e2e.py`). We tested the pipeline end to end with a scripted stand-in model; those episodes are not reported as results. No run with a language model was possible.
- **Paper change:** the paper no longer implies task-level results. §VII-E states that no end-to-end result exists and lists the questions it leaves open, and the components involved are marked unevaluated in Table II.
- **Location:** §VI-B (p. 5), Table III (p. 5), §VII-E (p. 7), `AUTHOR_ACTIONS.md` A1.

**R2. Realistic multi-step tasks.**
- **Action:** (a) for the task set, (c) for running it. The test set has 40 tasks on five self-hosted sites with fictional content (so answers cannot come from model memory):
  - categories: search, navigation, text entry, extraction, form submission, multi-step and unsatisfiable;
  - difficulty tiers 1–4, with a dev/test split; one site appears only in the test split;
  - documented selection and exclusion criteria.
- **Why not WebArena, Mind2Web, VisualWebArena or WorkArena:** we explain this in §VI-B (site images unavailable offline; live sites drift and block automation; Mind2Web is offline step prediction).
- **Location:** §VI-B (p. 5), Appendix B (p. 8), `benchmarks/e2e/tasks.json`.

**R3. Baselines.**
- **Action:**
  - **(a) Gate level:** the gate is compared with a dispatch-only rule, which is baseline (a) at component level, on the same 92 states, with exact McNemar tests. It is also compared with the gate before the fixes.
  - **(b)+(c) Episode level:** we implemented baseline (a), no verification, and baseline (b), LLM self-verification (`PILOT_VERIFICATION_MODE=self`), with the same model, budget and tasks.
  - **(c) Published framework:** a published agent as baseline (c) is in `AUTHOR_ACTIONS.md` A2.
- **Location:** Table IV (p. 6), Table III (p. 5), §V-c (p. 4).

**R4. Ablation study.**
- **Action:** (a) one-at-a-time removal of each kind of evidence (conjuncts E, H, Q, T, X, R and the bot-check halt β) on all 92 states, presented as a single table with paired tests. Ablations of memory/RAG and recovery need episodes: (b)+(c), and their configurations are implemented.
- **Location:** Table V (p. 6), §VII-B (p. 6), Table III (p. 5).

**R5. Independent held-out evaluation.**
- **Action:** (a). We added held-out 2: 42 states (22 unsatisfied), written to a stated procedure and committed (`b9d5088`, with its SHA-256 recorded) **before** the gate was run on them. No gate code changed afterwards.
  - Dev and held-out sets are reported separately.
  - The weak held-out result is reported as found: 9/22 withheld; 0/5 on extraction.
  - The limitation that held-out 2 has the same author is stated. Independent labelling is protocol A3.
- **Location:** §VI-A (p. 4–5), Table IV (p. 6), §VII-A (p. 6), §X (p. 7).

**R6. Implemented vs proposed.**
- **Action:** Table II now separates Impl./Integ./Test/Eval. Its caption states that claims are limited to rows with evidence.
  - The computer backend has moved from the main text to Appendix A, labelled "Design, Not Implemented".
  - Contributions and conclusions cover only implemented and evaluated parts.
- **Location:** Table II (p. 4), §I (p. 1), Appendix A (p. 8).

**R7. Claim strength ("privacy-preserving", "autonomous").**
- **Title:** the author asked to keep the title. We matched the claims to evidence instead of weakening the words.
- **Privacy:**
  - It is defined precisely: model inference restricted to the machine; records stored only on its disk.
  - It is now **enforced** in code: a non-loopback model endpoint is refused unless the user explicitly overrides it, and Chroma telemetry is off.
  - It is **tested**: in 70 full agent episodes, all 555 socket connections of the agent process went to 127.0.0.1. A repository test reproduces this.
  - What it does not cover is listed: data entered on websites, one-time downloads, unencrypted storage, Chromium background traffic.
- **Autonomy:** stated as browser-only, with user approval for high-risk tasks, CAPTCHAs handed to the user, and no end-to-end evaluation.
- **Threat model:** extended.
- **Location:** §I "Scope and terms" (p. 1), §V-c (p. 4), §VII-D (p. 6), §IX (p. 7), `tests/test_local_egress.py`.

**R8. Remove every [Pending].**
- **Action:** done. No `\todo`, "[Pending]", "TBD" or "XX" remains in the source or the PDF.
- **What happened to each of the nine placeholders:**

  | Placeholder | Resolution |
  |---|---|
  | Licence | Stated (MIT) |
  | Commit | Stated (`bf0a8a5`) |
  | Hardware | Stated for the experiments that were run |
  | Task list | Released (`tasks.json`) |
  | End-to-end results and case study | Scoped down (§VII-E) |
  | Acknowledgment note | Removed (the disclosure text is kept) |
  | Author block (3 items) | Empty `\author{}` for the author to fill (A6) |

**R9. FCR/FRR statistics.**
- **Action:** (a).
  - Definitions are restated with explicit counts (Eq. 2).
  - Every rate in Table IV is reported as k/n with Wilson 95% intervals; Clopper–Pearson intervals are in `gate_stats.csv`.
  - There is a per-category breakdown for the design set and held-out 2.
  - Exact McNemar tests compare against dispatch-only, against the gate before the fixes, and against each ablation.
  - **Operating point:** Φ is rule-based with no tunable threshold, which we now state (§III). The trade-off is shown through the ablation instead (only removing β, and removing X on the design set, trades FC for FR).
  - Bootstrap intervals for success differences are implemented for the episode-level analysis (`analyze_e2e.py`).
- **Location:** §III (p. 3), Table IV (p. 6), Table V (p. 6).

**R10. Independent oracle.**
- **Action:** (a) + (b). Both oracles are now defined.
  - **Gate study oracle:** it records whether the goal is achieved, judged from page facts. Each label was written with its state before the gate was run, and it shares no code with Φ. It has one annotator, so no κ is possible; protocol A3.
  - **End-to-end oracle:** it uses server-side records, the final URL and ground-truth facts, with no model and no shared code. Its error rate was measured on 114 scripted golden, idle and near-miss trajectories: 0/37 false negatives (95% CI 0–0.09) and 0/77 false positives (0–0.05). Its limitation to anticipated behaviour is stated.
- **Location:** §VI-A (p. 5), §VI-B (p. 5), §VII-D (p. 6), `benchmarks/e2e/validate_oracle.py`.

**R11. Algorithm 1.**
- **Action:** added, derived from the code (`graph.py`, `verify_node`, recovery engine). It covers inputs, observation, the β halt, planning, execution with evidence, retry and recovery, step progression, the Φ decision, and termination by budget.
- **Location:** Algorithm 1 (p. 3), referenced in §IV-A and Fig. 2.

**R12. Verification figure.**
- **Action:** Fig. 2 (TikZ) shows action → dispatch → (recovery | evidence sources) → conjuncts and β → Φ → completed, reject or blocked, with the evidence record. It replaces the earlier state-machine figure, which Algorithm 1 now subsumes.
- **Location:** Fig. 2 (p. 4).

**R13. Memory/RAG.**
- **Action:** (b) + (c). The memory contribution needs episodes. Memory is marked unevaluated in Table II and Table I (footnote d), and the contribution claim was removed.
- **What is ready:** the `no_memory` configuration, logging of retrieved items, and a report of episodes where memory coincided with a loss (`memory_losses.csv`) are implemented. Retrieval quality is not measurable without labelled relevance; the protocol inspects failure cases instead (A1).
- **Location:** §VII-E (p. 7), Table II (p. 4).

**R14. Recovery strategies.**
- **Action:** (b) + (c). The code-level fact is reported: only retry and vision fallback have distinct behaviour. Per-strategy comparison is implemented by pinning a strategy (`recovery_*_only`), with recovery rate, actions and model calls in `recovery.csv` (A1).
- **Location:** §IV-A (p. 3), §X (p. 7), Table III (p. 5).

**R15. Verification overhead.**
- **Action:** (a) at decision level: median latency of 26.8 ms (90th percentile 29.5 ms, max 34.6 ms) over 83 decisions; 0 model calls, 0 tokens, 0 API cost and 0 browser actions per decision, by construction. Added steps per task and gain per unit of overhead need episodes; `overhead.json` computes them (A1).
- **Location:** §VII-C (p. 6).

**R16. Table I.**
- **Action:** rebuilt with consistent columns: kind, environment, who decides completion, evidence, memory, open models, and a statement that all systems released code.
  - There is one legend; "--" was replaced by an explicit "n.r." (not reported).
  - Three references no longer cited were removed.
  - The new marks reuse the verified marks of the earlier table. The new "Completion" and "Environment" columns follow each paper's description.
- **Location:** Table I (p. 2).

**R17. Research gap.**
- **Action:** rewritten as three testable gaps (G1–G3), each grounded in cited work and mapped to a contribution and an experiment.
- **Location:** §I "Research gaps" (p. 1).

**R18. Contributions.**
- **Action:** split into scientific contributions (formulation; gate evidence including the negative generalization finding) and engineering contributions (agent and audit; locality enforcement and test; end-to-end harness), each with a section pointer.
- **Location:** §I (p. 1).

---

## Final checklist

| Item | Status |
|---|---|
| No placeholders | ✅ |
| Every number traces to the manuscript, an artifact or a logged run | ✅ (see `CHANGE_LOG.md`, claim sources) |
| FCR/FRR with counts, CIs and significance tests | ✅ for the gate study. The episode level is implemented, not run. |
| Baselines, ablations, memory/RAG, recovery and overhead each have a table or figure | ⚠️ Partly. Baseline (dispatch-only) is in Table IV, the ablation in Table V, and overhead in §VII-C (text). Memory/RAG and recovery have no data, only the design in Table III. This cannot be met honestly without model runs (A1). |
| Algorithm 1 and the verification figure, both referenced | ✅ |
| Oracle defined, with independence argument and error rate | ✅ (κ needs a second annotator: A3) |
| Privacy and autonomy matched to evidence and threat model | ✅ |
| Implemented vs proposed unambiguous | ✅ |
| Contributions split into scientific and engineering, each mapped to evidence | ✅ |
| All references verified | ✅ |
