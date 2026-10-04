# 12 — Revision audit (Phase 1) and plan (Phase 2)

Scope: `paper/` at commit `99dbeeb`, describing the agent code at `eb3803e`; artifacts in `artifacts/`. I have made no edits to the manuscript yet.

## 1. Manuscript map

| § | Content | Figures and tables |
|---|---|---|
| Abstract, I | Motivation, 4 contributions, scoped definitions of "autonomous" and "privacy-preserving" | — |
| II Related work | Web/computer-use agents, completion checking, memory, safety | Table I (`tab:related`, 13 systems × 8 capabilities) |
| III Problem | Environment and actions, α_t vs Φ (Eq. 1), postconditions per environment, browser predicate E/H/Q/T/X/R, grounding order, FCR (Eq. 2) and FRR | Table II (`tab:post`) |
| IV Architecture | LangGraph loop (11 nodes), browser backend, proposed computer backend | Fig. 1 (architecture), Fig. 2 (state machine) |
| V Implementation | Stack, capability audit, code fixes | Table III (`tab:status`) |
| VI Methodology | Gate fixture study (run); computer-use protocol (proposed) | Table V (`tab:protocol`) |
| VII Results | Gate study, routing resolution, test suite; end-to-end section with 2 pending items | Table IV (`tab:gate`) |
| VIII–XII | Discussion, safety/threat model, limitations, future work, conclusion, AI-assistance acknowledgment | — |

**FCR and FRR definitions (§III, Eq. 2):**
- FCR = |{τ ∈ T_c : Φ*(τ) = 0}| / |T_c|, over episodes the agent reports as complete.
- FRR = the fraction of episodes with Φ* = 1 that are not reported as complete.
- Φ* is a per-task oracle written by the experimenter.
- In the gate study, Φ* is the author's label on each constructed state.

**Datasets and tasks:**
- 38 design states and 12 held-out states, all constructed by the author and served offline with Playwright route interception.
- 6 categories: search, navigation, CAPTCHA, text entry, extraction, multi-step.
- No real-site tasks, no benchmark tasks, and no episodes involving a language model.

**Every quantitative claim in the paper and its source:**

| Claim | Value | Source |
|---|---|---|
| Design states, before fixes | Withheld 13–15 of 23 unsatisfied; rejected 3 of 15 satisfied | `verification_gate_*before_fixes.csv` |
| Design states, after fixes | Withheld 20/23; rejected 1/15 | `verification_gate_summary.csv` |
| Held-out states | Withheld 2/5 (1/5 before fixes); rejected 1/7 | same files |
| Gate latency | Median 30.6 ms | `verification_gate_run.log` |
| Test suite | 129 tests, 126 pass; coverage 65.0% | `junit_after_fixes.xml`, `coverage_after_fixes.txt` |
| Lines of code | 10,867 (1,679 in the graph nodes) | — |
| Routing resolution | No numeric result | routing CSVs |

All of these trace to logged runs. **I found no errors in the original numbers.**

## 2. Component status

Status key:
- **I+E**: implemented and evaluated.
- **I-NE**: implemented, not evaluated.
- **D**: proposed, design only.

| Component | Status | Evidence |
|---|---|---|
| Completion gate Φ (browser), bot-check halt | **I+E (component level only)** | `verification/manager.py`; gate study in the live `verify` node |
| Browser control (Playwright) | I+E (component) | Used by the gate study; tests |
| LangGraph loop, end to end with an LLM | **I-NE** | Code and mocked-model tests; no episode was run with a model |
| DOM grounding, vision fallback | I-NE | `nodes.py:688`; mocked tests only |
| Recovery: retry, vision_fallback | I-NE | `recovery/engine.py:45-112` |
| Recovery: alternative_selector, replan | **Partial**: label only, no distinct behaviour | `engine.py`; §V says so |
| Memory and RAG (Chroma) | I-NE | `memory/provider.py`, `rag/store.py`; retrieval runs, effect unmeasured |
| Model routing | I, evaluated only by resolution without inference | `routing_resolution.csv` |
| Task-level approval, injection sanitizer | I-NE | `security/`; the approval test needs web |
| Evaluation harness (6 presets) | I-NE: never run with a model | `experiment/runner.py`. Records status, duration and `llm_call_count`; **not tokens, cost or per-strategy recovery** |
| Privacy (local inference, local storage) | **I by default, not enforced**; no evidence beyond configuration | `config.py:14` loopback default; Chroma telemetry not disabled (`rag/store.py:36`, `memory/provider.py:60`) |
| Computer backend (desktop, files, processes, accessibility tree, action_gate, tiers) | **D**, plus an unintegrated prototype | `backend/desktop/`; nothing on the agent path |

