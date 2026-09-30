#!/usr/bin/env bash
python3 - <<'PY'
def load(L):
    d={}
    for line in open(f"/tmp/score_{L}.txt"):
        p=line.split()
        if len(p)>=5 and p[2]=="completed": d[p[1]]=(p[3].upper(), p[4])
    return d
D,E=load("D"),load("E")
both=[k for k in sorted(E) if k in D]
print("paired items:",len(both))
print("strict pass  D:",sum(D[k][0]=="PASS" for k in both),"| E:",sum(E[k][0]=="PASS" for k in both))
print("stale-call hits  D:",sum(D[k][1]=="True" for k in both),"| E:",sum(E[k][1]=="True" for k in both))
for k in both:
    if D[k]!=E[k]: print(" ",k,"D",D[k],"-> E",E[k])
PY
grep -E "strict pass|must_not" /tmp/score_D.txt
