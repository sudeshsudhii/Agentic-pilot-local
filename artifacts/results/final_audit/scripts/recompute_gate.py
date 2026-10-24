"""Independent recomputation of gate-study numbers (no project imports)."""
import csv, math
from math import comb
R = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/artifacts/results/"
def mc(b, c):
    n = b + c
    return 1.0 if n == 0 else min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
def wil(k, n, z=1.959963984540054):
    if n == 0: return (float('nan'),)*2
    p = k/n; d = 1+z*z/n; c = (p+z*z/(2*n))/d; h = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d; return c-h, c+h
def summarize(rows, label, col="gate_reports_complete"):
    neg = [r for r in rows if r["oracle_satisfied"] == "0"]; pos = [r for r in rows if r["oracle_satisfied"] == "1"]
    W = sum(r[col] == "0" for r in neg); FR = sum(r[col] == "0" for r in pos)
    rep = [r for r in rows if r[col] == "1"]; FC = sum(r["oracle_satisfied"] == "0" for r in rep)
    # paired decision correctness vs dispatch-only (always reports complete)
    gate_only = W  # unsatisfied withheld: gate correct, dispatch wrong
    disp_only = FR  # satisfied rejected: dispatch correct, gate wrong
    lw, hw = wil(W, len(neg)); lf, hf = wil(FR, len(pos))
    print(f"{label:24s} n={len(rows):3d} n-/n+={len(neg)}/{len(pos)} W={W}/{len(neg)} [{lw:.2f},{hw:.2f}] FR={FR}/{len(pos)} [{lf:.2f},{hf:.2f}] FC/R={FC}/{len(rep)} "
          f"acc={(W + len(pos) - FR)}/{len(rows)}  McNemar(correct) b/c={gate_only}/{disp_only} p={mc(gate_only, disp_only):.6f}  p(FC vs dispatch)={mc(0, W):.3g}")
    return dict(W=W, FR=FR, FC=FC, R=len(rep))
after = list(csv.DictReader(open(R + "verification_gate_cases.csv")))
before = list(csv.DictReader(open(R + "verification_gate_cases_before_fixes.csv")))
for name, rows in (("after", after), ("before", before)):
    for sp in ("design", "held_out", "held_out_2"):
        sub = [r for r in rows if r["split"] == sp]
        if sub: summarize(sub, f"{sp} {name}")
    if name == "after":
        summarize([r for r in rows if r["split"] in ("held_out", "held_out_2")], "held_out1+2 after")
        summarize(rows, "all 92 after")
        summarize([r for r in rows if r["split"] in ("held_out", "held_out_2")], "held_out1+2 live_verbose", "live_verbose_reports_complete")
        summarize([r for r in rows if r["split"] in ("held_out", "held_out_2")], "held_out1+2 live_empty", "live_empty_reports_complete")
print("--- per category (after)")
for sp in ("design", "held_out_2", "held_out"):
    for cat in ("search", "navigation", "captcha", "text_entry", "extraction", "multi_step"):
        sub = [r for r in after if r["split"] == sp and r["category"] == cat]
        neg = [r for r in sub if r["oracle_satisfied"] == "0"]; pos = [r for r in sub if r["oracle_satisfied"] == "1"]
        print(sp, cat, f"{len(neg)}/{len(pos)}", "W", sum(r["gate_reports_complete"] == "0" for r in neg), "FR", sum(r["gate_reports_complete"] == "0" for r in pos))
# paired before vs after on shared states
b = {r["case"]: r for r in before}
for sp in ("design", "held_out"):
    fixed = broken = 0
    for r in after:
        if r["split"] != sp or r["case"] not in b: continue
        ca = (r["gate_reports_complete"] == "1") == (r["oracle_satisfied"] == "1")
        cb = (b[r["case"]]["gate_reports_complete"] == "1") == (b[r["case"]]["oracle_satisfied"] == "1")
        fixed += ca and not cb; broken += cb and not ca
    print(sp, "before->after fixed", fixed, "broken", broken, "p", mc(fixed, broken))
# oracle unchanged between files?
diff = [r["case"] for r in after if r["case"] in b and b[r["case"]]["oracle_satisfied"] != r["oracle_satisfied"]]
print("oracle label differences before/after:", diff)
# latency
lat = sorted(float(r["gate_ms_median"]) for r in after if r["gate_ms_median"])
print("gate latency n", len(lat), "median", sorted(lat)[len(lat)//2] if len(lat)%2 else (lat[len(lat)//2-1]+lat[len(lat)//2])/2, "p95(rank round(.95(n-1))+1)", lat[round(0.95*(len(lat)-1))])
# ablation
ab = list(csv.DictReader(open(R + "verification_gate_ablation.csv")))
print("ablation cols", list(ab[0].keys()))
for sp in ("design", "held_out", "held_out_2"):
    sub = [r for r in ab if r["split"] == sp]
    for k in [c for c in ab[0] if c.startswith("without")]:
        neg = [r for r in sub if r["oracle_satisfied"] == "0"]; pos = [r for r in sub if r["oracle_satisfied"] == "1"]
        W = sum(r[k] == "0" for r in neg); FR = sum(r[k] == "0" for r in pos)
        fb = sum(((r["without_none"] == "1") == (r["oracle_satisfied"] == "1")) and not ((r[k] == "1") == (r["oracle_satisfied"] == "1")) for r in sub)
        ab_ = sum(not ((r["without_none"] == "1") == (r["oracle_satisfied"] == "1")) and ((r[k] == "1") == (r["oracle_satisfied"] == "1")) for r in sub)
        print(f"  {sp:10s} {k:12s} W {W}/{len(neg)} FR {FR}/{len(pos)} full_better {fb} ablated_better {ab_} p {mc(fb, ab_):.4g}")
