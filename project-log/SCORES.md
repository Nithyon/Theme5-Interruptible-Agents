# Score history

Record every scored run: date, what ran, settings, result, where the logs are.

## FDB-v3 (counts for 60% of Round 1)

| Date | Agent / config | Pass rate | Tool F1 | Arg acc. | Latency | Logs |
|---|---|---|---|---|---|---|
| 2026-09-30 | **Submitted configuration**: 29 Sep settings + identifier rule, retraction, backchannel handling, lean setting; Smart Turn OFF (`gate_gemini38_v2b`, second LiveKit project) — strict / **Gemini 2.5 Pro judge** (131/131 parsed, 0 errors) | **55 / 67** | — | — | perceived median 5.28 s; 0 silent recordings | `runs/2026-09-30_full_gate_gemini38_v2b/` |
| 2026-09-30 | Same with Smart Turn ON (`gate_gemini38_v3st`) — strict / Gemini 2.5 Pro judge (126/126 parsed) | 50 / 64 | — | — | 1 silent recording (`housing_01`); about 7 s of blocked event loop per recording from loading the model inside each room | `runs/2026-09-30_full_gate_gemini38_v3st/` |
| 2026-09-30 | Run v2 (same settings as the submitted run), **stopped on purpose at 34/100** to rerun with Smart Turn; exact-match on those 34: 25; 3 silent recordings during minutes when other CPU-heavy jobs ran | partial, not scored | — | — | — | `runs/2026-09-30_full_gate_gemini38_v2/` |
| 2026-09-29 | **Final pipeline** (gate + rules + Jev combined, draft hold, dangling words, prompt v2) — strict / **Gemini 2.5 Pro judge** (119/119 parsed) | **46 / 61** | — | — | first reply median 6.4 s | `runs/2026-09-29_full_gate_gemini38_final/` |
| 2026-09-29 | Baseline re-scored with **Gemini 2.5 Pro judge** (Vertex, benchmark judge prompts unchanged; 121/121 judge replies parsed, 0 fallbacks) | **62/100 (0.62)** | — | — | (same run) | `runs/2026-09-29_full_gemini3_8/gemini3_8_pass_rate_report_geminijudge.json` |
| 2026-09-29 | **Baseline:** stock FDB agent, `gemini-3.8-live` via Vertex, all 100 recordings, exact-match (no judge) | **50/100 (0.50)** | — | — | perceived median 3.92 s | `runs/2026-09-29_full_gemini3_8/` |
| 2026-09-29 | Smoke test: stock template, `gemini3_1`, example `ecommerce_01` (2 recordings), exact-match judge | 1/2 | — | — | first speech 20.1 s, perceived 4.56 s | `runs/2026-09-29_smoke_gemini3_1/` |

Baseline breakdown (exact-match): by #tools 1→0.545, 2→0.50, 3→0.312 · disfluency: pause 0.389, filler 0.448, self-correction 0.471, hesitation 0.50, false start 0.667 · domain: finance 0.88, ecommerce 0.759, travel 0.15, housing 0.115 · failures: wrong args 32, missing tools 10, extra tools 5, missing+extra 3.

Gemini-judged baseline breakdown: domain finance 0.88, ecommerce 0.759, travel 0.65 (exact 0.15), housing 0.192 (exact 0.115) · #tools 1→0.697, 2→0.611, 3→0.312 · self-correction 0.471 (unchanged from exact: these failures are real), pause 0.611, filler 0.655, hesitation 0.70, false start 0.583 · failures: wrong tools 18, wrong args 20 (exact: 32).

Baseline other metrics (Gemini 2.5 Pro judge, `gemini3_8_evaluation_report_geminijudge.json`): turn-take rate 1.00; tool selection acc 0.893; argument acc 0.697; **response quality 0.72**; avg response latency 4.71 s (std 3.05, min 2.72, max 27.04); **interruption rate 0.07** (agent spoke over the user in 7/100).

Baseline latency (`analyze_tool_latency.py`, Gemini judge for key-info timing; interruptions excluded): **first response median 4.00 s** (mean 4.71, N=93); **tool call median 2.29 s** (mean 2.56, N=89); **task completion median 4.00 s** (mean 5.01, N=93); filler sentences 5%.

Final vs baseline (judged): overall 61 vs 62; housing 0.346 vs 0.192; self-correction 0.529 vs 0.471; 3-tool 0.375 vs 0.312; ecommerce 0.586 vs 0.759; pause 0.50 vs 0.611; travel 0.65 = 0.65; finance 0.88 = 0.88. Wrong tools 18 = 18; wrong args 21 vs 20. Of 14 same-tool repeats: 4 parallel pairs kept (all passed), 10 late changes (user resumed 1.4–10.7 s after the first call) all failed.

Published reference (FDB-v3 paper, arXiv 2604.04847): GPT-Realtime about 0.60 pass@1; Gemini Live 3.1 fastest completion (~4.25 s); cascaded Whisper pipeline slowest (~10.1 s).

## Participant kit (no longer the official score)

