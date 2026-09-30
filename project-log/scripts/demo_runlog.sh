#!/usr/bin/env bash
# Show the evidence kept for one benchmark run. Usage: demo_runlog.sh <run folder name under project-log/runs>
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/${1:?run folder}
echo "=== $1 ==="; echo "--- files kept for this run:"; ls "$R" | tr '\n' ' '; echo
echo "--- settings (run.txt):"; cut -c1-220 "$R/run.txt"
python3 - "$R" <<'PY'
import json, os, sys, glob
R = sys.argv[1]
ev = os.path.join(R, "gate_events.log")
if os.path.exists(ev):
    rooms = [json.loads(l) for l in open(ev) if l.strip()]
    c = {}
    for r in rooms:
        for e in r["events"]: c[e["kind"]] = c.get(e["kind"], 0) + 1
    print(f"--- decision log: {len(rooms)} recordings | proposed {c.get('proposed',0)} | executed {c.get('execute',0)} | replaced {c.get('superseded',0)} | withdrawn {c.get('cancelled',0)} | duplicates blocked {c.get('duplicate',0)}")
per = glob.glob(os.path.join(R, "per_recording", "*.json"))
if per:
    silent = sum(1 for p in per if not (json.load(open(p)).get("transcript") or "").strip() and not json.load(open(p)).get("actual_tool_calls"))
    print(f"--- per-recording result files: {len(per)} | silent recordings: {silent}")
for p in sorted(glob.glob(os.path.join(R, "*pass_rate_report*.json"))):
    r = json.load(open(p))
    print(f"--- {os.path.basename(p)}: passed {r.get('passed')}/{r.get('total_scenarios')} | {r.get('failure_breakdown')}")
PY
