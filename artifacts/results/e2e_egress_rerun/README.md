# Locality (egress) test rerun on committed code (2026-10-24)

Command: `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python benchmarks/e2e/egress/run_egress.py <out>` with the environment of `requirements-paper.lock`, on clean commit `7133301` (`run_meta.json`: git_dirty false; `backend/` identical to `bf0a8a5`).

Result: 70 episodes (10 development tasks x 7 configurations), 555 socket connect calls in 8 Python processes, all to the stand-in on 127.0.0.1 (port in `stand_in_url.txt`); no page request left 127.0.0.1; memory returned records in 54 of 60 memory-enabled episodes. The stand-in is not a model: episode outcomes are not results.

SHA-256: egress_raw.jsonl 6a808b5144ecce18ac477b8b598993228020c7e2a038277b1adef1d078964ae3; episodes.jsonl 6c1c2eec5796372bedbde25bcf83b450f6d2ad2e30a505ca0c46ffebd458b53c
