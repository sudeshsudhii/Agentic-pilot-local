# Re-drives the project's model functions (read-only, no file writes) to obtain per-replication raw values;
# all summary statistics below are computed with my own code.
import sys, random, statistics, collections
sys.path.insert(0,str(__import__("pathlib").Path(__file__).resolve().parents[4]))
sys.path.insert(1,str(__import__('pathlib').Path(__file__).resolve().parent))
import types
_eng=types.ModuleType('backend.recovery.engine')
class RecoveryEngine:
    def classify_failure(self,m): return 'x'
    def select_strategy(self,f,r): return 'exhausted'
_eng.RecoveryEngine=RecoveryEngine
for nm in ('backend','backend.recovery'): sys.modules[nm]=types.ModuleType(nm)
sys.modules['backend.recovery.engine']=_eng
import benchmarks.simulation.simulate_v2 as M
M.P_REC={True:0.66,False:0.49}  # stored values from results.json (recovery_probabilities_used)
from st import pct_rank, mcnemar_exact
P=M.P; SEED=M.SEED; V1=M.V1
rng=random.Random(SEED*31)
diff=[]; cnt=collections.Counter(); sig=0; b_sizes=[]
for r in range(P['monte_carlo_replications']):
    rates=M.sample_rates(rng)
    sc=V1.generate(SEED*1000+r, P['n_scenarios'])
    out=M.run_set(sc, rates=rates, p_rec={True:M.P_REC[True],False:M.P_REC[False]})
    e=out['eps']; cl=out['claimed']
    fc=lambda c:[int(x['reported'] and not x['y']) for x in e[c]]
    ok=lambda c:[int(e[c][i]['accepted']==e[c][i]['y_claim']) for i in cl]
    su=lambda c:[int(x['reported'] and x['y']) for x in e[c]]
    ref='evidence_gated'
    for c in ['no_verification','basic_detection','enhanced_validation']:
        for nm,f in (('fc',fc),('dec',ok),('succ',su)):
            a,bb=f(c),f(ref)
            oth=sum(1 for p,q in zip(a,bb) if p and not q); phi=sum(1 for p,q in zip(a,bb) if q and not p)
            if oth>0: cnt[(c,nm,'other_only>0')]+=1
            if phi>0: cnt[(c,nm,'phi_only>0')]+=1
    a,bb=fc('no_verification'),fc(ref)
    b=sum(1 for p,q in zip(a,bb) if p and not q); c_=sum(1 for p,q in zip(a,bb) if q and not p)
    b_sizes.append(b); sig+= mcnemar_exact(b,c_)<0.05
    diff.append((sum(a)-sum(bb))/len(sc))
d=sorted(diff); n=len(d)
print('mean',statistics.mean(d),'v[25],v[974]',d[25],d[974],'v[24],v[974]',d[24],d[974],'type7',pct_rank(d,0.025),pct_rank(d,0.975))
print('share p<.05',sig/n,'share b>=6',sum(x>=6 for x in b_sizes)/n, 'min b',min(b_sizes))
for k,v in sorted(cnt.items()): print(k,v)

# extended: paired reductions for basic & enhanced, decision-accuracy differences, share decision p<.05
rng=random.Random(SEED*31)
red={c:[] for c in ['no_verification','basic_detection','enhanced_validation']}; dacc={c:[] for c in red}; sigdec=0
for r in range(P['monte_carlo_replications']):
    rates=M.sample_rates(rng)
    sc=V1.generate(SEED*1000+r, P['n_scenarios'])
    out=M.run_set(sc, rates=rates, p_rec={True:0.66,False:0.49})
    e=out['eps']; cl=out['claimed']
    fcn=lambda c: sum(int(x['reported'] and not x['y']) for x in e[c])
    ok=lambda c:[int(e[c][i]['accepted']==e[c][i]['y_claim']) for i in cl]
    for c in red:
        red[c].append((fcn(c)-fcn('evidence_gated'))/len(sc))
        if cl: dacc[c].append((sum(ok('evidence_gated'))-sum(ok(c)))/len(cl))
    do,dr=ok('no_verification'),ok('evidence_gated')
    b=sum(1 for p,q in zip(dr,do) if p and not q); c_=sum(1 for p,q in zip(dr,do) if q and not p)
    sigdec+= (mcnemar_exact(b,c_)<0.05 and sum(dr)>sum(do))
for c in red:
    v=sorted(red[c]); w=sorted(dacc[c])
    print(c,'FC reduction (other-phi)/N mean %.3f [%.3f, %.3f]'%(statistics.mean(v),pct_rank(v,.025),pct_rank(v,.975)),
          'dec acc diff (phi-other) mean %.3f [%.3f, %.3f]'%(statistics.mean(w),pct_rank(w,.025),pct_rank(w,.975)))
print('share decision phi better p<.05',sigdec/1000)
