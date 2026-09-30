#!/usr/bin/env bash
# Read-only: wait (up to ~9 min) for a judged score file to fill in, then print both runs' score files.
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
A=$R/2026-09-30_full_gate_gemini38_v3st/score_geminijudge.txt; B=$R/2026-09-30_full_gate_gemini38_v2b/score_geminijudge.txt
sa=$(stat -c %s "$A" 2>/dev/null || echo 0); sb=$(stat -c %s "$B" 2>/dev/null || echo 0)
for i in $(seq 1 54); do
  na=$(stat -c %s "$A" 2>/dev/null || echo 0); nb=$(stat -c %s "$B" 2>/dev/null || echo 0)
  { [ "$na" != "$sa" ] || [ "$nb" != "$sb" ]; } && { sleep 15; break; }
  sleep 10
done
date -u '+%H:%M UTC'
for d in 2026-09-30_full_gate_gemini38_v3st 2026-09-30_full_gate_gemini38_v2b; do
  echo "== $d"; tail -1 $R/$d/run.txt | cut -c1-80
  for f in score.txt score_geminijudge.txt; do [ -s $R/$d/$f ] && { echo "-- $f:"; grep -v '^by_difficulty\|^by_state' $R/$d/$f | cut -c1-330 | head -7; } || echo "-- $f: not written yet"; done
done
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh | grep 'v3st:\|v2b:'
pgrep -af 'judge_vertex' | cut -c1-90
