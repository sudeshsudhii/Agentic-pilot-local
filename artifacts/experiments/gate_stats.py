"""Statistics for the completion-gate study (R9): counts, 95% intervals and paired exact tests.

Reads artifacts/results/verification_gate_cases.csv (current code), *_before_fixes.csv (code before
the fixes; design and first held-out sets only) and verification_gate_ablation.csv.
Writes artifacts/results/gate_stats.csv and prints a readable summary.

All comparisons are paired by state. Against the dispatch-only rule, which accepts every state,
the discordant pairs are exactly the unsatisfied states the gate withholds (b) and the satisfied
states it rejects (c); McNemar's exact test is then a sign test on b vs c for each error type.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from benchmarks.e2e.stats import clopper_pearson, mcnemar_exact, paired_discordance, wilson  # noqa: E402

RES = REPO / "artifacts" / "results"


def rows(name: str) -> list[dict]:
    p = RES / name
    return list(csv.DictReader(open(p))) if p.exists() else []


def interval(k: int, n: int) -> str:
    if not n:
        return "--"
    w, c = wilson(k, n), clopper_pearson(k, n)
    return f"{k}/{n}={k / n:.2f} W[{w[0]:.2f},{w[1]:.2f}] CP[{c[0]:.2f},{c[1]:.2f}]"


def describe(sub: list[dict], accepts) -> dict:
    neg = [r for r in sub if r["oracle_satisfied"] == "0"]
    pos = [r for r in sub if r["oracle_satisfied"] == "1"]
    rep = [r for r in sub if accepts(r)]
    fc = [r for r in rep if r["oracle_satisfied"] == "0"]
    fr = [r for r in pos if not accepts(r)]
    withheld = len(neg) - len(fc)
    return {"n": len(sub), "unsat": len(neg), "sat": len(pos), "withheld": withheld, "fc": len(fc), "fr": len(fr),
            "reported": len(rep), "withheld_rate": interval(withheld, len(neg)), "FCR": interval(len(fc), len(rep)),
            "FRR": interval(len(fr), len(pos))}


def main() -> None:
    cur = rows("verification_gate_cases.csv")
    pre = {r["case"]: r for r in rows("verification_gate_cases_before_fixes.csv")}
    out = []
    gate = lambda r: r["gate_reports_complete"] == "1"  # noqa: E731
    live = lambda r: r["live_verbose_reports_complete"] == "1"  # noqa: E731
    for split in ("design", "held_out", "held_out_2"):
        sub = [r for r in cur if r["split"] == split]
        if not sub:
            continue
        cats = sorted({r["category"] for r in sub})
        for label, part in [("all", sub)] + [(c, [r for r in sub if r["category"] == c]) for c in cats]:
            for rule, acc in (("dispatch_only", lambda r: True), ("gate", gate), ("gate_live_verbose", live)):
                d = describe(part, acc)
                rec = {"split": split, "subset": label, "rule": rule, **d}
                if rule != "dispatch_only" and label == "all":
                    # paired vs dispatch-only, separately for the two error types
                    neg = [r for r in part if r["oracle_satisfied"] == "0"]
                    pos = [r for r in part if r["oracle_satisfied"] == "1"]
                    rec["p_fc_vs_dispatch"] = mcnemar_exact(sum(1 for r in neg if not acc(r)), 0)
                    rec["p_fr_vs_dispatch"] = mcnemar_exact(0, sum(1 for r in pos if not acc(r)))
                    # paired vs the gate before the fixes (same states, correct/incorrect decision)
                    if all(r["case"] in pre for r in part):
                        pre_acc = (lambda r: pre[r["case"]]["gate_reports_complete"] == "1") if rule == "gate" else \
                                  (lambda r: pre[r["case"]]["live_verbose_reports_complete"] == "1")
                        correct_now = [acc(r) == (r["oracle_satisfied"] == "1") for r in part]
                        correct_pre = [pre_acc(r) == (r["oracle_satisfied"] == "1") for r in part]
                        b, c = paired_discordance(correct_now, correct_pre)
                        rec.update({"fixed_vs_pre": b, "broken_vs_pre": c, "p_vs_pre": mcnemar_exact(b, c)})
                        dpre = describe(part, pre_acc)
                        rec["pre_fc"], rec["pre_fr"] = dpre["fc"], dpre["fr"]
                out.append(rec)

    abl = rows("verification_gate_ablation.csv")
    for split in ("design", "held_out", "held_out_2"):
        sub = [r for r in abl if r["split"] == split]
        base = [r["without_none"] == "1" for r in sub]
        for col in [k for k in (sub[0] if sub else {}) if k.startswith("without_") and k != "without_none"]:
            acc = [r[col] == "1" for r in sub]
            d = describe(sub, lambda r, c=col: r[c] == "1")
            correct_full = [a == (r["oracle_satisfied"] == "1") for a, r in zip(base, sub)]
            correct_abl = [a == (r["oracle_satisfied"] == "1") for a, r in zip(acc, sub)]
            b, c = paired_discordance(correct_full, correct_abl)
            out.append({"split": split, "subset": "all", "rule": f"ablation_{col}", **d,
                        "full_better": b, "ablated_better": c, "p_vs_full": mcnemar_exact(b, c)})

    keys = list(dict.fromkeys(k for r in out for k in r))
    with open(RES / "gate_stats.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    for r in out:
        if r["subset"] == "all":
            extra = {k: (f"{v:.2g}" if isinstance(v, float) else v) for k, v in r.items()
                     if k.startswith(("p_", "fixed", "broken", "pre_", "full_better", "ablated_better"))}
            print(f"{r['split']:10s} {r['rule']:24s} withheld {r['withheld_rate']:38s} FCR {r['FCR']:38s} FRR {r['FRR']:36s} {extra}")


if __name__ == "__main__":
    main()
