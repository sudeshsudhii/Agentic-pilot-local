# Final review: statistics, methodology, research integrity

Paper: `paper/main.tex` at commit e56c293 (paper sources unchanged in dc5f2eb, which was committed while this review ran). No file in the repository was edited. Scripts and builds for this review are in the scratchpad: `recompute_sim.py`, `recompute_gate.py`, `recompute_rates.py`, `wilson.py`, `rerun/` (a `git archive` copy used for reruns), `paper_build/` and `paper_build2/` (compile copies).

## Summary verdict

**Minor revision. No Critical issues.** Every number I recomputed from the raw CSVs matches `results.json`, the generated tables and the prose. That covers the simulation (policy and decision confusion counts, TSR/FCR/FRR, accuracies, Wilson intervals, all exact McNemar p-values, recovery, memory) and the gate study (W, FR, FC/R, McNemar against dispatch-only, ablation, latency). `simulate_v2` rerun in a scratch copy reproduces `results.json`, `scenarios.csv` and `recovery_scenarios.csv` byte for byte. `make_tables` then reproduces all nine `paper/tables/sim/*.tex` files and `ledger_simulation.csv` byte for byte. `gate_stats.py` reproduces `gate_stats.csv` byte for byte. The paper builds with no errors, no undefined references and no overfull boxes; it is 15 pages, and the PDF text is identical to the committed PDF.

Labelling of synthetic, proposed and actual results is consistent. There is one **Major** methodological issue: Study E/C model requests for help (`need_help`) as going "to the engine directly", but the code and the paper's own Algorithm 1 send them through the three inline retries first. This changes the size of the synthetic recovery-ablation effect. The rest are Minor wording, provenance and consistency fixes.

## Recomputed values

Abbreviations: res = `out/heldout_v2/results.json`; gate = `verification_gate_cases*.csv`; abl = `verification_gate_ablation.csv`.

