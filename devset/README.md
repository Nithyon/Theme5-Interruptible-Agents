# Dev set: our own practice scenarios for the commit gate

**Why this exists:** the participant guide disqualifies tuning on FDB-v3's 100 test recordings (`benchmark_data_v2.json`, `ground_truth`, anything in `fdb_v3_data_released/`). To tune the commit gate's quiet window and supersede rule (and later, Jev), we need our own spoken requests with disfluencies and self-corrections, written from scratch against only the public tool definitions in `~/theme5/Full-Duplex-Bench/v3/lk_agent_tool.py` (`class AssistantFnc`). This folder holds that dev set. Nothing benchmark-side was opened to build it.

## `scenarios.jsonl`

40 scenarios, one JSON object per line, 10 per domain (travel, finance, housing, ecommerce), covering all 12 stock tools:

| Field | Meaning |
|---|---|
| `id` | `s01`–`s40` |
| `domain` | `travel` / `finance` / `housing` / `ecommerce` |
| `level` | number of tool calls the turn should produce (1, 2, or 3 — "chained" here means multiple calls in one turn, not one call's output feeding another's argument, since this repo's actual tools — unlike the PDF's `dual_agent.py` sketch — don't pass ids like `flight_id` between calls; see `BUILD_PLAN_FDB_V3.md` note on the built vs. planned architecture) |
| `disfluency` | list from `filler`, `pause`, `hesitation`, `false_start`, `self_correction`; `[]` for a clean control utterance |
| `utterance` | as spoken, with fillers/pauses marked inline (e.g. `[pause 1.2s]`) and `...`/`--` marking a self-repair |
| `expected_calls` | ordered list of `{name, args}` the gate should let through, matching `AssistantFnc`'s exact parameter names |
| `must_not_call` | the stale pre-correction call a naive (non-gated) agent would make early — `null` when there's no correction to resist |
| `expected_answer_gist` | one line describing what the spoken final answer should convey (not exact wording) |

**Coverage (validated by parsing every line):**
- 40/40 valid JSON objects, unique ids, all 12 tools appear in at least one `expected_calls`.
- 25/40 (62.5%) carry `self_correction` — argument changes (destination, date, city, bedrooms, price, currency, amount, order id, product id, quantity, filter value), a full tool-change/cancel ("don't book, do X instead"), and one double-correction.
- 4 scenarios have two genuine, different calls in one turn (not a correction) — the gate must let both through, not merge or drop either (`s04`, `s13`, `s24`, `s33`).
- 4 scenarios chain three calls in one turn, no correction (`s06` also carries a correction; `s17`, `s27`, `s37` are clean three-call turns).
- 5 scenarios (`s09`, `s15`, `s25`, `s30`, `s35`) are pure single-call controls with no disfluency at all, plus 7 more multi-call scenarios that are also disfluency-free — 12 total with nothing to correct, so the gate's false-positive rate (holding/superseding something that didn't need it) can be measured too.

None of the wording, names, or numbers here were copied from or inspired by the FDB-v3 benchmark's own examples — they're original, written only against the tool signatures.

## Turning this into audio (proposal only — not installed or run)

The gate and Jev need real audio with real pauses and real disfluent speech, not just text with `[pause Ns]` markers. Proposal for a **local** TTS pipeline on the RTX 5070, so no API costs or keys:

1. **TTS engine:** [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (already the `BUILD_PLAN_FDB_V3.md` model-choice table's "local" TTS alternative) or [Piper](https://github.com/rhasspy/piper) as a fallback if Kokoro's voice set feels too uniform. Both run comfortably inside 8 GB VRAM.
   - Install (not run): `uv pip install kokoro soundfile` inside `~/theme5/fdb-env` (or a separate `~/theme5/tts-env` to avoid touching the frozen benchmark env), plus `torch` is already present.
2. **Voice variety:** render each scenario with 2–3 different Kokoro voices (it ships several English speakers) so the dev set isn't tuned to one voice's prosody — mirrors FDB-v3's own 12-speaker design.
3. **Real pauses, not silence-by-convention:** parse each `[pause Ns]` / `...` / `--` marker in `utterance` and splice in actual silence of that duration between the surrounding text's synthesized clips (`pydub` or raw `numpy` zero-padding at 24 kHz, matching Kokoro's native rate, then resample to 48 kHz to match the FDB-v3 room format documented in the PDF).
4. **Fillers/hesitations as real speech artifacts:** synthesize "um", "uh", "no wait", "actually" as their own short clips from the same voice and splice them in, rather than relying on the TTS engine to say them naturally (Kokoro/Piper don't reliably produce filled pauses on request).
5. **Output layout:** one folder per scenario under `devset/audio/<id>/`, each with `input.wav` (48 kHz, matching the FDB-v3 recording format) plus a `manifest.json` copied from the scenario line, so the same run/score scripts used for FDB-v3 (`project-log/scripts/smoke_one.sh`-style flow) could in principle stream these into a LiveKit room the same way — but **that step needs a small custom runner, not `run_tool_benchmark.py` itself**, since these aren't FDB-v3 examples and must never be merged into `fdb_v3_data_released/`.
6. **Validation before use:** transcribe our own synthesized output with the same NVIDIA Parakeet ASR the scorer uses (`project-log/scripts/keyfree_checks.sh` already does this for a test tone) to confirm the disfluency markers and corrections actually come through intelligibly before using these clips to tune anything.

Nothing above has been installed or run — this is a proposal for whoever picks up audio generation next, and it deliberately keeps this dev set's audio pipeline separate from the FDB-v3 data folder and scripts.
