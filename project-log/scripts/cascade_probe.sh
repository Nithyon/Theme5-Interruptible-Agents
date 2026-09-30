#!/usr/bin/env bash
# Read-only: what do we already have for a speech-to-text -> text model -> text-to-speech agent?
cd ~/theme5/Full-Duplex-Bench/v3
echo "== agent examples shipped with the benchmark:"; ls *.py | grep -i "agent\|cascad\|lk_" | tr '\n' ' '; echo
echo "== installed LiveKit packages:"; ~/theme5/fdb-env/bin/pip list 2>/dev/null | grep -i "livekit\|silero\|deepgram\|elevenlabs\|cartesia\|openai \|google-cloud-speech\|google-cloud-texttospeech" 
f=$(ls *.py | grep -i cascad | head -1)
if [ -n "$f" ]; then echo "== $f: which STT / LLM / TTS / VAD it uses (import and constructor lines only):"; grep -n "^from \|^import \|STT(\|TTS(\|LLM(\|VAD\|turn_detect\|AgentSession(" $f | cut -c1-150 | head -30; fi
echo "== does the google plugin expose STT and TTS classes?"; ~/theme5/fdb-env/bin/python -c "
from livekit.plugins import google
print('STT' , hasattr(google,'STT'), '| TTS', hasattr(google,'TTS'), '| LLM', hasattr(google,'LLM'))" 2>&1 | tail -1
