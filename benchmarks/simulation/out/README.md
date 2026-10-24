# Simulation outputs

| Directory | Produced by | Used in the paper |
|---|---|---|
| `heldout_v2/` | `python -m benchmarks.simulation.simulate_v2` (needs `requirements-paper.lock`), then `python -m benchmarks.simulation.make_tables` | All reported simulation tables and Fig. 3. This is the corrected model v2, which is post hoc. |
| `heldout_v1/` | Archived copy of `heldout/` made before v2 | v1 values, listed in `artifacts/results/final_audit/changed_numbers_ledger.csv` |
| `heldout/` | `python -m benchmarks.simulation.simulate --set heldout` (v1); `decision_analysis.py` also writes here | Byte-identical to `heldout_v1/`. It is kept because the v1 scripts write here. |
| `dev/` | `python -m benchmarks.simulation.simulate --set dev` (v1, seed 101) | Not reported; used only for debugging |

Files with no generator in the current scripts:
- `heldout*/mc_paired_fc_diff.json` was written by an interactive v1 analysis. Its value (mean 0.11 [0.05, 0.17]) is superseded by `monte_carlo_paired` in `heldout_v2/results.json`.
- The v1 ledgers are kept for the record.