The verifier is rule-based and makes **no model calls**, so its token and API cost is zero by construction. Its overhead is latency only, plus any extra steps it causes.

## 3. Placeholders and unsupported claims

`\todo` → "[Pending]" sites:

| # | Location | Item |
|---|---|---|
| 1–3 | Title block (hidden) | Author name, affiliation, email |
| 4 | §V | Licence and archived release |
| 5 | §VI | Hardware, OS, Ollama version, model digests |
| 6 | §VI | Task list and oracles |
| 7 | §VII-D | End-to-end results for 6 configurations |
| 8 | §VII-D | Screenshot case study |
| 9 | Acknowledgment | "review and adapt" |

Claims without sufficient evidence:
- **"Autonomous" in the title.** No autonomous episode has been run.
- **"Privacy-preserving" in the title.** Configuration default only. There is no egress test and no enforcement.
- **"Memory/RAG" as a capability.** Unmeasured.
- **Recovery as a capability.** Unmeasured, and 2 of the 4 strategies are labels only.
- **Table I rows.** Several marks are "--" or "P", and the column definitions mix "reported" and "supported". This is not a rigorous comparison (R16).
- **Gate results have no CIs and no significance tests (R9).** The held-out set has only 5 unsatisfied states, so its intervals will be very wide.
- **Same-author fixtures and labels.** No second annotator, so no κ is possible (R10).

## 4. Environment and feasibility (checked 2026-10-04)

| Resource | Status |
|---|---|
| CPU / RAM / disk | 4 vCPU, 15 GB, 28 GB free; no GPU |
| Ollama runtime | Downloadable (GitHub releases reachable) |
| **Model weights** | **Blocked**: `registry.ollama.ai` and `huggingface.co` are denied by the network policy |
| **Live websites** | **Blocked** (e.g., wikipedia.org, example.com denied) |
| PyPI, npm | Reachable |
| Hosted LLM API | None configured for the project. The session's own API endpoint is not a local model and would contradict the paper's design. |

**Feasible now, with no model:**
- **R9 statistics on the existing gate data:**
  - Wilson and Clopper–Pearson intervals;
  - exact McNemar's test of gate vs. dispatch-only on the same states;
  - per-category counts.
- **R4 partial:** a per-conjunct ablation of the gate (remove E, H, Q, T, X, R or the bot-check one at a time) on all 50 states. This is a real, new experiment.
- **R5 partial:** a larger held-out set, frozen and committed before scoring. It is still written by the same author, so it is not independent; that would be disclosed.
- **R15 partial:** verifier latency distribution and zero-token cost; extra actions per task needs episodes.
- **R7 evidence:**
  - enforce local-only model addresses and disable Chroma telemetry in code;
  - add a test that runs the agent with a mocked model and asserts no non-loopback connection.
- **R6, R8, R10–R12, R16–R18:** writing, with Algorithm 1 and the figure taken from the code.

**Feasible only if model weights can be downloaded:**
- R1, R3, R13, R14, and the episode part of R15. These would run on replayed local sites, because live web is blocked.
- With qwen2.5:1.5b on 4 CPUs, roughly 30 tasks × 4–6 configurations × 3 trials is about 6–15 hours. This is my estimate, not a measurement.

**Not feasible in this session:**
- **R2 with real benchmarks.** WebArena needs its Docker site images; Mind2Web is offline action prediction, not a closed loop.
- **R3(c) with a published verifier as specified,** which needs a hosted GPT-4-class model.
- **R10 κ,** which needs a second human annotator.

## 5. Revision plan (R1–R18)

