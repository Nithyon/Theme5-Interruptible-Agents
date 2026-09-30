# Plan: plugins (MCP tools) behind the Commit Harness

Status: **designed, not built.** Written 2026-09-30. Names: Commit Harness = `fdb_agent/gate.py`; recovery layer = `extension/recovery.py`.

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
