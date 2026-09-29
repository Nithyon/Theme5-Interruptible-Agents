#!/usr/bin/env bash
# Kokoro TTS in its own env (keeps fdb-env untouched). Log: ~/theme5/setup_tts.log
set -e
command -v espeak-ng >/dev/null || echo "NOTE: espeak-ng not installed (sudo apt install espeak-ng) - English usually works without it"
cd ~/theme5
[ -d tts-env ] || ~/.local/bin/uv venv tts-env --python 3.11 2>/dev/null || python3 -m venv tts-env
source tts-env/bin/activate
if command -v uv >/dev/null || [ -x ~/.local/bin/uv ]; then
  ~/.local/bin/uv pip install kokoro soundfile librosa numpy
else
  pip install kokoro soundfile librosa numpy
fi
python -c "import kokoro, soundfile, librosa; print('kokoro ok')"
