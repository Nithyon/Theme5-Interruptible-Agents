# Build plan: Theme 5 on Full-Duplex-Bench v3

_Written 2026-09-29 from the updated participant guide and a read of the FDB-v3 code (`github.com/DanielLin94144/Full-Duplex-Bench`, `v3/`). Only the benchmark's code and data schema were read, not the test items' dialogue or expected answers._

## 1. How the benchmark actually works

1. **Two processes.** Your agent runs as a LiveKit agent (`python agent.py start`). A second script (`run_tool_benchmark_all_released.py`) takes each of 100 recordings, opens a fresh LiveKit room, and streams `input.wav` into it in real time as if a user were speaking.
2. **The recording is the whole conversation.** Each `input.wav` holds all of the user's turns, with hesitations, false starts and self-corrections. Your agent's speech is recorded into a buffer **the same length as the input**, so anything said after the input (plus 1.5 s of silence) ends is lost.
3. **Tool calls come from your agent's own log.** Every tool function writes one line to `/tmp/agent_tool_calls.log` when it runs. The scorer reads that file. **A call is counted the moment it executes**, including calls made on a value the user corrects a second later.
4. **Scoring** (gpt-4o as judge):
   - **Strict pass rate**: the set of tool names called must equal the expected set exactly (multiset: no missing, **no extra**, duplicates count as extra), and every call's arguments must match. Arguments are paired in call order per function, so an early wrong call is compared instead of the later right one.
   - **Tool-selection F1**, **argument accuracy**, **response accuracy** (spoken answer, transcribed with NVIDIA Parakeet ASR), **latency** (first speech after the user finishes, tool timing).
   - Breakdowns by domain, difficulty (easy/medium/hard = 1–3 chained calls), disfluency type, and **state-rollback** scenarios.
5. **Tools.** 12 fixed mock tools in 4 domains: travel (`search_flights`, `book_flight`, `update_identity_doc`), finance (`get_card_benefits`, `get_exchange_rate`, `modify_autopay`), housing (`search_apartments`, `calculate_commute`, `update_search_filter`), e-commerce (`track_order`, `search_products`, `add_to_cart`). Chained calls reference earlier results (`$RESULT_0.flights[0].flight_id`).

**The consequence that decides the design:** the scoring punishes acting too early. If the user says "Boston… no, sorry, New York" and the agent calls `search_flights("Boston")` before the correction, the scenario fails even if the New York call follows. Published results agree: GPT-Realtime passes about 60% and fails most self-correction cases because it commits early. That is the gap to win.

## 2. Recommended architecture

A LiveKit agent where **our code, not the model, decides when a tool actually runs**.

```
user audio ─► VAD + streaming STT ─► turn text (interim + final)
                                         │
                            LLM planner (tool calling)
                                         │ proposed call
                                         ▼
                              ┌─ COMMIT GATE (ours) ─┐
  interim transcript ───────► │ hold until the turn   │ ─► execute + log (once)
  "no, actually…" cues ─────► │ is final; replace a   │
                              │ superseded call; drop │
                              │ duplicates; never     │
                              │ repeat a state change │
                              └──────────────────────┘
                                         │ result
                                         ▼
          instant spoken ack (TTS)   grounded answer (TTS)
```

- **Commit gate.** A proposed call is held until the user's turn is final (VAD silence past a threshold, no trailing correction cue, no newer proposal for the same function). A newer proposal for the same function replaces the held one. Only the survivor executes and is logged. State-changing tools (`book_flight`, `update_identity_doc`, `modify_autopay`, `update_search_filter`, `add_to_cart`) are never executed twice with the same arguments.
- **Honest logging.** The log line is written only when the mock tool really executes. Deferring the execution itself is the legitimate behavior the theme asks for ("discard stale intent, update tool arguments"); suppressing log lines for calls that did run would be gaming, and the video and Round 2 would expose it.
- **Instant acknowledgement.** Speak a short, truthful line as soon as the turn ends ("Let me look up flights to New York"), then the grounded answer. Never claim a result before the tool returns.
- **Chaining.** Keep results in session state so the second call (e.g. booking the flight just found) uses real returned IDs.

### Two ways to build it; start with A

| | A. Realtime model + commit gate | B. Cascaded (STT → LLM → TTS) + commit gate |
|---|---|---|
| Base | `lk_agent_tool.py` with `gpt_realtime` or `gemini3_1` | `cascaded_agent.py` pattern |
| Gate placement | inside each tool function: wait for turn end, drop superseded calls, return "superseded" to the model | between the LLM's tool call and execution; we also see interim transcripts |
| Control over corrections | medium (the model still decides when to call) | full |
| Latency | best (speech-to-speech) | higher (three hops), mitigated by instant ack |
| Effort | small: wrap 12 functions | larger: pipeline tuning |

