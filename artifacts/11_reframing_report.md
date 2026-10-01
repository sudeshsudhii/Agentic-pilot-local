# 11 — Reframing Report: browser agent → local computer-use direction

The paper describes agent code at commit `eb3803e`. The capability evidence is in `10_computer_use_audit.md`, and every claim and its source is listed in `07_claims_ledger.md`.

## A. What changed

- **Title:** changed from "…Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation" to **"Agentic Pilot: Toward a Local Computer-Use Agent with Evidence-Gated Task Completion"**.
  - "Toward" signals the direction without claiming a finished computer-use agent.
  - "Privacy-preserving" was dropped because only a narrow property is supported.
- **Structure:** now Introduction · Related Work · **Problem Formulation** (new) · **Architecture** (control loop, implemented browser backend, proposed computer backend) · Implementation (capability audit and fixes) · **Experimental Methodology** (component studies run, computer-use protocol proposed) · Results · **Discussion** (new) · **Computer-Use Safety and Privacy** (rewritten) · **Limitations and Threats to Validity** (new) · **Future Work** (new) · Conclusion.
- **Problem formulation:**
  - α (dispatch) vs Φ (completion) is generalized to Φ = ⋀ postconditions(g, P) ∧ π(P) ∧ ¬β(s, σ), over observed state, expected postconditions, task progress and safety/approval state.
  - The browser predicate (E, H, Q, T, X, R) is kept as the implemented instance.
  - FCR and FRR are defined in the problem section.
- **Table II (new):** postconditions per environment (browser, file, process, window, desktop UI, read-only), each with a status: *Impl.*, *Unit* (tested, not integrated) or *Prop.*
- **Architecture:**
  - Fig. 1 now shows an implemented browser backend and a dashed (proposed) computer backend.
  - The text states that the control loop's observation and execution nodes are still browser-bound.
  - A grounding order is given (typed state → DOM / accessibility tree → app metadata → vision → human), with implementation status per level.
- **Capability table (Table III):** separates *Impl.*, *Integ.*, *Test* and *Eval.* for 17 capabilities, including all computer-use ones.
- **Experiments:**
  - The gate, routing and test results are kept unchanged, explicitly scoped as browser component evidence.
  - New **proposed** computer-use protocol (Table V): browser, desktop app, files, process/window, cross-environment and safety families; VM snapshots; blind oracles; the 12 requested metrics, including human interventions and safety violations.
- **Safety:** a computer-use threat model covering:
  - injection via pages, documents, file names and accessibility labels;
  - destructive file and process actions;
  - command execution;
  - credentials, clipboard and screenshots.

  It states what exists, what does not, and the proposed controls. It makes **no security claim**.
- **Related work:** adds computer-use agents (Agent S, Windows Agent Arena, UI-TARS), completion judges (Pan et al., Sumyk and Kosovan), and agent safety (ToolEmu, OS-Harm, CaMeL). All 8 were verified; the bibliography now has 43 entries.

## B. What is actually implemented (verified)

The control loop (LangGraph), with these components:
- **Browser control** through Playwright: navigate, click, type with read-back, key, scroll, extract, screenshot.
- **Grounding:** DOM-first, with screenshot-based local vision fallback.
- **Completion predicate:** browser Φ with E/H/Q/T/X/R plus the bot-check pre-check and halt.
- **Evidence:** before/after screenshots per action, the DOM manifest, verification and recovery records, and execution records.
- **Approval:** a task-level human approval gate.
- **Recovery:** failure classification and bounded retries; the `vision_fallback` strategy is effective.
- **Models:** role-based local model routing; memory and RAG retrieval.
- **Evaluation:** an evaluation harness with six ablation presets.

**Computer-use specific:** nothing is integrated. The only tested computer-relevant code is a file-existence/size predicate and a text-file helper, both unit-tested and not called by the agent.

## C. What remains incomplete

- **Prototype, not integrated:**
  - PyAutoGUI mouse, keyboard and screenshot (interface-only test);
  - psutil process listing;
  - the file helper (no path confinement).
