#!/usr/bin/env bash
# Full FDB-v3 run: start an agent, stream all 100 recordings, stop the agent, save logs.
# Usage: run_baseline.sh <provider> <agent_script>   (e.g. gemini3_8 /mnt/d/.../baseline_agent.py)
set -uo pipefail
PROVIDER=${1:-gemini3_8}
AGENT_SCRIPT=${2:-/mnt/d/Theme5-Interruptible-Agents/fdb_agent/baseline_agent.py}
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_${PROVIDER}
mkdir -p "$OUT"
rm -f /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log
echo "start $(date)" > "$OUT/run.txt"
LK_PROVIDER=$PROVIDER python "$AGENT_SCRIPT" start > "$OUT/agent.log" 2>&1 &
AGENT=$!
sleep 20
python run_tool_benchmark_all_released.py --provider "$PROVIDER" --force > "$OUT/inference.log" 2>&1
echo "inference exit $? at $(date)" >> "$OUT/run.txt"
kill $AGENT 2>/dev/null; sleep 3; kill -9 $AGENT 2>/dev/null
cp /tmp/agent_tool_calls.log /tmp/agent_heartbeat.log "$OUT/" 2>/dev/null
cp fdb_v3_data_released/evaluation_summary_${PROVIDER}.json "$OUT/" 2>/dev/null
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/score_summary.sh "$PROVIDER" "$OUT" | tee "$OUT/score.txt"
echo "done $(date)" >> "$OUT/run.txt"
