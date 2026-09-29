# Score history

Record every scored run: date, what ran, settings, result, where the logs are.

## FDB-v3 (counts for 60% of Round 1)

| Date | Agent / config | Pass rate | Tool F1 | Arg acc. | Latency | Logs |
|---|---|---|---|---|---|---|
| 2026-09-29 | Smoke test: stock template, `gemini3_1`, example `ecommerce_01` (2 recordings), exact-match judge | 1/2 | — | — | first speech 20.1 s, perceived 4.56 s | `runs/2026-09-29_smoke_gemini3_1/` |

Published reference (FDB-v3 paper, arXiv 2604.04847): GPT-Realtime about 0.60 pass@1; Gemini Live 3.1 fastest completion (~4.25 s); cascaded Whisper pipeline slowest (~10.1 s).

## Participant kit (no longer the official score)

| Date | Agent | Setting | Result |
|---|---|---|---|
| 2026-09-25 | ParticipantAgent, no key | `eval_submission.py --reps 1 --time-scale 1` | weighted 83.7; text 100, audio 55.3, visual 72.3 |
| 2026-09-25 | ParticipantAgent | 45 generated scenarios, scale 4 | all 100 |
| 2026-09-25 | ParticipantAgent | `tests/test_traces.py` | 23/23 |
| 2026-09-24 | ParticipantAgent, first version | kit evaluator | weighted 83.7, plain 87.0 |
| 2026-09-20 | BaselineAgent (kit reference) | `run_local.py --all` | 56.6 |