| Quantity | Recomputed (own code) | Source | Paper (location) | Match |
|---|---|---|---|---|
| Policy TP/FP/FN/TN, none | 46/28/3/23; TSR .46, FCR 28/74 = .378, FRR 3/49 = .061 | scenarios.csv | tab sim-baseline, sim-ablation | yes |
| Policy, basic | 43/24/6/27; .43, .358, .122 | scenarios.csv | tab sim-baseline | yes |
| Policy, Φ | 44/19/6/31; .44, .302, .120; F1 .779 | scenarios.csv | tab sim-baseline/ablation; 07b:13 | yes |
| Policy, enhanced | 46/8/8/38; .46, .148, .148 | scenarios.csv | tab sim-baseline | yes |
| Ablation −Φ / −memory / −recovery / mem-filtered | 46/28/3/23; 44/20/6/30 (F1 .772); 35/16/6/43 (F1 .761); 45/19/6/30 | scenarios.csv | tab sim-ablation | yes |
| Wilson intervals (every one in sim-baseline/memory/recovery) | e.g. 44/100 [.35,.54], 52/74 [.59,.79], 87/93 [.87,.97] | wilson.py | tables | yes (all) |
| Claims / true at claim | 74 / 46 | scenarios.csv | 07b:11, abstract | yes |
| Decision TP/FP/FN/TN, acc | none 46/28/0/0 .622; basic 43/24/3/4 .635; Φ 43/19/3/9 .703; enh 41/8/5/20 .824 | scenarios.csv | tab sim-baseline; 07b:15; 05b H2; abstract | yes |
| McNemar FC vs Φ (b/c, p) | none 9/0 .00391; basic 5/0 .0625; enh 0/11 .000977; −Φ 9/0 .00391; −mem 1/0 1; −rec 0/3 .25; filt 0/0 1 | scenarios.csv | tab sim-tests; 07b:13 | yes |
| McNemar decision vs Φ | none 3/9 .146; basic 0/5 .0625; enh 11/2 .0225 | scenarios.csv | tab sim-tests; abstract p=0.15; 07b:15 | yes |
| McNemar success vs Φ | none 3/1 .625; basic 0/1 1; enh 4/2 .6875; −mem 1/1 1; −rec 0/9 .00391; filt 1/0 1 | scenarios.csv | tab sim-tests/ablation; 07b:15,21 | yes |
| Recovery: recovered / detected / FC / unnecessary / mean attempts | inline 29/93, 111/120, 9, 51, 1.283; retry+engine 67/93, 111/120, 9, 162, 3.117; guided 87/93, 118/120, 2, 162, 3.175 | recovery_scenarios.csv | tab sim-recovery; 07b:33; 05b H4 | yes |
| Recovery by mode | matches all 18 cells | recovery_scenarios.csv | tab sim-recovery | yes |
| Guided vs retry paired | 20/0, p = 1.9e-6 | recovery_scenarios.csv | 07b:33 | yes |
| Shares fed back to policy model | on .65, off .27 | recovery_scenarios.csv | tab sim-params | yes |
| Memory subset (n=44) | off 19/12/2/11; on 19/11/2/12; filtered 20/11/2/11 | scenarios.csv | tab sim-memory; 07b:27; 05b H3 | yes |
| Derived rates (k+0.5)/(n+1) | Φ nav 2/6 .36, search 2/4 .50, form 3/6 .50, data 1/3 .38, extr 0/6 .07, multi 2/3 .63; basic .36/.10/.07/.13/.07/.13; FR 0/24 .02 | inputs/m1_gate_rules.csv (identical to gate) | tab sim-params | yes |
| Retrieval P@3 / R@3 / MRR / top-1 bad | .519 / 1.00 / .926 / 3/10 | inputs/m4_memory.csv | tab sim-memory; 07b:27 | yes |
| Component latency median/p95 (ms) | nav 17.14/24.94, click 65.2/106.2, fill 12.5/17.4, DOM 76.4/105.6, screenshot 61.3/93.6, Φ site 5.17/6.93 | inputs/m2_latency.json samples | tab sim-overhead | yes |
| Gate W/n−, FR/n+, FC/R | design before 15/23, 3/15, 8/20; design after 20/23, 1/15, 3/17; HO1 before 1/5, 1/7, 4/10; HO1 after 2/5, 1/7, 3/9; HO2 9/22, 1/20, 13/32; HO1+2 11/27, 2/27, 16/41 | gate | tab gate; abstract; 07:11–13; 08:4; 12 | yes |
| Gate Wilson intervals | all printed brackets | gate | tab gate | yes |
| Gate per-category n−/n+, W, FR | all 36 cells | gate | tab gate (upper block) | yes |
| McNemar correct vs dispatch-only | HO2 9/1 p=.0215; HO1+2 11/2 p=.0225; HO1 2/1 p=1; HO1 before 1/1 p=1 (design not tested: 20/1, 2.1e-5) | gate | tab gate; abstract p=0.021; 07:13 | yes |
| Live modes | before: direct 15, empty 14, verbose 13 withheld (design); after: all modes agree on all 92 | gate | 07:11 | yes |
| Before→after fixed/broken (design) | 7/0 | gate | 07:11 | yes |
| Gate ablation FC/FR, p vs full (design) | E 8/1 .0625; H 7/1 .125; Q 4/1 1; T 6/1 .25; X 6/0 .625; R 4/1 1; β 5/1 .5; held-out cells all match | abl | tab ablation; 07:20 | yes (rounding: see F14) |
| Gate latency (83 non-blocked) | median 26.84, p90 29.49, p95 30.31, max 34.64; blocked max 13.36 | gate | 07:25; tab sim-overhead; abstract "27 ms" | yes |
| Egress | 70 episodes; 555 connects, all 127.0.0.1:11435; non-local page hosts 0; memories > 0 in 54; vision 0; knowledge 0 | e2e_smoke_stub | 07:30; abstract; 09:6 | yes (wording, F10) |
| Oracle validation | 114 trajectories; 37 achieved (35 golden + 2 idle), 77 not; 0 FN, 0 FP; Wilson upper .094 / .048 | e2e_oracle_validation.csv | 07:32 | yes |
| Tests | 144 passed, 3 failed (147) | pytest_revision.txt | 07:30 | yes |
| Task set | 40; dev/test per category and tier as printed | benchmarks/e2e/tasks.json | 13:17 | yes |
| Code facts | backend 11,052 lines; 11 graph nodes; 17 sanitizer patterns | backend/ | 05:4, 04, 09:12 | yes |

Checked only against `results.json` and reproduced by the byte-identical rerun, not with independent code: the Monte Carlo summaries (FCR/TSR/decision-accuracy means and percentiles, FC reduction 0.11 [0.05, 0.18], 94% and 42% shares), sensitivity (Table sim-sens, Fig. sim-sens, 07b:46), latency model (18.1/18.9/21.2/22.6 s medians, +2.6%, 80%/0.11%/4.1% shares, 10.0/36.8 s sweep). All printed values match `results.json`.

