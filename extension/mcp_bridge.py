"""SKETCH, NOT RUN: route MCP plugin tools through ToolRunner (the recovery layer).

Path: voice model -> (Commit Harness / recovery layer: supersede, dedupe, retry, rollback,
handoff) -> MCP plugin. We call list_tools() ourselves and hand the WRAPPED tools to
AgentSession(tools=...); we do NOT pass mcp_servers= to the session (those calls would bypass
the layer).

Usage (after `pip install mcp` in a separate env, benchmark finished):

    server = MCPServerStdio(command="python", args=["extension/mcp_home_server.py"])
    await server.initialize()
    tools = await build_wrapped_tools(server, runner)
    session = AgentSession(..., tools=tools)

UNVERIFIED (one point): the shape of what MCPServerStdio.list_tools() returns in LiveKit Agents
1.8.3. See the TODO markers below. Nothing here has been imported or executed.
"""
from __future__ import annotations

import json
from typing import Any, Awaitable, Callable, Dict, List

from livekit.agents import llm

from recovery import ToolRunner, _canon

# Same slot / state-changing settings the home pack (ext_agent.py) uses for these tools.
POLICY: Dict[str, Dict[str, Any]] = {
    "set_ac_temperature": {"slot": "ac_temperature", "state_changing": True},
    "start_washer": {"slot": "washer", "state_changing": True,
                     "undo_tool": "cancel_washer", "undo_arg": "job_id"},
    # cancel_washer is the undo step only; the model should not call it directly, so it is
    # not exposed.
}
HIDDEN = {"cancel_washer"}


def _make_wrapped(name: str, schema_tool: Any, runner: ToolRunner, tools_by_name: Dict[str, Any]):
    pol = POLICY[name]
    slot = pol["slot"]

    async def call_remote(tool_name: str, args: Dict[str, Any]) -> Any:
        # TODO(unverified): LIKELY case = list_tools() returned livekit RawFunctionTool objects,
        # invoked as `await tool(raw_arguments)` and returning a string. OTHER case = plain
        # FunctionTool objects with a Python signature: then call `await tool(**args)`.
        # Check with `type(tools[0])` and `llm.is_raw_function_tool(tools[0])` after install.
        raw = await tools_by_name[tool_name](args)
        try:
            return json.loads(raw) if isinstance(raw, str) else raw
        except ValueError:
            return {"status": "success", "text": raw}

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

    # TODO(unverified): LIKELY case = the MCP tool exposes a raw JSON schema at
    # `schema_tool.info.raw_schema` (RawFunctionTool). We re-publish the same schema so the
    # model sees it unchanged. OTHER case = FunctionTool with a Python signature: read
    # argument names/types from its JSON schema (llm.utils / tool.info) and build the wrapper
    # with `llm.function_tool` and matching keyword parameters instead of raw_arguments.
    raw_schema = dict(schema_tool.info.raw_schema)
    raw_schema["name"] = name
    return llm.function_tool(handler, raw_schema=raw_schema)


async def build_wrapped_tools(server: Any, runner: ToolRunner) -> List[Any]:
    listed = await server.list_tools()
    tools_by_name = {t.info.name: t for t in listed}  # TODO(unverified): attribute path
    return [_make_wrapped(n, t, runner, tools_by_name)
            for n, t in tools_by_name.items() if n in POLICY and n not in HIDDEN]
