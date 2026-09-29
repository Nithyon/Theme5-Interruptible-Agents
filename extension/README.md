# Extension: in-car assistant demo

See `DESIGN.md` for the scenario, behaviors, and mermaid diagram. This file is just how to
run the demo once you're ready — **not run in this session** (write-only draft; a benchmark
gate run was in progress, and this needs live LiveKit + Gemini credentials).

## Files

| File | What |
|---|---|
| `recovery.py` | `ToolRunner` — timeout, retry/backoff, idempotency, cancel/supersede, rollback/compensation, progress callbacks, handoff. No LiveKit imports. |
| `mock_tools.py` | 6 deterministic mock tools (`MockBackend`), seed-controlled, including the compensating `cancel_charging_booking`. |
| `ext_agent.py` | The LiveKit agent: wires `InCarAssistant`'s 5 `function_tool`s through a shared `ToolRunner`, speaks progress/handoff/rollback lines. |
| `test_recovery.py` | Offline tests for `recovery.py` (35 checks, all passing — see `project-log/SONNET_TASKS.md` S9, S16 for the rollback/compensation additions). |
| `DESIGN.md` | Scenario, behaviors, architecture diagram, demo script. |

## Prerequisites

Same `.env.local` as the FDB-v3 agent (`~/theme5/Full-Duplex-Bench/v3/.env.local`) — this
demo reuses the same LiveKit project and the same Gemini credentials (`GOOGLE_API_KEY`, or
`GOOGLE_GENAI_USE_VERTEXAI`/`GOOGLE_CLOUD_PROJECT`/`GOOGLE_CLOUD_LOCATION` for Vertex). No
new keys needed — env vars are read by name only, never printed.

## Running it

**Option A — LiveKit Agents Playground (closest to the real demo):**
```bash
cd ~/theme5/Full-Duplex-Bench/v3   # for .env.local's relative load path, same as fdb_agent
LK_PROVIDER=ext_gemini38 python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py dev
```
Then open the LiveKit Agents Playground (agents-playground.livekit.io), connect to the same
LiveKit project, and talk to it — same flow as testing `fdb_agent/gate_agent.py`, just a
different agent script.

**Option B — local console mode (mic/speaker, no LiveKit Cloud room needed):**
```bash
LK_PROVIDER=ext_gemini38 python /mnt/d/Theme5-Interruptible-Agents/extension/ext_agent.py console
```

## Tuning knobs (env vars, all optional, all have defaults in `ext_agent.py`)

| Var | Default | What |
|---|---|---|
| `GEMINI_LIVE_MODEL` | `gemini-3.8-live` | Same model as the FDB-v3 agent, for a fair "same brain, new adapter" comparison |
| `EXT_SEED` | `0` | Seed for `MockBackend` — same seed always gives the same slow/flaky sequence, useful for a repeatable demo take |
| `EXT_TIMEOUT_S` | `9.0` | Per-attempt tool timeout |
| `EXT_MAX_RETRIES` | `2` | Extra attempts after the first, on a plain failure |
| `EXT_BACKOFF_BASE_S` | `0.5` | Backoff base (doubles each retry, capped in `recovery.py`) |
| `EXT_PROGRESS_AFTER_S` | `1.5` | How long before the first "still checking..." |
| `EXT_HANDOFF_AFTER` | `2` | Consecutive failures on one request before handing off to a human |

## What the event log gives you for the video

`ext_agent.py` writes every recovery event (proposed/started/retry/succeeded/failed/
cancelled/superseded/duplicate/handoff) to `/tmp/ext_recovery_events.log` on shutdown, one
JSON line per event — the same idea as the FDB-v3 agent's `/tmp/agent_tool_calls.log`,
so a demo clip can be paired with the actual event trace behind it, the same way the
README's "logs travel with numbers" principle applies to the benchmark runs.

## Suggested demo take (seed 0)

Follow `DESIGN.md`'s 60–90s script. With `EXT_SEED=0` (the default), `find_charging_station`
fails its first two attempts for any given (near, connector) pair before succeeding — so the
"driver only hears the final answer, not the retries" beat in the script will reliably show
up on the first take.
