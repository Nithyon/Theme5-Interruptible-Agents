# Plan: plugins (MCP tools) behind the Commit Harness

Status: **plugin server and recovery path run and are tested offline (19 checks in `extension/test_mcp_plugin.py`, real stdio MCP subprocess); not yet attached to the live voice agent, and the LiveKit wrapping in `mcp_bridge.py` is not run.** Written 2026-09-30. Names: Commit Harness = `fdb_agent/gate.py`; recovery layer = `extension/recovery.py`.

## Why it fits the theme
The theme is an agent that stays responsive while tools run, acts only on what the user finally meant, and recovers when a tool is slow or fails. A plugin is a tool that is slow, remote and unreliable by nature, so it is the case our two layers were built for. Nothing new has to be invented; plugins are more tools behind the same two layers.

## What we checked (in our installed LiveKit Agents 1.8.3)
- MCP is supported natively: `AgentSession(mcp_servers=[...])` and `Agent(mcp_servers=[...])`, with `MCPServerHTTP`, `MCPServerStdio`, `MCPToolset` in `livekit/agents/llm/mcp.py`; each server has `list_tools()`.
- The `mcp` Python package is **not** installed in our environment. It would be an optional extra, kept out of the pinned benchmark environment.
- Not checked: whether tools returned by `list_tools()` have the same shape as the function tools our wrapper (`gate_tools`) handles. If they are raw-schema tools, the wrapper needs a second branch that reads argument names from the JSON schema instead of a Python signature.

## Design
1. **Load, then wrap.** Do not hand `mcp_servers` to the session directly (those calls would skip the harness). Call `list_tools()` ourselves, wrap every tool, pass the wrapped list as `tools=`. The model sees unchanged schemas.
2. **One policy entry per tool**, in a small table (`plugins.yaml`):

| Field | Meaning | Example: Drive search | Example: Calendar create |
|---|---|---|---|
| `kind` | read / write | read | write |
| `slot` | calls that replace each other on a correction | `drive.search` | `calendar.event` |
| `timeout_s`, `retries` | recovery settings | 8 s, 2 | 10 s, 0 (never auto-retry a timed-out write) |
| `idempotency` | key for "same request" | query text | title + start time |
| `undo` | compensation tool for rollback | none | `calendar.delete_event` |
| `confirm` | read back before running | no | yes, if irreversible |
| `progress_line` | what to say while waiting | "Searching your Drive…" | "Adding that to your calendar…" |

3. **Path of a plugin call:** model proposes → Commit Harness (Propose → Settle → Commit: hold until the turn settles, supersede on correction, withdraw on retraction, no duplicates) → recovery layer (timeout, retry with backoff for reads, idempotency, rollback with `undo`, human handoff) → MCP server.
4. **Unknown tools are treated as writes with no retry and a read-back**, so a newly added plugin is safe by default.
5. **Tool-result safety:** text returned by a plugin is data. It is summarized to the user and never treated as an instruction to call further tools.

## Scenarios this gives us
- "Add a meeting with Priya at 3… no, 4 pm." → one calendar event at 4 pm; the 3 pm call is superseded before it runs.
- "Find the Q3 report in Drive." (slow) → "Searching your Drive…" within about a second, result when ready; a timeout is retried once, then reported honestly.
- "Book it… actually cancel that." after the event exists → `undo` runs (`delete_event`), and the agent says what it undid.
- Plugin server down → two failures, then handoff with a reference, never silence.

## Build steps and time
| Step | Time | Note |
|---|---|---|
| 1. Local MCP server (stdio) exposing our home mock tools | 30 min | No external account; proves the path end to end |
| 2. Loader + wrapper branch for MCP tools + `plugins.yaml` | 45 min | The unverified point above decides how much work |
| 3. Offline tests (supersede, no duplicate, retry, rollback, handoff) through the MCP path | 30 min | Same cases as `test_recovery_home.py` |
| 4. One real plugin (Drive search, read-only) | 45 min + OAuth setup | Read-only first: nothing to roll back |
| 5. Live run and a demo beat | 20 min | |

Steps 1–3 (about 1 h 45 min) give a working "plugin" demo without any account. Step 4 needs credentials and is the only part with an external dependency.

