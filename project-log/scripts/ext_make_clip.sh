#!/usr/bin/env bash
# Synthesize the home-assistant request clip (Kokoro, local CPU).
source ~/theme5/tts-env/bin/activate
python /mnt/d/Theme5-Interruptible-Agents/extension/e2e/make_clip.py 2>&1 | grep -v "Warning\|warn" | tail -5
ls -la /mnt/d/Theme5-Interruptible-Agents/extension/e2e/audio/*/ | awk '{print $5, $9}'
