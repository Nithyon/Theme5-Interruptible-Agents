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

## Second scenario: Bixby-style home assistant (mock SmartThings-like tools)

The same `ext_agent.py` and the same `ToolRunner` (`recovery.py`) can run a smart-home /
device-assistant scenario instead of the in-car one. The pack is chosen by an environment
variable: `EXT_PACK=car` (default, unchanged) or `EXT_PACK=home`. The home pack lives in
`mock_tools_home.py` (`HomeBackend`) and the `HomeAssistant` tool class in `ext_agent.py`;
its offline tests are in `test_recovery_home.py`.

Run:

```bash
EXT_PACK=home LK_PROVIDER=ext_gemini38 EXT_SEED=0 python extension/ext_agent.py console
```

Tools and which recovery path each one exercises: `set_ac_temperature` (fast, idempotent;
supersede on a correction), `set_lights` (fast), `start_washer` (state-changing, returns a job
id, idempotent so it never double-starts), `cancel_washer` (the rollback compensation for
`start_washer`, not exposed to the model), `check_energy_usage` (3-6 s, "still checking"
progress), `find_phone` (fails twice, then succeeds: silent retry), `call_service_center`
(permanently down: human handoff).

### Demo script (seed 0, six beats)

1. Say: "Set the living room AC to 24 — no, 22." Only 22 is applied; the 24 call is superseded.
2. Say: "How much energy have I used today?" The assistant says it is still checking while the
   slow tool runs, then reads the kWh.
3. Say: "Find my phone." Two internal failures are retried silently; you only hear where it is.
4. Say: "Start the washer on cotton." One job id is read back. Then say "start the washer on
   cotton" again: the same job id, no second start.
5. Say: "Actually, make it eco instead." The cotton job is cancelled first, then the eco job
   starts (`rollback_and_run` with `cancel_washer` as compensation); the assistant says it
   cancelled the previous wash and started eco.
6. Say: "The washer is leaking, call the service centre." The mock line is permanently down, so
   after two failures the assistant hands off to a human and reads back `HANDOFF-0001`.

### Honest note

These are mock tools. This is not an integration with Bixby or SmartThings, and no real device
or vendor API is called. The point is that the recovery layer (timeout, retry/backoff,
idempotency, supersede, rollback, progress, handoff) is scenario-independent: swapping the
tool pack required no change to `recovery.py`.

## Offline fallback with a local Gemma model (evaluation pending)

