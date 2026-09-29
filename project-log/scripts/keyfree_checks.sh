#!/usr/bin/env bash
# Checks that need no API keys: templates import on the installed LiveKit, and the
# scoring ASR (NVIDIA Parakeet) loads on the GPU. Transcribes only a synthetic tone
# file, never a benchmark recording, so no test content is read.
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
echo "=== template import (livekit-agents $(python -c 'import livekit.agents as a; print(a.__version__)'))"
for f in lk_agent_tool cascaded_agent; do
  python - "$f" <<'PY' 2>&1 | tail -3
import importlib, sys
name = sys.argv[1]
sys.argv = [name + ".py"]
try:
    m = importlib.import_module(name)
    tools = [n for n in dir(m.AssistantFnc) if not n.startswith("_") and n != "log_tool_call"]
    print(f"{name}: import ok, {len(tools)} tools")
except Exception as e:
    print(f"{name}: IMPORT FAILED: {type(e).__name__}: {e}")
PY
done
echo "=== Parakeet ASR on GPU"
python - <<'PY' 2>&1 | grep -vE "^\[NeMo W|warnings.warn|^ +" | tail -6
import time, numpy as np, wave, torch
t = time.time()
import nemo.collections.asr as nemo_asr
m = nemo_asr.models.ASRModel.from_pretrained(model_name="nvidia/parakeet-tdt-0.6b-v2").cuda()
print(f"model loaded in {time.time()-t:.0f}s on", next(m.parameters()).device)
sr = 16000
x = (0.1 * np.sin(2 * np.pi * 440 * np.arange(sr * 2) / sr) * 32767).astype(np.int16)
with wave.open("/tmp/tone.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(x.tobytes())
out = m.transcribe(["/tmp/tone.wav"], timestamps=True)
print("transcribe ok:", type(out[0]).__name__, "| gpu mem used", round(torch.cuda.max_memory_allocated() / 2**30, 2), "GB")
PY
