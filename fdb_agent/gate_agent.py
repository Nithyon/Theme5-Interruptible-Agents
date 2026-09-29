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
from jev import make_judge                                        # noqa: E402

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")
PROVIDER = os.getenv("LK_PROVIDER", "gate_gemini38")


def realtime_model():
    if "gate_gemini" in PROVIDER.lower():
        return gemini_live(MODEL)
    return stock.get_realtime_model()




# Generic behaviour rules added to the stock instructions (GATE_PROMPT=1). They address
# failure modes, not particular requests: asking follow-ups the user can't answer,
# acting on a value the user then corrected, and claiming success before a result.
EXTRA_RULES = (
    " RULES FOR THIS CALL: The user cannot answer follow-up questions. If a detail is not"
    " stated, call the tool with the user's own words as the value (for example 'home',"
    " 'my office', 'the gym'); never ask for more details. When the user corrects"
    " themselves, only the last value they state counts: call the tool once with the"
    " corrected values and never with the earlier ones. If the user asks for several"
    " things, call a tool for each of them. Never say an action is done until its tool"
    " result has come back; while waiting, you may say you're checking."
)


# GATE_PROMPT=2: the merged rule set (ours + Lohit's prompt_addendum, T5_upgrade_pack).
EXTRA_RULES_V2 = (
    " TURN RULES: Wait until the user has finished the whole request before acting; people"
    " pause, say 'um', and correct themselves. The LAST stated value wins: 'Boston… no wait,"
    " New York' means New York; '200, make that 250' means 250. If the user cancels or"
    " replaces a request ('don't book, just…', 'forget that'), do not perform the cancelled"
    " action. Call each tool exactly once per distinct request and never repeat a call you"
    " already made. If the user asks for two different items with the same tool (two order"
    " ids, two cards), call it once for each item. Use values exactly as the user said them"
    " (city names, product ids, order ids, names); currencies as 3-letter codes (USD, EUR,"
    " GBP, JPY, INR, CAD); numbers as digits. The user cannot answer follow-up questions: if a"
    " detail is not stated, use the user's own words as the value (for example 'home', 'my"
    " office'); never ask for more details. After the tools return, always speak a short"
    " answer that states the key results first. Never say something is done before its tool"
    " result arrives; while waiting you may say you're checking."
)


class GatedVoiceAgent(stock.VoiceAgent):
    def __init__(self) -> None:
        super().__init__()
        mode = os.getenv("GATE_PROMPT", "1")
        if mode == "1":
            self._instructions = self.instructions + EXTRA_RULES
        elif mode == "2":
            self._instructions = self.instructions + EXTRA_RULES_V2


server = stock.AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    tracker = stock.LatencyTracker()
    fnc_ctx = stock.AssistantFnc(tracker, ctx.room.name)
    gate = CommitGate(quiet_s=float(os.getenv("GATE_QUIET_S", "0.9")),
                      hesitant_quiet_s=float(os.getenv("GATE_HESITANT_QUIET_S", "1.8")),
                      unclear_supersedes=os.getenv("GATE_UNCLEAR_SUPERSEDES", "1") == "1",
                      judge=make_judge(),
                      draft_hold_s=float(os.getenv("GATE_DRAFT_HOLD_S", "0")))
    tools = gate_tools(llm.find_function_tools(fnc_ctx), gate, FunctionTool)
    session = AgentSession(llm=realtime_model(), tools=tools)

    @session.on("user_state_changed")
    def _user_state(ev):
        gate.on_user_state(ev.new_state)

    @session.on("user_input_transcribed")
    def _user_text(ev):
        gate.on_user_transcript(getattr(ev, "transcript", "") or "", getattr(ev, "is_final", None))
        if not tracker.query_received:
            tracker.user_done_at = time.time()
            tracker.query_received = True

    @session.on("agent_state_changed")
    def _agent_state(ev):
        if ev.new_state == "speaking" and tracker.query_received and not tracker.agent_start_at:
            tracker.agent_start_at = time.time()
            tracker.log_breakdown(tool_name="Search Tool", room_name=ctx.room.name)
            tracker.reset()

    reported = []

    def _report():
        if reported:
            return
        reported.append(True)
        with open("/tmp/gate_stats.log", "a") as f:
            jev_stats = gate.judge.stats if gate.judge is not None else None
            f.write(json.dumps({"room": ctx.room.name, **gate.stats, "jev": jev_stats}) + "\n")
        with open("/tmp/gate_events.log", "a") as f:
            f.write(json.dumps({"room": ctx.room.name, "events": gate.events}, default=str) + "\n")

    async def _report_async():
        _report()
    ctx.add_shutdown_callback(_report_async)

    @session.on("close")
    def _closed(ev):
        _report()

    await session.start(room=ctx.room, agent=GatedVoiceAgent())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)
