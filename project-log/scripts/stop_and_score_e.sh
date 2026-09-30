#!/usr/bin/env bash
# Stop practice run E early and compare its finished items with run D (yesterday's final config) on the same items.
pkill -f run_dev.sh; pkill -f dev_ab.sh; pkill -f run_tool_benchmark; pkill -f livekit_inference; pkill -f gate_agent.py; sleep 3
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_dev_dev_gate_gemini38_E
echo "stopped early at $(date) with $(ls /mnt/d/Theme5-Interruptible-Agents/devset/audio/*/result_dev_gate_gemini38_E.json | wc -l)/62 items; gate logs for the first ~23 rooms were lost (a demo start check deleted /tmp/gate_*.log mid-run) and one room hit an agent assignment timeout at 11:30 UTC" >> "$R/run.txt"
cp /tmp/gate_stats.log /tmp/gate_events.log "$R/" 2>/dev/null
cd /mnt/d/Theme5-Interruptible-Agents/devset
for L in D E; do ~/theme5/fdb-env/bin/python score_dev.py --provider dev_gate_gemini38_$L > /tmp/score_$L.txt 2>&1; done
cp /tmp/score_E.txt "$R/score_partial.txt"
python3 - <<'PY'
import re
def load(L):
    d={}
    for line in open(f"/tmp/score_{L}.txt"):
        m=re.match(r"^([sp]\d+)_\S*\s+(PASS|FAIL)(.*)", line)
        if m: d[m.group(1)]=(m.group(2), m.group(3).strip()[:60])
    return d
D,E=load("D"),load("E")
both=[k for k in sorted(E) if k in D]
print("items in E:",len(E),"| paired with D:",len(both))
print("D pass on these:",sum(D[k][0]=="PASS" for k in both),"| E pass:",sum(E[k][0]=="PASS" for k in both))
for k in both:
    if D[k][0]!=E[k][0]: print(" ",k,"D",D[k][0],"-> E",E[k][0],"|",E[k][1])
PY
grep -E "strict pass|must_not" /tmp/score_E.txt | head -4; sed -n '1,6p' /tmp/score_E.txt
