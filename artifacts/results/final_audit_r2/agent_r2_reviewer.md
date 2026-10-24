# Independent Review (Agent 7, round 2)

**Paper:** "Agentic Pilot: An Evidence-Driven Local Autonomous AI Agent Framework for Privacy-Preserving Intelligent Task Automation"
**Sources reviewed:** `paper/main.tex`, `sections/*.tex`, `tables/*.tex`, `tables/sim/*.tex`, `figures/*.tex`, `references.bib`. I rebuilt the PDF from a copy (`sh build.sh`): it has 17 pages, the text of every page matches the committed `main.pdf`, all 47 references are cited, and there are no BibTeX warnings and no undefined references.
**Data checked:** `artifacts/results/gate_stats.csv`, `verification_gate_cases.csv`, `verification_gate_cases_before_fixes.csv`, `e2e_oracle_validation.txt`, `pytest_revision.txt`, `e2e_smoke_stub/*`, `benchmarks/simulation/inputs/m1_gate_rules.csv`, `m2_latency.json`, `m4_memory.csv`, `benchmarks/simulation/out/heldout_v1|v2/results.json`, `benchmarks/e2e/tasks.json`, and git history.
**Ground rules applied:** I did not ask for physical hardware tests. The study is judged as a component-level study (ACTUAL) plus a seeded simulation (SYNTHETIC), with no end-to-end LLM evaluation. I comment on the title but do not ask for it to change.

---

## 1. Summary of the submission

The paper describes a local browser agent whose control loop may report `Completed` only when a keyword-triggered conjunctive predicate Φ over the observed page holds. Each decision is stored as evidence. The ACTUAL evidence consists of:

- **Gate study.** 92 constructed states in three sets: design 38, held-out-1 12, and held-out-2 42, which was frozen before testing. The gate runs inside the real verification node with stubbed I/O. The study includes a per-conjunct ablation.
- **Latency of Φ.**
- **Egress test.** 70 episodes with a scripted stand-in model, plus a loopback-only endpoint check.
- **Oracle validation.** 114 scripted trajectories.
- **Small probes** of the memory store and the recovery engine.

A post-hoc-revised seeded simulation (v2) then propagates these measurements, together with stated assumptions, through a model of the loop to address H1–H5. The end-to-end harness (40 tasks, 5 self-hosted sites) is released but was not run.

The honesty and traceability are well above the norm. Every number I checked matches the data files. The weaknesses are scientific rather than clerical:

- **Weak primary comparison.** The headline test (p = 0.021) is made against the weakest possible baseline: a dispatch-only rule that accepts everything. Against the non-trivial error-check-only detector, which the authors measured but report only as a simulation input, the held-out advantage is not significant.
- **Unverified ground truth.** All ground-truth labels were written by the AI agent that designed the gate fixes, and no human has checked them.
- **Egress evidence not tied to the evaluated code.** The egress test ran on an unrecorded working tree, not on the evaluated commit.
- **Too long.** The paper is about twice the length of an 8-page IEEE conference paper, and much of the extra length is caveats repeated across sections and captions.

---

## 2. Scores (1 = poor, 5 = excellent)

