import csv, sys, json, statistics, collections, math
sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from st import *
B=str(__import__("pathlib").Path(__file__).resolve().parents[4]) + "/"
cur = list(csv.DictReader(open(B+'artifacts/results/verification_gate_cases.csv')))
phi=sorted(float(r['gate_ms_median']) for r in cur if r['gate_decision']!='blocked')
blk=sorted(float(r['gate_ms_median']) for r in cur if r['gate_decision']=='blocked')
n=len(phi)
print('phi n',n,'median',statistics.median(phi),'max',max(phi),'blocked n',len(blk),'max',max(blk))
for q in (0.9,0.95):
    print(q,'type7',round(pct_rank(phi,q),2),'rank round(q(n-1))+1 ->',phi[int(round(q*(n-1)))], 'nearest-rank ceil', phi[math.ceil(q*n)-1])
# m2 latency
L=json.load(open(B+'benchmarks/simulation/inputs/m2_latency.json'))
for k,v in L.items():
    if isinstance(v,dict) and 'samples_ms' in v:
        s=sorted(v['samples_ms']); n=len(s)
        print(k,n,'median',statistics.median(s),'printed',v.get('median_ms'),'p95(rank round(.95(n-1))+1)',s[int(round(0.95*(n-1)))],'printed',v.get('p95_ms'))
    else: print(k, str(v)[:200])
# memory
M=list(csv.DictReader(open(B+'benchmarks/simulation/inputs/m4_memory.csv')))
rel=[r for r in M if int(r['n_relevant'])>0]
print('queries',len(M),'with relevant',len(rel))
p3=statistics.mean(int(r['relevant_in_top_k'])/3 for r in rel)
r3=statistics.mean(int(r['relevant_in_top_k'])/min(3,int(r['n_relevant'])) for r in rel)
r3b=statistics.mean(int(r['relevant_in_top_k'])/int(r['n_relevant']) for r in rel)
mrr=statistics.mean(float(r['reciprocal_rank']) for r in rel)
print('P@3',p3,'R@3',r3,r3b,'MRR',mrr, 'MRR all 10', statistics.mean(float(r['reciprocal_rank']) for r in M))
print('P@3 max possible', statistics.mean(min(3,int(r['n_relevant']))/3 for r in rel))
for r in M: print(r['group'], r['reciprocal_rank'], r['top1'][:80])
# egress
E_=B+'artifacts/results/e2e_smoke_stub/'
raw=[json.loads(l) for l in open(E_+'egress_raw.jsonl')]
print('connects',len(raw),collections.Counter((x['host'],x['port']) for x in raw),'pids',len({x['pid'] for x in raw}))
ep=[json.loads(l) for l in open(E_+'episodes.jsonl')]
print('episodes',len(ep),collections.Counter(e['config'] for e in ep))
print('nonlocal hosts', sum(1 for e in ep if e['non_local_page_hosts']))
meta=json.load(open(E_+'run_meta.json')); print({k:v for k,v in meta.items() if k not in('environment','tasks')})
mem=[e for e in ep if e['config'] not in ('no_memory','abl_no_memory','ablation_no_memory')]
print(collections.Counter((e['config'], e['memories_retrieved']>0) for e in ep))
print('vision', sum(e['vision_called'] for e in ep),'knowledge',sum(e['knowledge_retrieved']>0 for e in ep),'browser actions', collections.Counter(e['browser_actions'] for e in ep))
