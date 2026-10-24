# Research Integrity Audit: Agentic Pilot paper

Auditor: research-integrity agent (read-only; no repository file was modified).
Audit base: `HEAD = 1615ac5` on branch `ccr-4b8200f0-5i3k5m`. This commit ("Audit fixes A-D, F, I") landed **during** the audit, at 2026-10-24 01:16 UTC. I re-read every file it touched: abstract, 05b, 06, 07b, conclusion, and sim tables ablation/baseline/tests. Findings below refer to the current text. Items that 1615ac5 already fixed are listed in section 1.4.
`paper/main.pdf` is current: its text extracted with mutool contains the 1615ac5 wording.

Legend. Class: **A** = ACTUAL (measured), **D** = DERIVED, **S** = SYNTHETIC, **L** = LITERATURE, **P** = PROPOSED. Severity: High / Med / Low.

---

## 1. Claim classification and overstatement check

### 1.1 Claim ledger (abstract, intro, results, simulation, discussion, safety, limitations, conclusion)

| # | Location | Claim (abridged) | Class | Verdict |
|---|---|---|---|---|
| 1 | Abstract s1 | Browser agents report false completion; many send observations to hosted models | L | OK |
| 2 | Abstract s2; Intro C4; Sec. V | "Agentic Pilot is an open-source browser agent with local models" / "open-source local agent"; code public at github URL | A (code) | **Overstated, High (O1).** The repo's default branch `main` (7654519) defaults to the cloud **Gemini** provider (`LLM_PROVIDER=gemini`, `backend/llm/gemini.py`, `hybrid.py`) and adds a Windows desktop-automation subsystem. The paper's code exists only on the non-default branch. See section 2. |
| 3 | Abstract | Formalizes evidence-gated completion, FCR/FRR | P/D (definition) | OK |
| 4 | Abstract; Results VII-A | Gate withheld 20/23 unsatisfied design states [0.68,0.95], rejected 1/15 | A | OK. "Design" is disclosed as in-sample/optimistic in Results and Limitations. |
| 5 | Abstract; Intro C2; Results; Discussion | "inside the agent's live verification node" | A | **Low (O8).** The node ran with database, browser-pool and evidence I/O stubbed, and with empty or generic planner reasoning (Sec. VI-A, Limitations). "Live" is defensible, but the abstract does not qualify it. |
| 6 | Abstract | Held-out-2: 9/22 withheld [0.23,0.61]; "exact McNemar p=0.004 against a dispatch-only rule" | A + D | **Med (O2).** The test is degenerate. A dispatch-only rule withholds nothing by construction, and `gate_stats.py` calls `mcnemar_exact(W, 0)`, which gives p = 2·0.5^W. The p-value therefore only says W ≥ 9 > 0, which the Wilson interval already shows. Presenting it as a significance result (and in VII-A/Discussion as "a significant share") inflates the evidence. |
| 7 | Abstract | "...9 of 22 ..., because its answer check depends on request wording" | A (interpretation) | **Low (O7).** 1615ac5 deleted "and none of the 5 unsatisfied extraction states", so the causal clause now explains the whole 9/22 result. Only the 5 extraction misses are attributable to X. The other 8 misses come from E/T/H/Q phrasing gaps, a redirect, add-to-cart and press-and-hold (VII-A). |
| 8 | Abstract; VII-C | Median 27 ms per decision, no model call | A | OK. On gate states it is 26.8 ms; on site pages 5.2 ms (A). |
| 9 | Abstract | Model client refuses non-local endpoints; 70 stub-model episodes opened no non-loopback connection | A | OK as reworded in 1615ac5. The explicit user override is disclosed in Sec. IX. |
| 10 | Abstract; 07b-D/E | Memory has no relevance threshold; recovery does not recognize a missing confirmation | A | OK. Measured on the real store with a 23-record synthetic corpus and on the real recovery engine with 6 messages. |
| 11 | Abstract; 07b-A | Simulation: 19 vs 28 FC per 100; decision accuracy 45 vs 43 of 71; "conditional on the assumptions" | S | OK (fixed in 1615ac5). |
| 12 | Abstract; VII-E; Conclusion | "No end-to-end evaluation ... executed; its harness is released" | A (negative) | **Med (O3).** It is "released" only on a non-default branch. VII-E also says the harness "run[s] with one command on a machine with Ollama", which is untested: no run with a real model server exists, only the 70-episode stub smoke run. |
| 13 | Intro p1 | Hosted multimodal agents; PII leaks from LMs | L | OK |
| 14 | Intro G1 | In-loop completion checks "not reported with intervals and held-out data" | L (absence claim) | Unverifiable negative claim. Acceptable as framing. |
| 15 | Intro G3 | Locality claims "seldom measured" | L | Unverifiable framing. Acceptable. |
| 16 | Intro Scope | Autonomous; privacy-preserving = inference on the machine; desktop is a design | A/P | OK for this branch. On `main` a desktop subsystem is implemented, which contradicts "is a design" for the code at the published URL (O1). |
| 17 | Intro C2 | "ACTUAL evidence on G1 and G2 ... with intervals, paired tests and a per-conjunct ablation" | A | The "paired tests" against dispatch-only are degenerate (O2). The ablation tests (p ≥ 0.06) are legitimate. |
| 18 | Intro C3 | "A seeded, simulation-based evaluation of H1–H5 ... which shows the trade-off ..." | S | **Low (O9).** "Shows" is stronger than the sim warrants. For H4 and enhanced H2 the outcome follows from assumptions (05b says so). Suggest "illustrates under stated assumptions". |
| 19 | Intro C5 | Enforcement and ACTUAL test of local-only model traffic | A | OK. `tests/test_local_egress.py` (18 cases) all pass in `junit_revision.xml`; the file is present at bf0a8a5. |
| 20 | Intro C6 | Harness: self-hosted sites, 40 tasks, oracle validated on scripted trajectories | A | OK. Validation covers 114 author-written trajectories, disclosed in VII-D. |
| 21 | Intro last | "simulated results are labelled as such throughout" | — | Mostly true. Exception: the 0.64→0.86 filter result (O6). |
| 22 | VII-A | Pre-fix gate: 15/23, 3/15; live node 14 or 13 | A | OK (gate_stats.csv) |
| 23 | VII-A | Fixes correct 7 states, break 0 (p=0.016) | D | OK. A legitimate paired test; its optimism is disclosed. |
| 24 | VII-A | Held-out-2 FR 1/20; pooled 11/27 [0.25,0.59], FR 2/27 | A | OK |
| 25 | VII-A, Discussion | "the gate withholds a significant share of premature completions at a low false-rejection rate" | A + D | **Med (O2).** "Significant" rests on the degenerate test. "Low FR" is not established: the held-out-2 FR upper bound is 0.24. The states are author-constructed, not planner-produced premature completions (O11). |
| 26 | VII-B | Ablation: every removal raises FC on design states; none significant; Q, X change nothing on held-out | A | OK and honestly worded. "Evidence types thus contribute on the states that trigger them" is a mild generalization from non-significant results. Acceptable. |
| 27 | VII-C | Latency percentiles; pre-check ≤ 13.4 ms; zero tokens | A | OK |
| 28 | VII-D | 70 episodes "on the working tree that was then committed as 55ac1ea" | A | **Low (O10).** `artifacts/results/e2e_smoke_stub/run_meta.json` records `git_commit 1435fe9`, `git_dirty: true` at 07:20 UTC. 55ac1ea is from 07:28. No diff hash was recorded, so the tree-to-commit link is an unverifiable assertion. The disclosure is honest but cannot be checked. |
| 29 | VII-D | 555 attempts all to 127.0.0.1 | A | Verified (`egress_summary.json`) |
| 30 | VII-D | 144/147 tests pass; 3 failures need live websites or a running model | A | Verified (`pytest_revision.txt`). The 3 failures navigate live google.com/twitter.com with a mocked model; the explanation is plausible. The approval flow is separately tested and passes (`tests/e2e/test_runner::test_high_risk_approval_flow`). |
| 31 | VII-D | Oracle 0/37 FN, 0/77 FP, intervals | A | OK. The "anticipated behaviors only" caveat is present. |
| 32 | VII-E | No claim about task success, baselines, memory, recovery | A (negative) | OK |
| 33 | 07b box | Values are synthetic except those marked ACTUAL | — | OK |
| 34 | 07b-A | H1: 19 vs 28, p=0.004 conditional; MC 96% of sets p<0.05 | S | OK. Labelled conditional. The MC values are not independently recomputed, and that is disclosed. |
| 35 | 07b-A | H2: decision accuracy 0.63 vs 0.61, p=0.80; enhanced 54/71 "follows from assumed detection rates" | S/P | Wording OK. **Process issue (O4)**: the decision-level metric was introduced post hoc (1615ac5) after the results were seen, and simulate.py was changed after the freeze without disclosure. See section 1.3. |
| 36 | 07b-B | Ablation: removing recovery 0.37→0.30; evidence removal changes no decision | S + A (code behaviour) | OK. The 1615ac5 relabel clarifies the simulated vs implemented switch. |
| 37 | 07b-C | Real store recall@3 1.00, MRR 0.93, 3/10 top-1 irrelevant or failed | A | OK |
| 38 | 07b-C | Memory gives no gain (18 vs 19 of 44), "so H3 is not supported" | S | Acceptable, because the section is boxed as synthetic. Better: "not supported in the simulation". |
| 39 | 07b-C | "A relevance filter ... (proposed) raises contextual accuracy from 0.64 to 0.86 in the simulation" | S/P | **Low-Med (O6).** 0.86 is essentially 1 − the PROPOSED misleading rate 0.1 (Table params), so it holds by assumption. Unlike H4 ("a consequence of its assumed success rates"), it is not marked as such. |
| 40 | 07b-D | Real engine classifies `net::ERR_` transient, invalid submission → replan, missing confirmation → unknown | A | OK |
| 41 | 07b-D | Retry 69/93, guided 87/93 "a consequence of its assumed success rates, not evidence for it" | S/P | OK (well hedged) |
| 42 | 07b-E | Latencies 5.2 / 26.8 / 61 / 76 ms | A | OK |
| 43 | 07b-E | Inference 84% of episode; Φ +0.2%; self-check +24% | S (assumed 3 s per call) | OK. Labelled. |
| 44 | 07b-F | Sensitivity in π; FCR 0.14 vs 0.21 at π=0.3, etc. | S | OK |
| 45 | 05b | Hypothesis table outcomes "conditional", "by assumption" | S | OK after 1615ac5 |
| 46 | 06 | "Independent validation ... recomputation of the analysis code's arithmetic ... neither independent human annotation ... nor replication" | D | OK after 1615ac5. Minor: the "validation agent" is an AI sub-agent ("Agent 4" in the report). `simulation_validation_report.md` names its script at a `/tmp/.../scratchpad/validator.py` path that is not in the repo. A copy is in `benchmarks/simulation/independent_validator.py`, but with hard-coded absolute and /tmp output paths. Reproducibility nit. |
| 47 | Discussion p1 | "withholds a significant share ... at a low false-rejection rate"; "does not show that the agent completes tasks" | A | First clause: O2. The rest is OK. |
| 48 | Discussion p2 | Rules keyed to wording; judges complementary; "we expect" | L/P | OK, marked as expectation |
| 49 | Safety: threat model, privacy property | Loopback refusal, telemetry off, 70 episodes no non-loopback | A | **Low (O10b).** Sec. IX says "in 70 agent episodes" without the scripted-stand-in qualifier that the abstract and VII-D now carry. |
| 50 | Safety | 17-pattern sanitizer; approval gate before navigation; loopback service; model calls logged | A (code) | Verified: 17 patterns in `backend/security/sanitizer.py` |
| 51 | Safety | "We make no security claim"; denylist insufficient | A/L | OK |
| 52 | Limitations | Internal, external, power, simulation, construct and system validity | — | Accurate and candid. 54 held-out states (27/27) verified arithmetically. |
| 53 | Conclusion | Three-way framing (measured / simulated / not executed) | A/S | OK after 1615ac5. "Withheld most premature completions" refers to constructed states (O11, Low). "Released" is subject to O1/O3. |
| 54 | Table I, own row | Env "W" (live websites) | A? | **Low-Med (O5).** The paper never evaluates on live websites. Every measurement uses constructed states or self-hosted sites (Wr), and the only live-site tests are the 3 failing ones. Since the caption says the table reports "what each paper reports", the row should read Wr (W designed). |

