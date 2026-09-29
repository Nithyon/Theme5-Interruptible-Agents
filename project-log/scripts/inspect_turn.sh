#!/usr/bin/env bash
P=/home/saini/theme5/fdb-env/lib/python3.10/site-packages/livekit
grep -nE 'input_audio_transcription|input_transcription' $P/plugins/google/realtime/realtime_api.py | head -6
echo "--- plugins installed:"; ls $P/plugins
echo "--- turn detection vs realtime:"
grep -rnE 'turn_detection' $P/agents/voice/agent_session.py | head -5
grep -rnE 'realtime.*turn_detection|turn_detection.*realtime|stt.*turn_detector|turn_detector.*stt' $P/agents/voice/*.py | head -6
echo "--- user transcripts seen in baseline agent log:"
grep -c 'user_input_transcribed\|transcript' /mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_full_gemini3_8/agent.log
