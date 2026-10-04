# Change log: revision for R1–R18 (2026-10-04)

**Commits on branch `ccr-4b8200f0-5i3k5m`, in order:**
1. `1435fe9`: audit and plan (`artifacts/12_revision_audit.md`).
2. `b9d5088`: freeze of held-out set 2.
3. `55ac1ea`: code, harness and statistics.
4. `bf0a8a5`: oracle validation (the code commit the paper describes).
5. `a86183a`: revised paper.
6. The commit that adds this file.

## 1. Code (`backend/`)

| File | Change | Behaviour in normal use |
|---|---|---|
| `security/locality.py` (new) | `is_loopback_url`, `require_local_endpoint`, `local_chroma_settings` | — |
| `config.py` | `allow_remote_model` (default False); `verification_mode` (`rule`/`self`/`none`); `verification_disabled_checks`; `recovery_fixed_strategy` | Defaults reproduce the previous behaviour, except that a non-loopback model endpoint is now refused |
| `llm/gateway.py` | Endpoint check before the client is created; process-wide `usage` counters (calls, prompt/completion tokens from Ollama, latency) | Unchanged, apart from the refusal |
| `rag/store.py`, `memory/provider.py` | Chroma clients created with `anonymized_telemetry=False` | No telemetry |
| `security/audit.py` | Locality decided by the parsed host, not a substring test. Before, `http://example.com/?h=127.0.0.1` counted as local. | Bug fix |
| `verification/manager.py` | Per-conjunct switches (E, H, Q, T, X, R); `self_verify_completion` (self-verification baseline) with `SelfCheck` schema | Unchanged when no switch is set |
| `agent/nodes.py` | `verify_node`: β switch (B); `verification_mode` dispatch; check latency and self-check model calls recorded in the `VERIFICATION_RESULT` event; self-check calls count towards the 15-call budget | Unchanged in `rule` mode |
| `recovery/engine.py` | Optional pinned strategy | Unchanged by default |

**Bug introduced and fixed during this revision:** the first version of the E switch still left E's expected value in the final comparison, so "without E" still rejected error pages. This was found in the first ablation run and fixed before the reported run. The normal path was not affected. Both logs exist only in this session's history; the reported log is `verification_gate_ablation.log`.

## 2. New experiment code and data

| Path | Content |
|---|---|
| `benchmarks/e2e/sites.py` | Five self-hosted sites with fictional content; server-side state for oracles |
| `benchmarks/e2e/tasks.json` | 40 tasks (10 dev / 30 test), categories, tiers, oracles |
| `benchmarks/e2e/oracle.py` | Independent oracle Φ* |
| `benchmarks/e2e/run_e2e.py` | Runner: one process per configuration, environment record, per-episode JSONL |
| `benchmarks/e2e/analyze_e2e.py`, `stats.py` | Wilson and Clopper–Pearson intervals, exact McNemar, cluster bootstrap; LaTeX tables |
| `benchmarks/e2e/validate_oracle.py` | Golden, idle and perturbed scripted trajectories |
| `benchmarks/e2e/fake_ollama.py` | Scripted stand-in for the Ollama API (pipeline and egress tests only) |
| `benchmarks/e2e/egress/sitecustomize.py` | Socket-connection logger |
| `artifacts/experiments/gate_heldout2.py` | Held-out set 2 (42 states), frozen in `b9d5088` |
| `artifacts/experiments/verification_gate_study.py` | Adds held-out 2 and `--ablation` |
| `artifacts/experiments/gate_stats.py` | Intervals and paired tests |
| `tests/test_local_egress.py` | 18 tests, including a full agent episode with no non-loopback connection |

## 3. Results produced in this revision (`artifacts/results/`)

| File | Content |
|---|---|
| `verification_gate_cases.csv`, `_summary.csv`, `_run.log` | Re-run on current code. All 50 earlier states have identical decisions to the earlier run (checked); adds held-out 2. |
| `verification_gate_ablation.csv`, `.log` | Per-conjunct ablation, 92 states × 8 settings |
| `gate_stats.csv`, `.txt` | All intervals and p-values in Tables IV and V |
| `gate_heldout2_freeze.txt` | SHA-256 of the frozen held-out file |
| `e2e_oracle_validation.csv`, `.txt` | 114 trajectories, 0 FN / 0 FP |
| `e2e_smoke_stub/` | 70 stand-in episodes. **Not results**, except `egress_summary.json` (555/555 connections to 127.0.0.1). |
| `pytest_revision.txt`, `junit_revision.xml` | 147 tests: 144 pass, 3 fail (need live web) |