| Criterion | Score | Justification |
|---|---|---|
| Novelty | **2** | "Dispatch ≠ completion" checked by postconditions over observed state is classical execution monitoring (STRIPS/PLANEX-style plan monitoring, robotics execution monitoring, design-by-contract postconditions). It is also close to recent runtime rule-enforcement work for LLM agents. The paper does not cite these lines of work. The new elements are modest: (i) a held-out, frozen-before-test measurement of an in-loop rule gate with intervals; (ii) a mismatch between direct and live-node modes, found only inside the live node (13–14 vs 15 withheld before the fixes); (iii) an honest implementation audit. The predicate itself is a set of keyword-triggered string checks. |
| Research gap | **3** | G1 (in-loop completion checks are rarely measured with held-out data and intervals) is real and clearly stated, but "has not been reported" (`01_introduction.tex:8`) should be softened to "to our knowledge". G2 follows naturally from G1. G3 (locality is "rarely checked") is an engineering check rather than a research gap. The gaps G1–G3 and RQ1–RQ5 do not map onto each other: G3 has no RQ, and RQ3–RQ5 have no gap (`05b_hypotheses.tex:4`). |
| Technical contribution | **2** | The core artifact is a rule set that, by the paper's own result, generalizes poorly to new phrasings: 0 of 5 unsatisfied extraction states are withheld, and when no trigger fires Φ reduces to ¬E. The engineering is substantial: about 11k LOC, a loopback enforcement, a harness, an oracle, a simulation and an audit table. The released end-to-end harness is a useful by-product but is unexercised. |
| Methodological soundness | **3** | Strengths: a design/held-out separation with a committed freeze (the SHA of `gate_heldout2.py` is recorded); paired decisions; the gate run inside the real verification node, not only called directly; one-factor ablation; per-category reporting; explicit evidence classes; post-hoc changes disclosed. Weaknesses: (a) the only reported inferential baseline is dispatch-only, which accepts 100% of states by construction; (b) all states and labels were authored by the same AI agent that designed the fixes and knew the rules, and no human has checked them; (c) the egress test ran on a dirty tree based on `1435fe9`, which is 9 backend files away from the evaluated `bf0a8a5` and predates the commit `55ac1ea` that introduced the loopback enforcement; (d) the simulation was revised twice post hoc, both times in Φ's favour (disclosed). |
| Statistical validity | **3** | The tests are correct and correctly computed: exact McNemar, Wilson/Clopper–Pearson intervals, and honest statements of the attainable minimum p (0.063, 0.25). There are no arithmetic errors (section 6). However: (a) against dispatch-only, McNemar reduces to "withheld (9) vs false rejections (1)", which is close to a tautology for any rule that rejects anything. Against the error-check-only detector, which the authors measured, the held-out-2 result is 7 vs 1, p = 0.070 (pooled held-out 8 vs 2, p = 0.11), so it is **not significant** (recomputed from `benchmarks/simulation/inputs/m1_gate_rules.csv`). (b) No primary endpoint or multiplicity policy is declared, although ten or more p-values are reported. (c) Wilson intervals on constructed, non-random states describe a hypothetical population defined by the authoring procedure; this should be said. (d) Synthetic p-values are labelled as conditional, which is correct, but they carry almost no information, as the paper itself says for H1, H4 and enhanced-H2. |
| Reproducibility | **4** | Very good. Scripts, seeds, raw outputs, a pinned `requirements-paper.lock`, `make reproduce-paper`, deterministic before-fix runs, recomputation scripts and a raw egress log are all present. What is missing: there is **no release tag** (`git tag` is empty; the text says "to be fixed by a release tag"). The evaluated code is identified by an auto-generated branch name (`ccr-4b8200f0-5i3k5m`). The egress run cannot be tied to a commit. The latency of Φ was measured on two different machines (2.1 GHz vs 2.8 GHz). |
| Treatment of limitations | **5** | Exceptionally thorough: internal, external, statistical, construct and simulation validity; system limitations; and a residual-risk table for privacy, including the unauthenticated local API, DNS rebinding and proxy variables. If anything it is excessive (see Writing). |
| Academic writing (clarity, repetition, tone) | **2** | The tone is appropriately modest and never promotional. Clarity and concision are poor. The abstract has 310 words (IEEE: 150–250) and contains a garden-path sentence ("frozen before testing the gate withheld…"). Paragraphs of 250–350 words are packed with parentheticals (`07_results.tex:30`, `06_methodology.tex:36`, `06_methodology.tex:47`). The statement that no end-to-end evaluation was executed appears in at least 7 places. "Synthetic p-values … conditional on assumptions" appears in the boxed note, in 5 captions and in 3 text locations. Several captions are longer than their tables (Tables IV, VII, X, XI). Revision-history language ("an earlier version … is corrected here", v1/v2 changes, an "audit found") belongs in a response letter, not a first submission. |
| Consistency (abstract ↔ hypotheses ↔ results ↔ conclusion) | **4** | The numbers are consistent across the abstract, Table III, Sections VIII–IX, Limitations and the Conclusion; I found no numerical contradiction. Issues: (a) the hypotheses are framed at full-agent level, but the only inferential evidence is component-level; (b) the gaps and RQs are not aligned (see Research gap); (c) the Discussion and Conclusion say the gate's benefit "is paid for in false rejections". That trade-off in the simulation is driven mostly by the ASSUMED missing-evidence rejection rate (0.8), not by Φ's measured false-rejection rate (0 of 24 outside bot-check pages). (d) The title promises an "Autonomous AI Agent Framework" for "Intelligent Task Automation", while no task automation was evaluated and only a browser backend exists. |
| Evidence labelling | **5** | Exemplary. It uses six evidence classes (ACTUAL / SYNTHETIC / ASSUMED / DERIVED / LITERATURE / PROPOSED), a boxed disclaimer on the simulation section, ‡ markers for proposed components, "(cond.)" on synthetic p-values, an evidence ledger, and a Status table restricting claims. I found **no synthetic or assumed result presented as real-world**. Minor points: class names are typeset inconsistently ("ACTUAL" in capitals in `tables/sim/memory.tex:3`, `overhead.tex:3`, `params.tex` vs `\textsc{actual}` elsewhere), and the "paid for in false rejections" sentence should name the assumed driver (B4). |

