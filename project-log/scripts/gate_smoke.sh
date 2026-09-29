#!/usr/bin/env bash
# Live smoke test of the gate agent on one scenario + what the gate decided.
IDX=${1:-1}
rm -f /tmp/gate_stats.log
AGENT_SCRIPT=/mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py \
  bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/smoke_one.sh gate_gemini38 "$IDX" 2>&1 | grep -v Killed | tail -6
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_smoke_gate_gemini38
echo "--- gate stats:"; cat /tmp/gate_stats.log 2>/dev/null
echo "--- gate decisions:"; grep -hoE 'INFO:commit_gate:[^"]{0,160}' "$OUT/agent.log" | sort -u | head
echo "--- tools actually executed:"; cut -c1-200 "$OUT/agent_tool_calls.log" 2>/dev/null
