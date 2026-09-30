#!/usr/bin/env bash
# Full 100-recording FDB-v3 run with configuration C, then strict + Gemini-judge scoring.
export GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 GATE_QUIET_S=0.9 GATE_HESITANT_QUIET_S=1.8 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_SMART_TURN=0
P=gate_gemini38_v2
rm -f /tmp/gate_stats.log /tmp/gate_events.log
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/run_baseline.sh "$P" /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_$P
cp /tmp/gate_stats.log /tmp/gate_events.log "$R/" 2>/dev/null
echo "config V2 (final config + lean gate + backchannel + retraction + ID rule; Smart Turn off): GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 quiet 0.9/1.8 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_SMART_TURN=0" >> "$R/run.txt"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_score.sh "$P" "$R" | tee "$R/score_geminijudge.txt"
