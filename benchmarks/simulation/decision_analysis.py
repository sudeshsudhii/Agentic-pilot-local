"""Separate decision-level verification accuracy from policy-level task success (audit issues A and B).

Decision level: among scenarios in which the planner claims completion, does the verifier's first
accept/withhold decision match the true state at the moment of the claim (y_claim)? The four verifier
configurations share memory and recovery settings, so the set of claims and y_claim are identical across
them and the comparison is paired on the same units with the same ground truth.

Policy level: does the episode end with the task achieved and reported (success = reported and y)?
The final state y may differ across configurations for the same scenario, because a rejection returns
control to planning and the episode may then finish; success is still a well-defined paired binary outcome.

The earlier "correct = (reported == y)" indicator mixed both levels: y is configuration-dependent, so the
indicator compares each configuration against a different ground truth. Its p = 0.80 is withdrawn.

All values are SYNTHETIC and conditional on params.json. Usage: python -m benchmarks.simulation.decision_analysis
"""

from __future__ import annotations

import json
from pathlib import Path

from benchmarks.e2e.stats import mcnemar_exact, wilson
from benchmarks.simulation import simulate as S

HERE = Path(__file__).parent
VERIFIERS = ["no_verification", "basic_detection", "evidence_gated", "enhanced_validation"]


def main() -> None:
    scen = S.generate(S.P["seed_heldout"], S.P["n_scenarios"])
    eps = {c: [S.episode(s, S.CONFIGS[c]) for s in scen] for c in VERIFIERS}

    claimed = [i for i, e in enumerate(eps["evidence_gated"]) if e["claimed"]]
    for c in VERIFIERS:  # same claims and same y_claim across verifier configurations
        assert [i for i, e in enumerate(eps[c]) if e["claimed"]] == claimed
        assert [eps[c][i]["y_claim"] for i in claimed] == [eps["evidence_gated"][i]["y_claim"] for i in claimed]

    out: dict = {"n_scenarios": len(scen), "n_claims": len(claimed),
                 "n_claims_true": sum(eps["evidence_gated"][i]["y_claim"] for i in claimed), "decision": {}, "policy": {}}
    dec_correct = {}
    for c in VERIFIERS:
        tp = sum(1 for i in claimed if eps[c][i]["accepted"] and eps[c][i]["y_claim"])
        fp = sum(1 for i in claimed if eps[c][i]["accepted"] and not eps[c][i]["y_claim"])
        fn = sum(1 for i in claimed if not eps[c][i]["accepted"] and eps[c][i]["y_claim"])
        tn = sum(1 for i in claimed if not eps[c][i]["accepted"] and not eps[c][i]["y_claim"])
        k = tp + tn
        lo, hi = wilson(k, len(claimed))
        out["decision"][c] = {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "accuracy": k / len(claimed),
                              "accuracy_wilson": [lo, hi], "accepted": tp + fp}
        dec_correct[c] = [int(eps[c][i]["accepted"] == eps[c][i]["y_claim"]) for i in claimed]

    success = {c: [int(e["reported"] and e["y"]) for e in eps[c]] for c in VERIFIERS}
    for c in VERIFIERS:
        k = sum(success[c])
        lo, hi = wilson(k, len(scen))
        out["policy"][c] = {"success": k, "TSR": k / len(scen), "TSR_wilson": [lo, hi]}

    out["paired_vs_evidence_gated"] = {}
    for c in VERIFIERS:
        if c == "evidence_gated":
            continue
        ref, oth = dec_correct["evidence_gated"], dec_correct[c]
        b = sum(1 for x, y in zip(ref, oth) if x and not y)
        d = sum(1 for x, y in zip(ref, oth) if y and not x)
        sr, so = success["evidence_gated"], success[c]
        bs = sum(1 for x, y in zip(sr, so) if x and not y)
        ds = sum(1 for x, y in zip(sr, so) if y and not x)
        out["paired_vs_evidence_gated"][c] = {
            "decision_correct_phi_only": b, "decision_correct_other_only": d, "decision_mcnemar_p": mcnemar_exact(b, d),
            "success_phi_only": bs, "success_other_only": ds, "success_mcnemar_p": mcnemar_exact(bs, ds)}

    # the withdrawn analysis, reproduced for the correction report
    old = json.loads((HERE / "out" / "heldout" / "results.json").read_text())["paired_tests_vs_evidence_gated"]["no_verification"]
    out["withdrawn_mixed_indicator_no_verification"] = {k: old[k] for k in ("correct_ref_only", "correct_other_only", "mcnemar_p_correct")}

    (HERE / "out" / "heldout" / "decision_analysis.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
