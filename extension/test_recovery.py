"""Offline tests for the extension's recovery layer (no network, no LiveKit, no benchmark).
Run with the fdb env's python:
  wsl -d Ubuntu -- ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/test_recovery.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recovery import ToolRunner, ToolFailure          # noqa: E402
from mock_tools import MockBackend                    # noqa: E402

fails = 0


def check(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1


async def scenarios():
    all_runners = []

    # (a) progress callback fires for a slow tool, without claiming it's done -------------
    backend = MockBackend(seed=1)
    progress_calls = []
    runner = ToolRunner(progress_after_s=0.05, timeout_s=2.0)
    all_runners.append(runner)
    runner.on_progress = lambda tool, call_id: progress_calls.append((tool, call_id))

    result = await runner.run(
        "check_traffic", {"route_id": "R1"},
        lambda: backend.check_traffic("R1", delay_range=(0.2, 0.2)),
        slot="traffic", state_changing=False,
    )
    check(result["status"] == "success", "(a) slow read-only call still succeeds")
    check(len(progress_calls) >= 1, "(a) on_progress fired at least once while the call was in flight")
    check(all(kind != "progress" for kind in [e.kind for e in runner.log.events]),
          "(a) progress updates go through the callback, not logged as a false completion")

    # (b) retry with backoff on failure, and idempotency for a state-changing call --------
    backend = MockBackend(seed=2)
    runner = ToolRunner(backoff_base_s=0.02, backoff_cap_s=0.05, max_retries=2, timeout_s=2.0)
    all_runners.append(runner)

    r1 = await runner.run(
        "find_charging_station", {"near": "Downtown", "connector_type": "CCS"},
        lambda: backend.find_charging_station("Downtown", "CCS"),
        slot="charging_search", state_changing=False,
    )
    check(r1["status"] == "success", "(b) flaky read-only tool recovers within its retry budget")
    call1_id = next(e.call_id for e in runner.log.events if e.kind == "succeeded")
    retries_seen = [e for e in runner.log.events if e.kind == "retry" and e.call_id == call1_id]
    check(len(retries_seen) == 2, "(b) exactly 2 retries were logged before success (fails twice, then succeeds)")

    book_args = {"station_id": "CHG-001", "time_slot": "18:00"}
    b1 = await runner.run("book_charging_slot", book_args,
                          lambda: backend.book_charging_slot(**book_args),
                          slot="booking", state_changing=True)
    b2 = await runner.run("book_charging_slot", book_args,
                          lambda: backend.book_charging_slot(**book_args),
                          slot="booking", state_changing=True)
    check(b1["status"] == "success" and b2 == b1, "(b) identical booking call returns the same cached result")
    check(len(backend.bookings) == 1, "(b) the underlying tool only actually booked once")
    dup_events = [e for e in runner.log.events if e.kind == "duplicate"]
    check(len(dup_events) == 1, "(b) the repeat call was logged as a duplicate, not re-executed")

    # (c) user interrupts mid-wait -> the pending call is cancelled/superseded ------------
    backend = MockBackend(seed=3)
    runner = ToolRunner(timeout_s=5.0)
    all_runners.append(runner)

    async def slow_reroute(dest):
        await asyncio.sleep(2.0)
        return await backend.reroute_navigation(dest)

    task = asyncio.create_task(runner.run(
        "reroute_navigation", {"destination": "Airport"},
        lambda: slow_reroute("Airport"),
        slot="destination", state_changing=True,
    ))
    await asyncio.sleep(0.05)  # let it start and register as pending
    check("destination" in runner.pending, "(c) the call is registered as pending while in flight")
    runner.supersede("destination")  # user: "actually, never mind"
    result = await task
    check(result["status"] == "cancelled", "(c) the superseded call resolves as cancelled, not success")
    check("destination" not in runner.pending, "(c) the slot is cleared after cancellation")
    check(not backend.reroutes, "(c) the cancelled call's tool never actually completed/recorded a reroute")
    superseded_events = [e for e in runner.log.events if e.kind == "superseded"]
    check(len(superseded_events) == 1, "(c) a superseded event was logged")

    # a NEW call in the same slot afterwards proceeds normally
    result2 = await runner.run(
        "reroute_navigation", {"destination": "Downtown"},
        lambda: backend.reroute_navigation("Downtown"),
        slot="destination", state_changing=True,
    )
    check(result2["status"] == "success" and backend.reroutes == ["Downtown"],
          "(c) a fresh call in the same slot after supersession runs normally")

    # (d) repeated failures on the same request -> graceful handoff with a reference -----
    backend = MockBackend(seed=4)
    handoffs = []
    runner = ToolRunner(backoff_base_s=0.01, backoff_cap_s=0.02, max_retries=1,
                        handoff_after_failures=2, timeout_s=2.0)
    all_runners.append(runner)
    runner.on_handoff = lambda tool, call_id, ref: handoffs.append((tool, call_id, ref))

    r_a = await runner.run("call_roadside_assistance", {"issue": "flat tire"},
                           lambda: backend.call_roadside_assistance("flat tire"),
                           slot="roadside", state_changing=True)
    check(r_a["status"] == "failed", "(d) first failed attempt on this request reports 'failed', not handoff yet")
    r_b = await runner.run("call_roadside_assistance", {"issue": "flat tire"},
                           lambda: backend.call_roadside_assistance("flat tire"),
                           slot="roadside", state_changing=True)
    check(r_b["status"] == "handoff", "(d) the second consecutive failure on the same request triggers handoff")
    check(r_b.get("reference", "").startswith("HANDOFF-"), "(d) the handoff result carries a reference number")
    check(len(handoffs) == 1, "(d) on_handoff callback fired exactly once")

    # a call that times out while state-changing is never blindly retried (ambiguous outcome)
    backend2 = MockBackend(seed=5)

    async def hangs_forever(*a, **kw):
        await asyncio.sleep(10)

    runner2 = ToolRunner(timeout_s=0.05, backoff_base_s=0.01, max_retries=3, handoff_after_failures=5)
    all_runners.append(runner2)
    r_timeout = await runner2.run("book_charging_slot", {"station_id": "X", "time_slot": "y"},
                                  lambda: hangs_forever(), slot="ambiguous", state_changing=True)
    retry_events = [e for e in runner2.log.events if e.kind == "retry"]
    check(r_timeout["status"] == "failed" and not retry_events,
          "(d) a state-changing call that times out is never auto-retried (no retry event logged)")

    # (e) everything is logged, and every line is valid JSON -----------------------------
    all_events = [line for r in all_runners for line in r.log.lines()]
    check(len(all_events) > 0, "(e) events were recorded")
    parsed_ok = True
    for line in all_events:
        try:
            json.loads(line)
        except Exception:
            parsed_ok = False
    check(parsed_ok, "(e) every logged event line is valid JSON")
    kinds_seen = {json.loads(l)["kind"] for l in all_events}
    expected_kinds = {"proposed", "started", "succeeded", "failed", "retry", "cancelled",
                      "superseded", "handoff"}
    check(expected_kinds.issubset(kinds_seen), f"(e) all expected event kinds appear: missing {expected_kinds - kinds_seen}")


asyncio.run(scenarios())
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
