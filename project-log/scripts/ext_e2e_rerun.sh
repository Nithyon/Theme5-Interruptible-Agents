#!/usr/bin/env bash
# Rebuild the clip, keep the first attempt's folder, and run the home assistant end to end again.
R=/mnt/d/Theme5-Interruptible-Agents/project-log/runs
[ -d $R/$(date +%F)_ext_home_e2e ] && [ ! -d $R/$(date +%F)_ext_home_e2e_attempt1 ] && mv $R/$(date +%F)_ext_home_e2e $R/$(date +%F)_ext_home_e2e_attempt1
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/ext_make_clip.sh | tail -3
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/ext_e2e.sh