Option codes:
- **(a)** run in this session;
- **(b)** scope the claim down;
- **(c)** add to `AUTHOR_ACTIONS.md` with a protocol.

| R | Current state | Planned change | Evidence / option |
|---|---|---|---|
| R1 End-to-end | None | If weights become available: run the full loop on replayed local sites and report success, steps, model calls, latency. Otherwise state that no end-to-end result exists. | (a) if weights, else (b)+(c) |
| R2 Real tasks | Constructed states only | Replayed local sites with documented selection, tiers and exclusions; real-site or WebArena runs as an author action | (a) partial if weights; (c) for real sites |
| R3 Baselines | Dispatch-only rule on fixtures | Fixtures: gate vs. dispatch-only (exists) plus McNemar. Episodes: no-gate and LLM self-check baselines, same model and budget, if weights. Published verifier: author action. | (a) fixtures; (a)/(c) episodes |
| R4 Ablations | Presets exist, never run | One table: per-conjunct ablation on fixtures (new run). Component ablations on episodes if weights, otherwise rows marked "not run" with no values. | (a) + (a)/(c) |
| R5 Held-out | 12 states | Enlarge to ≥40, frozen by commit hash before scoring; dev vs. held-out reported separately; same-author limitation stated. Independent labelling as an author action. | (a) + (c) |
| R6 Status | Table III exists | Add an "Evaluated" level per claim; move the computer backend fully into a labelled design section and Future Work | writing |
| R7 Claims | Title keeps both words, scoped in §I and §IX | Enforce local-only addresses, disable telemetry, add an egress test; state the autonomy level (browser only, approval for high-risk, CAPTCHA hand-off, not tested end to end). **Title wording needs your decision (see Q3).** | (a) code + (b) |
| R8 No [Pending] | 6 visible plus 3 hidden | Remove all; scope sentences down; move items to `AUTHOR_ACTIONS.md` | (b)+(c) |
| R9 Statistics | Counts only | Counts, Wilson 95% CIs, exact McNemar vs. dispatch-only and vs. pre-fix gate, per-category table. The rule gate has no threshold, so no trade-off curve; conjunct ablation shows the trade-off instead. | (a) |
| R10 Oracle | Briefly described | Define the fixture oracle: what each label asserts, how it was fixed before scoring, why independent (no model, written from page facts, not from Φ's output), and that it has a single annotator (no κ). | writing + (c) for κ |
| R11 Algorithm 1 | None | Pseudocode from `verify_node`, `verify_task_completion` and the recovery router | writing (from code) |
| R12 Figure | Fig. 2 state machine | New TikZ figure: action → evidence sources → Φ conjuncts/β → decision → recovery or commit | writing |
| R13 Memory/RAG | Unmeasured | With vs. without on episodes if weights; otherwise claim removed from the contributions and stated as unmeasured | (a)/(b)+(c) |
| R14 Recovery | Unmeasured | Per-strategy table on episodes if weights; otherwise only the code-level facts (2 of 4 strategies have no distinct behaviour) | (a)/(b)+(c) |
| R15 Overhead | Median latency only | Latency distribution; 0 tokens and $0 by construction; extra steps from episodes if weights | (a) + (a)/(c) |
| R16 Table I | Mixed semantics | Fix the column set (verification type, evidence sources, recovery, memory, real-web eval, open source, local models); one legend; re-verify each mark against the cited paper; drop rows I cannot verify | writing + checks |
| R17 Gap | Prose in §I–II | 2–3 falsifiable gaps, each mapped to a contribution and an experiment | writing |
| R18 Contributions | 4 items | Split into scientific and engineering, each pointing to a section | writing |

**Page limit:** the target venue is not given. New material (Algorithm 1, figure, 2–3 tables) will not fit 8 IEEE conference pages, so it needs either an appendix or a journal format (see Q2).

**Expected outcome without model weights:** R1–R3 and R13–R15 can be answered only by scoping the claims down and providing author protocols. The checklist items "baselines, ablations, memory/RAG, recovery and overhead each have a table" would then be met with fixture-level tables plus explicit "not run" statements, not end-to-end numbers.
