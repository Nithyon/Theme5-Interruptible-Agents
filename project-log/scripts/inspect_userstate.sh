#!/usr/bin/env bash
P=/home/saini/theme5/fdb-env/lib/python3.10/site-packages/livekit
echo "== gemini plugin: speech-start / activity events"
grep -nE 'input_speech_started|input_speech_stopped|InputSpeechStarted|activity_start|interrupted' $P/plugins/google/realtime/realtime_api.py | head -12
echo "== agent_activity: what sets user state"
grep -nE '_update_user_state|user_state|on_input_speech_started|input_speech_started' $P/agents/voice/agent_activity.py | head -20
echo "== stock template: VAD / turn detection in AgentSession?"
grep -nE 'AgentSession\(|vad=|turn_detection|silero' ~/theme5/Full-Duplex-Bench/v3/lk_agent_tool.py | head
