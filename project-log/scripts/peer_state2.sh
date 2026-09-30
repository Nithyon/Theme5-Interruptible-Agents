#!/usr/bin/env bash
# Read-only: current state of the other session's Smart Turn runs.
date -u '+now %H:%M:%S UTC'
echo "== processes:"; pgrep -af 'gate_agent.py|run_tool_benchmark|livekit_inference|full_run_v|smoke_one|run_baseline' | cut -c1-140
D=~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released
echo "== results: v3st $(find $D -name 'result_gate_gemini38_v3st.json' | wc -l)/100 | smoke $(find $D -name 'result_gate_gemini38_v3st_smoke.json' | wc -l)"
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
for d in $R/2026-09-30_smoke_gate_gemini38_v3st_smoke $R/2026-09-30_full_gate_gemini38_v3st; do
  [ -d "$d" ] || { echo "== $(basename $d): (no folder)"; continue; }
  echo "== $(basename $d): files: $(ls $d | tr '\n' ' ')"
  [ -f $d/run.txt ] && cut -c1-200 $d/run.txt
  echo "   agent.log: registered worker=$(grep -c 'registered worker' $d/agent.log) | worker failed=$(grep -c 'worker failed' $d/agent.log) | 'Smart Turn disabled'=$(grep -ci 'smart turn disabled' $d/agent.log) | tracebacks=$(grep -c '^Traceback' $d/agent.log) | jobs received=$(grep -c 'received job request' $d/agent.log | head -1)"
  grep -i 'smart turn\|smart_turn\|feed_from_room\|AudioStream\|track_subscribed' $d/agent.log | cut -c1-200 | head -5
done
echo "== live gate logs in /tmp:"
for f in /tmp/gate_events.log /tmp/gate_stats.log; do [ -f $f ] && echo "$f: $(wc -l < $f) rooms, smart_turn mentions $(grep -o 'smart_turn' $f | wc -l)"; done
python3 - <<'PY'
import json, os
f = "/tmp/gate_events.log"
if os.path.exists(f):
    ps, holds = [], []
    for line in open(f):
        try: ev = json.loads(line)["events"]
        except Exception: continue
        ps += [e.get("p_complete") for e in ev if e.get("kind") == "smart_turn"]
        holds += [e.get("held_s") for e in ev if e.get("kind") == "execute"]
    real = [p for p in ps if p is not None]
    print(f"smart_turn verdicts: {len(ps)} (None: {len(ps)-len(real)}) | p<0.5 ('not finished'): {sum(p < 0.5 for p in real)} | executed calls: {len(holds)}, median hold {sorted(holds)[len(holds)//2] if holds else None}")
f = "/tmp/gate_stats.log"
if os.path.exists(f):
    for line in open(f).read().splitlines()[-2:]:
        d = json.loads(line); print("stats:", {k: d.get(k) for k in ("room", "proposed", "executed", "superseded", "smart_turn")})
PY
echo "== /tmp/full_v3st.out tail:"; tail -4 /tmp/full_v3st.out 2>/dev/null | cut -c1-220
