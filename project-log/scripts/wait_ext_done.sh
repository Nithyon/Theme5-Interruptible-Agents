#!/usr/bin/env bash
# Wait (up to ~5 min) until no extension end-to-end run is in progress.
for i in $(seq 1 60); do
  pgrep -f 'ext_e2e.sh|ext_e2e_rerun.sh|ext_agent.py start|run_tool_benchmark_all_released.py --provider ext_' > /dev/null || break
  sleep 5
done
date -u '+%H:%M:%S UTC'; pgrep -af 'ext_e2e|ext_agent.py start|run_tool_benchmark' | cut -c1-90 | head -3
echo "home rerun folder: $(ls /mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_ext_home_e2e 2>/dev/null | tr '\n' ' ')"
