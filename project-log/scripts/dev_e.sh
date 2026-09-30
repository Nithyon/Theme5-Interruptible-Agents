#!/usr/bin/env bash
# Practice run E: final config + lean gate (Jev never lengthens a hold) + backchannel + retraction + ID rule.
export GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/dev_ab.sh E 0.9 1.8 2
echo "config E: GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_LEAN=1 GATE_BACKCHANNEL=1 GATE_RETRACT=1 GATE_ID_NORMALIZE=1" >> /mnt/d/Theme5-Interruptible-Agents/project-log/runs/$(date +%F)_dev_dev_gate_gemini38_E/run.txt