### 1.2 Overstated-claim summary (11)

| ID | Severity | Issue | Fix |
|---|---|---|---|
| O1 | **High** | "Open-source ... with local models" and the code URL: the public default branch is a diverged codebase that defaults to cloud Gemini and implements Windows desktop control. A reader following `\url{...}` gets code that contradicts the paper's locality and scope claims. | Cite a tag or release (and ideally an archival DOI) for the paper commit; name the branch in the paper; add a README note on `main`. |
| O2 | Med | McNemar vs dispatch-only (p=0.004, <0.001, 0.001) is degenerate (p = 2·0.5^W). This drives "significant share" in the abstract, VII-A, Discussion and Intro C2. FR "low" with upper CI 0.24. | Drop the p-value, or state that it only tests W>0; rely on the Wilson intervals; replace "significant share" with the counts. |
| O3 | Med | Harness "released and run with one command on a machine with Ollama": it has never been run with a model, and it is released only on a non-default branch. | Say it "has been exercised only with a scripted stand-in". |
| O4 | Med | Sec. VI-D says "After the freeze, one function was changed: the latency model". 1615ac5 changed `episode()` in `benchmarks/simulation/simulate.py` again: additive fields `claimed`, `y_claim`, `accepted`. It also added a post-hoc decision-level analysis (`decision_analysis.py`) whose docstring says an earlier p "is withdrawn", and redefined H2's dependent variable from "accuracy, F1" to "decision accuracy" after the outcomes were known. The policy-level outputs are unchanged (the diff is additive), but the freeze statement is now inaccurate and the H2 redefinition is undisclosed. | Amend VI-D to list the second post-freeze change, and label the decision-level analysis and the H2 dependent variable as post hoc. |
| O5 | Low-Med | Table I own-row Env "W" unsupported by any evaluation. | Change to Wr (W: designed). |
| O6 | Low-Med | Filter 0.64→0.86 holds by assumption but is not marked so. | Add "by assumption (misleading rate 0.1, proposed)". |
| O7 | Low | Abstract causal clause misattributes all held-out misses to the answer check. | Restore "none of the 5 extraction states" or say "partly because". |
| O8 | Low | "Live verification node" without noting stubbed I/O and stand-in reasoning in the abstract. | Add "with stubbed I/O" once. |
| O9 | Low | Intro C3 "shows the trade-off" for synthetic results. | Use "illustrates under stated assumptions". |
| O10 | Low | 55ac1ea working-tree provenance cannot be verified from `run_meta.json`; Sec. IX omits the stub qualifier. | State that the run was from a dirty tree at 1435fe9; add "with a scripted model stand-in" to Sec. IX. |
| O11 | Low | "Premature completions" used for author-constructed end states (VII-A, Discussion, Conclusion). | Use "unsatisfied constructed states". |

