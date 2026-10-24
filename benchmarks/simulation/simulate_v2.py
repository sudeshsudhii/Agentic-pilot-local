"""Corrected simulation model (v2). SYNTHETIC; NOT an execution of the agent.

v2 was written after the v1 results and after an independent methodology audit
(artifacts/results/final_audit/audit_*.md). It is therefore not pre-registered. It reuses v1's scenario generator, seeds
and assumptions, so scenario identities are the same, and changes only what the audit showed to contradict
the implementation or the measurements:

  C1  False-rejection rates are derived from the same gate categories as the detection rates. v1 took them
      from all satisfied held-out states, and both of Phi's false rejections were bot-check pages (H7, B4),
      a category the scenarios do not contain.
  C2  The basic detector also fails closed when the page cannot be read (it shares the error check E).
  C3  After a rejected premature claim, a successful continuation is checked again by the verifier, as
      verify_node does; a false rejection of an unchanged, completed page is repeated (the rule check is
      deterministic), so v1's unconditional re-claim acceptance is removed.
  C4  Recovery follows the implemented path per failure mode: three inline retries in verify_node for action
      errors, including need_help, then the recovery engine from retry count 3; a failed initial navigation is
      retried three times by the browser executor and then enters the engine at retry count 0; a missing
      confirmation raises no error and is handled by rejection and continuation. With recovery disabled the
      engine fails at once but the retries before it remain. The policy simulation's recovery probabilities are
      taken from this recovery study instead of a separate assumption. Each scenario has one failure, which
      matches the code for the first failure of a task (the retry counter is per task).
  C5  Monte Carlo replications also draw every derived rate from its Beta posterior (Jeffreys prior),
      so the percentiles include parameter uncertainty.
  C6  The latency model counts re-planning after rejections, a check per claim, three screenshots per step
      and two at completion (as in the code), and recovery attempts from the recovery study.
  C7  Study H additionally sweeps the continuation rate, which v1's paper text wrongly said was swept.

Usage: python -m benchmarks.simulation.simulate_v2   -> out/heldout_v2/
"""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
from pathlib import Path

from benchmarks.e2e.stats import mcnemar_exact, wilson
from benchmarks.simulation import simulate as V1

HERE = Path(__file__).parent
P = V1.P
OUT = HERE / "out" / "heldout_v2"
SEED = P["seed_heldout"]
FAILURE_MSG = {
    "navigation_failure": "Navigation failed: net::ERR_NAME_NOT_RESOLVED at http://shop.example",
    "timeout": "Timeout 30000ms exceeded while waiting for selector",
    "missing_element": "Element has no usable selector: element not found on page",
    "invalid_submission": "Input verification failed: field value does not match requested text",
    "unexpected_state": "Agent needed assistance: page layout differs from plan, need_help",
}
# Entry path per failure mode (code inspection, backend/agent/graph.py, nodes.py, browser/executor.py):
#   inline:   action error -> verify_node retries up to 3 times through a fresh observation, then error_recovery
#             from retry count 3. need_help is turned into an error by execute_action_node, so it takes this
#             path too (the need_help branch of verify_node is reached only after the error check).
#   executor: initial navigation -> PlaywrightExecutor.navigate retries transient net::ERR_/timeout errors up to
#             3 times itself, then navigate_node routes the error to error_recovery from retry count 0. The
#             executor's immediate retries are modelled with the same assumed per-attempt success rate.
#   (Correction after the independent final review: v2 first sent need_help and navigation failures to the
#    engine directly, without these retries.)
ENTRY = {"navigation_failure": "executor", "timeout": "inline", "missing_element": "inline",
         "invalid_submission": "inline", "unexpected_state": "inline", "missing_confirmation": "continuation"}


