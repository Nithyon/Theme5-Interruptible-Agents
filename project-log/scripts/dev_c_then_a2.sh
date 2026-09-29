#!/usr/bin/env bash
# Padded dev set: C (everything) then A2 (run A's settings), sequentially.
S=/mnt/d/Theme5-Interruptible-Agents/project-log/scripts/dev_ab.sh
GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 bash $S C 0.9 1.8 2
GATE_JEV=0 GATE_DRAFT_HOLD_S=0 GATE_DANGLING=0 bash $S A2 0.9 1.8 1
