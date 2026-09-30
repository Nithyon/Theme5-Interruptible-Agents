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
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))                        # this folder
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fdb_agent"))  # for models.py

from livekit import agents                                    # noqa: E402
from livekit.agents import Agent, AgentServer, AgentSession, llm  # noqa: E402

from mock_tools import MockBackend                             # noqa: E402
from mock_tools_home import HomeBackend                         # noqa: E402
from recovery import ToolRunner, _canon                         # noqa: E402
from models import gemini_live                                  # noqa: E402

if hasattr(llm, "function_tool"):
    ai_callable_decorator = llm.function_tool
else:
    ai_callable_decorator = llm.ai_callable

MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.8-live")
PROVIDER = os.getenv("LK_PROVIDER", "ext_gemini38")
# Which tool pack to run: "car" (default, in-car assistant) or "home" (Bixby-style home
# assistant with mock SmartThings-like tools). Same agent, same ToolRunner either way.
PACK = os.getenv("EXT_PACK", "car").strip().lower()
if PACK not in ("car", "home"):
    raise SystemExit(f"EXT_PACK must be 'car' or 'home', got {PACK!r}")

SYSTEM_PROMPT = (
    "You are the voice assistant built into a car. Keep responses short and spoken-natural. "
    "You have tools for navigation, traffic, EV charging search/booking, and roadside "
    "assistance. Execute the right tool immediately when the driver asks for something — "
    "do not ask clarifying questions, do not wait for confirmation before calling a tool. "
    "If the driver corrects themselves mid-request (e.g. 'reroute to the airport... actually "
    "downtown instead'), act only on their final, corrected request. If the driver changes "
    "their mind about a charging booking that's already confirmed (e.g. 'actually, book the "
    "Ionity one instead'), just call book_charging_slot again with the new station — the old "
    "booking is cancelled for you automatically, don't call anything else first. "
    "Some tools take a few seconds; you will be told to say a short progress update if one is "
    "still running — keep it brief and never claim a result before you actually have one. "
    "If a tool reports status 'failed', say plainly that it did not work; never say you transferred, escalated or handed anything off unless the tool's status is 'handoff'. If a tool reports a 'handoff' status, tell the driver you've passed their request to a "
    "human agent and read back the reference number. Always speak the key result: for a "
    "charging station, its id and distance; for a booking, its confirmation id; for traffic, "
    "the congestion level; for a reroute, the new ETA."
)

