#!/usr/bin/env bash
# Make sure nothing from an earlier run is alive and port 8081 is free, then smoke-test Smart Turn live.
for pat in 'gate_agent[.]py' 'run_tool_benchmark' 'livekit_inference'; do pkill -f "$pat"; done
sleep 4
echo "left: $(pgrep -fc 'gate_agent[.]py|run_tool_benchmark|livekit_inference')  port8081 listeners: $(ss -ltn | grep -c ':8081 ')"
SMOKE=1 bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/full_run_v3st.sh
echo "registered: $(grep -c 'registered worker' /mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_smoke_gate_gemini38_v3st_smoke/agent.log)"
