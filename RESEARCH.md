# Research: Interruptible Agents (Theme 5)

_Compiled 2026-09-24 from a web research pass, then checked against `harness/scorer.py`, `docs/PROTOCOL.md`, `docs/SCORING.md` and `CLAUDE_HANDOFF.md`. Where published research and the scorer disagree, the scorer wins, because it is the code that grades the hidden set. Section 9 lists every claim that was corrected._

---

## 1. The short version

1. **Build two layers.** A rules-based reflex layer handles acknowledgements and cancellations instantly. An async LLM planner does the understanding in the background. This dual-path design is the published state of the art (RelayS2S, 2026), and it is also what the kit's walkthrough recommends.
2. **Get cancellation right before anything clever.** The newest benchmarks show that the best commercial voice agents fail at exactly this. In Full-Duplex-Bench-v3, even GPT-Realtime passes only 60% of tool-use tasks under disfluency. IHBench finds that agents often keep completing the original task after the user interrupts. Recovery is worth 35 points, so this is where points are won.
3. **Use one multimodal model for audio and images, with no separate speech-recognition step.** In Full-Duplex-Bench-v3, the cascaded pipeline (speech recognition, then LLM, then speech synthesis) was the slowest system at 10.12 s, against 4.25 s for the fastest end-to-end model.
4. **Model choice has moved on.** Gemini 2.5 is now limited to existing users. `gemini-3.8-flash` is the model Google's audio docs use, and it accepts MP3 input directly. `gemini-3.5-flash-lite` is Google's "fastest, most cost-effective 3.5 model" and is the one to test for the fast text planner.
5. **Speculation: mostly no.** Don't act on partial turns, and never call state-modifying tools speculatively. Calling a read-only tool as soon as `end_of_turn` arrives isn't speculation. That's the baseline.

---

## 2. What research says, mapped to each scoring category

| Category | What the research shows | What to do in this harness |
|---|---|---|
| **Task (40)** | Tool-selection accuracy is high in top models (GPT-Realtime F1 0.876 in FDB-v3). Argument accuracy is the weak point (0.680). | Validate args locally against the manifest schema before emitting. Canonicalize slot values to the user's words. Put the grounded facts from the tool result into the final response verbatim. |
| **Recovery (35)** | This is the dominant failure mode in both IHBench and EchoChain. Agents lock in the old intent and finish the original task. | Keep an epoch counter and a call registry. On an interruption, cancel the dependent calls in the same handler tick, and never re-issue a call carrying the invalidated args. |
| **Latency (15)** | People switch turns in about 200 ms, and voice agents typically take 700–1000 ms. A filler hides tool wait time. | Emit a rules-based, content-aware acknowledgement in the same loop tick as `end_of_turn` or the `interruption`. Never await a model before the first speech. |
| **Safety (10)** | Early speech generation that runs ahead of the tool timeline produces false claims. | Lint every spoken line against the scorer's claim patterns before emitting. Never retry state-modifying tools automatically. |
| **Quality ×0.90–1.10** | LLM judges reward content-aware speech over generic phrases. | Make the acknowledgement name the change ("Switching to New York") rather than using a stock line ("Let me check"). Don't repeat yourself. |

---

## 3. Architecture recommendations

### R1: A reflex layer plus an async planner

**What:** two roles sharing one state object.

- **Reflex layer (no model):** runs synchronously inside the event handler on `end_of_turn`, `interruption`, `tool_result` and `scenario_end`. It emits `filler_speech` and `cancel_tool` immediately.
- **Planner (LLM):** runs as a spawned `asyncio` task. It emits `tool_call`, `clarification_request` and `final_response`. It checks the epoch after every `await` and discards its own output if the user has moved on.

**Evidence:** RelayS2S (arXiv 2603.23346) runs a fast duplex model that drafts a response prefix while a slower pipeline generates the rest. VoiceAgentRAG (arXiv 2603.02206) uses the same split for retrieval, with idempotency keys on background actions.

**Risk:** the reflex layer must never claim results the planner hasn't produced. It may acknowledge ("Switching to New York") but must not report outcomes ("Your New York flight is booked").

### R2: A call registry with slot dependencies, cancelled selectively

**What:** record every `tool_call` in `self.pending` as `{call_id, api, args, kind, epoch, depends_on_slots}`. On an interruption, work out which slots changed and cancel only the calls that depend on them. Call IDs must be unique and never reused.

**Evidence:** IHBench and EchoChain penalize both over-cancelling and under-cancelling. LangGraph 1.0 and AutoGen 0.4 both use cooperative cancellation plus checkpointed state.

**Harness specifics (from the scorer):** a stale call is fine if it was cancelled before it completed, or if it completed at or before the interruption. It is a violation if it completes more than 800 ms of *virtual* time after the interruption without being cancelled, if it is still running at shutdown, or if it is re-issued with the old args. Cancel immediately and explicitly.

