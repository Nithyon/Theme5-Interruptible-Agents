#!/usr/bin/env bash
P=/home/saini/theme5/fdb-env/lib/python3.10/site-packages
grep -nE 'realtime_input_config|RealtimeInputConfig|automatic_activity_detection' $P/livekit/plugins/google/realtime/realtime_api.py | head -6
grep -nE 'class AutomaticActivityDetection\(' -A 40 $P/google/genai/types.py | grep -E 'class|Optional\[|sensitivity|silence|prefix' | head -12