### 1.3 Post-freeze verification of the gate (held-out-2)
- `artifacts/experiments/gate_heldout2.py` was committed alone in `b9d5088` together with `gate_heldout2_freeze.txt`. The recorded SHA-256 `15b85e6e…a28a` equals the current file hash, so the file is unchanged since the freeze.
- `git diff b9d5088 bf0a8a5 -- backend/verification/manager.py backend/agent/nodes.py` adds only conjunct-disable switches (default empty), a self-verification mode and latency/model-call bookkeeping. Locality enforcement is in other files. This is consistent with the paper's statement that only ablation switches were added and default behaviour is unchanged.
- `git log bf0a8a5..HEAD -- backend` is empty, so the agent code at HEAD equals bf0a8a5, as the paper claims.

### 1.4 Already fixed by 1615ac5 (no longer flagged)
- Synthetic p-values and intervals were not marked conditional. They are now marked in the abstract, 05b, 06, 07b and the tables.
- "Independent validation" read as more than recomputation. It now says explicitly "neither independent human annotation ... nor replication".
- The abstract's "70 agent episodes" lacked the stub qualifier. Fixed in the abstract and Results (not in Safety, see O10).
- The policy/decision-level confusion in the H2 accuracy test is fixed. Its process is flagged in O4.

---