**What it is.** `local_fallback.py` (`LocalFallback`) is an optional offline tool selector: given a
text command and the tool schemas (`CAR_TOOLS` / `HOME_TOOLS`, mirroring `ext_agent.py`), it asks a
small local Ollama model (`functiongemma`, Google's 270M function-calling Gemma) which tool to call
and returns `{"tool", "args"}`, `{"tool": None}`, or `None` on any error/timeout (default 8 s).
`fallback_eval.jsonl` holds 40 hand-written commands (20 car, 20 home; 6 with a spoken
self-correction, 4 chit-chat); `eval_fallback.py` scores it; `test_local_fallback.py` has offline
tests with a fake HTTP responder (no inference).

**Not part of the benchmark.** This is not in the benchmark pipeline and is not required to
reproduce the benchmark score.

**Risky actions.** State-changing tools (`book_charging_slot`, `cancel_charging_booking`,
`start_washer`, `cancel_washer`, `call_roadside_assistance`, `call_service_center`) are never returned
as executable offline: the result carries `"needs_confirmation": True` and the caller must confirm first.

**Install (userspace, no sudo; what we did on WSL Ubuntu).**
1. Download Ollama (the current Linux asset is `.tar.zst`; if `zstd` is missing, decompress with any
   tool that supports zstd, e.g. Windows `tar`):
   `curl -L --limit-rate 3M -o ~/theme5/ollama/ollama-linux-amd64.tar.zst https://ollama.com/download/ollama-linux-amd64.tar.zst`
   then extract into `~/theme5/ollama/` so `bin/ollama` and `lib/ollama/` exist
   (helper scripts: `project-log/scripts/fb_install_ollama.sh`, `fb_extract_ollama.sh`).
2. Pull the model once: `project-log/scripts/fb_pull_model.sh functiongemma`
   (starts the server with `OLLAMA_MODELS=~/theme5/ollama/models`, pulls, stops it).
3. Run the evaluation (starts and stops the server itself; run only when the machine is idle):
   `wsl -d Ubuntu bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/fallback_eval.sh`
   (add `--limit N` for a partial run). It writes `project-log/runs/<date>_local_fallback_eval.json`.

Offline unit tests: `~/theme5/fdb-env/bin/python extension/test_local_fallback.py`.

**Accuracy (2026-09-30):** measured twice on our 40 test commands (CPU, while the benchmark was running): 11/40 and 13/40 fully correct (27.5% and 32.5%), 0 of 18 in-car commands correct in both runs, 15 to 18 of 40 with no answer. Not usable as built. Both runs were made while a benchmark run was using the machine, against this section's own advice, so repeat on a quiet machine before relying on the numbers. Known causes: runaway generation (fixed by `max_tokens=64`), replies lost in Ollama's parsing of the model's call format (open), wrong argument values from the untuned model (open), server stalls (cause not identified).

**Re-run on a second, idle machine (2026-09-30 evening).** Same 40 commands and `eval_fallback.py`, with `--timeout 30`. The machine was a laptop with an Intel Arc iGPU and no NVIDIA GPU, running Ollama 0.32.14.

| Model | Correct tool | Exact tool + args | Self-corrections exact | No answer | Median latency |
|---|---|---|---|---|---|
| `functiongemma` (270M, the original choice) | 24/40 | 15/40 | 1/6 | 11 | 0.8 s |
| `qwen3:30b-a3b-instruct-2507-q4_K_M` | 38/40 | 36/40 | 6/6 | 2 (30 s timeouts) | 2.2 s |
| **`gemma4:26b-a4b-it-qat`** | **40/40** | **38/40** | **6/6** | **0** | **5.4 s** |

- **Gemma 4 26B needed a fix first.** Its first run returned nothing on 38 of 40 commands. The cause: Gemma 4 "thinks" by default and spent the whole 64-token budget on it, so no tool call came out. `local_fallback.py` now sends `think: False` (the fix is in the diff); functiongemma's numbers are unchanged by it. The broken run is kept as `..._thinking_on_BROKEN.json`.
- **What the misses are.** Gemma's two misses are free-text `issue` wording ("the car won't start" vs "car won't start"). Qwen's two wording misses dropped "the" from a place name. Its two timeouts may have been caused by another model loading on the same GPU during the run.
- **Gemma 4 26B is a large model** (15 GB). It needs a strong laptop or a GPU and takes about 5.4 s per command here. That makes it a fallback for a PC or a car computer, not for a phone or an appliance.
- **Safety rule unchanged.** State-changing tools still come back with `needs_confirmation: True` and are never executed offline.
- **Not part of the benchmark.** This is still not in the benchmark pipeline. It is measured on typed commands, not audio, and one run per model.
- **Result files:** `project-log/runs/2026-09-30_local_fallback_eval_*_laptop.json`.

Offline tests on the same laptop (Python 3.12):
- `test_recovery.py` 35/35, `test_recovery_home.py` 28/28, `test_local_fallback.py` 11/11 and `test_mcp_plugin.py` 19/19.
- The MCP test needs `mcp<2`; mcp 2.x renamed FastMCP and the import fails.

## End-to-end runs on audio (2026-09-30)

Run end to end on audio on 2026-09-30: a recorded request clip (our own lines, synthetic voice) was streamed through LiveKit to the extension agent the way the benchmark streams its recordings, and the agent's spoken replies and the recovery log were saved. **In-car EV assistant (the headline scenario), `project-log/runs/2026-09-30_ext_car_e2e/`:** a corrected reroute (one call), a traffic check, a charger lookup that failed twice and succeeded on the third try, a booking, a repeated booking that was not re-executed, a change of time that cancelled the first booking before making the new one, and two failed roadside requests ending in a hand-off with a reference. The home pack was run the same way (`runs/2026-09-30_ext_home_e2e*/`). Each folder has `conversation.wav` (the whole exchange), the recovery log and the agent log. Limits: one run per scenario, no live human speaker, and the spoken progress notice for slow tools is switched off because the model read its instruction aloud (see `WORKLOG.md`).

To repeat: `python extension/e2e/make_clip_car.py` (in the text-to-speech environment) builds the request clip; `bash project-log/scripts/ext_e2e_car.sh` starts the agent, streams the clip with the benchmark's runner and saves the results (`ext_e2e.sh` and `make_clip.py` do the same for the home pack). Do not run it while a benchmark run is using the same LiveKit project.

What the first attempts found and fixed: `session.say(text)` is not available on a speech-to-speech session (it crashed the tool on rollback); recovery events are now written as they happen; the model read callback instructions aloud, so hand-off and rollback are announced from the tool result and the progress notice is off; a prompt rule stops the model from claiming a transfer when a tool only failed. The first attempts are kept in `runs/*_attempt1` and `*_attempt2`.

## Update, late 30 September: real speech for the extension, and the fallback re-measured

**Extension on real recordings (SLURP).** SLURP (Bastianelli et al., EMNLP 2020) is a published set of real people giving
home-assistant commands; its audio licence is CC BY-NC 4.0. We took one shard of its test split and selected by a fixed
rule, without listening: light-control intents, headset recordings, one per sentence, in file order (5 off, 2 on, 2 dim,
2 up = 11 recordings). They were joined with 11 s of silence between them and played to the home assistant through LiveKit,
the way the benchmark plays its recordings. The lights tool was set to fail on the first attempt of each new request
(`EXT_LIGHTS_FAIL_FIRST=1`).

| | Attempt 1 | After the fix |
|---|---|---|
| Requests that ended in a lights action with the asked state | 9 of 11 | 10 of 11 |
| Injected first-attempt failures, recovered by a retry | 4 of 4 | 8 of 8 |
| Requests answered from an earlier identical request | 5 | 0 |
| Hand-offs | 0 | 0 |

- Attempt 1 exposed a defect in the no-repeat rule: "lights on", then "dim", then "turn up the brightness" produced the same
  call as the first request and was answered from memory, so the lights stayed dimmed while the agent said they were up.
  Fix in `extension/recovery.py`: a repeat is answered from memory only while it still matches the latest completed action
  of that kind. Offline tests still pass (35 and 28).
- Not done in either run: "light colour for study room" (we have no colour tool; the agent said so). "Turn off bedroom light
  at nine thirty pm" was declined in attempt 1 and, in the second run, switched off at once with the agent saying it cannot
  schedule; we count that as a lights action, not as a correct handling of the time.
- Limits: 11 recordings, one run after the fix, the room is not scored (most requests name none and the agent picks one),
  brightness is logged but not scored, mock tools. The SLURP audio is not stored in the repository;
  `extension/e2e/make_clip_slurp.py` rebuilds the clip from the dataset.
- Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/` and `..._attempt1/` (recovery log, per-request score,
  agent audio). Run script: `project-log/scripts/ext_e2e_slurp.sh`.

**Local fallback re-measured (teammate's laptop, idle; our own 40 typed commands; one run each).**

| Model | Right tool | Fully correct | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|
| FunctionGemma (300 MB) | 24/40 | 15/40 | 1/6 | 11 | 0.8 s |
| Qwen3 30B | 38/40 | 36/40 | 6/6 | 2 | 2.2 s |
| Gemma 4 26B, thinking on (before the fix) | 2/40 | 2/40 | 0/6 | 38 | 10.2 s |
| Gemma 4 26B, thinking off | 40/40 | 38/40 | 6/6 | 0 | 5.4 s |

Gemma 4 spent its whole reply limit on hidden thinking and returned no tool call; `"think": False` in the request fixes it.
The earlier statement "about 30% correct, not usable" holds for FunctionGemma only. Gemma 4 26B is a large model, suited to
a PC or a car computer, not a phone. The fallback is still not attached to the voice agent and is not part of the benchmark
score. Result files: `project-log/runs/2026-09-30_local_fallback_eval_*_laptop*.json`.

## Fallback test suite (`fallback_suite.py`)

One command, two small text sets, several runs, and a record of the machine:

```bash
python extension/fallback_suite.py --model gemma4:26b-a4b-it-qat --runs 3 --timeout 30
```

| Set | File | What it checks |
|---|---|---|
| own | `fallback_eval.jsonl` (40) | Commands we wrote for the car and home tools, 6 with a self-correction |
| slurp | `fallback_eval_slurp.jsonl` (111) | Real user requests from the SLURP test set (Bastianelli et al., EMNLP 2020, text CC BY 4.0): 51 light-control requests (right tool, right on/off) and 60 requests none of our tools can serve (the model must not act) |

- Needs a running Ollama with the model pulled (`ollama pull <model>`). Nothing else to download: both sets are in the repo (18 KB).
- Output folder `project-log/runs/<date>_fallback_suite_<model>/`: `machine.json` (CPU, RAM, Ollama version, tokens per second), one result file per set and run with every command and the model's answer, `summary.md` with a table.
- Time: about 5 s per command on a CPU-only laptop, so about 13 minutes per run of both sets. `--runs 1` for a single pass, `--sets slurp` for one set, `--limit 10` for a quick check.
- The mapping from SLURP intent to our tool is ours (`make_fallback_slurp.py`); room and brightness are not scored because most requests name no room. Typed text, no audio.

## Local fallback on Aryan's laptop (30 September, 22:07 to 22:30 IST)

Measured by Aryan with `extension/fallback_suite.py`, one run, typed text.

**Device.** Intel Core Ultra 7 258V laptop (8 cores), 32 GB RAM, no discrete or NVIDIA GPU (the integrated Arc
graphics shares system RAM; Ollama placed 8.3 GB of the model there). Linux (CachyOS), Ollama 0.32.14. Model
`gemma4:26b-a4b-it-qat` (25.2B parameters, Q4_0, 15.9 GB loaded). 16.4 tokens per second as measured by the suite.
Details: `project-log/runs/2026-09-30_fallback_suite_gemma4_26b-a4b-it-qat/machine.json` and `machine_note.txt`.

| Set | Right tool | Right tool and values | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|
| Our 40 commands | 36/36 | 34/36 | 4/4 | 6/6 | 0 | 5.6 s |
| 111 real SLURP requests | 46/51 | 45/51 (right on/off) | 60/60 | n/a | 0 | 6.0 s |

- It never acted on a request none of our tools can serve (60 of 60), which matters most for a fallback that runs
  without the cloud.
- The 8 misses: 2 requests asking for something the tool cannot do (a scheduled time, a colour), 2 vague wordings
  ("and the darkness has fallen"), 2 in our own set where the model's free text ("the car won't start") did not
  exactly match our expected text ("won't start"), 1 request about a screen that SLURP labels as lights, and 1 real
  error: "no lights in the kitchen" turned the lights on. The exact-text and mislabelled cases are arguably scoring
  artefacts; we report the measured score, not an adjusted one.
- One run only: three runs would not have finished before the deadline, so stability across runs is not measured.
- It is not wired into the voice agent and is not part of the benchmark score.
- A third set, `fallback_eval_interrupt.jsonl` (37 commands we wrote: corrected values, "never mind", hesitations,
  "no rush"), was added after this run and has not been run with Gemma 4. The small FunctionGemma on our desktop scores
  13 of 29 on its action commands and stays out on 0 of 8 cancellations
  (`project-log/runs/2026-09-30_fallback_suite_functiongemma/`).

### Model size against accuracy (same laptop, same settings)

| Model | Loaded size | Runs | Our 40: right tool and values | SLURP lights: right | SLURP "no tool fits": left alone | Self-corrections | Median time |
|---|---|---|---|---|---|---|---|
| Gemma 4 26B (`gemma4:26b-a4b-it-qat`) | 15.9 GB | 1 | 34/36 | 45/51 | 60/60 | 6/6 | 5.6 to 6.0 s |
| Gemma 4 e4b (`gemma4:e4b-it-qat`) | 3.1 GB | 3 | 34/36 | 18/51 | 60/60 | 6/6 | 1.7 to 2.1 s |

- On our own 40 commands the two models tie; the small one is about three times faster.
- On the real SLURP requests the small one fails: 31 of its 33 misses are requests it declined, including plain ones
  such as "turn the lights off". Our hand-written set hid this difference; only the real requests showed it.
- A likely cause, not tested: our lights tool requires a room, most SLURP requests name none, and the small model
  declines instead of choosing one. Making the room optional is the obvious next experiment.
- The small model gave identical answers in all 3 runs. Neither model ever acted when no tool fitted.
- Recounted from the per-run result files (`project-log/scripts/suite_check.py`); folders
  `project-log/runs/2026-09-30_fallback_suite_gemma4_26b-a4b-it-qat/` and `..._gemma4_e4b-it-qat/`.