## Findings

1. **Major. Study E/C path for requests for help contradicts the code.** Locations: `07b_simulation.tex:33` ("navigation failures and requests for help go to the engine directly"), `tables/sim/recovery.tex:3` ("Entry paths and strategy sequences follow the code"), `simulate_v2.py` (`ENTRY["unexpected_state"]="engine"`, message "…need_help").
   - Evidence: `execute_action_node` turns `need_help` into `error=…` (`backend/agent/nodes.py:984-989`). `verify_node` tests `state["error"]` before its `need_help` branch, so the request is retried three times inline first (`nodes.py:1367-1380`); the `need_help` branch at 1382 is unreachable in normal flow. The engine then receives "Max retries exceeded: <reasoning>", which it classifies as unknown, not vision_needed. The repository's own test log shows this: `pytest_revision.txt:16`, "Unclassified failure during need_help: Max retries exceeded: …". Algorithm 1 (lines 16–18) also shows inline retries for any failed dispatch.
   - Two further simplifications: (a) mid-task `navigate` actions also take the inline path; only the initial `navigate_node` goes to the engine. (b) `executor.navigate` already makes 3 attempts on transient `net::ERR_` errors (`backend/browser/executor.py:164-188`), so "inline retries only: 0/16 navigation" understates the implementation.
   - Impact: I reran the model in scratch with only the `unexpected_state` path made code-faithful. Recovery without the engine becomes 39/93 instead of 29/93 (unexpected state 10/14 instead of 0/14), and the share fed back becomes 0.37 instead of 0.27. The Study C "−recovery engine" TSR becomes 0.37 instead of 0.35, and success discordance 0/7 with p=0.016 instead of 0/9 with p=0.0039. The direction is unchanged; the size and the claim "follows the code" are not.
   - Fix: model `need_help` as inline then engine with the "Max retries exceeded" message. Either model executor-level navigation retries or state that a simulated navigation failure is one that survives them, and that only the initial navigation bypasses inline retries. Regenerate Tables sim-recovery, sim-ablation and sim-params, and edit 07b:21,33. Alternatively, state the simplification explicitly and drop "follow the code".
2. **Minor. "Independent validation" does not cover the reported numbers.** Location: `06_methodology.tex:45`, `14_simparams.tex:4`. The validation report covers v1 (`out/heldout`); all reported numbers are v2. The validator ran in the same authoring pipeline: its report names the same scratchpad path as this session. Fix: say plainly that v2 was not independently validated by the authors' validator. Optionally cite this review's recomputation, which matches all v2 policy, decision, paired and recovery values. Use "separately written code" instead of "independent".
3. **Minor. Rule on design-state tests is applied inconsistently.** Location: `tables/ablation.tex` p column and caption; `07_results.tex:20`. Table gate refuses tests on design states as circular, but Table ablation reports McNemar p only on design states. No significance is claimed (all p ≥ 0.06), and the text correctly avoids reading non-significance as no effect. Fix: drop the p column, or move it to held-out sets and note that design p-values are optimistic for the same reason.
4. **Minor. The abstract over-attributes the held-out drop.** Location: `00_abstract.tex:2`, "because its answer check depends on request wording". Of the 13 held-out-2 misses, extraction (X) accounts for 5. The other 8 are search 1, navigation 3, bot check 1, text entry 2 and multi-step 1, from error pages, unparsed text-entry phrasings and redirects (07:13). Fix: "because its checks are keyed to request wording".
5. **Minor. The ablation definition contradicts the code.** Location: `tables/e2e_design.tex:17`, `no_recovery`: "failures not retried". With `enable_recovery=False` the engine fails at once (`backend/recovery/engine.py:133`), but the 3 inline retries in `verify_node` remain, as `tables/sim/ablation.tex` itself says. Fix: "recovery engine off; inline retries remain".
6. **Minor. A count is misstated.** Location: `07b_simulation.tex:15`, "false rejections cost a few successes, and continuation after a correct rejection recovers about as many". The data show 3 successes lost and 1 recovered (success discordance 3/1). Fix: "…cost 3 successes; continuation recovers 1".
7. **Minor. Discordant-pair order is inconsistent.** Location: `07b_simulation.tex:15`, "discordant pairs 1 and 3" (Φ first). Line 13 and Table sim-tests give the other configuration first (3/1). Fix: write "3 and 1 (b/c as in Table sim-tests)".
8. **Minor. Sample description is ambiguous and a range is incomplete.** Location: `06_methodology.tex:30`.
   - "the 22 and 5 unsatisfied states, without the bot-check category" reads as 27 states. Detection actually uses 22 states (18 from held-out 2 and 4 from held-out 1).
   - "a small nonzero rate (0.07–0.13) where none was observed" omits FR 0/24 → 0.02.
   - Fix both wordings.
