# AI usage — factual reference for the organizers' declaration form

This is a factual list of which AI tools did what, for the user to transcribe into the organizers' actual AI-usage declaration form (referenced in `project-log/meetings/2026-09-29_organizer_briefing_notes.md`, fact 14 — *"there are no restriction on what AI you can use... whenever you are using an AI, please make sure that you are filling it out"*). **This file is not the form itself** — the user fills that in separately.

## The short, honest version (updated 2026-09-30)

AI assistants wrote almost all of the code, tests, scripts and documentation in this repository and ran the experiments. The team set the direction, made the decisions, supplied the accounts, and is responsible for every claim. Specifically:

| Who | What they did |
|---|---|
| Team lead (the user) | Chose the approach and priorities; decided what to build, which runs to make and which to submit (for example "the Reasoner may only shorten a hold", including Smart Turn in a test run, the names used in the documents); created the accounts and typed every key (no key was given to an AI tool to handle); approved or stopped actions; records the demo and fills in the forms. |
| Lohit | The upgrade pack: the dangling-word rule, the merged prompt rules and 12 pause-focused practice scenarios (built with an AI assistant, as noted below). |
| Aryan | TODO for the team: state Aryan's contribution here before submitting. |

**How AI output was checked.** Code was checked by automated tests and by benchmark and practice runs, which were themselves written and run by AI; humans reviewed results and decisions, not every line of code. Research claims were checked against the original pages where we cite them, and unverified ones are marked as such. Several AI mistakes were caught and corrected during the work and are recorded in `WORKLOG.md` (unsupported quotes in a research note, a miscounted test total, a wrong statement that a side measurement had not disturbed a benchmark run, and an early over-optimistic reading of Smart Turn).

**What AI was not used for.** No AI tool was used to read, tune on or generate the FDB-v3 test recordings' expected answers. Practice data is our own; its audio is synthetic speech and is labelled as such. The demo video is recorded by a person.

## AI tools used to build the submission (process/tooling)

| Tool | What it did |
|---|---|
| **Claude (Opus, "lead" session)** | Primary design and implementation: `fdb_agent/gate.py` (commit gate), `jev.py` (Jev integration), `gate_agent.py`/`baseline_agent.py`, `models.py`; ran and managed the actual benchmark and dev-set runs; found and fixed the positional-args gate bug and the supersede/`speech_epoch` bug; applied the housing prompt fix (`GATE_PROMPT=2`, merged with Lohit's rules). |
| **Claude (Sonnet, this session and others, "assistant engineer")** | Documentation (`README.md`, `BUILD_PLAN_FDB_V3.md`, `PLAN_VS_ACTUAL.md`, `INDUSTRY_BENCHMARKS.md`, this file, `VIDEO_SCRIPT.md`, `SLIDES_OUTLINE.md`); scripts (`devset/make_audio.py`, `run_dev.sh`, `score_dev.py`, `reproduce.sh` draft); the extension's offline core (`extension/recovery.py`, `mock_tools.py`, `test_recovery.py`, `ext_agent.py` draft); research (organizer-briefing analysis, FDB-v3 paper lineage/author research, industry-benchmark survey); the C: drive cleanup survey (unrelated to the submission itself). |
| **Claude (Opus, lead session, 2026-09-30)** | Today's additions: retraction, identifier and backchannel handling, the lean switch, the Smart Turn integration, the demo launch scripts, the scoring and health-check scripts, the architecture review and the documents `JUDGE_QA.md`, `USE_CASES_SAMSUNG.md`, `PLAN_PLUGINS_MCP.md`; delegated sub-tasks to Sonnet sub-agents (home tool pack, plugin test path, local-fallback module, research notes, document updates). |
| **Claude (second session started by the team lead, 2026-09-30)** | Ran the Smart Turn check on older public recordings and the two final benchmark runs (with and without Smart Turn). |
| **Gemini CLI / Antigravity ("junior assistant")** | Light, well-scoped tasks per `project-log/GEMINI_TASKS.md`: downloading and verifying the FDB-v3 benchmark audio, checking which realtime model ids the installed LiveKit plugins accept, and an initial research note on the FDB-v3 authors' publications (later independently verified by the Claude sessions against the actual papers). |
| **Lohit's upgrade pack** | Built by a teammate, with the help of an AI assistant (tool unspecified to this session) — contributed the dangling-word hold-extension rule (`GATE_DANGLING`), the merged prompt rules (`GATE_PROMPT=2`'s `EXTRA_RULES_V2`), and 12 pause-focused dev-set scenarios (`p01`–`p12`), reviewed and integrated by the Claude sessions. |

## AI models running inside the submitted product itself

| Model | Role |
|---|---|
| **Gemini 3.8 Live** (Google) | The realtime reasoner/talker inside `gate_agent.py` — listens, decides which tool to call, and speaks the response. Reached via Vertex AI + ADC in our own development environment, or a plain `GOOGLE_API_KEY` as the default reproduction path (see `README.md`'s Reproduce section). |
| **TypeSafe Jev** | An optional typed decision-layer classifier inside the commit gate (`fdb_agent/jev.py`) — judges whether a turn sounds finished, and whether a repeated tool call is a correction or an addition. Every call has a hard timeout and falls back to rule-based logic on any failure, so a failure never blocks a turn. It adds one network call per user turn. |
| **Gemini 2.5 Pro** | Used as our own **development-time** judge (via Vertex) to re-score baseline runs during tuning — a stand-in for the GPT-4o judge used in the FDB-v3 paper, with the benchmark's own judge prompts unchanged. All judged numbers we report come from this stand-in and are labelled as such; they are not presented as equivalent to a GPT-4o-judged score. (The organizer briefing did not name a judge model.) |
| **NVIDIA Parakeet-TDT-0.6B-v2** | The ASR the benchmark's own scoring pipeline runs on our agent's spoken output — this is the benchmark harness's model, not something our agent invokes itself. |
| **Smart Turn v3.2** (Pipecat, open source) | Optional acoustic end-of-turn model inside the agent (`fdb_agent/smart_turn.py`), runs locally on CPU. Used in one of the two final benchmark runs; whether it is part of the submitted configuration is stated in the README. |
| **FunctionGemma** (Google, through Ollama) | Local model tried as an offline fallback in the extension only; measured at about 30% fully correct on our own 40 commands, not used in the benchmark agent. |
| **Kokoro-82M** | Local text-to-speech used only to synthesize our own practice/dev-set audio (`devset/make_audio.py`) — never used on, or mixed with, the real FDB-v3 benchmark recordings. |

## Notes for filling in the actual form

- Every AI tool listed above touched **our own code, our own practice data, or our own documentation** — none were used to read, tune on, or generate FDB-v3's own expected answers. We read only pass/fail results and our own agent's outputs from benchmark runs. (We treated tuning on the test set as off limits; the briefing transcript does not state a disqualification rule in those words.)
- If the form asks for specific model versions/dates: Gemini 3.8 Live and Gemini 2.5 Pro version details are in `project-log/runs/env-freeze.txt` and `project-log/STATUS.md`; TypeSafe Jev's SDK version (`typesafe-sdk` 0.7.2) is noted in `project-log/DECISIONS.md`.