Plan: build A first (fast win on the biggest failure mode), measure, then move to B only if the per-disfluency breakdown shows the realtime model still commits too early.

### Which realtime model (from the guide's Artificial Analysis link, read 2026-09-29)

The leaderboard ranks speech-to-speech models on speech reasoning, conversational dynamics (Full-Duplex-Bench: pauses, turn-taking, interruptions, backchannels), task success (τ-Voice tool calling), time to first audio and cost. Values below were extracted by a page summarizer; confirm on the page before quoting them in slides.

| Model | Task success | Conv. dynamics | First audio | Cost / hour of audio | In the FDB-v3 templates? |
|---|---|---|---|---|---|
| Grok Voice Think Fast 2.0 High | 94.6% | 95.1% | 0.70 s | $4.80 | `grok` (xAI plugin; check which version it uses) |
| Gemini 3.8 Live | 93.2% | 96.1% | 1.18 s | $0.84 | no (template has 3.1 Flash Live); may work by changing the model id |
| GPT-Realtime-2.1 High | 91.5% | 95.7% | 1.21 s | $10.75 | no (template has 1.5) |
| GPT-Realtime-1.5 | 85.1% | 95.7% | 0.81 s | $11.44 | `gpt_realtime` |
| Gemini 3.1 Flash Live (Minimal / High) | 74.6% / 71.8% | 72.3% / 74.3% | 0.96 s / 2.99 s | $1.50 / $1.75 | `gemini3_1` |

Take-aways: the templates pin older models; newer ones score much higher on tool use. **Gemini 3.8 Live** looks like the best value (high task success, cheapest, and you already have a Gemini key), and **Grok** the best accuracy-plus-speed. First check that LiveKit's plugins accept these model ids, then pick by a small dev-set comparison, with the commit gate on each.

### Optional decision layer: TypeSafe Jev (researched 2026-09-29)

Jev returns typed choices with probabilities (70–500 ms, $0.042 per million input tokens, output free) and generates no text or audio. It sits **on top of** the voice model as the brain of the commit gate:

| Question asked of Jev each time a transcript update or tool proposal arrives | Choices | What it buys |
|---|---|---|
| Is the user done with this request, or likely still correcting? | `final` / `still_speaking` / `correcting` | Commit as soon as `final` is confident instead of waiting a fixed silence timeout: **lower latency**, fewer early calls |
| What did the new words do to the pending call? | `correction` / `addition` / `retraction` / `new_request` / `backchannel` | Replace, extend, drop or keep the held call |
| Does this proposed call repeat an action already executed? | `duplicate` / `new` | Never perform a state change twice |

