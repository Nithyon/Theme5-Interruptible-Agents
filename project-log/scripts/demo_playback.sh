#!/usr/bin/env bash
# Replay a recorded practice run end to end (sound + what ran). Usage: demo_playback.sh <1|2|3>
source /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/audio_env.sh
source ~/theme5/fdb-env/bin/activate
python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_playback.py "${1:-1}"
