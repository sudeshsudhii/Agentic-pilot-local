"""Write the paper's simulation tables and the evidence ledger from out/heldout/results.json.

Every table produced here is SYNTHETIC unless a cell says ACTUAL. Usage: python -m benchmarks.simulation.make_tables
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

from benchmarks.e2e.stats import wilson

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
R = json.loads((HERE / "out" / "heldout" / "results.json").read_text())
P = json.loads((HERE / "params.json").read_text())
TAB = ROOT / "paper" / "tables" / "sim"
TAB.mkdir(parents=True, exist_ok=True)
LEDGER: list[dict] = []


def ci(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} [{lo:.2f},{hi:.2f}]"


def f3(x: float) -> str:
    return f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.2f}"


def led(claim: str, value, source: str, cls: str, where: str) -> None:
    LEDGER.append({"claim": claim, "value": value, "source": source, "classification": cls, "location": where})


def table(name: str, caption: str, label: str, spec: str, header: list[str], rows: list[list[str]], size: str = "\\footnotesize",
          sep: str = "2pt", note: str = "", wide: bool = False) -> None:
    env = "table*" if wide else "table"
    lines = [f"\\begin{{{env}}}[t]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}", size,
             f"\\setlength{{\\tabcolsep}}{{{sep}}}", f"\\begin{{tabular}}{{@{{}}{spec}@{{}}}}", "\\toprule"]
    if any(h.strip() for h in header):
        lines += [" & ".join(header) + " \\\\", "\\midrule"]
    for r in rows:
        lines.append("\\midrule" if r == ["MIDRULE"] else " & ".join(r) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    if note:
        lines += ["", "\\vspace{2pt}\\raggedright\\scriptsize " + note]
    lines += [f"\\end{{{env}}}", ""]
    (TAB / f"{name}.tex").write_text("\n".join(lines))


C = R["configs"]
MC = R["monte_carlo"]
T = R["paired_tests_vs_evidence_gated"]
NAMES = {"no_verification": "No verification", "basic_detection": "Basic success detection",
         "evidence_gated": "Evidence-gated ($\\Phi$)", "enhanced_validation": "Enhanced validation$^{\\ddagger}$"}
SIM = "\\textsc{Simulation-based (synthetic)}"

# ---- Table: baseline comparison (Study A/B)
rows = []
for c, nm in NAMES.items():
    m = C[c]
    rows.append([nm, str(m["TP"]), str(m["FP"]), str(m["FN"]), str(m["TN"]),
                 ci(m["TP"], m["N"]), ci(m["FP"], m["TP"] + m["FP"]), ci(m["FN"], m["TP"] + m["FN"]),
                 f3(m["F1"]), f3(m["accuracy"])])
    for k in ("TP", "FP", "FN", "TN"):
        led(f"{c} {k}", m[k], "out/heldout/results.json configs", "SYNTHETIC", "Table sim-baseline")
    led(f"{c} FCR", round(m["FCR"], 4), "FP/(TP+FP)", "SYNTHETIC", "Table sim-baseline")
    led(f"{c} FRR", round(m["FRR"], 4), "FN/(TP+FN)", "SYNTHETIC", "Table sim-baseline")
table("baseline", f"{SIM} Study~B: completion decisions of four configurations on the same 100 held-out synthetic scenarios. Confusion counts and rates with Wilson 95\\% intervals. $^{{\\ddagger}}$Not implemented (proposed).",
      "tab:sim-baseline", "lccccccccc", ["Configuration", "TP", "FP", "FN", "TN", "TSR", "FCR", "FRR", "F1", "Acc."], rows,
      size="\\footnotesize", sep="5pt", wide=True)

# ---- Table: paired tests and Monte Carlo
rows = []
for c, nm in NAMES.items():
    mc = MC[c]["FCR"]
    if c == "evidence_gated":
        rows.append([nm, "ref.", "ref.", "ref.", "--", f"{mc['mean']:.2f} [{mc['p2.5']:.2f},{mc['p97.5']:.2f}]"])
        continue
    t = T[c]
    rows.append([nm, f"{t['fp_other_only']}/{t['fp_ref_only']}", f"{t['mcnemar_p_fp']:.3f}",
                 f"{t['fp_rate_diff']:+.2f} [{t['fp_rate_diff_ci'][0]:+.2f},{t['fp_rate_diff_ci'][1]:+.2f}]",
                 f"{t['cohens_h_tsr']:+.2f}", f"{mc['mean']:.2f} [{mc['p2.5']:.2f},{mc['p97.5']:.2f}]"])
    led(f"{c} McNemar p (false completion vs evidence_gated)", round(t["mcnemar_p_fp"], 4), "exact McNemar on paired FP indicators", "SYNTHETIC", "Table sim-tests")
table("tests", f"{SIM} Paired comparison with the evidence-gated configuration on the same scenarios. $b/c$: scenarios with a false completion only in the other configuration / only under $\\Phi$; $p$: exact McNemar test; $\\Delta$FC: difference in false completions per scenario (other minus $\\Phi$) with scenario-level bootstrap 95\\% interval; $h$: Cohen's $h$ for TSR ($\\Phi$ minus other). MC: mean FCR and 2.5--97.5th percentiles over {P['monte_carlo_replications']} regenerated scenario sets.",
      "tab:sim-tests", "lccccc", ["Configuration", "$b/c$", "$p$", "$\\Delta$FC", "$h$", "MC FCR"], rows, size="\\scriptsize", sep="2pt")

# ---- Table: ablation (Study C)
AB = {"evidence_gated": "Full", "abl_no_evidence_collection": "-- evid.\\ collection",
      "abl_no_evidence_validation": "-- $\\Phi$", "abl_no_memory": "-- memory, RAG", "abl_no_recovery": "-- recovery"}
rows = []
for c, nm in AB.items():
    m = C[c]
    mc = MC[c]
    rows.append([nm, ci(m["TP"], m["N"]), f3(m["FCR"]), f3(m["FRR"]), f3(m["F1"]), f"{m['evidence_available']:.2f}",
                 f"{mc['TSR']['mean']:.2f}", f"{mc['FCR']['mean']:.2f}"])
    led(f"{c} TSR", m["TSR"], "TP/N", "SYNTHETIC", "Table sim-ablation")
table("ablation", f"{SIM} Study~C: ablation of the full architecture on the same 100 scenarios. Evid.: share of episodes with audit evidence stored. MC: means over {P['monte_carlo_replications']} regenerated sets. Disabling evidence collection leaves decisions unchanged because $\\Phi$ reads the live page, not the stored evidence (code behaviour).",
      "tab:sim-ablation", "lccccccc", ["Configuration", "TSR", "FCR", "FRR", "F1", "Evid.", "MC TSR", "MC FCR"], rows, size="\\scriptsize", sep="2pt")

# ---- Table: memory (Study D) — ACTUAL retrieval on synthetic corpus + SYNTHETIC repeated workflows
mem = list(csv.DictReader(open(HERE / "inputs" / "m4_memory.csv")))
with_rel = [m for m in mem if m["n_relevant"] not in ("", "0")]
p3 = sum(int(m["relevant_in_top_k"]) for m in with_rel) / (3 * len(with_rel))
r3 = statistics.mean(float(m["recall_at_k"]) for m in with_rel)
mrr = statistics.mean(float(m["reciprocal_rank"]) for m in with_rel)
mis = R["derived_inputs"]["memory_misleading"]
led("retrieval precision@3", round(p3, 3), "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
led("retrieval recall@3", round(r3, 3), "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
led("retrieval MRR", round(mrr, 3), "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
led("queries with misleading top-1", f"{mis['k']}/{mis['n']}", "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
M = R["memory"]
rows = [["\\multicolumn{5}{@{}l}{\\emph{ACTUAL retrieval, real store, 23 synthetic records; 9 queries with a relevant record}}"],
        ["Precision@3 / Recall@3 / MRR", f"{p3:.2f}", f"{r3:.2f}", f"{mrr:.2f}", ""],
        ["Top-1 irrelevant or failed (all 10 queries)", f"{mis['k']}/{mis['n']}", "", "", ""],
        ["MIDRULE"],
        ["\\multicolumn{5}{@{}l}{\\emph{SYNTHETIC repeated workflows (n=" + str(M['evidence_gated']['N']) + ")}}"],
        ["Configuration", "TSR", "FCR", "Ctx.\\ acc.", ""]]
for c, nm in (("abl_no_memory", "Memory disabled"), ("evidence_gated", "Memory enabled"), ("mem_filtered", "Relevance-filtered$^{\\ddagger}$")):
    m = M[c]
    rows.append([nm, ci(m["TP"], m["N"]), f3(m["FCR"]), "--" if m["contextual_accuracy"] is None else f"{m['contextual_accuracy']:.2f}", ""])
table("memory", f"Study~D, memory and retrieval. Upper block ACTUAL (real store, synthetic records); lower block {SIM}. Ctx.\\ acc.: share of repeated workflows whose retrieved context is not misleading. $^{{\\ddagger}}$Not implemented.",
      "tab:sim-memory", "lcccc", ["", "", "", "", ""], rows, size="\\scriptsize", sep="3pt")

# ---- Table: recovery (Study E)
REC = R["recovery"]
REC_ROWS = [r for r in csv.DictReader(open(HERE / "out" / "heldout" / "recovery_scenarios.csv")) if r["config"] == "retry_based"]
rows = []
for c, nm in (("no_recovery", "No recovery"), ("retry_based", "Retry-based (implemented)"), ("evidence_guided", "Evidence-guided$^{\\ddagger}$")):
    d = REC[c]
    rows.append([nm, ci(*d["failure_detection"]), ci(*d["recovery_success"]), str(d["false_completions"]),
                 str(d["unnecessary_attempts"]), f"{d['mean_cost_s']:.1f}"])
    led(f"recovery {c} success", f"{d['recovery_success'][0]}/{d['recovery_success'][1]}", "recovery_scenarios.csv", "SYNTHETIC", "Table sim-recovery")
modes = ["navigation_failure", "timeout", "missing_element", "invalid_submission", "unexpected_state", "missing_confirmation"]
short = {"navigation_failure": "nav.", "timeout": "time-out", "missing_element": "missing el.", "invalid_submission": "invalid sub.",
         "unexpected_state": "unexp. state", "missing_confirmation": "missing conf."}
rows.append(["MIDRULE"])
rows.append(["\\multicolumn{6}{@{}l}{\\emph{Recovered / recoverable by failure mode (retry-based; evidence-guided)}}"])
cells = [f"{short[m]} {REC['retry_based']['by_mode'][m][0]}/{REC['retry_based']['by_mode'][m][1]}; {REC['evidence_guided']['by_mode'][m][0]}" for m in modes]
rows.append(["\\multicolumn{6}{@{}l}{" + ", ".join(cells[:3]) + "}"])
rows.append(["\\multicolumn{6}{@{}l}{" + ", ".join(cells[3:]) + "}"])
table("recovery", f"{SIM} Study~E: 120 failure scenarios, 20 per mode; {sum(int(r['permanent']) for r in REC_ROWS)} drawn as permanent ({int(P['recovery']['permanent_share']['value']*100)}\\% expected), none of them a missing confirmation. Detected: failure noticed by the agent; FC: undetected missing confirmations reported complete; Unnec.: attempts spent on permanent failures; Cost: mean seconds per scenario. Strategy sequences are those of the real recovery engine. $^{{\\ddagger}}$Not implemented.",
      "tab:sim-recovery", "lccccc", ["Recovery", "Detected", "Recovered", "FC", "Unnec.", "Cost"], rows, size="\\scriptsize", sep="2pt")

# ---- Table: overhead (Study F) — ACTUAL components + SYNTHETIC totals, separate blocks
lat = json.loads((HERE / "inputs" / "m2_latency.json").read_text())
gate = [float(r["gate_ms_median"]) for r in csv.DictReader(open(ROOT / "artifacts" / "results" / "verification_gate_cases.csv")) if r["gate_decision"] != "blocked"]
gate.sort()
rows = [["\\multicolumn{4}{@{}l}{\\emph{ACTUAL component latency (ms), local sites, 30 repetitions}}"],
        ["Operation", "median", "p95", ""]]
for k, nm in (("navigate", "navigate"), ("click", "click + load"), ("fill", "fill"), ("dom_extract", "DOM extraction"),
              ("screenshot", "screenshot (evidence)"), ("phi", "$\\Phi$ on a site page")):
    rows.append([nm, f"{lat[k]['median_ms']:.1f}", f"{lat[k]['p95_ms']:.1f}", ""])
    led(f"actual latency {k} median ms", lat[k]["median_ms"], "inputs/m2_latency.json", "ACTUAL", "Table sim-overhead")
rows.append(["$\\Phi$ on gate states$^{*}$", f"{statistics.median(gate):.1f}", f"{gate[int(round(0.95*(len(gate)-1)))]:.1f}", ""])
rows.append(["MIDRULE"])
rows.append(["\\multicolumn{4}{@{}l}{\\emph{SYNTHETIC episode time (s), inference median " + str(P['latency']['inference_median_s']['value']) + " s assumed}}"])
rows.append(["Configuration", "median", "p95", "verif.\\ share"])
L = R["latency"]
for c, nm in (("no_verification", "No verification"), ("evidence_gated", "Evidence-gated ($\\Phi$)"),
              ("self_verification", "LLM self-verification"), ("enhanced_validation", "$\\Phi$ + model check$^{\\ddagger}$")):
    d = L[c]
    rows.append([nm, f"{d['median_s']:.1f}", f"{d['p95_s']:.1f}", f"{100*d['share']['verification']:.1f}\\%"])
    led(f"sim latency {c} median s", round(d["median_s"], 2), "latency_study", "SYNTHETIC", "Table sim-overhead")
table("overhead", f"Study~F, verification overhead. Upper block ACTUAL; lower block {SIM}, built from the ACTUAL component samples and an ASSUMED inference time; the two blocks are not combined into one claim. $^{{*}}$83 decisions on the constructed gate states, each the median of 20 repetitions (Section~\\ref{{sec:res-overhead}}). All times are medians. Inference dominates every synthetic episode ({100*L['evidence_gated']['share']['inference']:.0f}\\% of time under $\\Phi$); evidence screenshots take {100*L['evidence_gated']['share']['evidence']:.1f}\\%. $^{{\\ddagger}}$Not implemented.",
      "tab:sim-overhead", "lccc", ["", "", "", ""], rows, size="\\scriptsize", sep="3pt")

# ---- Sensitivity figure data (Study H)
S = R["sensitivity"]
coords = {}
for c in ("no_verification", "basic_detection", "evidence_gated", "enhanced_validation"):
    pts = S["premature_claim_rate"][c]
    coords[c] = {"FCR": " ".join(f"({k},{v['FCR']:.3f})" for k, v in pts.items()),
                 "FRR": " ".join(f"({k},{v['FRR']:.3f})" for k, v in pts.items())}
style = {"no_verification": "dashed", "basic_detection": "dotted", "evidence_gated": "thick", "enhanced_validation": "dashdotted"}
lab = {"no_verification": "no verification", "basic_detection": "basic detection", "evidence_gated": "$\\Phi$", "enhanced_validation": "enhanced$^{\\ddagger}$"}
fig = ["\\begin{figure}[t]", "\\centering", "\\begin{tikzpicture}",
       "\\begin{axis}[width=0.98\\columnwidth, height=4.2cm, xlabel={assumed premature-claim rate $\\pi$}, ylabel={FCR (solid marks) / FRR (open)},",
       "  xmin=0.25, xmax=1.0, ymin=0, ymax=0.5, legend style={font=\\tiny, at={(0.02,0.98)}, anchor=north west, legend columns=2},",
       "  tick label style={font=\\scriptsize}, label style={font=\\scriptsize}]"]
for c in coords:
    fig.append(f"\\addplot[{style[c]}, mark=*, mark size=1.2pt] coordinates {{{coords[c]['FCR']}}};")
    fig.append(f"\\addlegendentry{{{lab[c]}}}")
for c in coords:
    fig.append(f"\\addplot[{style[c]}, mark=o, mark size=1.2pt, forget plot] coordinates {{{coords[c]['FRR']}}};")
fig += ["\\end{axis}", "\\end{tikzpicture}",
        f"\\caption{{{SIM} Study~H: mean FCR and FRR over 300 regenerated scenario sets per point as the assumed rate at which the planner claims completion of an unfinished task varies. Stricter verification lowers FCR at every rate and raises FRR; its FCR advantage grows with $\\pi$. $^{{\\ddagger}}$Not implemented.}}",
        "\\label{fig:sim-sens}", "\\end{figure}", ""]
(TAB / "sensitivity_fig.tex").write_text("\n".join(fig))

rows = []
for k, v in S["phi_detection_multiplier"].items():
    rows.append([f"$\\Phi$ detection $\\times{k}$", f"{v['FCR']:.2f}", f"{v['FRR']:.2f}", f"{v['TSR']:.2f}"])
for k, v in S["missing_evidence_share"].items():
    rows.append([f"missing evidence {float(k)*100:.0f}\\%: $\\Phi$", f"{v['evidence_gated']['FCR']:.2f}", f"{v['evidence_gated']['FRR']:.2f}", f"{v['evidence_gated']['TSR']:.2f}"])
for k, v in S["action_failure_rate"].items():
    rows.append([f"action failure rate {k}", f"{v['FCR']:.2f}", f"{v['FRR']:.2f}", f"{v['TSR']:.2f}"])
table("sensitivity", f"{SIM} Study~H: robustness of the evidence-gated configuration (means over 300 regenerated sets per row).",
      "tab:sim-sens", "lccc", ["Varied factor", "FCR", "FRR", "TSR"], rows, size="\\scriptsize", sep="3pt")

# ---- Parameter table (appendix)
rows = []
def add(name, val, tag):
    rows.append([name, val, tag])
add("Scenarios per set; dev / held-out seed", f"{P['n_scenarios']}; {P['seed_dev']} / {P['seed_heldout']}", "design")
add("Outcome classes (successful, incomplete, incorrect, missing, contradictory, stale, ambiguous)", " / ".join(f"{P['outcome_mix'][k]:.2f}" for k in ['successful','incomplete','incorrect_action','missing_evidence','contradictory_evidence','stale_evidence','ambiguous']), "ASSUMED")
add("Planner claims completion: if complete / if not ($\\pi$)", f"{P['p_claim_if_complete']['value']} / {P['p_claim_if_not_complete']['value']}", "ASSUMED")
d = R["derived_inputs"]
add("$\\Phi$ withhold rate by category (held-out gate states)", ", ".join(f"{c[:4]}. {v['rate']:.2f}" for c, v in d["detect"]["phi_accepts"].items()), "DERIVED")
add("Basic detection withhold rate by category", ", ".join(f"{c[:4]}. {v['rate']:.2f}" for c, v in d["detect"]["basic_accepts"].items()), "DERIVED")
add("False rejection: $\\Phi$ / basic", f"{d['false_reject']['phi_accepts']['rate']:.3f} / {d['false_reject']['basic_accepts']['rate']:.3f}", "DERIVED")
add("$\\Phi$ rejects when evidence is missing", f"{P['phi_missing_evidence_reject']['value']}", "ASSUMED")
add("Enhanced: extra catch / extra false rejection", f"{P['enhanced_extra_catch']['value']} / {P['enhanced_extra_false_reject']['value']}", "PROPOSED")
add("Finish after rejection; re-claim after false rejection", f"{P['p_continue_success_after_reject']['value']}; {P['p_reclaim_after_false_reject']['value']}", "ASSUMED")
add("Action failure; recovered when recovery on", f"{P['p_action_failure']['value']}; {P['p_recovered_with_recovery']['value']}", "ASSUMED")
add("Repeated workflows; memory gain / loss", f"{P['repeated_workflow_share']['value']}; {P['memory_helpful_gain']['value']} / {P['memory_misleading_loss']['value']}", "ASSUMED")
add("Misleading retrieval: store / filtered", f"{d['memory_misleading']['rate']:.2f} / {P['memory_misleading_prob_filtered']['value']}", "DERIVED / PROPOSED")
add("Recovery strategy sequences", "real engine (Table~\\ref{tab:sim-recovery})", "ACTUAL")
add("Recovery success per attempt", "0.10--0.45 (re-plan), 0.05--0.35 (vision)", "ASSUMED")
add("Missing-confirmation detection: retry / guided", f"{d['missing_confirmation_detection']['rate']:.2f} / {P['recovery']['evidence_guided_confirmation_detection']['value']}", "DERIVED / PROPOSED")
add("Inference time per call (median, log-sd)", f"{P['latency']['inference_median_s']['value']} s, {P['latency']['inference_log_sigma']['value']}", "ASSUMED")
add("Browser, DOM, screenshot, $\\Phi$ latency", "resampled from measurements", "ACTUAL")
table("params", "Simulation parameters and their provenance (\\texttt{benchmarks/simulation/params.json}). DERIVED rates use $(k+0.5)/(n+1)$ on the held-out gate states.",
      "tab:sim-params", "p{3.6cm}p{3.0cm}p{1.3cm}", ["Parameter", "Value", "Class"], rows, size="\\scriptsize", sep="2pt")

with open(HERE / "out" / "heldout" / "ledger_simulation.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(LEDGER[0]))
    w.writeheader()
    w.writerows(LEDGER)
print(f"wrote {len(list(TAB.glob('*.tex')))} tables to {TAB}; ledger rows {len(LEDGER)}")
print(f"P@3 {p3:.3f} R@3 {r3:.3f} MRR {mrr:.3f}")
