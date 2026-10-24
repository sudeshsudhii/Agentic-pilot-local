"""Reproduce the locality (egress) test: 10 development tasks x 7 configurations against the scripted
stand-in model server, with every socket connect of the harness's Python processes logged.

The stand-in is NOT a model; episode outcomes are not results. Run from a clean, committed tree:
    python benchmarks/e2e/egress/run_egress.py artifacts/results/e2e_egress_rerun
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from benchmarks.e2e.fake_ollama import FakeOllama  # noqa: E402

CONFIGS = "full,no_verification,self_verification,no_recovery,no_memory,gate_without_T,recovery_replan_only"


def main(out: str) -> None:
    out_dir = (ROOT / out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    raw = out_dir / "egress_raw.jsonl"
    raw.unlink(missing_ok=True)
    with FakeOllama() as fake:
        env = {**os.environ,
               "PYTHONPATH": os.pathsep.join([str(ROOT / "benchmarks" / "e2e" / "egress"), str(ROOT)]),
               "PILOT_EGRESS_LOG": str(raw), "PILOT_OLLAMA_BASE_URL": fake.url,
               "PILOT_OLLAMA_MODEL": "scripted-stub:latest", "PILOT_HEADLESS_BROWSER": "true"}
        subprocess.run([sys.executable, "-m", "benchmarks.e2e.run_e2e", "--split", "dev", "--trials", "1",
                        "--configs", CONFIGS, "--out", str(out_dir), "--episode-timeout", "180"],
                       cwd=ROOT, env=env, check=True)
        (out_dir / "stand_in_url.txt").write_text(fake.url + "\n")
    subprocess.run([sys.executable, str(ROOT / "benchmarks" / "e2e" / "egress" / "summarize_egress.py"), str(out_dir)],
                   cwd=ROOT, check=True)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "artifacts/results/e2e_egress_rerun")