## 2. Artifact, script, dataset and commit verification

Repository: `sudeshsudhii/Agentic-pilot-local` is **public**, MIT license, default branch **`main`** (`gh api`).
Branches on GitHub: `main` @7654519 and `ccr-4b8200f0-5i3k5m` @1615ac5. The merge-base is `2361d50`. The paper branch has diverged: 39 ahead and 2 behind `main`. No PR exists.

`main` after the merge-base:
- `a474924` "add Google Gemini provider, hybrid LLM routing, and Windows desktop automation subsystem" (2026-10-09). Gemini is the default (`gateway.py`: `provider_type = (cfg.llm_provider or "gemini")`; `.env.example: LLM_PROVIDER=gemini`).
- `7654519` "Fix Agentic Pilot Ollama fallback ...".

None of `artifacts/results`, `benchmarks/e2e` or `benchmarks/simulation` exists on `main`.

### 2.1 Commit hashes

| Hash | Cited where | Exists locally | On origin (GitHub API 200) | Branch on GitHub | On default branch? | Content matches the paper's use? |
|---|---|---|---|---|---|---|
| bf0a8a5 | Sec. V ("this paper describes"), VII-D | yes | yes | ccr only | **no** | Yes. Egress test present; backend unchanged to HEAD. |
| 55ac1ea | VII-D (egress tree) | yes | yes | ccr only | **no** | Yes, but see O10 (dirty-tree provenance). |
| 3a0aa8e | VI-D (sim freeze) | yes | yes | ccr only | **no** | Yes. simulate.py changed afterwards in 41a6097 (disclosed) **and in 1615ac5 (undisclosed, O4)**. |
| 41a6097 | VI-D (latency CRN fix) | yes | yes | ccr only | **no** | Yes |
| 2361d50 | Sec. V (pre-fix extraction bug) | yes | yes | main and ccr | yes | Yes. `nodes.py:1108-1123` hard-codes SRM campus facts. |
| b9d5088 | not cited by hash (held-out-2 freeze) | yes | yes | ccr only | no | Yes. SHA-256 matches. |
| eb3803e | not cited by hash | yes | yes | ccr only | no | n/a |
| f3edacc, 1615ac5 | not cited (paper sources) | yes | yes | ccr only | no | The paper text itself lives only here. |

