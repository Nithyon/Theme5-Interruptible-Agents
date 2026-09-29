#!/usr/bin/env bash
# One dev-set run of the gate agent with given gate settings, then score it.
# Usage: dev_ab.sh <label> <quiet_s> <hesitant_quiet_s> [prompt 1|0]
L=${1:?label}; Q=${2:-0.9}; H=${3:-1.8}; PR=${4:-1}
export GATE_QUIET_S=$Q GATE_HESITANT_QUIET_S=$H GATE_PROMPT=$PR
rm -f /tmp/gate_stats.log /tmp/gate_events.log
P=dev_gate_gemini38_$L
bash /mnt/d/Theme5-Interruptible-Agents/devset/run_dev.sh "$P" /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py
OUT=/mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_dev_$P
cp /tmp/gate_stats.log /tmp/gate_events.log "$OUT/" 2>/dev/null
echo "settings: quiet=$Q hesitant=$H prompt=$PR" >> "$OUT/run.txt"
~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/devset/score_dev.py --help >/dev/null 2>&1