## Risks
- A second network hop makes slow tools slower; the progress line and the must-speak watchdog matter more.
- OAuth tokens for real plugins must stay out of the repo and logs.
- More tools in the prompt can lower tool-selection accuracy in the voice model (the FDB-v3 agents have 12 tools); load only the plugins a scenario needs.

## Demo plan (offline path tested; live voice attachment not run)
What now runs (2026-09-30): `extension/mcp_home_server.py` (stdio MCP mock: set_ac_temperature, start_washer, cancel_washer) starts and answers the official `mcp` 1.30 client. Through `ToolRunner` (via `mcp_bridge.make_plugin_handler`, transport-independent), 19 offline checks pass: correction supersedes a pending call (only 22 reaches the server), duplicate start_washer gives one job, cotton -> eco rolls back (start, cancel, start), a killed plugin process gives failures then a handoff with no hang, a timed-out state change is not retried. The supersede test holds the first call before it is sent; a request already on the wire is not un-sent by a client cancel.
Still NOT run: the LiveKit part of `extension/mcp_bridge.py` (`_make_wrapped`, `build_wrapped_tools`, `MCPServerStdio`, unverified TODOs), any attachment to `ext_agent.py` or a live voice session, and the three beats below by voice. Note `mcp` must be `<2` (2.x renamed FastMCP).

Reproduce:
1. Create env: `wsl -d Ubuntu bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/mcp_env_setup.sh`
2. Run tests: `wsl -d Ubuntu bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/mcp_test.sh` (expect `19 PASS, 0 FAIL`)

Path shown: voice model -> Commit Harness / recovery layer -> plugin.

### (a) Three beats, about 40 seconds
| Beat | Say | Viewer sees | Log revealed after |
|---|---|---|---|
| 1 (10 s) | "Set the bedroom AC to 24, no, 22." | Plugin panel shows one `set_ac_temperature` call with 22. Agent: "Bedroom AC set to 22." | `proposed` 24 -> `superseded` -> `proposed` 22 -> `success`; 24 never reached the plugin |
| 2 (15 s) | "Start the washer on cotton." then "make it eco." | Panel: `start_washer cotton` (WASH-0001), then `cancel_washer WASH-0001`, then `start_washer eco` (WASH-0002). Agent says what it undid. | `rollback` event with the compensating call, then the new job |
| 3 (15 s) | Kill the plugin process by hand, then "set the bedroom AC to 20." | Agent gives a progress line, retries, then a handoff line with a reference | two `failed` events, then `handoff HANDOFF-0001` |

The event log is shown after each beat, as in VIDEO_SCRIPT.md. Beat 3 needs the failure count to reach the handoff threshold (default 3 failed run() calls per slot, each with retries); expect to repeat the request or lower `handoff_after_failures` for the demo. Not tested.

### (b) Setup, only AFTER the benchmark ends
1. Separate env: `~/theme5/mcp-env` already exists with `mcp<2` (done); add `livekit-agents==1.8.3` there only after the benchmark ends. Do not touch the benchmark env.
2. First check (done, passes): `python extension/mcp_home_server.py` sits waiting on stdin; `test_mcp_plugin.py` drives it.
3. In a Python shell, start `MCPServerStdio(command="python", args=["extension/mcp_home_server.py"])`, `await server.initialize()`, and print `type(t)` and `t.info` for each of `await server.list_tools()`. This settles the unverified TODOs in `mcp_bridge.py`; fix the bridge to match.
4. Add a flag in `ext_agent.py` to use `build_wrapped_tools(...)` instead of the home pack (not written yet). Run the three beats once off camera.

### (c) Fallback if there is no time
Show the plan slide and say: "designed, not built." Do not show the sketch files as working, and do not describe the demo as run.

### (d) What this proves / does not prove
- Proves (if the beats run): correction, undo and failure handling apply unchanged to a tool the agent did not define, across a process boundary.
- Does not prove: behaviour with a real third-party plugin, real OAuth, or real network latency; the plugin is our own mock.
- Does not prove that model tool-selection stays accurate with many plugin tools loaded.
