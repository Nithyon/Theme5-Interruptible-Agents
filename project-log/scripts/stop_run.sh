#!/usr/bin/env bash
# Stop any running benchmark + agent and save gate logs into a run folder. Usage: stop_run.sh <run_dir> <note>
R=${1:?run dir}; NOTE=${2:-stopped}
pkill -f run_baseline.sh; pkill -f run_tool_benchmark_all_released; pkill -f livekit_inference
pkill -f gate_agent.py; pkill -f baseline_agent.py; sleep 3
echo "still running: $(pgrep -fc 'run_tool_benchmark|livekit_inference|gate_agent|baseline_agent')"
cp /tmp/gate_stats.log /tmp/agent_tool_calls.log "$R/" 2>/dev/null
echo "$NOTE at $(date -u)" >> "$R/run.txt"
