"""Run the full agent loop (planner -> browser -> verifier -> recovery) on the local sites.

Usage (from the repository root, with Ollama running and the models pulled):

    python -m benchmarks.e2e.run_e2e --split test --trials 3 \
        --configs full,no_verification,self_verification --out artifacts/results/e2e/run1

Each configuration runs in its own process with its own database, memory store and logs, so
memory written in one configuration cannot help another. Results are appended to
<out>/episodes.jsonl, one line per episode; analyze them with benchmarks/e2e/analyze_e2e.py.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]

# Environment overrides per configuration. Every configuration uses the same tasks, model(s),
# sampling settings and step budget (15 planner-side model calls).
CONFIGS: dict[str, dict[str, str]] = {
    "full": {},
    "no_verification": {"PILOT_VERIFICATION_MODE": "none"},
    "self_verification": {"PILOT_VERIFICATION_MODE": "self"},
    "no_recovery": {"PILOT_ENABLE_RECOVERY": "false"},
    "no_memory": {"PILOT_ENABLE_MEMORY": "false", "PILOT_ENABLE_RAG": "false"},
    "single_model": {"PILOT_ENABLE_MULTI_MODEL": "false"},
    "vision_only_grounding": {"PILOT_GROUNDING_MODE": "vision_only"},
    "recovery_retry_only": {"PILOT_RECOVERY_FIXED_STRATEGY": "retry"},
    "recovery_vision_only": {"PILOT_RECOVERY_FIXED_STRATEGY": "vision_fallback"},
    "recovery_replan_only": {"PILOT_RECOVERY_FIXED_STRATEGY": "replan"},
    **{f"gate_without_{c}": {"PILOT_VERIFICATION_DISABLED_CHECKS": json.dumps([c])} for c in "EHQTXRB"},
}


def load_tasks(split: str, ids: list[str] | None) -> list[dict]:
    data = json.loads((Path(__file__).parent / "tasks.json").read_text())
    tasks = [t for t in data["tasks"] if split == "all" or t["split"] == split]
    if ids:
        tasks = [t for t in tasks if t["id"] in ids]
    return tasks


def environment_record() -> dict:
    """Hardware, software and model versions for the paper's setup paragraph."""

    import urllib.request

    rec: dict = {
        "date_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_count": os.cpu_count(),
    }
    try:
        rec["git_commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        rec["git_dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except Exception:
        pass
    base = os.environ.get("PILOT_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    for key, path in (("ollama_version", "/api/version"), ("ollama_models", "/api/tags")):
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                rec[key] = json.loads(r.read())
        except Exception as exc:
            rec[key] = f"unavailable: {exc}"
    for k in ("PILOT_LLM_TEMPERATURE", "PILOT_LLM_SEED", "PILOT_OLLAMA_MODEL", "PILOT_OLLAMA_VISION_MODEL"):
        rec[k] = os.environ.get(k)
    return rec


# --------------------------------------------------------------------------- worker

async def run_worker(config_name: str, tasks: list[dict], trials: int, out: Path, episode_timeout_s: int) -> None:
    from backend.agent import nodes
    from backend.agent.graph import build_graph
    from backend.browser.pool import browser_pool
    from backend.db.database import database
    from backend.llm import gateway as gw
    from benchmarks.e2e import oracle
    from benchmarks.e2e.sites import SiteServer, reset_state, snapshot_state

    await database.connect()
    graph = build_graph()
    if graph is None:
        raise RuntimeError("LangGraph is not installed")

    # Record every URL the browser requests, to show page traffic stayed on this machine.
    page_requests: list[str] = []
    original_acquire = browser_pool.acquire

    async def acquire_with_log():
        ctx = await original_acquire()
        if not getattr(ctx, "_e2e_logged", False):
            ctx.on("request", lambda r: page_requests.append(r.url))
            ctx._e2e_logged = True
        return ctx

    browser_pool.acquire = acquire_with_log

    with SiteServer() as site, open(out / "episodes.jsonl", "a") as sink:
        # Trial-major order: all tasks once, then again; memory written in trial 1 is available in trial 2.
        for trial in range(1, trials + 1):
            for task in tasks:
                reset_state()
                gw.reset_usage()
                page_requests.clear()
                goal = task["goal"].format(base=site.base)
                task_id = str(uuid.uuid4())
                await database.create_task(task_id, goal)
                state = {
                    "task_id": task_id, "input_text": goal, "parsed_intent": None, "current_url": None,
                    "action_manifest": None, "action_history": [], "retry_count": 0, "status": "running",
                    "approval_id": None, "error": None, "result": None, "plugin_id": None, "llm_call_count": 0,
                    "planned_action": None, "approved": True, "navigation_succeeded": False, "session_id": None,
                    "task_plan": None, "current_step_index": 1, "retrieved_knowledge": None,
                    "retrieved_memories": None, "retrieval_metadata": {}, "selected_model": None,
                    "model_role": None, "routing_reason": None, "model_switch": False,
                }
                started = time.perf_counter()
                final_state: dict = {}
                error = None
                try:
                    final_state = await asyncio.wait_for(
                        graph.ainvoke(state, config={"recursion_limit": 200}), timeout=episode_timeout_s
                    )
                except asyncio.TimeoutError:
                    error = "episode_timeout"
                except Exception as exc:  # the episode fails; the run continues
                    error = f"{type(exc).__name__}: {exc}"
                duration_ms = int((time.perf_counter() - started) * 1000)

                final_url = None
                ctx = browser_pool._task_contexts.get(task_id) or getattr(browser_pool._retained_contexts.get(task_id), "context", None)
                if ctx is not None and ctx.pages:
                    final_url = ctx.pages[0].url
                final_url = final_url or (final_state.get("result") or {}).get("url") or final_state.get("current_url")
                await browser_pool.close_task_browser(task_id, reason="new_task")
                await browser_pool.release_task_context(task_id)

                events = [e.model_dump() if hasattr(e, "model_dump") else dict(e) for e in await database.list_events(task_id)]
                verifications = [e.get("payload") or {} for e in events if e.get("type") == "VERIFICATION_RESULT"]
                recoveries = [e.get("payload") or {} for e in events if e.get("type") == "RECOVERY_ATTEMPT"]
                actions = final_state.get("action_history") or []
                site_state = snapshot_state()
                answer = oracle.answer_text_of(final_state)
                achieved, reason = oracle.evaluate(task["oracle"], final_url, answer, site_state)
                status = final_state.get("status") or "failed"
                foreign = sorted({urlsplit(u).hostname or "" for u in page_requests} - {"127.0.0.1"} - {""})

                record = {
                    "config": config_name, "task_id": task["id"], "trial": trial, "split": task["split"],
                    "site": task["site"], "category": task["category"], "tier": task["tier"],
                    "satisfiable": task["oracle"]["type"] != "unsatisfiable",
                    "status": status, "reported_complete": status == "completed",
                    "oracle_achieved": achieved, "oracle_reason": reason,
                    "final_url": final_url, "answer": answer[:500], "error": error or final_state.get("error"),
                    "duration_ms": duration_ms, "planner_calls": final_state.get("llm_call_count", 0),
                    "browser_actions": len(actions),
                    "model_usage": gw.reset_usage(),
                    "verifications": [{k: v.get(k) for k in ("passed", "mode", "latency_ms", "model_calls", "message")} for v in verifications],
                    "recoveries": [{k: v.get(k) for k in ("strategy", "failure_type", "outcome", "recovery_strategy")} for v in recoveries],
                    "memories_retrieved": len(final_state.get("retrieved_memories") or []),
                    "knowledge_retrieved": len(final_state.get("retrieved_knowledge") or []),
                    "vision_called": bool(final_state.get("vision_called")),
                    "non_local_page_hosts": foreign,
                }
                sink.write(json.dumps(record, default=str) + "\n")
                sink.flush()
                print(f"[{config_name}] trial {trial} {task['id']}: status={status} oracle={achieved} "
                      f"{duration_ms / 1000:.1f}s calls={record['planner_calls']}", flush=True)
    await browser_pool.shutdown()
    await database.close()  # aiosqlite's worker thread would otherwise keep the process alive


# --------------------------------------------------------------------------- orchestrator

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--configs", default="full,no_verification,self_verification",
                    help="comma-separated; available: " + ", ".join(CONFIGS))
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--tasks", default="", help="comma-separated task ids (default: whole split)")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--out", default="artifacts/results/e2e/run")
    ap.add_argument("--episode-timeout", type=int, default=600, help="seconds per episode")
    ap.add_argument("--worker", default="", help=argparse.SUPPRESS)
    args = ap.parse_args()

    out = Path(args.out).resolve()
    tasks = load_tasks(args.split, [t for t in args.tasks.split(",") if t])

    if args.worker:
        asyncio.run(run_worker(args.worker, tasks, args.trials, out, args.episode_timeout))
        return

    out.mkdir(parents=True, exist_ok=True)
    names = [c.strip() for c in args.configs.split(",") if c.strip()]
    unknown = [n for n in names if n not in CONFIGS]
    if unknown:
        sys.exit(f"unknown configuration(s): {unknown}")
    env_base = {**os.environ, "PILOT_HEADLESS_BROWSER": os.environ.get("PILOT_HEADLESS_BROWSER", "true"),
                "PILOT_LLM_TEMPERATURE": os.environ.get("PILOT_LLM_TEMPERATURE", "0"),
                "PILOT_LLM_SEED": os.environ.get("PILOT_LLM_SEED", "7"),
                "PILOT_KEEP_BROWSER_OPEN": "false"}
    meta = {"environment": environment_record(), "split": args.split, "trials": args.trials,
            "tasks": [t["id"] for t in tasks], "configs": {n: CONFIGS[n] for n in names}}
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1, default=str))
    print(f"{len(tasks)} tasks x {args.trials} trials x {len(names)} configurations -> {out}")

    for name in names:
        cdir = out / name
        cdir.mkdir(exist_ok=True)
        env = {**env_base, **CONFIGS[name],
               "PILOT_DB_PATH": str(cdir / "data.db"), "PILOT_DATA_DIR": str(cdir / "data"),
               "PILOT_LOG_DIR": str(cdir / "logs"), "PILOT_EXPERIMENT_OUTPUT_DIR": str(cdir),
               "PILOT_RAG_KNOWLEDGE_DIR": str(cdir / "knowledge")}
        cmd = [sys.executable, "-m", "benchmarks.e2e.run_e2e", "--worker", name, "--split", args.split,
               "--trials", str(args.trials), "--out", str(out), "--episode-timeout", str(args.episode_timeout)]
        if args.tasks:
            cmd += ["--tasks", args.tasks]
        print(f"=== configuration {name} ===", flush=True)
        rc = subprocess.call(cmd, cwd=ROOT, env=env)
        if rc != 0:
            print(f"configuration {name} exited with code {rc}", flush=True)
    print(f"Done. Analyze with: python -m benchmarks.e2e.analyze_e2e {out}")


if __name__ == "__main__":
    main()
