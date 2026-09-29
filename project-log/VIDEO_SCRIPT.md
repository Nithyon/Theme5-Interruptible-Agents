# Video script (3–5 minutes)

Per the participant guide: *"a real interruption being handled on the benchmark, then your extension use case"*, and *"unedited single takes are preferred."* Three parts, budgeted ~2 min / ~2 min / ~30s. Grounded in the actual code paths as of 2026-09-29 (`fdb_agent/gate.py`, `gate_agent.py`, `jev.py`, `extension/DESIGN.md`) — every command, file, and event name below is real, not invented for the script.

**One mechanism worth knowing before recording, so the script doesn't overclaim:** `/tmp/gate_events.log` (the full decision trail — `proposed`, `same_tool_again`, `superseded`, `execute`, etc.) is written **once, at session shutdown/close** (`gate_agent.py`'s `_report()`), not streamed line-by-line during the conversation. Only two event kinds print live to the console via Python logging: `superseded` and `duplicate`. So the honest way to show the decision log is: **have the conversation, let the turn finish, then reveal the log** — not a live-updating dashboard. Don't script it as if the log scrolls in real time next to the audio; it doesn't, and claiming otherwise on camera would be the kind of thing that undermines trust in everything else in the video.

## Part 1 — A real interruption, handled live (~2 min)

**Scenario:** our own dev-set scenario `s31` from `devset/scenarios.jsonl` — *"Track order BOB12... actually, sorry, it's BOB21."* Expected: exactly one `track_order(order_id=BOB21)` call; `track_order(order_id=BOB12)` must never execute. **This is explicitly one of our own practice scenarios, never an FDB-v3 test recording** — say this on camera, it's a real constraint (disqualifying to tune on or demo with the actual test items) and stating it builds credibility, not just covers us.

