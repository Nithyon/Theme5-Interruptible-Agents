#!/usr/bin/env bash
# Build the in-car clip (local text-to-speech), then run the in-car EV assistant end to end on it.
source ~/theme5/tts-env/bin/activate
python /mnt/d/Theme5-Interruptible-Agents/extension/e2e/make_clip_car.py 2>&1 | grep "^wrote"
deactivate
bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/ext_e2e_car.sh
