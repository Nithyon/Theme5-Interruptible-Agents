# Score history

Record every scored run: date, what ran, settings, result, where the logs are.

## FDB-v3 (counts for 60% of Round 1)

| Date | Agent / config | Pass rate | Tool F1 | Arg acc. | Latency | Logs |
|---|---|---|---|---|---|---|
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
