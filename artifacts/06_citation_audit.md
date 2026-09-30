# 06 — Citation Audit (C1)

**Scope.** Every `\cite{}` in `paper/sections/*.tex` and `paper/tables/*.tex`, checked against `paper/references.bib` and the verification record in `03_literature_matrix.md`.

**Mechanical checks**
- 35 bib entries, 35 distinct keys cited. No uncited entries. No citation to a missing key.
- `bibtex` with `IEEEtran.bst` reports 0 warnings (`paper/main.blg`).

**Limits of this audit.** Direct fetches of arXiv, doi.org, ACL Anthology, OpenReview and the proceedings sites were blocked from this sandbox. Existence and metadata were verified through search-index records of the primary pages and the authors' own BibTeX on GitHub (see matrix). Claims were checked against:
- abstracts and venue pages;
- the matrix notes;
- for one claim, an additional search (below).

They were **not** checked against the full PDFs. The author should re-read the PDFs for the claims marked ◐.

## Claim-by-claim

| # | Where | Claim in paper | Key(s) | Check | Verdict |
|---|---|---|---|---|---|
| 1 | §I ¶1 | Several web/GUI agents send screenshots to a hosted multimodal model | he2024webvoyager, zheng2024seeact, zhang2025ufo, zhang2025appagent | Matrix: GPT-4V / GPT-Vision backbones in all four | ✓ |
| 2 | §I ¶1 | PII leakage from LMs measured even after scrubbing | lukas2023pii | Matrix note: leaks PII "even after scrubbing or DP training" | ✓ |
| 3 | §I ¶2 | State-checking benchmarks show a large gap | zhou2024webarena, xie2024osworld | 14.41% vs 78.24% (WebArena); 12.24% vs 72.36% (OSWorld) | ✓ |
| 4 | §I ¶2, §II-A | Intrinsic self-correction without external feedback does not improve and can degrade reasoning | huang2024cannot | Title and abstract | ✓ |
| 5 | §II-A | ReAct interleaves reasoning and actions; CoT basis | yao2023react, wei2022chain | Abstracts | ✓ |
| 6 | §II-A | Toolformer learns when to call APIs | schick2023toolformer | Abstract | ✓ |
| 7 | §II-A | Reflexion stores verbal self-critiques in an episodic buffer | shinn2023reflexion | Abstract | ✓ |
| 8 | §II-A | RCI: recursive self-criticism on computer tasks | kim2023rci | Abstract | ✓ |
| 9 | §II-A | Voyager: skill library plus a model-based self-check before committing a skill | wang2024voyager | Abstract (self-verification with GPT-4) | ◐ confirm wording in PDF |
| 10 | §II-B | MiniWoB-style pages; RL / imitation learning | shi2017wob | Abstract | ✓ |
| 11 | §II-B | Mind2Web: a small ranker filters DOM elements, an LLM picks the action | deng2023mind2web | MindAct description | ✓ |
| 12 | §II-B | WebArena: self-hosted sites with functional correctness checks | zhou2024webarena | Abstract | ✓ |
| 13 | §II-B | WebVoyager: live sites from screenshots; a multimodal model judges trajectories | he2024webvoyager | Abstract (GPT-4V evaluator, 85.3% agreement) | ✓ |
| 14 | §II-C | OSWorld: execution-based checkers; large agent–human gap | xie2024osworld | Abstract | ✓ |
| 15 | §II-C | UFO: UI Automation control; asks the user to confirm sensitive actions | zhang2025ufo | Matrix (safeguard) | ◐ confirm in PDF |
| 16 | §II-C | AppAgent learns reusable app documentation | zhang2025appagent | Abstract | ✓ |
| 17 | §II-C | GPTDroid / QTypist: LLMs for GUI testing / text input | liu2024gptdroid, liu2023qtypist | Titles and abstracts | ✓ |
| 18 | §II-D | SeeAct: grounding is the bottleneck; HTML plus image beats Set-of-Mark | zheng2024seeact, yang2023som | Matrix note | ◐ confirm the SoM comparison in the PDF |
| 19 | §II-D | CogAgent, SeeClick locate elements from screenshots | hong2024cogagent, cheng2024seeclick | Abstracts | ✓ |
| 20 | §II-D | OmniParser converts screenshots to structured elements | lu2024omniparser | Abstract | ✓ |
| 21 | §II-E | RAG couples a model with a non-parametric store | lewis2020rag | Abstract | ✓ |
| 22 | §II-E | Sentence embeddings for indexing | reimers2019sbert | Abstract | ✓ |
| 23 | §II-E | Generative Agents: recency, importance, relevance | park2023generative | Paper method | ✓ |
| 24 | §II-E | MemGPT: OS-style paging of context | packer2023memgpt | Abstract | ✓ |
| 25 | §II-F, §VIII | Indirect prompt injection via content the agent reads | greshake2023indirect | Abstract | ✓ |
| 26 | §II-F | Liu et al. formalize attacks and benchmark defenses | liu2024formalizing | Abstract | ✓ |
| 27 | §VIII | Systematic evaluation finds existing defenses insufficient | liu2024formalizing | Extra search this session: pure.psu.edu record and alphaxiv overview state that existing defenses are insufficient (prevention: limited effectiveness and utility loss; detection: high false-negative rates) | ✓ |
| 28 | §II-F | InjecAgent, AgentDojo measure how often agents follow injections | zhan2024injecagent, debenedetti2024agentdojo | Abstracts | ✓ |
| 29 | §II-G | Qwen2.5 / Qwen2-VL come in consumer-hardware sizes | yang2024qwen25, wang2024qwen2vl | Model sizes 0.5B–72B / 2B–72B | ✓ |
| 30 | §II-G | Quantization reduces memory footprint | lin2024awq | Abstract | ✓ |
| 31 | §II-G | Surveys organize profile/memory/planning/action and list trustworthiness as an open problem | wang2024survey, xi2025rise | Matrix notes (Wang: taxonomy; Xi: trustworthiness) | ✓ |
| 32 | Table I | Per-system capability cells | 12 systems | Copied from the matrix comparison table, which is based only on the papers' own reporting. "n.r." means not found in the abstract, venue page or README. | ◐ re-check novelty-driving cells in the PDFs |

## Fixes made during this audit

1. **§II-G.** Changed "surveys note that dependable execution and deployment constraints remain open problems", which was stronger than the matrix supports, to a description of the taxonomy plus trustworthiness.
2. **§VIII.** Changed "denylist can be evaded by paraphrase or encoding [liu2024formalizing]", which attributed our own reasoning to the paper. The citation now supports only "existing defenses insufficient", and the paraphrase remark stands as our own uncited observation about regex matching.
3. **Table I, after the mock review.** WebArena, WebVoyager, OSWorld and AgentDojo "Gate" cells were changed from P to N: their checks are benchmark-side or post hoc, not in-agent at run time, per the column's own definition. Our own Gate cell was changed from Y to P.
4. **Table I.** The matrix row for Agentic Pilot claimed "memory: yes", "injection defense: yes" and "approval: yes". The paper uses P (partial) for all three, with footnotes, per the code audit.

## Author to-do

- Spot-check the ~10 DOIs flagged in the matrix in a normal browser.
- Re-read the PDFs for rows 9, 15, 18 and 32.
