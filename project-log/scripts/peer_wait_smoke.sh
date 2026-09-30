#!/usr/bin/env bash
# Read-only: wait (up to ~110 s) for the other session's smoke run to write its gate logs, then summarize.
for i in $(seq 1 22); do [ -s /tmp/gate_events.log ] && ! pgrep -f 'run_tool_benchmark.py --provider gate_gemini38_v3st_smoke' >/dev/null && break; sleep 5; done
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/peer_state2.sh | sed -n '1,4p;9,40p'
python3 - <<'PY'
import json, os
f = "/tmp/gate_events.log"
if os.path.exists(f):
    for line in open(f):
        ev = json.loads(line)["events"]
        kinds = {}
        for e in ev: kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
        print("room", json.loads(line)["room"], kinds)
        for e in ev:
            if e["kind"] in ("smart_turn", "execute", "proposed"): print("   ", {k: v for k, v in e.items() if k != "t"})
PY
