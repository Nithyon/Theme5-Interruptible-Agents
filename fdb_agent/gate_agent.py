"""FDB-v3 agent with the commit gate: the stock template's tools and prompt, with every
tool call routed through fdb_agent/gate.py. Model: GEMINI_LIVE_MODEL (default
gemini-3.8-live) when LK_PROVIDER starts with "gate_gemini", else the stock provider.

Run from the FDB v3 directory:
    LK_PROVIDER=gate_gemini38 python /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py start
"""
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.getcwd())                                   # FDB v3 directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))    # this folder
import lk_agent_tool as stock                                     # noqa: E402
from livekit import agents                                        # noqa: E402
from livekit.agents import AgentSession, llm                      # noqa: E402
from livekit.agents.llm.tool_context import FunctionTool          # noqa: E402
from gate import CommitGate, gate_tools                           # noqa: E402
from models import gemini_live                                    # noqa: E402

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")
PROVIDER = os.getenv("LK_PROVIDER", "gate_gemini38")


def realtime_model():
    if PROVIDER.lower().startswith("gate_gemini"):
        return gemini_live(MODEL)
    return stock.get_realtime_model()




server = stock.AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    tracker = stock.LatencyTracker()
    fnc_ctx = stock.AssistantFnc(tracker, ctx.room.name)
    gate = CommitGate(quiet_s=float(os.getenv("GATE_QUIET_S", "0.9")),
                      hesitant_quiet_s=float(os.getenv("GATE_HESITANT_QUIET_S", "1.8")))
    tools = gate_tools(llm.find_function_tools(fnc_ctx), gate, FunctionTool)
    session = AgentSession(llm=realtime_model(), tools=tools)

    @session.on("user_state_changed")
    def _user_state(ev):
        gate.on_user_state(ev.new_state)

    @session.on("user_input_transcribed")
    def _user_text(ev):
        gate.on_user_transcript(getattr(ev, "transcript", "") or "")
        if not tracker.query_received:
            tracker.user_done_at = time.time()
            tracker.query_received = True

    @session.on("agent_state_changed")
    def _agent_state(ev):
        if ev.new_state == "speaking" and tracker.query_received and not tracker.agent_start_at:
            tracker.agent_start_at = time.time()
            tracker.log_breakdown(tool_name="Search Tool", room_name=ctx.room.name)
            tracker.reset()

    async def _report():
        with open("/tmp/gate_stats.log", "a") as f:
            f.write(json.dumps({"room": ctx.room.name, **gate.stats}) + "\n")
    ctx.add_shutdown_callback(_report)

    await session.start(room=ctx.room, agent=stock.VoiceAgent())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)
