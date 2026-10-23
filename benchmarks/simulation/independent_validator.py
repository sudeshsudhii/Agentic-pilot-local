"""Independent validator for heldout simulation results (Agent 4).
Written from scratch; does not import the authors' simulate.py or stats.py."""
import csv, json, math, sys
from math import comb

BASE = "/home/user/Agentic-pilot-local/benchmarks/simulation/out/heldout/"
OUT = "/tmp/claude-0/-home-user-Agentic-pilot-local/9002c3ac-134c-52d7-af0a-ddf50aa21ff5/scratchpad/validation_report.md"
CONFIGS = ["no_verification", "basic_detection", "evidence_gated", "enhanced_validation",
           "abl_no_evidence_collection", "abl_no_evidence_validation", "abl_no_memory",
           "abl_no_recovery", "mem_filtered"]
REF = "evidence_gated"
Z = 1.959964
TOL = 1e-3


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def wilson(k, n):
    if n == 0:
        return (None, None)
    p = k / n
    den = 1 + Z * Z / n
    centre = (p + Z * Z / (2 * n)) / den
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def div(a, b):
    return a / b if b else None


def confusion(rows, c):
    tp = fp = fn = tn = 0
    for r in rows:
        rep, y = int(r[c + "_reported"]), int(r[c + "_y"])
        if rep == 1 and y == 1: tp += 1
        elif rep == 1 and y == 0: fp += 1
        elif rep == 0 and y == 1: fn += 1
        else: tn += 1
    n = len(rows)
    prec = div(tp, tp + fp)
    rec = div(tp, tp + fn)
    f1 = (2 * prec * rec / (prec + rec)) if (prec is not None and rec is not None and prec + rec) else None
    return dict(N=n, TP=tp, FP=fp, FN=fn, TN=tn,
                TSR=div(tp, n), FCR=div(fp, tp + fp), FRR=div(fn, tp + fn),
                precision=prec, recall=rec, F1=f1, accuracy=div(tp + tn, n),
                TSR_ci=wilson(tp, n), FCR_ci=wilson(fp, tp + fp), FRR_ci=wilson(fn, tp + fn))


def mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    s = sum(comb(n, i) for i in range(k + 1))
    return min(1.0, 2 * s / 2 ** n)


def paired(rows, other):
    cr_only = co_only = fo_only = fr_only = 0
    fp_diff_sum = 0
    for r in rows:
        rr, ry = int(r[REF + "_reported"]), int(r[REF + "_y"])
        orp, oy = int(r[other + "_reported"]), int(r[other + "_y"])
        c_ref, c_oth = rr == ry, orp == oy
        f_ref, f_oth = int(rr == 1 and ry == 0), int(orp == 1 and oy == 0)
        if c_ref and not c_oth: cr_only += 1
        if c_oth and not c_ref: co_only += 1
        if f_oth and not f_ref: fo_only += 1
        if f_ref and not f_oth: fr_only += 1
        fp_diff_sum += f_oth - f_ref
    return dict(correct_ref_only=cr_only, correct_other_only=co_only,
                mcnemar_p_correct=mcnemar_exact(cr_only, co_only),
                fp_other_only=fo_only, fp_ref_only=fr_only,
                mcnemar_p_fp=mcnemar_exact(fo_only, fr_only),
                fp_rate_diff=fp_diff_sum / len(rows))


def recovery(rows):
    out = {}
    cfgs = []
    for r in rows:
        if r["config"] not in cfgs:
            cfgs.append(r["config"])
    for c in cfgs:
        rs = [r for r in rows if r["config"] == c]
        tr = [r for r in rs if int(r["permanent"]) == 0]
        perm = [r for r in rs if int(r["permanent"]) == 1]
        rec = sum(int(r["recovered"]) for r in tr)
        det = sum(int(r["detected"]) for r in rs)
        out[c] = dict(recovery_success=[rec, len(tr)], recovery_success_rate=div(rec, len(tr)),
                      failure_detection=[det, len(rs)], failure_detection_rate=div(det, len(rs)),
                      false_completions=sum(int(r["false_completion"]) for r in rs),
                      unnecessary_attempts=sum(int(r["attempts"]) for r in perm),
                      mean_cost_s=sum(float(r["cost_s"]) for r in rs) / len(rs),
                      n_rows=len(rs), n_perm=len(perm))
    return out


def cmp(label, mine, theirs, discrepancies):
    """Compare scalar or 2-list values, record discrepancy if any."""
    if isinstance(mine, (list, tuple)):
        if not isinstance(theirs, (list, tuple)) or len(theirs) != len(mine):
            discrepancies.append((label, mine, theirs)); return
        for i, (a, b) in enumerate(zip(mine, theirs)):
            cmp(f"{label}[{i}]", a, b, discrepancies)
        return
    if mine is None or theirs is None:
        if not (mine is None and theirs is None):
            discrepancies.append((label, mine, theirs))
        return
    if abs(float(mine) - float(theirs)) > TOL:
        discrepancies.append((label, mine, theirs))


