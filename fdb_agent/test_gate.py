"""Offline tests for the commit gate (no LiveKit, no API calls).
Run from the FDB v3 dir: python /mnt/d/Theme5-Interruptible-Agents/fdb_agent/test_gate.py"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lk_agent_tool as stock                                   # noqa: E402
from livekit.agents import llm                                  # noqa: E402
from livekit.agents.llm.tool_context import FunctionTool        # noqa: E402
from livekit.agents.llm.utils import build_legacy_openai_schema  # noqa: E402
from gate import CommitGate, gate_tools                         # noqa: E402

fails = 0


def check(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1


# 1. schemas unchanged
orig = llm.find_function_tools(stock.AssistantFnc(stock.LatencyTracker(), "t"))
gate = CommitGate(quiet_s=0.3)
wrapped = gate_tools(orig, gate, FunctionTool)
same = all(json.dumps(build_legacy_openai_schema(a), sort_keys=True) ==
           json.dumps(build_legacy_openai_schema(b), sort_keys=True) for a, b in zip(orig, wrapped))
check(len(orig) == len(wrapped) == 12 and same, "12 tools, schemas identical after wrapping")


async def scenarios():
    ran = []

    def fake(name, args):
        async def go():
            ran.append((name, args))
            return json.dumps({"status": "success", **args})
        return go

    # 2. correction: call made, user speaks again, newer call supersedes the held one
    g = CommitGate(quiet_s=0.3)
    g.on_user_state("listening")
    t1 = asyncio.create_task(g.run("search_flights", {"destination": "Boston"},
                                   fake("search_flights", {"destination": "Boston"})))
    await asyncio.sleep(0.05)
    g.on_user_state("speaking")           # "…no, sorry, New York"
    await asyncio.sleep(0.2)
    g.on_user_state("listening")
    t2 = asyncio.create_task(g.run("search_flights", {"destination": "New York"},
                                   fake("search_flights", {"destination": "New York"})))
    r1, r2 = await asyncio.gather(t1, t2)
    check(ran == [("search_flights", {"destination": "New York"})], "correction: only the corrected call runs")
    check("superseded" in r1, "correction: stale call told it was superseded")

    # 3. two calls in one turn (two different orders) both run
    ran.clear()
    g = CommitGate(quiet_s=0.2)
    await asyncio.gather(g.run("track_order", {"order_id": "A1"}, fake("track_order", {"order_id": "A1"})),
                         g.run("track_order", {"order_id": "B2"}, fake("track_order", {"order_id": "B2"})))
    check(len(ran) == 2, "same tool twice in one turn: both run")

    # 4. identical repeat never executes twice
    ran.clear()
    await g.run("add_to_cart", {"product_id": "P1", "quantity": 1}, fake("add_to_cart", {}))
    await g.run("add_to_cart", {"product_id": "p1 ", "quantity": 1}, fake("add_to_cart", {}))
    check(len(ran) == 1, "duplicate state change executed once")

    # 5. held while the user is still talking
    ran.clear()
    g = CommitGate(quiet_s=0.3)
    g.on_user_state("speaking")
    t = asyncio.create_task(g.run("get_card_benefits", {"card_type": "gold"}, fake("get_card_benefits", {})))
    await asyncio.sleep(0.5)
    check(not ran, "held while the user is speaking")
    g.on_user_state("listening")
    t0 = time.monotonic()
    await t
    check(ran and time.monotonic() - t0 >= 0.25, "runs after the quiet window")

    # 6. hesitant tail ("…no, sorry") waits longer than a finished sentence
    from gate import ends_hesitantly
    check(ends_hesitantly("track order 447, um") and ends_hesitantly("book Boston. No wait")
          and ends_hesitantly("New York, I mean") and not ends_hesitantly("order 4471 please")
          and not ends_hesitantly("I know") and not ends_hesitantly(""),
          "hesitant-tail detection")
    ran.clear()
    g = CommitGate(quiet_s=0.2, hesitant_quiet_s=0.8)
    g.on_user_transcript("search flights to Boston, uh")
    g.on_user_state("listening")
    t0 = time.monotonic()
    await g.run("search_flights", {"destination": "Boston"}, fake("search_flights", {}))
    check(time.monotonic() - t0 >= 0.7, "hesitant tail: waits the longer window")
    g.on_user_transcript("New York please")
    g.on_user_state("speaking"); g.on_user_state("listening")
    t0 = time.monotonic()
    await g.run("search_flights", {"destination": "New York"}, fake("search_flights", {}))
    check(0.15 <= time.monotonic() - t0 < 0.6, "finished sentence: normal window")

asyncio.run(scenarios())
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