# ------------------------------------------------------------------ derived rates (C1)
def derive_rates() -> dict:
    rows = list(csv.DictReader(open(HERE / "inputs" / "m1_gate_rules.csv")))
    ho = [r for r in rows if r["split"] in P["detector_rates_source"]["splits"]]
    mapped = sorted({g for c in V1.CATS for g in P["detector_category_map"][c]})
    pos = [r for r in ho if r["oracle"] == "1" and r["category"] in mapped]
    fr = {}
    for rule in ("basic_accepts", "phi_accepts"):
        k = sum(1 for r in pos if r[rule] == "0")
        fr[rule] = {"k": k, "n": len(pos), "rate": (k + 0.5) / (len(pos) + 1)}
    return {"detect": V1.D["detect"], "false_reject": fr, "memory_misleading": V1.D["memory_misleading"],
            "missing_confirmation_detection": V1.D["missing_confirmation_detection"],
            "false_reject_v1": V1.D["false_reject"], "false_reject_categories": mapped}


RATES = derive_rates()


def sample_rates(rng: random.Random) -> dict:
    """C5: draw each derived rate from Beta(k+0.5, n-k+0.5)."""
    def b(k, n):
        return rng.betavariate(k + 0.5, n - k + 0.5)
    det = {rule: {c: {"rate": b(v["k"], v["n"])} for c, v in cats.items()} for rule, cats in RATES["detect"].items()}
    fr = {rule: {"rate": b(v["k"], v["n"])} for rule, v in RATES["false_reject"].items()}
    mm = RATES["memory_misleading"]
    mc = RATES["missing_confirmation_detection"]
    return {"detect": det, "false_reject": fr, "memory_misleading": {"rate": b(mm["k"], mm["n"])},
            "missing_confirmation_detection": {"rate": b(mc["k"], mc["n"])}}


def v2_draws(s: dict) -> dict:
    """Extra per-scenario draws from a separate stream, so v1 scenario identities are unchanged."""
    r = random.Random(f"{s['id']}-v2")
    return {"u_fr2": r.random(), "u_enh_fr2": r.random()}


# ------------------------------------------------------------------ recovery study (C4)
def engine_sequences() -> dict:
    from backend.recovery.engine import RecoveryEngine

    eng = RecoveryEngine()
    seq = {}
    for m, msg in FAILURE_MSG.items():
        ftype = eng.classify_failure(msg)
        start = 3 if ENTRY[m] == "inline" else 0
        seq[m] = {"failure_type": ftype,
                  "engine": [s for s in (eng.select_strategy(ftype, r) for r in range(start, 7)) if True]}
        # stop at the first exhausted
        if "exhausted" in seq[m]["engine"]:
            seq[m]["engine"] = seq[m]["engine"][: seq[m]["engine"].index("exhausted")]
    return seq


SEQ = engine_sequences()


def attempts_plan(mode: str, config: str) -> list[str]:
    """Ordered list of attempt kinds: 'replan' (fresh observation and planning) or 'vision'."""
    if ENTRY[mode] == "continuation":
        return []
    inline = ["replan"] * 3 if ENTRY[mode] in ("inline", "executor") else []
    if config == "no_recovery":
        return inline
    if config == "evidence_guided":
        return ["guided"] * P["recovery"]["max_attempts"]
    eng = ["vision" if st == "vision_fallback" else "replan" for st in SEQ[mode]["engine"]]
    return inline + eng


