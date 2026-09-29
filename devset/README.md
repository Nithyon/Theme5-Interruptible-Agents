# Dev set: our own practice scenarios for the commit gate

**Why this exists:** the participant guide disqualifies tuning on FDB-v3's 100 test recordings (`benchmark_data_v2.json`, `ground_truth`, anything in `fdb_v3_data_released/`). To tune the commit gate's quiet window and supersede rule (and later, Jev), we need our own spoken requests with disfluencies and self-corrections, written from scratch against only the public tool definitions in `~/theme5/Full-Duplex-Bench/v3/lk_agent_tool.py` (`class AssistantFnc`). This folder holds that dev set. Nothing benchmark-side was opened to build it.

## `scenarios.jsonl`

50 scenarios, one JSON object per line, covering all 12 stock tools (`s01`–`s40`: 10 per domain across travel/finance/housing/ecommerce; `s41`–`s50`: 10 more added for S11, focused specifically on `pause`/`hesitation` disfluency, since only 2 of the original 40 carried those tags):

| Field | Meaning |
|---|---|
| `id` | `s01`–`s50` |
| `domain` | `travel` / `finance` / `housing` / `ecommerce` |
| `level` | number of tool calls the turn should produce (1, 2, or 3 — "chained" here means multiple calls in one turn, not one call's output feeding another's argument, since this repo's actual tools — unlike the PDF's `dual_agent.py` sketch — don't pass ids like `flight_id` between calls; see `BUILD_PLAN_FDB_V3.md` note on the built vs. planned architecture) |
| `disfluency` | list from `filler`, `pause`, `hesitation`, `false_start`, `self_correction`; `[]` for a clean control utterance |
| `utterance` | as spoken, with fillers/pauses marked inline (e.g. `[pause 1.2s]`) and `...`/`--` marking a self-repair |
| `expected_calls` | ordered list of `{name, args}` the gate should let through, matching `AssistantFnc`'s exact parameter names |
| `must_not_call` | the stale pre-correction call a naive (non-gated) agent would make early — `null` when there's no correction to resist |
| `expected_answer_gist` | one line describing what the spoken final answer should convey (not exact wording) |

**Coverage (validated by parsing every line):**
- 50/50 valid JSON objects, unique ids, all 12 tools appear in at least one `expected_calls`.
- 10 of the 50 (`s41`–`s50`) are dedicated pause/hesitation scenarios added in S11 — bringing the total with a `pause` or `hesitation` tag from 4 (out of the original 40) to 14 (out of 50), since pause/hesitation was previously the thinnest-covered category here.
- 25/40 of the original set (62.5%) carry `self_correction` — argument changes (destination, date, city, bedrooms, price, currency, amount, order id, product id, quantity, filter value), a full tool-change/cancel ("don't book, do X instead"), and one double-correction.
- 4 scenarios have two genuine, different calls in one turn (not a correction) — the gate must let both through, not merge or drop either (`s04`, `s13`, `s24`, `s33`).
- 4 scenarios chain three calls in one turn, no correction (`s06` also carries a correction; `s17`, `s27`, `s37` are clean three-call turns).
- 5 scenarios (`s09`, `s15`, `s25`, `s30`, `s35`) are pure single-call controls with no disfluency at all, plus 7 more multi-call scenarios that are also disfluency-free — 12 total with nothing to correct, so the gate's false-positive rate (holding/superseding something that didn't need it) can be measured too.

None of the wording, names, or numbers here were copied from or inspired by the FDB-v3 benchmark's own examples — they're original, written only against the tool signatures.

## Turning this into audio (`make_audio.py` — written, not yet installed or run)

The gate and Jev need real audio with real pauses and real disfluent speech, not just text with `[pause Ns]` markers. `devset/make_audio.py` implements this with a **local** TTS pipeline, so no API costs or keys:

