"""Independent recomputation of v2 simulation numbers from CSVs (no project imports)."""
import csv, json, sys
from math import comb
from fractions import Fraction
D = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/benchmarks/simulation/out/heldout_v2/"
rows = list(csv.DictReader(open(D + "scenarios.csv")))
res = json.load(open(D + "results.json"))
cfgs = sorted({k[:-len("_reported")] for k in rows[0] if k.endswith("_reported")}, key=lambda c: list(rows[0]).index(c + "_reported"))
def mc(b, c):
    n = b + c
    if n == 0: return 1.0
    return min(1.0, 2 * sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n)
I = lambda r, k: int(r[k]) if r[k] != "" else None
out = {"policy": {}, "decision": {}, "paired": {}}
print("N =", len(rows))
for c in cfgs:
    tp = sum(1 for r in rows if I(r, c+"_reported") == 1 and I(r, c+"_y") == 1)
    fp = sum(1 for r in rows if I(r, c+"_reported") == 1 and I(r, c+"_y") == 0)
    fn = sum(1 for r in rows if I(r, c+"_reported") == 0 and I(r, c+"_y") == 1)
    tn = sum(1 for r in rows if I(r, c+"_reported") == 0 and I(r, c+"_y") == 0)
    n = len(rows)
    m = dict(TP=tp, FP=fp, FN=fn, TN=tn, TSR=tp/n, FCR=fp/(tp+fp), FRR=fn/(tp+fn))
    out["policy"][c] = m
    j = res["policy"][c]
    ok = all(abs(j[k]-m[k]) < 1e-12 for k in m)
    print(f"{c:28s} TP{tp:3d} FP{fp:3d} FN{fn:3d} TN{tn:3d} TSR {m['TSR']:.3f} FCR {m['FCR']:.4f} FRR {m['FRR']:.4f} match_json={ok}")
claimed = [i for i, r in enumerate(rows) if I(r, "evidence_gated_claimed") == 1]
print("claims", len(claimed), "true claims", sum(I(rows[i], "evidence_gated_y_claim") for i in claimed))
V = ["no_verification", "basic_detection", "evidence_gated", "enhanced_validation"]
for c in V:
    assert [i for i, r in enumerate(rows) if I(r, c+"_claimed") == 1] == claimed
    acc = [I(rows[i], c+"_accepted") for i in claimed]; yc = [I(rows[i], c+"_y_claim") for i in claimed]
    tp = sum(a == 1 and y == 1 for a, y in zip(acc, yc)); fp = sum(a == 1 and y == 0 for a, y in zip(acc, yc))
    fn = sum(a == 0 and y == 1 for a, y in zip(acc, yc)); tn = sum(a == 0 and y == 0 for a, y in zip(acc, yc))
    m = dict(TP=tp, FP=fp, FN=fn, TN=tn, accuracy=(tp+tn)/len(claimed), FCR=fp/(tp+fp), FRR=fn/(tp+fn))
    out["decision"][c] = m
    j = res["decision"][c]; ok = all(abs(j[k]-m[k]) < 1e-12 for k in m)
    print(f"DEC {c:22s} TP{tp} FP{fp} FN{fn} TN{tn} acc {m['accepted' if False else 'accuracy']:.4f} FCR {m['FCR']:.4f} FRR {m['FRR']:.4f} match={ok}")
ref = "evidence_gated"
def disc(a, b): return sum(x and not y for x, y in zip(a, b)), sum(y and not x for x, y in zip(a, b))
for c in cfgs:
    if c == ref: continue
    fo = [I(r, c+"_reported") == 1 and I(r, c+"_y") == 0 for r in rows]; fr = [I(r, ref+"_reported") == 1 and I(r, ref+"_y") == 0 for r in rows]
    so = [I(r, c+"_reported") == 1 and I(r, c+"_y") == 1 for r in rows]; sr = [I(r, ref+"_reported") == 1 and I(r, ref+"_y") == 1 for r in rows]
    b1, c1 = disc(fo, fr); b2, c2 = disc(so, sr)
    d = dict(fc_other_only=b1, fc_phi_only=c1, fc_p=mc(b1, c1), success_other_only=b2, success_phi_only=c2, success_p=mc(b2, c2))
    if c in V:
        do = [I(rows[i], c+"_accepted") == I(rows[i], c+"_y_claim") for i in claimed]
        dr = [I(rows[i], ref+"_accepted") == I(rows[i], ref+"_y_claim") for i in claimed]
        b3, c3 = disc(do, dr); d.update(decision_other_only=b3, decision_phi_only=c3, decision_p=mc(b3, c3))
    j = res["paired_vs_evidence_gated"][c]; ok = all(abs(j[k]-d[k]) < 1e-12 for k in d)
    out["paired"][c] = d
    print(f"PAIR {c:26s} {d} match={ok}")
