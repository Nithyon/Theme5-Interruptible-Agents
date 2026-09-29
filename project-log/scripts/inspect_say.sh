#!/usr/bin/env bash
P=/home/saini/theme5/fdb-env/lib/python3.10/site-packages/livekit/agents/voice
grep -nE '    def say\(' -A 16 $P/agent_session.py | head -26
echo "--- say with realtime model / no tts:"
grep -nE 'audio.*is_given|tts.*required|no TTS|TTS is not|say\(\) requires' $P/agent_activity.py | head -8
