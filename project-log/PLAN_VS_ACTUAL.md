# Plan vs. actual: PDF build plan vs. what's built

Compares `D:\Downloads\Theme 05 Build Plan — FDB-v3.pdf` (Himanshu, 2026-09-29) against the repo's own `BUILD_PLAN_FDB_V3.md`, `project-log/STATUS.md`, `WORKLOG.md`, `DECISIONS.md`, `SCORES.md`, and `fdb_agent/*.py`. Never opened `benchmark_data_v2.json` or `scenarios/*.json`.

**Bottom line:** the two plans agree on the goal (commit gate beats stale early tool calls) but diverge on architecture — the PDF's `dual_agent.py` (cascaded STT→talker/reasoner→TTS) was never built; what exists is `BUILD_PLAN_FDB_V3.md`'s "Option A" (speech-to-speech realtime model + a gate wrapping the stock tools). A 100-recording run is in progress right now on `gemini-3.8-live`; no scored numbers exist yet.

## Where we stand (PDF table, p.1–2)

| PDF item | Status | Evidence | Note |
|---|---|---|---|
| Theme 05 research report | done | `RESEARCH.md` (19KB, exists) | Not re-verified for "two stale numbers" fix |
| Samsung participant kit replaced for scoring | done | `SCORES.md:13-21` kit runs logged as "no longer official"; `STATUS.md:8` | — |
| `VERIFICATION.md` (kit checks) | **unverified** | not found at `claude/VERIFICATION.md` or anywhere in repo (glob empty) | PDF marks this "Done"; can't confirm it exists under this name/path |
| `MEETING_2026-09-29_FDBv3_switch.md` | **unverified** | same — not found anywhere in the tree | Same caveat |
| FDB-v3 environment (LiveKit, keys, data) | done | `STATUS.md:19-28` all checked; `SCORES.md` smoke runs; S2 done (LiveKit connected, Gemini key OK) | Phase 0 of PDF |
| Baseline numbers in our environment | **in progress** | `WORKLOG.md:7` "Full baseline (gemini-3.8-live, stock agent, Vertex) started"; `runs/2026-09-29_full_gemini3_8/run.txt` start timestamp only, no score yet | Earlier baseline attempt aborted (billing); this is a live run — **do not project a result** |
| Our agent (`dual_agent.py`) | **changed** | no file named `dual_agent.py` in repo; `fdb_agent/gate_agent.py` is the actual built agent | See "Architecture" below |
| Deck, README, video, declaration form | not started | no `docs/architecture`, no deck/video files found; `README.md` exists but is the old participant-kit README (Sep 20), not FDB-v3 | — |

## Phase checklist (PDF Phase 0–5)

| Phase | PDF check | Status | Evidence |
|---|---|---|---|
| 0 — Setup/smoke | 3 results + eval reports on disk | done | `runs/2026-09-29_smoke_gemini3_1/` and `_smoke_gemini3_8/` both have result.json + eval logs |
| 0 — Email PRISM | sent today | **unverified** | not mentioned in WORKLOG/STATUS/DECISIONS |
| 0 — `requirements.lock` | frozen versions | **changed** | `project-log/runs/env-freeze.txt` via `uv`, not conda + `requirements.lock` (`WORKLOG.md:24`) |
| 1 — Stock baselines on all 100 | done, table filled | **in progress** | current run is exactly this (gemini3_8); GPT-4o cascaded baseline not attempted (no OpenAI key, `STATUS.md:29`) |
| 2 — Build `dual_agent.py` | beats stock Pass@1 on dev set | **changed / not verified** | Built `gate_agent.py` instead (different architecture, see below); no dev-set Pass@1 comparison in `SCORES.md` |
| 3 — Full runs + ablations | frozen at 18:00, results table filled | not started | Only A1-equivalent exists (`baseline_agent.py` = no gate); A2/A3 not built |
| 4a — Extension | scored demo | not started | no `extension/` folder |
| 4b — Deck/README/video | — | not started | template only, per PDF's own "Where we stand" |
| 5 — Package/submit, fresh clone | — | not started | `reproduce.sh` is S4 (this session), not yet drafted at time of writing |

## The 7 Pass@1 rules (PDF p.4–5)

