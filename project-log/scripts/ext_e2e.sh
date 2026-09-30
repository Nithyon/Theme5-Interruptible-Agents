#!/usr/bin/env bash
# Run the home assistant end to end on the recorded clip: start the extension agent, stream the
# clip into a LiveKit room with the benchmark's own runner, save the agent's audio and logs.
# Does not touch /tmp/agent_tool_calls.log, /tmp/agent_heartbeat.log or /tmp/gate_*.log.
set -uo pipefail
P=ext_home_e2e
A=/mnt/d/Theme5-Interruptible-Agents/extension/e2e/audio
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_$P
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local; set +a
mkdir -p "$OUT"; rm -f /tmp/ext_recovery_events.log
echo "start $(date -u)" > "$OUT/run.txt"
echo "EXT_PACK=home EXT_SEED=0 provider=$P clip=$(ls $A)" >> "$OUT/run.txt"
EXT_PACK=home EXT_SEED=0 LK_PROVIDER=$P python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py start > "$OUT/agent.log" 2>&1 &
AGENT=$!
sleep 20
python run_tool_benchmark_all_released.py --provider "$P" --root_dir "$A" --force > "$OUT/inference.log" 2>&1
echo "inference exit $? at $(date -u)" >> "$OUT/run.txt"
sleep 6; kill $AGENT 2>/dev/null; sleep 4; kill -9 $AGENT 2>/dev/null
cp /tmp/ext_recovery_events.log "$OUT/" 2>/dev/null
F=$(ls -d $A/*/ | head -1)
cp "$F"result_$P.json "$OUT/result.json" 2>/dev/null; cp "$F"output_$P.wav "$OUT/agent_reply.wav" 2>/dev/null; cp "$F"metadata.json "$OUT/" 2>/dev/null
echo "== files: $(ls $OUT | tr '\n' ' ')"
echo "== agent log: registered worker $(grep -c 'registered worker' $OUT/agent.log) | errors $(grep -c '"level": "ERROR"' $OUT/agent.log) | tracebacks $(grep -c '^Traceback' $OUT/agent.log)"
python - "$OUT" <<'PY'
import json, os, sys
o = sys.argv[1]
p = os.path.join(o, "result.json")
if os.path.exists(p):
    r = json.load(open(p)); print("status:", r.get("status")); print("agent said:", (r.get("transcript") or "")[:700])
else: print("NO result file")
p = os.path.join(o, "ext_recovery_events.log")
if os.path.exists(p):
    print("recovery events:")
    for line in open(p):
        try: e = json.loads(line)
        except ValueError: continue
        print("  ", e.get("kind"), {k: v for k, v in e.items() if k not in ("kind", "seq", "t", "ts") and v not in (None, "", {}, [])})
else: print("NO recovery log")
PY
