#!/usr/bin/env bash
# Read-only: which LiveKit plugins can be imported in the benchmark environment?
~/theme5/fdb-env/bin/python - <<'PY'
import importlib
for m in ("livekit.plugins.silero", "livekit.plugins.openai", "livekit.plugins.google", "livekit.plugins.turn_detector", "livekit.plugins.deepgram", "livekit.plugins.elevenlabs", "google.cloud.speech", "google.cloud.texttospeech"):
    try:
        importlib.import_module(m); print("available:", m)
    except Exception as e:
        print("MISSING  :", m, "-", type(e).__name__)
PY
