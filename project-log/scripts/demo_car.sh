#!/usr/bin/env bash
# Demo 2: talk to the extension agent. Usage: demo_car.sh [car|home]
source /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/audio_env.sh
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
rm -f /tmp/ext_recovery_events.log
EXT_PACK=${1:-car} EXT_SEED=0 LK_PROVIDER=ext_gemini38 python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py console