- **Proposed, no code:**
  - accessibility-tree grounding (UIA, AX, AT-SPI);
  - window operations;
  - native application control;
  - file actions with typed postconditions;
  - process launch and terminate;
  - the `action_gate` node with permission tiers;
  - action-bound approvals and a hash-chained audit log;
  - a modality router for cross-environment tasks.
- **Partial:**
  - the `alternative_selector` and `replan` recovery strategies (labels only);
  - per-step postconditions (dispatch-based);
  - evidence integrity.

## D. Existing evidence (measured in this session)

1. **Browser completion-gate component study**, 38 design states and 12 held-out, run directly and inside the live `verify` node:

   | | Unsatisfied states withheld | Satisfied states rejected |
   |---|---|---|
   | Design set, before fixes | 13–15 of 23 | 3 of 15 |
   | Design set, after fixes | 20 of 23 | 1 of 15 |
   | Held-out, after fixes | 2 of 5 (1 before) | 1 of 7 |

   Median latency is 30.6 ms per decision.
2. **Routing resolution** without inference, before and after the fixes.
3. **Test suite:** 129 tests, 126 pass (the 3 failures need live web); Observatory 20/20; coverage 65.0%.

None of these involves a language model, a live website or any computer-use action.

## E. Missing evidence (needed for stronger computer-use claims)

- **Browser family** end-to-end with local models, measuring success, FCR, FRR, latency, actions and model calls, recovery, vision use, evidence completeness and interventions. Runnable now with `python main.py --eval` plus an author-written task list and oracles.
- **Desktop app, file, process/window and cross-environment families.** These need the computer backend first.
- **Safety and prompt-injection tasks**, OS-Harm-style, measuring safety violations and approval adherence.
- **Ablations:** no gate, no recovery, vision-only, single model, no memory; for the desktop, accessibility-first vs vision-only.
- **Comparisons:** against a model-based completion judge and against planner self-report.
- **Labelling:** fixtures labelled by people who do not know Φ, ideally sampled from real trajectories.

## F. Claims weakened or removed

- "Local **Autonomous AI Agent Framework** for **Privacy-Preserving** … Automation" (old title) is now "**Toward** a local computer-use agent". Privacy is stated only as "model inference stays on the host by default".
- "Backend-independent control loop" (first draft of contribution 2) is now "the loop's observation and execution nodes are bound to the browser".
- The desktop "extension" is no longer presented as an extension of the system. It is a proposed backend with an explicit list of what exists (an unintegrated prototype).
- "Evaluation protocol the harness is prepared to run" is now "whose browser part the harness can already run".
- The safety section now states "we make no security claim about the current system". Proposed controls are labelled proposed and unmeasured.
- Browser results are explicitly scoped: "all results concern the browser backend and its components; none measures end-to-end task success, and none involves the computer backend".
- No claim of being the first agent of any kind. Novelty is limited to the in-loop, evidence-recorded, measured completion gate plus the audit methodology.

## G. Final contribution (strongest defensible)

Agentic Pilot makes task completion a checked property of the observed environment rather than the model's claim. This is formulated across browser, desktop, file and process state, implemented and logged as evidence in a local browser agent, and measured with false-completion and false-rejection rates. A component study inside the live verification loop, with held-out cases, quantifies how far rule-based completion predicates prevent premature completion, and where they fail to generalize. A capability audit and a concrete design (typed postconditions plus deterministic pre-action permission tiers) define the path to a verifiable local computer-use agent.

## H. Biggest reviewer risks

1. **No end-to-end evaluation.** No task has been run with a language model, so success, FCR and FRR on real tasks are unknown.
2. **The computer-use framing outruns the implementation.** The computer backend is a design plus an unintegrated prototype, so a reviewer may see the title and framing as premature.
3. **Weak experimental validity.** The fixtures and labels are author-written, the fixes were tuned on the design set, the held-out set is small (12 states, 5 unsatisfied), and there is no model-judge baseline.
4. **Hand-written, wording-keyed browser predicate.** It is brittle, reduces to an error check when no keyword fires, and on the held-out set it generalized only modestly.
5. **The safety posture is design-only.** Approval is per task and model-labelled, the sanitizer is a denylist, there is no authentication or evidence integrity, and the anti-detection browser settings raise ethical questions. None of the proposed controls is implemented or measured.
