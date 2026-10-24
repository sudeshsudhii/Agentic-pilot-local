# Final audit report (round 2)

**Inputs.** The paper as of commit `aee8c50` ("main-8"), audited by seven agents:
1. methodology;
2. statistics;
3. experimental evaluation;
4. research integrity;
5. privacy and security;
6. reproducibility;
7. independent academic reviewer.

**Outputs.** Corrected paper `paper/main.pdf` (8 pages + references) and `paper/supplement.pdf`, at the final commit of branch `ccr-4b8200f0-5i3k5m`. The full agent reports are in this folder as `agent_r2_*.md`.

**Status key:** **Fixed**: corrected in the paper or artifacts. **Disclosed**: cannot be fixed with the available evidence, so it is stated in the paper. **Author**: needs the author.

## Critical and major issues

| # | Source | Issue | Correction | Status |
|---|---|---|---|---|
| 1 | Integrity F1 | The acknowledgment understated the AI's role. "One author" wrote the labels, but git shows the AI agent wrote the states, labels, simulation, fixes and text. | Acknowledgment rewritten. The methodology and limitations say the AI agent wrote the labels and no person has relabelled them. | Fixed; **the author must confirm their own role** |
| 2 | Reviewer A4 | The only inferential baseline was dispatch-only, which is trivially weak. | Gate vs the measured error-check-only detector added: held-out 2 p = 0.070, pooled p = 0.11, not significant. Shown in Table IV and the text, and claims qualified throughout. | Fixed |
| 3 | Reviewer A10 | 17 pages against an 8-page limit. | Full simulation, ablation, implementation audit, harness, design appendix and threat table moved to a cross-referenced supplement. Paper is now 8 pages + 2 of references. | Fixed |
| 4 | Reviewer A5; experiments F1 | Egress run on an uncommitted tree; raw log not in the repo. | Raw logs committed with SHA-256. `run_egress.py` added and **rerun on clean commit `7133301`**: same result. `summarize_egress.py` added. | Fixed |
| 5 | Stats F1 | McNemar p printed for structurally zero cells in Table VII. | p removed for those cells; the paired ΔFC with its Monte Carlo interval is shown instead. The Basic zeros are explained as nesting, not structure. | Fixed |
| 6 | Methodology 1 | A simulated "claim" did not match the code's Φ trigger. | "Claim" defined as any point where the code evaluates Φ. The `no_verification` description corrected. | Fixed |
| 7 | Methodology 2 | The retry counter was described as per action; it is per task. | Architecture text and recovery caption corrected. | Fixed |
| 8 | Methodology 3; integrity F14 | H2 "not supported" was not reconciled with the component evidence. | Table III and §VI give the ACTUAL 28 vs 20 (p = 0.021; vs E only 0.070) next to the SYNTHETIC p = 0.15. They also note that 2 of 3 synthetic false rejections come from an ASSUMED rate. | Fixed |
| 9 | Integrity F4 | Five evidence classes listed; ASSUMED missing; labels inconsistent. | Six classes defined. Parameter-table classes corrected: "mapping ASSUMED", "via ASSUMED proxy", "SYNTHETIC (Study E)". | Fixed |
| 10 | Integrity F2, F7–F11 | Synthetic results phrased as performance; "inside the live loop"; "measured misleading rate". | Rephrased: "simulated configuration", "real verification node called directly with stubbed I/O", "derived; mapping assumed". | Fixed |
| 11 | Integrity F12; stats F7 | Post-hoc v2 not fully disclosed. | Disclosure now covers: the direction of the changes (all in Φ's favour); the second revision; the decision-level outcome defined after the v1 results; "post hoc" in captions; the v1 freeze sentence scoped to v1. | Fixed |
| 12 | Privacy M1–M3 | Abstract privacy sense; local API exposure; untested paths. | Abstract states the narrow sense. Added: no Host/Origin check on the API; proxy environment variables; monitoring-UI fonts; process boundaries of the instrumentation; threat rows. | Fixed |
| 13 | Experiments F4 | Study E reused random draws for attempts 7–9. | Separate stream added. No output changed (verified). | Fixed |
| 14 | Experiments F3 | Oracle validation overstated. | Restated as 35 solutions and 34 near misses (0–0.10). The rest are negative by construction. | Fixed |
| 15 | Reviewer A1 | Abstract 310 words. | 249 words. | Fixed |
| 16 | Reviewer A2, A3; reproducibility 1 | No release tag; author username in the URL (double-blind). | Branch and commit cited. | **Author**: tag the release and anonymize the URL if the venue is double-blind |
| 17 | Reviewer A6 | AI-only labels; no inter-annotator agreement. | Disclosed in the methodology, limitations and acknowledgment. | **Author** (recommended): a human relabels the 54 held-out states and reports κ |

## Minor issues

All are fixed unless noted.

**Statistics:**
- p-value convention: 2 significant figures, half up.
- Attainable-p statements for the ablation and held-out 1.
- "Significant share" wording.
- Monte Carlo limits (independent Basic/Φ draws; fixed assumed values) disclosed.
- P@3 stated as the attainable maximum.

**Methodology:**
- Algorithm 1 blocked and budget paths.
- E definition completed.
- Recovery-strategy count.
- H3/H5 dependent variables.
- Latency-model inputs.
- "By construction" holds in the model only.
- H never fires on the harness sites.
- Repetition cut throughout.

**Integrity:**
- Oracle "no code shared" wording.
- "Tested" changed to "examined" for simulation.
- Held-out wording for synthetic data.
- Related-work footnote d.
- Status table split into harness and oracle.
- "Honest estimate" removed.
- SeeAct / Set-of-Mark and Qwen citations reworded.
- lukas2023pii context corrected.

**Experiments:**
- β ablation mechanism.
- Freeze wording.
- Before-fix provenance.
- Self-check is cost only.
- Parameter table completed.
- `gate_stats.txt` regenerated.
- Test command and date.

**Reproducibility:**
- `requirements-paper.lock` added.
- `make reproduce-paper` added.
- Deterministic PDF build.
- Repo-relative validator and recomputation scripts (archived).
- `out/README.md` added.
- Dev outputs refreshed.
- `gate_stats.py` fails loudly on missing input.
- Documentation drift fixed.

**Still open:**
- Hand-copied gate tables: values verified, but no generator script.
- No CI for the paper chain.

**Title.** Kept as the author decided. The integrity auditor and the reviewer noted that "Privacy-Preserving" and "Intelligent Task Automation" go beyond the evidence. The abstract and §XI qualify both.

## Verification after the corrections

**Statistics:**
- The statistical auditor recomputed about 120 values: 0 mismatches.
- The final reviewer spot-checked 16 groups: all match.

**Reproducibility:**
- `simulate_v2` → `make_tables` → `gate_stats.py` reproduce byte for byte.
- The paper and supplement build with 0 errors, 0 undefined references, 0 overfull boxes and 0 multiply-defined labels.