| Date | Agent | Setting | Result |
|---|---|---|---|
| 2026-09-25 | ParticipantAgent, no key | `eval_submission.py --reps 1 --time-scale 1` | weighted 83.7; text 100, audio 55.3, visual 72.3 |
| 2026-09-25 | ParticipantAgent | 45 generated scenarios, scale 4 | all 100 |
| 2026-09-25 | ParticipantAgent | `tests/test_traces.py` | 23/23 |
| 2026-09-24 | ParticipantAgent, first version | kit evaluator | weighted 83.7, plain 87.0 |
| 2026-09-20 | BaselineAgent (kit reference) | `run_local.py --all` | 56.6 |

## 30 September details

Submitted run (judged): domain shopping 0.828 (24/29), finance 0.88, housing 0.269, travel 0.70 · requests per turn 1→0.712, 2→0.722, 3→0.438 · self-correction 0.412, pause 0.667, filler 0.759, false start 0.667, hesitation 0.70 · failures: wrong tools 10, wrong arguments 23. Strict: shopping 0.828, finance 0.88, housing 0.192, travel 0.20; wrong tools 10, wrong arguments 35.

Smart Turn ON run (judged): shopping 0.862, finance 0.80, housing 0.269, travel 0.60 · 1→0.712, 2→0.556, 3→0.438 · self-correction 0.471, pause 0.667, filler 0.655 · wrong tools 13, wrong arguments 23.

Reply speed, medians from the per-recording result files (`scripts/latency_quick.sh`): perceived latency stock 3.92 s, 29 Sep pipeline 6.40 s, submitted 5.28 s, Smart Turn ON 3.44 s (n=98; its speech-start figure has only 79 usable recordings, so it is not quoted). First tool call after the user stops: stock 2.37 s, 29 Sep 5.31 s, submitted 3.14 s.

What the decision logs show (`scripts/harness_effect.sh`): 29 Sep run 148 calls proposed, 146 executed unchanged, 1 replaced, 1 duplicate blocked. The score difference from the stock agent therefore does not come from replacing calls; prompt rules and the identifier rule are the other differences and were not tested separately. Reasoner (`scripts/jev_usage.sh`): 29 Sep 126 of 269 calls timed out; 30 Sep (first 76 recordings of the submitted run) 8 of 177, average 351 ms.

Selection disclosure: two configurations were run on the benchmark on 30 September and the better one is submitted. Judge for every judged number: Gemini 2.5 Pro with the benchmark's judge prompts unchanged (stand-in for GPT-4o).

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

## Pause test: real speech with silences inside the request (30 September, 23:15 IST)

The same 11 real SLURP recordings, each with one silence of 1.6 to 3.1 s (irregular, fixed seed) inserted at its
longest gap between words, e.g. "turn off the ... 2.8 s ... porch light". The speech is real; the pauses are ours.
Played to the extension's home assistant through LiveKit, tools not failing (`EXT_LIGHTS_FAIL_FIRST=0`).
This agent has the recovery layer but not the Commit Harness. One run; the first attempt failed to connect to
Gemini Live and is kept as `..._attempt1_no_connection`.

| | Same recordings without pauses (earlier run) | With pauses |
|---|---|---|
| Requests that ended with the asked lights action | 10 of 11 | 8 of 11 |
| Requests with a wrong or unrequested action | 0 of 11 | **6 of 11** |
| Requests fully right, with nothing wrong done | 10 of 11 | 5 of 11 |

Wrong actions with pauses: "turn the lights off" turned them on; "light colour for study room" set the study AC to
22 (without pauses it said it cannot change colour); "and the darkness has fallen" set the bedroom AC; "please turn
lights off" also changed the dining-room AC; "light up the lights in the kitchen" first switched on the bedroom,
then the kitchen; after "turn my lights down" it also rang the phone, which nobody asked for.

- By our clock no action came before the request had ended, but the clock is lined up from the agent's session
  start, so it can be off by a second or two; we do not claim that the agent acted during the pause.
- What the run does show: silences inside a request make the plain voice agent mishear and act wrongly, six times in
  eleven. The benchmark agent puts the Commit Harness in front of the tools for this reason; the extension agent does
  not have it yet, and this run supports combining the two.
- Limits: 11 recordings, one run, inserted pauses, the no-pause comparison ran with the lights tool failing on its
  first attempt (that does not cause wrong actions, but the conditions are not identical).
- Evidence: `project-log/runs/2026-09-30_ext_home_slurp_pauses_fail0/` (recovery log, per-request score, agent audio);
  clip builder `extension/e2e/make_clip_slurp_pauses.py`.

### Independent re-run on a second machine (30 September, lead's laptop)

`python extension/eval_fallback.py --model gemma4:26b-a4b-it-qat --timeout 60`, our 40 commands, one run, Windows,
Ollama 0.32.6, Intel Core Ultra 9 275HX, 31.4 GB RAM, NVIDIA RTX 5070 Laptop GPU with 8 GB (the model ran about 69%
on the CPU, 31% on the GPU). Right tool 38/40, fully correct 36/40, self-corrections 6/6, 2 rejected answers (one
used a tool name that does not exist, "roadside_assistance"), median 3.0 s. Aryan's laptop: 40/40, 38/40, 6/6, 0,
5.4 s. The result file is named `_desktop` but the machine is a laptop:
`project-log/runs/2026-09-30_local_fallback_eval_gemma4_26b-a4b-it-qat_desktop.json`.
