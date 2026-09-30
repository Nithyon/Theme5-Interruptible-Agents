#!/usr/bin/env bash
# Smart Turn smoke test: load the model, time it, and try it on two practice clips cut at a
# mid-sentence point vs the full sentence (TTS audio: a sanity check, not a validation).
source ~/theme5/fdb-env/bin/activate
cd /mnt/d/Theme5-Interruptible-Agents/fdb_agent
python - <<'PY'
import time, glob, numpy as np, soundfile as sf
from smart_turn import SmartTurn, SR
m = SmartTurn()
x = np.random.randn(SR*3).astype(np.float32)*0.01
m.predict(x); t=time.monotonic(); [m.predict(x) for _ in range(5)]; print("ms per call:", round((time.monotonic()-t)/5*1000,1))
files = sorted(glob.glob("/mnt/d/Theme5-Interruptible-Agents/devset/audio/*/input.wav"))[:4] or sorted(glob.glob("/mnt/d/Theme5-Interruptible-Agents/devset/audio/**/*.wav", recursive=True))[:4]
for f in files:
    a, sr = sf.read(f, dtype="float32")
    if a.ndim > 1: a = a[:,0]
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr/SR), np.arange(len(a)), a).astype(np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]
    end = nz[-1] if len(nz) else len(a)
    mid = int(end*0.5)
    print(f.split("/")[-2], "cut mid-sentence p(complete)=%.2f" % m.predict(a[:mid]), " full sentence+0.3s p(complete)=%.2f" % m.predict(a[:end+int(0.3*SR)]))
PY
