# Updated 18-point compliance matrix

**Status key:**
- **Met**: done with ACTUAL evidence, or a wording/structure change that is fully done.
- **Partly met**: done at component level or by simulation, but the end-to-end evidence the point asks for does not exist.
- **Not met**: cannot be met without running a language model.

Section numbers refer to the current `paper/main.pdf`.

| # | Requirement | Status | Evidence in the paper | What is still missing |
|---|---|---|---|---|
| R1 | End-to-end LLM agent experiments | **Not met** | The harness is implemented and validated with a scripted stand-in model (§VII-B, §VIII-E). The abstract, introduction and conclusion state "No end-to-end evaluation with a language model was executed". | Running `benchmarks/e2e` with Ollama models (`AUTHOR_ACTIONS.md` A1). |
| R2 | Realistic multi-step tasks | Partly met | 40 tasks on 5 self-hosted sites, with tiers and a dev/test split (App. B). | No results on these tasks (R1). |
| R3 | Baselines | Partly met | ACTUAL: the gate vs a dispatch-only rule, with a corrected paired test (Table IV). SYNTHETIC: none, basic, Φ and enhanced (Tables VI–VII). Self-verification is implemented. | Episode-level baselines with a model, and a published-framework baseline (A2). |
| R4 | Ablation study | Partly met | ACTUAL: a per-conjunct ablation on 92 states (Table V). SYNTHETIC: removal of Φ, memory and the recovery engine (Table VIII), with labels that match the code switches. | Memory and recovery ablations on real episodes. |
| R5 | Independent held-out evaluation | Met (component level) | Held-out 2 was frozen in a commit before testing (42 states). The corrected McNemar gives p = 0.021, and the pooled test p = 0.022. Design-set tests were removed as circular. | Held-out states labelled by an independent annotator (A3). |
| R6 | Implemented vs proposed | Met | Table II uses the classes IE/IS/IN/PI/PR with evidence columns. Every proposed component is marked ‡ in the simulation tables. The ablation no longer contains a stored-evidence row that has no code switch. | — |
| R7 | Claim strength ("privacy-preserving", "autonomous") | Met | Privacy is defined in a narrow sense (a loopback model endpoint by default). The stand-in egress test is qualified: Python processes only, no real inference. A "does not cover" list is in §X. Autonomy is scoped to the browser. | An egress test with a real Ollama model, and a system-wide capture that includes Chromium (A-list). |
| R8 | Remove every [Pending] | Met | No `\todo`, "[Pending]" or TBD in the source or the PDF (checked by grep). | The author block must be filled in (A6). |
| R9 | FCR/FRR statistics | Met (component); SYNTHETIC elsewhere | k/n with Wilson intervals. Corrected exact McNemar on paired decision correctness. FCR is flagged as prevalence-dependent. Synthetic p-values are marked as conditional. | — |
| R10 | Independent oracle | Partly met | Gate oracle: written before testing; no shared code. End-to-end oracle: validated on 114 scripted trajectories. "Independent validation" of the simulation is restated as code recomputation only. | Inter-annotator agreement (κ). |
| R11 | Algorithm 1 | Met | Algorithm 1, derived from the code. | — |
| R12 | Verification figure | Met | Fig. 2. | — |
| R13 | Memory/RAG | Partly met | ACTUAL: retrieval on the real store (22 records, 10 queries). SYNTHETIC: repeated workflows, labelled underpowered. Contextual accuracy, which was true by construction, was removed. | A memory evaluation on real episodes. |
| R14 | Recovery strategies | Partly met | ACTUAL: the engine's classification and strategy order. SYNTHETIC: Study E along the code's entry paths. The evidence-guided variant is labelled "by assumption". | Recovery measured on real failures. |
| R15 | Verification overhead | Met (component); SYNTHETIC for episodes | ACTUAL: a median of 26.8 ms with 0 model calls. Percentile method stated. SYNTHETIC: +2.6% mean episode time, including re-planning. | Measured episode overhead. |
| R16 | Table I | Met | Four miscoded cells corrected (Reflexion, WebArena and MemGPT Deploy; MemGPT Env/Eval). Own Env changed to Wr with a footnote. | Five cells the auditor could not verify (`audit_integrity.md` §3.2). |
| R17 | Research gap | Met | G1–G3, mapped to contributions and experiments. | — |
| R18 | Contributions | Met | Scientific and engineering contributions are split. Contribution 3 now says "indicates, under those assumptions". | — |

## Summary

| Status | Count | Items |
|---|---|---|
| Met | 11 | R5, R6, R7, R8, R9, R11, R12, R15, R16, R17, R18. R5, R9 and R15 are met at component level only. |
| Partly met | 6 | R2, R3, R4, R10, R13, R14 |
| Not met | 1 | R1 |

## Notes

- The earlier `RESPONSE_TO_REVIEWERS.md` describes privacy as "model inference restricted to the machine" and says "all 555 socket connections of the agent process". Both are superseded by the qualified wording above.
- The R1 gap cannot be closed honestly by simulation. The paper does not attempt to.
