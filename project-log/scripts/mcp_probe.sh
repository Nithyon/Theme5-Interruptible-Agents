#!/usr/bin/env bash
# Read-only look at how the installed LiveKit Agents version attaches MCP servers (no agent is started).
S=~/theme5/fdb-env/lib/python3.10/site-packages/livekit/agents
ls $S/llm | tr '\n' ' '; echo
grep -n "^class \|def list_tools\|def __init__" $S/llm/mcp.py 2>/dev/null | head -30
grep -rn "mcp_servers" $S/voice/agent_session.py $S/voice/agent.py $S/voice/agent_activity.py 2>/dev/null | cut -c1-170 | head -20
pip list 2>/dev/null | grep -i "^mcp " ; ~/theme5/fdb-env/bin/python -c "import mcp,sys;print('mcp package', getattr(mcp,'__version__','present'))" 2>&1 | tail -1
grep -n "^def gate_tools" -A22 /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate.py | cut -c1-150