9. **Minor. Estimator stated inconsistently.** Location: `tables/sim/params.tex` caption, "DERIVED rates use (k+0.5)/(n+1)". The misleading-retrieval rate is used as the raw 3/10 = 0.30, while the Jeffreys estimate is 0.32 and the Monte Carlo draws Beta(3.5, 7.5). Fix: state the exception or use 0.32.
10. **Minor. Wording on memory retrieval.** Location: `07_results.tex:30`, "memory retrieval ran in 54 of them". Sixty episodes had memory enabled; `memories_retrieved > 0` holds in 54, and the first episode per configuration starts with an empty store. Fix: "returned at least one memory in 54 of the 60 memory-enabled episodes".
11. **Minor. Title overreaches the locality evidence.** Location: `main.tex` title ("Privacy-Preserving") and keywords; intro contribution 5 ("addressing G3"). The egress evidence is Python-process connect calls with a scripted stand-in model server; the driver, Chromium, DNS and a real model server were not observed. The text qualifies this well (01:13, 09:6, threats table). Fix: qualify the title (e.g. "Loopback-Only Inference") or keep it but change contribution 5 to "partially addressing G3".
12. **Minor. One table mixes two machines.** Location: `tables/sim/overhead.tex`, upper block. "Φ on gate states 26.8 ms" was measured on 2026-10-04 on a 2.1 GHz Xeon (06:4); the other rows were measured on 2026-10-23 on a 2.8 GHz Xeon (06:30). Fix: note the two machines in the caption.
13. **Minor. Egress run is not tied to a commit.** Location: `07_results.tex:30`. The run used an uncommitted tree on 1435fe9 at 07:20 UTC (`run_meta.json`). The locality enforcement and ablation switches were committed later, in 55ac1ea (07:28). This is disclosed, but the tested code cannot be recovered. Fix: rerun the 70-episode check on HEAD (agent code bf0a8a5) and cite that commit.
14. **Minor. Rounding is inconsistent.** Location: `tables/ablation.tex`. 0.125 is printed as .12 and 0.625 as .62, while 07b:15 prints 0.625 as 0.63. Fix: use one rule throughout (round half up: .13, .63).
15. **Minor. Provenance of two p-values.** Location: `tables/gate_results.tex` caption, "Source: gate_stats.csv (column p_correct_vs_dispatch)". The "before" rows are not in `gate_stats.csv`; they are in `gate_stats_corrected_tests.csv`, which no script in the repository produces. Fix: add its generator or compute the before rows in `gate_stats.py`, and cite both files.
16. **Minor. Overstatement about where defects appeared.** Location: `08_discussion.tex:4`, "Its defects showed up only when it was tested inside the live node". Called directly, the pre-fix gate already missed 8 of 23 design states; the live node revealed additional node defects (15 → 14/13). Fix: "Some of its defects showed up only…".
17. **Minor. Overstatement about the harness.** Location: `06_methodology.tex:22`, "every host the browser contacted". The harness records page-request hosts reported by Playwright; browser-internal traffic, WebSockets and DNS are not seen (07:30, 09:6). Fix: "the host of every page request Playwright reports".
18. **Minor. Unverifiable claim.** Location: `14_simparams.tex:4`, "Assumed values were chosen to be neither favourable nor unfavourable to verification". No procedure supports this. Fix: delete it, or replace it with "the two most influential assumptions are swept (Study H)".
19. **Minor. Status classes understate actual measurements.** Location: `tables/status.tex`. "Memory store retrieval" and "Recovery engine: classification" are classed IS ("studied only by simulation"), but both have ACTUAL component measurements (Table sim-memory upper block; m3). Fix: IE (component) for retrieval ranking and classification, IS for their effect.
20. **Minor. Synthetic tests that are uninformative by construction.** Location: `07b_simulation.tex:13` and Table sim-tests. FC McNemar p (0.004) and "p<0.05 in 94% of sets" come from a test whose c-cell is 0 by construction. This is disclosed; the p adds no information beyond the count. Fix: report only the reduction and its Monte Carlo interval, or mark the p as a structural consequence.
21. **Minor. Wording.** Location: `07b_simulation.tex:33`, "Neither recovers missing confirmations (2 of 20, both by continuation)". Fix: "Neither recovers more than 2 of 20 missing confirmations (both by continuation)".
22. **Minor. Reproducibility pointers are missing or stale.**
    - The before-fix decisions come from code 08653e2 (commit message of b55670b), which the paper does not cite.
    - The "statistical correction report" (06:34) has no path. It is now `artifacts/results/final_audit/1_STATISTICAL_CORRECTION_REPORT.md`.
    - The `simulate_v2.py` docstring cites `artifacts/results/audit_*.md`, which are now under `final_audit/`.
    - `out/heldout/` is a byte-identical duplicate of `out/heldout_v1/`.
    - Fix: cite 08653e2 and the report path, and remove or rename the duplicate directory.
