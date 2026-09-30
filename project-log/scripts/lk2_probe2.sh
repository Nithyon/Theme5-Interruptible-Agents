#!/usr/bin/env bash
cd ~/theme5/fdb-env/lib/python3.10/site-packages/livekit/agents
grep -n "8081\|LIVEKIT_AGENT_PORT\|port: " worker.py cli/*.py 2>/dev/null | cut -c1-180 | head -20
grep -n "AgentServer(\|server = \|gate_events\|gate_stats\|cli.run_app\|WorkerOptions" /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py ~/theme5/Full-Duplex-Bench/v3/lk_agent_tool.py | cut -c1-200
