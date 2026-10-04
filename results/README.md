# Results index

The scripts, seeds, raw outputs and analysis code for the experiments run in this revision. The files stay where the existing scripts write them; this index points to them.

| Experiment | Script | Raw output | Seed / settings |
|---|---|---|---|
| Gate study (design, held-out 1, held-out 2) | `artifacts/experiments/verification_gate_study.py` | `artifacts/results/verification_gate_cases.csv`, `_summary.csv`, `_run.log` | Deterministic (no model); 20 timing repetitions |
| Gate ablation | `verification_gate_study.py --ablation` | `artifacts/results/verification_gate_ablation.csv`, `.log` | Deterministic |
| Gate statistics | `artifacts/experiments/gate_stats.py` | `artifacts/results/gate_stats.csv`, `.txt` | Exact methods (no random sampling) |
| Held-out 2 freeze | `artifacts/experiments/gate_heldout2.py` | `artifacts/results/gate_heldout2_freeze.txt` (SHA-256), commit `b9d5088` | — |
| Oracle validation | `benchmarks/e2e/validate_oracle.py` | `artifacts/results/e2e_oracle_validation.csv`, `.txt` | Deterministic scripted trajectories |
| Egress (locality) | `benchmarks/e2e/run_e2e.py` with `benchmarks/e2e/egress/` on `PYTHONPATH` and `fake_ollama.py` | `artifacts/results/e2e_smoke_stub/egress_summary.json` | Stand-in model; **episode outcomes are not results** |
| Test suite | `pytest` with `PILOT_HEADLESS_BROWSER=true --timeout 240` | `artifacts/results/pytest_revision.txt`, `junit_revision.xml` | — |
| End-to-end runs (not run here) | `benchmarks/e2e/run_e2e.py`, `analyze_e2e.py` | written to `artifacts/results/e2e/<run>/` | temperature 0, seed 7 (defaults); see `AUTHOR_ACTIONS.md` A1 |

The bootstrap in `benchmarks/e2e/stats.py` uses `seed=7` and 10,000 resamples.
