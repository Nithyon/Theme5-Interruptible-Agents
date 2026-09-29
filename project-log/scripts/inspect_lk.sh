#!/usr/bin/env bash
SP=$(~/theme5/fdb-env/bin/python -c 'import livekit.agents,os;print(os.path.dirname(livekit.agents.__file__))')
echo "$SP"
grep -nE '^def function_tool|^class FunctionTool|^def find_function_tools|_tool_info|^def is_function_tool|^class RawFunctionTool|^def get_fnc_tool_names' "$SP/llm/tool_context.py" | head -30
sed -n "$(grep -n '^def function_tool' "$SP/llm/tool_context.py" | head -1 | cut -d: -f1),+60p" "$SP/llm/tool_context.py"
echo "=== events"
grep -nE 'class (UserStateChangedEvent|UserInputTranscribedEvent)|UserState = |new_state' "$SP/voice/events.py" | head -10
