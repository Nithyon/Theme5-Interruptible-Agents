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

async def transcript_driven():
    # 8. no VAD/user-state events at all (Gemini realtime): transcript text alone decides
    ran = []

    def fake(args):
        async def go():
            ran.append(args)
            return "ok"
        return go

    g = CommitGate(quiet_s=0.3)
    g.on_user_transcript("book a flight to Boston")
    t1 = asyncio.create_task(g.run("search_flights", {"destination": "Boston"}, fake("Boston")))
    await asyncio.sleep(0.1)
    g.on_user_transcript("no sorry, New York")
    t2 = asyncio.create_task(g.run("search_flights", {"destination": "New York"}, fake("New York")))
    await asyncio.gather(t1, t2)
    check(ran == ["New York"], f"transcript correction: only the corrected call runs {ran}")

    ran.clear()
    g = CommitGate(quiet_s=0.3)
    g.on_user_transcript("track order A1")
    t1 = asyncio.create_task(g.run("track_order", {"order_id": "A1"}, fake("A1")))
    await asyncio.sleep(0.1)
    g.on_user_transcript("and also order B2")
    t2 = asyncio.create_task(g.run("track_order", {"order_id": "B2"}, fake("B2")))
    await asyncio.gather(t1, t2)
    check(sorted(ran) == ["A1", "B2"], f"transcript addition: both calls run {ran}")
    check(any(e["kind"] == "same_tool_again" for e in g.events), "decisions are logged")


class FakeJev:
    """Stands in for JevJudge offline: fixed answers, optional delay/failure."""
    def __init__(self, turn=None, followup=None, delay=0.0):
        self.turn, self.follow, self.delay = turn, followup, delay
        self.stats = {"calls": 0}

    async def turn_state(self, text):
        self.stats["calls"] += 1
        await asyncio.sleep(self.delay)
        return self.turn

    async def followup(self, a, b, said):
        self.stats["calls"] += 1
        await asyncio.sleep(self.delay)
        return self.follow


async def with_jev():
    # 9. Jev confident the user is done -> fast release; thinks they'll continue -> hold
    async def noop():
        return "ok"
    g = CommitGate(quiet_s=0.6, judge=FakeJev(turn={"complete": 0.95, "continuing": 0.05}))
    g.on_user_transcript("track order 4471 please")
    await asyncio.sleep(0.05)
    t0 = time.monotonic()
    await g.run("track_order", {"order_id": "4471"}, noop)
    check(time.monotonic() - t0 < 0.55, "jev 'complete': released faster than the rule window")

    g = CommitGate(quiet_s=0.3, judge=FakeJev(turn={"complete": 0.2, "continuing": 0.8}))
    g.on_user_transcript("book a flight to Boston")
    await asyncio.sleep(0.05)
    t0 = time.monotonic()
    await g.run("search_flights", {"destination": "Boston"}, noop)
    check(time.monotonic() - t0 >= 2.3, "jev 'continuing': held for the longer window")

    # 10. Jev decides correction vs addition, overriding the keyword rules
    ran = []

    def fake(v):
        async def go():
            ran.append(v)
            return "ok"
        return go
    g = CommitGate(quiet_s=0.3, judge=FakeJev(followup={"correction": 0.1, "addition": 0.85, "unrelated": 0.05}))
    g.on_user_transcript("track order A1")
    t1 = asyncio.create_task(g.run("track_order", {"order_id": "A1"}, fake("A1")))
    await asyncio.sleep(0.1)
    g.on_user_transcript("no, the other one too")          # rules would say correction
    t2 = asyncio.create_task(g.run("track_order", {"order_id": "B2"}, fake("B2")))
    await asyncio.gather(t1, t2)
    check(sorted(ran) == ["A1", "B2"], f"jev 'addition' overrides the keyword rule {ran}")

    # 11. Jev unavailable (None) -> rules decide
    ran.clear()
    g = CommitGate(quiet_s=0.3, judge=FakeJev(turn=None, followup=None))
    g.on_user_transcript("book Boston")
    t1 = asyncio.create_task(g.run("search_flights", {"destination": "Boston"}, fake("Boston")))
    await asyncio.sleep(0.1)
    g.on_user_transcript("no sorry, New York")
    t2 = asyncio.create_task(g.run("search_flights", {"destination": "New York"}, fake("New York")))
    await asyncio.gather(t1, t2)
    check(ran == ["New York"], f"jev down: rule fallback still corrects {ran}")


async def draft_rule():
    # 12. a placeholder call (empty date) at a pause is held and replaced by the real one
    from gate import looks_draft
    check(looks_draft({"destination": "Amsterdam", "date": ""}) and looks_draft({"bedrooms": 0})
          and not looks_draft({"quantity": 3, "product_id": "P42"}), "draft detection")
    ran = []

    def fake(v):
        async def go():
            ran.append(v)
            return "ok"
        return go
    g = CommitGate(quiet_s=0.3, draft_hold_s=1.5)
    g.on_user_transcript("search flights to Amsterdam on")
    t1 = asyncio.create_task(g.run("search_flights", {"destination": "Amsterdam", "date": ""}, fake("draft")))
    await asyncio.sleep(1.0)                        # a 1 s pause: past the normal window
    g.on_user_transcript("September 20th")
    t2 = asyncio.create_task(g.run("search_flights", {"destination": "Amsterdam", "date": "2026-09-20"}, fake("real")))
    await asyncio.gather(t1, t2)
    check(ran == ["real"], f"draft call replaced by the completed call {ran}")


async def wrapped_tools():
    # 7. through the real wrapped tools: positional and keyword calls both carry their
    # arguments into the gate, so two different orders are not treated as duplicates
    g = CommitGate(quiet_s=0.05)
    tools = {t.info.name: t for t in gate_tools(orig, g, FunctionTool)}
    tr = tools["track_order"]
    await tr("A1")
    await tr(order_id="B2")
    await tr("A1")
    check(g.stats["executed"] == 2 and g.stats["duplicate"] == 1,
          f"wrapped tool: positional+keyword args reach the gate {g.stats}")

asyncio.run(scenarios())
asyncio.run(transcript_driven())
asyncio.run(with_jev())
asyncio.run(draft_rule())
asyncio.run(wrapped_tools())
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
