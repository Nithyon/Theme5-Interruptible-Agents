"""Smoke: drive extension/mcp_home_server.py over stdio with the official mcp client."""
import asyncio, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "extension", "mcp_home_server.py")

async def main():
    params = StdioServerParameters(command=sys.executable, args=[os.path.abspath(SERVER)])
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            print("tools:", sorted(t.name for t in (await s.list_tools()).tools))
            for n, a in [("set_ac_temperature", {"room": "living room", "celsius": 22}),
                         ("start_washer", {"cycle": "cotton"})]:
                res = await s.call_tool(n, a); print(n, res.isError, res.structuredContent, [c.text for c in res.content])
            res = await s.call_tool("cancel_washer", {"job_id": "WASH-0001"})
            print("cancel_washer", res.isError, res.structuredContent)
asyncio.run(main())
