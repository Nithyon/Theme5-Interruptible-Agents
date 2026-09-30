#!/usr/bin/env bash
nohup setsid bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/full_run_v2.sh > /tmp/full_v2.out 2>&1 < /dev/null &
sleep 45; pgrep -af 'gate_agent.py start' | head -2; ls ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released/*/result_gate_gemini38_v2.json 2>/dev/null | wc -l; tail -2 /tmp/full_v2.out