### R3: A state snapshot on every spoken action, with the final one complete

**What:** attach `state_snapshot = {"intent": ..., "slots": {...}}` as a top-level sibling of `payload` on every `filler_speech`, `clarification_request` and `final_response`. The runner drops snapshots on `tool_call` and `cancel_tool`, so those never reach the scorer.

**What the scorer actually reads:** the *last* snapshot at or after the interruption, across the whole trace. The acknowledgement's snapshot only counts if nothing spoken follows it. The real risk is a later final response whose snapshot still carries stale or incomplete slots.

**Penalty:** a `final_response` without a dict snapshot costs a flat −0.20 of the safety category (`MISSING_SNAPSHOT_DEDUCTION`). `"state_snapshot": None` passes the protocol validator but still fails this check.

### R4: Native multimodal input

**What:** send the raw MP3 or PNG bytes inline to one multimodal model. Google's audio docs support MP3 (`audio/mp3` and `audio/mpeg`) inline, up to 20 MB per request. Ask for a transcript and a confidence value. If a slot is ambiguous, send a `clarification_request` that names the alternatives rather than guessing.

**Evidence:** FDB-v3's cascaded baseline was the slowest configuration it tested. Audio and visual scenarios carry 1.5× weight, and together they make up about 60% of the weighted hidden set.

**Harness specifics:** audio chunks carry `end_of_turn` themselves (PROTOCOL.md, `user_audio_chunk`), so you don't need voice-activity detection or turn prediction. Buffer the audio parts until `end_of_turn`. `pub_06` is a mid-turn self-repair, so acting on the first part is a stale call.

### R5: Speculation last, and only on read-only tools

This is covered in section 5.

---

## 4. Model choice

The Gemini lineup was checked against Google's models page on 2026-09-24. Latency figures from the research pass were measured on Gemini 2.5 and don't carry over to 3.x, so **measure time-to-first-token yourself** on the model IDs you choose.

| Role | Recommendation | Why | Caveat |
|---|---|---|---|
| Reflex layer | Plain Python rules | Zero model latency. The acknowledgement and cancellation happen in the same tick. | Rules only cover shape-level speech, not content decisions. |
| Fast text planner | `gemini-3.5-flash-lite` | Google describes it as the fastest, most cost-effective 3.5 model. It suits intent, slot and tool-argument extraction on text. | Audio input isn't confirmed on the models page, so test it before relying on it for audio. |
| Audio and image understanding | `gemini-3.8-flash` | It's the model used in Google's audio-understanding code examples, and it accepts MP3 inline. It's the newest stable Flash. | Its latency is unmeasured here. Always call it through the async client (`client.aio`) in a spawned task. |
| Transcription only (alternative) | `gemini-3.5-transcribe` | A dedicated audio-to-text model. | This adds a hop, which is the cascaded pattern that benchmarks worst. Use it only if the general model's transcripts are poor. |
| Offline fallback | Gemma 3n (open weights; check for a newer Gemma) | Takes audio, image and text. Loads in `setup()` with no network calls. The organizers encourage Gemma. | The evaluation machine's hardware isn't published. On CPU-class hardware, throughput can be a few tokens per second, which would break the latency budget. Ask the organizers what hardware they use. |

**Not recommended for this harness:**

- **Gemini Live models** (`gemini-3.8-live`, `gemini-3.1-flash-live-preview`) are built for streaming sessions. The harness hands you whole clips and discrete events, so a session API adds setup cost for no benefit.
- **GPT-Realtime** tops FDB-v3 on tool use, but its API is built around streaming audio. It would also need a separate provider and key. (The research pass said it has no image input. That appears outdated, so verify before ruling it in or out.)
- **Claude** accepts images but not raw audio, so the audio scenarios would need a transcriber in front of it.
- **Kyutai Moshi** has no image input and isn't built for tool calling.
- **Qwen3-Omni** is a strong open-weight omni model, but heavy. Only consider it if the evaluation hardware can run it.

`SUBMISSION.md` allows any model. Declare every key name under `env` in `submission.yaml`, and keep the keys out of the repo.

---

## 5. Speculative execution: verdict

**Don't speculate on partial turns, and never speculate on state-modifying tools.** Once `end_of_turn` arrives, call read-only tools right away. That's normal behavior, not speculation.

- **The evidence cuts both ways.** ToolSpec (arXiv 2604.13519) reports an 11.5% latency cut at a 39% hit rate. Cost-Aware Speculative Execution (arXiv 2606.07846) reports 20–48% speedups in favorable conditions. Both require stable inputs and idempotent tools. FDB-v3 finds that early processing "locks in outdated user intents" even in GPT-Realtime.
- **The scorer's asymmetry settles it.** Speculation can only help the 15-point latency category, and the reflex-layer acknowledgement already earns those points. A wrong speculative call risks the 35-point recovery category.
- **There's a cost specific to this harness.** Every tool call increments `MockEnvironment.call_counts`, which shifts the deterministic delays and the targets of injected failures. For example, `pub_08` injects its timeout on the first `flight_search` call. An extra speculative call changes which call fails.

