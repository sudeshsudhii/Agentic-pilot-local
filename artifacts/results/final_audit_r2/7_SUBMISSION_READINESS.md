# Submission readiness assessment

**Verdict.** The paper is ready for submission as a component-evaluated, simulation-based study, once the two mandatory author actions below are done. Every numerical result has been verified. No fabricated or simulated result is presented as an actual or real-world measurement. Hardware testing is not a prerequisite and is not listed as pending.

The independent reviewer (Agent 7), on the version before its corrections were applied, recommended:
- **IEEE conference:** major revision. Its blocking points were length, the weak baseline, the egress tree, the abstract and the process notes; all are now fixed except those requiring the author (below).
- **Workshop:** minor revision.

**Expected reception.**
- **Strengths:** evidence labelling, honesty and reproducibility.
- **Weaknesses:**
  - **Novelty:** checking postconditions in the loop resembles classical execution monitoring.
  - **Technical depth:** the gate is a set of keyword-triggered rule checks.
  - **Evidence:** the gate is not significantly better than its own error check on held-out states, and there is no end-to-end evaluation.

## Mandatory before submission (author)

1. **Release tag.** Tag the final commit, for example `git tag -a paper-ieee-v1.0 && git push origin paper-ieee-v1.0`. Optionally create a GitHub release or Zenodo DOI. Then cite the tag in §V.
   - This is not done automatically, because pushing a tag is a public action.
2. **Author block and acknowledgment.**
   - Fill in `\author{}`.
   - Confirm the acknowledgment's description of the author's own role. If you checked, relabelled or wrote any states or text yourself, say so.
   - For a double-blind venue, replace the GitHub URL with an anonymized mirror and keep the author block empty.

## Recommended improvements

1. **Have at least one person blind-relabel the 54 held-out gate states.** Report agreement (κ), then recompute Table IV with `gate_stats.py`. This is the single most valuable improvement to the gate evidence.
2. **Add related work on execution monitoring and plan verification.** The reviewer flagged this as a novelty concern; cite the classical planning and robotics literature on execution monitoring.
3. **Declare a primary endpoint and a multiplicity policy for the gate study.** For example: the paired correctness against E-only on held-out 2 as primary, with the remaining comparisons descriptive.
4. **Add a script that writes Tables IV and V** from `gate_stats.csv`.
5. **Run `make reproduce-paper` in CI** on the paper branch.

## Optional future work (PROPOSED)

- Run the released end-to-end protocol with local Ollama models (`AUTHOR_ACTIONS.md` A1). This is the only way to support agent-level claims, and it needs no special hardware beyond a machine that can run 1.5B–7B models.
- Derive postconditions per step from the plan, and add a local vision-language judge as a second opinion.
- Run an egress test with a real Ollama model and a system-wide capture (DNS, UDP, Chromium).
- Fix the evidence-file path check in the local API (`tasks.py`). The privacy auditor flagged a possible traversal; the fix is in the code, not the paper.

## Acceptance criteria (from the request)

| Criterion | Status |
|---|---|
| All numerical results verified | ✔ About 120 values recomputed with separate code (0 mismatches); byte-identical regeneration. |
| No fabricated actual experiments | ✔ Every experiment's execution was confirmed from artifacts. The egress run was re-executed on a clean commit. |
| Synthetic and assumed data disclosed | ✔ Six evidence classes; ASSUMED rows in the supplement's parameter table; box and captions in §IX. |
| Statistical interpretations valid | ✔ Structural zeros handled; E-only baseline added; attainable p stated; post-hoc revision disclosed. |
| Hypotheses aligned with conclusions | ✔ Table III reconciles the ACTUAL and SYNTHETIC evidence for each hypothesis. |
| Privacy claims match the evidence | ✔ Narrow sense in the abstract and §XI; process boundaries stated; untested paths listed. |
| Reproducibility sufficient | ✔ Lockfile, `make reproduce-paper`, raw logs and seeds are in place. The release tag is pending (author). |
| No unresolved critical integrity issue | ✔ The acknowledgment is corrected; the author must confirm their role. |
| Hardware not a prerequisite | ✔ |
