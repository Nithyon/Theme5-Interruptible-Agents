"""Offline tests: the MCP plugin (mcp_home_server.py, real stdio subprocess, official `mcp`
client) driven THROUGH the recovery layer (ToolRunner) via mcp_bridge.make_plugin_handler.
No network, no LiveKit, no model. Every scenario has a hard timeout.

Run in the separate env (NOT the benchmark env):
  wsl -d Ubuntu bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/mcp_test.sh

Not covered (not run): the LiveKit part of mcp_bridge.py (_make_wrapped / build_wrapped_tools).
Note on (a): a client-side cancel does not un-send a request already on the wire, so the test
holds the first call before it is sent (a slow/queued dispatch) and supersedes it there.
"""
import asyncio
import contextlib
import json
import os
import signal
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp import ClientSession, StdioServerParameters          # noqa: E402
from mcp.client.stdio import stdio_client                     # noqa: E402
from recovery import ToolRunner                               # noqa: E402
import mcp_bridge                                             # noqa: E402

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_home_server.py")
HARD_TIMEOUT = 30.0
fails = 0
passes = 0


def check(cond, msg):
    global fails, passes
    print(("PASS " if cond else "FAIL ") + msg)
    if cond:
        passes += 1
    else:
        fails += 1


@contextlib.asynccontextmanager
async def plugin(delay=None):
    """Start the MCP server subprocess; yield (session, call_remote, read_log)."""
    fd, logpath = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    env = {"EXT_MCP_CALL_LOG": logpath}
    if delay:
        env["EXT_MCP_DELAY_S"] = str(delay)
    params = StdioServerParameters(command=sys.executable, args=[SERVER], env=env)

    def read_log():
        with open(logpath) as f:
            return [json.loads(l) for l in f if l.strip()]

    try:
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                yield session, mcp_bridge.session_caller(session), read_log
    finally:
        os.unlink(logpath)


def handlers(runner, call_remote):
    return {n: mcp_bridge.make_plugin_handler(n, runner, call_remote) for n in mcp_bridge.POLICY}


def seq(log):
    return [(e["tool"], tuple(sorted(e["args"].items()))) for e in log]


async def t_list():
    async with plugin() as (session, _c, _l):
        names = sorted(t.name for t in (await session.list_tools()).tools)
    check(names == ["cancel_washer", "set_ac_temperature", "start_washer"],
          "(0) server lists its 3 tools over stdio")
    check(set(mcp_bridge.POLICY) == {"set_ac_temperature", "start_washer"}
          and mcp_bridge.HIDDEN == {"cancel_washer"},
          "(0) bridge exposes set_ac_temperature and start_washer, hides cancel_washer")


async def t_supersede():
    async with plugin() as (_s, call_remote, read_log):
        runner = ToolRunner(timeout_s=5.0)

        async def held(tool, args):          # slow dispatch: request not yet sent
            await asyncio.sleep(0.6)
            return await call_remote(tool, args)

        h24 = mcp_bridge.make_plugin_handler("set_ac_temperature", runner, held)
        h22 = mcp_bridge.make_plugin_handler("set_ac_temperature", runner, call_remote)
        t24 = asyncio.create_task(h24({"room": "living room", "celsius": 24}))
        await asyncio.sleep(0.1)
        r22 = json.loads(await h22({"room": "living room", "celsius": 22}))   # "no, 22"
        r24 = json.loads(await t24)
        await asyncio.sleep(0.8)              # past the point the held call would have sent
        log = read_log()
    check(r24["status"] == "cancelled", "(a) the superseded AC 24 call resolves as cancelled")
    check(r22["status"] == "success" and r22["celsius"] == 22, "(a) AC 22 succeeds")
    check([e["args"]["celsius"] for e in log if e["tool"] == "set_ac_temperature"] == [22],
          "(a) only 22 reached the plugin server; 24 never did")
    check(len([e for e in runner.log.events if e.kind == "superseded"]) == 1,
          "(a) a superseded event was logged")


