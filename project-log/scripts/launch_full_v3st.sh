#!/usr/bin/env bash
nohup setsid bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/full_run_v3st.sh > /tmp/full_v3st.out 2>&1 < /dev/null &
sleep 50; pgrep -af 'gate_agent.py start' | head -2; find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v3st.json' | wc -l; tail -2 /tmp/full_v3st.out
