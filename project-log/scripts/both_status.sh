#!/usr/bin/env bash
# Status of the two parallel full runs (v3st: Smart Turn on, main project; v2b: Smart Turn off, second project).
D=~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released
RB=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_gate_gemini38_v2b
date '+%H:%M UTC'
echo "v3st results: $(find $D -name 'result_gate_gemini38_v3st.json' | wc -l)/100"
echo "v2b  results: $(find $D -name 'result_gate_gemini38_v2b.json' -newer $RB/run.txt | wc -l)/100   registered: $(grep -c 'registered worker' $RB/agent.log)  bind errors: $(grep -c 'address already in use' $RB/agent.log)"
echo "agent processes: $(pgrep -f 'gate_agent[.]py start' | wc -l) main, $(pgrep -f 'gate_agent_b[.]py start' | wc -l) second"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh 2>/dev/null | grep 'v3st\|v2b'
echo "load: $(cut -d' ' -f1-3 /proc/loadavg)"
tail -2 /tmp/full_v2b.out 2>/dev/null | cut -c1-200
