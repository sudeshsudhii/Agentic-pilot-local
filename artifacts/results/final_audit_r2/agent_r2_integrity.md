# R2 Research Integrity Audit — Agentic Pilot paper

Auditor: Agent 4 (Research Integrity). I edited no repository files.
Scope: every file under `paper/sections/*.tex`, `paper/tables/*.tex`, `paper/tables/sim/*.tex` and `paper/figures/*.tex`; `references.bib`; `main.pdf` (built 2026-10-24 01:51, newer than every source). I also checked the claims against the repository: git history, `artifacts/results/final_audit/changed_numbers_ledger.csv`, `benchmarks/simulation/out/heldout_v2/ledger_simulation.csv` and `artifacts/results/simulation_validation_report.md`.

Evidence classes required: ACTUAL, SYNTHETIC, ASSUMED, DERIVED, LITERATURE, PROPOSED.

## Summary of checks

| Check | Result |
|---|---|
| (a) SYNTHETIC/ASSUMED readable as actual performance | 6 Major, 4 Minor (F2, F7–F11, F18, F21, F25, F26) |
| (b) PROPOSED described as implemented | No substantive case found. The architecture figure, Appendix A, Table post and Table status all mark designs correctly. Minor: F22, F23 |
| (c) Recomputation confusable with independent annotation, ground truth or replication | 1 Critical (F1), 2 Major (F5, F6) |
| (d) Label inconsistencies across abstract, intro, hypotheses table, results, discussion and conclusion | 2 Major (F3, F4), several Minor |
| (e) Synthetic significance used to support a real-world hypothesis | No explicit case. Implicit cases: F2 (abstract), F3 (conclusion), F15 (05b "tested") |
| (f) Disclosure of post-hoc simulation v2 | Disclosed (06:34, 10:10, 07b box, abstract), but incomplete: the direction of the changes and the second correction are not stated (F12) |
| (g) Accuracy of the AI-assistance acknowledgment | Inaccurate and incomplete (F1) |
| (h) Citations | All 47 `\cite` keys exist in references.bib; no bib entry is uncited; bibtex reports 0 warnings. A few attributions are unverified (F27) |
| Six-class scheme / ASSUMED | The paper names five classes. ASSUMED appears only in table cells and captions, never as a class in the text. LITERATURE is defined but never applied. The `\status{}` macro is defined in main.tex but unused (F4) |
| Physical hardware presented as pending or a blocker | None. The end-to-end run is attributed to model weights that could not be downloaded, not to hardware. Pass |

---

## Findings

### F1 — Critical — (g)/(c) The acknowledgment understates the AI's role, and "one author" wrote the oracle labels
- **Files:** `sections/12_conclusion.tex:7`, `sections/06_methodology.tex:11`, `sections/10_limitations.tex:4`
- **Quoted:**
  - 12:7 "An AI system (Anthropic's Claude) assisted with analyzing the source code, implementing the experiment harness, running the reported component experiments, searching and checking references, and drafting the text of this paper. The authors reviewed, verified and revised all content and take full responsibility for it."
  - 06:11 "Its limitation is that one author wrote all states and labels, so no inter-annotator agreement exists"
  - 10:4 "One author wrote all gate states and labels and designed the fixes on the design states"
- **Why:** The git history shows that the AI agent (commit author "Claude"), not a human author, committed the following:
  - all gate-state and oracle-label files: `artifacts/experiments/verification_gate_study.py` (commits 48b2976, 08653e2, b55670b) and `gate_heldout2.py` (b9d5088, the freeze commit);
  - the agent-code fixes and the locality enforcement: `backend/` commits 5359458 and 55ac1ea;
  - the e2e tasks and oracle (55ac1ea, bf0a8a5);
  - the whole simulation and its assumed parameter values (3a0aa8e, 41a6097, bbd7be5, aee8c50);
  - the "validation agent" report, whose own header reads "Independent validation report ... (Agent 4)";
  - the bibliography, which its header says was "Compiled by the Literature Scout sub-agent";
  - all 24 commits under `paper/`.

  The oracle labels are the ground truth for every ACTUAL gate number. Calling their writer "one author" while the acknowledgment lists only "analysis, harness, running experiments, references, drafting" misattributes who annotated them. It also hides the fact that the labeller, the person who designed the gate fixes, and the system being evaluated came from the same AI pipeline. The acknowledgment also omits that the AI changed the code under evaluation and designed the simulation and its ASSUMED values. Finally, "verified ... all content" cannot be checked; if the human author did not independently check the labels, the sentence overstates.

  If the human author in fact wrote or rewrote the states and labels, the authors must say so explicitly. The repository history indicates otherwise.
