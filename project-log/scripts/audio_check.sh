#!/usr/bin/env bash
source /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/audio_env.sh
source ~/theme5/fdb-env/bin/activate
python - <<'PY'
import sounddevice as sd, numpy as np
print(sd.query_devices())
try:
    r = sd.rec(int(0.5*16000), samplerate=16000, channels=1, dtype="int16"); sd.wait()
    print("mic capture ok, peak", int(np.abs(r).max()))
    sd.play(np.zeros(8000, dtype="int16"), 16000); sd.wait(); print("speaker ok")
except Exception as e:
    print("audio error:", type(e).__name__, e)
PY