1. **TTS engine:** [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), the same model `BUILD_PLAN_FDB_V3.md`'s model-choice table names as the local TTS alternative. Runs comfortably inside 8 GB VRAM (or CPU, just slower).
   - **Install into a separate venv, never `~/theme5/fdb-env`** (that one's frozen for the benchmark; see `project-log/runs/env-freeze.txt`):
     ```bash
     python3 -m venv ~/theme5/tts-env
     source ~/theme5/tts-env/bin/activate
     pip install kokoro soundfile librosa numpy
     # Kokoro needs espeak-ng for some languages/fallback phonemization:
     sudo apt install espeak-ng   # Ubuntu; harmless if already present
     ```
   - Not installed or run in this session — do this yourself when ready.
2. **Voice variety:** `make_audio.py --voices af_heart,am_adam` (default) renders every scenario with 2 Kokoro voices; pass more comma-separated voice ids for more variety. Mirrors FDB-v3's own 12-speaker design, at a smaller scale.
3. **Real pauses, not silence-by-convention:** `make_audio.py` parses each `[pause Ns]` marker and splices in actual zero-signal silence of that duration at Kokoro's native sample rate, between the surrounding text's synthesized clips, then resamples the whole thing to 48kHz mono 16-bit PCM — verified against one real benchmark `input.wav`'s header (mono, 48000 Hz; header only, never its content) to match the format `run_tool_benchmark_all_released.py` expects.
4. **Fillers/hesitations as real speech artifacts:** words like "um", "uh", "actually", "no wait" are just part of the surrounding text segment and get synthesized normally by Kokoro in context, not stitched in from a separate clip — simpler than treating them specially, and Kokoro handles them as ordinary tokens fine.
5. **Output layout — reuses the benchmark's own runner, doesn't reinvent one:** `make_audio.py` writes `devset/audio/<scenario_id>_<24-hex-fake-speaker-id>/input.wav` + `metadata.json`, matching exactly the "released flat layout" `run_tool_benchmark_all_released.py` already knows how to walk (`discover_inputs_released()`, folder regex `^(.+)_([0-9a-f]{24})$`). Passing `--root_dir devset/audio` to that same script (see `run_dev.sh`) makes it process our scenarios exactly like the real 100 — loading `benchmark_data_v2.json` if present (it won't be, under `devset/audio/`) and falling back to `{}`, then merging in every folder's own `metadata.json` — **so no FDB-v3 data file is read or needed to run this.** `metadata.json`'s `expected_tool_calls` key name (`"function"`, not `"name"`) was taken directly from reading `evaluate_pass_rate.py`'s own code, not guessed.
6. **Validation before use:** transcribe our own synthesized output with the same NVIDIA Parakeet ASR the scorer uses (`project-log/scripts/keyfree_checks.sh` already does this for a test tone) to confirm the disfluency markers and corrections actually come through intelligibly before using these clips to tune anything.

## Running the dev set (`run_dev.sh` + `score_dev.py` — written, not yet run)

Once `devset/audio/` exists (via `make_audio.py`) and the gate run has finished (never run this at the same time — they share `/tmp/agent_tool_calls.log` and the LiveKit project):

```bash
wsl -d Ubuntu -- bash -lc "bash /mnt/d/Theme5-Interruptible-Agents/devset/run_dev.sh dev_gate_gemini38 /mnt/d/Theme5-Interruptible-Agents/fdb_agent/gate_agent.py"
```

This starts the agent, runs `run_tool_benchmark_all_released.py --root_dir devset/audio`, then calls `score_dev.py`, which reads each `result_<provider>.json` and scores it against `scenarios.jsonl`: **strict pass** (multiset tool-name match, no missing/no extra, then exact-match args after light normalization — the same rule `evaluate_pass_rate.py` applies, read directly from that file) and a **`must_not_call` hit rate** (how often the stale pre-correction call shows up in `actual_tool_calls` — this should be as close to 0% as possible; a nonzero rate means the gate let a stale call through). Prints a per-row table plus a summary with a domain breakdown.

Nothing in this section has been installed or run in this session — the scripts exist and are `py_compile`-clean, ready for whoever runs them next, and this dev set's audio pipeline stays entirely separate from the FDB-v3 data folder and scripts.
