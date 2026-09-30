"""Route MCP plugin tools through ToolRunner (the recovery layer).

STATUS: the transport-independent part (POLICY, parse_call_result, session_caller,
make_plugin_handler) RUNS and is tested offline against the official `mcp` client by
test_mcp_plugin.py. The LiveKit-specific part at the bottom (_make_wrapped / build_wrapped_tools,
needs livekit-agents and MCPServerStdio) is NOT RUN: livekit is not installed in mcp-env.

Path: voice model -> (Commit Harness / recovery layer: supersede, dedupe, retry, rollback,
handoff) -> MCP plugin. We call list_tools() ourselves and hand the WRAPPED tools to
AgentSession(tools=...); we do NOT pass mcp_servers= to the session (those calls would bypass
the layer).

LiveKit usage (NOT RUN):

    server = MCPServerStdio(command="python", args=["extension/mcp_home_server.py"])
    await server.initialize()
    tools = await build_wrapped_tools(server, runner)
    session = AgentSession(..., tools=tools)

UNVERIFIED (one point): the shape of what MCPServerStdio.list_tools() returns in LiveKit Agents
1.8.3. See the TODO markers below.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Dict, List

from recovery import ToolFailure, ToolRunner, _canon

# Same slot / state-changing settings the home pack (ext_agent.py) uses for these tools.
POLICY: Dict[str, Dict[str, Any]] = {
    "set_ac_temperature": {"slot": "ac_temperature", "state_changing": True},
    "start_washer": {"slot": "washer", "state_changing": True,
                     "undo_tool": "cancel_washer", "undo_arg": "job_id"},
    # cancel_washer is the undo step only; the model should not call it directly, so it is
    # not exposed.
}
HIDDEN = {"cancel_washer"}


# ---- transport-independent part: RUNS, tested offline ---------------------------------------

def parse_call_result(res: Any) -> Any:
    """MCP CallToolResult -> dict. isError -> ToolFailure (retryable). Text content is JSON."""
    text = "".join(getattr(c, "text", "") for c in (getattr(res, "content", None) or []))
    if getattr(res, "isError", False):
        raise ToolFailure(text or "plugin tool error")
    try:
        return json.loads(text)
    except ValueError:
        return {"status": "success", "text": text}


def session_caller(session: Any) -> Callable[[str, Dict[str, Any]], Awaitable[Any]]:
    """call_remote(tool, args) over an mcp ClientSession. Transport errors (server died, pipe
    closed) become ToolFailure so the runner retries / hands off instead of crashing. A hang is
    bounded by ToolRunner.timeout_s, not here."""
    async def call_remote(tool_name: str, args: Dict[str, Any]) -> Any:
        try:
            res = await session.call_tool(tool_name, args)
        except ToolFailure:
            raise
        except Exception as e:  # noqa: BLE001 - MCPError, ClosedResourceError, BrokenPipe...
            raise ToolFailure(f"plugin transport error: {type(e).__name__}: {e}") from e
        return parse_call_result(res)
    return call_remote


def make_plugin_handler(name: str, runner: ToolRunner,
                        call_remote: Callable[[str, Dict[str, Any]], Awaitable[Any]]):
    """Core: handler(args) -> JSON string, going through the recovery layer (supersede, dedupe,
    retry, rollback via the undo tool, handoff)."""
    pol = POLICY[name]
    slot = pol["slot"]

    async def handler(raw_arguments: Dict[str, Any]) -> str:
        args = dict(raw_arguments)
        undo = pol.get("undo_tool")
        prior = runner.completed.get(slot) if undo else None
        if prior is None or prior.compensated or prior.args_key == name + "|" + _canon(args):
            result = await runner.run(
                name, args, lambda: call_remote(name, args),
                slot=slot, state_changing=pol["state_changing"])
        else:
            # earlier call in this slot already succeeded and the user changed it: undo, then new.
            old_id = prior.result[pol["undo_arg"]]
            result = await runner.rollback_and_run(
                name, args, lambda: call_remote(name, args), slot=slot,
                compensate_tool=undo, compensate_args={pol["undo_arg"]: old_id},
                compensate_execute=lambda: call_remote(undo, {pol["undo_arg"]: old_id}))
        return json.dumps(result)

    return handler


# ---- LiveKit-specific part: NOT RUN (needs livekit-agents + MCPServerStdio) ------------------

def _make_wrapped(name: str, schema_tool: Any, runner: ToolRunner, tools_by_name: Dict[str, Any]):
    async def call_remote(tool_name: str, args: Dict[str, Any]) -> Any:
        # TODO(unverified): LIKELY case = list_tools() returned livekit RawFunctionTool objects,
        # invoked as `await tool(raw_arguments)` and returning a string. OTHER case = plain
        # FunctionTool objects with a Python signature: then call `await tool(**args)`.
        raw = await tools_by_name[tool_name](args)
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            return {"status": "success", "text": raw}

    handler = make_plugin_handler(name, runner, call_remote)

    # TODO(unverified): LIKELY case = the MCP tool exposes a raw JSON schema at
    # `schema_tool.info.raw_schema` (RawFunctionTool); we re-publish it unchanged. OTHER case =
    # FunctionTool with a Python signature: build the wrapper with `llm.function_tool` and
    # matching keyword parameters instead of raw_arguments.
    from livekit.agents import llm  # lazy: keeps this module importable without livekit
    raw_schema = dict(schema_tool.info.raw_schema)
    raw_schema["name"] = name
    return llm.function_tool(handler, raw_schema=raw_schema)


async def build_wrapped_tools(server: Any, runner: ToolRunner) -> List[Any]:
    listed = await server.list_tools()
    tools_by_name = {t.info.name: t for t in listed}  # TODO(unverified): attribute path
    return [_make_wrapped(n, t, runner, tools_by_name)
            for n, t in tools_by_name.items() if n in POLICY and n not in HIDDEN]