---

## 3. Spot-check of numbers against data files (16 checks, all match)

| # | Paper claim (location) | Data file → value | Match |
|---|---|---|---|
| 1 | Held-out-2: W 9/22 [0.23, 0.61], FR 1/20 [0.01, 0.24], FC/R 13/32 (Table IV; abstract) | `gate_stats.csv` held_out_2/all/gate: `9/22=0.41 W[0.23,0.61]`, `1/20 W[0.01,0.24]`, `13/32` | ✓ |
| 2 | McNemar vs dispatch, held-out-2, p = 0.021 | `gate_stats.csv` `p_correct_vs_dispatch=0.021484375` (9 vs 1) | ✓ |
| 3 | Pooled held-out 11/27 [.25, .59], 2/27 [.02, .23], p = 0.022, FC/R 16/41 | `gate_stats.csv` held_out_1+2: `0.0224609375`, 11/2 discordant | ✓ |
| 4 | Design after fixes 20/23 [.68, .95], 1/15 [.01, .30]; 7 fixed, 0 broken; before fixes 15/23, 3/15 | `gate_stats.csv` design/gate: 20, `fixed_vs_pre=7`, `broken_vs_pre=0`, `pre_fc=8`, `pre_fr=3` | ✓ |
| 5 | Before fixes, live node withheld 14 (empty) / 13 (verbose) | `verification_gate_cases_before_fixes.csv` design: 15 / 14 / 13 withheld | ✓ |
| 6 | Ablation design FC: E 8 (p .063), H 7 (.13), Q 4, T 6, X 6 with FR 0 (.63), R 4, β 5 (.50); held-out-2 β 15/0 | `gate_stats.csv` ablation rows: `p_vs_full` 0.0625, 0.125, 1.0, 0.25, 0.625, 1.0, 0.5; HO2 B 15/0 | ✓ |
| 7 | Φ latency median 26.8 ms, p90 29.5, p95 30.3, max 34.6 over 83 decisions; pre-check ≤ 13.4 ms | Recomputed from `verification_gate_cases.csv`: 83 non-blocked → 26.84 / 29.49 / 30.31 / 34.64; 9 blocked max 13.36 | ✓ |
| 8 | Egress: 555 attempts, all 127.0.0.1:11435, 8 processes, 70 episodes; 54 of 60 memory episodes retrieved ≥ 1 record | `e2e_smoke_stub/egress_summary.json`, `egress_raw.jsonl` (555/555 port 11435); `episodes.jsonl` → 54 | ✓ |
| 9 | Oracle 114 trajectories, no errors | `e2e_oracle_validation.txt`: 40 + 40 + 34, FN 0/37 (35 golden + 2 idle duplicates), FP 0/77 | ✓ (35 is explained in text) |
| 10 | 144 of 147 tests pass | `pytest_revision.txt`: "3 failed, 144 passed" | ✓ |
| 11 | Simulation decision level: Φ 52/74, none 46/74, b/c 3/9, p = 0.15; enhanced 61/74, p = 0.022 | `heldout_v2/results.json` decision TP+TN 43+9, 46+0, 41+20; `decision_p=0.1460`, `0.0225` | ✓ |
| 12 | Policy FC 19 vs 28; FCR .302 vs .378; TSR 44 vs 46 (3/1, p = .63) | `policy.evidence_gated FP=19, FCR=0.3016`; `no_verification FP=28`; `success_p=0.625` | ✓ |
| 13 | MC ΔFC +0.11 [0.05, 0.18]; Φ better at p < .05 in 42% of sets; MC acc .74 vs .64; Φ-only FC in 39% of sets vs basic | `monte_carlo_paired`: 0.1106 [0.05, 0.18], 0.419, 0.739/0.636, 0.394 | ✓ |
| 14 | Recovery 51 / 68 / 87 of 93; FC 9 / 9 / 2; unnecessary 81 / 174 / 162; guided-only 19, none engine-only | `recovery.*`; `recovery_paired_guided_vs_retry=[19,0,…]` | ✓ |
| 15 | Episode mean 20.2 vs 19.7 s (+2.6%); self-check 22.4 s (+14%); inference 80%; sweep 10.0 / 36.8 s | `latency`: 20.166 / 19.662 (+2.56%), 22.398 (+13.9%), 0.7955; `latency_sweep` 10.03 / 36.81 | ✓ |
| 16 | Memory P@3 0.52, R@3 1.00, MRR 0.93, top-1 irrelevant 3/10; derived rates (k+0.5)/(n+1) (nav .36, search .50, form .50, data .38, extr .07, multi .63; FR 0/24 → 0.02) | `m4_memory.csv` → 0.519 / 1.0 / 0.926 / 3; `results.json rates.*` | ✓ |