| Rule | Status | Evidence |
|---|---|---|
| 1. Execute only after turn ends | done, different mechanism | `gate.py:92-93` gates on `quiet_s` (0.9s) + `max_hold_s` (8s cap), not a semantic turn-gate model |
| 2. Last stated value wins | done | `gate.py:79-82` newer proposal for same tool after new speech supersedes the held one; tested `test_gate.py:44-57` |
| 3. Chain strictly | **changed** | PDF's chaining logic belongs to the reasoner in `dual_agent.py`; the built agent uses the realtime model's own function-calling, gate doesn't sequence multi-step chains itself |
| 4. No extras / dedupe | done | `gate.py:99-107` canonicalized-args dedupe; tested `test_gate.py:66-70` |
| 5. Always speak the answer | **unverified** | no code inspection of spoken-response behavior; relies on stock `lk_agent_tool.py` prompt, unchanged |
| 6. Never talk over the user (content-aware ack) | **not built** | no talker/ack layer exists in `gate_agent.py`; `WORKLOG.md:9` flags NON_BLOCKING tool calls may let the model keep talking while a call is held — **unchecked** |
| 7. Keep the logging contract | done | `gate.py` docstring + design: only executed calls logged, held/superseded never logged |

## Model choices (PDF table, p.5–6)

| Layer | PDF default | Built | Note |
|---|---|---|---|
| STT | streaming API STT w/ fillers (Deepgram) | **not used** | speech-to-speech realtime model has no separate STT stage |
| Turn detection | VAD + turn-detector + filler-word hold rule | **changed** | `gate.py:25` flat 0.9s silence window, no word-list hold rule |
| Reasoner | Gemini Flash, temp 0 | **changed** | `gemini-3.8-live` (realtime, not Flash text) via `models.py`; Vertex AI + ADC, not an AI Studio key (org policy blocks API keys, `STATUS.md:30`) |
| Talker | template ack | not built | — |
| TTS | OpenAI tts-1 / Google TTS | **not used** | folded into the realtime model's own voice output |

## Ablations A1–A3 (PDF p.8)

| Ablation | Status | Evidence |
|---|---|---|
| A1: no commit gate | **exists** | `baseline_agent.py` is functionally this (stock tools, no gate) |
| A2: GPT-4o as reasoner | blocked | no OpenAI key yet (`STATUS.md:29`) |
| A3: no talker ack | **N/A** | no talker exists to ablate (see rule 6) |

## Extension (PDF p.12–13)

| PDF scenario | Status |
|---|---|
| Kit-harness barge-in, book-once, timeout, unseen-tool, camera-frame, Bixby pack | not started |
| BUILD_PLAN's alternative: camera device-troubleshooting in LiveKit | not started (`BUILD_PLAN_FDB_V3.md:90-91`) |

Both extension concepts are proposals only; neither has code. They differ (kit-harness reuse vs. LiveKit-native camera agent) — unresolved which one this project will actually build.

## Deliverables / repo layout (PDF p.13–14)

| PDF item | Status |
|---|---|
| `run_benchmark.sh` | missing (glob found none) — S4 (this session) is drafting `reproduce.sh` instead, a different name/scope |
| `.env.example` | missing |
| `core/` + `adapters/` split (LiveKit-import-free coordinator) | **not followed** — `fdb_agent/` is flat, `gate_agent.py` imports `livekit.agents` directly |
| `environment.yml`/`requirements.lock` | **changed** — `env-freeze.txt` via `uv` |
| 12-slide `samsung.pptx` deck | not started |
| 5-min video | not started |

## Differences that matter