def recovery_study(rates: dict | None = None, seed: int = SEED) -> dict:
    rates = rates or RATES
    rng = random.Random(seed + 7)  # same scenario draws as v1's recovery study
    R = P["recovery"]
    scen = []
    for m in V1.MODES:
        for i in range(R["n_per_mode"]):
            scen.append({"id": f"R{seed}-{m}-{i + 1:02d}", "mode": m, "permanent": int(rng.random() < R["permanent_share"]["value"]),
                         "u_detect": rng.random(), "u": [rng.random() for _ in range(R["max_attempts"])]})
    p_cont = P["p_continue_success_after_reject"]["value"]
    out = {}
    for config in ("no_recovery", "retry_based", "evidence_guided"):
        rows = []
        for s in scen:
            m = s["mode"]
            attempts, recovered, detected = 0, False, True
            if m == "missing_confirmation":
                det_rate = R["evidence_guided_confirmation_detection"]["value"] if config == "evidence_guided" else rates["missing_confirmation_detection"]["rate"]
                detected = s["u_detect"] < det_rate
                if detected and not s["permanent"]:
                    if config == "evidence_guided":  # proposed: explicit confirmation check, repeated attempts
                        for k in range(R["max_attempts"]):
                            attempts += 1
                            if s["u"][k] < R["p_success_evidence_guided"][m]:
                                recovered = True
                                break
                    else:  # implemented: rejection returns to planning once; no recovery-engine involvement
                        attempts = 1
                        recovered = s["u"][0] < p_cont
            else:
                plan = attempts_plan(m, config)
                for k, kind in enumerate(plan[: R["max_attempts"] + 3]):
                    attempts += 1
                    if s["permanent"]:
                        continue
                    p = {"replan": R["p_success_replan"][m], "vision": R["p_success_vision"][m],
                         "guided": R["p_success_evidence_guided"][m]}[kind]
                    if s["u"][k % len(s["u"])] < p:
                        recovered = True
                        break
            rows.append({"id": s["id"], "mode": m, "permanent": s["permanent"], "detected": int(detected),
                         "attempts": attempts, "recovered": int(recovered), "false_completion": int(not detected)})
        rec = [r for r in rows if not r["permanent"]]
        out[config] = {"rows": rows, "recovery_success": (sum(r["recovered"] for r in rec), len(rec)),
                       "failure_detection": (sum(r["detected"] for r in rows), len(rows)),
                       "false_completions": sum(r["false_completion"] for r in rows),
                       "unnecessary_attempts": sum(r["attempts"] for r in rows if r["permanent"]),
                       "mean_attempts": statistics.mean(r["attempts"] for r in rows),
                       "recovered_share_all": sum(r["recovered"] for r in rows) / len(rows),
                       "recovered_share_action_errors": (sum(r["recovered"] for r in rows if r["mode"] != "missing_confirmation")
                                                         / sum(1 for r in rows if r["mode"] != "missing_confirmation")),
                       "by_mode": {mm: (sum(r["recovered"] for r in rec if r["mode"] == mm), sum(1 for r in rec if r["mode"] == mm)) for mm in V1.MODES}}
    return out


REC = recovery_study()
P_REC = {True: REC["retry_based"]["recovered_share_action_errors"], False: REC["no_recovery"]["recovered_share_action_errors"]}


