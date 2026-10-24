# Harness smoke run with a scripted stand-in model (NOT results)

These 70 episodes (10 dev tasks x 7 configurations, 2026-10-04) were run with `benchmarks/e2e/fake_ollama.py`, which returns fixed answers and always claims completion. They show that the harness, the oracles and the analysis run end to end. **They say nothing about the agent's task success and must not be reported as results.**

The one measurement used from this run is `egress_summary.json`. A socket logger (`benchmarks/e2e/egress/sitecustomize.py`) recorded every socket.connect/connect_ex call in the harness's Python processes. All 555 attempts went to 127.0.0.1, and no page request left 127.0.0.1 (`non_local_page_hosts` is empty in every episode).

Caveat: Chroma's default embedding model was already cached in `~/.cache/chroma`. On a machine without the cache, Chroma downloads it once on first use.

## Released raw files and provenance

| File | Lines | SHA-256 | Origin |
|---|---|---|---|
| `egress_raw.jsonl` | 555 | `c8d779713d9a1af3419a204e80b4cede4fd7a42ed0b1decff4a0273c2f0f3ae1` | Written by `sitecustomize.py` through `PILOT_EGRESS_LOG` during the run (file time 2026-10-04 07:24 UTC). It was kept in the session's scratch directory and copied here unchanged on 2026-10-24. |
| `episodes.jsonl` | 70 | `4cb9d0f031f689fd59c3cc96127690356cd9a8e22459c4e55f1a0a232267acaf` | Written by `run_e2e.py` during the run (2026-10-04 07:28 UTC). |

`egress_summary.json` is rebuilt from these files by `python benchmarks/e2e/egress/summarize_egress.py artifacts/results/e2e_smoke_stub`.

**What was instrumented.** `socket.connect` and `connect_ex` on IPv4 and IPv6 sockets in the harness's eight Python processes.

**What was not instrumented:**
- UDP and DNS;
- the Playwright driver and Chromium;
- the model server.

**Code version.** The run used an uncommitted tree based on `1435fe9` (`run_meta.json`), and those uncommitted changes were not saved.

**Reconstructed command.** The exact argv was not recorded. The run was approximately:

```
PILOT_EGRESS_LOG=<file> PYTHONPATH=benchmarks/e2e/egress python -m benchmarks.e2e.run_e2e --split dev --trials 1 --configs full,no_verification,self_verification,no_recovery,no_memory,gate_without_T,recovery_replan_only
```

It ran against `python benchmarks/e2e/fake_ollama.py` on 127.0.0.1:11435, with `PILOT_OLLAMA_BASE_URL=http://127.0.0.1:11435` (configurations from `run_meta.json`).