# recovery
rr = list(csv.DictReader(open(D + "recovery_scenarios.csv")))
for cfg in ("no_recovery", "retry_based", "evidence_guided"):
    R = [r for r in rr if r["config"] == cfg]; rec = [r for r in R if r["permanent"] == "0"]
    rs = (sum(int(r["recovered"]) for r in rec), len(rec)); fd = (sum(int(r["detected"]) for r in R), len(R))
    fc = sum(int(r["false_completion"]) for r in R); un = sum(int(r["attempts"]) for r in R if r["permanent"] == "1")
    ma = sum(int(r["attempts"]) for r in R) / len(R)
    ae = [r for r in R if r["mode"] != "missing_confirmation"]
    sh_ae = sum(int(r["recovered"]) for r in ae) / len(ae); sh_all = sum(int(r["recovered"]) for r in R) / len(R)
    modes = {}
    for r in rec: modes.setdefault(r["mode"], [0, 0]); modes[r["mode"]][0] += int(r["recovered"]); modes[r["mode"]][1] += 1
    j = res["recovery"][cfg]
    ok = (list(j["recovery_success"]) == list(rs) and list(j["failure_detection"]) == list(fd) and j["false_completions"] == fc
          and j["unnecessary_attempts"] == un and abs(j["mean_attempts"]-ma) < 1e-12 and abs(j["recovered_share_action_errors"]-sh_ae) < 1e-12
          and all(list(j["by_mode"][k]) == v for k, v in modes.items()))
    print(f"REC {cfg:16s} success {rs} detect {fd} FC {fc} unnecessary {un} mean_att {ma:.3f} share_all {sh_all:.4f} share_ae {sh_ae:.3f} modes {modes} match={ok}")
# guided vs retry paired recovery
g = {r["id"]: int(r["recovered"]) for r in rr if r["config"] == "evidence_guided" and r["permanent"] == "0"}
t = {r["id"]: int(r["recovered"]) for r in rr if r["config"] == "retry_based" and r["permanent"] == "0"}
b = sum(g[k] and not t[k] for k in g); c = sum(t[k] and not g[k] for k in g)
print("guided-vs-retry discordant", b, c, mc(b, c), "json", res["recovery_paired_guided_vs_retry"])
# over all rows incl permanent
g = {r["id"]: int(r["recovered"]) for r in rr if r["config"] == "evidence_guided"}
t = {r["id"]: int(r["recovered"]) for r in rr if r["config"] == "retry_based"}
b = sum(g[k] and not t[k] for k in g); c = sum(t[k] and not g[k] for k in g); print("all rows", b, c, mc(b, c))
# memory subset (repeated)
rep = [r for r in rows if r["repeated"] == "1"]
for c in ("abl_no_memory", "evidence_gated", "mem_filtered"):
    tp = sum(1 for r in rep if I(r, c+"_reported") == 1 and I(r, c+"_y") == 1); fp = sum(1 for r in rep if I(r, c+"_reported") == 1 and I(r, c+"_y") == 0)
    fn = sum(1 for r in rep if I(r, c+"_reported") == 0 and I(r, c+"_y") == 1); tn = len(rep) - tp - fp - fn
    j = res["memory"][c]
    print(f"MEM {c} N{len(rep)} TP{tp} FP{fp} FN{fn} TN{tn} TSR {tp/len(rep):.4f} FCR {fp/(tp+fp):.4f} match={(j['TP'],j['FP'],j['FN'],j['TN'],j['N'])==(tp,fp,fn,tn,len(rep))}")
json.dump(out, open(sys.argv[0].replace(".py", ".json"), "w"), indent=1)
