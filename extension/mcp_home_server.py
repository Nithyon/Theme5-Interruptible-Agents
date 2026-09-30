"""MOCK local MCP server (stdio) exposing three smart-home tools: set_ac_temperature,
start_washer, cancel_washer. Each delegates to HomeBackend (mock_tools_home.py). No real device,
no network.

STATUS: runs over stdio and is exercised offline by test_mcp_plugin.py (official `mcp` client).
Needs `mcp<2` (FastMCP was renamed in mcp 2.x) in a SEPARATE env, never the benchmark env:
project-log/scripts/mcp_env_setup.sh creates ~/theme5/mcp-env.

State lives in this process only. Killing the process is how the demo simulates a plugin outage.

Test hooks (env vars, off by default): EXT_MCP_CALL_LOG=<file> appends one JSON line per tool
call as it arrives (tool, args, pid); EXT_MCP_DELAY_S=<sec> delays each tool to simulate a slow
plugin.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP  # noqa: E402  (needs `pip install "mcp<2"`)

from mock_tools_home import HomeBackend  # noqa: E402

mcp = FastMCP("home-mock-plugin")
backend = HomeBackend(seed=int(os.environ.get("EXT_SEED", "0")))


async def _enter(tool: str, args: dict) -> None:
    path = os.environ.get("EXT_MCP_CALL_LOG")
    if path:
        with open(path, "a") as f:
            f.write(json.dumps({"tool": tool, "args": args, "pid": os.getpid()}) + "\n")
    delay = float(os.environ.get("EXT_MCP_DELAY_S", "0"))
    if delay:
        await asyncio.sleep(delay)


@mcp.tool()
async def set_ac_temperature(room: str, celsius: float) -> dict:
    """Set the air conditioner target temperature in a room (degrees Celsius)."""
    await _enter("set_ac_temperature", {"room": room, "celsius": celsius})
    return await backend.set_ac_temperature(room, celsius)


@mcp.tool()
async def start_washer(cycle: str, delay_minutes: int = 0) -> dict:
    """Start the washer with a cycle such as 'cotton' or 'eco', optionally delayed."""
    await _enter("start_washer", {"cycle": cycle, "delay_minutes": delay_minutes})
    return await backend.start_washer(cycle, delay_minutes)


@mcp.tool()
async def cancel_washer(job_id: str) -> dict:
    """Cancel a washer job by id. Used as the undo step for start_washer."""
    await _enter("cancel_washer", {"job_id": job_id})
    return await backend.cancel_washer(job_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
