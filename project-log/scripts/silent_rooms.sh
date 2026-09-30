#!/usr/bin/env bash
# Read-only. (1) What does v2's agent log say during the three silent finance rooms (12:06-12:08:30 UTC)?
# (2) Silent-recording check for any run: results where the agent said nothing and called nothing.
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
L=$R/2026-09-30_full_gate_gemini38_v2/agent.log
echo "== v2 agent.log, warnings/errors by minute (UTC) 12:03-12:10:"
for m in 03 04 05 06 07 08 09 10; do
  w=$(grep "T12:$m:" $L | grep -c '"level": "WARNING"'); e=$(grep "T12:$m:" $L | grep -c '"level": "ERROR"')
  b=$(grep "T12:$m:" $L | grep -o 'event loop blocked for [0-9]*ms' | grep -o '[0-9]*' | sort -n | tail -1)
  echo "  12:$m  warnings=$w errors=$e  longest loop block=${b:-0}ms"
done
echo "== earlier baseline, same log, 11:40-11:45:"
for m in 40 41 42 43 44 45; do
  b=$(grep "T11:$m:" $L | grep -o 'event loop blocked for [0-9]*ms' | grep -o '[0-9]*' | sort -n | tail -1)
  echo "  11:$m  warnings=$(grep "T11:$m:" $L | grep -c '"level": "WARNING"')  longest loop block=${b:-0}ms"
done
echo "== distinct warning/error messages 12:06-12:08 (trimmed):"
grep 'T12:0[678]:' $L | grep '"level": "WARNING"\|"level": "ERROR"' | grep -o '"message": "[^"]\{0,110\}' | sed 's/[0-9]\{3,\}ms/Nms/' | sort | uniq -c | sort -rn | head -8
python3 - <<'PY'
import json, os
D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
print("== silent recordings (agent transcript empty AND no tool call), per run:")
for prov in ("gemini3_8", "gate_gemini38_final", "gate_gemini38_v2", "gate_gemini38_v3st"):
    tot = sil = 0; names = []
    for f in sorted(os.listdir(D)):
        p = os.path.join(D, f, f"result_{prov}.json")
        if not os.path.exists(p): continue
        r = json.load(open(p)); tot += 1
        if not (r.get("transcript") or "").strip() and not (r.get("actual_tool_calls") or []):
            sil += 1; names.append(f[:14])
    print(f"  {prov}: {sil} silent of {tot} results", names[:8])
PY
