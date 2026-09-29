#!/usr/bin/env bash
# Progress of a running FDB-v3 run. Usage: progress.sh <provider>
P=${1:-gemini3_8}
D=~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released
echo "outputs: $(ls $D/*/output_$P.wav 2>/dev/null | wc -l)/100  results: $(ls $D/*/result_$P.json 2>/dev/null | wc -l)/100"
echo "tool calls logged: $( [ -f /tmp/agent_tool_calls.log ] && wc -l < /tmp/agent_tool_calls.log || echo 0)"
echo "processes: $(pgrep -fc 'run_tool_benchmark|livekit_inference|baseline_agent|gate_agent')"
echo "now (UTC): $(date -u +%H:%M:%S)  last result written: $(ls -t $D/*/result_$P.json 2>/dev/null | head -1 | xargs -r stat -c %y | cut -c12-19)"
