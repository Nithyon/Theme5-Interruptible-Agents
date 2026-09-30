#!/usr/bin/env bash
# Stop anything running, then start practice run E detached (survives the calling shell).
pkill -f run_dev.sh; pkill -f dev_ab.sh; pkill -f run_tool_benchmark; pkill -f livekit_inference; pkill -f gate_agent.py
sleep 3
nohup setsid bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/dev_e.sh > /tmp/dev_e.out 2>&1 < /dev/null &
sleep 10
pgrep -af 'gate_agent|run_dev|livekit_inference' | head -5
tail -3 /tmp/dev_e.out
