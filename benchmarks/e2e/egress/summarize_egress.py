"""Rebuild artifacts/results/e2e_smoke_stub/egress_summary.json from the raw socket log of the stand-in run.

The raw log (egress_raw.jsonl) has one record per socket.connect/connect_ex call made in the harness's Python
processes, written by benchmarks/e2e/egress/sitecustomize.py through PILOT_EGRESS_LOG. Usage:
    python benchmarks/e2e/egress/summarize_egress.py artifacts/results/e2e_smoke_stub
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path


def main(run_dir: str) -> None:
    d = Path(run_dir)
    raw = [json.loads(line) for line in (d / "egress_raw.jsonl").read_text().splitlines() if line.strip()]
    episodes = sum(1 for line in (d / "episodes.jsonl").read_text().splitlines() if line.strip())
    out = {
        "connections_by_host": dict(Counter(r["host"] for r in raw)),
        "episodes": episodes,
        "connections_by_host_port": dict(Counter(f"{r['host']}:{r['port']}" for r in raw)),
        "python_processes": len({r["pid"] for r in raw}),
        "note": "Stand-in model server listened on "
                + ((d / "stand_in_url.txt").read_text().strip() if (d / "stand_in_url.txt").exists() else "http://127.0.0.1:11435")
                + "; raw per-connection log in egress_raw.jsonl",
    }
    (d / "egress_summary.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results/e2e_smoke_stub")
