"""Resolve the model router's choice per role for a given set of installed models.

No LLM is called: the registry is told which models are installed
(ModelRegistry.mark_installed) and ModelRouter.route() is evaluated for the
call types issued by the agent graph (backend/agent/nodes.py).

Usage: python artifacts/experiments/routing_default_install.py
Output: artifacts/results/routing_resolution.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from backend.llm.registry import ModelRegistry  # noqa: E402
from backend.llm.router import ModelRouter  # noqa: E402

# Call sites in nodes.py and the arguments they pass to route().
CALLS = {
    "intent_parsing (parse_intent)": dict(task_type="intent_parsing", input_text="Search Google for 'Alan Turing'", complexity="low"),
    "decomposition (parse_intent)": dict(task_type="planning", input_text="Go to wikipedia.org, search for 'Alan Turing' and extract his birth year", complexity="high"),
    "action planning, 1-step (plan_action)": dict(task_type="navigate", input_text="Open google.com", action_type="navigate", complexity="medium"),
    "action planning, multi-step (plan_action)": dict(task_type="search", input_text="Go to wikipedia.org, search for 'Alan Turing' and extract his birth year", action_type="search", complexity="high"),
    "image input": dict(task_type="vision", input_text="find the button", has_image=True),
}

SCENARIOS = {
    "launcher_default": ["qwen2.5:1.5b", "moondream:latest"],
    "full_role_set": ["qwen2.5:1.5b", "qwen2.5:7b", "qwen3.5:2b", "deepseek-r1:1.5b", "qwen3-vl:2b", "moondream:latest", "qwen2.5-coder:3b"],
}


def main() -> None:
    rows = []
    for scen, installed in SCENARIOS.items():
        for mode in ("isolated", "sequence"):
            # isolated: fresh router per call, so no model is "active" (pure role preference)
            # sequence: one router, calls issued in graph order, as the agent does; the router
            #           remembers its last selection and applies stickiness.
            reg = ModelRegistry()
            reg.mark_installed(installed)
            shared = ModelRouter(registry=reg)
            active = None
            for label, kwargs in CALLS.items():
                if mode == "isolated":
                    d = ModelRouter(registry=reg).route(**kwargs)
                else:
                    d = shared.route(active_model=active, **kwargs)
                    active = d.selected_model
                rows.append({"scenario": scen, "mode": mode, "installed": " ".join(installed), "call": label,
                             "role": d.role, "selected_model": d.selected_model, "fallback_used": d.fallback_used,
                             "reason": d.reason[:120]})
                print(f"{scen:17s} {mode:8s} {label:42s} role={d.role:11s} model={d.selected_model:18s} fallback={d.fallback_used}")
    # Probes added after review: substring keyword matching and recovery stickiness.
    reg = ModelRegistry()
    reg.mark_installed(SCENARIOS["launcher_default"])
    for text in ["Find a guitar guide on youtube.com", "Search Google Images for cats",
                 "Open the screening schedule on imdb.com", "Search Google for Alan Turing"]:
        d = ModelRouter(registry=reg).route(task_type="intent_parsing", input_text=text, complexity="low")
        rows.append({"scenario": "launcher_default", "mode": "keyword_probe", "installed": " ".join(SCENARIOS["launcher_default"]),
                     "call": f"intent_parsing: {text}", "role": d.role, "selected_model": d.selected_model,
                     "fallback_used": d.fallback_used, "reason": d.reason[:120]})
        print(f"keyword probe {text!r:45s} role={d.role:11s} model={d.selected_model}")
    # Cross-task probe: a new task starts with no active model. Since the fix it must not inherit the
    # previous task's model. (The agent no longer routes recovery: RecoveryEngine makes no model call.)
    reg = ModelRegistry()
    reg.mark_installed(SCENARIOS["full_role_set"])
    r = ModelRouter(registry=reg)
    a = r.route(task_type="intent_parsing", input_text="Open google.com", complexity="low")
    b = r.route(task_type="planning", input_text="Go to wikipedia.org, then open the Alan Turing article",
                complexity="high", active_model=None)
    for label, d in (("task 1: intent parsing", a), ("task 2: first planning call", b)):
        rows.append({"scenario": "full_role_set", "mode": "cross_task", "installed": " ".join(SCENARIOS["full_role_set"]),
                     "call": label, "role": d.role, "selected_model": d.selected_model,
                     "fallback_used": d.fallback_used, "reason": d.reason[:120]})
        print(f"cross-task probe {label:30s} model={d.selected_model} ({d.reason[:60]})")
    out = REPO / "artifacts" / "results" / "routing_resolution.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
