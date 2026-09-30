#!/usr/bin/env bash
# Demo 1: talk to the benchmark pipeline (commit gate) with the laptop mic. Ctrl+C to stop,
# then show the gate's decisions with: bash project-log/scripts/demo_show_log.sh
source /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/audio_env.sh
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
set -a; source .env.local; set +a
export GATE_COMBINE=either GATE_JEV=1 GATE_DRAFT_HOLD_S=2.5 GATE_DANGLING=1 GATE_PROMPT=2 GATE_QUIET_S=0.9 GATE_HESITANT_QUIET_S=1.8 GATE_LEAN=1
# the rest of the submitted run's settings (2026-09-30_full_gate_gemini38_v2b)
export GATE_RETRACT=1 GATE_ID_NORMALIZE=1 GATE_BACKCHANNEL=1 GATE_SMART_TURN=0
export GATE_LOG_DIR=/tmp/demo; mkdir -p /tmp/demo; rm -f /tmp/demo/gate_events.log /tmp/demo/gate_stats.log
LK_PROVIDER=gate_gemini38_demo python /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py console "$@"