def f(x, nd=4):
    if x is None: return "n/a"
    if isinstance(x, int): return str(x)
    return f"{x:.{nd}f}"


def ci(t):
    return "n/a" if t[0] is None else f"[{t[0]:.3f}, {t[1]:.3f}]"


def main():
    sc = load(BASE + "scenarios.csv")
    rc = load(BASE + "recovery_scenarios.csv")
    res = json.load(open(BASE + "results.json"))
    disc, sanity = [], []

    # sanity checks
    ids = [r["id"] for r in sc]
    sanity.append(f"Scenario rows: {len(sc)}; unique ids: {len(set(ids))}")
    for c in CONFIGS:
        for col in (c + "_reported", c + "_y"):
            vals = {r[col] for r in sc}
            if not vals <= {"0", "1"}:
                sanity.append(f"FAIL non-binary values in {col}: {vals}")
    conf = {c: confusion(sc, c) for c in CONFIGS}
    for c in CONFIGS:
        m = conf[c]
        s = m["TP"] + m["FP"] + m["FN"] + m["TN"]
        sanity.append(f"{'OK' if s == 100 else 'FAIL'}: {c} TP+FP+FN+TN = {s}")

    def same(a, b):
        diffs = [r["id"] for r in sc if r[a + "_reported"] != r[b + "_reported"] or r[a + "_y"] != r[b + "_y"]]
        return diffs
    for a, b in [("abl_no_evidence_validation", "no_verification"), ("abl_no_evidence_collection", "evidence_gated")]:
        d = same(a, b)
        sanity.append(f"{'OK' if not d else 'FAIL'}: {a} vs {b} per-scenario identical "
                      f"(reported and y): {len(d)} differing rows" + (f" {d[:10]}" if d else ""))
    # y consistency with y_base (informational)
    for c in CONFIGS:
        nd = sum(1 for r in sc if r[c + "_y"] != r["y_base"])
        if nd:
            sanity.append(f"INFO: {c}_y differs from y_base in {nd} scenarios")
    sanity.append(f"INFO: repeated==1 count: {sum(int(r['repeated']) for r in sc)}")

    # compare configs
    for c in CONFIGS:
        theirs = res["configs"].get(c)
        if theirs is None:
            disc.append((f"configs.{c}", "present", "missing")); continue
        for k in ["N", "TP", "FP", "FN", "TN", "TSR", "FCR", "FRR", "precision", "recall", "F1", "accuracy"]:
            cmp(f"configs.{c}.{k}", conf[c][k], theirs.get(k), disc)
        for k in ["TSR_ci", "FCR_ci", "FRR_ci"]:
            if k in theirs:
                cmp(f"configs.{c}.{k}", list(conf[c][k]), theirs[k], disc)

    pt = {c: paired(sc, c) for c in CONFIGS if c != REF}
    for c, m in pt.items():
        theirs = res["paired_tests_vs_evidence_gated"].get(c)
        if theirs is None:
            disc.append((f"paired.{c}", "present", "missing")); continue
        for k, v in m.items():
            cmp(f"paired_tests_vs_evidence_gated.{c}.{k}", v, theirs.get(k), disc)

    rep = [r for r in sc if int(r["repeated"]) == 1]
    mem = {c: confusion(rep, c) for c in ["abl_no_memory", REF, "mem_filtered"]}
    for c, m in mem.items():
        theirs = res["memory"].get(c)
        if theirs is None:
            disc.append((f"memory.{c}", "present", "missing")); continue
        for k in ["N", "TP", "FP", "FN", "TN", "TSR", "FCR", "FRR", "precision", "recall", "F1", "accuracy"]:
            cmp(f"memory.{c}.{k}", m[k], theirs.get(k), disc)

    rv = recovery(rc)
    for c, m in rv.items():
        theirs = res["recovery"].get(c)
        if theirs is None:
            disc.append((f"recovery.{c}", "present", "missing")); continue
        for k in ["recovery_success", "failure_detection", "false_completions", "unnecessary_attempts", "mean_cost_s"]:
            cmp(f"recovery.{c}.{k}", m[k], theirs.get(k), disc)
    for c in res["recovery"]:
        if c not in rv:
            disc.append((f"recovery.{c}", "missing in CSV", "present"))

    # ---------------- report ----------------
    L = []
    L.append("# Independent validation report: heldout simulation (Agent 4)\n")
    L.append("Inputs: `benchmarks/simulation/out/heldout/{scenarios.csv, recovery_scenarios.csv, results.json}`. "
             "All values recomputed from the CSVs with independent code "
             f"(`{__file__}`); the authors' simulate.py / stats.py were not read or imported. "
             f"Wilson 95% intervals use z = {Z}. Comparison tolerance = {TOL}.\n")
    L.append("## Sanity checks\n")
    L += [f"- {s}" for s in sanity]
    L.append("")
    L.append("## 1. Per-configuration metrics (N = 100)\n")
    L.append("| Config | TP | FP | FN | TN | TSR [95% CI] | FCR [95% CI] | FRR [95% CI] | Precision | Recall | F1 | Accuracy |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in CONFIGS:
        m = conf[c]
        L.append(f"| {c} | {m['TP']} | {m['FP']} | {m['FN']} | {m['TN']} | {f(m['TSR'],3)} {ci(m['TSR_ci'])} | "
                 f"{f(m['FCR'],3)} {ci(m['FCR_ci'])} | {f(m['FRR'],3)} {ci(m['FRR_ci'])} | {f(m['precision'],3)} | "
                 f"{f(m['recall'],3)} | {f(m['F1'],3)} | {f(m['accuracy'],3)} |")
    L.append("")
    L.append("## 2. Paired tests vs evidence_gated (exact two-sided McNemar)\n")
    L.append("Correct test: ref_only = evidence_gated correct and other wrong; other_only = the reverse. "
             "FP test: other_only = other has a false completion and evidence_gated does not. "
             "Risk difference = mean(FP_other - FP_ref).\n")
    L.append("| Config | correct ref_only | correct other_only | p (correct) | FP other_only | FP ref_only | p (FP) | FP risk diff |")
    L.append("|---|---|---|---|---|---|---|---|")
    for c, m in pt.items():
        L.append(f"| {c} | {m['correct_ref_only']} | {m['correct_other_only']} | {f(m['mcnemar_p_correct'],6)} | "
                 f"{m['fp_other_only']} | {m['fp_ref_only']} | {f(m['mcnemar_p_fp'],6)} | {m['fp_rate_diff']:+.2f} |")
    L.append("")
    L.append(f"## 3. Memory subset (repeated == 1, N = {len(rep)})\n")
    L.append("| Config | TP | FP | FN | TN | TSR [95% CI] | FCR [95% CI] | FRR [95% CI] | Precision | Recall | F1 | Accuracy |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c, m in mem.items():
        L.append(f"| {c} | {m['TP']} | {m['FP']} | {m['FN']} | {m['TN']} | {f(m['TSR'],3)} {ci(m['TSR_ci'])} | "
                 f"{f(m['FCR'],3)} {ci(m['FCR_ci'])} | {f(m['FRR'],3)} {ci(m['FRR_ci'])} | {f(m['precision'],3)} | "
                 f"{f(m['recall'],3)} | {f(m['F1'],3)} | {f(m['accuracy'],3)} |")
    L.append("")
    L.append("## 4. Recovery\n")
    L.append("| Config | rows | Recovery success (transient) | Failure detection | False completions | Unnecessary attempts (permanent) | Mean cost (s) |")
    L.append("|---|---|---|---|---|---|---|")
    for c, m in rv.items():
        rs, fd = m["recovery_success"], m["failure_detection"]
        L.append(f"| {c} | {m['n_rows']} ({m['n_perm']} permanent) | {rs[0]}/{rs[1]} = {f(m['recovery_success_rate'],3)} | "
                 f"{fd[0]}/{fd[1]} = {f(m['failure_detection_rate'],3)} | {m['false_completions']} | "
                 f"{m['unnecessary_attempts']} | {m['mean_cost_s']:.4f} |")
    L.append("")
    L.append("## 5. Discrepancies vs results.json (tolerance 0.001)\n")
    if disc:
        L.append(f"**{len(disc)} discrepancies found:**\n")
        L.append("| Field | Recomputed | results.json |")
        L.append("|---|---|---|")
        for lab, a, b in disc:
            L.append(f"| {lab} | {a} | {b} |")
    else:
        n_checked = "all"
        L.append("**None.** Every compared field in `configs` (N, TP, FP, FN, TN, TSR, FCR, FRR, precision, recall, F1, "
                 "accuracy), `paired_tests_vs_evidence_gated` (correct_ref_only, correct_other_only, mcnemar_p_correct, "
                 "fp_other_only, fp_ref_only, mcnemar_p_fp, fp_rate_diff), `memory` (same confusion metrics) and "
                 "`recovery` (recovery_success, failure_detection, false_completions, unnecessary_attempts, mean_cost_s) "
                 "matches the independent recomputation within 0.001.")
    L.append("")
    open(OUT, "w").write("\n".join(L))
    print("\n".join(L))
    print(f"\nDISCREPANCIES: {len(disc)}")


if __name__ == "__main__":
    main()
