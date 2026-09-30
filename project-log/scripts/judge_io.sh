#!/usr/bin/env bash
# Read-only: is the judge process exchanging data? Sample its I/O counters twice, 20 s apart.
P=$(pgrep -f 'judge_vertex.py' | head -1)
[ -z "$P" ] && { echo "no judge process running"; ls -la /mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2b/score_geminijudge.txt; exit 0; }
a=$(grep -E '^(rchar|wchar|syscr|syscw)' /proc/$P/io | tr '\n' ' '); t1=$(ps -o time= -p $P)
sleep 20
b=$(grep -E '^(rchar|wchar|syscr|syscw)' /proc/$P/io | tr '\n' ' '); t2=$(ps -o time= -p $P)
echo "pid $P elapsed $(ps -o etime= -p $P)"
echo "before: $a cpu $t1"; echo "after : $b cpu $t2"
