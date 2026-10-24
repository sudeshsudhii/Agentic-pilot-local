import csv, sys, json, collections, statistics
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from st import *
O=str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/benchmarks/simulation/out/heldout_v2/"
S=list(csv.DictReader(open(O+'scenarios.csv')))
print('N',len(S))
cfgs=['no_verification','basic_detection','evidence_gated','enhanced_validation','abl_no_evidence_validation','abl_no_memory','abl_no_recovery','mem_filtered']
I=lambda v: int(v) if v!='' else None
def w(k,n): a,b=wilson(k,n); return f"{k}/{n} [{a:.2f},{b:.2f}]"
pol={}
for c in cfgs:
    rep=[I(s[c+'_reported']) for s in S]; y=[I(s[c+'_y']) for s in S]
    TP=sum(r and t for r,t in zip(rep,y)); FP=sum(r and not t for r,t in zip(rep,y)); FN=sum((not r) and t for r,t in zip(rep,y)); TN=len(S)-TP-FP-FN
    pol[c]=dict(TP=TP,FP=FP,FN=FN,TN=TN)
    prec=TP/(TP+FP); rec=TP/(TP+FN); F1=2*prec*rec/(prec+rec)
    print(f"{c:28s} TP{TP} FP{FP} FN{FN} TN{TN} TSR {w(TP,100)} FCR {w(FP,TP+FP)} ({FP/(TP+FP):.3f}) FRR {w(FN,TP+FN)} ({FN/(TP+FN):.3f}) F1 {F1:.3f} acc {(TP+TN)/100}")
claimed=[i for i,s in enumerate(S) if s['evidence_gated_claimed']=='1']
for c in cfgs[:4]:
    assert [i for i,s in enumerate(S) if s[c+'_claimed']=='1']==claimed
    assert all(S[i][c+'_y_claim']==S[i]['evidence_gated_y_claim'] for i in claimed)
ytrue=sum(int(S[i]['evidence_gated_y_claim']) for i in claimed)
print('claims',len(claimed),'true at claim',ytrue)
dec={}
for c in cfgs[:4]:
    acc=[int(S[i][c+'_accepted'])==int(S[i][c+'_y_claim']) for i in claimed]
    TP=sum(int(S[i][c+'_accepted']) and int(S[i][c+'_y_claim']) for i in claimed)
    FP=sum(int(S[i][c+'_accepted']) and not int(S[i][c+'_y_claim']) for i in claimed)
    FN=sum((not int(S[i][c+'_accepted'])) and int(S[i][c+'_y_claim']) for i in claimed)
    TN=len(claimed)-TP-FP-FN
    dec[c]=acc
    print(f"dec {c:22s} {TP}/{FP}/{FN}/{TN} acc {w(sum(acc),len(claimed))} = {sum(acc)/len(claimed):.3f}")
ref='evidence_gated'
def pr(a,b):
    x=sum(1 for p,q in zip(a,b) if p and not q); y=sum(1 for p,q in zip(a,b) if q and not p); return x,y,mcnemar_exact(x,y)
for c in cfgs:
    if c==ref: continue
    fo=[I(s[c+'_reported']) and not I(s[c+'_y']) for s in S]; fr=[I(s[ref+'_reported']) and not I(s[ref+'_y']) for s in S]
    so=[I(s[c+'_reported']) and I(s[c+'_y']) for s in S]; sr=[I(s[ref+'_reported']) and I(s[ref+'_y']) for s in S]
    out=f"{c:28s} FC b/c {pr(fo,fr)}  Succ {pr(so,sr)}"
    if c in dec: out+=f"  Dec {pr(dec[c],dec[ref])}"
    print(out)
# check characterisation of discordant decisions none vs phi
nv=[(S[i]['evidence_gated_accepted'],S[i]['evidence_gated_y_claim']) for i in claimed if dec['no_verification'][claimed.index(i)]!=dec[ref][claimed.index(i)]]
print('none-vs-phi discordant (phi_accepted, y_claim):',collections.Counter(nv))
# Wilson for single-set FC reduction 9/100
print('FC prevented 9/100 wilson',wilson(9,100), 'CP',clopper_pearson(9,100))
# memory subset
rep_=[s for s in S if s['repeated']=='1']
print('repeated',len(rep_))
for c in ['abl_no_memory','evidence_gated','mem_filtered']:
    TP=sum(I(s[c+'_reported']) and I(s[c+'_y']) for s in rep_); FP=sum(I(s[c+'_reported']) and not I(s[c+'_y']) for s in rep_)
    print('mem',c,w(TP,len(rep_)),'FCR',round(FP/(TP+FP),3))
# recovery
R=list(csv.DictReader(open(O+'recovery_scenarios.csv')))
for c in ['no_recovery','retry_based','evidence_guided']:
    rr=[r for r in R if r['config']==c]
    perm=[r for r in rr if r['permanent']=='1']; rec=[r for r in rr if r['permanent']=='0']
    k=sum(int(r['recovered']) for r in rec); d=sum(int(r['detected']) for r in rr)
    print(c,'n',len(rr),'perm',len(perm),'recoverable',len(rec),'recovered',w(k,len(rec)),'detected',w(d,len(rr)),'FC',sum(int(r['false_completion']) for r in rr),
          'unnec',sum(int(r['attempts']) for r in perm),'mean att',round(statistics.mean(int(r['attempts']) for r in rr),3),
          'perm modes',collections.Counter(r['mode'] for r in perm))
    print('   by mode',{m:(sum(int(r['recovered']) for r in rec if r['mode']==m),sum(1 for r in rec if r['mode']==m)) for m in sorted({r['mode'] for r in rr})})
g={r['id']:int(r['recovered']) for r in R if r['config']=='evidence_guided' and r['permanent']=='0'}
e={r['id']:int(r['recovered']) for r in R if r['config']=='retry_based' and r['permanent']=='0'}
o={r['id']:int(r['recovered']) for r in R if r['config']=='no_recovery' and r['permanent']=='0'}
print('guided vs engine',pr([g[k] for k in g],[e[k] for k in g]), 'engine vs off', pr([e[k] for k in e],[o[k] for k in e]))
# MC values from results
res=json.load(open(O+'results.json'))
print(res['monte_carlo_paired']); 
for c in cfgs[:4]: print(c, {k:round(v['mean'],3) for k,v in res['monte_carlo'][c].items()}, [round(res['monte_carlo'][c]['FCR'][q],3) for q in ('p2.5','p97.5')])
print({c:res['monte_carlo'][c]['TSR']['mean'] for c in ['evidence_gated','abl_no_recovery']})
L=res['latency']; print({c:(round(v['median_s'],1),round(v['mean_s'],1),round(100*v['verify_share'],2),round(100*v['inference_share'],1),round(100*v['evidence_share'],1)) for c,v in L.items()})
print('mean +%', (L['evidence_gated']['mean_s']/L['no_verification']['mean_s']-1)*100, 'self',(L['self_verification']['mean_s']/L['no_verification']['mean_s']-1)*100, 'enh',(L['enhanced_validation']['mean_s']/L['no_verification']['mean_s']-1)*100)
print(res['latency_sweep'])