HOME_SYSTEM_PROMPT = (
    "You are a Bixby-style voice assistant for a smart home (mock devices, SmartThings-like). "
    "Keep responses short and spoken-natural. You have tools for the air conditioner, lights, "
    "the washer, energy usage, finding the user's phone, and the service centre. Execute the "
    "right tool immediately when the user asks for something — do not ask clarifying questions, "
    "do not wait for confirmation before calling a tool. If the user corrects themselves "
    "mid-request (e.g. 'set the AC to 24... no, 22'), act only on their final, corrected "
    "request. If the user changes the cycle of a washer that was already started (e.g. 'actually, "
    "make it eco instead'), just call start_washer again with the new cycle — the old job is "
    "cancelled for you automatically, don't call anything else first. Some tools take a few "
    "seconds; you will be told to say a short progress update if one is still running — keep it "
    "brief and never claim a result before you actually have one. If a tool reports status 'failed', say plainly that it did not work; never say you transferred, escalated or handed anything off unless the tool's status is 'handoff'. If a tool reports a 'handoff' "
    "status, tell the user you've passed their request to a human agent and read back the "
    "reference number. Always speak the key result: for the AC or lights, the new setting; for "
    "the washer, its job id; for energy usage, the kWh; for the phone, where it is."
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
        args = {"station_id": station_id, "time_slot": time_slot}
        prior = self.runner.completed.get("charging_booking")
        if prior is None or prior.compensated or prior.args_key == "book_charging_slot|" + _canon(args):
            # nothing already booked in this slot, or this "booking" is identical to what's
            # already there — a normal call, no compensation involved.
            result = await self.runner.run(
                "book_charging_slot", args,
                lambda: self.backend.book_charging_slot(station_id, time_slot),
                slot="charging_booking", state_changing=True,
            )
        else:
            # the driver already has a successful booking in this slot and is now asking for a
            # different one — cancel the old one first, then book the new one.
            old_booking_id = prior.result["booking_id"]
            result = await self.runner.rollback_and_run(
                "book_charging_slot", args,
                lambda: self.backend.book_charging_slot(station_id, time_slot),
                slot="charging_booking",
                compensate_tool="cancel_charging_booking",
                compensate_args={"booking_ref": old_booking_id},
                compensate_execute=lambda: self.backend.cancel_charging_booking(old_booking_id),
            )
            if isinstance(result, dict) and result.get("booking_id"):
                result = {**result, "cancelled_booking_id": old_booking_id,
                          "note": f"The earlier booking {old_booking_id} was cancelled first, then this one "
                                  "was made. Tell the driver both."}
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


class HomeAssistant:
    """Exposes the 6 mock smart-home tools as function_tools (plus cancel_washer, used only as
    the rollback compensation), routed through the same shared ToolRunner as the in-car pack.
    Mock tools only: not an integration with Bixby or SmartThings."""

    def __init__(self, runner: ToolRunner, backend: HomeBackend):
        self.runner = runner
        self.backend = backend

    @ai_callable_decorator(description="Set the air conditioner target temperature in a room.")
    async def set_ac_temperature(self, room: str, celsius: float):
        """
        Args:
            room: Which room, e.g. 'living room'
            celsius: Target temperature in degrees Celsius
        """
        result = await self.runner.run(
            "set_ac_temperature", {"room": room, "celsius": celsius},
            lambda: self.backend.set_ac_temperature(room, celsius),
            slot="ac_temperature", state_changing=True,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Turn the lights in a room on or off and set brightness.")
    async def set_lights(self, room: str, state: str, brightness: int = 100):
        """
        Args:
            room: Which room, e.g. 'bedroom'
            state: 'on' or 'off'
            brightness: Brightness percent 0-100
        """
        result = await self.runner.run(
            "set_lights", {"room": room, "state": state, "brightness": brightness},
            lambda: self.backend.set_lights(room, state, brightness),
            slot="lights", state_changing=True,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Start the washer with a cycle, optionally delayed.")
    async def start_washer(self, cycle: str, delay_minutes: int = 0):
        """
        Args:
            cycle: Washer cycle, e.g. 'cotton' or 'eco'
            delay_minutes: Minutes to wait before starting, default 0
        """
        args = {"cycle": cycle, "delay_minutes": delay_minutes}
        prior = self.runner.completed.get("washer")
        if prior is None or prior.compensated or prior.args_key == "start_washer|" + _canon(args):
            # nothing already started, or this is the identical request — a normal call.
            result = await self.runner.run(
                "start_washer", args,
                lambda: self.backend.start_washer(cycle, delay_minutes),
                slot="washer", state_changing=True,
            )
        else:
            # a washer job already started in this slot and the user wants a different cycle —
            # cancel the old job first, then start the new one.
            old_job_id = prior.result["job_id"]
            result = await self.runner.rollback_and_run(
                "start_washer", args,
                lambda: self.backend.start_washer(cycle, delay_minutes),
                slot="washer",
                compensate_tool="cancel_washer",
                compensate_args={"job_id": old_job_id},
                compensate_execute=lambda: self.backend.cancel_washer(old_job_id),
            )
            if isinstance(result, dict) and result.get("job_id"):
                result = {**result, "cancelled_job_id": old_job_id,
                          "note": f"The earlier washer job {old_job_id} was cancelled first, then this one "
                                  "was started. Tell the user both."}
        return json.dumps(result)

    @ai_callable_decorator(description="Check home energy usage for a period. Can take a few seconds.")
    async def check_energy_usage(self, period: str = "today"):
        """
        Args:
            period: 'today', 'this week' or 'this month'
        """
        result = await self.runner.run(
            "check_energy_usage", {"period": period},
            lambda: self.backend.check_energy_usage(period),
            slot="energy", state_changing=False,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Ring the user's phone to find it. May need a couple of tries.")
    async def find_phone(self):
        result = await self.runner.run(
            "find_phone", {},
            lambda: self.backend.find_phone(),
            slot="find_phone", state_changing=False,
        )
        return json.dumps(result)

    @ai_callable_decorator(description="Call the appliance service centre about a problem.")
    async def call_service_center(self, issue: str):
        """
        Args:
            issue: What's wrong, e.g. 'washer leaking'
        """
        result = await self.runner.run(
            "call_service_center", {"issue": issue},
            lambda: self.backend.call_service_center(issue),
            slot="service_center", state_changing=True,
        )
        return json.dumps(result)


class InCarVoiceAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=HOME_SYSTEM_PROMPT if PACK == "home" else SYSTEM_PROMPT)


def realtime_model():
    return gemini_live(MODEL)


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: agents.JobContext):
    seed = int(os.getenv("EXT_SEED", "0"))
    backend = HomeBackend(seed=seed) if PACK == "home" else MockBackend(seed=seed)
    runner = ToolRunner(
        timeout_s=float(os.getenv("EXT_TIMEOUT_S", "9.0")),
        max_retries=int(os.getenv("EXT_MAX_RETRIES", "2")),
        backoff_base_s=float(os.getenv("EXT_BACKOFF_BASE_S", "0.5")),
        progress_after_s=float(os.getenv("EXT_PROGRESS_AFTER_S", "1.5")),
        handoff_after_failures=int(os.getenv("EXT_HANDOFF_AFTER", "2")),
    )
    fnc_ctx = HomeAssistant(runner, backend) if PACK == "home" else InCarAssistant(runner, backend)
    tools = llm.find_function_tools(fnc_ctx)
    session = AgentSession(llm=realtime_model(), tools=tools)

    def _speak(text: str):
        # A realtime (speech-to-speech) session cannot say() raw text: found in the first
        # end-to-end run (2026-09-30), where say() raised inside the rollback callback and
        # failed the tool. Ask the model to say the line instead, and never let a speech
        # problem break a tool call: the same facts are also put in the tool result.
        try:
            session.generate_reply(instructions=text)
        except Exception as e:
            logging.getLogger("ext_agent").warning("could not speak %r: %s", text, type(e).__name__)

    # Progress notices are OFF. In the end-to-end runs of 2026-09-30 the speech-to-speech model
    # read the instruction text aloud ("The tool is still running. Say one short sentence...")
    # instead of acting on it, in both wordings we tried. A pre-recorded audio clip is the
    # likely fix (as fdb_agent/responsive.py does for the acknowledgement); not built yet.
    # EXT_PROGRESS_SPEECH=1 turns the old behaviour back on for testing.
    if os.getenv("EXT_PROGRESS_SPEECH", "0") == "1":
        runner.on_progress = lambda tool, call_id: _speak(
            "The tool is still running. In one short sentence, tell the user you are still "
            "checking and will have the answer in a moment. Do not state any result yet."
        )
    # Hand-off and rollback are announced by the model from the tool result (status "handoff"
    # with a reference; "cancelled_job_id" / "cancelled_booking_id" with a note), so the
    # callbacks stay silent: speaking here as well made the agent say those lines twice.
    runner.on_handoff = None
    runner.on_rollback = None

    _emit = runner.log.emit

    def _emit_and_write(*a, **k):
        # write each recovery event as it happens (the first end-to-end run, which wrote
        # the log only in a shutdown hook, ended without a log file; cause not established)
        e = _emit(*a, **k)
        try:
            with open(os.getenv("EXT_EVENT_LOG", "/tmp/ext_recovery_events.log"), "a") as f:
                f.write(e.to_json() + "\n")
        except OSError:
            pass
        return e
    runner.log.emit = _emit_and_write

    await session.start(room=ctx.room, agent=InCarVoiceAgent())
    try:  # clock anchor, so tool events can be lined up with the input clip afterwards
        with open(os.getenv("EXT_EVENT_LOG", "/tmp/ext_recovery_events.log"), "a") as f:
            f.write(json.dumps({"kind": "session_start", "ts": time.monotonic()}) + "\n")
    except OSError:
        pass


def _progress_line(tool: str) -> str:
    return {
        "check_traffic": "Still checking traffic, one moment...",
        "find_charging_station": "Still looking for a charging station...",
        "book_charging_slot": "Still booking that slot...",
        "reroute_navigation": "Still rerouting...",
        "call_roadside_assistance": "Still trying to reach roadside assistance...",
        "check_energy_usage": "Still checking your energy usage, one moment...",
        "find_phone": "Still trying to find your phone...",
        "start_washer": "Still starting the washer...",
        "call_service_center": "Still trying to reach the service centre...",
    }.get(tool, "Still working on that...")


def _rollback_line(old_tool: str, new_result: dict) -> str:
    if old_tool == "book_charging_slot":
        return f"Done — I've cancelled the previous booking and booked {new_result.get('station_id', 'the new station')} instead."
    if old_tool == "start_washer":
        return (f"Done — I've cancelled the previous wash and started the "
                f"{new_result.get('cycle', 'new')} cycle instead.")
    return "Done — I've reversed the previous action and completed the new one instead."


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agents.cli.run_app(server)