### 2.2 Files and paths named in the paper (all at HEAD 1615ac5; `git status` clean, so all committed and pushed to `origin/ccr-…`)

| Path | Exists | Tracked | Pushed (ccr) | On `main` |
|---|---|---|---|---|
| `artifacts/` (scripts, raw outputs) | yes | yes | yes | no (only some legacy docs) |
| `artifacts/results/gate_stats.csv` | yes | yes | yes | no |
| `artifacts/results/verification_gate_ablation.csv` | yes | yes | yes | no |
| `artifacts/results/simulation_validation_report.md` | yes | yes | yes | no |
| `artifacts/results/` (ledger, validation) | yes | yes | yes | no |
| `benchmarks/e2e/` incl. `run_e2e.py`, `analyze_e2e.py`, `tasks.json` | yes | yes | yes | no |
| `benchmarks/simulation/`, `params.json`, `out/heldout/` (`scenarios.csv`, `recovery_scenarios.csv`, `results.json`, `ledger_simulation.csv`, `decision_analysis.json`) | yes | yes | yes | no |
| Held-out-2 SHA-256 "recorded in the repository" | yes (`gate_heldout2_freeze.txt`) | yes | yes | no |
| Cohen's κ relabelling protocol "in the repository" | yes (`AUTHOR_ACTIONS.md` §A3) | yes | yes | no |
| Egress test (`tests/test_local_egress.py`) | yes | yes | yes | no |
| Evidence ledger | yes (`ledger_simulation.csv`) | yes | yes | no |
| LICENSE (MIT) | yes | yes | yes | yes |

Result: **0 missing, 0 untracked, 0 unpushed.** Every artifact except LICENSE, and every cited commit except 2361d50, is reachable on GitHub **only through the non-default branch `ccr-4b8200f0-5i3k5m`**. The paper gives only the repository URL, and that URL resolves to a contradictory codebase. The public-availability and reproducibility claims are therefore technically true but practically unsupported for a reader who follows the URL, and the auto-generated branch could be deleted. Recommendation: merge to `main` or create a release tag such as `paper-v1` at 1615ac5 (or the final commit), archive it (Zenodo DOI), and cite tag + hash in Sec. V.

Additional reproducibility notes:
- The independent validator writes to `/tmp/claude-0/.../scratchpad/validation_report.md` and reads an absolute `/home/user/...` path, so it does not run elsewhere without edits.
- The decision-level values (05b, 07b, Tables sim/baseline and sim/tests) come from `decision_analysis.py`, which regenerates scenarios in memory. They are not covered by the independent recomputation (disclosed).

