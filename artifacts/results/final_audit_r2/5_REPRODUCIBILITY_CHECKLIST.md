# Reproducibility checklist

The reproducibility auditor (Agent 6) verified this list in fresh clones; after the fixes it was updated to commit `66bc660`.

| Artifact / command | Exists | Regenerates identically | Notes |
|---|---|---|---|
| `python -m benchmarks.simulation.simulate_v2` → `out/heldout_v2/{results.json, scenarios.csv, recovery_scenarios.csv}` | ✔ | ✔ byte for byte | ~35 s; needs `requirements-paper.lock` (imports the recovery engine) |
| `python -m benchmarks.simulation.make_tables` → `paper/tables/sim/*.tex` (9 files), `ledger_simulation.csv` | ✔ | ✔ byte for byte | <1 s |
| `python artifacts/experiments/gate_stats.py` → `gate_stats.csv` (stdout → `gate_stats.txt`) | ✔ | ✔ byte for byte | Fails loudly if an input is missing |
| `python benchmarks/e2e/egress/summarize_egress.py artifacts/results/e2e_smoke_stub` → `egress_summary.json` | ✔ (new) | ✔ same content | Raw logs now committed, with SHA-256 in the README |
| `sh paper/build.sh` → `paper/main.pdf` | ✔ | ✔ text identical; bit-identical with `SOURCE_DATE_EPOCH` | TeX Live 2023, IEEEtran 1.8b; 0 errors, 0 overfull boxes, 0 float warnings |
| `make reproduce-paper` (whole chain + `git diff --exit-code`) | ✔ (new) | — | Single entry point |
| `python -m benchmarks.simulation.simulate --set heldout` (v1) | ✔ | ✔ | Writes `out/heldout/`, which is identical to `out/heldout_v1/`; see `out/README.md` |
| `python -m benchmarks.simulation.simulate --set dev` | ✔ | ✔ (refreshed) | Not reported |
| `python -m benchmarks.simulation.decision_analysis` | ✔ | ✔ | v1 decision-level analysis |
| `python benchmarks/simulation/independent_validator.py [out.md]` | ✔ | ✔ 0 discrepancies | Paths are now repo-relative |
| `artifacts/results/final_audit/scripts/*.py` (round-2 recomputation) | ✔ (new) | ✔ | Repo-relative; `mc_check.py` re-drives the model read-only |
| `python -m benchmarks.simulation.measure_inputs` (M1–M4) | ✔ | m1, m3, m4 identical; m2 timings differ, as timings do | Needs Playwright 1.56.0 / Chromium 141 (pinned) |
| `python artifacts/experiments/verification_gate_study.py [--ablation]` | ✔ | All 92 decisions identical; ablation byte-identical; timings differ | Needs Playwright 1.56.0 |
| Before-fix gate decisions | ✔ (outputs) | Not scripted | Study script run against the agent code of `08653e2`, checked out separately |
| `python -m benchmarks.e2e.validate_oracle` | ✔ | `.txt` identical; `.csv` differs only in a random port | Use the `-m` form |
| `python -m pytest` | ✔ | Not rerun in this audit | `pytest_revision.txt`: 144/147 |
| 70-episode egress run | Raw outputs ✔ | Not rerun; command reconstructed in the README | It ran on an uncommitted tree that cannot be recovered |
| `tables/gate_results.tex`, `tables/ablation.tex` | ✔ | Hand-copied from `gate_stats.csv` (values verified) | Recommended: generate them with a script |

## Versions

| Component | Version |
|---|---|
| Python | 3.11.15 |
| Playwright | 1.56.0 |
| Chromium | 141 |
| LangGraph | 1.2.12 |
| chromadb | 1.5.9 |
| ollama (Python client) | 0.6.3 |
| pydantic | 2.13.5 |
| FastAPI | 0.142.2 |
| httpx | 0.28.1 |

- All package versions are pinned in `requirements-paper.lock` (pip freeze of the experiment environment, `.venv-eval`). The versions are stated in §VII.
- `requirements.txt` uses `>=` and today resolves to newer versions (for example Playwright 1.63, which expects a different Chromium build).
- **Machines:**
  - gate study and tests: 4-core Xeon at 2.1 GHz, 2026-10-04;
  - simulation inputs (M2–M4): 4-core Xeon at 2.8 GHz, 2026-10-23.
  - Both are stated in the paper. They are not recorded inside the output files.

## Identifiers

- **Commits.** Every commit the paper cites exists on branch `ccr-4b8200f0-5i3k5m`: `bf0a8a5`, `2361d50`, `08653e2`, `3a0aa8e`, `41a6097`, `1435fe9`, `55ac1ea`, `b9d5088`.
- **Agent code.** `git diff bf0a8a5 HEAD -- backend` is empty.
- **Held-out 2.** Its SHA-256 matches the freeze record.
- **Seeds.** 101 / 202; 1,000 Monte Carlo sets (`params.json`).
- **Names.** Every config name, environment switch and model tag the paper uses exists in the code.

## Missing or open items

1. **No release tag.** There are no tags; the cited hashes live only on an auto-generated session branch, and `origin/main` has diverged (47 ahead, 2 behind; main adds Gemini and Windows desktop automation).
   - **Action (author):** create an annotated tag, for example `paper-ieee-v1.0`, on the final commit of this branch. Then make a GitHub release, optionally archive it on Zenodo for a DOI, and cite the tag or DOI in §V instead of the branch.
   - Pushing a tag is a public, outward-facing action, so it is left to the author.
2. **No continuous integration** for the paper chain. Recommended: run `make reproduce-paper` in CI on the paper branch.
3. **Hand-copied gate tables** (`gate_results.tex`, `ablation.tex`). Their values are verified, but no generator exists.
4. **Before-fix gate decisions are not scripted.** They were produced with a separate checkout of `08653e2`.
5. **The egress run cannot be re-executed exactly.** It ran on a dirty tree; the raw data is released.
6. **Absolute paths in raw logs** (for example `/home/user/...` inside `episodes.jsonl`) are harmless provenance.
