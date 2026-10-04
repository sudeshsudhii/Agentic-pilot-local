"""Analyze end-to-end runs: success, FCR, FRR with 95% intervals, paired tests, cost and overhead.

Usage:  python -m benchmarks.e2e.analyze_e2e <run_dir> [--split test]

Writes <run_dir>/analysis/*.csv and LaTeX tables <run_dir>/analysis/tables/*.tex.

Definitions (paper Section III):
  success      the oracle Phi* holds on the final state (for answer tasks: the answer states the fact)
  FCR          episodes reported complete with Phi* = 0, over episodes reported complete
  FRR          episodes with Phi* = 1 not reported complete, over episodes with Phi* = 1
Paired comparisons are by (task, trial) against the reference configuration (default: full).
McNemar's exact test compares binary outcomes; the bootstrap resamples whole tasks.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from benchmarks.e2e.stats import bootstrap_diff_ci, mcnemar_exact, paired_discordance, wilson


def load(run_dir: Path, split: str) -> list[dict]:
    rows = [json.loads(l) for l in (run_dir / "episodes.jsonl").read_text().splitlines() if l.strip()]
    return [r for r in rows if split == "all" or r["split"] == split]


def ci(k: int, n: int) -> str:
    if n == 0:
        return "--"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({lo:.2f}--{hi:.2f})"


def med(xs: list[float]) -> float:
    return statistics.median(xs) if xs else float("nan")


def summarize(eps: list[dict]) -> dict:
    rep = [e for e in eps if e["reported_complete"]]
    sat = [e for e in eps if e["oracle_achieved"]]
    vlat = [v["latency_ms"] for e in eps for v in e["verifications"] if v.get("latency_ms") is not None]
    return {
        "episodes": len(eps),
        "success_k": len(sat), "success": ci(len(sat), len(eps)),
        "reported": len(rep),
        "fc_k": sum(1 for e in rep if not e["oracle_achieved"]), "fcr": ci(sum(1 for e in rep if not e["oracle_achieved"]), len(rep)),
        "fr_k": sum(1 for e in sat if not e["reported_complete"]), "frr": ci(sum(1 for e in sat if not e["reported_complete"]), len(sat)),
        "median_actions": med([e["browser_actions"] for e in eps]),
        "median_planner_calls": med([e["planner_calls"] for e in eps]),
        "mean_model_calls": statistics.mean([e["model_usage"]["calls"] for e in eps]) if eps else float("nan"),
        "mean_tokens": statistics.mean([e["model_usage"]["prompt_tokens"] + e["model_usage"]["completion_tokens"] for e in eps]) if eps else float("nan"),
        "median_duration_s": med([e["duration_ms"] / 1000 for e in eps]),
        "median_check_ms": med(vlat),
        "checks_per_episode": statistics.mean([len(e["verifications"]) for e in eps]) if eps else float("nan"),
        "check_model_calls": sum(v.get("model_calls") or 0 for e in eps for v in e["verifications"]),
        "rejections_per_episode": statistics.mean([sum(1 for v in e["verifications"] if not v.get("passed")) for e in eps]) if eps else float("nan"),
        "episodes_with_recovery": sum(1 for e in eps if e["recoveries"]),
        "vision_rate": ci(sum(1 for e in eps if e["vision_called"]), len(eps)),
        "non_local_page_hosts": sorted({h for e in eps for h in e["non_local_page_hosts"]}),
    }


def paired(ref: list[dict], other: list[dict], key) -> dict:
    a_map = {(e["task_id"], e["trial"]): e for e in ref}
    pairs = [(a_map[(e["task_id"], e["trial"])], e) for e in other if (e["task_id"], e["trial"]) in a_map]
    if not pairs:
        return {}
    a = [bool(key(x)) for x, _ in pairs]
    b = [bool(key(y)) for _, y in pairs]
    disc = paired_discordance(a, b)
    point, lo, hi = bootstrap_diff_ci([int(x) for x in a], [int(y) for y in b], clusters=[x["task_id"] for x, _ in pairs])
    return {"pairs": len(pairs), "ref_only": disc[0], "other_only": disc[1], "mcnemar_p": mcnemar_exact(*disc),
            "diff": point, "diff_lo": lo, "diff_hi": hi}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def tex_table(path: Path, caption: str, label: str, header: list[str], rows: list[list[str]], spec: str) -> None:
    lines = [r"\begin{table}[t]", r"\centering", rf"\caption{{{caption}}}", rf"\label{{{label}}}", r"\footnotesize",
             r"\setlength{\tabcolsep}{2.5pt}", rf"\begin{{tabular}}{{@{{}}{spec}@{{}}}}", r"\toprule",
             " & ".join(header) + r" \\", r"\midrule"]
    lines += [" & ".join(r) + r" \\" for r in rows]
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--reference", default="full")
    args = ap.parse_args()
    run = Path(args.run_dir)
    out = run / "analysis"
    (out / "tables").mkdir(parents=True, exist_ok=True)
    eps = load(run, args.split)
    by_cfg: dict[str, list[dict]] = defaultdict(list)
    for e in eps:
        by_cfg[e["config"]].append(e)
    if not by_cfg:
        raise SystemExit(f"no episodes for split {args.split}")
    ref = by_cfg.get(args.reference, [])

    # 1. One row per configuration, with paired tests against the reference.
    rows = []
    for cfg, xs in by_cfg.items():
        s = {"config": cfg, **summarize(xs)}
        if cfg != args.reference and ref:
            ps = paired(ref, xs, lambda e: e["oracle_achieved"])
            pf = paired(ref, xs, lambda e: e["reported_complete"] and not e["oracle_achieved"])
            s.update({f"success_{k}": v for k, v in ps.items()})
            s.update({f"falsecomp_{k}": v for k, v in pf.items()})
        rows.append(s)
    write_csv(out / "configurations.csv", rows)

    def fmt_p(r, pre):
        if f"{pre}_mcnemar_p" not in r:
            return "ref."
        return f"{r[f'{pre}_diff']:+.2f} [{r[f'{pre}_diff_lo']:+.2f}, {r[f'{pre}_diff_hi']:+.2f}], p={r[f'{pre}_mcnemar_p']:.3f}"

    tex_table(out / "tables" / "e2e_configs.tex",
              f"End-to-end results on the {args.split} tasks of the local sites (counts with Wilson 95\\% intervals). "
              f"$\\Delta$: success difference to \\texttt{{{args.reference}}} with task-level bootstrap 95\\% interval and exact McNemar $p$.",
              "tab:e2e", ["Configuration", "Success", "FCR", "FRR", r"$\Delta$ success", "Calls", "Time (s)"],
              [[r["config"].replace("_", r"\_"), r["success"], r["fcr"], r["frr"], fmt_p(r, "success"),
                f"{r['mean_model_calls']:.1f}", f"{r['median_duration_s']:.0f}"] for r in rows], "lcccccc")

    # 2. Per-category breakdown for the reference and the baselines.
    cat_rows = []
    for cfg in [c for c in (args.reference, "no_verification", "self_verification") if c in by_cfg]:
        cats: dict[str, list[dict]] = defaultdict(list)
        for e in by_cfg[cfg]:
            cats[e["category"]].append(e)
        for cat, xs in sorted(cats.items()):
            s = summarize(xs)
            cat_rows.append({"config": cfg, "category": cat, "episodes": s["episodes"], "success": s["success"], "fcr": s["fcr"], "frr": s["frr"]})
    write_csv(out / "categories.csv", cat_rows)

    # 3. Recovery: per strategy in the reference run, and per pinned-strategy configuration.
    rec_rows = []
    strat: dict[str, list[dict]] = defaultdict(list)
    for e in ref:
        for s in {r.get("strategy") for r in e["recoveries"] if r.get("strategy")}:
            strat[s].append(e)
    for s, xs in sorted(strat.items()):
        rec_rows.append({"source": args.reference, "strategy": s, "episodes_using": len(xs),
                         "recovered_success": ci(sum(1 for e in xs if e["oracle_achieved"]), len(xs)),
                         "median_actions": med([e["browser_actions"] for e in xs]),
                         "mean_model_calls": statistics.mean([e["model_usage"]["calls"] for e in xs])})
    for cfg in [c for c in by_cfg if c.startswith("recovery_") or c == "no_recovery"]:
        s = summarize(by_cfg[cfg])
        rec_rows.append({"source": cfg, "strategy": cfg.replace("recovery_", "").replace("_only", ""),
                         "episodes_using": s["episodes_with_recovery"], "recovered_success": s["success"],
                         "median_actions": s["median_actions"], "mean_model_calls": s["mean_model_calls"]})
    write_csv(out / "recovery.csv", rec_rows)

    # 4. Memory: with vs without, plus episodes where retrieval coincided with a loss.
    mem_rows = []
    if "no_memory" in by_cfg and ref:
        nomem = {(e["task_id"], e["trial"]): e for e in by_cfg["no_memory"]}
        for e in ref:
            o = nomem.get((e["task_id"], e["trial"]))
            if o and e["memories_retrieved"] and o["oracle_achieved"] and not e["oracle_achieved"]:
                mem_rows.append({"task_id": e["task_id"], "trial": e["trial"], "memories_retrieved": e["memories_retrieved"],
                                 "with_memory_status": e["status"], "without_memory_status": o["status"], "note": "inspect: possible misleading retrieval"})
    write_csv(out / "memory_losses.csv", mem_rows)

    # 5. Verification overhead: reference vs no_verification, per episode.
    ovh = {}
    if "no_verification" in by_cfg and ref:
        a, b = summarize(ref), summarize(by_cfg["no_verification"])
        ovh = {"added_median_time_s": a["median_duration_s"] - b["median_duration_s"],
               "added_median_actions": a["median_actions"] - b["median_actions"],
               "added_mean_model_calls": a["mean_model_calls"] - b["mean_model_calls"],
               "added_mean_tokens": a["mean_tokens"] - b["mean_tokens"],
               "median_check_ms": a["median_check_ms"], "checks_per_episode": a["checks_per_episode"],
               "false_completions_avoided": b["fc_k"] - a["fc_k"], "success_change": a["success_k"] - b["success_k"]}
    (out / "overhead.json").write_text(json.dumps(ovh, indent=1))

    print(json.dumps({"split": args.split, "configs": {r["config"]: {k: r[k] for k in ("success", "fcr", "frr")} for r in rows},
                      "overhead": ovh}, indent=1, default=str))
    print(f"tables in {out / 'tables'}")


if __name__ == "__main__":
    main()
