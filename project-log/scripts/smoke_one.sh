#!/usr/bin/env bash
# Smoke test: start the stock FDB-v3 agent, stream ONE recording through LiveKit,
# score it, stop the agent. Usage: smoke_one.sh <provider> [example_folder_index]
set -uo pipefail
PROVIDER=${1:-gemini3_1}
IDX=${2:-1}
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_smoke_${PROVIDER}
mkdir -p "$OUT"

FOLDER=$(ls -d fdb_v3_data_released/*/ | sed -n "${IDX}p")
EXAMPLE=$(basename "$FOLDER" | sed -E 's/_[0-9a-f]{24}$//')
echo "example: $EXAMPLE  (folder $(basename "$FOLDER"))"

rm -f /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log
LK_PROVIDER=$PROVIDER python ${AGENT_SCRIPT:-lk_agent_tool.py} start > "$OUT/agent.log" 2>&1 &
AGENT=$!
sleep 15
python run_tool_benchmark.py --provider "$PROVIDER" --example "$EXAMPLE" --force > "$OUT/inference.log" 2>&1
echo "inference exit: $?"
kill $AGENT 2>/dev/null; sleep 2; kill -9 $AGENT 2>/dev/null

cp /tmp/agent_tool_calls.log "$OUT/" 2>/dev/null
R=$(ls "$FOLDER"result_${PROVIDER}.json 2>/dev/null)
if [ -n "$R" ]; then
  cp "$R" "$OUT/result.json"
  python - "$R" <<'PY'
import json, sys
r = json.load(open(sys.argv[1]))
print("status:", r.get("status"))
print("tool calls made:", [c.get("function") for c in r.get("actual_tool_calls", [])])
print("first speech (s):", r.get("latency", {}).get("first_speech_s"), "| perceived latency:", r.get("perceived_total_latency"))
print("agent said (chars):", len(r.get("transcript", "")))
PY
else
  echo "no result file"; tail -20 "$OUT/inference.log"; echo "--- agent log:"; tail -20 "$OUT/agent.log"
fi
echo "logs in $OUT"
