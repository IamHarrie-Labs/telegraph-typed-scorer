import math, sys, statistics
from bench import Scorer
import cases

B=sys.argv[1]; C=sys.argv[2]
corpus=cases.all_cases()

print("=== B. Statelessness: does the bump allocator corrupt later calls?")
# Score 6 probes on a FRESH instance, then again on an instance that has
# already done 400 calls (incl. the 3.8KB adversarial answers).
probes=[(q,gt,g) for _,q,gt,g,_,_ in corpus[:3]] + [(q,gt,b) for _,q,gt,_,b,_ in corpus[300:303]]
fresh=[Scorer(C).score(*p) for p in probes]
warm=Scorer(C)
for intent,q,gt,g,b,fam in corpus:
    warm.score(q,gt,g); warm.score(q,gt,b)
after=[warm.score(*p) for p in probes]
drift=max(abs(a-f) for a,f in zip(after,fresh))
print(f"  fresh vs after {2*len(corpus)} calls -> max drift {drift:.9f}  {'OK' if drift<1e-9 else 'CORRUPTION'}")

print()
print("=== C. Harness sanity: baseline scored against ITSELF must be identical")
s1,s2=Scorer(B),Scorer(B)
diffs=0
for intent,q,gt,g,b,fam in corpus[::7]:
    if abs(s1.score(q,gt,g)-s2.score(q,gt,g))>1e-9: diffs+=1
print(f"  {len(corpus[::7])} cases, mismatches: {diffs}  {'OK' if diffs==0 else 'HARNESS BUG'}")

print()
print("=== D. Do the numbers match hand-computed math?  score = exp(-rel/TAU), TAU=0.005")
sc=Scorer(C)
checks=[("111240.55 USD","111238.02",111240.55,111238.02),
        ("3418.90 USD","3419.15",3418.90,3419.15),
        ("184.22 USD","187.00",184.22,187.00),
        ("25 gwei","0.000000025 ETH",25e-9,25e-9),
        ("2841977","2841977",2841977,2841977)]
for gt,ans,t,a in checks:
    got=sc.score("q",gt,ans)
    rel=abs(a-t)/abs(t); want=math.exp(-rel/0.005)
    ok="OK" if abs(got-want)<2e-3 else "MISMATCH"
    print(f"  gt={gt:<14} ans={ans:<20} rel={rel:.3e}  wasm={got:.6f} hand={want:.6f}  {ok}")

print()
print("=== E. Result excluding the 56 verbatim freebies")
sb=Scorer(B)
kept=[c for c in corpus if c[3].strip()!=c[2].strip()]
bw=cw=0; bm=[]; cm=[]
for intent,q,gt,g,b,fam in kept:
    bg,bb=sb.score(q,gt,g),sb.score(q,gt,b)
    cg,cb=sc.score(q,gt,g),sc.score(q,gt,b)
    bw+= bg>bb; cw+= cg>cb; bm.append(bg-bb); cm.append(cg-cb)
print(f"  cases {len(kept)} (dropped {len(corpus)-len(kept)} verbatim)")
print(f"  baseline  margin {statistics.fmean(bm):.4f}  wins {bw}/{len(kept)}")
print(f"  candidate margin {statistics.fmean(cm):.4f}  wins {cw}/{len(kept)}")
