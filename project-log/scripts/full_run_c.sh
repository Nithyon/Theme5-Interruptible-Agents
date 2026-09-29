#!/usr/bin/env bash
# Full 100-recording FDB-v3 run with configuration C, then strict + Gemini-judge scoring.
export GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 GATE_QUIET_S=0.9 GATE_HESITANT_QUIET_S=1.8
P=gate_gemini38_c
rm -f /tmp/gate_stats.log /tmp/gate_events.log
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/run_baseline.sh "$P" /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_$P
cp /tmp/gate_stats.log /tmp/gate_events.log "$R/" 2>/dev/null
echo "config C: GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 quiet 0.9/1.8" >> "$R/run.txt"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_score.sh "$P" "$R" | tee "$R/score_geminijudge.txt"
