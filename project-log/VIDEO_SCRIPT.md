# Video script (3–5 minutes)

> **Names used in this document vs. the code.** Commit Harness = `fdb_agent/gate.py` (`CommitGate`), settings `GATE_*`; Reflex = the rule-based decider in `gate.py`; Reasoner = `fdb_agent/jev.py` (TypeSafe Jev); Listener = `fdb_agent/smart_turn.py` (Smart Turn v3.2). Flow: **Propose -> Settle -> Commit**. Log names such as `gate_events.log` and the event `source` values `"rules"` / `"jev"` are literal and unchanged.

> **How to launch (updated 2026-09-30)**
> - Demo 1 (Commit Harness): `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_gate.sh`, then after Ctrl+C: `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_show_log.sh`
> - Demo 2 (extension): `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_car.sh car` or `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_car.sh home`
> - Run these in the Ubuntu (WSL) terminal; they use the laptop microphone. They have **not yet been rehearsed live**.

Per the participant guide: *"a real interruption being handled on the benchmark, then your extension use case"*, and *"unedited single takes are preferred."* Three parts, budgeted ~2 min / ~2 min / ~30s. Grounded in the actual code paths as of 2026-09-29 (`fdb_agent/gate.py`, `gate_agent.py`, `jev.py`, `extension/DESIGN.md`) — every command, file, and event name below is real, not invented for the script.

**One mechanism worth knowing before recording, so the script doesn't overclaim:** `/tmp/gate_events.log` (the full decision trail — `proposed`, `same_tool_again`, `superseded`, `execute`, etc.) is written **once, at session shutdown/close** (`gate_agent.py`'s `_report()`), not streamed line-by-line during the conversation. Only two event kinds print live to the console via Python logging: `superseded` and `duplicate`. So the honest way to show the decision log is: **have the conversation, let the turn finish, then reveal the log** — not a live-updating dashboard. Don't script it as if the log scrolls in real time next to the audio; it doesn't, and claiming otherwise on camera would be the kind of thing that undermines trust in everything else in the video.

## Part 1 — A real interruption, handled live (~2 min)

**Scenario:** our own dev-set scenario `s31` from `devset/scenarios.jsonl` — *"Track order BOB12... actually, sorry, it's BOB21."* Expected: exactly one `track_order(order_id=BOB21)` call; `track_order(order_id=BOB12)` must never execute. **This is explicitly one of our own practice scenarios, never an FDB-v3 test recording** — say this on camera, it's a real constraint (disqualifying to tune on or demo with the actual test items) and stating it builds credibility, not just covers us.