## 4. Paper

| Element | Change |
|---|---|
| Abstract | Rewritten with the new evidence and an explicit "no end-to-end run" statement |
| §I | Gaps G1–G3 (R17); scope and terms for autonomy and privacy (R7); contributions split into scientific and engineering (R18) |
| §II, Table I | Trimmed. Table I rebuilt (R16); VisualWebArena and WorkArena added; 3 uncited references removed |
| §III | Browser-focused formulation; FCR/FRR with explicit counts; withheld share; no-threshold statement (R9) |
| §IV | Algorithm 1 (R11); Fig. 2, the verification pipeline (R12), replacing the state-machine figure; computer backend moved to Appendix A |
| §V, Table II | Status table with an Eval column and the claim restriction (R6); locality enforcement and experiment switches |
| §VI | Gate study with three splits, oracle definition and statistics (R5, R9, R10); end-to-end harness, tasks, oracle and protocol (R1–R3); Table III, the design (replaces the old protocol table) |
| §VII | Table IV (CIs, p, categories); Table V (ablation); overhead; locality and oracle validity; end-to-end "not run" statement |
| §VIII–XII | Rewritten to match the evidence; §IX threat model, privacy property, autonomy; §X adds statistical power |
| Appendix A, B | Computer-backend design with the postcondition table; task-set summary |
| `main.tex` | `algorithm`/`algpseudocode`; `\todo` macro removed; `\author{}` left for the author |

## 5. Changed or corrected values

| Earlier statement | Now | Reason |
|---|---|---|
| Gate latency median 30.6 ms (max 39.5) over 35 design decisions | 26.8 ms (p90 29.5, max 34.6) over 83 decisions in all sets; design only 27.9 ms | Re-measured on this container (Xeon 2.1 GHz) with the same code. Not an error; timing differs between machines. |
| "4-core Intel Xeon at 2.8 GHz" | 2.1 GHz for the current-code runs | The current runs used a different container (`/proc/cpuinfo`) |
| 129 tests, 126 pass | 147 tests, 144 pass, 3 fail (need web) | 18 new tests |
| 10,867 lines | about 11,000 | New code |
| Held-out evidence: 12 states | 12 + 42 states | R5 |

**Errors in original numbers:** none found. All 50 earlier states give the same decisions on re-run. The before-fix counts in Table IV (design 15/23 withheld, 3/15 rejected; live 13–14) match the earlier CSVs.

## 6. Sources of every number in the revised paper

| Claim | Source |
|---|---|
| 20/23, 1/15, 15/23 before, 3/15 before, 9/22, 1/20, 11/27, 2/27, 2/5, 1/7; FC/R; Wilson CIs; McNemar p (<.001, .50, .004, .001, .016) | `gate_stats.txt` |
| Per-category W/FR (Table IV) | `verification_gate_summary.csv` |
| Ablation counts and p (Table V) | `verification_gate_ablation.log`, `gate_stats.txt` |
| Live modes agree on every state; live before-fix withheld 14/13 | `verification_gate_cases.csv`, `_before_fixes.csv` |
| Latency 26.8 / 29.5 / 34.6 ms over 83 decisions; pre-check at most 13.4 ms | `verification_gate_cases.csv` (`gate_ms_median`) |
| 70 episodes, 555 connections, all to 127.0.0.1 | `e2e_smoke_stub/egress_summary.json` |
| Oracle 0/37 FN, 0/77 FP, 114 trajectories | `e2e_oracle_validation.txt` |
| 144/147 tests | `pytest_revision.txt` |
| 40 tasks, 10/30, 5 unsatisfiable, tier and category counts | `benchmarks/e2e/tasks.json` |
| Held-out 2 frozen before testing | commit `b9d5088` precedes `55ac1ea`; SHA-256 in `gate_heldout2_freeze.txt` |
| 17 sanitizer patterns, approval triggers, recovery behaviour, router models | code (unchanged from the earlier audit, `artifacts/07_claims_ledger.md`) |
