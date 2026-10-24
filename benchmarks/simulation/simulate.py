"""Simulation-based evaluation (Studies A-F, H) for Agentic Pilot. NOT an execution of the agent.

Every number this script produces is SYNTHETIC: it follows from params.json (assumptions, each tagged)
and from ACTUAL component measurements in inputs/ (measure_inputs.py). The scenario generator, not the
agent, decides how often the planner claims completion, how often actions fail and how memory helps.

Usage:
  python -m benchmarks.simulation.simulate --set dev        # debugging only, never reported
  python -m benchmarks.simulation.simulate --set heldout    # reported set; params frozen beforehand
Outputs go to benchmarks/simulation/out/<set>/.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from pathlib import Path

from benchmarks.e2e.stats import bootstrap_diff_ci, mcnemar_exact, paired_discordance, wilson

HERE = Path(__file__).parent
P = json.loads((HERE / "params.json").read_text())
CATS = [k for k in P["category_mix"] if not k.startswith("_")]
OUTCOMES = [k for k in P["outcome_mix"] if not k.startswith("_")]
MODES = ["navigation_failure", "timeout", "missing_element", "invalid_submission", "unexpected_state", "missing_confirmation"]


# ------------------------------------------------------------------ derived inputs (from ACTUAL measurements)
def derive_inputs() -> dict:
    rows = list(csv.DictReader(open(HERE / "inputs" / "m1_gate_rules.csv")))
    ho = [r for r in rows if r["split"] in P["detector_rates_source"]["splits"]]

    def rate(rule: str, cats: list[str]) -> dict:
        neg = [r for r in ho if r["oracle"] == "0" and r["category"] in cats]
        k = sum(1 for r in neg if r[rule] == "0")
        return {"k": k, "n": len(neg), "rate": (k + 0.5) / (len(neg) + 1)}

    det = {rule: {c: rate(rule, P["detector_category_map"][c]) for c in CATS} for rule in ("basic_accepts", "phi_accepts")}
    pos = [r for r in ho if r["oracle"] == "1"]
    fr = {rule: {"k": sum(1 for r in pos if r[rule] == "0"), "n": len(pos)} for rule in ("basic_accepts", "phi_accepts")}
    for v in fr.values():
        v["rate"] = (v["k"] + 0.5) / (v["n"] + 1)
    mem = list(csv.DictReader(open(HERE / "inputs" / "m4_memory.csv")))
    misleading = [m for m in mem if (not m["n_relevant"] or m["n_relevant"] == "0") or float(m["reciprocal_rank"]) < 1.0
                  or "Status: Failed" in m["top1"]]
    mc = det["phi_accepts"]["multi_step"]
    lat = json.loads((HERE / "inputs" / "m2_latency.json").read_text())
    gate = [float(r["gate_ms_median"]) for r in csv.DictReader(open(HERE.parents[1] / "artifacts" / "results" / "verification_gate_cases.csv"))
            if r["gate_decision"] != "blocked"]
    seq = {r["failure_mode"]: r["strategies_retry0_to_6"].split(" > ") for r in csv.DictReader(open(HERE / "inputs" / "m3_recovery.csv"))}
    return {"detect": det, "false_reject": fr,
            "memory_misleading": {"k": len(misleading), "n": len(mem), "rate": len(misleading) / len(mem),
                                  "groups": [m["group"] for m in misleading]},
            "missing_confirmation_detection": mc, "latency": lat, "phi_ms": gate, "strategy_sequence": seq}


D = derive_inputs()


# ------------------------------------------------------------------ scenario generation
def pick(rng: random.Random, mix: dict) -> str:
    keys = [k for k in mix if not k.startswith("_")]
    return rng.choices(keys, weights=[mix[k] for k in keys])[0]


def generate(seed: int, n: int, outcome_mix: dict | None = None) -> list[dict]:
    rng = random.Random(seed)
    om = outcome_mix or P["outcome_mix"]
    out = []
    for i in range(n):
        cat, oc = pick(rng, P["category_mix"]), pick(rng, om)
        s = {"id": f"S{seed}-{i + 1:03d}", "category": cat, "outcome": oc,
             "y_base": int(rng.random() < P["p_true_complete_given_outcome"][oc]),
             "repeated": int(rng.random() < P["repeated_workflow_share"]["value"])}
        # common random numbers: the same draws are reused by every configuration
        for k in ("claim", "detect", "fr", "missing", "contra", "enh", "enh_fr", "cont", "reclaim",
                  "actfail", "recov", "mem", "mem_eff"):
            s["u_" + k] = rng.random()
        out.append(s)
    return out


CONFIGS = {
    # name: (verifier, memory, recovery, evidence collection)
    "no_verification": ("none", "on", True, True),
    "basic_detection": ("basic", "on", True, True),
    "evidence_gated": ("phi", "on", True, True),
    "enhanced_validation": ("enhanced", "on", True, True),
    # ablations of the full system (= evidence_gated)
    "abl_no_evidence_collection": ("phi", "on", True, False),
    "abl_no_evidence_validation": ("none", "on", True, True),
    "abl_no_memory": ("phi", "off", True, True),
    "abl_no_recovery": ("phi", "on", False, True),
    "mem_filtered": ("phi", "filtered", True, True),
}


def episode(s: dict, cfg: tuple, pi: float | None = None, det_mult: float = 1.0, p_actfail: float | None = None) -> dict:
    verifier, memory, recovery, evidence = cfg
    p_af = P["p_action_failure"]["value"] if p_actfail is None else p_actfail
    # action failure and recovery
    if s["u_actfail"] < p_af and not (recovery and s["u_recov"] < P["p_recovered_with_recovery"]["value"]):
        return {"reported": 0, "y": 0, "failed": 1, "evidence": int(evidence), "claimed": 0, "y_claim": 0}
    # memory on repeated workflows
    y = s["y_base"]
    if s["repeated"] and memory != "off":
        p_mis = D["memory_misleading"]["rate"] if memory == "on" else P["memory_misleading_prob_filtered"]["value"]
        if s["u_mem"] < p_mis:
            if y == 1 and s["u_mem_eff"] < P["memory_misleading_loss"]["value"]:
                y = 0
        elif y == 0 and s["u_mem_eff"] < P["memory_helpful_gain"]["value"]:
            y = 1
    p_claim = P["p_claim_if_complete"]["value"] if y else (P["p_claim_if_not_complete"]["value"] if pi is None else pi)
    if s["u_claim"] >= p_claim:
        return {"reported": 0, "y": y, "failed": 0, "evidence": int(evidence and s["outcome"] != "missing_evidence"),
                "claimed": 0, "y_claim": y}
    ev = int(evidence and s["outcome"] != "missing_evidence")
    # Fields "claimed", "y_claim" and "accepted" describe the verifier's decision at the first completion claim
    # (decision level); "reported" and "y" describe the final outcome of the episode (policy level).
    if verifier == "none":
        return {"reported": 1, "y": y, "failed": 0, "evidence": ev, "claimed": 1, "y_claim": y, "accepted": 1}
    rule = "basic_accepts" if verifier == "basic" else "phi_accepts"
    phi_like = verifier in ("phi", "enhanced")
    if y == 0:
        q = min(1.0, D["detect"][rule][s["category"]]["rate"] * (det_mult if phi_like else 1.0))
        if s["outcome"] == "ambiguous":
            q *= P["ambiguous_detection_factor"]["value"]
        withhold = s["u_detect"] < q
    else:
        withhold = s["u_fr"] < D["false_reject"][rule]["rate"]
    if phi_like and s["outcome"] == "missing_evidence" and s["u_missing"] < P["phi_missing_evidence_reject"]["value"]:
        withhold = True
    if verifier == "enhanced":
        if y == 0 and s["u_enh"] < P["enhanced_extra_catch"]["value"]:
            withhold = True
        if y == 1 and s["u_enh_fr"] < P["enhanced_extra_false_reject"]["value"]:
            withhold = True
        if s["outcome"] == "contradictory_evidence" and s["u_contra"] < P["enhanced_contradiction_reject"]["value"]:
            withhold = True
    if not withhold:
        return {"reported": 1, "y": y, "failed": 0, "evidence": ev, "checks": 1, "claimed": 1, "y_claim": y, "accepted": 1}
    if y == 0:  # rejected premature claim: control returns to planning
        done = s["u_cont"] < P["p_continue_success_after_reject"]["value"]
        return {"reported": int(done), "y": int(done), "failed": 0, "evidence": ev, "checks": 2, "rejected": 1,
                "claimed": 1, "y_claim": 0, "accepted": 0}
    again = s["u_reclaim"] < P["p_reclaim_after_false_reject"]["value"]
    return {"reported": int(again), "y": 1, "failed": 0, "evidence": ev, "checks": 2, "rejected": 1,
            "claimed": 1, "y_claim": 1, "accepted": 0}


def metrics(eps: list[dict]) -> dict:
    tp = sum(1 for e in eps if e["reported"] and e["y"])
    fp = sum(1 for e in eps if e["reported"] and not e["y"])
    fn = sum(1 for e in eps if not e["reported"] and e["y"])
    tn = sum(1 for e in eps if not e["reported"] and not e["y"])
    n = len(eps)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    rec = tp / (tp + fn) if tp + fn else float("nan")
    return {"N": n, "TP": tp, "FP": fp, "FN": fn, "TN": tn, "TSR": tp / n,
            "FCR": fp / (tp + fp) if tp + fp else float("nan"), "FRR": fn / (tp + fn) if tp + fn else float("nan"),
            "precision": prec, "recall": rec, "F1": 2 * prec * rec / (prec + rec) if prec + rec else float("nan"),
            "accuracy": (tp + tn) / n, "evidence_available": sum(e["evidence"] for e in eps) / n}


def cohens_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))


# ------------------------------------------------------------------ Study E: recovery
def recovery_study(seed: int) -> dict:
    rng = random.Random(seed + 7)
    R = P["recovery"]
    scen = []
    for m in MODES:
        for i in range(R["n_per_mode"]):
            scen.append({"id": f"R{seed}-{m}-{i + 1:02d}", "mode": m, "permanent": int(rng.random() < R["permanent_share"]["value"]),
                         "u_detect": rng.random(), "u": [rng.random() for _ in range(R["max_attempts"])]})
    per_attempt_s = P["latency"]["inference_median_s"]["value"] + (D["latency"]["click"]["median_ms"] + D["latency"]["dom_extract"]["median_ms"]) / 1000
    mc_det = D["missing_confirmation_detection"]["rate"]
    out = {}
    for name in ("no_recovery", "retry_based", "evidence_guided"):
        rows = []
        for s in scen:
            if s["mode"] == "missing_confirmation":
                detected = s["u_detect"] < (mc_det if name != "evidence_guided" else R["evidence_guided_confirmation_detection"]["value"])
            else:
                detected = True
            attempts, recovered = 0, False
            if detected and name != "no_recovery" and not s["permanent"]:
                seq = D["strategy_sequence"][s["mode"]]
                for k in range(R["max_attempts"]):
                    if name == "retry_based":
                        st = seq[k]
                        if st == "exhausted":
                            break
                        p = R["p_success_vision"][s["mode"]] if st == "vision_fallback" else R["p_success_replan"][s["mode"]]
                    else:
                        p = R["p_success_evidence_guided"][s["mode"]]
                    attempts += 1
                    if s["u"][k] < p:
                        recovered = True
                        break
            elif detected and name != "no_recovery" and s["permanent"]:
                attempts = sum(1 for st in D["strategy_sequence"][s["mode"]] if st != "exhausted") if name == "retry_based" else R["max_attempts"]
            rows.append({"id": s["id"], "mode": s["mode"], "permanent": s["permanent"], "detected": int(detected),
                         "attempts": attempts, "recovered": int(recovered),
                         "false_completion": int(not detected), "cost_s": round(attempts * per_attempt_s, 2)})
        recoverable = [r for r in rows if not r["permanent"]]
        out[name] = {"rows": rows,
                     "recovery_success": (sum(r["recovered"] for r in recoverable), len(recoverable)),
                     "failure_detection": (sum(r["detected"] for r in rows), len(rows)),
                     "false_completions": sum(r["false_completion"] for r in rows),
                     "unnecessary_attempts": sum(r["attempts"] for r in rows if r["permanent"]),
                     "mean_cost_s": statistics.mean(r["cost_s"] for r in rows),
                     "by_mode": {m: (sum(r["recovered"] for r in recoverable if r["mode"] == m), sum(1 for r in recoverable if r["mode"] == m)) for m in MODES}}
    return out


# ------------------------------------------------------------------ Study F: latency
def latency_study(scen: list[dict], seed: int, inference_median: float | None = None) -> dict:
    """Common random numbers: every configuration sees the same base draws per scenario;
    verification draws come from a separate stream, so configurations differ only by what they add."""
    L = D["latency"]
    med = P["latency"]["inference_median_s"]["value"] if inference_median is None else inference_median
    sigma = P["latency"]["inference_log_sigma"]["value"]

    def infer(rng):
        return med * math.exp(rng.gauss(0, sigma))

    def samp(rng, k):
        return rng.choice(L[k]["samples_ms"]) / 1000

    res = {}
    for name, extra_infer, phi in (("no_verification", 0, False), ("evidence_gated", 0, True),
                                   ("self_verification", 1, False), ("enhanced_validation", 1, True)):
        totals, comp = [], {"inference": 0.0, "browser": 0.0, "evidence": 0.0, "verification": 0.0, "recovery": 0.0}
        for idx, s in enumerate(scen):
            rb = random.Random(seed * 100003 + idx)          # base execution draws
            rv = random.Random(seed * 100003 + idx + 7 ** 9)  # verification draws
            steps = P["latency"]["steps_by_category"][s["category"]]
            t = {"inference": infer(rb), "browser": 0.0, "evidence": 0.0, "verification": 0.0, "recovery": 0.0}
            for k in range(steps):
                t["inference"] += infer(rb)
                t["browser"] += samp(rb, "dom_extract") + samp(rb, "navigate" if k == 0 else rb.choice(["click", "fill"]))
                t["evidence"] += 2 * samp(rb, "screenshot")
            rec_draws = [infer(rb) + samp(rb, "dom_extract") + samp(rb, "click") for _ in range(2)]
            if s["u_actfail"] < P["p_action_failure"]["value"]:
                t["recovery"] += sum(rec_draws)
            checks = 2 if s["outcome"] in ("incomplete", "incorrect_action") else 1
            phi_draws = [rv.choice(D["phi_ms"]) / 1000 for _ in range(checks)]
            judge_draws = [infer(rv) for _ in range(checks)]
            if phi:
                t["verification"] += sum(phi_draws)
            if extra_infer:
                t["verification"] += sum(judge_draws)
            totals.append(sum(t.values()))
            for k in comp:
                comp[k] += t[k]
        totals.sort()
        res[name] = {"median_s": statistics.median(totals), "p95_s": totals[int(round(0.95 * (len(totals) - 1)))],
                     "mean_s": statistics.mean(totals),
                     "share": {k: v / sum(comp.values()) for k, v in comp.items()},
                     "verification_mean_s": comp["verification"] / len(scen), "evidence_mean_s": comp["evidence"] / len(scen)}
    return res


# ------------------------------------------------------------------ main
def run(set_name: str) -> None:
    seed = P["seed_dev"] if set_name == "dev" else P["seed_heldout"]
    out = HERE / "out" / set_name
    out.mkdir(parents=True, exist_ok=True)
    scen = generate(seed, P["n_scenarios"])
    results: dict = {"set": set_name, "seed": seed, "derived_inputs": {k: v for k, v in D.items() if k not in ("latency", "phi_ms")}}

    # Studies A-C: per-scenario outcomes for every configuration (scenario identities shared)
    per = {name: [episode(s, cfg) for s in scen] for name, cfg in CONFIGS.items()}
    with open(out / "scenarios.csv", "w", newline="") as f:
        keys = ["id", "category", "outcome", "y_base", "repeated"]
        w = csv.writer(f)
        w.writerow(keys + [f"{c}_{k}" for c in CONFIGS for k in ("reported", "y")])
        for i, s in enumerate(scen):
            w.writerow([s[k] for k in keys] + [per[c][i][k] for c in CONFIGS for k in ("reported", "y")])
    results["configs"] = {c: metrics(v) for c, v in per.items()}

    ref = per["evidence_gated"]
    tests = {}
    for c in CONFIGS:
        if c == "evidence_gated":
            continue
        correct_ref = [int(e["reported"] == e["y"]) for e in ref]
        correct_c = [int(e["reported"] == e["y"]) for e in per[c]]
        b, cc = paired_discordance([bool(x) for x in correct_ref], [bool(x) for x in correct_c])
        fp_ref = [int(e["reported"] and not e["y"]) for e in ref]
        fp_c = [int(e["reported"] and not e["y"]) for e in per[c]]
        bf, cf = paired_discordance([bool(x) for x in fp_c], [bool(x) for x in fp_ref])
        d, lo, hi = bootstrap_diff_ci(fp_c, fp_ref, clusters=[s["id"] for s in scen])
        tests[c] = {"correct_ref_only": b, "correct_other_only": cc, "mcnemar_p_correct": mcnemar_exact(b, cc),
                    "fp_other_only": bf, "fp_ref_only": cf, "mcnemar_p_fp": mcnemar_exact(bf, cf),
                    "fp_rate_diff": d, "fp_rate_diff_ci": [lo, hi],
                    "cohens_h_tsr": cohens_h(results["configs"]["evidence_gated"]["TSR"], results["configs"][c]["TSR"])}
    results["paired_tests_vs_evidence_gated"] = tests

    # Monte Carlo over generator seeds (simulation uncertainty, not sampling uncertainty of the real system)
    mc = {c: {"FCR": [], "FRR": [], "TSR": []} for c in CONFIGS}
    for r in range(P["monte_carlo_replications"]):
        sc = generate(seed * 1000 + r, P["n_scenarios"])
        for c, cfg in CONFIGS.items():
            m = metrics([episode(s, cfg) for s in sc])
            for k in mc[c]:
                if not math.isnan(m[k]):
                    mc[c][k].append(m[k])
    results["monte_carlo"] = {c: {k: {"mean": statistics.mean(v), "p2.5": sorted(v)[int(0.025 * len(v))], "p97.5": sorted(v)[int(0.975 * len(v)) - 1]}
                                  for k, v in d.items()} for c, d in mc.items()}

    # Study D: memory (repeated workflows only)
    rep = [i for i, s in enumerate(scen) if s["repeated"]]
    results["memory"] = {c: {**metrics([per[c][i] for i in rep]),
                             "contextual_accuracy": (sum(1 for i in rep if scen[i]["u_mem"] >= (D["memory_misleading"]["rate"] if c == "evidence_gated" else P["memory_misleading_prob_filtered"]["value"]))
                                                     / len(rep)) if c != "abl_no_memory" else None}
                         for c in ("abl_no_memory", "evidence_gated", "mem_filtered")}

    # Study E and F
    rec = recovery_study(seed)
    with open(out / "recovery_scenarios.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["config"] + list(rec["retry_based"]["rows"][0]))
        w.writeheader()
        for c, v in rec.items():
            for r in v["rows"]:
                w.writerow({"config": c, **r})
    results["recovery"] = {c: {k: v for k, v in d.items() if k != "rows"} for c, d in rec.items()}
    results["latency"] = latency_study(scen, seed)
    results["latency_sweep"] = {str(m): latency_study(scen, seed, m)["evidence_gated"]["median_s"] for m in P["latency"]["inference_median_s"]["sweep"]}

    # Study H: sensitivity (Monte Carlo, 300 replications per point)
    sens = {"premature_claim_rate": {}, "phi_detection_multiplier": {}, "missing_evidence_share": {}, "action_failure_rate": {}}
    reps = 300

    def mc_point(cfgname, **kw):
        fc, fr, ts = [], [], []
        mix = kw.pop("mix", None)
        for r in range(reps):
            sc = generate(seed * 7919 + r, P["n_scenarios"], mix)
            m = metrics([episode(s, CONFIGS[cfgname], **kw) for s in sc])
            fc.append(m["FCR"]); fr.append(m["FRR"]); ts.append(m["TSR"])
        return {"FCR": statistics.mean(fc), "FRR": statistics.mean(fr), "TSR": statistics.mean(ts)}

    for c in ("basic_detection", "evidence_gated", "enhanced_validation", "no_verification"):
        sens["premature_claim_rate"][c] = {str(pi): mc_point(c, pi=pi) for pi in P["p_claim_if_not_complete"]["sweep"]}
    sens["phi_detection_multiplier"] = {str(m): mc_point("evidence_gated", det_mult=m) for m in (0.5, 1.0, 1.5)}
    for share in (0.0, 0.08, 0.20):
        mix = dict(P["outcome_mix"]); mix["successful"] = 0.48 - share; mix["missing_evidence"] = share
        sens["missing_evidence_share"][str(share)] = {c: mc_point(c, mix=mix) for c in ("basic_detection", "evidence_gated", "enhanced_validation")}
    sens["action_failure_rate"] = {str(a): mc_point("evidence_gated", p_actfail=a) for a in (0.1, 0.25, 0.4)}
    results["sensitivity"] = sens

    (out / "results.json").write_text(json.dumps(results, indent=1, default=str))
    for c, m in results["configs"].items():
        print(f"{c:28s} TP {m['TP']:3d} FP {m['FP']:3d} FN {m['FN']:3d} TN {m['TN']:3d}  TSR {m['TSR']:.2f} FCR {m['FCR']:.3f} FRR {m['FRR']:.3f} F1 {m['F1']:.3f} acc {m['accuracy']:.2f}")
    print("derived:", json.dumps({k: results['derived_inputs'][k] for k in ('false_reject', 'memory_misleading', 'missing_confirmation_detection')}))
    for c, d in results["recovery"].items():
        print("recovery", c, d["recovery_success"], d["failure_detection"], d["false_completions"], d["unnecessary_attempts"], round(d["mean_cost_s"], 1))
    for c, d in results["latency"].items():
        print("latency", c, round(d["median_s"], 1), round(d["p95_s"], 1), {k: round(v, 3) for k, v in d["share"].items()})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=["dev", "heldout"], default="dev")
    run(ap.parse_args().set)