23. **Minor. Hypothesis-table wording.** Location: `05b_hypotheses.tex:17`. H2 reads "not supported for Φ" without the sample-size qualifier used in 07b:15. Fix: "not supported at n=74 (MC: significant in 42% of sets)".
24. **Minor. Configuration name mismatch.** Location: `tables/e2e_design.tex`. The table says `vision_only`; `run_e2e.py` defines `vision_only_grounding`. Fix: rename one so they match.
25. **Minor (venue). Page count.** The paper is 15 pages including appendices. Check it against the target venue's limit.

### Integrity checks with no issues found

- Synthetic results are labelled as SYNTHETIC wherever they appear: the boxed notice, every sim caption, the abstract, the hypotheses table and the conclusion.
- Proposed components carry ‡ / PR / "proposed" everywhere: enhanced validation, evidence-guided recovery, relevance filter, desktop backend.
- Non-significance is not presented as evidence of no effect (H3, the ablation, held-out 1).
- Ablation labels match the code switches: `verification_mode`, `enable_memory`, `enable_recovery` and `enable_evidence` in `backend/config.py:37-48`; `enable_rag` gates RAG in `backend/rag/*.py`.
- "Inline retries remain when recovery is disabled" matches `nodes.py:1376` and `engine.py:133`.
- Held-out 2 was frozen: the SHA-256 of `gate_heldout2.py` matches `gate_heldout2_freeze.txt`. The freeze commit b9d5088 (07:21:57) precedes the results commit 55ac1ea (07:28:30). The gate code diff between them adds only switches that are off by default.
- Simulation parameters in `params.json` are unchanged since freeze commit 3a0aa8e.

## Reproducibility

- **Commits:** 1435fe9, 2361d50, 3a0aa8e, 41a6097 and bf0a8a5 all exist and are on `origin/ccr-4b8200f0-5i3k5m`. `git log bf0a8a5..HEAD -- backend/` is empty, as the paper claims. The claim about the 2361d50 extraction handler is confirmed (`nodes.py:1110-1129` at that commit). The repository is public, under the MIT licence, at the cited URL.
- **Paths:** every `\texttt` path or file in the paper exists, except the `vision_only` configuration name (F24).

## Compile check

The paper was copied to the scratchpad and built twice there.

- **`pdflatex` ×2 with the committed `.bbl`:** 0 errors, 0 undefined references or citations, no rerun warnings, 0 overfull boxes. There are 47 underfull boxes, mostly badness 10000 in narrow `p{}` table columns. Output is **15 pages** (407,009 bytes), and its text is identical to the committed `paper/main.pdf`.
- **Full rebuild with `bibtex`:** 0 bibtex warnings.

## Not checked

- Monte Carlo, sensitivity and latency-model values were checked only against `results.json`; they are reproduced by the byte-identical rerun but not by independent code.
- Oracle labels of the 92 gate states and the 40 e2e tasks (no relabelling).
- Correctness of `fake_ollama.py` and the egress socket logger.
- Whether the "before fixes" decisions reproduce from 08653e2 (that code was not rerun).
- Literature claims and the related-work table.
- The 06:32 claim that Studies A–E/H were unchanged by 41a6097 (pre-change outputs are not available).
- Figures other than the sensitivity plot coordinates (checked) and the algorithm and loop structure (checked).
