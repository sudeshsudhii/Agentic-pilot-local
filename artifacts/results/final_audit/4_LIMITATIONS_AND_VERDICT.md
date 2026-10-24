# Remaining limitations and submission-readiness verdict

## Verdict

**Ready for submission as a component-level and simulation study, with three conditions.** It is **not** ready as an empirical evaluation of an autonomous agent.

**Integrity: no blocking issue.**
- Every number in the paper traces to a dataset, a script or a cited source.
- The independent final review recomputed all policy-level, decision-level, paired-test, recovery, memory and gate values with separately written code and found no mismatch (rerun after the last correction).
- Synthetic, proposed and actual results are labelled throughout.

**Conditions before submission:**

1. **Page limit.** The PDF has 15 pages, and the body runs to about page 12 with its floats. An 8-page IEEE conference limit is not met.
   - The author must move material to an appendix or supplement. Candidates: Tables XI, XII and XVI, Fig. 3, and Table VIII.
   - Alternatively, target a venue with a longer limit or a journal.
   - This is an editorial decision for the author; no evidence is affected.
2. **Author block, release tag and link.**
   - Fill in the author block.
   - Create a release tag for the evaluated branch `ccr-4b8200f0-5i3k5m`. Its agent code has been unchanged since commit `bf0a8a5`.
   - Cite the tag. The default branch has diverged and must not be cited.
3. **Title.** The author asked to keep "Privacy-Preserving". The body supports only a narrow claim: a loopback model endpoint by default, tested with a scripted stand-in model server.
   - Reviewers may object to the title.
   - The abstract, introduction ("partially addressing G3") and Section XI carry the qualification.

## What the paper can claim

| Class | Claim |
|---|---|
| ACTUAL | The gate withheld 20/23 unsatisfied design states (counts only; tests on these states would be circular). It withheld 9/22 held-out-2 states with 1/20 false rejections (paired test p = 0.021) and 11/27 pooled (p = 0.022). Median 26.8 ms per decision, with no model call. |
| ACTUAL | A per-conjunct ablation. Retrieval ranks on a 22-record synthetic corpus. The recovery engine's classification. 555 connect calls of the Python processes, all to loopback, in 70 episodes with a stand-in model server. |
| SYNTHETIC (conditional; v2 is post hoc) | False completions are lower with Φ (19 vs 28; this direction is guaranteed by construction). Decision accuracy is not significantly better (52 vs 46 of 74, p = 0.15). Memory is underpowered. Recovery with the engine recovers 68/93 vs 51/93 without it. The evidence-guided variant's 87/93 holds only by assumption. Overhead is +2.6% of mean episode time. |
| NOT EXECUTED | End-to-end evaluation with a language model: task success, the self-verification baseline, and memory or recovery on real episodes. |

## Remaining limitations

1. **No end-to-end evidence (R1).** Every claim about agent-level effectiveness is conditional or absent.
2. **Simulation validity.**
   - Planner behaviour (π = 0.65), continuation (0.35), action failure (0.25), memory gain/loss and the per-attempt recovery rates are assumed.
   - The derived rates rest on small samples: 3 multi-step states, 6 extraction states, 24 satisfied states.
   - The (k + 0.5)/(n + 1) estimator gives nonzero rates where none was observed.
3. **The reported model (v2) is post hoc.**
   - It was corrected after v1 results and audits were known, and once more after the final review (recovery entry paths).
   - The direction of every correction was chosen to match the code, but the choice was made with the results in view.
   - v1 is archived, and all changes are listed in `changed_numbers_ledger.csv`.
4. **Gate study.**
   - The states were constructed by one author, so inter-annotator agreement is not possible.
   - The states are template-like, which strains the independence assumption behind the intervals.
   - FC/R depends on the constructed prevalence.
   - Rule coverage of new phrasings is the binding limit: the extraction check withholds 0/5 held-out states.
5. **Locality.**
   - Only Python-process connect calls were logged.
   - Chromium's own traffic and real Ollama inference were not covered. Ollama cloud models and tunnels can send requests off the machine.
   - The run used an uncommitted tree based on `1435fe9`; the enforcement code was committed later, in `55ac1ea`.
   - **Rerunning the egress test on the evaluated head is recommended.**
6. **Validation.**
   - Recomputation was done by agents in the same authoring pipeline, with separately written code. It is not human annotation and not an independent replication.
   - Monte Carlo, sensitivity and latency values were checked only by a deterministic rerun.
7. **Unverifiable items.**
   - Five cells of Table I could not be verified against their papers.
   - The pre-fix gate decisions (`08653e2`) were not re-executed.
   - The outputs from before the `41a6097` latency fix were not kept.

## Recommended author actions, in priority order

1. Run the end-to-end protocol with local Ollama models (`AUTHOR_ACTIONS.md` A1). This is the only way to support agent-level claims.
2. Shorten the paper to the venue's limit.
3. Tag the release, cite the tag, and fill in the author block.
4. Rerun the egress test on the tagged head, with a real Ollama model and a system-wide capture.
5. Have a second annotator label the held-out gate states (κ).