1. **Architecture: cascaded vs. speech-to-speech.** The PDF's core design is `dual_agent.py` — streaming STT that keeps filler words, a semantic turn-gate, a template talker + Gemini Flash text reasoner, separate TTS. What's actually built is `BUILD_PLAN_FDB_V3.md`'s "Option A": a single speech-to-speech realtime model (`gemini-3.8-live`) with a commit gate wrapping the 12 stock tool functions (`gate_agent.py`). Consequences: no STT/TTS/talker stages to reason about separately; "hold ~1.5s on trailing fillers/repair words" became a flat 0.9s silence window with an 8s hard cap and no word-list rule (`gate.py:25-26`); PDF's A3 ablation (no talker) has nothing to ablate; A1 already exists as `baseline_agent.py`; A2 is blocked on a key, same in both plans.
2. **Dev set vs. no-tuning rule — direct conflict, not resolved.** The PDF (p.8) says: tune the agent on a 20-example dev set covering all domains/tiers/corrections, hold out the other 80, "tune only on these." `DECISIONS.md:10` and `GEMINI.md` say: never read or tune on FDB-v3 test items' `ground_truth`, disqualifying. These read as contradictory guidance — the PDF's dev-set plan is exactly the kind of test-item exposure the hard rule prohibits, unless "dev set" means synthetic recordings built by the team (which is what `BUILD_PLAN_FDB_V3.md:102` actually proposes: "record or synthesize disfluent requests... to iterate on without tuning to the test items"). Flagging, not resolving — whoever runs Phase 2/3 needs to pick the BUILD_PLAN interpretation, not the PDF's.
3. **Model access path.** PDF assumes a plain Gemini API key. Actual: org policy on the Google Cloud project blocks API keys entirely, so the team switched to Vertex AI + Application Default Credentials (`STATUS.md:30`, `WORKLOG.md:6`, `models.py:14-20`).
4. **Judge.** PDF wants `--use-llm` (GPT-4o judge) as the headline metric. No OpenAI key yet, so all current scoring is exact-match (`STATUS.md:29`, `SCORES.md:9`).
5. **Compute.** PDF assumes one 48GB GPU throughout. Actual dev hardware is an 8GB RTX 5070 laptop (`WORKLOG.md` various) plus a since-**stopped** AWS A10G 24GB box in Hong Kong for the clean-machine test (`STATUS.md:15-16`) — smaller than the PDF's reference GPU in both cases.
6. **Decision layer (Jev).** Only in `BUILD_PLAN_FDB_V3.md` (a researched, optional layer on top of the gate); the PDF doesn't mention it at all. Not built either way.
7. **Extension direction.** PDF: reuse the old kit harness + a Bixby-style scenario pack, scored by the kit's own scorer. BUILD_PLAN: a camera-frame device-troubleshooting agent purely in LiveKit. Neither started; these are two different plans for the same 20%, not yet reconciled.
8. **Team model.** PDF assumes 4 owners with named workstreams and sync meetings. Actual: one user plus Claude sessions (this one, "Theme 5 guidelines", and a Gemini/Antigravity junior) — no named 4-person team exists.
9. **Deck size / env tooling** (smaller): PDF wants a 12-slide `samsung.pptx` template; `BUILD_PLAN_FDB_V3.md:104` says "≤ 8 slides." PDF wants conda + `requirements.lock`; actual is `uv` + `env-freeze.txt`.

## Open risks

- **Deadline.** PDF states 30 Sep 23:59 IST as binding "until PRISM confirms in writing" — that confirmation isn't recorded anywhere in STATUS/WORKLOG/DECISIONS. `STATUS.md:34` "Submission deadline" is an open checkbox. Treat the deadline as unconfirmed.
- **Gate correctness under real load.** `gate.py`/`gate_agent.py` have only offline unit tests (`test_gate.py`, 7/7 pass) — no end-to-end scored run of the gated agent exists in `SCORES.md` yet.
- **NON_BLOCKING models.** `WORKLOG.md:9`: the LiveKit plugin marks `gemini-3.8-live`-class models NON_BLOCKING by default, meaning the model may keep talking while a held call waits on the gate — this directly threatens Rule 6 (never talk over the user / never claim early) and is explicitly flagged as unchecked.
- **Only a 2-recording smoke test scored so far** (1/2 exact-match, `SCORES.md:9`). The 100-recording run on Vertex/`gemini-3.8-live` is running right now — **no numbers exist for it yet**; do not treat the earlier aborted full run (2 recordings, billing failure) as data.
- **Organizer rerun of a Vertex-based agent** needs the organizers' own Google Cloud login/ADC setup — not just a shared API key (`STATUS.md:30`). This is a real reproducibility gap versus the PDF's "one command, any machine" goal.
- **Two exposed secrets, rotation unconfirmed.** A LiveKit secret was pasted in chat (`WORKLOG.md:13`) and an AWS SSH private key was attached in chat (`STATUS.md:16`, `WORKLOG.md:14`). Both are flagged for rotation in the logs but neither log confirms the rotation happened.
- **Fresh-clone test not done.** The PDF explicitly says "never cut" this check (p.9); it hasn't been attempted yet since no `run_benchmark.sh`/`reproduce.sh` exists to run.
- **Dev-set conflict above** is unresolved and could quietly cause a disqualifying rule violation if Phase 2/3 follows the PDF literally instead of `BUILD_PLAN_FDB_V3.md`.
