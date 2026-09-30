"""Second gate agent on the same machine (a second LiveKit project): identical to
gate_agent.py except for the worker's local HTTP port (AGENT_PORT, default 8082), so it can
run beside another agent that already holds 8081. Usage: python gate_agent_b.py start
"""
import os
import sys

sys.path.insert(0, os.getcwd())                                   # FDB v3 directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))    # this folder
import lk_agent_tool as stock                                     # noqa: E402

_AgentServer = stock.AgentServer
stock.AgentServer = lambda *a, **k: _AgentServer(*a, port=int(os.getenv("AGENT_PORT", "8082")), **k)
import gate_agent                                                 # noqa: E402
from livekit import agents                                        # noqa: E402

if __name__ == "__main__":
    agents.cli.run_app(gate_agent.server)
