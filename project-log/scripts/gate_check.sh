#!/usr/bin/env bash
L=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_full_gate_gemini38/agent.log
~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/our_calls.py gate_gemini38 | tail -2
echo "--- most common agent log messages:"
grep -oE '"message": "[^"]{0,80}' "$L" | sed 's/[0-9a-f]\{8,\}//g' | sort | uniq -c | sort -rn | head -15
