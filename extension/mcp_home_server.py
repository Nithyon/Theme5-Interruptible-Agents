"""MOCK local MCP server (stdio) exposing three smart-home tools: set_ac_temperature,
start_washer, cancel_washer. Each delegates to HomeBackend (mock_tools_home.py). No real device,
no network.

STATUS: written but NOT yet run. It needs the official `mcp` package, which is deliberately not
installed in the benchmark environment. After the benchmark ends: `pip install mcp` in a
SEPARATE venv, then run this file (see project-log/PLAN_PLUGINS_MCP.md, "Demo plan").

State lives in this process only. Killing the process is how the demo simulates a plugin outage.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP  # noqa: E402  (needs `pip install mcp`)

from mock_tools_home import HomeBackend  # noqa: E402

mcp = FastMCP("home-mock-plugin")
backend = HomeBackend(seed=int(os.environ.get("EXT_SEED", "0")))


@mcp.tool()
async def set_ac_temperature(room: str, celsius: float) -> dict:
    """Set the air conditioner target temperature in a room (degrees Celsius)."""
    return await backend.set_ac_temperature(room, celsius)


@mcp.tool()
async def start_washer(cycle: str, delay_minutes: int = 0) -> dict:
    """Start the washer with a cycle such as 'cotton' or 'eco', optionally delayed."""
    return await backend.start_washer(cycle, delay_minutes)


@mcp.tool()
async def cancel_washer(job_id: str) -> dict:
    """Cancel a washer job by id. Used as the undo step for start_washer."""
    return await backend.cancel_washer(job_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
