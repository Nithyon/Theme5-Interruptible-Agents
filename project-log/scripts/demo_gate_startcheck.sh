#!/usr/bin/env bash
timeout 25 bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_gate.sh < /dev/null > /tmp/demo_start.log 2>&1
sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' /tmp/demo_start.log | tr -d '\n' | grep -o 'Error[^"]\{0,300\}' | head -5
echo; echo "== run E:"; tail -1 /tmp/dev_e.out; grep -c "job crashed\|Traceback" /mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_dev_dev_gate_gemini38_E/agent.log
echo "== repro:"; tail -3 /tmp/repro_setup.log