async def t_duplicate():
    async with plugin() as (_s, call_remote, read_log):
        runner = ToolRunner(timeout_s=5.0)
        h = handlers(runner, call_remote)
        a = json.loads(await h["start_washer"]({"cycle": "cotton", "delay_minutes": 0}))
        b = json.loads(await h["start_washer"]({"cycle": "Cotton ", "delay_minutes": 0}))
        log = read_log()
    check(a["status"] == "success" and a == b, "(b) duplicate start_washer returns the same job id")
    check(len([e for e in log if e["tool"] == "start_washer"]) == 1,
          "(b) the server saw exactly one start_washer")
    check(len([e for e in runner.log.events if e.kind == "duplicate"]) == 1,
          "(b) the repeat was logged as a duplicate")


async def t_rollback():
    async with plugin() as (_s, call_remote, read_log):
        runner = ToolRunner(timeout_s=5.0)
        rollbacks = []
        runner.on_rollback = lambda *a: rollbacks.append(a)
        h = handlers(runner, call_remote)
        first = json.loads(await h["start_washer"]({"cycle": "cotton", "delay_minutes": 0}))
        second = json.loads(await h["start_washer"]({"cycle": "eco", "delay_minutes": 0}))
        log = read_log()
    tools = [e["tool"] for e in log]
    check(tools == ["start_washer", "cancel_washer", "start_washer"],
          "(c) server saw start(cotton), cancel, start(eco) in that order")
    check(log[1]["args"] == {"job_id": first["job_id"]}, "(c) the cancel targeted the first job id")
    check(log[2]["args"]["cycle"] == "eco" and second["status"] == "success"
          and second["job_id"] != first["job_id"], "(c) eco started with a new job id")
    check(len(rollbacks) == 1 and len([e for e in runner.log.events if e.kind == "rollback"]) == 1,
          "(c) one rollback event / callback")


async def t_outage():
    async with plugin() as (_s, call_remote, read_log):
        runner = ToolRunner(timeout_s=2.0, max_retries=0, backoff_base_s=0.01,
                            handoff_after_failures=2)
        handoffs = []
        runner.on_handoff = lambda *a: handoffs.append(a)
        h = handlers(runner, call_remote)
        ok = json.loads(await h["set_ac_temperature"]({"room": "living room", "celsius": 23}))
        pid = read_log()[0]["pid"]
        os.kill(pid, signal.SIGKILL)          # simulate plugin outage
        await asyncio.sleep(0.3)
        r1 = json.loads(await h["set_ac_temperature"]({"room": "living room", "celsius": 21}))
        r2 = json.loads(await h["set_ac_temperature"]({"room": "living room", "celsius": 20}))
    check(ok["status"] == "success", "(d) call works before the kill")
    check(r1["status"] == "failed", "(d) call after the plugin process is killed fails (no hang)")
    check(r2["status"] == "handoff" and r2["reference"].startswith("HANDOFF-") and len(handoffs) == 1,
          "(d) after the failure threshold a handoff is produced")


async def t_timeout():
    async with plugin(delay=1.0) as (_s, call_remote, read_log):
        runner = ToolRunner(timeout_s=0.3, max_retries=3, backoff_base_s=0.01,
                            handoff_after_failures=5)
        h = handlers(runner, call_remote)
        r = json.loads(await h["start_washer"]({"cycle": "cotton", "delay_minutes": 0}))
        await asyncio.sleep(1.2)              # let a (wrong) retry show up if there were one
        log = read_log()
    check(r["status"] == "failed", "(e) a timed-out start_washer reports failed")
    check(not [e for e in runner.log.events if e.kind == "retry"],
          "(e) no retry event for the timed-out state change")
    check(len([e for e in log if e["tool"] == "start_washer"]) == 1,
          "(e) the server saw exactly one start_washer (not auto-retried)")


async def main():
    for fn in (t_list, t_supersede, t_duplicate, t_rollback, t_outage, t_timeout):
        try:
            await asyncio.wait_for(fn(), HARD_TIMEOUT)
        except BaseException as e:            # noqa: BLE001 - report, keep going
            check(False, f"{fn.__name__} raised {type(e).__name__}: {e}")


asyncio.run(main())
print(f"{passes} PASS, {fails} FAIL")
print("ALL PASS" if not fails else f"{fails} FAILED")
sys.exit(1 if fails else 0)