How it plugs in: interim and final transcripts from LiveKit (`user_input_transcribed`) plus the held tool proposal go to Jev through the async `typesafe-sdk` client; the gate acts on its answer. Jev calls can start on interim transcripts (speculatively, like Deepgram Flux's `EagerEndOfTurn` in public Jev voice-agent demos) and are cheap enough to ask several questions in one call.

Limits: text only (it never hears audio, so turn-ending still needs VAD/STT); it doesn't build tool arguments (the LLM does); every call is a network hop, so it runs in parallel with a timeout and the rule-based gate is the fallback. A LiveKit plugin was proposed (`livekit/agents` issue #7355, closed, no released package), so use `typesafe-sdk` directly. It is a hosted API, which the guide allows: declare it and the `TYPESAFE_API_KEY` in the README and reproduction script.

Keep it only if it measurably improves pass rate or latency on our own dev set versus the rules-only gate.

### What carries over from the participant-kit agent
Cancellation and supersession logic, idempotency keys for state-changing calls, argument validation against schemas, claim lint (no "booked" before success), self-correction detection, and the research in `RESEARCH.md`. The kit's queue harness and scorer do not carry over.

## 3. Use-case extension (20%)
Device troubleshooting with a camera frame: the user points the camera at a device and asks "what is this port for?", then changes their mind mid-question. This reuses the `pub_07` work (frame understanding, manual lookup, hybrid embedding). LiveKit carries video tracks, and Gemini's live model accepts video. It must run end to end on camera in the demo video.

## 4. Phases

1. **Setup (half a day).**
   - Windows is not supported as-is: the code writes to `/tmp`, needs `ffmpeg`, and uses NVIDIA NeMo for ASR. Use **WSL2 Ubuntu** with Python 3.10 (conda), per the repo README. The RTX 5070 needs a PyTorch build for CUDA 12.8 or newer for the Parakeet ASR step.
   - Free LiveKit Cloud project → `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` in `v3/.env.local`.
   - `OPENAI_API_KEY` is needed regardless (gpt-4o judge), plus `GOOGLE_API_KEY` for Gemini templates.
   - Download the benchmark audio (Google Drive link in `v3/README.md`).
2. **Baseline (1 day).** Run one stock template on all 100 recordings; run the three evaluations. Keep the logs: they are the "before" for the slides.
3. **Commit gate on the realtime template (2–3 days).** Wrap the 12 tools; add the ack; re-run; compare the per-disfluency and rollback breakdowns.
4. **Our own dev set.** Record or synthesize disfluent requests for the same 12 tools (our own wording) to iterate on without tuning to the test items; FDB v1/v1.5 for turn-taking practice.
5. **Extension (2–3 days).** Camera troubleshooting agent in LiveKit.
6. **Submission (1–2 days).** One-command script (install → check keys → start agent → run 100 recordings → evaluate), pinned versions and seeds, README with diagram, run logs, 3–5 min video, ≤ 8 slides. Test the script on a clean machine or a fresh WSL instance.

## 5. Rules that shape the work
- Don't read, memorize or tune on the test items' dialogue or expected calls; disqualifying, and checked.
- No calls to our own servers at evaluation time; hosted model APIs are fine and must be declared.
- No state cached across scenarios; each room starts fresh.
- The organizers' machine: one 48 GB NVIDIA GPU (CUDA 12.x/13.x) or declared hosted APIs. Only their re-run counts; a script that doesn't reproduce scores 0 for 60% of the grade.

## 6. Cost to watch
Each full run is 100 realtime-model conversations plus about 300 gpt-4o judge calls. Run single examples (`--example`) while iterating and full runs only at milestones.

## 7. Reproducing our score

`reproduce.sh` (repo root) is the drafted one-command reproduction script — **not yet run**. It:

1. Installs system deps (`ffmpeg`, `git`, `curl`), detecting `apt` (Ubuntu) vs `dnf` (Amazon Linux 2023).
2. Installs `uv`.
3. Clones `Full-Duplex-Bench` at a pinned commit (see **Assumptions** — no commit hash is recorded anywhere yet, so `FDB_COMMIT` is currently empty and the script warns and uses HEAD).
4. Builds the Python env from `project-log/runs/env-freeze.txt` via `uv pip install -r`.
5. Downloads and extracts the FDB-v3 data the same way `GEMINI_TASKS.md`'s G1 did (`gdown` on the Drive file id from `v3/README.md`, skip `__MACOSX`, expect 100 `input.wav`).
6. Checks required env vars **by name only** — never reads or prints a value: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and either `GOOGLE_API_KEY` or (`GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_CLOUD_PROJECT`, with `gcloud auth application-default login` already done). Warns (doesn't print) if `OPENAI_API_KEY` is absent — scoring then falls back to exact-match instead of `--use-llm`.
7. Starts the agent, runs the full 100-recording benchmark, scores it, and archives everything under `project-log/runs/<date>_repro_<provider>/` — modeled directly on `project-log/scripts/run_baseline.sh`.

Usage: `./reproduce.sh [agent_script] [provider]` — defaults to `fdb_agent/gate_agent.py` / `gate_gemini38`; pass `fdb_agent/baseline_agent.py gemini3_8` for the stock baseline instead.

**What it needs from you first** (typed into `~/theme5/Full-Duplex-Bench/v3/.env.local` yourself, never pasted to an agent): the LiveKit and model credentials above. Nothing else.

**What it deliberately does not do:** it does not run automatically as part of any other script, and must never be started while another agent or benchmark run is using the same LiveKit project or `/tmp/agent_tool_calls.log` — see the warning in `project-log/SONNET_TASKS.md`.

### Assumptions this draft could not verify (needs a human or a later Claude session to check)
- **No pinned Full-Duplex-Bench commit hash exists anywhere in the repo yet.** `env-freeze.txt` records Python package versions, not the benchmark repo's own commit. Someone needs to run `git -C ~/theme5/Full-Duplex-Bench rev-parse HEAD` at freeze time and set `FDB_COMMIT` in the script (or export it as an env var before running).
- Whether `v3/requirements.txt` exists and differs from `env-freeze.txt` — the script tries to install it and tolerates it being absent, but this hasn't been checked.
- Whether `run_tool_benchmark_all_released.py` (used by `run_baseline.sh` and this script) is present at the pinned commit — it's referenced by an existing working script, but wasn't independently re-verified here.
- Amazon Linux 2023's default `dnf` repos may not carry `ffmpeg` (it's often only in RPM Fusion/EPEL) — the script surfaces this as an error rather than guessing a fix, since guessing wrong on a clean machine wastes the reproduction attempt.
- Whether `gdown` can fetch the Drive file non-interactively on a clean machine, or hits Google's "too many downloads" block (`GEMINI_TASKS.md` G1 already flags this as a known risk with no fallback beyond "blocked: needs browser download").
- Full end-to-end run of this script has **not been attempted** (the rule against starting agents while the current 100-recording benchmark run is in progress applies here too).

## 8. Related work — the FDB-v3 authors' other papers (checked 2026-09-29)

The user shared the publication list of Guan-Ting Lin (FDB-v3's first author, NTU/Hung-yi Lee's lab). Went through all of it; most is unrelated (ASR test-time adaptation, prosody/SSL, textless QA, patents, awards). What's actually useful for this project:

**The FDB lineage confirms our whole thesis, with a citable number.** FDB-v3 (arXiv 2604.04847) evolved from three earlier benchmarks by the same group:
- **v1** (ASRU 2025, arXiv 2503.04721) — turn-taking only: pause handling, backchanneling, interruption management.
- **v1.5** (ICASSP 2026, arXiv 2507.23159) — adds overlap handling; finds models split into two strategies, "responsive" (react fast to overlap) vs. "floor-holding" (filter overlapping events to keep talking) — directly relevant to how our talker/ack layer should behave when the user talks over it.
- **v2** (ACL 2026, arXiv 2510.07838) — adds an automated multi-turn examiner across Daily/Correction/Entity Tracking/Safety tasks; finds duplex systems "often get confused when people talk at the same time, struggle to handle corrections smoothly, and sometimes lose track of who or what is being talked about" — i.e. the same correction/state-tracking failure the commit gate targets, one version earlier.
- **v3** (arXiv 2604.04847, our benchmark) — adds tool use. Confirmed via the actual abstract: 6 models evaluated (GPT-Realtime, Gemini Live 2.5/3.1, Grok, Ultravox v0.7, Cascaded Whisper→GPT-4o→TTS); GPT-Realtime leads Pass@1 (0.600); Gemini Live 3.1 is fastest (4.25s) but has the lowest turn-take rate (78.0%); Cascaded has a perfect turn-take rate but the highest latency (10.12s). **The paper's own stated conclusion: "self-correction handling and multistep reasoning under hard scenarios remain the most consistent failure modes" across every model tested** — this is the strongest citable evidence for the deck's slide 3 (existing solutions and gaps) and slide 8 (results/limits): it's not just our read of the benchmark, it's the authors' own headline finding, and it's exactly the gap the commit gate is built to close.

**Two other papers suggest concrete technique ideas, not yet adopted:**
- **SUTA-LM** (Huang, Lin, Lee; ASRU 2025, arXiv 2506.11121) — test-time adaptation for ASR that avoids TTA interfering with LM rescoring. Relevant to the PDF's own flagged risk "Parakeet mishears our TTS voice" (Phase 0 risk table): if our TTS voice consistently confuses the scorer's Parakeet ASR in a fixable way, SUTA-LM's approach (adapt at inference, don't fight the LM rescoring step) is a citable technique for the "known limits" section — not something to implement under this deadline, just worth a one-line mention if the voice-selection test in Phase 0 turns up systematic ASR errors.
- **"Can LLMs Understand the Implication of Emphasized Sentences in Dialogue?"** (Lin & Lee, EMNLP 2024 Findings, arXiv 2406.11065) — benchmark for whether LLMs correctly infer meaning from vocal emphasis (their `Emphasized-Talk` set). Marginally relevant: our reasoner already has to detect "no, actually X" corrections from text; if audio-level emphasis cues (stress on the corrected word) ever get piped into the reasoner's prompt, this paper's framing of "emphasis implies contrastive intent" is a citable precedent. Not required for the current text-transcript-only design.

**Not relevant, skip:** Align-SLM (RLAIF for textless spoken LMs), the speaking-styles and paralinguistics-enhanced LLM papers (general spoken-dialogue LLM training, not tool-calling or turn-taking), DUAL (textless spoken QA), the other ASR-TTA papers, the patent, and the awards/service list.

**Suggested use:** cite v1→v3 as the benchmark's own evolution in the deck's "Theme" slide (interruption is a state-consistency problem the authors themselves have been iterating on for a year), and quote the v3 paper's "self-correction... most consistent failure mode" line directly — it's the single best piece of external validation available for why the commit gate is the right bet.
