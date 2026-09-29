"""LiveKit agent draft for the extension's in-car assistant demo (extension/DESIGN.md).

Modelled on fdb_agent/gate_agent.py's AgentServer/rtc_session/AgentSession pattern and
fdb_agent/models.py's gemini_live(), but entirely separate from the FDB-v3 benchmark agent:
different tools (extension/mock_tools.py, not the 12 stock FDB-v3 tools), different recovery
layer (extension/recovery.py's ToolRunner, not fdb_agent/gate.py's CommitGate — this use case
needs retry/backoff/handoff for slow-or-failing tools, which the benchmark's zero-latency
mock APIs never require).

WRITE-ONLY DRAFT: not run in this session (a benchmark gate run was in progress, and this
needs LiveKit + Gemini credentials this session never touches). Run it yourself per
extension/README.md once the gate run is done and you're ready to demo.

Run (once ready):
    LK_PROVIDER=ext_gemini38 python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py console
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                        # this folder
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fdb_agent"))  # for models.py

from livekit import agents                                    # noqa: E402
from livekit.agents import Agent, AgentServer, AgentSession, llm  # noqa: E402

from mock_tools import MockBackend                             # noqa: E402
from recovery import ToolRunner                                 # noqa: E402
from models import gemini_live                                  # noqa: E402

if hasattr(llm, "function_tool"):
    ai_callable_decorator = llm.function_tool
else:
    ai_callable_decorator = llm.ai_callable

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")
PROVIDER = os.getenv("LK_PROVIDER", "ext_gemini38")

SYSTEM_PROMPT = (
    "You are the voice assistant built into a car. Keep responses short and spoken-natural. "
    "You have tools for navigation, traffic, EV charging search/booking, and roadside "
    "assistance. Execute the right tool immediately when the driver asks for something — "
    "do not ask clarifying questions, do not wait for confirmation before calling a tool. "
    "If the driver corrects themselves mid-request (e.g. 'reroute to the airport... actually "
    "downtown instead'), act only on their final, corrected request. "
    "Some tools take a few seconds; you will be told to say a short progress update if one is "
    "still running — keep it brief and never claim a result before you actually have one. "
    "If a tool reports a 'handoff' status, tell the driver you've passed their request to a "
    "human agent and read back the reference number. Always speak the key result: for a "
    "charging station, its id and distance; for a booking, its confirmation id; for traffic, "
    "the congestion level; for a reroute, the new ETA."
)


class InCarAssistant:
    """Exposes the 5 mock in-car tools as function_tools, each routed through a shared
    ToolRunner so slow/flaky/state-changing behaviour is handled the same way regardless of
    which tool the model calls."""

    def __init__(self, runner: ToolRunner, backend: MockBackend):
        self.runner = runner
        self.backend = backend

    @ai_callable_decorator(description="Change the car's active navigation destination.")
    async def reroute_navigation(self, destination: str):
        """
        Args:
            destination: Where to navigate to, e.g. 'the airport' or '123 Main St'
        """
        result = await self.runner.run(
            "reroute_navigation", {"destination": destination},
            lambda: self.backend.reroute_navigation(destination),
            slot="destination", state_changing=True,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Check traffic conditions on the current route. Can take a few seconds.")
    async def check_traffic(self, route_id: str = "current"):
        """
        Args:
            route_id: Which route to check, defaults to the current route
        """
        result = await self.runner.run(
            "check_traffic", {"route_id": route_id},
            lambda: self.backend.check_traffic(route_id),
            slot="traffic", state_changing=False,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Find a nearby EV charging station. May need a couple of tries.")
    async def find_charging_station(self, near: str, connector_type: str):
        """
        Args:
            near: Area to search near, e.g. 'downtown'
            connector_type: Connector type, e.g. 'CCS' or 'NACS'
        """
        result = await self.runner.run(
            "find_charging_station", {"near": near, "connector_type": connector_type},
            lambda: self.backend.find_charging_station(near, connector_type),
            slot="charging_search", state_changing=False,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Book a specific EV charging station time slot.")
    async def book_charging_slot(self, station_id: str, time_slot: str):
        """
        Args:
            station_id: The station id from a prior search, e.g. 'CHG-001'
            time_slot: Requested time, e.g. '18:00'
        """
        result = await self.runner.run(
            "book_charging_slot", {"station_id": station_id, "time_slot": time_slot},
            lambda: self.backend.book_charging_slot(station_id, time_slot),
            slot="charging_booking", state_changing=True,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Call roadside assistance for a car problem.")
    async def call_roadside_assistance(self, issue: str):
        """
        Args:
            issue: What's wrong, e.g. 'flat tire' or 'won't start'
        """
        result = await self.runner.run(
            "call_roadside_assistance", {"issue": issue},
            lambda: self.backend.call_roadside_assistance(issue),
            slot="roadside", state_changing=True,
        )
        return json.dumps(result)


class InCarVoiceAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)


def realtime_model():
    return gemini_live(MODEL)


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    backend = MockBackend(seed=int(os.getenv("EXT_SEED", "0")))
    runner = ToolRunner(
        timeout_s=float(os.getenv("EXT_TIMEOUT_S", "9.0")),
        max_retries=int(os.getenv("EXT_MAX_RETRIES", "2")),
        backoff_base_s=float(os.getenv("EXT_BACKOFF_BASE_S", "0.5")),
        progress_after_s=float(os.getenv("EXT_PROGRESS_AFTER_S", "1.5")),
        handoff_after_failures=int(os.getenv("EXT_HANDOFF_AFTER", "2")),
    )
    fnc_ctx = InCarAssistant(runner, backend)
    tools = llm.find_function_tools(fnc_ctx)
    session = AgentSession(llm=realtime_model(), tools=tools)

    def _speak(text: str):
        # session.say()/generate_reply() are coroutines; schedule them from the runner's
        # sync callbacks without blocking the callback itself.
        asyncio.create_task(session.say(text))

    runner.on_progress = lambda tool, call_id: _speak(_progress_line(tool))
    runner.on_handoff = lambda tool, call_id, ref: _speak(
        f"I've passed this to a human agent. Your reference number is {ref}."
    )

    async def _report():
        with open("/tmp/ext_recovery_events.log", "a") as f:
            for line in runner.log.lines():
                f.write(line + "\n")
    ctx.add_shutdown_callback(_report)

    await session.start(room=ctx.room, agent=InCarVoiceAgent())


def _progress_line(tool: str) -> str:
    return {
        "check_traffic": "Still checking traffic, one moment...",
        "find_charging_station": "Still looking for a charging station...",
        "book_charging_slot": "Still booking that slot...",
        "reroute_navigation": "Still rerouting...",
        "call_roadside_assistance": "Still trying to reach roadside assistance...",
    }.get(tool, "Still working on that...")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)
