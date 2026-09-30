#!/usr/bin/env bash
date '+%H:%M UTC'
echo "done: $(find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v3st.json' | wc -l)/100"
python3 - <<'PY'
import json
ps=[];ex=[]
for l in open('/tmp/gate_events.log'):
    for e in json.loads(l).get('events',[]):
        if e['kind']=='smart_turn' and e.get('p_complete') is not None: ps.append(e['p_complete'])
        if e['kind']=='execute': ex.append(e['held_s'])
import statistics as s
if ps: print(f"smart_turn verdicts: {len(ps)}  finished(p>=0.5): {sum(p>=0.5 for p in ps)}  not finished: {sum(p<0.5 for p in ps)}")
if ex: print(f"executed calls: {len(ex)}  median hold {s.median(ex):.2f}s")
PY
