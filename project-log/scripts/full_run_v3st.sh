#!/usr/bin/env bash
# Full 100-recording FDB-v3 run: config v2 + Smart Turn (acoustic decider) ON, then strict + Gemini-judge scoring.
# SMOKE=1: one recording only, to check the audio tap and Smart Turn verdicts live.
export GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 GATE_QUIET_S=0.9 GATE_HESITANT_QUIET_S=1.8 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_SMART_TURN=1
rm -f /tmp/gate_stats.log /tmp/gate_events.log
if [ "${SMOKE:-0}" = "1" ]; then
  AGENT_SCRIPT=/mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/smoke_one.sh gate_gemini38_v3st_smoke 1 | tail -15
  echo "smart_turn events: $(grep -c smart_turn /tmp/gate_events.log)"; grep smart_turn /tmp/gate_events.log | head -8
  cat /tmp/gate_stats.log | tail -2 | cut -c1-600
  grep -i "smart turn\|smart_turn\|Traceback\|Error" /mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_smoke_gate_gemini38_v3st_smoke/agent.log | head -8
  exit 0
fi
P=gate_gemini38_v3st
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/run_baseline.sh "$P" /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_full_$P
cp /tmp/gate_stats.log /tmp/gate_events.log "$R/" 2>/dev/null
echo "config V3ST (= v2 + Smart Turn v3.2 acoustic decider ON): GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 quiet 0.9/1.8 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_SMART_TURN=1" >> "$R/run.txt"
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/judge_score.sh "$P" "$R" | tee "$R/score_geminijudge.txt"
