#!/usr/bin/env bash
echo "port 8082 listeners before: $(ss -ltn | grep -c ':8082 ')"
nohup setsid bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/full_run_v2b.sh > /tmp/full_v2b.out 2>&1 < /dev/null &
sleep 75
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_gate_gemini38_v2b
echo "v2b registered: $(grep -c 'registered worker' $R/agent.log)  bind errors: $(grep -c 'address already in use' $R/agent.log)  results: $(find ~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released -name 'result_gate_gemini38_v2b.json' -newer $R/run.txt | wc -l)"
echo "agents alive: $(pgrep -fc 'gate_agent(_b)?[.]py start')"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/v3st_progress.sh | head -2
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh 2>&1 | grep 'v3st\|v2b'
uptime