---

## 3. Bibliography (J)

All 47 bib entries are cited and all citations resolve; `main.blg` has 0 warnings. Fields are internally plausible: venues match years, DOI prefixes match publishers (10.18653 ACL, 10.1145 ACM, 10.1109 IEEE, 10.1007 Springer, 10.1080/10.1093/10.1214/10.1177 for the statistics classics), and page ranges are ascending. Booktitle abbreviation style is inconsistent ("Learn. Represent." vs "Learning Representations"; "Datasets and Benchmarks Track" with and without a comma). Cosmetic only.

Network note: direct fetches to dblp, arXiv and Crossref were blocked by the proxy. Verification used web search against publisher, proceedings and anthology listings.

### 3.1 Entries verified (20)

| Key | Checked | Result |
|---|---|---|
| yao2023react | ICLR 2023, authors | OK |
| shinn2023reflexion | NeurIPS 36 proceedings author list | OK. Matches the proceedings, which omit E. Berman; the arXiv/GitHub lists include him. |
| zhou2024webarena | ICLR 2024, authors | OK |
| deng2023mind2web | NeurIPS 2023 D&B, authors | OK |
| he2024webvoyager | ACL 2024 long, pp. 6864–6890, DOI 2024.acl-long.371, 8 authors | OK |
| zheng2024seeact | ICML 2024, PMLR 235, pp. 61349–61385, authors | OK |
| xie2024osworld | NeurIPS 2024 D&B, first 12 authors + others | OK (from known listing) |
| zhang2025ufo | NAACL 2025 long, pp. 597–622, 12 authors | OK. The bib omits DOI 10.18653/v1/2025.naacl-long.26 (optional). |
| zhang2025appagent | CHI '25, Article 70, pp. 1–20, DOI 10.1145/3706598.3713600 | OK. The ACM record lists Yanda Li; the arXiv/GitHub 8-author list does not, so the bib follows the published version. |
| hong2024cogagent | CVPR 2024, pp. 14281–14290 | **Minor error.** The CVF listing has exactly 11 authors (Hong … Jie Tang), all in the bib, but the bib appends `and others`, so IEEEtran prints "et al." spuriously. The arXiv version has 14 authors in a different order. |
| packer2023memgpt | arXiv 2310.08560, authors (v2+) | OK. Not peer-reviewed; v1 lists a different author set. |
| debenedetti2024agentdojo | NeurIPS 2024 D&B, 6 authors | OK |
| drouin2024workarena | ICML 2024, PMLR 235, pp. 11642–11662, 9 authors | OK. Matches PMLR, while arXiv has 12. |
| kuntz2025osharm | NeurIPS 2025 D&B, 7 authors | OK. Missing `volume = {38}`, unlike the sibling entries (incomplete, not wrong). |
| sumyk2025done | arXiv 2511.20067, 2 authors, Nov 2025 | OK. Also appeared at the AAAI 2026 TrustAgent workshop (optional update). |
| liu2024formalizing | USENIX Security 2024, pp. 1831–1847 | OK |
| koh2024visualwebarena | ACL 2024, pp. 881–905, DOI 2024.acl-long.50 | OK |
| reimers2019sbert | EMNLP-IJCNLP 2019, pp. 3982–3992, D19-1410 | OK |
| cheng2024seeclick | ACL 2024 long, authors | Authors OK. Pages 9313–9332 and DOI not confirmed by search; consistent with my knowledge. |
| lukas2023pii | IEEE S&P 2023, authors | Venue and authors OK. Pages and DOI not confirmed by search; consistent with my knowledge. |

From known records without a search (no discrepancy noticed): wei2022chain (NeurIPS 35, 24824–24837), lewis2020rag (NeurIPS 33, 9459–9474), park2023generative (UIST, DOI), greshake2023indirect (AISec, DOI), wang2024survey (FCS 18(6) 186345), the five statistics classics, huang2024cannot, ruan2024toolemu, agashe2025agents, pan2024autonomous, lin2024awq, schick2023toolformer, kim2023rci, wang2024voyager.

Not confirmed by search: xi2025rise (Sci. China Inf. Sci. 68:121101, DOI 10.1007/s11432-024-4222-0; search found only the arXiv preprint, though the details agree with my knowledge) and zhan2024injecagent pages 10471–10506 (no result).

