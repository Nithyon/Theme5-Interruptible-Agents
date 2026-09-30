#!/usr/bin/env bash
# 1) prove the second project's credentials work, 2) one-recording smoke on it, 3) health of the main run.
LK_ENV_FILE=~/theme5/lk2.env ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/check_livekit2.py 2>&1 | grep -i "livekit"
SMOKE=1 bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/full_run_v2b.sh
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/v3st_progress.sh
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/silent_rooms.sh 2>&1 | grep v3st
