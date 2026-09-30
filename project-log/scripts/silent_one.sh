#!/usr/bin/env bash
# Read-only: when did the silent recording in run v3st happen, and what did the logs show around it?
python3 - <<'PY'
import json, os, glob
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
for prov in ("gate_gemini38_v3st", "gate_gemini38_v2b"):
    rows = []
    for f in sorted(os.listdir(D)):
        p = os.path.join(D, f, f"result_{prov}.json")
        if os.path.exists(p):
            r = json.load(open(p)); rows.append((r.get("evaluated_at", ""), f[:16], bool((r.get("transcript") or "").strip()), len(r.get("actual_tool_calls") or []), r.get("room_name"), r.get("inference_time_s")))
    rows.sort()
    print(prov, "- last 6 finished (UTC time, recording, agent spoke, calls, room):")
    for x in rows[-6:]: print("   ", x[0][11:19], x[1], "spoke" if x[2] else "SILENT", x[3], x[4], x[5])
    for x in rows:
        if not x[2] and x[3] == 0: print("   silent:", x)
PY
L=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v3st/agent.log
echo "== v3st agent.log per minute (UTC): warnings / cgroup-load warnings / errors"
for m in 04 05 06 07 08 09 10 11; do echo "  13:$m  $(grep "T13:$m:" $L | grep -c '"level": "WARNING"') / $(grep "T13:$m:" $L | grep -c 'impossible cgroup') / $(grep "T13:$m:" $L | grep -c '"level": "ERROR"')"; done
echo "== distinct WARNING/ERROR messages 13:06-13:10:"
grep 'T13:0[6789]:\|T13:10:' $L | grep '"level": "WARNING"\|"level": "ERROR"' | grep -o '"message": "[^"]\{0,100\}' | sed 's/[0-9]\{3,\}ms/Nms/;s/[0-9.]\{5,\}s/Ns/g' | sort | uniq -c | sort -rn | head -6
echo "== my own scoring runs (files in /tmp/demo, UTC):"; ls -la --time-style=+%H:%M:%S /tmp/demo/common_gate_gemini38_v3st.json | awk '{print $6, $7}'
