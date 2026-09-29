#!/usr/bin/env bash
source ~/theme5/fdb-env/bin/activate
python /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/our_calls.py "${1:-gemini3_8}"
echo "== tool schemas"
cd ~/theme5/Full-Duplex-Bench/v3
python - <<'PY' 2>&1 | grep -v 'API Backend'
import sys; sys.path.insert(0, '.')
import lk_agent_tool as s
from livekit.agents import llm
from livekit.agents.llm.utils import build_legacy_openai_schema
for t in llm.find_function_tools(s.AssistantFnc(s.LatencyTracker(), 'x')):
    sc = build_legacy_openai_schema(t)['function']
    props = {k: (v.get('description') or v.get('type')) for k, v in sc['parameters'].get('properties', {}).items()}
    print(' ', sc['name'], '|', (sc.get('description') or '')[:90].replace('\n', ' '), '|', props)
PY