# ------------------------------------------------------------------ episode model (C2, C3)
def episode(s: dict, cfg: tuple, rates: dict | None = None, pi: float | None = None, det_mult: float = 1.0,
            p_actfail: float | None = None, p_cont: float | None = None, p_rec: dict | None = None) -> dict:
    rates = rates or RATES
    p_rec = p_rec or P_REC
    x = v2_draws(s)
    verifier, memory, recovery, evidence = cfg
    p_af = P["p_action_failure"]["value"] if p_actfail is None else p_actfail
    pc = P["p_continue_success_after_reject"]["value"] if p_cont is None else p_cont
    if s["u_actfail"] < p_af and not (s["u_recov"] < p_rec[recovery]):
        return {"reported": 0, "y": 0, "failed": 1, "claimed": 0, "y_claim": 0, "rejections": 0}
    y = s["y_base"]
    if s["repeated"] and memory != "off":
        p_mis = rates["memory_misleading"]["rate"] if memory == "on" else P["memory_misleading_prob_filtered"]["value"]
        if s["u_mem"] < p_mis:
            if y == 1 and s["u_mem_eff"] < P["memory_misleading_loss"]["value"]:
                y = 0
        elif y == 0 and s["u_mem_eff"] < P["memory_helpful_gain"]["value"]:
            y = 1
    p_claim = P["p_claim_if_complete"]["value"] if y else (P["p_claim_if_not_complete"]["value"] if pi is None else pi)
    if s["u_claim"] >= p_claim:
        return {"reported": 0, "y": y, "failed": 0, "claimed": 0, "y_claim": y, "rejections": 0}
    if verifier == "none":
        return {"reported": 1, "y": y, "failed": 0, "claimed": 1, "y_claim": y, "accepted": 1, "rejections": 0}
    rule = "basic_accepts" if verifier == "basic" else "phi_accepts"
    fr_rate = rates["false_reject"][rule]["rate"]

    def rejects_complete(u_fr, u_enh) -> bool:
        r = u_fr < fr_rate
        if verifier == "enhanced" and u_enh < P["enhanced_extra_false_reject"]["value"]:
            r = True
        return r

    if y == 0:
        q = min(1.0, rates["detect"][rule][s["category"]]["rate"] * (det_mult if verifier in ("phi", "enhanced") else 1.0))
        if s["outcome"] == "ambiguous":
            q *= P["ambiguous_detection_factor"]["value"]
        withhold = s["u_detect"] < q
        if verifier == "enhanced" and s["u_enh"] < P["enhanced_extra_catch"]["value"]:
            withhold = True
    else:
        withhold = rejects_complete(s["u_fr"], s["u_enh_fr"])
    if s["outcome"] == "missing_evidence" and s["u_missing"] < P["phi_missing_evidence_reject"]["value"]:
        withhold = True  # C2: every rule-based verifier fails closed on an unreadable page
    if verifier == "enhanced" and s["outcome"] == "contradictory_evidence" and s["u_contra"] < P["enhanced_contradiction_reject"]["value"]:
        withhold = True
    if not withhold:
        return {"reported": 1, "y": y, "failed": 0, "claimed": 1, "y_claim": y, "accepted": 1, "rejections": 0}
    if y == 1:  # C3: deterministic check rejects the unchanged, completed page again
        return {"reported": 0, "y": 1, "failed": 0, "claimed": 1, "y_claim": 1, "accepted": 0, "rejections": 1}
    if s["u_cont"] < pc:  # continuation reaches completion; C3: the new claim is checked again
        if rejects_complete(x["u_fr2"], x["u_enh_fr2"]):
            return {"reported": 0, "y": 1, "failed": 0, "claimed": 1, "y_claim": 0, "accepted": 0, "rejections": 2, "continued": 1}
        return {"reported": 1, "y": 1, "failed": 0, "claimed": 1, "y_claim": 0, "accepted": 0, "rejections": 1, "continued": 1}
    return {"reported": 0, "y": 0, "failed": 0, "claimed": 1, "y_claim": 0, "accepted": 0, "rejections": 1}


VERIFIERS = ["no_verification", "basic_detection", "evidence_gated", "enhanced_validation"]
CONFIGS = {k: v for k, v in V1.CONFIGS.items() if k != "abl_no_evidence_collection"}  # that row is not simulated in v2


def decision_metrics(eps: list[dict], claimed: list[int]) -> dict:
    tp = sum(1 for i in claimed if eps[i]["accepted"] and eps[i]["y_claim"])
    fp = sum(1 for i in claimed if eps[i]["accepted"] and not eps[i]["y_claim"])
    fn = sum(1 for i in claimed if not eps[i]["accepted"] and eps[i]["y_claim"])
    tn = sum(1 for i in claimed if not eps[i]["accepted"] and not eps[i]["y_claim"])
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": (tp + tn) / len(claimed),
            "FCR": fp / (tp + fp) if tp + fp else float("nan"), "FRR": fn / (tp + fn) if tp + fn else float("nan")}


def run_set(scen: list[dict], rates=None, **kw) -> dict:
    eps = {c: [episode(s, cfg, rates=rates, **kw) for s in scen] for c, cfg in CONFIGS.items()}
    claimed = [i for i, e in enumerate(eps["evidence_gated"]) if e["claimed"]]
    for c in VERIFIERS:
        assert [i for i, e in enumerate(eps[c]) if e["claimed"]] == claimed
    return {"eps": eps, "claimed": claimed}


