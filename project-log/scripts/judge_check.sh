#!/usr/bin/env bash
# Read-only: is the judge for run v2b making progress? (sizes, times and counts only; no log content)
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
A=$R/2026-09-30_full_gate_gemini38_v3st/gate_gemini38_v3st_eval_geminijudge.log
B=$R/2026-09-30_full_gate_gemini38_v2b/gate_gemini38_v2b_eval_geminijudge.log
date -u '+now %H:%M:%S UTC'
ps -eo pid,etime,pcpu,args | grep '[j]udge_vertex' | cut -c1-110
for f in "$A" "$B"; do echo "$(basename $f): $(wc -l < $f) lines, $(stat -c %s $f) bytes, last written $(date -u -d @$(stat -c %Y $f) +%H:%M:%S) UTC"; done
echo "JUDGE lines in v2b log: $(grep -c '^JUDGE' $B)"
s1=$(stat -c %s "$B"); sleep 20; s2=$(stat -c %s "$B")
echo "v2b log grew by $((s2 - s1)) bytes in 20 s"
echo "report file written: $(ls $R/2026-09-30_full_gate_gemini38_v2b/ | grep -c 'pass_rate_report_geminijudge')"
