# Harness smoke run with a scripted stand-in model (NOT results)

These 70 episodes (10 dev tasks x 7 configurations, 2026-10-04) were run with `benchmarks/e2e/fake_ollama.py`, which returns fixed answers and always claims completion. They show that the harness, the oracles and the analysis run end to end. **They say nothing about the agent's task success and must not be reported as results.**

The one measurement used from this run is `egress_summary.json`. A socket logger (`benchmarks/e2e/egress/sitecustomize.py`) recorded every outbound connection the agent process attempted. All 555 attempts went to 127.0.0.1, and no page request left 127.0.0.1 (`non_local_page_hosts` is empty in every episode).

Caveat: Chroma's default embedding model was already cached in `~/.cache/chroma`. On a machine without the cache, Chroma downloads it once on first use.