- **Replacement (12:7):**
  > An AI system (Anthropic's Claude, run as a set of coding, analysis and writing agents) did most of the technical work reported here. It analyzed the source code; implemented the agent fixes and the locality enforcement of Section~\ref{sec:impl}; wrote the constructed gate states and their oracle labels, and the end-to-end tasks, sites and oracle; designed and implemented the simulation and proposed its assumed parameter values; ran all reported experiments; performed the methodology audits and the recomputation checks of Section~\ref{sec:sim} (the ``validation agent'' and ``final reviewer'' there are AI agents, not people); compiled and checked the references; and drafted the text. The human author [state precisely what was done, e.g.\ defined the research goals, reviewed the code changes, spot-checked N of the 92 gate labels, and revised the text]. The authors take full responsibility for the content.
- **Replacement (06:11, last sentence):**
  > Its limitation is that all states and labels were written by the AI agent that also designed the gate fixes (Acknowledgment), and no human or second annotator has relabelled them, so no inter-annotator agreement exists; a protocol for independent relabelling with Cohen's $\kappa$~\cite{cohen1960coefficient} is in the repository.
- **Replacement (10:4, first sentence):**
  > The same AI agent wrote all gate states and labels and designed the fixes on the design states, so the design results are optimistic.

### F2 — Major — (a)/(e)/(d) The abstract's simulation sentence reads as a performance result and omits "by construction"
- **File:** `sections/00_abstract.tex:2`
- **Quoted:** "\emph{In a seeded simulation} built on these measurements and stated assumptions, the gate reduced episode-level false completions (19 against 28 of 100 synthetic scenarios) but did not significantly improve decision accuracy (52 against 46 of 74 claims, $p=0.15$); these outcomes are conditional on the assumptions of a model corrected after an audit."
- **Why:**
  - "The gate reduced" is an active performance verb. The structure "reduced ... but did not significantly improve" implies that the first effect was a significant empirical finding, yet 07b:13 states that its direction is fixed by construction (one discordant cell is always 0).
  - "74 claims" lacks the word "synthetic".
  - "A model corrected after an audit" does not tell the reader that the correction was made after the first results were known and is not pre-registered.
  - The abstract is therefore inconsistent with the hypotheses table ("lower by construction") and with 07b:13.
- **Replacement:**
  > \emph{In a seeded simulation} built on these measurements and on assumed planner behaviour, the configuration with the gate ended in fewer false completions (19 against 28 of 100 synthetic scenarios, a direction fixed by construction) and its decision accuracy did not differ significantly from accepting every claim (52 against 46 of 74 synthetic claims, $p=0.15$); these values follow from the assumptions of a simulation model revised post hoc, after its first results were known, and are not measurements of the agent.

### F3 — Major — (d)/(e) The conclusion credits the simulation with findings that come from ASSUMED rates of PROPOSED components
- **File:** `sections/12_conclusion.tex:4`
- **Quoted:** "\emph{Simulated, conditional on stated assumptions:} the gate's benefit depends on how often the planner claims completion prematurely and is paid for in false rejections, and memory and recovery would need a relevance filter and an explicit confirmation check."
- **Why:** 05b:4, 07b:27 and 07b:33 all say that the simulated effects of the relevance filter (20 vs 19 of 44) and of guided recovery (87 vs 68) follow only from assumed rates and are "not evidence". The conclusion turns them into a simulated finding. The actual basis for the two needs is ACTUAL:
  - the store returns irrelevant top-1 records in 3 of 10 queries;
  - the engine classifies a missing confirmation as unknown.
- **Replacement:**
  > \emph{Simulated, conditional on stated assumptions:} the gate's benefit depends on how often the planner claims completion prematurely and is paid for in false rejections. Component measurements, not the simulation, show that memory retrieval has no relevance threshold and that recovery does not recognize a missing confirmation; the simulated gains of a relevance filter and a confirmation check follow from their assumed rates and are not evidence for them.

### F4 — Major — (d) The paper names five evidence classes, omits ASSUMED, and applies its labels inconsistently
- **Files:**
  - `sections/06_methodology.tex:28`
  - `tables/sim/params.tex:11,20,23`
  - `sections/01_introduction.tex:21`
  - `sections/05b_hypotheses.tex:8`
  - `sections/07b_simulation.tex:4`
  - `main.tex:21` (`\status` defined, never used)
- **Quoted (06:28):** "Its outputs follow from two kinds of input, and every number in this paper carries one of five classes: \textsc{actual} (measured on the implementation), \textsc{derived} (computed from actual measurements), \textsc{synthetic} (produced by the simulation), \textsc{literature}, or \textsc{proposed} (behaviour of an unimplemented component)."
- **Why:** The sentence itself says that the outputs come from measured and *assumed* inputs, yet ASSUMED is not one of the listed classes. The labels in use are inconsistent:
  - Table sim-params uses ASSUMED (16 cells), plus "design", "ASSUMED rate" and "ASSUMED; from Study E".
  - The intro and the hypotheses-table caption use "\textsc{simulation}", which is not a class.
  - The sim captions use "Simulation-based (synthetic)".
  - The narrative never uses \textsc{assumed} or \textsc{derived}; LITERATURE is never applied.
  - The evidence ledger the paper cites (`ledger_simulation.csv`) uses only ACTUAL and SYNTHETIC. It classifies the PROPOSED-component values (enhanced validation, guided recovery, filter) as plain SYNTHETIC.
  - "Every number ... carries one of five classes" is also not literally true: many numbers in the text carry no explicit label.
- **Replacement (06:28, from "Its outputs follow ..." to the end of the paragraph):**
  > Its outputs follow from measured and assumed inputs. Every number in this paper belongs to one of six classes: \textsc{actual} (genuinely executed or measured on the implementation), \textsc{synthetic} (produced by the simulation), \textsc{assumed} (an input value chosen by us, not measured), \textsc{derived} (computed from existing results, e.g.\ a rate estimated from actual counts), \textsc{literature} (taken from cited work), or \textsc{proposed} (behaviour of a component that is not implemented, or an evaluation not yet done). Tables and figures state the class of their values in the caption or row label; in the text, numbers in Sections~\ref{sec:results} and~\ref{sec:safety} are \textsc{actual} unless stated, and numbers in Section~\ref{sec:sim-results} are \textsc{synthetic} unless marked otherwise. An evidence ledger lists every simulated value in the main tables with its source and class.
- **Also:**
  - Replace "\textsc{simulation}-based" in 01:21 with "\textsc{synthetic} (simulation-based)".
  - Replace "outcome in the \textsc{simulation}" in 05b:8 with "\textsc{synthetic} outcome in the simulation".
  - In params.tex, change "design" (line 11) to "ASSUMED (design choice)", "ASSUMED rate" (line 20) to "ASSUMED", and "ASSUMED; from Study E" (line 23) to "ASSUMED; SYNTHETIC (output of Study E)".
  - Regenerate the ledger so that its proposed-component rows read "SYNTHETIC (PROPOSED component, ASSUMED rates)" (repository change, outside the paper).
  - Use the existing `\status{}` macro for every class mention, so that the typography is uniform.

### F5 — Major — (c) The "validation agent", "final reviewer" and "independent validator" can be read as human or independent replication
- **Files:** `sections/06_methodology.tex:45`, `sections/14_simparams.tex:4`
- **Quoted:**
  - 06:45 "For v1, a separate validation agent in the same authoring pipeline recomputed, with separately written code ..."
  - 06:45 "For v2, a final reviewer recomputed with separately written code ..."
  - 14:4 "the independent validator of v1 contains absolute paths of the machine it ran on."
- **Why:** 06:45 rightly says that the check "is neither independent human annotation ... nor an independent replication". But:
  - "final reviewer" reads as a human reviewer;
  - "validation agent" does not say it is an AI;
  - 14:4 calls the script "independent".
  
  The repository file is titled "Independent validation report" and the script is `independent_validator.py`, which a reader following the paper's pointers will see. All of these were AI agents of the same pipeline that built the simulation.
- **Replacement (06:45, two phrases):** "a separate AI agent of the same authoring pipeline, given only the per-scenario output files, recomputed ..." and "For v2, a final AI review agent of the same pipeline recomputed with separately written code ..."
- **Replacement (14:4, last clause):** "the v1 recomputation script (\texttt{independent\_validator.py}, an AI-written arithmetic check, not an independent replication) contains absolute paths of the machine it ran on."
- **Recommendation (repository, not the paper):** retitle `simulation_validation_report.md` to "Recomputation check (AI agent, same pipeline)".

### F6 — Major — (c) "An oracle written independently of Φ"
- **File:** `sections/03_problem.tex:13`
- **Quoted:** "$\Phi^{\star}$ an oracle written independently of $\Phi$ (Section~\ref{sec:method})"
- **Why:** In the gate study the oracle labels were written by the same agent that designed Φ's fixes (06:11, 10:4, F1). "Written independently" can be read as independent annotation. What is true is code and input independence.
- **Replacement:** "$\Phi^{\star}$ an oracle that shares no code or inputs with $\Phi$ (written by the same author as $\Phi$'s fixes; Section~\ref{sec:method})".

### F7 — Major — (a) Policy-level synthetic outcomes are phrased as the system completing tasks
- **Files:** `sections/07b_simulation.tex:15`, `sections/07b_simulation.tex:21`
- **Quoted:**
  - 07b:15 "At the policy level, $\Phi$ completes 44 tasks against 46 without verification (3 successes only without verification, 1 only with $\Phi$; $p=0.63$): false rejections cost 3 successes, and continuation after a correct rejection recovers 1."
  - 07b:21 "Disabling the recovery engine, with the retries before it still in place, lowers TSR from 0.44 to 0.41 (3 successes lost, none gained; $p=0.25$)"
- **Why:** The section box labels these values, but each sentence on its own states that Φ "completes tasks" and that disabling the engine "lowers TSR". The paper elsewhere stresses that it makes no claim about task success (01:32, 07:37). Sentences get quoted out of context.
- **Replacement (07b:15):**
  > At the policy level, the simulated $\Phi$ configuration ends with 44 of 100 synthetic scenarios achieved and reported, against 46 without verification (3 only without verification, 1 only with $\Phi$; $p=0.63$): in the simulation, false rejections cost 3 successes and continuation after a correct rejection recovers 1.
- **Replacement (07b:21):**
  > In the simulation, disabling the recovery engine, with the retries before it still in place, lowers synthetic TSR from 0.44 to 0.41 (3 successes lost, none gained; $p=0.25$)

### F8 — Major — (a) Simulated recovery numbers attributed to "the engine", and the table row labelled "(impl.)"
- **Files:** `sections/07b_simulation.tex:33`, `tables/sim/recovery.tex:12`
- **Quoted:**
  - 07b:33 "the retries before the engine recover 51 of 93 recoverable failures, and the engine raises this to 68 of 93."
  - 07b:33 "The engine spends 174 attempts on permanent failures, the guided variant 162."
  - Table row: "Engine on (impl.)"
- **Why:** The values 51, 68 and 174 are SYNTHETIC. They are determined by ASSUMED per-attempt success rates (Table sim-params row "Recovery success per attempt ... ASSUMED"). "The engine raises this" and "(impl.)" read as measured behaviour of the implemented engine. Only the entry paths and strategy sequences are ACTUAL.
- **Replacement (07b:33):**
  > Simulated along these paths with assumed per-attempt success rates (Table~\ref{tab:sim-recovery}), the retries before the engine recover 51 of 93 synthetic recoverable failures, and adding the engine raises this to 68 of 93.
  
  and "In the simulation the engine spends 174 attempts on permanent failures, the guided variant 162."
- **Replacement (table row):** "Engine on (as implemented; simulated)".

### F9 — Major — (a) "Measured misleading rate" — the mapping to "misleads the planner" is assumed
- **Files:** `sections/07b_simulation.tex:27`, `tables/sim/memory.tex:16`, `tables/sim/params.tex:25`
- **Quoted:**
  - 07b:27 "With that measured misleading rate, the simulated repeated workflows succeed 19 times of 44 with and without memory"
  - Table: "0.30 (meas.)"
- **Why:** What was measured is the share of queries whose top-1 record is irrelevant or a failed attempt (3/10, on a synthetic corpus). The memory table caption defines P(misleading) as the "probability that the retrieved context misleads the planner". Treating the first as the second is an ASSUMED mapping with no model in the loop. The label "measured" makes the H3 result look grounded in observation.
- **Replacement (07b:27):** "With a misleading rate set to the measured share of irrelevant top-1 records (3/10; that this share equals the probability of misleading the planner is assumed), the simulated repeated workflows succeed 19 times of 44 with and without memory"
- **Replacement (table cells):** "0.30 (derived; mapping assumed)" in memory.tex; "DERIVED (mapping ASSUMED) / PROPOSED" in params.tex:25.

### F10 — Major — (a)/(d) DERIVED rates that rest on assumed proxies and category mappings
- **Files:** `sections/06_methodology.tex:30`, `tables/sim/params.tex:16,17,29`
- **Quoted:**
  - 06:30 "Simulated categories map to gate categories as follows: ... data entry to text entry, and form submission to text entry and multi-step pooled. The detection rate of a missing confirmation is proxied by the multi-step rate, which rests on 3 states."
  - params:29 "Missing-confirmation detection: retry / guided & 0.63 / 0.9 & DERIVED / PROPOSED"
- **Why:** The k/n counts are ACTUAL. Two things are not:
  - the choice of proxy (missing confirmation ≈ multi-step);
  - the category mapping (form submission ≈ text entry + multi-step).
  
  Both are ASSUMED. Labelling the resulting rates purely DERIVED overstates their empirical grounding, and they drive the H4 and false-completion results. 0.63 rests on 3 states.
- **Replacement (06:30, last sentence):** "The detection rate of a missing confirmation is proxied by the multi-step rate (an assumed proxy; 3 states), and the category mapping above is likewise assumed."
- **Replacement (params, Class column):**
  - row 16: "DERIVED (mapping ASSUMED)"
  - row 17: "DERIVED (mapping ASSUMED)"
  - row 29: "DERIVED via ASSUMED proxy / PROPOSED"

### F11 — Major — (a) "Inside the live loop" / "inside the agent loop" overstates how the gate was exercised
- **Files:** `sections/12_conclusion.tex:4`, `sections/08_discussion.tex:4`; also `sections/00_abstract.tex:2`, `sections/01_introduction.tex:20`, `sections/07_results.tex:11` ("live verification node")
- **Quoted:**
  - 12:4 "inside the live loop the predicate withheld most premature completions on the states it was designed on and 41\% on states frozen before testing"
  - 08:4 "A rule over observed state, evaluated inside the agent loop, withholds a significant share of premature completions"
- **Why:** 06:13 describes the actual setup: the real verification node was called directly, with database, browser-pool and evidence I/O stubbed, an empty or generic planner reasoning, and hand-constructed end states. No agent episode, planner or loop produced these states. "Inside the live loop" and "evaluated inside the agent loop" can be read as measurements taken during agent runs, which the paper says were never executed.
- **Replacement (12:4):** "in the agent's real verification node, called directly on constructed states with stubbed I/O, the predicate withheld most premature completions ..."
- **Replacement (08:4):** "A rule over observed state, run in the agent's real verification node on constructed states, withholds ..."
- **Also:** in 00:2 and 01:20, change "inside the agent's live verification node" to "in the agent's real verification node (called directly, with stubbed I/O)".

### F12 — Major — (f) The post-hoc v2 is disclosed, but not the direction of the changes or the second correction
- **Files:** `sections/06_methodology.tex:32,34`, `sections/10_limitations.tex:10`
- **Quoted:**
  - 06:32 "Parameters and code were committed (\texttt{3a0aa8e}) before the reported held-out set (seed 202, 100 scenarios) was generated"
  - 06:34 "It was written after the v1 results were known and is therefore \emph{not pre-registered}; v1's outputs are archived ... and every number that changed is listed in the statistical correction report"
  - 10:10 "The reported model (v2) was corrected after its first results and an audit were known"
- **Why:**
  - **Positive:** the disclosure is clear that v2 is post hoc and not pre-registered. The 07b box says "(v2, post hoc)".
  - **Gap 1:** 06:32 says parameters were frozen "before the reported held-out set was generated". That freeze applies to v1, but the *reported* numbers come from v2, so a reader can take 06:32 as pre-registration of the reported results.
  - **Gap 2:** the paper does not say in which direction the corrections moved the results. Per `final_audit/changed_numbers_ledger.csv`:
    - Φ vs no-verification task success went from 37 vs 43 (v1, $p=0.07$) to 44 vs 46 ($p=0.63$);
    - Φ decision accuracy went from 45/71 vs 43/71 ($p=0.80$) to 52/74 vs 46/74 ($p=0.15$);
    - Φ's false-rejection input fell from 0.089 to 0.02.
    
    Every listed change for Φ moved in the gate's favour. Readers need this to judge the researcher-degrees-of-freedom risk.
  - **Gap 3:** v2 itself was corrected a second time after the final review (06:45, recovery entry paths; commit aee8c50). 10:10 mentions only one correction.
- **Replacement (06:32, first clause):** "For v1, parameters and code were committed (\texttt{3a0aa8e}) before the held-out set (seed 202, 100 scenarios) was generated; the reported results come from the post-hoc v2 described below."
- **Add after "...not pre-registered;" in 06:34:**
  > the corrections moved the results for $\Phi$ in its favour (task success relative to no verification from 37 against 43, $p=0.07$, to 44 against 46; decision accuracy from 45/71 against 43/71 to 52/74 against 46/74), mainly because v1's false-rejection rate (0.089) came from bot-check pages;
- **Replacement (10:10, sentence 4):**
  > The reported model (v2) was revised twice after its first results were known (after a methodology audit, and again after a final review of the recovery paths), so it is not pre-registered; the corrections bring it closer to the code and moved the results in favour of $\Phi$, but the choice of what to correct was made with the results in view.

### F13 — Minor — (d) Intro contribution 3 credits ACTUAL shortfalls to the simulation and calls it an "evaluation of H1–H5"
- **File:** `sections/01_introduction.tex:21`
- **Quoted:** "A seeded, \textsc{simulation}-based evaluation of H1--H5, with inputs measured on the implementation and every assumption stated, which indicates, under those assumptions, the trade-off between false completions and false rejections and where the implementation falls short---memory without a relevance threshold, recovery blind to missing confirmations"
- **Why:**
  - "Memory without a relevance threshold" and "recovery blind to missing confirmations" are ACTUAL findings from measurement and code inspection, not simulation outputs.
  - "Evaluation of H1–H5" implies hypothesis testing.
  - "\textsc{simulation}" is not a class.
- **Replacement:**
  > A seeded simulation (\textsc{synthetic}) of H1--H5, with inputs measured on the implementation and every assumed value stated, which shows under those assumptions the trade-off between false completions and false rejections; measurements made for it (\textsc{actual}) show that memory retrieval has no relevance threshold and that recovery does not recognize a missing confirmation (Section~\ref{sec:sim-results}).

### F14 — Minor — (d)/(e) Hypotheses table: "enhanced: yes", H3 wording, and no ACTUAL column
- **File:** `sections/05b_hypotheses.tex:17,18` (and caption line 8)
- **Quoted:**
  - H2 cell: "enhanced: yes by assumption"
  - H3 cell: "not supported; underpowered (19 vs 19 of 44)"
- **Why:**
  - "Yes" reads as hypothesis support.
  - "Not supported" for H3 conflicts with 07b:27 ("uninformative about H3 rather than evidence against it").
  - 05b:4 says H1/H2 have ACTUAL component evidence, but the table shows only synthetic outcomes. A reader comparing p=0.021 (ACTUAL, gate vs dispatch on held-out 2) with p=.15 (SYNTHETIC) gets no reconciliation.
- **Replacements:**
  - H2 cell: "for $\Phi$: no significant difference at $n{=}74$ synthetic claims (.70 vs .62, $p{=}.15$ cond.); enhanced: follows from assumed rates, no evidence"
  - H3 cell: "uninformative; underpowered (19 vs 19 of 44)"
  - Append to caption: "Component-level \textsc{actual} evidence bearing on H1/H2 (Section~\ref{sec:res-gate}): on held-out~2 the gate withholds 9 of 22 unsatisfied states and rejects 1 of 20 satisfied ones (exact McNemar against dispatch-only $p=0.021$); it concerns constructed states, not agent episodes."

### F15 — Minor — (e) "Each is tested here only by simulation"
- **File:** `sections/05b_hypotheses.tex:4`
- **Quoted:** "At the level of the full agent each is tested here only by simulation (Section~\ref{sec:sim}), which shows what the hypotheses imply under stated assumptions"
- **Why:** A simulation cannot test a hypothesis about the agent. "Tested" invites reading the synthetic p-values as tests.
- **Replacement:** "At the level of the full agent each is examined here only in simulation (Section~\ref{sec:sim}), which cannot test it but shows what it implies under stated assumptions"

### F16 — Minor — (d) The Section 07b box classes assumed values as synthetic
- **File:** `sections/07b_simulation.tex:4`
- **Quoted:** "All values in this section except those marked \textsc{actual} are \textsc{synthetic}"
- **Why:** The section also states ASSUMED inputs (3 s per call, π = 0.3 to 0.95, gain 0.08), DERIVED rates and PROPOSED-component outputs.
- **Replacement:** "All values in this section are \textsc{synthetic} unless marked \textsc{actual} or stated as \textsc{assumed} inputs; rows marked $^{\ddagger}$ are \textsc{proposed} components simulated with assumed rates."

### F17 — Minor — (b)/(d) The gate code changed after the held-out-2 freeze by more than configuration switches
- **File:** `sections/06_methodology.tex:9`
- **Quoted:** "afterwards only configuration switches for the ablation were added to the gate code, which leave its default behaviour unchanged."
- **Why:** Commit 55ac1ea, after freeze commit b9d5088, added the ablation switches. In the same file (`backend/verification/manager.py`) it also added a new `self_verify_completion` method, used for the self-verification baseline. I checked the diff: default Φ behaviour is unchanged, so the claim holds in substance, but the sentence is incomplete.
- **Replacement:** "afterwards only configuration switches for the ablation and a separate self-verification baseline method were added to the gate code; neither changes the gate's default behaviour (diff \texttt{b9d5088..55ac1ea})."

### F18 — Minor — (a) "Because Φ fails closed" explains an effect that comes from an ASSUMED rate of 0.8
- **File:** `sections/07b_simulation.tex:46`
- **Quoted:** "missing evidence raises FRR (0.09 to 0.22) because $\Phi$ fails closed on an unreadable page"
- **Why:** Table params row 20 sets the simulated rejection rate on missing evidence to 0.8 (ASSUMED). Deterministic fail-closed behaviour would be 1.0.
- **Replacement:** "missing evidence raises FRR (0.09 to 0.22) because the simulated $\Phi$ rejects a claim on an unreadable page with assumed probability 0.8"

### F19 — Minor — (e) The table's H1 p-value lacks the structural-zero caveat
- **File:** `tables/sim/tests.tex:3,11`
- **Quoted:** "None & 9/0 & 0.00391"
- **Why:** 07b:13 says that one cell is always 0 and that the p-value is not informative, but the table, which is what readers excerpt, does not.
- **Replacement (append to caption):** "For FC against None and Basic, $c=0$ by construction ($\Phi$ only withholds claims), so those $p$-values carry no information about direction."

### F20 — Minor — (a) "Held-out scenarios" for synthetic data
- **Files:** `sections/07b_simulation.tex:11`, `tables/sim/baseline.tex:3`
- **Quoted:** "compares four completion rules on the same 100 held-out scenarios"
- **Why:** The term is shared with the ACTUAL held-out gate sets (held-out 1 and held-out 2) and suggests held-out real data.
- **Replacement:** "on the same 100 scenarios of the reported synthetic set (seed 202)"

### F21 — Minor — (a) The abstract leads with design-state figures, and "27 ms" lacks context
- **File:** `sections/00_abstract.tex:2`
- **Quoted:** "the gate withheld 20 of 23 unsatisfied design states (95\% interval 0.68--0.95) ... A decision costs a median of 27\,ms and no model call."
- **Why:**
  - "Design states" is undefined in the abstract.
  - 07:11 says these states are circular, because the fixes were designed on them, yet an interval is given as if they were an estimate.
  - 27 ms was measured on constructed states on a 2.1 GHz machine; on the self-hosted sites it is 5.2 ms.
- **Replacement:** "the gate withheld 20 of 23 unsatisfied states of the set its fixes were designed on (an optimistic figure) ... A decision on the constructed states costs a median of 27\,ms and no model call."

### F22 — Minor — (b)/(d) The related-work footnote conflicts with the status table on memory
- **File:** `tables/related_work.tex:30`
- **Quoted:** "$^{d}$Implemented; studied only by simulation."
- **Why:** Table status gives "Memory store retrieval (Chroma, SQLite) IE, C (10 queries, synthetic corpus), S", so retrieval was measured (ACTUAL).
- **Replacement:** "$^{d}$Implemented; retrieval measured on 10 queries over a synthetic corpus, effect on tasks studied only by simulation."

### F23 — Minor — (b) The status table lists the e2e harness as "experimentally evaluated"
- **File:** `tables/status.tex:14`
- **Quoted:** "End-to-end harness and oracle $\Phi^{\star}$ & IE & O (114 trajectories)"
- **Why:** Only the oracle was evaluated. The harness has not been run with a model; it ran only with a stand-in, in the egress test.
- **Replacement:** split into two rows: "End-to-end oracle $\Phi^{\star}$ & IE & O (114 trajectories)" and "End-to-end harness (run with a language model) & IN & E (stand-in only)".

### F24 — Minor — (a) "The held-out sets give the honest estimate"
- **File:** `sections/07_results.tex:13`
- **Why:** 10:4 says the author of held-out 2 knew the gate's rules, so this estimate is less biased, not unbiased.
- **Replacement:** "The held-out sets give a less optimistic estimate."

### F25 — Minor — (a) The title implies demonstrated task automation
- **File:** `main.tex:28`
- **Quoted:** "Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation"
- **Why:** No task was executed end to end, and the privacy property holds only in the narrow sense of Section~\ref{sec:safety}.
- **Suggested:** "Agentic Pilot: Evidence-Gated Completion for a Local Browser Agent, with Component Measurements and a Simulation Study"

### F26 — Minor — (d) The Discussion omits the simulation evidence and the H2 reconciliation
- **File:** `sections/08_discussion.tex:4`
- **Why:** The abstract and conclusion present three evidence tiers; the Discussion covers only ACTUAL. That is acceptable, but a reader may then take "What the evidence supports" as covering everything.
- **Add at end of 08:4:** "The simulation (Section~\ref{sec:sim-results}) adds no empirical support; it shows that under the stated assumptions the benefit of the gate depends on the unmeasured premature-claim rate and is paid for in false rejections."

### F27 — Minor — (h) Citations
- **Keys:** All 47 `\cite` keys in the sources exist in `references.bib`. No entry is unused. `main.blg` reports 0 warnings, and the PDF has no undefined references.
- **Plausible from my knowledge (not fetched):** ReAct, Reflexion, Toolformer, CoT, RCI, Voyager (model-based self-verification), WebArena, VisualWebArena, WorkArena, Mind2Web (MindAct ranker + LLM), WebVoyager (GPT-4V judge), SeeAct (grounding bottleneck), OSWorld, WAA, UFO, Agent S, AppAgent, CogAgent, SeeClick, UI-TARS, OmniParser, RAG, SBERT, Generative Agents, MemGPT, Greshake, Liu et al. (defenses insufficient), InjecAgent, AgentDojo, ToolEmu, OS-Harm, CaMeL, Huang et al. (self-correction), Pan et al. (evaluators to judge/refine), Lukas et al. (PII leakage), and the statistics references (Wilson, Clopper–Pearson, McNemar, Efron, Cohen).
- **Unverified:**
  - `sumyk2025done` (arXiv:2511.20067): "train a completion judge for macOS applications" (02:8). Check that it is trained and macOS-specific.
  - 02:6 `\cite{zheng2024seeact,yang2023som}` attributes SeeAct's "grounding is the bottleneck" finding jointly to Set-of-Mark. Suggest: "SeeAct finds grounding to be the bottleneck~\cite{zheng2024seeact}, which Set-of-Mark prompting addresses~\cite{yang2023som}".
  - 02:10 "Open-weight models such as Qwen2.5 and Qwen2-VL run on consumer hardware~\cite{yang2024qwen25,wang2024qwen2vl,lin2024awq}". The Qwen reports describe small model sizes; the consumer-hardware claim is supported mainly by AWQ. Suggest: "are released in sizes that, with 4-bit quantization~\cite{lin2024awq}, run on consumer hardware".
  - Table related_work cells: WebArena "Deploy. H", SeeAct "Deploy. P", WebVoyager "Evid. Y", UFO "Mem. P". Check against each paper, since the caption says "from what each paper reports".

---

## Items checked and found compliant
- Physical hardware is never presented as pending or a blocker; the reason given for the missing e2e run (07:37, 06:28) is unavailable model weights.
- Designs are labelled as designs (03:9, 01:13, Appendix A, Table post, Fig. arch caption): the desktop/computer backend, action gate and permission tiers. The PROPOSED sim components carry ‡ and "Not implemented".
- 07:4 and 07:37 correctly state that no end-to-end task success was measured. The 70-episode egress test is described with its stand-in and its uninstrumented processes (07:30, 09:6).
- The gate McNemar correction (an earlier withheld-only test) is disclosed (06:13). Design-set tests are withheld as circular (07:11).
- Synthetic p-values are stated as conditional in every simulation caption, in 06:41 and 10:10. H1 "consistent with, not empirical confirmation" (07b:13) and the H4/enhanced "by assumption" disclaimers (05b:4, 07b:15, 07b:33) are good.
- 06:45 explicitly says that recomputation is neither human annotation nor replication; only the actor descriptions need fixing (F5).
- The agent code freeze claim holds: `git diff bf0a8a5 HEAD -- backend/` is empty. The egress run on an uncommitted tree based on 1435fe9 is disclosed (07:30).