| | |
|---|---|
| **On screen** | Two windows: left = LiveKit console/Playground showing the live transcript as the scenario is spoken; right = a terminal, initially empty/waiting |
| **Command** | `LK_PROVIDER=gate_gemini38 GATE_PROMPT=2 GATE_DRAFT_HOLD_S=1.0 python fdb_agent/gate_agent.py console` (or `dev` + the Agents Playground, if console mode's audio isn't demo-friendly) |
| **What's said (presenter)** | "This is one of our own practice scenarios — we're never allowed to read or tune on the real benchmark's test recordings, so we built 62 of our own to test this on." Then speaks the scenario line: *"Track order BOB12... actually, sorry, it's BOB21."* |
| **What happens** | Agent responds with BOB21's tracking status. Presenter: "Let's see what the gate actually did." |
| **Reveal** | `cat /tmp/gate_events.log \| python -m json.tool` (or `tail -1` piped through `json.tool` if other rooms' events are in the same file) — walks through the JSON: a `proposed` event for `track_order(BOB12)`, a `same_tool_again` event with `followup: "correction"` and `source: "rules"` or `"jev"` (whichever fired), `replace: true`, then a `superseded` event for BOB12, a second `proposed` for BOB21, and an `execute` event — the only one that also appears in the benchmark's own `/tmp/agent_tool_calls.log` |
| **Numbers stated** | Dev-set results only, clearly labeled as dev-set, not benchmark: *"On our own 62-scenario practice set, this design scores 41/62 with 4 stale calls out of 30 correction scenarios."* Then explicitly: **"The actual 100-recording benchmark result is still TBD — that run is in progress and will be in the final submission, not guessed at here."** Show the `TBD` row from `README.md`'s Results table on screen as a placeholder card, don't state a number. |
| **Fallback if something misbehaves live** | If Jev times out or errors during the take, the rules-only fallback still supersedes correctly — this is a *feature* to narrate ("even if the smarter judge doesn't answer in time, the rule-based gate still catches it"), not a failed take. If the LiveKit session itself fails to connect, fall back to narrating over one of the already-completed dev-set runs' real `gate_events.log`/`score.txt` (e.g. run C) instead of faking a live one — say on camera that this is a previously recorded run, not a fresh take, rather than passing it off as live. |

## Part 2 — Extension: in-car assistant, tool recovery (~2 min)

Follows `extension/DESIGN.md`'s demo script directly (same 5 beats, same seed for repeatability).

**Prerequisite, stated plainly:** `extension/ext_agent.py` has not been run yet as of this writing (see `project-log/SONNET_TASKS.md` S10) — **someone must actually run it once as a rehearsal before the real take**, per `IMPROVEMENT_PLAN.md`'s Tier 1 item #3 ("run it once, record it, stop"). This script assumes that rehearsal has happened.

| | |
|---|---|
| **Command** | `LK_PROVIDER=ext_gemini38 EXT_SEED=0 python extension/ext_agent.py console` (seed 0 is deterministic — the same flaky/retry pattern repeats every take, per `extension/README.md`) |
| **Beat 1 (0–15s)** | Driver: *"Reroute to the airport."* → on screen: instant confirmation with an ETA. |
| **Beat 2 (15–30s)** | Driver: *"Actually, check traffic on the way to downtown instead."* → agent says *"Still checking traffic..."* while `check_traffic`'s mock 3–8s delay runs, then reports congestion. Narrate: "that's the progress callback — it never claims a result before it has one." |
| **Beat 3 (30–65s)** | Driver: *"Find me a charging station near downtown, CCS."* → with seed 0, the first two lookups fail internally and retry with backoff before succeeding on the third — **the driver only hears the final answer**, not the retries (narrate this explicitly, since it's invisible on screen otherwise: "under the hood that just failed twice and retried — you never heard that"). Driver: *"Book the 6pm slot."* → confirmed. Driver, as a deliberate test: *"Book it again."* → same booking id comes back, no duplicate booking. |
| **Beat 4 (65–85s)** | Driver: *"Reroute to the mall instead — no wait, actually, forget it, call roadside assistance, my tire's flat."* → the pending reroute is superseded cleanly (never completes, never gets acted on). |
| **Beat 5 (85–110s)** | Roadside assistance fails (the mock is permanently down) — on the second consecutive failure (`EXT_HANDOFF_AFTER=2` default), agent says *"I've passed this to a human agent, reference HANDOFF-0001"* instead of retrying forever or failing silently. |
| **Reveal** | `cat /tmp/ext_recovery_events.log \| python -m json.tool` — same "reveal after, not during" pattern as Part 1, for the same reason (`recovery.py`'s `EventLog` is written on shutdown). |
| **Fallback** | If the charging-station retry doesn't audibly happen within the take (e.g. speech-to-text produces slightly different `near`/`connector_type` text than rehearsal, changing the cache key), just ask for the same station search again on camera — the flaky-then-succeed behavior is keyed per exact argument pair, so a fresh phrasing gets a fresh 2-fail-then-succeed sequence. If `ext_agent.py` itself isn't ready by recording time, this whole part falls back to a voiceover walkthrough of `extension/DESIGN.md`'s architecture diagram and design decisions instead of a live take — say so on camera rather than presenting a mockup as real. |

## Part 3 — Architecture + results (~30s)

| | |
|---|---|
| **On screen** | The mermaid diagram from `README.md`'s Architecture section (rendered as a static image/slide — most tools render mermaid to SVG/PNG for a deck), then the Results table from `README.md`, exactly as it stands at recording time (including any `TBD` cells — don't fill them in for the video before they're real). |
| **What's said** | One or two sentences: what the commit gate does (hold until the turn settles, supersede on correction, never re-execute), that it's optionally backed by Jev with a rules-only fallback, and the honest dev-set finding — *"on our own practice set, Jev roughly ties the rules-only gate, with a small reduction in stale calls; the failures that remain are pauses that come after a sentence that already sounds finished, which no turn judge can predict."* |
| **Command/window** | None — this is a slide/voiceover segment, no live terminal. |
| **Fallback** | If the full benchmark run (config C) has finished by recording time, use the real number instead of TBD — check `project-log/SCORES.md` right before recording this part, since it's the last thing to lock in. |

## General notes for whoever records this

- Total run time budget: ~2 + ~2 + ~0.5 = 4.5 min, inside the 5-minute cap with room to spare for the "TBD" framing lines.
- "Unedited single takes are preferred" — plan Part 1 and Part 2 as genuinely single continuous takes (one scenario each), not multiple cuts stitched together, even though the "reveal the log after" beat means there's a natural pause point.
- Every number spoken on camera should be traceable to a file in `project-log/runs/` or `project-log/SCORES.md` at the moment of recording — if a number changes between now and recording day, re-check this script against the current `README.md` before filming, don't rely on what's written here.
