"""Write the paper's simulation tables and the evidence ledger from the corrected model's out/heldout_v2/results.json.

v2 (simulate_v2.py) is post hoc: it corrects modelling errors found by the methodology audit and is not
pre-registered; v1 outputs are archived in out/heldout_v1/. Every table produced here is SYNTHETIC unless a
cell says ACTUAL. Usage: python -m benchmarks.simulation.make_tables
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

from benchmarks.e2e.stats import wilson

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
OUT = HERE / "out" / "heldout_v2"
R = json.loads((OUT / "results.json").read_text())
P = json.loads((HERE / "params.json").read_text())
TAB = ROOT / "paper" / "tables" / "sim"
TAB.mkdir(parents=True, exist_ok=True)
LEDGER: list[dict] = []


def ci(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{k}/{n} [{lo:.2f},{hi:.2f}]"


def d2(x: float) -> str:
    return f"{x:.2f}".replace("0.", ".", 1)


def f3(x: float) -> str:
    return f"{x:.3f}".replace("0.", ".", 1) if x < 1 else f"{x:.2f}"


def r2(x: float) -> str:
    """Two decimals, ties rounded half up (0.125 -> 0.13), as readers expect."""
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def pf(p: float) -> str:
    """Exact p-value to three significant figures (no half-even rounding surprises at 0.0625)."""
    return "<0.001" if p < 0.001 else f"{p:.3g}"


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


C = R["policy"]
DEC = R["decision"]
MC = R["monte_carlo"]
T = R["paired_vs_evidence_gated"]
NAMES = {"no_verification": "No verification", "basic_detection": "Basic success detection",
         "evidence_gated": "Evidence-gated ($\\Phi$)", "enhanced_validation": "Enhanced validation$^{\\ddagger}$"}
SIM = "\\textsc{Simulation-based (synthetic)}"
NCL = R["n_claims"]
COND = "Synthetic $p$-values and intervals are conditional on the simulation assumptions; they are not empirical tests of the agent."
SRC = "out/heldout_v2/results.json"

# ---- Table: baseline comparison (Study A/B): policy level (final outcome) and decision level (first claim)
rows = []
for c, nm in NAMES.items():
    m = C[c]
    d = DEC[c]
    rows.append([nm, str(m["TP"]), str(m["FP"]), str(m["FN"]), str(m["TN"]),
                 ci(m["TP"], m["N"]), ci(m["FP"], m["TP"] + m["FP"]), ci(m["FN"], m["TP"] + m["FN"]),
                 f"{d['TP']}/{d['FP']}/{d['FN']}/{d['TN']}", ci(d["TP"] + d["TN"], NCL)])
    for k in ("TP", "FP", "FN", "TN"):
        led(f"{c} policy {k}", m[k], f"{SRC} policy", "SYNTHETIC", "Table sim-baseline")
    led(f"{c} FCR", round(m["FCR"], 4), "FP/(TP+FP)", "SYNTHETIC", "Table sim-baseline")
    led(f"{c} FRR", round(m["FRR"], 4), "FN/(TP+FN)", "SYNTHETIC", "Table sim-baseline")
    led(f"{c} decision TP/FP/FN/TN", f"{d['TP']}/{d['FP']}/{d['FN']}/{d['TN']}", f"{SRC} decision", "SYNTHETIC", "Table sim-baseline")
    led(f"{c} decision accuracy", f"{d['TP'] + d['TN']}/{NCL}", "(TP+TN)/claims", "SYNTHETIC", "Table sim-baseline")
table("baseline", f"{SIM} Study~B on the same 100 held-out synthetic scenarios (corrected model v2). Policy level: final outcome of each episode (TP reported and achieved, FP reported but not achieved, FN achieved but not reported, TN neither); the final state can differ between configurations because a rejection returns control to planning. Decision level: the verifier's first accept/withhold decision on the {NCL} scenarios in which the planner claims completion ({R['n_claims_true']} truly complete), against the true state at that claim. Wilson 95\\% intervals. {COND} $^{{\\ddagger}}$Not implemented (proposed).",
      "tab:sim-baseline", "lccccccccc", ["Configuration", "TP", "FP", "FN", "TN", "TSR", "FCR", "FRR", "Decision TP/FP/FN/TN", "Decision acc."], rows,
      size="\\footnotesize", sep="4pt", wide=True)

# ---- Table: paired tests and Monte Carlo
rows = []
for c, nm in NAMES.items():
    mc = MC[c]["FCR"]
    mcd = MC[c]["dec_acc"]
    mcs = f"{d2(mc['mean'])} [{d2(mc['p2.5'])},{d2(mc['p97.5'])}]; {d2(mcd['mean'])}"
    if c == "evidence_gated":
        rows.append(["$\\Phi$", "ref.", "", "ref.", "", "ref.", "", mcs])
        continue
    t = T[c]
    rows.append([nm.replace(" success detection", "").replace(" validation", "").replace("No verification", "None"),
                 f"{t['fc_other_only']}/{t['fc_phi_only']}", pf(t['fc_p']),
                 f"{t['decision_other_only']}/{t['decision_phi_only']}", pf(t['decision_p']),
                 f"{t['success_other_only']}/{t['success_phi_only']}", pf(t['success_p']), mcs])
    led(f"{c} McNemar p (episode false completion vs evidence_gated)", round(t["fc_p"], 4), "exact McNemar on paired FP indicators", "SYNTHETIC", "Table sim-tests")
    led(f"{c} McNemar p (decision correctness vs evidence_gated)", round(t["decision_p"], 4), "exact McNemar on paired first-decision correctness", "SYNTHETIC", "Table sim-tests")
    led(f"{c} McNemar p (task success vs evidence_gated)", round(t["success_p"], 4), "exact McNemar on paired success indicators", "SYNTHETIC", "Table sim-tests")
table("tests", f"{SIM} Paired comparisons with $\\Phi$, exact McNemar tests on discordant pairs $b/c$ ($b$: only the other configuration; $c$: only $\\Phi$). FC: episode ends in a false completion (100 scenarios). Dec.: first decision correct ({NCL} claims). Succ.: task achieved and reported (100 scenarios). MC: mean FCR [2.5--97.5th percentiles]; mean decision accuracy, over {P['monte_carlo_replications']} regenerated scenario sets with rates drawn from their Beta posteriors. For FC against None and Basic, $c=0$ by construction ($\\Phi$ only withholds claims; for Enhanced, $b=0$ likewise), so those $p$-values carry no information about direction; the size of the reduction and its Monte Carlo interval are the informative quantities. {COND}",
      "tab:sim-tests", "lccccccc", ["Config.", "FC $b/c$", "$p$", "Dec.\\ $b/c$", "$p$", "Succ.\\ $b/c$", "$p$", "MC FCR; dec.\\ acc."], rows, size="\\scriptsize", sep="1.5pt")
MP = R["monte_carlo_paired"]
led("MC paired FC reduction Phi vs none (mean [p2.5,p97.5])", f"{MP['fc_reduction_phi_vs_none']['mean']:.3f} [{MP['fc_reduction_phi_vs_none']['p2.5']:.2f},{MP['fc_reduction_phi_vs_none']['p97.5']:.2f}]", f"{SRC} monte_carlo_paired", "SYNTHETIC", "Sec. sim-results H1")
led("MC share of sets with FC McNemar p<0.05", MP["share_fc_p_lt_05"], f"{SRC} monte_carlo_paired", "SYNTHETIC", "Sec. sim-results H1")
led("MC share of sets with Phi decision accuracy better at p<0.05", MP["share_decision_phi_better_p_lt_05"], f"{SRC} monte_carlo_paired", "SYNTHETIC", "Sec. sim-results H2")

# ---- Table: ablation (Study C)
AB = {"evidence_gated": "Full ($\\Phi$)", "abl_no_evidence_validation": "-- $\\Phi$",
      "abl_no_memory": "-- memory", "abl_no_recovery": "-- recovery engine$^{\\S}$"}
rows = []
for c, nm in AB.items():
    m = C[c]
    mc = MC[c]
    t = T.get(c)
    lo, hi = wilson(m["TP"], m["N"])
    rows.append([nm, f"{m['TP']} [{d2(lo)},{d2(hi)}]", f3(m["FCR"]), f3(m["FRR"]), f3(m["F1"]),
                 "ref." if t is None else f"{t['success_other_only']}/{t['success_phi_only']}; {pf(t['success_p'])}",
                 f"{mc['TSR']['mean']:.2f}", f"{mc['FCR']['mean']:.2f}"])
    led(f"{c} TSR", m["TSR"], "TP/N", "SYNTHETIC", "Table sim-ablation")
    led(f"{c} MC TSR mean", round(mc["TSR"]["mean"], 4), f"{SRC} monte_carlo", "SYNTHETIC", "Table sim-ablation")
table("ablation", f"{SIM} Study~C: one component removed at a time, on the same 100 scenarios (policy level). Each row is a simulated configuration, not a run of the implementation; each corresponds to a switch in the code (\\texttt{{verification\\_mode}}, \\texttt{{enable\\_memory}}, \\texttt{{enable\\_recovery}}). $^{{\\S}}$As in the code, disabling the recovery engine leaves the three inline retries of the verification node in place. Removal of stored evidence is not simulated: $\\Phi$ reads the live page, so stored evidence affects the audit trail, not decisions (code behaviour). Succ.: paired task-success discordance $b/c$ with $\\Phi$ and exact McNemar $p$. MC: means over {P['monte_carlo_replications']} regenerated sets. {COND}",
      "tab:sim-ablation", "lccccccc", ["Configuration", "TP (of 100)", "FCR", "FRR", "F1", "Succ.\\ $b/c$; $p$", "MC TSR", "MC FCR"], rows, size="\\scriptsize", sep="1.6pt")

# ---- Table: memory (Study D) — ACTUAL retrieval on synthetic corpus + SYNTHETIC repeated workflows
mem = list(csv.DictReader(open(HERE / "inputs" / "m4_memory.csv")))
with_rel = [m for m in mem if m["n_relevant"] not in ("", "0")]
p3 = sum(int(m["relevant_in_top_k"]) for m in with_rel) / (3 * len(with_rel))
r3 = statistics.mean(float(m["recall_at_k"]) for m in with_rel)
mrr = statistics.mean(float(m["reciprocal_rank"]) for m in with_rel)
mis = R["rates"]["memory_misleading"]
led("retrieval precision@3", round(p3, 3), "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
led("retrieval recall@3", round(r3, 3), "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
led("retrieval MRR", round(mrr, 3), "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
led("queries with misleading top-1", f"{mis['k']}/{mis['n']}", "inputs/m4_memory.csv", "ACTUAL (synthetic corpus)", "Table sim-memory")
M = R["memory"]
NREC = 22  # 14 group records + 8 distractors, measure_inputs.MEMORY_GROUPS / DISTRACTORS
rows = [["\\multicolumn{5}{@{}l}{\\emph{ACTUAL retrieval, real store, " + str(NREC) + " synthetic records; 9 queries with a relevant record}}"],
        ["Precision@3 / Recall@3 / MRR", f"{p3:.2f}", f"{r3:.2f}", f"{mrr:.2f}", ""],
        ["Top-1 irrelevant or failed (all 10 queries)", f"{mis['k']}/{mis['n']}", "", "", ""],
        ["MIDRULE"],
        ["\\multicolumn{5}{@{}l}{\\emph{SYNTHETIC repeated workflows (n=" + str(M['evidence_gated']['N']) + ")}}"],
        ["Configuration", "TSR", "FCR", "P(misleading)", ""]]
for c, nm, pm in (("abl_no_memory", "Memory disabled", "--"), ("evidence_gated", "Memory enabled", f"{mis['k'] / mis['n']:.2f} (derived; mapping assumed)"),
                  ("mem_filtered", "Relevance-filtered$^{\\ddagger}$", f"{P['memory_misleading_prob_filtered']['value']:.2f} (assumed)")):
    m = M[c]
    rows.append([nm, ci(m["TP"], m["N"]), f3(m["FCR"]), pm, ""])
    led(f"memory {c} successes", f"{m['TP']}/{m['N']}", f"{SRC} memory", "SYNTHETIC", "Table sim-memory")
table("memory", f"Study~D, memory and retrieval. Upper block ACTUAL (real store, synthetic records); lower block {SIM}. P(misleading): probability that the retrieved context misleads the planner; for the filter it is an assumed input, so any effect of the filter follows from that assumption. With 44 repeated workflows the study cannot detect an effect of the assumed size (gain 0.08, loss 0.10). $^{{\\ddagger}}$Not implemented.",
      "tab:sim-memory", "lcccc", ["", "", "", "", ""], rows, size="\\scriptsize", sep="3pt")

# ---- Table: recovery (Study E)
REC = R["recovery"]
REC_ROWS = [r for r in csv.DictReader(open(OUT / "recovery_scenarios.csv")) if r["config"] == "retry_based"]
rows = []
for c, nm in (("no_recovery", "Engine off$^{\\S}$"), ("retry_based", "Engine on (as impl.; sim.)"), ("evidence_guided", "Evidence-guided$^{\\ddagger}$")):
    d = REC[c]
    rows.append([nm, ci(*d["failure_detection"]), ci(*d["recovery_success"]), str(d["false_completions"]),
                 str(d["unnecessary_attempts"]), f"{d['mean_attempts']:.2f}"])
    led(f"recovery {c} success", f"{d['recovery_success'][0]}/{d['recovery_success'][1]}", f"{SRC} recovery", "SYNTHETIC", "Table sim-recovery")
    led(f"recovery {c} false completions", d["false_completions"], f"{SRC} recovery", "SYNTHETIC", "Table sim-recovery")
    led(f"recovery {c} unnecessary attempts", d["unnecessary_attempts"], f"{SRC} recovery", "SYNTHETIC", "Table sim-recovery")
b, cc, pr = R["recovery_paired_guided_vs_retry"]
led("recovery guided vs retry paired b/c, p", f"{b}/{cc}, {pr:.2g}", f"{SRC} recovery_paired_guided_vs_retry", "SYNTHETIC (by assumption)", "Sec. sim-results E")
modes = ["navigation_failure", "timeout", "missing_element", "invalid_submission", "unexpected_state", "missing_confirmation"]
short = {"navigation_failure": "nav.", "timeout": "time-out", "missing_element": "missing el.", "invalid_submission": "invalid sub.",
         "unexpected_state": "unexp. state", "missing_confirmation": "missing conf."}
rows.append(["MIDRULE"])
rows.append(["\\multicolumn{6}{@{}l}{\\emph{Recovered / recoverable by mode (engine off; engine on; guided)}}"])
cells = [f"{short[m]} {REC['no_recovery']['by_mode'][m][0]}; {REC['retry_based']['by_mode'][m][0]}; {REC['evidence_guided']['by_mode'][m][0]} / {REC['retry_based']['by_mode'][m][1]}" for m in modes]
rows.append(["\\multicolumn{6}{@{}l}{" + ", ".join(cells[:3]) + "}"])
rows.append(["\\multicolumn{6}{@{}l}{" + ", ".join(cells[3:]) + "}"])
table("recovery", f"{SIM} Study~E: 120 failure scenarios, 20 per mode; {sum(int(r['permanent']) for r in REC_ROWS)} drawn as permanent ({int(P['recovery']['permanent_share']['value']*100)}\\% expected), none of them a missing confirmation. Entry paths and strategy sequences follow the code for the first failure of a task (each scenario has one failure; in the code later failures find the shared retry counter partly used): action errors, including a planner's request for help, are retried three times inline before the engine is called; a failed initial navigation is retried three times by the browser executor and then passed to the engine; a missing confirmation raises no error and is handled only by rejection and continuation. $^{{\\S}}$The retries before the engine remain. Per-attempt success rates are ASSUMED (PROPOSED for the guided variant), so differences between rows follow from them. Detected: failure noticed; FC: undetected missing confirmations reported complete; Unnec.: attempts on permanent failures; Att.: mean attempts. $^{{\\ddagger}}$Not implemented.",
      "tab:sim-recovery", "lccccc", ["Recovery", "Detected", "Recovered", "FC", "Unnec.", "Att."], rows, size="\\scriptsize", sep="2pt")

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
rows.append(["Configuration", "median", "mean", "verif.\\ share"])
L = R["latency"]
for c, nm in (("no_verification", "No verification"), ("evidence_gated", "Evidence-gated ($\\Phi$)"),
              ("self_verification", "LLM self-verification"), ("enhanced_validation", "$\\Phi$ + model check$^{\\ddagger}$")):
    d = L[c]
    rows.append([nm, f"{d['median_s']:.1f}", f"{d['mean_s']:.1f}", f"{100*d['verify_share']:.2f}\\%"])
    led(f"sim latency {c} median s", round(d["median_s"], 2), f"{SRC} latency", "SYNTHETIC", "Table sim-overhead")
    led(f"sim latency {c} mean s", round(d["mean_s"], 2), f"{SRC} latency", "SYNTHETIC", "Table sim-overhead")
led("sim latency Phi mean overhead vs none", f"{100*(L['evidence_gated']['mean_s']/L['no_verification']['mean_s']-1):.1f}%", "mean_s ratio", "SYNTHETIC", "Sec. sim-results F")
led("sim latency self-check mean overhead vs none", f"{100*(L['self_verification']['mean_s']/L['no_verification']['mean_s']-1):.1f}%", "mean_s ratio", "SYNTHETIC", "Sec. sim-results F")
table("overhead", f"Study~F, verification overhead. Upper block ACTUAL; p95 is the order statistic of rank $\\mathrm{{round}}(0.95(n-1))+1$. $^{{*}}$83 decisions on the constructed gate states, each the median of 20 repetitions (Section~\\ref{{sec:res-overhead}}), measured on 2026-10-04 on a 2.1\\,GHz machine; the other rows on 2026-10-23 on a 2.8\\,GHz machine, so the two $\\Phi$ rows are not directly comparable. Lower block {SIM}, built from the ACTUAL component samples and an ASSUMED inference time, with re-planning after rejections and recovery attempts included; the two blocks are not combined into one claim. Inference takes {100*L['evidence_gated']['inference_share']:.0f}\\% of synthetic episode time under $\\Phi$, evidence screenshots {100*L['evidence_gated']['evidence_share']:.1f}\\%. $^{{\\ddagger}}$Not implemented.",
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
for c in coords:
    for k, v in S["premature_claim_rate"][c].items():
        led(f"sensitivity pi={k} {c} FCR/FRR", f"{v['FCR']:.3f}/{v['FRR']:.3f}", f"{SRC} sensitivity", "SYNTHETIC", "Fig. sim-sens")

rows = []
for k, v in S["phi_detection_multiplier"].items():
    rows.append([f"$\\Phi$ detection $\\times{k}$", f"{v['FCR']:.2f}", f"{v['FRR']:.2f}", f"{v['TSR']:.2f}"])
for k, v in S["missing_evidence_share"].items():
    rows.append([f"missing evidence {float(k)*100:.0f}\\%", f"{v['FCR']:.2f}", f"{v['FRR']:.2f}", f"{v['TSR']:.2f}"])
for k, v in S["action_failure_rate"].items():
    rows.append([f"action failure rate {k}", f"{v['FCR']:.2f}", f"{v['FRR']:.2f}", f"{v['TSR']:.2f}"])
for k, v in S["continuation_rate"]["evidence_gated"].items():
    rows.append([f"finish after rejection {k}", f"{v['FCR']:.2f}", f"{v['FRR']:.2f}", f"{v['TSR']:.2f}"])
for grp in ("phi_detection_multiplier", "missing_evidence_share", "action_failure_rate"):
    for k, v in S[grp].items():
        led(f"sensitivity {grp}={k} Phi FCR/FRR/TSR", f"{v['FCR']:.3f}/{v['FRR']:.3f}/{v['TSR']:.3f}", f"{SRC} sensitivity", "SYNTHETIC", "Table sim-sens")
for k, v in S["continuation_rate"]["evidence_gated"].items():
    led(f"sensitivity continuation={k} Phi FCR/FRR/TSR", f"{v['FCR']:.3f}/{v['FRR']:.3f}/{v['TSR']:.3f}", f"{SRC} sensitivity", "SYNTHETIC", "Table sim-sens")
table("sensitivity", f"{SIM} Study~H: robustness of the evidence-gated configuration (means over 300 regenerated sets per row, drawn from a random stream separate from the 1{{,}}000-set Monte Carlo of Table~\\ref{{tab:sim-tests}}, so the unperturbed rows differ slightly from it). Without verification FCR stays at {S['continuation_rate']['no_verification']['0.35']['FCR']:.2f} at every continuation rate.",
      "tab:sim-sens", "lccc", ["Varied factor ($\\Phi$)", "FCR", "FRR", "TSR"], rows, size="\\scriptsize", sep="3pt")

# ---- Parameter table (appendix)
rows = []
def add(name, val, tag):
    rows.append([name, val, tag])
d = R["rates"]
add("Scenarios per set; dev / held-out seed; MC sets", f"{P['n_scenarios']}; {P['seed_dev']} / {P['seed_heldout']}; {P['monte_carlo_replications']}", "ASSUMED (design choice)")
add("Task categories (nav., search, form, data entry, extraction, multi-step)", " / ".join(f"{P['category_mix'][k]:.2f}" for k in ['navigation','search','form','data_entry','extraction','multi_step']), "ASSUMED")
add("Outcome classes (successful, incomplete, incorrect, missing, contradictory, stale, ambiguous)", " / ".join(f"{P['outcome_mix'][k]:.2f}" for k in ['successful','incomplete','incorrect_action','missing_evidence','contradictory_evidence','stale_evidence','ambiguous']), "ASSUMED")
add("P(task truly complete $\\mid$ class), same order", " / ".join(f"{P['p_true_complete_given_outcome'][k]:.1f}" for k in ['successful','incomplete','incorrect_action','missing_evidence','contradictory_evidence','stale_evidence','ambiguous']), "ASSUMED")
add("Planner claims completion: if complete / if not ($\\pi$)", f"{P['p_claim_if_complete']['value']} / {P['p_claim_if_not_complete']['value']}", "ASSUMED")
add("$\\Phi$ withhold rate on unsatisfied states, by task category", ", ".join(f"{c[:4]}. {r2(v['rate'])}" for c, v in d["detect"]["phi_accepts"].items()), "DERIVED (mapping ASSUMED)")
add("Basic detection withhold rate, same", ", ".join(f"{c[:4]}. {r2(v['rate'])}" for c, v in d["detect"]["basic_accepts"].items()), "DERIVED (mapping ASSUMED)")
add("False rejection: $\\Phi$ / basic", f"{d['false_reject']['phi_accepts']['k']}/{d['false_reject']['phi_accepts']['n']} $\\to$ {d['false_reject']['phi_accepts']['rate']:.2f} / {d['false_reject']['basic_accepts']['rate']:.2f} (satisfied states of the mapped categories; bot-check pages excluded)", "DERIVED")
add("Ambiguous-class detection factor", f"{P['ambiguous_detection_factor']['value']}", "ASSUMED")
add("Verifier rejects when evidence is missing ($\\Phi$ and basic)", f"{P['phi_missing_evidence_reject']['value']}", "ASSUMED")
add("Enhanced: extra catch / extra false rej. / contradiction rej.", f"{P['enhanced_extra_catch']['value']} / {P['enhanced_extra_false_reject']['value']} / {P['enhanced_contradiction_reject']['value']}", "PROPOSED")
add("Finish after rejection (continuation is verified again)", f"{P['p_continue_success_after_reject']['value']}", "ASSUMED")
add("Action failure; recovered with / without engine", f"{P['p_action_failure']['value']}; {R['recovery_probabilities_used']['recovery_on']:.2f} / {R['recovery_probabilities_used']['recovery_off']:.2f}", "ASSUMED; SYNTHETIC (Study E)")
add("Repeated workflows; memory gain / loss", f"{P['repeated_workflow_share']['value']}; {P['memory_helpful_gain']['value']} / {P['memory_misleading_loss']['value']}", "ASSUMED")
add("Misleading retrieval: store / filtered", f"{d['memory_misleading']['rate']:.2f} (raw $k/n$) / {P['memory_misleading_prob_filtered']['value']}", "DERIVED (mapping ASSUMED) / PROPOSED")
add("Recovery: permanent share; max attempts", f"{P['recovery']['permanent_share']['value']}; {P['recovery']['max_attempts']}", "ASSUMED")
add("Recovery entry paths and strategy sequences", "code (Table~\\ref{tab:sim-recovery})", "ACTUAL")
add("Recovery success per attempt", "0.10--0.45 (re-plan), 0.05--0.35 (vision); guided 0.35--0.55", "ASSUMED / PROPOSED")
add("Missing-confirmation detection: retry / guided", f"{r2(d['missing_confirmation_detection']['rate'])} / {P['recovery']['evidence_guided_confirmation_detection']['value']}", "DERIVED via ASSUMED proxy / PROPOSED")
add("Steps per episode by category (same order as above)", " / ".join(str(P['latency']['steps_by_category'][k]) for k in ['navigation','search','form','data_entry','extraction','multi_step']), "ASSUMED")
add("Inference time per call (median, log-sd)", f"{P['latency']['inference_median_s']['value']} s, {P['latency']['inference_log_sigma']['value']}", "ASSUMED")
add("Browser, DOM, screenshot, $\\Phi$ latency", "resampled from measurements", "ACTUAL")
table("params", "Simulation parameters of the corrected model v2 and their provenance (\\texttt{benchmarks/simulation/params.json}, \\texttt{simulate\\_v2.py}). DERIVED gate rates use $(k+0.5)/(n+1)$ on the held-out gate states (the misleading-retrieval rate is the raw share $3/10$); Monte Carlo sets draw them from Beta$(k+0.5, n-k+0.5)$.",
      "tab:sim-params", "p{3.6cm}p{3.0cm}p{1.3cm}", ["Parameter", "Value", "Class"], rows, size="\\scriptsize", sep="2pt")

with open(OUT / "ledger_simulation.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(LEDGER[0]))
    w.writeheader()
    w.writerows(LEDGER)
print(f"wrote {len(list(TAB.glob('*.tex')))} tables to {TAB}; ledger rows {len(LEDGER)}")
print(f"P@3 {p3:.3f} R@3 {r3:.3f} MRR {mrr:.3f}")
