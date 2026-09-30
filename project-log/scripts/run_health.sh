#!/usr/bin/env bash
# Read-only health check of the final run (v2). Touches nothing.
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2
echo "results: $(ls ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released/*/result_gate_gemini38_v2.json 2>/dev/null | wc -l)/100"
echo "agent processes: $(pgrep -fc 'gate_agent.py start')"
echo "assignment timeouts: $(grep -c 'AssignmentTimeoutError' $R/agent.log)"
echo "jobs crashed: $(grep -c 'job crashed' $R/agent.log)"
echo "inference log errors: $(grep -ci 'traceback\|error' $R/inference.log)"
echo "ollama running: $(pgrep -fc 'ollama serve')"
date -u '+now %H:%M UTC'
