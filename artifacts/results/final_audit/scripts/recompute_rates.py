import csv
R = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/"
m1 = list(csv.DictReader(open(R + "benchmarks/simulation/inputs/m1_gate_rules.csv")))
cases = {r["case"]: r for r in csv.DictReader(open(R + "artifacts/results/verification_gate_cases.csv"))}
# consistency of m1 phi_accepts with measured gate decisions
mism = [r["case"] for r in m1 if r["phi_accepts"] != cases[r["case"]]["gate_reports_complete"] or r["oracle"] != cases[r["case"]]["oracle_satisfied"]]
print("m1 vs cases mismatches:", mism, "n", len(m1))
ho = [r for r in m1 if r["split"] in ("held_out", "held_out_2")]
cmap = {"navigation": ["navigation"], "search": ["search"], "form": ["text_entry", "multi_step"], "data_entry": ["text_entry"], "extraction": ["extraction"], "multi_step": ["multi_step"]}
for rule in ("basic_accepts", "phi_accepts"):
    for c, g in cmap.items():
        neg = [r for r in ho if r["category"] in g and r["oracle"] == "0"]
        k = sum(r[rule] == "0" for r in neg)
        print(rule, c, f"{k}/{len(neg)} -> {(k + .5) / (len(neg) + 1):.3f}")
    pos = [r for r in ho if r["oracle"] == "1" and r["category"] != "captcha"]
    k = sum(r[rule] == "0" for r in pos); print(rule, "FR", f"{k}/{len(pos)} -> {(k + .5) / (len(pos) + 1):.3f}")
mem = list(csv.DictReader(open(R + "benchmarks/simulation/inputs/m4_memory.csv"))); print(mem[0].keys()); [print(x) for x in mem]
