# Theme 05 — Interruptible Real-Time Agents

Working brief. Everything here is drawn from the official theme guide
(`docs-source/Theme 5_Guide.pdf`) and the participant kit (`participant-kit/`).

---

## 1. The problem, in one idea

You write **one Python class** that lives on the harness's own asyncio event loop.
A user talks to it continuously. The class must **say something real within ~800 ms**,
while the tools that do the actual work take **0.6–3 seconds** to come back.

So you need a **fast path and a slow path** running at the same time. That is the
entire problem.

The guide's own framing:

> Standard AI assistants operate in half-duplex mode (listen, think, speak), failing
> in full-duplex conversations where users interrupt, re-plan, or correct themselves
> mid-sentence. Technically, this is a **concurrency and state-consistency challenge**.

Prescribed architecture — a **dual-process model**:

| layer | responsibility |
|---|---|
| Fast Path | responsive within a few hundred ms: acknowledgment, clarification, progress narration |
| Slow Path | async tools, multimodal processing, complex reasoning |
| Coordination Layer | non-blocking execution, call cancellation, state snapshot updates, idempotency |

The coordination layer is the actual deliverable. Fast and slow paths are easy in
isolation; keeping them consistent when the user barges in is the contest.

---

## 2. The contract

```python
class ParticipantAgent:
    def __init__(self, in_queue, out_queue):   # keep trivial
        ...
    async def setup(self):                     # optional, off the clock, 300 s cap
        ...
    async def run(self):                       # the whole agent
        while True:
            event = await self.in_q.get()
            ...
            await self.out_q.put({"action": ..., "payload": ...})
```

Two queues are the entire interface. Nothing else.

### Seven events in

| event | when |
|---|---|
| `tool_manifest` | always first — schemas of every tool callable this scenario |
| `user_speech_chunk` | pre-transcribed text, with `end_of_turn` flag |
| `user_audio_chunk` | raw MP3 at `audio_ref`, **no transcript** |
| `video_frame` | raw PNG at `image_ref`, **no caption** |
| `interruption` | the user barged in |
| `tool_result` | an earlier call finished; match on `call_id` |
| `scenario_end` | no more user events; 6 s tail to finish |

### Five actions out

| action | payload |
|---|---|
| `filler_speech` | `{"text"}` — budget ~4 per scenario |
| `tool_call` | `{"call_id", "api_name", "args"}` — **always set your own call_id** |
| `cancel_tool` | `{"call_id"}` — the heart of the recovery score |
| `clarification_request` | `{"text"}` |
| `final_response` | `{"text"}` **+ top-level `state_snapshot`** |

---

## 3. Scoring

Per scenario, 0–100:

| category | weight | what it measures |
|---|---|---|
| Task | 40 | right tools, right args, grounded final answer, accurate snapshot |
| Interruption recovery | 35 | cancelled stale calls, no stale re-runs, updated snapshot |
| Latency | 15 | time to first *substantive* spoken action |
| Safety & protocol | 10 | no duplicate state-changing calls, valid payloads |

Absent categories redistribute their weight, so every scenario is out of 100.
Then multiplied by an **LLM quality grade** on relevance, truthfulness, naturalness,
non-redundancy.

Latency curve: `≤800 ms` full credit → `≥2500 ms` zero, linear between.

---

## 4. Three details that are the cheapest points to lose

1. **`state_snapshot` is a top-level sibling of `payload`**, not inside it, and is
   mandatory on every `final_response`. The recovery scorer reads the *latest*
   snapshot after the interruption timestamp — so attach one to your
   post-interruption filler too, or recovery fails even when behavior was right.

2. **Only substantive speech stops the latency clock** — ≥3 chars, ≥50% alphabetic.
   A `tool_call` is not speech. `"..."` earns zero.

3. **A synchronous LLM/HTTP call inside `run()` freezes the entire simulation.**
   Events arrive late and bunched, and the scorer blames *you* for a stale call it
   forced you to emit late. PROTOCOL.md §5 documents a 100 → 61 drop from exactly this.
   Use async clients or `asyncio.to_thread`.

---

## 5. PDF vs kit — three disagreements

| | PDF says | kit says | trust |
|---|---|---|---|
| Audio format | WAV | MP3 (files in `audio/` are `.mp3`) | kit, but sniff the format |
| Quality multiplier | 0.80×–1.20× | 0.90×–1.10× | kit |
| Cancel grace | "within few ms" | 800 ms (`CANCEL_GRACE_MS`) | kit |

`harness/scorer.py` is stated byte-identical to the one grading the hidden set.
The PDF is v1.0.0, written before the kit shipped.

---

## 6. Public vs hidden

**Public (in this kit):** 9 scenarios — 6 text, 2 audio, 1 visual — with
`ground_truth` visible. Unlimited local runs. This is the only feedback during
the event.