**Bibliographic errors: 1 confirmed (CogAgent spurious "and others"), plus 1 incomplete field (OS-Harm volume). No wrong author, year, venue, page or DOI was found among the verified entries.**

### 3.2 Table I (paper/tables/related_work.tex) fairness

| Row / cell | Assessment |
|---|---|
| ReAct: Ws, A, model, N, N, H, E2E | Fair. PaLM/GPT-3 are hosted; the tasks are HotpotQA/FEVER/ALFWorld/WebShop. |
| Reflexion: Deploy "n.r." | **Questionable.** The paper reports results with hosted OpenAI models (GPT-3/3.5/4), so "H" (or "P", if the StarChat-beta appendix result is counted; unconfirmed) is supported. "Not reported" is inaccurate. The other cells are fair. |
| WebArena: Deploy "n.r." | **Inaccurate.** The paper reports GPT-4, GPT-3.5 and text-bison-001, all hosted, so it should be "H". Coding is also inconsistent with OSWorld/AgentDojo, which are coded by the models they evaluated. The other cells are fair. |
| Mind2Web: Wr, B, n/a, P, N, L, Off | Fair. MindAct uses Flan-T5 (open) and GPT; the dataset stores per-step snapshots ("P" is unclear but defensible). |
| WebVoyager: W, A, model; judge, Y, N, H, E2E | Fair. GPT-4V judge confirmed. "Evid. Y" (per-step screenshots saved) is plausible but unverified. |
| SeeAct: W, Wr, A, model, n.r., N, P, E2E, Off | Fair. Online and offline Mind2Web settings confirmed. "Deploy P" (open LMM baselines) is unverified. |
| OSWorld: D, B, benchmark, n.r., N, L, E2E | Fair. Open models were evaluated. |
| UFO: D, A, model, n.r., P, H, E2E | Mostly fair. GPT-4V, hosted. "Mem P" is unverified. |
| AppAgent: Mo, A, model, n.r., Y, H, E2E | Fair. Exploration knowledge base, GPT-4V. |
| CogAgent: Wr, Mo, M, n/a, N, N, L, Off | Fair. Mind2Web and AITW offline. |
| MemGPT: Deploy "n.r.", Eval "n/a" | **Unfair.** MemGPT reports evaluations (deep memory retrieval, multi-document QA, nested KV) run with GPT-4/GPT-4-Turbo/GPT-3.5 (hosted), so Deploy should be "H" and Eval should be something other than "n/a" (e.g. a non-web task evaluation). |
| AgentDojo: Ws, B, benchmark, n.r., N, L, E2E | Fair (includes an open Llama-3 70B evaluation, from my knowledge; not re-verified). |
| Agentic Pilot: Env "W" | **Overclaim (O5).** No live-website evaluation; it should be Wr. "Mem P^d" and "Eval C+S" are fair and honestly footnoted. |
| Caption "All listed systems released code" | Consistent with my knowledge for all 12. |

Table I issues: 4 cells miscoded (Reflexion Deploy, WebArena Deploy, MemGPT Deploy and Eval) plus the own-row Env overclaim. Cells I could not verify: WebVoyager Evid, SeeAct Deploy, UFO Mem, Mind2Web Evid "P", AgentDojo Deploy.

---

## 4. Counts
- **Overstated claims: 11.** 1 High (O1, default branch contradicts local-only/open-source framing), 3 Medium (O2 degenerate McNemar / "significant share"; O3 harness "runs with one command" and is "released"; O4 undisclosed post-freeze simulate.py change and post-hoc H2 dependent variable), 7 Low or Low-Med (O5–O11).
- **Missing or unpushed artifacts: 0 missing, 0 untracked, 0 unpushed.** But 7 of the 8 relevant commits (all except 2361d50) and every paper artifact are absent from the default branch `main`, which has diverged with a cloud-Gemini default. The availability claim is only reachable through a non-default, auto-named branch.
- **Bibliographic errors: 1 confirmed minor** (CogAgent "and others") and 1 incomplete field (OS-Harm volume). 0 wrong author, year, venue, page or DOI among the 20 verified. Table I: 4 miscoded cells for other systems plus 1 own-row overclaim; 5 cells unverifiable.
