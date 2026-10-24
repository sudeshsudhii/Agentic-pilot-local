import csv, sys, statistics, collections
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from st import *
R = str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/artifacts/results/"
cur = list(csv.DictReader(open(R+'verification_gate_cases.csv')))
pre = list(csv.DictReader(open(R+'verification_gate_cases_before_fixes.csv')))
abl = list(csv.DictReader(open(R+'verification_gate_ablation.csv')))
def f3(x): return f"{x:.3f}"
def acc(rows, col, val='completed'):
    # gate 'reports complete' if decision == completed
    return {r['case']: int(r[col] == val) for r in rows}
print(collections.Counter(r['gate_decision'] for r in cur), collections.Counter(r['live_empty_decision'] for r in cur))
def summary(rows, col, label):
    neg = [r for r in rows if r['oracle_satisfied']=='0']; pos=[r for r in rows if r['oracle_satisfied']=='1']
    W = sum(1 for r in neg if r[col]!='completed'); FR = sum(1 for r in pos if r[col]!='completed')
    FC = len(neg)-W; Rep = FC + len(pos)-FR
    # McNemar vs dispatch-only (accepts all): gate-only correct = W, dispatch-only correct = FR
    p = mcnemar_exact(W, FR)
    print(f"{label:28s} n-={len(neg)} n+={len(pos)} W={W} [{f3(wilson(W,len(neg))[0])},{f3(wilson(W,len(neg))[1])}] CP{tuple(round(x,3) for x in clopper_pearson(W,len(neg)))} "
          f"FR={FR} [{f3(wilson(FR,len(pos))[0])},{f3(wilson(FR,len(pos))[1])}] CP{tuple(round(x,3) for x in clopper_pearson(FR,len(pos)))} FC/R={FC}/{Rep} p_correct={p:.6g} p_fc_only={mcnemar_exact(W,0):.6g}")
    return W, FR
for split in ['design','held_out','held_out_2']:
    for col in ['gate_decision','live_empty_decision','live_verbose_decision']:
        summary([r for r in cur if r['split']==split], col, f"{split} cur {col}")
    if split!='held_out_2':
        for col in ['gate_decision','live_empty_decision','live_verbose_decision']:
            summary([r for r in pre if r['split']==split], col, f"{split} PRE {col}")
summary([r for r in cur if r['split'] in('held_out','held_out_2')], 'gate_decision', 'held_out_1+2 cur')
# categories table IV
for split in ['design','held_out_2']:
    for cat in sorted({r['category'] for r in cur}):
        rs=[r for r in cur if r['split']==split and r['category']==cat]
        neg=[r for r in rs if r['oracle_satisfied']=='0']; pos=[r for r in rs if r['oracle_satisfied']=='1']
        print(split, cat, f"{len(neg)}/{len(pos)}", sum(r['gate_decision']!='completed' for r in neg), sum(r['gate_decision']!='completed' for r in pos))
# agreement of modes
for r in cur:
    if not (r['gate_decision']==r['live_empty_decision']==r['live_verbose_decision']): print('MODE DISAGREE', r['case'], r['split'])
# fixed vs pre on design
for split in ['design','held_out']:
    c = {r['case']:r for r in cur if r['split']==split}; pr={r['case']:r for r in pre if r['split']==split}
    for pc in ['gate_decision','live_empty_decision','live_verbose_decision']:
        fixed=broken=0
        for k in c:
            okc = (c[k]['gate_decision']=='completed')==(c[k]['oracle_satisfied']=='1')
            okp = (pr[k][pc]=='completed')==(pr[k]['oracle_satisfied']=='1')
            fixed += okc and not okp; broken += okp and not okc
        print(split, 'cur vs pre', pc, 'fixed', fixed, 'broken', broken, 'p', mcnemar_exact(fixed, broken))
# ablation
cols=['without_none','without_E','without_H','without_Q','without_T','without_X','without_R','without_B']
for split in ['design','held_out','held_out_2']:
    rs=[r for r in abl if r['split']==split]
    full={r['case']: (r['without_none']=='1')==(r['oracle_satisfied']=='1') for r in rs}
    for c in cols:
        fc=sum(1 for r in rs if r['oracle_satisfied']=='0' and r[c]=='1'); fr=sum(1 for r in rs if r['oracle_satisfied']=='1' and r[c]=='0')
        ok={r['case']:(r[c]=='1')==(r['oracle_satisfied']=='1') for r in rs}
        fb=sum(full[k] and not ok[k] for k in ok); ab=sum(ok[k] and not full[k] for k in ok)
        ch=sum((r[c])!=(r['without_none']) for r in rs)
        print(split, c, 'FC',fc,'FR',fr,'full_better',fb,'abl_better',ab,'p',round(mcnemar_exact(fb,ab),4),'changed',ch)
# ablation 'none' equals gate_decision?
cd={r['case']+r['split']:r for r in cur}
mm=[r['case'] for r in abl if (r['without_none']=='1')!=(cd[r['case']+r['split']]['gate_decision']=='completed')]
print('ablation none vs gate mismatch', mm)
# latency
ms=[(float(r['gate_ms_median']), r) for r in cur if r['gate_ms_median']]
print('n with latency', len(ms))
phi=[]; pc=[]
for v,r in ms:
    msg=r['gate_message']
    phi.append(v)
print(collections.Counter(r['gate_message'][:40] for r in cur).most_common(12))