**Hidden:** ~60 scenarios, ~10 tools you have never seen, delivered by schema only
via `tool_manifest`. 3 reps per scenario, median taken.

**Multimodal is 60% of the grade**, not 50%:

```
text    30 × 1.0 = 30
audio   18 × 1.5 = 27     →  multimodal = 45 / 75 = 60%
visual  12 × 1.5 = 18
```

Three guarantees from the organizers:
1. Every event type, field, action, and scoring rule used in hidden scenarios
   appears in this kit. Harder *combinations*, never new *mechanics*.
2. Hidden tools follow `docs/TOOLS.md` conventions exactly.
3. The scorer here is the scorer that grades you.

---

## 7. Baseline measurement

`BaselineAgent` across all 9 public scenarios (measured, `--time-scale 8`):

```
OVERALL: 56.6 / 100
  100.0  pub_01_text_simple           56.9  pub_03_text_chained_booking
  100.0  pub_02_text_interrupt         0.0  pub_05_audio_asr_ambiguity
  100.0  pub_04_text_no_tool           0.0  pub_06_audio_disfluency
   47.7  pub_07_visual_port_lookup    56.9  pub_08_text_tool_failure
   47.7  pub_09_text_unseen_tool
```

The two zeros are because `BaselineAgent` ignores `user_audio_chunk` entirely and
stays silent — the scorer's no-participation gate then forces 0.

**Note:** on an audio scenario with no interruption, weights redistribute to
task 61.5 / latency 23.1 / safety 15.4. Simply *acknowledging* the audio event
without understanding a word collects roughly **38 points**. Handling the event
at all is free points.

---

## 8. Constraints

- Python **3.10–3.12** (pure Python; class imported in-process, no subprocess)
- 120 s wall-clock per scenario, 300 s for `setup()`
- Session-scoped memory only, no cross-session caching
- Decision logic lives in the submission, not on your own server
- No secrets in repo; key *names* under `env` in `submission.yaml`

**Disqualifying:** reading `ground_truth`, `_`-prefixed annotations, scenario IDs,
or timestamps to decide behavior. Hardcoding tool names / city lists / expected
strings is manually reviewed.

**Out of scope:** wake-word detection, voice synthesis tuning, UI design. You never
produce audio — "speech" is text in a JSON action.

---

## 9. Environment gaps to fix

- [ ] **`submission.yaml` still says `team: "your-team-name"`.** Only you can fill
      this in. Also add `requirements:` and `env:` entries once you pick a model.
- [ ] **Python version.** This machine has 3.14.0; the kit supports 3.10–3.12 and
      `submission.yaml` declares 3.12. The harness happens to run on 3.14, but local
      numbers aren't a reliable proxy until you're on a supported version.
      Needs a 3.12 virtualenv.
- [ ] **No API key.** `google-genai` 1.75.0 is installed but neither
      `GEMINI_API_KEY` nor `GOOGLE_API_KEY` is set. Gemini isn't mandatory — the
      docs say "any model is welcome" — but audio + visual is 60% of the grade and
      needs *something* multimodal. The organizers encourage Gemini/Gemma and the
      doc examples use `SECRET_GEMINI_API_KEY`.

---

## 10. Suggested build order

1. **Coordination layer + fast path.** No model needed. Fixes recovery (35%) and
   latency (15%) *everywhere*, including on audio/visual scenarios you can't yet
   understand.
2. **Schema-driven tool calling.** Read `tool_manifest`, build args from the schema.
   Tested by `pub_09` and the `unseen_tool` generator template.
3. **Multimodal grounding.** Now you need a model.

Steps 1–2 should move the public set from 56.6 into the 70s with no API key.

The guide's focus areas name **speculative execution** — acting on partial turns
before `end_of_turn` and being ready to discard that work. That's the only hint in
either document about what separates a good score from a winning one.

---

## 11. Commands

```bash
# live trace, one scenario
python run_local.py --scenario scenarios/pub_02_text_interrupt.json

# whole public set, fast, scores only
python run_local.py --all --time-scale 8 --quiet --agent agent.agent:ParticipantAgent

# official setting — trust only this number
python run_local.py --all --time-scale 1 --agent agent.agent:ParticipantAgent

# dump trace + score for inspection
python run_local.py --scenario scenarios/pub_05_audio_asr_ambiguity.json --json out.json

# practice scenarios you did not write
python -m harness.scenario_gen --template search_interrupt --n 10 --seed 1 --out generated/
python -m harness.scenario_gen --template unseen_tool --n 5 --seed 3 --out generated/

# dry-run the official submission procedure
python eval_submission.py . --time-scale 8 --reps 1
python eval_submission.py . --reps 3
```