---

## 6. Interruption-handling patterns

1. **Classify the interruption into one of four kinds (plus "unrelated"), because each needs a different response:**
   - **Correction** ("actually, Boston"): cancel the dependent calls, update the slot, and acknowledge with the new value.
   - **Addition** ("and make it Friday"): keep a still-valid call in flight rather than cancelling and re-issuing it. Re-issuing args that still match the invalidated subset counts as a stale call.
   - **Retraction** ("never mind"): cancel everything pending and don't start new work.
   - **Intent change** ("forget the flight, my TV is blinking red"): cancel everything and switch flows.

   Keyword rules catch the clear cases ("never mind", "actually", "instead", "forget"). Let the planner handle the rest, epoch-guarded.
2. **Cancel by slot dependency, not by blanket rule.** Tag each call with the slots it depends on when you issue it.
3. **Acknowledge the change, not the intent.** "Switching to New York" is truthful and specific, while "Let me check that" is generic and risks the −0.15 penalty for a verbatim repeat.
4. **Speak once.** There are about 4 fillers per scenario (`max_fillers`, which can be lower in hidden scenarios), so aim for 3 or fewer. Route extra speech to clarifications and finals, which don't count toward the filler budget.
5. **Handle races.** A `tool_result` for the old call can arrive just before the `interruption`. Drain the queue in batches and handle interruptions before grounding a final on a result from the same batch.

---

## 7. Papers