def paired(a: list[int], b: list[int]) -> tuple[int, int, float]:
    x = sum(1 for p, q in zip(a, b) if p and not q)
    y = sum(1 for p, q in zip(a, b) if q and not p)
    return x, y, mcnemar_exact(x, y)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scen = V1.generate(SEED, P["n_scenarios"])
    rs = run_set(scen)
    eps, claimed = rs["eps"], rs["claimed"]
    res: dict = {"model": "v2", "seed": SEED, "rates": {k: v for k, v in RATES.items()},
                 "recovery_probabilities_used": {"recovery_on": P_REC[True], "recovery_off": P_REC[False]},
                 "n_claims": len(claimed), "n_claims_true": sum(eps["evidence_gated"][i]["y_claim"] for i in claimed),
                 "policy": {c: V1.metrics([{**e, "evidence": 0} for e in v]) for c, v in eps.items()},
                 "decision": {c: decision_metrics(eps[c], claimed) for c in VERIFIERS}}
    ref = "evidence_gated"
    res["paired_vs_evidence_gated"] = {}
    for c in [k for k in CONFIGS if k != ref]:
        fc_o = [int(e["reported"] and not e["y"]) for e in eps[c]]
        fc_r = [int(e["reported"] and not e["y"]) for e in eps[ref]]
        su_o = [int(e["reported"] and e["y"]) for e in eps[c]]
        su_r = [int(e["reported"] and e["y"]) for e in eps[ref]]
        d = {"fc_other_only": paired(fc_o, fc_r)[0], "fc_phi_only": paired(fc_o, fc_r)[1], "fc_p": paired(fc_o, fc_r)[2],
             "success_other_only": paired(su_o, su_r)[0], "success_phi_only": paired(su_o, su_r)[1], "success_p": paired(su_o, su_r)[2]}
        if c in VERIFIERS:
            dc_o = [int(eps[c][i]["accepted"] == eps[c][i]["y_claim"]) for i in claimed]
            dc_r = [int(eps[ref][i]["accepted"] == eps[ref][i]["y_claim"]) for i in claimed]
            d.update({"decision_other_only": paired(dc_o, dc_r)[0], "decision_phi_only": paired(dc_o, dc_r)[1], "decision_p": paired(dc_o, dc_r)[2]})
        res["paired_vs_evidence_gated"][c] = d

    with open(OUT / "scenarios.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "outcome", "y_base", "repeated"] + [f"{c}_{k}" for c in CONFIGS for k in ("reported", "y", "claimed", "y_claim", "accepted")])
        for i, s in enumerate(scen):
            w.writerow([s[k] for k in ("id", "category", "outcome", "y_base", "repeated")] +
                       [eps[c][i].get(k, "") for c in CONFIGS for k in ("reported", "y", "claimed", "y_claim", "accepted")])

    # Monte Carlo with parameter uncertainty (C5)
    rng = random.Random(SEED * 31)
    mc = {c: {"FCR": [], "TSR": [], "dec_acc": []} for c in CONFIGS}
    mc_fc_diff, mc_sig_fc, mc_sig_dec = [], 0, 0
    reps = P["monte_carlo_replications"]
    for r in range(reps):
        rates = sample_rates(rng)
        p_rec_r = {True: P_REC[True], False: P_REC[False]}
        sc = V1.generate(SEED * 1000 + r, P["n_scenarios"])
        out = run_set(sc, rates=rates, p_rec=p_rec_r)
        e, cl = out["eps"], out["claimed"]
        for c in CONFIGS:
            m = V1.metrics([{**x, "evidence": 0} for x in e[c]])
            if not math.isnan(m["FCR"]):
                mc[c]["FCR"].append(m["FCR"])
            mc[c]["TSR"].append(m["TSR"])
            if c in VERIFIERS and cl:
                mc[c]["dec_acc"].append(decision_metrics(e[c], cl)["accuracy"])
        fo = [int(x["reported"] and not x["y"]) for x in e["no_verification"]]
        fr_ = [int(x["reported"] and not x["y"]) for x in e[ref]]
        mc_fc_diff.append((sum(fo) - sum(fr_)) / len(sc))
        mc_sig_fc += paired(fo, fr_)[2] < 0.05
        if cl:
            do = [int(e["no_verification"][i]["accepted"] == e["no_verification"][i]["y_claim"]) for i in cl]
            dr = [int(e[ref][i]["accepted"] == e[ref][i]["y_claim"]) for i in cl]
            mc_sig_dec += paired(dr, do)[2] < 0.05 and sum(dr) > sum(do)

    def summ(v):
        v = sorted(v)
        return {"mean": statistics.mean(v), "p2.5": v[int(0.025 * len(v))], "p97.5": v[int(0.975 * len(v)) - 1]}

    res["monte_carlo"] = {c: {k: summ(v) for k, v in d.items() if v} for c, d in mc.items()}
    res["monte_carlo_paired"] = {"fc_reduction_phi_vs_none": summ(mc_fc_diff), "share_fc_p_lt_05": mc_sig_fc / reps,
                                 "share_decision_phi_better_p_lt_05": mc_sig_dec / reps}

    # memory subset (repeated workflows), labelled memory only
    rep = [i for i, s in enumerate(scen) if s["repeated"]]
    res["memory"] = {c: V1.metrics([{**eps[c][i], "evidence": 0} for i in rep]) for c in ("abl_no_memory", "evidence_gated", "mem_filtered")}

    # recovery study rows
    with open(OUT / "recovery_scenarios.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["config"] + list(REC["retry_based"]["rows"][0]))
        w.writeheader()
        for c, v in REC.items():
            for r in v["rows"]:
                w.writerow({"config": c, **r})
    res["recovery"] = {c: {k: v for k, v in d.items() if k != "rows"} for c, d in REC.items()}
    rb, eg = REC["retry_based"]["rows"], REC["evidence_guided"]["rows"]
    res["recovery_paired_guided_vs_retry"] = paired([r["recovered"] for r in eg if not r["permanent"]], [r["recovered"] for r in rb if not r["permanent"]])

    # latency (C6)
    res["latency"] = latency(scen, eps)
    res["latency_sweep"] = {str(m): latency(scen, eps, m)["evidence_gated"]["median_s"] for m in P["latency"]["inference_median_s"]["sweep"]}

    # sensitivity (C7), 300 replications per point, parameters at point estimates
    def point(cfg, **kw):
        fc, ts, fr = [], [], []
        mix = kw.pop("mix", None)
        for r in range(300):
            sc = V1.generate(SEED * 7919 + r, P["n_scenarios"], mix)
            m = V1.metrics([{**episode(s, CONFIGS[cfg], **kw), "evidence": 0} for s in sc])
            fc.append(m["FCR"]); ts.append(m["TSR"]); fr.append(m["FRR"])
        return {"FCR": statistics.mean(fc), "FRR": statistics.mean(fr), "TSR": statistics.mean(ts)}

    sens = {"premature_claim_rate": {c: {str(pi): point(c, pi=pi) for pi in P["p_claim_if_not_complete"]["sweep"]} for c in VERIFIERS},
            "phi_detection_multiplier": {str(m): point("evidence_gated", det_mult=m) for m in (0.5, 1.0, 1.5)},
            "continuation_rate": {c: {str(pc): point(c, p_cont=pc) for pc in (0.1, 0.35, 0.6)} for c in ("no_verification", "evidence_gated")},
            "action_failure_rate": {str(a): point("evidence_gated", p_actfail=a) for a in (0.1, 0.25, 0.4)},
            "missing_evidence_share": {}}
    for share in (0.0, 0.08, 0.20):
        mix = dict(P["outcome_mix"]); mix["successful"] = 0.48 - share; mix["missing_evidence"] = share
        sens["missing_evidence_share"][str(share)] = point("evidence_gated", mix=mix)
    res["sensitivity"] = sens
    (OUT / "results.json").write_text(json.dumps(res, indent=1, default=str))
    for c in CONFIGS:
        m = res["policy"][c]
        print(f"{c:28s} policy TP {m['TP']:3d} FP {m['FP']:3d} FN {m['FN']:3d} TN {m['TN']:3d} TSR {m['TSR']:.2f} FCR {m['FCR']:.3f}")
    for c in VERIFIERS:
        print(c, "decision", res["decision"][c])
    print(json.dumps(res["paired_vs_evidence_gated"], indent=0)[:1500])
    print("rates FR v2", RATES["false_reject"], "P_REC", P_REC)
    print("MC paired", res["monte_carlo_paired"])
    print("recovery", {c: (d["recovery_success"], d["false_completions"], d["unnecessary_attempts"], round(d["mean_attempts"], 2)) for c, d in res["recovery"].items()}, res["recovery_paired_guided_vs_retry"])
    print("latency", {c: (round(d["median_s"], 1), round(d["p95_s"], 1), round(d["verify_share"] * 100, 2), round(d["mean_s"], 2)) for c, d in res["latency"].items()})


def latency(scen: list[dict], eps: dict, inference_median: float | None = None) -> dict:
    L = V1.D["latency"]
    med = P["latency"]["inference_median_s"]["value"] if inference_median is None else inference_median
    sig = P["latency"]["inference_log_sigma"]["value"]
    att = {True: REC["retry_based"]["mean_attempts"], False: REC["no_recovery"]["mean_attempts"]}
    out = {}
    for name, verifier_key, judge in (("no_verification", "no_verification", False), ("evidence_gated", "evidence_gated", False),
                                      ("self_verification", "no_verification", True), ("enhanced_validation", "enhanced_validation", True)):
        tot, comp = [], {k: 0.0 for k in ("inference", "browser", "evidence", "verification", "recovery")}
        for i, s in enumerate(scen):
            rb = random.Random(SEED * 100003 + i)
            rv = random.Random(SEED * 100003 + i + 7 ** 9)
            inf = lambda r: med * math.exp(r.gauss(0, sig))  # noqa: E731
            smp = lambda r, k: r.choice(L[k]["samples_ms"]) / 1000  # noqa: E731
            e = eps[verifier_key][i]
            steps = P["latency"]["steps_by_category"][s["category"]]
            t = {k: 0.0 for k in comp}
            t["inference"] += inf(rb)
            for k in range(steps):
                t["inference"] += inf(rb)
                t["browser"] += smp(rb, "dom_extract") + smp(rb, "navigate" if k == 0 else rb.choice(["click", "fill"]))
                t["evidence"] += 3 * smp(rb, "screenshot")
            t["evidence"] += 2 * smp(rb, "screenshot")
            rejections = e.get("rejections", 0) if verifier_key != "no_verification" else 0
            if judge and verifier_key == "no_verification":  # self-verification: model judges each claim
                rejections = 0
            for _ in range(rejections):  # re-plan after a rejection
                t["inference"] += inf(rv)
                t["browser"] += smp(rv, "dom_extract") + smp(rv, "click")
                t["evidence"] += 3 * smp(rv, "screenshot")
            checks = (1 + rejections) if e.get("claimed") else 0
            if verifier_key != "no_verification":
                t["verification"] += sum(rv.choice(V1.D["phi_ms"]) / 1000 for _ in range(checks))
            if judge:
                t["verification"] += sum(inf(rv) for _ in range(max(checks, 1 if e.get("claimed") else 0)))
            if s["u_actfail"] < P["p_action_failure"]["value"]:
                for _ in range(round(att[True])):
                    t["recovery"] += inf(rb) + smp(rb, "dom_extract") + smp(rb, "click")
            tot.append(sum(t.values()))
            for k in comp:
                comp[k] += t[k]
        tot.sort()
        out[name] = {"median_s": statistics.median(tot), "p95_s": tot[int(round(0.95 * (len(tot) - 1)))], "mean_s": statistics.mean(tot),
                     "verify_share": comp["verification"] / sum(comp.values()), "inference_share": comp["inference"] / sum(comp.values()),
                     "evidence_share": comp["evidence"] / sum(comp.values()), "replan_inference_mean_s": None}
    return out


if __name__ == "__main__":
    main()
