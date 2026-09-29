# Theme 05: Interruptible Real-Time Agents — FDB-v3 submission

## What it is

A LiveKit voice agent for **Full-Duplex-Bench v3** (the organizers' scored benchmark) that fixes the benchmark's single biggest failure mode — tools firing on a value the user is still in the middle of correcting. A **commit gate** sits between the realtime model and its 12 tool functions: it holds every proposed call until the user's turn has actually settled, drops a held call the moment a newer one supersedes it, and never executes the same call twice.

## Architecture

```mermaid
flowchart LR
    A["FDB-v3 recording<br/>input.wav"] --> B["LiveKit room"]
    B --> C["Gemini 3.8 Live<br/>(realtime model)"]
    C -- "proposed tool call" --> D["Commit Gate<br/>(fdb_agent/gate.py)"]
    D -- "held / superseded<br/>(never executed)" --> C
    D -- "released, executed once" --> E["12 stock tools<br/>(4 domains)"]
    E --> F["/tmp/agent_tool_calls.log"]
    C --> G["Spoken answer (TTS)"]
```

The gate (`fdb_agent/gate.py`, wired in `fdb_agent/gate_agent.py`):

- Holds a proposed call until the user has been quiet for **0.9 s** — or **1.8 s** if their last words trail off on a filler/hesitation/correction cue ("um", "wait", "actually", "no", "I mean", "or", "scratch that", …).
- **Supersedes** a held call the instant a newer call to the *same tool* arrives after the user speaks again — that's a correction, not a second request; the superseded call is told so and never runs.
- **Never executes an identical call twice** — canonicalized args (case/whitespace-insensitive) are checked against everything already executed; a repeat returns the cached result instead of re-calling the tool.
- Caps any hold at **8 s**, so a genuinely long pause can't stall the conversation forever.
- **Only executed calls are logged.** Held or superseded calls never touch `/tmp/agent_tool_calls.log` — nothing is hidden from the scorer, execution is just deferred until it's safe.

## Why this design

Full-Duplex-Bench v3's own scoring is unforgiving of early commitment: a single wrong or extra tool call fails the entire scenario's strict Pass@1, even if the corrected call follows immediately after (`evaluate_pass_rate.py`'s multiset + precision check — verified by reading the benchmark's own code, not assumed). The paper's own published numbers (arXiv 2604.04847, verified against the paper directly) confirm this is a universal problem, not one model's quirk:

| System | Pass@1 | Notes |
|---|---|---|
| GPT-Realtime | 0.600 | Best overall, but only 58.8% on self-correction scenarios specifically |
| Gemini Live 3.1 | 0.540 | Task completion 4.25 s |
| Gemini Live 2.5 | 0.490 | |
| Cascaded (Whisper → GPT-4o → TTS) | 0.450 | Task completion 10.12 s (slowest in the paper); our reading: extra hops, and the text step loses hesitation cues in the audio |
| Grok | 0.430 | |
| Ultravox v0.7 | 0.410 | |

Self-correction is explicitly named in the paper as one of the two most consistent failure modes across *every* system tested — that's the gap this gate targets. (Our 0.9s/1.8s hold windows are a tuned starting point refined against our own synthetic dev set, `devset/scenarios.jsonl` — not a number taken from the paper; the paper does not publish a specific hesitation-pause duration, and we don't claim it does.)

## Results

| System | Pass@1 (exact-match) | Pass@1 (`--use-llm` GPT-4o judge) | Latency | Source |
|---|---|---|---|---|
| Paper: GPT-Realtime | — | 0.600 | — | arXiv 2604.04847 |
| Paper: Gemini Live 3.1 | — | 0.540 | 4.25 s task completion | arXiv 2604.04847 |
| Paper: Cascaded (Whisper/GPT-4o/TTS) | — | 0.450 | 10.12 s task completion | arXiv 2604.04847 |
| **Ours: stock agent, no gate** (`baseline_agent.py`, `gemini-3.8-live`, all 100) | **0.50 (50/100)** | TBD (no judge key yet) | 3.92 s median perceived (first reply); task completion TBD | `project-log/SCORES.md`, `runs/2026-09-29_full_gemini3_8/` |
| **Ours: with commit gate** (`gate_agent.py`) | **TBD — run in progress** | TBD | TBD | `project-log/runs/` (link added once frozen) |

> The paper's pass rates were scored with the GPT-4o judge; our exact-match numbers are stricter, so they are **not** directly comparable until our runs are re-scored with the judge. Latency: the paper reports task-completion time; "perceived" is time from the user's speech end to the agent's first reply.

Baseline failure breakdown (exact-match, from `project-log/SCORES.md`): by disfluency — pause 0.389, filler 0.448, self-correction 0.471, hesitation 0.50, false start 0.667; by domain — finance 0.88, e-commerce 0.759, travel 0.15, housing 0.115; failure causes — 32 wrong-argument, 10 missing-tool, 5 extra-tool, 3 missing+extra.