| | |
|---|---|
| **On screen** | Two windows: left = LiveKit console/Playground showing the live transcript as the scenario is spoken; right = a terminal, initially empty/waiting |
| **Command** | `LK_PROVIDER=gate_gemini38 GATE_PROMPT=2 GATE_DRAFT_HOLD_S=1.0 python fdb_agent/gate_agent.py console` (or `dev` + the Agents Playground, if console mode's audio isn't demo-friendly) |
| **What's said (presenter)** | "This is one of our own practice scenarios — we're never allowed to read or tune on the real benchmark's test recordings, so we built 62 of our own to test this on." Then speaks the scenario line: *"Track order BOB12... actually, sorry, it's BOB21."* |
| **What happens** | Agent responds with BOB21's tracking status. Presenter: "Let's see what the Commit Harness actually did." |
| **Reveal** | `cat /tmp/gate_events.log \| python -m json.tool` (or `tail -1` piped through `json.tool` if other rooms' events are in the same file) — walks through the JSON: a `proposed` event for `track_order(BOB12)`, a `same_tool_again` event with `followup: "correction"` and `source: "rules"` (the Reflex layer) or `"jev"` (the Reasoner), whichever fired, `replace: true`, then a `superseded` event for BOB12, a second `proposed` for BOB21, and an `execute` event — the only one that also appears in the benchmark's own `/tmp/agent_tool_calls.log` |
| **Numbers stated** | Dev-set results only, clearly labeled as dev-set, not benchmark: *"On our own 62-scenario practice set, this design scores 41/62 with 4 stale calls out of 30 correction scenarios."* Then explicitly: **"The actual 100-recording benchmark result is still TBD — that run is in progress and will be in the final submission, not guessed at here."** Show the `TBD` row from `README.md`'s Results table on screen as a placeholder card, don't state a number. |
| **Fallback if something misbehaves live** | If the Reasoner (TypeSafe Jev) times out or errors during the take, the Reflex-only fallback still supersedes correctly — this is a *feature* to narrate ("even if the smarter judge doesn't answer in time, the Reflex layer of the Commit Harness still catches it"), not a failed take. If the LiveKit session itself fails to connect, fall back to narrating over one of the already-completed dev-set runs' real `gate_events.log`/`score.txt` (e.g. run C) instead of faking a live one — say on camera that this is a previously recorded run, not a fresh take, rather than passing it off as live. |

## Part 2 — Extension: in-car assistant, tool recovery (~2 min)

Follows `extension/DESIGN.md`'s demo script directly (same 6 beats, same seed for repeatability).

**Prerequisite, stated plainly:** `extension/ext_agent.py` has not been run yet as of this writing (see `project-log/SONNET_TASKS.md` S10) — **someone must actually run it once as a rehearsal before the real take**, per `IMPROVEMENT_PLAN.md`'s Tier 1 item #3 ("run it once, record it, stop"). This script assumes that rehearsal has happened.

| | |
|---|---|
| **Command** | `LK_PROVIDER=ext_gemini38 EXT_SEED=0 python extension/ext_agent.py console` (seed 0 is deterministic — the same flaky/retry pattern repeats every take, per `extension/README.md`) |
| **Beat 1 (0–15s)** | Driver: *"Reroute to the airport."* → on screen: instant confirmation with an ETA. |
| **Beat 2 (15–30s)** | Driver: *"Actually, check traffic on the way to downtown instead."* → agent says *"Still checking traffic..."* while `check_traffic`'s mock 3–8s delay runs, then reports congestion. Narrate: "that's the progress callback — it never claims a result before it has one." |
| **Beat 3 (30–65s)** | Driver: *"Find me a charging station near downtown, CCS."* → with seed 0, the first two lookups fail internally and retry with backoff before succeeding on the third — **the driver only hears the final answer**, not the retries (narrate this explicitly, since it's invisible on screen otherwise: "under the hood that just failed twice and retried — you never heard that"). Driver: *"Book the 6pm slot."* → confirmed. Driver, as a deliberate test: *"Book it again."* → same booking id comes back, no duplicate booking. |
| **Beat 4 (65–80s)** | Driver, now that the booking has already succeeded: *"Actually, book the Ionity station instead."* → this is **rollback, not supersede** — the first booking already completed, so there's nothing left pending to cancel-in-flight. `ToolRunner.rollback_and_run` compensates first (`cancel_charging_booking` on the Tesla booking), and only then books Ionity; agent says *"Done — I've cancelled the previous booking and booked Ionity instead."* Narrate the safety property explicitly: "if that cancellation had failed, it would have handed off to a human instead of silently booking a second charger" — that's a real code path (`extension/test_recovery.py` scenario (g)), not just a claim. |
| **Beat 5 (80–95s)** | Driver: *"Reroute to the mall instead — no wait, actually, forget it, call roadside assistance, my tire's flat."* → the pending reroute is superseded cleanly (never completes, never gets acted on) — contrast this on camera with Beat 4: this one was still *pending*, so it's a cancel, not a rollback. |
| **Beat 6 (95–120s)** | Roadside assistance fails (the mock is permanently down) — on the second consecutive failure (`EXT_HANDOFF_AFTER=2` default), agent says *"I've passed this to a human agent, reference HANDOFF-0001"* instead of retrying forever or failing silently. |
| **Reveal** | `cat /tmp/ext_recovery_events.log \| python -m json.tool` — same "reveal after, not during" pattern as Part 1, for the same reason (`recovery.py`'s `EventLog` is written on shutdown). |
| **Fallback** | If the charging-station retry doesn't audibly happen within the take (e.g. speech-to-text produces slightly different `near`/`connector_type` text than rehearsal, changing the cache key), just ask for the same station search again on camera — the flaky-then-succeed behavior is keyed per exact argument pair, so a fresh phrasing gets a fresh 2-fail-then-succeed sequence. If the model doesn't naturally re-book on the rollback line, be explicit on camera ("book the Ionity station instead of the Tesla one") — the behavior is triggered by any second `book_charging_slot` call in the same slot, not by specific wording. If `ext_agent.py` itself isn't ready by recording time, this whole part falls back to a voiceover walkthrough of `extension/DESIGN.md`'s architecture diagram and design decisions instead of a live take — say so on camera rather than presenting a mockup as real. |

## Part 2b (optional, ~45 s): Bixby-style home scenario

Same `ext_agent.py` and same recovery layer, different tool pack: `EXT_PACK=home LK_PROVIDER=ext_gemini38 EXT_SEED=0 python extension/ext_agent.py console` (or `demo_car.sh home`). Mock tools, **not a Bixby or SmartThings integration**; say so on camera. Six beats, copied from `extension/README.md` (seed 0):

1. Say: "Set the living room AC to 24 — no, 22." Only 22 is applied; the 24 call is superseded.
2. Say: "How much energy have I used today?" The assistant says it is still checking while the slow tool runs, then reads the kWh.
3. Say: "Find my phone." Two internal failures are retried silently; you only hear where it is.
4. Say: "Start the washer on cotton." One job id is read back. Then say "start the washer on cotton" again: the same job id, no second start.
5. Say: "Actually, make it eco instead." The cotton job is cancelled first, then the eco job starts (`rollback_and_run` with `cancel_washer` as compensation); the assistant says it cancelled the previous wash and started eco.
6. Say: "The washer is leaking, call the service centre." The mock line is permanently down, so after two failures the assistant hands off to a human and reads back `HANDOFF-0001`.

**Reveal (after the take, not during):** `cat /tmp/ext_recovery_events.log | python -m json.tool`, same pattern as Parts 1 and 2. The point of the segment: the recovery layer did not change between the car and home packs. Live status is unconfirmed until rehearsed; if it is not run live, use the fallback voiceover over `extension/README.md` and `test_recovery_home.py` output (28 offline tests) and say so.

## Part 3 — Architecture + results (~30s)

| | |
|---|---|
| **On screen** | The mermaid diagram from `README.md`'s Architecture section (rendered as a static image/slide — most tools render mermaid to SVG/PNG for a deck), then the Results table from `README.md`, exactly as it stands at recording time (including any `TBD` cells — don't fill them in for the video before they're real). |
| **What's said** | One or two sentences: what the Commit Harness does (Propose -> Settle -> Commit: hold until the turn settles, supersede on correction, never re-execute), that it's optionally backed by the Reasoner (TypeSafe Jev) with a Reflex-only fallback, and the honest dev-set finding — *"on our own practice set, the Reasoner roughly ties the Reflex-only Commit Harness, with a small reduction in stale calls; the failures that remain are pauses that come after a sentence that already sounds finished, which no turn judge can predict."* |
| **Command/window** | None — this is a slide/voiceover segment, no live terminal. |
| **Fallback** | If the full benchmark run (config C) has finished by recording time, use the real number instead of TBD — check `project-log/SCORES.md` right before recording this part, since it's the last thing to lock in. |

## General notes for whoever records this

- Total run time budget: ~2 + ~2 + ~0.5 = 4.5 min, inside the 5-minute cap with room to spare for the "TBD" framing lines.
- "Unedited single takes are preferred" — plan Part 1 and Part 2 as genuinely single continuous takes (one scenario each), not multiple cuts stitched together, even though the "reveal the log after" beat means there's a natural pause point.
- Every number spoken on camera should be traceable to a file in `project-log/runs/` or `project-log/SCORES.md` at the moment of recording — if a number changes between now and recording day, re-check this script against the current `README.md` before filming, don't rely on what's written here.
