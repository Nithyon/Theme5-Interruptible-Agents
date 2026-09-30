"""Offline tests for the home (Bixby-style, mock SmartThings-like) tool pack on the same
recovery layer (no network, no LiveKit, no benchmark). Run with the fdb env's python:
  wsl -d Ubuntu -- ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/test_recovery_home.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recovery import ToolRunner, ToolFailure          # noqa: E402
from mock_tools_home import HomeBackend               # noqa: E402

fails = 0


def check(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg)
    fails += 0 if cond else 1


async def scenarios():
    all_runners = []

    # (a) correction supersedes a pending call: AC 24 -> "no, 22" -------------------------
    backend = HomeBackend(seed=0)
    runner = ToolRunner(timeout_s=5.0)
    all_runners.append(runner)

    async def slow_ac(celsius):
        await asyncio.sleep(2.0)
        return await backend.set_ac_temperature("living room", celsius)

    task = asyncio.create_task(runner.run(
        "set_ac_temperature", {"room": "living room", "celsius": 24},
        lambda: slow_ac(24), slot="ac_temperature", state_changing=True))
    await asyncio.sleep(0.05)
    check("ac_temperature" in runner.pending, "(a) the AC 24 call is pending while in flight")
    runner.supersede("ac_temperature")  # user: "no, 22"
    r24 = await task
    check(r24["status"] == "cancelled", "(a) the superseded AC 24 call resolves as cancelled")
    check(not backend.ac, "(a) the cancelled call never touched the AC")
    r22 = await runner.run("set_ac_temperature", {"room": "living room", "celsius": 22},
                           lambda: backend.set_ac_temperature("living room", 22),
                           slot="ac_temperature", state_changing=True)
    check(r22["status"] == "success" and backend.ac == {"living room": 22},
          "(a) the corrected AC 22 call runs and is the only setting applied")
    check(len([e for e in runner.log.events if e.kind == "superseded"]) == 1,
          "(a) a superseded event was logged")

    # (b) duplicate start_washer -> same job id, no double start ---------------------------
    backend = HomeBackend(seed=1)
    runner = ToolRunner(timeout_s=2.0)
    all_runners.append(runner)
    args = {"cycle": "cotton", "delay_minutes": 0}
    w1 = await runner.run("start_washer", args, lambda: backend.start_washer(**args),
                          slot="washer", state_changing=True)
    w2 = await runner.run("start_washer", args, lambda: backend.start_washer(**args),
                          slot="washer", state_changing=True)
    check(w1["status"] == "success" and w2 == w1, "(b) duplicate start_washer returns the same job id")
    check(len(backend.washer_jobs) == 1, "(b) the washer was only started once")
    check(len([e for e in runner.log.events if e.kind == "duplicate"]) == 1,
          "(b) the repeat was logged as a duplicate, not re-executed")

    # (c) rollback: washer cycle change cancels the old job, then starts the new one -------
    backend = HomeBackend(seed=2)
    rollbacks = []
    runner = ToolRunner(timeout_s=2.0)
    all_runners.append(runner)
    runner.on_rollback = lambda old, comp, new, res: rollbacks.append((old, comp, new, res))

    cotton = {"cycle": "cotton", "delay_minutes": 0}
    first = await runner.run("start_washer", cotton, lambda: backend.start_washer(**cotton),
                             slot="washer", state_changing=True)
    old_id = first["job_id"]
    eco = {"cycle": "eco", "delay_minutes": 0}
    second = await runner.rollback_and_run(
        "start_washer", eco, lambda: backend.start_washer(**eco), slot="washer",
        compensate_tool="cancel_washer", compensate_args={"job_id": old_id},
        compensate_execute=lambda: backend.cancel_washer(old_id))
    check(second["status"] == "success" and second["cycle"] == "eco" and second["job_id"] != old_id,
          "(c) the new eco job starts with a new job id after the cancel")
    check(backend.washer_jobs["cotton|0"].get("cancelled") is True,
          "(c) the old cotton job is marked cancelled in the backend")
    active = [j for j in backend.washer_jobs.values() if not j.get("cancelled")]
    check(len(active) == 1 and active[0]["cycle"] == "eco", "(c) exactly one active washer job remains")
    check(len(rollbacks) == 1 and rollbacks[0][:3] == ("start_washer", "cancel_washer", "start_washer"),
          "(c) on_rollback fired once, naming old, compensating and new tools")
    check(len([e for e in runner.log.events if e.kind == "rollback"]) == 1,
          "(c) exactly one rollback event was logged")

    # (d) cancel fails -> handoff, no second job --------------------------------------------
    backend = HomeBackend(seed=3)
    handoffs = []
    runner = ToolRunner(timeout_s=2.0, backoff_base_s=0.01, backoff_cap_s=0.02, max_retries=0,
                        handoff_after_failures=99)
    all_runners.append(runner)
    runner.on_handoff = lambda tool, call_id, ref: handoffs.append((tool, call_id, ref))
    first = await runner.run("start_washer", cotton, lambda: backend.start_washer(**cotton),
                             slot="washer", state_changing=True)

    async def cancel_down():
        raise ToolFailure("washer cloud connection down")

    blocked = await runner.rollback_and_run(
        "start_washer", eco, lambda: backend.start_washer(**eco), slot="washer",
        compensate_tool="cancel_washer", compensate_args={"job_id": first["job_id"]},
        compensate_execute=cancel_down)
    check(blocked["status"] == "handoff", "(d) a failed cancel routes to human handoff")
    check(len(handoffs) == 1, "(d) on_handoff fired once")
    check("eco|0" not in backend.washer_jobs and len(backend.washer_jobs) == 1,
          "(d) no second washer job was started")
    check(not backend.washer_jobs["cotton|0"].get("cancelled"),
          "(d) the original job was left untouched")

    # (e) slow tool emits progress ----------------------------------------------------------
    backend = HomeBackend(seed=4)
    progress_calls = []
    runner = ToolRunner(progress_after_s=0.05, timeout_s=2.0)
    all_runners.append(runner)
    runner.on_progress = lambda tool, call_id: progress_calls.append((tool, call_id))
    res = await runner.run("check_energy_usage", {"period": "today"},
                           lambda: backend.check_energy_usage("today", delay_range=(0.2, 0.2)),
                           slot="energy", state_changing=False)
    check(res["status"] == "success" and "kwh" in res, "(e) slow energy check still succeeds")
    check(len(progress_calls) >= 1 and progress_calls[0][0] == "check_energy_usage",
          "(e) on_progress fired while the energy check was in flight")

    # (f) flaky tool retried silently -------------------------------------------------------
    backend = HomeBackend(seed=5)
    runner = ToolRunner(backoff_base_s=0.02, backoff_cap_s=0.05, max_retries=2, timeout_s=2.0)
    all_runners.append(runner)
    res = await runner.run("find_phone", {}, lambda: backend.find_phone(),
                           slot="find_phone", state_changing=False)
    check(res["status"] == "success" and res["location"], "(f) find_phone succeeds after silent retries")
    cid = next(e.call_id for e in runner.log.events if e.kind == "succeeded")
    check(len([e for e in runner.log.events if e.kind == "retry" and e.call_id == cid]) == 2,
          "(f) exactly 2 retries logged (fails twice, then succeeds)")

    # (g) dead tool -> handoff after 2 failures ---------------------------------------------
    backend = HomeBackend(seed=6)
    handoffs = []
    runner = ToolRunner(backoff_base_s=0.01, backoff_cap_s=0.02, max_retries=1,
                        handoff_after_failures=2, timeout_s=2.0)
    all_runners.append(runner)
    runner.on_handoff = lambda tool, call_id, ref: handoffs.append((tool, call_id, ref))
    ra = await runner.run("call_service_center", {"issue": "washer leaking"},
                          lambda: backend.call_service_center("washer leaking"),
                          slot="service_center", state_changing=True)
    check(ra["status"] == "failed", "(g) first failure reports 'failed', not handoff yet")
    rb = await runner.run("call_service_center", {"issue": "washer leaking"},
                          lambda: backend.call_service_center("washer leaking"),
                          slot="service_center", state_changing=True)
    check(rb["status"] == "handoff" and rb.get("reference", "").startswith("HANDOFF-"),
          "(g) second consecutive failure hands off with a reference number")
    check(len(handoffs) == 1, "(g) on_handoff fired exactly once")

    # (h) a timed-out state change is never auto-retried ------------------------------------
    async def hangs_forever():
        await asyncio.sleep(10)

    runner = ToolRunner(timeout_s=0.05, backoff_base_s=0.01, max_retries=3, handoff_after_failures=5)
    all_runners.append(runner)
    rt = await runner.run("start_washer", {"cycle": "cotton", "delay_minutes": 0},
                          lambda: hangs_forever(), slot="washer", state_changing=True)
    check(rt["status"] == "failed" and not [e for e in runner.log.events if e.kind == "retry"],
          "(h) a timed-out start_washer is never auto-retried (no retry event)")

    # (i) determinism + log validity --------------------------------------------------------
    ka = [(await HomeBackend(seed=0).check_energy_usage("today", delay_range=(0, 0)))["kwh"] for _ in range(2)]
    check(ka[0] == ka[1], "(i) same seed gives the same energy reading")
    all_events = [line for r in all_runners for line in r.log.lines()]
    ok = True
    for line in all_events:
        try:
            json.loads(line)
        except Exception:
            ok = False
    check(len(all_events) > 0 and ok, "(i) every logged event line is valid JSON")
    kinds = {json.loads(l)["kind"] for l in all_events}
    expected = {"proposed", "started", "succeeded", "failed", "retry", "cancelled",
                "superseded", "handoff", "duplicate", "rollback"}
    check(expected.issubset(kinds), f"(i) all expected event kinds appear: missing {expected - kinds}")


asyncio.run(scenarios())
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