All numbers above without a source link are **TBD** and will be filled in from a `runs/` folder once frozen — no number here is reported without a log behind it.

## Reproduce

`reproduce.sh` (repo root) is the one-command reproduction script; see `BUILD_PLAN_FDB_V3.md` §7 for exactly what each step does and its unverified assumptions. It needs these environment variables set **by name only** in `~/theme5/Full-Duplex-Bench/v3/.env.local` (values are never written to this repo or asked for by any script):

- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`
- `GOOGLE_API_KEY` — **default path**, a plain Gemini API key
- *(optional alternative)* `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION` — Vertex AI via Application Default Credentials, used in our own development environment because our org's Cloud policy blocks plain API keys; **not required for reproduction**, the API-key path is simpler for anyone re-running this
- `OPENAI_API_KEY` (optionally `OPENAI_BASE_URL` for an Azure OpenAI deployment) — optional, only needed for `--use-llm` judge scoring; without it, scoring falls back to exact-match

```bash
./reproduce.sh fdb_agent/gate_agent.py gate_gemini38   # our agent
./reproduce.sh fdb_agent/baseline_agent.py gemini3_8   # stock baseline, for comparison
```

## Extension (placeholder — not yet built)

**Audio-only "slow/failing tool recovery" use case.** The organizer briefing (`project-log/meetings/2026-09-29_organizer_briefing_notes.md`) confirmed FDB-v3 has no video input in Round 1 and named exactly this scenario as something they want showcased: *"There will be instances where the tasks will fail... there will be instances where the latency will be variable... if you can showcase [that], that will be very good... you should be able to recover — retry, close the session, move to human in the loop."* The plan is to reuse the same coordinator (talker/reasoner/commit gate) behind a second adapter, feeding it slow or failing mock tool calls instead of LiveKit audio, and show: a retried read-only call, a state-changing call that is never blindly retried, and a clean handoff when recovery isn't possible. **Not implemented yet** — this section is a placeholder until it is.

## Honest limitations

- **Single reported run so far.** The results table above is one baseline pass; the gate run and a second full run (for mean + variance, per `BUILD_PLAN_FDB_V3.md`'s own plan) are still pending.
- **Exact-match scoring only, for now.** No OpenAI/Azure key is wired in yet, so `--use-llm` numbers are TBD; exact-match can penalize a correct answer in a different valid format.
- **Cloud-dependent.** The reasoner is a hosted realtime model (Gemini 3.8 Live); there's no fully local fallback in the current build, though `BUILD_PLAN_FDB_V3.md` scopes one as a stretch goal if the deadline moves.
- **Tuned only on our own synthetic dev set** (`devset/scenarios.jsonl`, 40 scenarios written from scratch against the tool signatures) — never on FDB-v3's own 100 test recordings, per the organizers' disqualification rule. This means our gate's timing constants are our best guess refined on synthetic data, not on the actual test distribution.
- **Extension is not yet built** (see above) — currently a stated plan, not working code.
- **`book_flight` argument scope.** The stock tool only takes `passenger_name`, no `flight_id` — an open question for how the judge treats any expected `flight_id` reference (`project-log/STATUS.md`).

## Declared models / APIs

- **Reasoner:** Gemini 3.8 Live (Google), via a plain API key by default, or Vertex AI with ADC in our own dev environment
- **Voice infrastructure:** LiveKit Cloud (real-time audio room, required by the benchmark's own harness)
- **Judge (optional):** GPT-4o, via OpenAI API or an Azure OpenAI deployment — declared, not yet wired in
- **Scoring ASR:** NVIDIA Parakeet-TDT-0.6B-v2 — run by the benchmark's own scorer, not by our agent

## AI usage

This project was built with AI coding assistance: Claude (Sonnet, this session and others, as lead engineering assistant) and Gemini CLI/Antigravity (as a junior assistant for light, well-scoped research tasks — see `project-log/GEMINI_TASKS.md`). The organizers' AI-usage declaration form is filled out accordingly (see `project-log/STATUS.md`'s checklist).

## History

This repository began as the Samsung PRISM participant kit (a local text/audio/visual interruption-handling harness, scored ~57–84 on its own evaluator — see `project-log/SCORES.md`'s "Participant kit" table). On 2026-09-26 the official scoring guide moved to Full-Duplex-Bench v3, retiring that harness as the scored benchmark; this README now describes the FDB-v3 submission. The original kit's code, docs (`docs/PROTOCOL.md`, `docs/SCORING.md`, etc.) and scenarios are kept in the repository as the reusable base for the extension work above, but are no longer the graded harness.
