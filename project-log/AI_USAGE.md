# AI usage — factual reference for the organizers' declaration form

This is a factual list of which AI tools did what, for the user to transcribe into the organizers' actual AI-usage declaration form (referenced in `project-log/meetings/2026-09-29_organizer_briefing_notes.md`, fact 14 — *"there are no restriction on what AI you can use... whenever you are using an AI, please make sure that you are filling it out"*). **This file is not the form itself** — the user fills that in separately.

## AI tools used to build the submission (process/tooling)

| Tool | What it did |
|---|---|
| **Claude (Opus, "lead" session)** | Primary design and implementation: `fdb_agent/gate.py` (commit gate), `jev.py` (Jev integration), `gate_agent.py`/`baseline_agent.py`, `models.py`; ran and managed the actual benchmark and dev-set runs; found and fixed the positional-args gate bug and the supersede/`speech_epoch` bug; applied the housing prompt fix (`GATE_PROMPT=2`, merged with Lohit's rules). |
| **Claude (Sonnet, this session and others, "assistant engineer")** | Documentation (`README.md`, `BUILD_PLAN_FDB_V3.md`, `PLAN_VS_ACTUAL.md`, `INDUSTRY_BENCHMARKS.md`, this file, `VIDEO_SCRIPT.md`, `SLIDES_OUTLINE.md`); scripts (`devset/make_audio.py`, `run_dev.sh`, `score_dev.py`, `reproduce.sh` draft); the extension's offline core (`extension/recovery.py`, `mock_tools.py`, `test_recovery.py`, `ext_agent.py` draft); research (organizer-briefing analysis, FDB-v3 paper lineage/author research, industry-benchmark survey); the C: drive cleanup survey (unrelated to the submission itself). |
| **Gemini CLI / Antigravity ("junior assistant")** | Light, well-scoped tasks per `project-log/GEMINI_TASKS.md`: downloading and verifying the FDB-v3 benchmark audio, checking which realtime model ids the installed LiveKit plugins accept, and an initial research note on the FDB-v3 authors' publications (later independently verified by the Claude sessions against the actual papers). |
| **Lohit's upgrade pack** | Built by a teammate, with the help of an AI assistant (tool unspecified to this session) — contributed the dangling-word hold-extension rule (`GATE_DANGLING`), the merged prompt rules (`GATE_PROMPT=2`'s `EXTRA_RULES_V2`), and 12 pause-focused dev-set scenarios (`p01`–`p12`), reviewed and integrated by the Claude sessions. |

## AI models running inside the submitted product itself

| Model | Role |
|---|---|
| **Gemini 3.8 Live** (Google) | The realtime reasoner/talker inside `gate_agent.py` — listens, decides which tool to call, and speaks the response. Reached via Vertex AI + ADC in our own development environment, or a plain `GOOGLE_API_KEY` as the default reproduction path (see `README.md`'s Reproduce section). |
| **TypeSafe Jev** | An optional typed decision-layer classifier inside the commit gate (`fdb_agent/jev.py`) — judges whether a turn sounds finished, and whether a repeated tool call is a correction or an addition. Every call has a hard timeout and falls back to rule-based logic on any failure, so it can only ever help, never block a turn. |
| **Gemini 2.5 Pro** | Used as our own **development-time** judge (via Vertex) to re-score baseline runs during tuning — separate from, and not a substitute for, the organizers' official judge. The FDB-v3 paper and the organizer briefing both use GPT-4o as the judge; our Gemini-2.5-Pro-judged numbers are for our own iteration only and are labeled as such, never presented as equivalent to a GPT-4o-judged score. |
| **NVIDIA Parakeet-TDT-0.6B-v2** | The ASR the benchmark's own scoring pipeline runs on our agent's spoken output — this is the benchmark harness's model, not something our agent invokes itself. |
| **Kokoro-82M** | Local text-to-speech used only to synthesize our own practice/dev-set audio (`devset/make_audio.py`) — never used on, or mixed with, the real FDB-v3 benchmark recordings. |

## Notes for filling in the actual form

- Every AI tool listed above touched **our own code, our own practice data, or our own documentation** — none were used to read, tune on, or generate FDB-v3's own test recordings or expected answers, per the organizers' disqualification rule.
- If the form asks for specific model versions/dates: Gemini 3.8 Live and Gemini 2.5 Pro version details are in `project-log/runs/env-freeze.txt` and `project-log/STATUS.md`; TypeSafe Jev's SDK version (`typesafe-sdk` 0.7.2) is noted in `project-log/DECISIONS.md`.
