# Evidence provenance matrix

**Classes:**

| Class | Meaning |
|---|---|
| ACTUAL | Genuinely executed or measured on the implementation |
| SYNTHETIC | Produced by the simulation |
| ASSUMED | An input value chosen by the authors |
| DERIVED | Computed from existing results |
| LITERATURE | Taken from cited work |
| PROPOSED | Not implemented, or not yet done |

No result in the paper comes from physical hardware testing, and none is required.

| # | Result as stated in the paper | Class | Source (file) | Generator / command | Scope and caveats |
|---|---|---|---|---|---|
| 1 | Held-out 2: gate withholds 9/22 unsatisfied states, rejects 1/20 satisfied; paired correctness 28 vs 20 of 42, McNemar p = 0.021 | ACTUAL (test: DERIVED) | `artifacts/results/verification_gate_cases.csv`, `gate_stats.csv` | `verification_gate_study.py`; `gate_stats.py` | Constructed states. The real verification node is called directly with stubbed I/O. States and labels were written by the AI agent; there is no second annotator. The held-out set was frozen at `b9d5088` before testing. |
| 2 | Pooled held-out 11/27, 2/27, p = 0.022; held-out 1: 2/5, 1/7, p = 1.0 | ACTUAL / DERIVED | same | same | — |
| 3 | Design set 20/23, 1/15; before the fixes 15/14/13 of 23; 7 fixed, 0 broken | ACTUAL | `verification_gate_cases*.csv` | same; before-fix code from `08653e2` | Optimistic, because the fixes were designed on these states. No test is reported. |
| 4 | Per-conjunct ablation (Table V) | ACTUAL | `verification_gate_ablation.csv` | `verification_gate_study.py --ablation` | Predicate called directly. β is skipped by a script argument. p-values are descriptive only. |
| 5 | Gate decision latency: median 26.8 ms (P90 29.5, P95 30.3, maximum 34.6), n = 83 | ACTUAL | `verification_gate_cases.csv` | gate study, 20 repetitions | 2.1 GHz container, 2026-10-04. Percentiles are of per-state medians. |
| 6 | Component latencies (navigation, click, fill, DOM, screenshot, Φ 5.2 ms on site pages) | ACTUAL | `benchmarks/simulation/inputs/m2_latency.json` | `measure_inputs.py` | 2.8 GHz container, 2026-10-23. 30 repetitions. Self-hosted sites. |
| 7 | Recovery engine: classification and strategy order for 6 failure messages; missing confirmation classed as unknown | ACTUAL | `inputs/m3_recovery.csv` | `measure_inputs.py` | Real `RecoveryEngine`. The entry paths come from code inspection. |
| 8 | Memory retrieval: P@3 0.52 (attainable maximum), R@3 1.00, MRR 0.93; no relevance threshold; 3/10 top-1 irrelevant or failed | ACTUAL (synthetic corpus) | `inputs/m4_memory.csv` | `measure_inputs.py` | 22 records; relevance labelled by group (loose). |
| 9 | Locality: 70 episodes; 555 connects of the Python processes, all to the stand-in on 127.0.0.1. Rerun 2026-10-24 on clean commit `7133301` (agent code = `bf0a8a5`) with the same result. | ACTUAL | `artifacts/results/e2e_egress_rerun/` (clean run); `e2e_smoke_stub/` (original run) | `python benchmarks/e2e/egress/run_egress.py <out>`; `summarize_egress.py` | Scripted stand-in model server, so no real inference. Python `connect` / `connect_ex` only. **Not covered:** UDP, DNS, Chromium and Playwright driver, real Ollama, proxies, the desktop client. The original run used an uncommitted tree (`1435fe9`); the rerun used a clean commit. |
| 10 | Loopback endpoint enforcement; Chroma telemetry off | ACTUAL (unit tests) + code | `backend/security/locality.py`; `tests/` | `pytest` | The override `PILOT_ALLOW_REMOTE_MODEL=true` disables it. Proxy variables and model names are not checked. |
| 11 | Oracle validation: 0 false negatives on 35 solutions, 0 false positives on 34 near misses | ACTUAL | `e2e_oracle_validation.csv` | `python -m benchmarks.e2e.validate_oracle` | Scripted trajectories written by the oracle's author (AI agent). |
| 12 | Unit tests: 144/147 pass | ACTUAL | `artifacts/results/pytest_revision.txt` | `python -m pytest` (2026-10-04) | The 3 failures need live web or a running model. |
| 13 | Simulated false completions 19 vs 28 of 100; paired reduction 0.11 [0.05, 0.18] | SYNTHETIC | `out/heldout_v2/results.json`, `scenarios.csv` | `simulate_v2` | Direction fixed by construction in the model. Post-hoc v2. |
| 14 | Simulated decision accuracy 52/74 vs 46/74, p = 0.15; Monte Carlo: Φ better at p < 0.05 in 42% of sets | SYNTHETIC | same | same | Conditional on ASSUMED inputs. 2 of 3 false rejections come from an ASSUMED rate. |
| 15 | Simulated policy success 44 vs 46 (p = 0.63) | SYNTHETIC | same | same | — |
| 16 | Ablation: engine off TSR 0.41 vs 0.44 (p = 0.25); memory no effect | SYNTHETIC | same | same | Recovery probabilities come from Study E (ASSUMED per-attempt rates). |
| 17 | Memory study: 19 / 19 / 20 of 44 | SYNTHETIC (filter: PROPOSED) | same | same | Underpowered. The misleading-rate mapping is ASSUMED. |
| 18 | Recovery study: 51 / 68 / 87 of 93; false completions 9 / 9 / 2 | SYNTHETIC (guided: PROPOSED) | `recovery_scenarios.csv` | same | Strategy sequences ACTUAL; success rates ASSUMED. |
| 19 | Overhead: Φ +2.6% mean episode time; self-check +14% (cost only); inference 80% | SYNTHETIC (inputs ACTUAL + ASSUMED) | `results.json` latency | same | Inference time is ASSUMED (3 s). |
| 20 | Sensitivity: π sweep, detection ×0.5/1.5, missing evidence, action failure, continuation | SYNTHETIC | `results.json` sensitivity | same | 300 sets per point, separate random stream. |
| 21 | Detection and false-rejection rates used by the simulation | DERIVED (mapping and proxy ASSUMED) | `inputs/m1_gate_rules.csv` | `simulate_v2.derive_rates` | (k + 0.5)/(n + 1); small n. |
| 22 | P(recover) 0.66 / 0.49 used in the policy simulation | SYNTHETIC (output of Study E) | `results.json` | same | — |
| 23 | All other simulation inputs (Table XVI) | ASSUMED / PROPOSED | `params.json` | — | Swept where marked. |
| 24 | Related-work comparison (Table I) and cited findings | LITERATURE | `references.bib` | — | Four cells are unverified (`audit_integrity.md`, round-2 F27). |
| 25 | End-to-end task success, self-verification baseline, memory and recovery in real episodes | PROPOSED (protocol implemented, not executed) | `benchmarks/e2e/` | `run_e2e.py` (needs local model weights) | Explicitly not claimed. |
| 26 | Desktop backend, action gate, permission tiers, enhanced validation, guided recovery, relevance filter | PROPOSED | Appendix A; Table II | — | Not implemented. |

**Who produced the work.** The acknowledgment now states that an AI system (Claude) wrote the gate states and labels, the simulation and its assumed values, the code fixes, the recomputation checks, and the text. The author set the goals and directed the work. The author should confirm or amend this description of their own role.
