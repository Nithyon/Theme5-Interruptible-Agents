#!/usr/bin/env bash
# Read-only: what is running right now, and what state is the v2 final run in?
date -u '+now %H:%M:%S UTC'
echo "== processes:"; pgrep -af 'gate_agent.py|run_tool_benchmark|livekit_inference|full_run_v|smoke_one|run_baseline' | cut -c1-150
echo "== v2 results: $(find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v2.json' | wc -l)/100 | v3st results: $(find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v3st*.json' | wc -l)"
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2
echo "== v2 run.txt:"; cat $R/run.txt | cut -c1-260
echo "== v2 agent.log: assignment timeouts $(grep -c AssignmentTimeoutError $R/agent.log) | last line time: $(tail -1 $R/agent.log | grep -o '"timestamp": "[^"]*"' | tail -1)"
echo "== v2 inference.log tail:"; tail -3 $R/inference.log | cut -c1-200
echo "== /tmp/full_v2.out tail:"; tail -3 /tmp/full_v2.out | cut -c1-200