Also checked: the task distribution in Appendix B matches `tasks.json` exactly. The v1 numbers quoted in §VII-C (37 vs 43; 45/71 vs 43/71) match `heldout_v1/results.json` and `final_audit/changed_numbers_ledger.csv`. Sensitivity values (π = 0.3: 0.14 vs 0.21; π = 0.95: 0.32 vs 0.45; ×0.5 detection gives FCR 0.30) match `results.json → sensitivity`.

**Additional analysis (not in the paper, from the authors' own data).** This uses `benchmarks/simulation/inputs/m1_gate_rules.csv`, column `basic_accepts`, which is the error check E with no bot-check halt, run on the real implementation. Comparing Φ with this basic detector by exact McNemar on paired decision correctness:

| Set | Φ withholds | Basic withholds | Φ-only correct / basic-only correct | p |
|---|---|---|---|---|
| Design | 20/23 | 6/23 | 14 / 1 | 0.001 (circular) |
| Held-out-2 | 9/22 | 2/22 | 7 / 1 | **0.070** |
| Held-out 1+2 | 11/27 | 3/27 | 8 / 2 | **0.11** |

The direction favours Φ, but on held-out data it is not significant against this non-trivial ACTUAL baseline. The paper currently reports only the dispatch-only comparison at component level.

---

## 4. Page count vs 8-page IEEE conference limit

The build has **17 pages**:

| Part | Pages |
|---|---|
| Body, §I–XIV and Acknowledgment | ≈ 13.7 (Conclusion ends on p. 14) |
| Appendices A–C | ≈ 1.5 (Table XVI floats to p. 16) |
| References (47) | ≈ 1.7 (start on p. 15) |

The paper is therefore about **2× an 8-page limit**, or about 2.4× a "6 + 2 pages of references" limit. A submission in this form would be desk-rejected.

**What can move to an appendix or online supplement, or be cut** (estimated saving in pages):

1. **§IX simulation (Tables VI–XII, Fig. 3; ≈ 2.5 pp) and §VII-C simulation methodology (≈ 1.3 pp).** Keep one paragraph of method, Fig. 3 (sensitivity to π, the only informative synthetic result) and a 4-row excerpt of Table VI. Move Tables VII–XII, the v1→v2 history, "Validation by recomputation" and Table XVI to the supplement. Saves about 3.2 pp.
2. **§VII-B end-to-end harness, Appendix B and Table XV (≈ 0.8 pp).** These were not executed. Keep 3 sentences and a pointer. Move the oracle-validation paragraph of §VIII-D to the supplement. Saves about 0.7 pp.
3. **Appendix A and Table XIV, the computer-backend design (≈ 0.6 pp).** Not implemented; supplement or drop. Saves 0.6 pp.
4. **§XI safety (≈ 1 pp).** Keep the privacy-property paragraph. Move Table XIII and "What it does not provide" to the supplement, leaving a one-sentence pointer. Saves about 0.6 pp.
5. **Table II implementation audit.** Shrink to 6 rows or move to the supplement. **Table I related work:** cut to about 6 systems. **Table III hypotheses:** replace with component-level hypotheses (see B2). Saves about 0.6 pp.
6. **Prose.** Remove repeated caveats (one evidence-class statement in §VII plus labels in captions); shorten the "Fixes" paragraph (§V); shorten captions. Saves about 0.8 pp.
7. **References.** Cut 47 to about 30. Saves about 0.4 pp.

After these changes, the core of the paper (problem formulation, architecture with Algorithm 1 and Fig. 2, the gate study with Tables IV–V, latency, locality, a compressed simulation with Fig. 3, limitations, conclusion) fits in 8 pages.

---

## 5. (A) Mandatory corrections before submission

**A1. Abstract exceeds IEEE length and has a garden-path sentence**
- **Where:** `sections/00_abstract.tex:2`.
- **Problem:** 310 words (IEEE: 150–250). In "on 42 held-out states frozen before testing the gate withheld…" a comma is missing after "testing".
- **Fix:** replace the abstract with a version of 250 words or fewer that also includes A4. Proposed text (about 245 words; the authors should confirm p = 0.070 from their scripts):

> Browser agents can report a task as finished when it is not, and many send every observation to a hosted model. Agentic Pilot is an open-source browser agent with local models that may report completion only when a rule-based predicate over the observed page holds, and that stores the inputs of each decision as evidence. We formalize this evidence-gated completion with false-completion and false-rejection rates and evaluate it at component level, in the agent's real verification node with stubbed I/O. On 42 held-out constructed states frozen before testing, the gate withheld 9 of 22 unsatisfied states (41%, 95% CI 0.23–0.61) and rejected 1 of 20 satisfied ones. It was correct on more states than a dispatch-only rule (exact McNemar p = 0.021) but not significantly more than an error-check-only detector (p = 0.070), and far below the 20 of 23 withheld on its design states, because its checks are keyed to request wording. A decision costs a median of 27 ms and no model call. By default the model client refuses non-loopback endpoints; in 70 episodes with a scripted stand-in model server, the agent's Python processes connected only to 127.0.0.1. Component measurements also show that memory retrieval has no relevance threshold and that recovery does not recognize a missing confirmation. A seeded simulation, revised post hoc, shows that the gate's benefit depends on the unmeasured rate of premature completion claims; its outputs are not measurements of the agent. No end-to-end evaluation with a language model was executed; its harness is released.

**A2. De-anonymization in a double-blind submission**
- **Where:** `sections/05_implementation.tex:4`.
- **Problem:** `main.tex:29` declares the submission anonymous, but this line contains the URL `https://github.com/sudeshsudhii/Agentic-pilot-local`, which carries the author's username. The branch name and commit hashes are also searchable on GitHub.
- **Fix:** replace the URL with an anonymized mirror, e.g. `\url{https://anonymous.4open.science/r/agentic-pilot-XXXX}`, and replace "branch `ccr-4b8200f0-5i3k5m`, whose agent code … unchanged since commit `bf0a8a5`" with "release `v1.0-paper` of the anonymized repository". Restore the real URL in the camera-ready version.

**A3. No release tag exists; the evaluated version is described as "to be fixed"**
- **Where:** `sections/05_implementation.tex:4`.
- **Problem:** the text says "the evaluated version of the paper's artifacts is the head of that branch at submission, to be fixed by a release tag", but `git tag` is empty.
- **Fix:**
  1. Create an annotated tag, e.g. `v1.0-paper`, on the submitted commit, and ideally archive it with a DOI (Zenodo).
  2. Replace the sentence with: "The evaluated version is release `v1.0-paper` (agent code identical to commit `bf0a8a5`); all experiment scripts, data and the simulation are in that release."
  3. Delete "The repository's default branch has diverged … is not the version evaluated here".

**A4. The component-level G1 claim rests only on a trivial baseline; report the measured error-check-only baseline**
- **Where:** `sections/07_results.tex:13`, `tables/gate_results.tex:26-33`, `sections/05b_hypotheses.tex:4` (and the Table III caption at line 8), `sections/08_discussion.tex:4`, `sections/12_conclusion.tex:4`.
- **Problem:** the dispatch-only rule accepts every state, so McNemar against it reduces to "withheld vs false rejections". The authors already measured an error-check-only detector (E, no β) on all 92 states (`benchmarks/simulation/inputs/m1_gate_rules.csv`), but use it only as a simulation input.
- **Fix:**
  1. In `tables/gate_results.tex`, add a column "p vs E-only" with values: Design "--", Held-out 1 "1.0", Held-out 2 "0.070", Held-out 1+2 "0.11". Add a caption sentence: "E-only: error check E alone, without β (`m1_gate_rules.csv`, column `basic_accepts`); it withholds 2/22 on held-out 2 and 3/27 pooled."
  2. In `07_results.tex:13`, replace "the gate is correct on significantly more held-out states than a dispatch-only rule and withholds 41% of premature completions" with "the gate is correct on significantly more held-out states than a dispatch-only rule (p = 0.021), but not significantly more than the error check E alone (7 against 1, p = 0.070), and withholds 41% of premature completions".
  3. Mirror this qualifier in `05b_hypotheses.tex:4`, `08_discussion.tex:4` ("is correct on significantly more held-out states than a dispatch-only rule" → "… than a dispatch-only rule, though not significantly more than an error check alone") and `12_conclusion.tex:4`.
  4. Recompute with the project's own scripts and use their values.

**A5. The egress (locality) evidence was not produced by the evaluated code, although it is cheap to rerun**
- **Where:** `sections/07_results.tex:30` ("on an uncommitted working tree based on commit `1435fe9` … cannot be tied exactly to the evaluated commit `bf0a8a5`, whose agent code differs … in nine files").
- **Problem:** `git log` shows that the loopback enforcement was committed in `55ac1ea`, *after* `1435fe9`. This test needs only the scripted stand-in and no model or hardware.
- **Fix:**
  1. Rerun `run_e2e.py` with the egress `sitecustomize` on the tagged release (A3), store the run in `artifacts/results/e2e_smoke_stub_release/` with `git_dirty=false`, and regenerate `summarize_egress.py`.
  2. Replace the parenthetical with: "on the evaluated release (commit `bf0a8a5`, clean tree, recorded in `run_meta.json`)".
  3. Update the counts (555 attempts, 54 of 60) if they change. Update `tables/status.tex:13` and `sections/09_safety.tex:6` accordingly.
- **If the rerun is impossible:** state in the abstract that the egress test predates the evaluated commit.

**A6. Ground-truth labels have never been checked by a human**
- **Where:** `sections/06_methodology.tex:13`, `sections/10_limitations.tex:4`, `sections/12_conclusion.tex:7` ("No person has relabelled the gate states").
- **Problem:** every inferential gate result depends on oracle labels that were written by the same AI agent that designed the fixes. Checking them is not hardware testing; 54 held-out states take a few hours.
- **Fix:**
  1. Have at least one human (the author, plus ideally one independent annotator) blind-label the 54 held-out states using the protocol already in the repository, report agreement with the AI labels (raw agreement and Cohen's κ), and recompute Table IV on the adjudicated labels.
  2. Replace "Its limitation is that … no person or second annotator has relabelled them, so no inter-annotator agreement exists" with "The 54 held-out labels were independently relabelled by [one/two] annotator(s) blind to the gate's decisions (agreement x/54, κ = y); disagreements were adjudicated before the gate statistics were recomputed."
  3. Delete "No person has relabelled the gate states." from `12_conclusion.tex:7`.

**A7. Inaccurate oracle independence claim and double parenthesis**
- **Where:** `sections/03_problem.tex:13`.
- **Problem:** the text says "$\Phi^{\star}$ an oracle that shares no code or inputs with $\Phi$ (written by the same AI agent as $\Phi$'s fixes) (Section~\ref{sec:method})". In the gate study the oracle label judges the *same* page and answer that Φ reads, so "no inputs" is false.
- **Fix:** replace with "$\Phi^{\star}$ an oracle that shares no code with $\Phi$; in the end-to-end harness it also uses only signals that $\Phi$ does not read (Section~\ref{sec:method})."

**A8. Revision-history language in a first submission**
- **Where:** `sections/06_methodology.tex:15`.
- **Problem:** "an earlier version tested the withheld count alone and is corrected here". Reviewers have no earlier version, and in double-blind review this hints at a prior submission.
- **Fix:** delete this clause. Also, in `sections/06_methodology.tex:47`, delete "It also found that v2 first sent requests for help … this was corrected before the values reported here." (keep it in the artifact audit log).

**A9. Mis-cited privacy motivation**
- **Where:** `sections/01_introduction.tex:4`.
- **Problem:** "personal information has been shown to leak from language models~\cite{lukas2023pii}". Lukas et al. study leakage of PII memorized from *training data*, which is not the threat of sending screenshots to a hosted provider.
- **Fix:** replace with "although such screens carry names, messages and account data that a hosted provider then processes and may retain; language models can moreover leak personal information they were trained on~\cite{lukas2023pii}." Better still, also cite a source on provider-side data handling.

**A10. Fit the venue's page limit**
- **Where:** `main.tex:34-50`.
- **Problem:** the paper is 17 pages against an 8-page limit.
- **Fix:** follow the condensation plan in Section 4: move §VII-C and Tables VII–XII and XVI, §VII-B/Appendix B/Table XV, Appendix A/Table XIV, and Table XIII to a supplement, and condense §IX to one paragraph plus Fig. 3 and a Table VI excerpt. Add `\input{supplement}` only in the arXiv/extended version. Verify that the result is 8 pages or fewer with `sh build.sh`.

---

## 6. (B) Recommended improvements

**B1. Align gaps, RQs and hypotheses** (`01_introduction.tex:6-11`, `05b_hypotheses.tex:4`).
Either add an RQ for G3 (locality) and drop RQ3/RQ4 from the main paper (they are supported only by assumption-driven simulation), or add gaps for memory and recovery.

**B2. Restate the main-paper hypotheses at component level**, so that what is tested matches what is measured. Example:

| Hypothesis | Statement | Test |
|---|---|---|
| H1c | On frozen held-out states, Φ is correct on more states than dispatch-only and than E-only | exact McNemar |
| H2c | Φ's false-rejection rate on satisfied held-out states is ≤ 0.10 | Wilson upper bound |
| H5c | Φ's median decision latency is < 50 ms | — |

Keep the full-agent H1–H5 as the pre-registered plan for the end-to-end protocol. Declare held-out-2 vs dispatch-only and E-only as the primary endpoints; label all other p-values exploratory or apply Holm correction.

**B3. Say what the intervals mean.** In §VII-A, state that the constructed states are not a random sample of real tasks, so the Wilson intervals describe variability among states produced by the stated authoring procedure.

**B4. Attribute the simulated false-rejection cost correctly** (`07b_simulation.tex:15`, `08_discussion.tex:4`, `12_conclusion.tex:4`).
"The benefit … is paid for in false rejections" should add: "in the simulation these false rejections come mainly from the ASSUMED rejection of claims on pages with missing evidence (0.8); the measured false-rejection rate of Φ outside bot-check pages is 0 of 24."

**B5. Cite the classical and recent precursors.** Each paper should be checked before it is cited:
- execution monitoring in planning and robotics: Fikes, Hart & Nilsson 1972 (PLANEX); Pettersson 2005 survey on execution monitoring in robotics;
- design-by-contract postconditions;
- tool-grounded critique: CRITIC (Gou et al., ICLR 2024);
- runtime rule enforcement for LLM agents: e.g. AgentSpec, GuardAgent;
- completion judges for web agents: Agent-as-a-Judge, AgentRewardBench, Online-Mind2Web/WebJudge.

Then restate novelty as the measurement (frozen held-out sets, live-node vs direct discrepancies, per-conjunct ablation), not the concept.

**B6. Cut repetition.** Keep one statement that no end-to-end evaluation was executed (abstract plus §VIII-E) and one evidence-class paragraph (§VII). Captions should carry only the class label and the source file. Target captions of 40 words or fewer for Tables IV, VII, X and XI.

**B7. Typeset class names consistently.** Use `\textsc{actual}`, `\textsc{synthetic}`, `\textsc{assumed}`, `\textsc{derived}` and `\textsc{proposed}` everywhere (currently plain capitals in `tables/sim/memory.tex:3`, `tables/sim/overhead.tex:3`, `tables/sim/params.tex`).

**B8. Fix the Fig. 3 caption** (`tables/sim/sensitivity_fig.tex:21`). "Stricter verification … raises FRR" is not monotone: basic detection's FRR (≈ 0.143) is slightly above Φ's (≈ 0.139). Use "verification raises FRR relative to no verification".

**B9. Measure Φ latency on one machine.** Measure the gate-state and site-page latencies on the same machine, so the abstract's "27 ms" and Table XI's 5.2 ms are comparable. This takes minutes.

**B10. Drop or footnote the ablation p column** (`tables/ablation.tex`). The caption already calls those p-values descriptive and circular.

**B11. Extend the egress instrumentation to the whole process tree.** Running the 70 episodes in a network namespace, or under a packet capture with only loopback allowed, covers Chromium, DNS and the Playwright driver. It is cheap and closes the largest stated hole in G3.

**B12. Expand the Discussion.** It is two short paragraphs. Add:
- the practical meaning of a keyword-triggered gate: an adversarial or unusual phrasing silently disables it, because Φ reduces to ¬E;
- when it is worth deploying despite that;
- how the live-node-only defects argue for testing verifiers in situ.

**B13. Title (comment only, no change required).** "Autonomous AI Agent Framework … Intelligent Task Automation" promises more than the evidence, which covers a browser-only agent, component-level measurements and no task automation results. The first two sentences of the abstract should make the browser-only, component-level scope unmistakable, which the A1 text does.

**B14. Remove the internal history from the main text** ("At commit `2361d50`, the extraction handler formatted every answer as facts about one university campus …", `05_implementation.tex:10`). Keep a one-sentence summary and leave the details to the audit artifact.

---

## 7. (C) Optional future work

1. Run the released end-to-end protocol with local models (three trials, 30 test tasks): task success, FCR/FRR of the full agent, and the self-verification baseline.
2. Independent multi-annotator relabelling of all 92 states, and a larger held-out set written by people who do not know the rules.
3. A phrasing-robustness study: paraphrase each held-out goal k times (human- or LLM-generated) and report withholding as a function of trigger-word coverage.
4. Derive postconditions from the planner's expected outcome per step instead of request keywords. Compare against a local VLM judge on the same states, as a component-level comparison that needs a model but no browser episodes.
5. Evaluation on real sites, or WebArena-style images when available. Add prompt-injection robustness (AgentDojo-style) for the sanitizer and the once-per-task risk gate.
6. Implement the relevance threshold for memory and the confirmation check for recovery, then measure them, replacing the assumed rates in Studies D and E.
7. Desktop backend with pre-action permission tiers (Appendix A).

---

## 8. Overall recommendation

| Venue | Recommendation | Reason |
|---|---|---|
| (i) IEEE conference, 8-page limit | **Major revision**; would be desk-rejected in its current form for length | The scientific core is a defensible component-level study with careful labelling and fully reproducible numbers. It is sound enough to support a short conference paper once A1–A10 are addressed, especially A4 (the non-trivial baseline), A5 (egress on the evaluated code) and A6 (human-checked labels). Novelty is limited, so acceptance would depend on presenting it as a rigorous negative/partial result on rule-based in-loop verification. |
| (ii) Workshop with longer limits | **Minor revision** | A1–A9 apply; A10 is relaxed. The length is acceptable and the transparency is a strength. |
| (ii) Archival journal | **Major revision** | Journal reviewers will expect A4–A6 plus at least one of: the end-to-end run, or a phrasing-robustness study with independently authored states. The novelty of the predicate alone is not enough for a journal. |

---

### Summary of scores

Novelty 2 · Research gap 3 · Technical contribution 2 · Methodological soundness 3 · Statistical validity 3 · Reproducibility 4 · Limitations 5 · Writing 2 · Consistency 4 · Evidence labelling 5.