| # | Paper | Authors, date | Why it matters here | Checked |
|---|---|---|---|---|
| 1 | Full-Duplex-Bench-v3: Benchmarking Tool Use for Full-Duplex Voice Agents Under Real-World Disfluency ([arXiv 2604.04847](https://arxiv.org/abs/2604.04847)) | Lin, Chen, Chen, Lee; Apr 2026 | The closest published benchmark to this theme. GPT-Realtime Pass@1 0.600; Gemini Live 3.1 fastest at 4.25 s; cascaded baseline 10.12 s. | ✔ abstract read |
| 2 | IHBench: Evaluating Post-Interruption Recovery in Voice Agents with Structured Workflows ([arXiv 2606.19595](https://arxiv.org/abs/2606.19595)) | Salimi, Ma, Tang, Shen, Li, Smola; Jun 2026 | Measures the exact skill the Recovery category grades, across 27 model configurations. | ✔ abstract read |
| 3 | RelayS2S: A Dual-Path Speculative Generation for Real-Time Dialogue ([arXiv 2603.23346](https://arxiv.org/abs/2603.23346)) | Mai, Liang; Mar 2026 | The published blueprint for the fast-path/slow-path design. | ✔ abstract read |
| 4 | Moshi: a speech-text foundation model for real-time dialogue ([arXiv 2410.00037](https://arxiv.org/abs/2410.00037)) | Défossez et al., Kyutai; 2024 | The reference full-duplex architecture, with 160–200 ms latency. | Well known |
| 5 | EchoChain: A Full-Duplex Benchmark for State-Update Reasoning Under Interruptions ([arXiv 2604.16456](https://arxiv.org/abs/2604.16456)) | 2026 | Belief-state updates after mid-turn changes, which is what the snapshot checks test. | Not opened |
| 6 | ToolSpec: Accelerating Tool Calling via Schema-Aware and Retrieval-Augmented Speculative Decoding ([arXiv 2604.13519](https://arxiv.org/abs/2604.13519)) | 2026 | Measured gains and waste from speculative tool calls. | Not opened |
| 7 | Cost-Aware Speculative Execution for LLM-Agent Workflows ([arXiv 2606.07846](https://arxiv.org/abs/2606.07846)) | 2026 | A framework for deciding when speculation pays off. | Not opened |
| 8 | AOSpec: Action and Observation Co-Speculation for Low-Latency Agent Serving ([arXiv 2608.00881](https://arxiv.org/abs/2608.00881)) | 2026 | Predicts tool results as well as actions. | Not opened |
| 9 | VoiceAgentRAG: Dual-Agent Architectures for Real-Time Voice Agents ([arXiv 2603.02206](https://arxiv.org/abs/2603.02206)) | 2026 | Dual-agent design with idempotency keys on background actions. | Not opened |
| 10 | Prompt-Guided Turn-Taking Prediction ([arXiv 2506.21191](https://arxiv.org/abs/2506.21191)) | 2025 | Turn-end prediction. It's useful background, but the harness already gives you `end_of_turn`. | Not opened |
| 11 | A Survey of Full-Duplex Spoken Dialogue Systems ([arXiv 2606.19453](https://arxiv.org/abs/2606.19453)) | 2026 | A broad overview of the field. | Not opened |

"Not opened" means the research pass found and cited the paper, but I didn't read it myself. Open it before you cite it in your write-up.

---

## 8. Context: organizers and other teams

- **Likely inspiration (an inference, not confirmed):** the rubric lines up closely with FDB-v3 and IHBench. Task corresponds to tool-use accuracy, Recovery to post-interruption recovery, and Latency to latency. The disfluency scenarios such as `pub_06` match FDB-v3's self-correction category. Reading those two papers is the best preparation for the hidden set's edge cases.
- **Other Theme 5 repos are public.** For example, `github.com/joannamariyajames/interject` exists and says it's a PRISM Y2026 Theme 05 entry. It's a FastAPI and React app with its own design, not built on the kit's harness, so it doesn't transfer much. Treat it as a competitor. Don't copy code, because the top submissions get a manual review.

---

## 9. Corrections made to the research pass

| Research pass said | Actually | Source |
|---|---|---|
| Use Gemini 2.5 Flash-Lite and 2.5 Flash | 2.5 is limited to existing users. Google tells new projects to use 3.5 Flash-Lite or 3.8 Flash. | Gemini models page |
| Missing snapshot costs −0.10 | A flat −0.20 (`MISSING_SNAPSHOT_DEDUCTION`). −0.10 is the per-error protocol penalty. | `scorer.py` lines 19–20, 370–375 |
| Retrying `book_flight` after a timeout costs −0.5 for a duplicate | Only *successful* duplicate completions with identical args count. Still don't retry automatically: it's unsafe, and hidden checkpoints may forbid it. | `scorer.py` line 345 |
| You produce `end_of_turn` yourself for audio, so use voice-activity detection | Audio chunks carry `end_of_turn`, so turn detection isn't needed. | PROTOCOL.md, `user_audio_chunk` |
| A filler with the corrected snapshot banks half the recovery score | The *last* snapshot after the interruption is what's scored, so the final's snapshot decides it. | `scorer.py` `_last_snapshot`; handoff §2 |
| An 800 ms wall-clock cancel window | 800 ms of *virtual* time is slack on when the stale call *completes*. Cancelling before completion always passes. | `scorer.py` recovery; handoff §3.1 |
| Claude has no image input | Claude accepts images. It lacks raw audio input. | Model capabilities |
| GPT-Realtime has no image input | Probably outdated. Verify before deciding. | Needs checking |
| Gemma 3n runs at about 5 tok/s but adds single-digit ms overhead | The two claims contradict each other. The real throughput depends on unknown evaluation hardware. | Internal inconsistency |
| The baseline scores 57 partly because it doesn't use `setup()` | It scores 57 because it keyword-matches and ignores audio (0.0 on both audio scenarios). | Local run |
| Fillers help most with 4+ s tool waits, which matches the kit | The kit's tools take 1.5–3 s. The reason to use a filler here is the 800 ms latency rule. | TOOLS.md delays |

---

## Sources

- [Full-Duplex-Bench-v3 (arXiv 2604.04847)](https://arxiv.org/abs/2604.04847)
- [IHBench (arXiv 2606.19595)](https://arxiv.org/abs/2606.19595)
- [RelayS2S (arXiv 2603.23346)](https://arxiv.org/abs/2603.23346)
- [Moshi (arXiv 2410.00037)](https://arxiv.org/abs/2410.00037)
- [EchoChain (arXiv 2604.16456)](https://arxiv.org/abs/2604.16456)
- [ToolSpec (arXiv 2604.13519)](https://arxiv.org/abs/2604.13519)
- [Cost-Aware Speculative Execution (arXiv 2606.07846)](https://arxiv.org/abs/2606.07846)
- [AOSpec (arXiv 2608.00881)](https://arxiv.org/abs/2608.00881)
- [VoiceAgentRAG (arXiv 2603.02206)](https://arxiv.org/abs/2603.02206)
- [Prompt-Guided Turn-Taking Prediction (arXiv 2506.21191)](https://arxiv.org/abs/2506.21191)
- [Full-Duplex Spoken Dialogue Systems survey (arXiv 2606.19453)](https://arxiv.org/abs/2606.19453)
- [Gemini API models](https://ai.google.dev/gemini-api/docs/models)
- [Gemini API audio understanding](https://ai.google.dev/gemini-api/docs/audio)
- [Gemma 3n developer guide](https://developers.googleblog.com/en/introducing-gemma-3n-developer-guide/)
- [Kyutai Moshi on GitHub](https://github.com/kyutai-labs/moshi)
- [Interject (another team's public Theme 5 repo)](https://github.com/joannamariyajames/interject)
