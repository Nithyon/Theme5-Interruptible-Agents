# Objectives (set 2026-09-29, evidence-based)

Grade = 60% benchmark (organizers' re-run, GPT-4o judge; ties broken on strict pass rate) + 20% extension + 20% docs/architecture/video. A benchmark run that doesn't reproduce scores **zero**, so reproducibility gates the 60%.

Evidence sources: baseline run `runs/2026-09-29_full_gemini3_8/` (strict + Gemini-judged reports), dev runs `runs/2026-09-29_dev_*`, decision eval `runs/2026-09-29_decision_eval.json`. Never tune on FDB-v3 items; levers are chosen from aggregate failure kinds and our own dev set.

## A. Benchmark score (60%)

| # | Objective | Metric (how measured) | Now (evidence) | Target | Levers | Status |
|---|---|---|---|---|---|---|
| A1 | Overall strict pass | `evaluate_pass_rate.py` pass rate, judged | baseline **62/100** judged (50 strict) | **≥ 70** judged | all below | final run in progress |
| A2 | Self-corrections | pass rate, SELF_CORRECTION slice | **0.47** (same strict & judged → real errors, not wording) | ≥ 0.60 | gate supersede, draft-call hold, prompt "last value wins" | in final run |
| A3 | Housing domain | pass rate, housing slice | **0.19** judged; 8 of 10 "missing tool" failures; 5 runs asked a follow-up question instead of calling | ≥ 0.50 | prompt: never ask follow-ups, use the user's own words ("home", "office") | in final run |
| A4 | 3-call requests | pass rate, 3-tool slice | **0.31** judged | ≥ 0.50 | prompt "one call per request / each item"; check the gate never merges distinct calls | in final run; verify |
| A5 | Pauses | pass rate, PAUSE slice | **0.61** judged (0.39 strict); dev pause set 3/12 | ≥ 0.70 | rules + Jev combined hold (catches 68% of pauses vs 60% rules / 64% Jev), dangling words | in final run |
| A6 | Extra / stale calls | failure kind "wrong/unexpected tools" | **18** judged failures; dev stale calls A2 5/30 → C 4/30 | ≤ 10 | gate supersede + duplicate block + draft hold | in final run |
| A7 | Argument accuracy | failure kind "wrong arguments" | **20** judged (32 strict; 12 were wording only) | ≤ 12 | prompt: values exactly as said, currencies as codes, digits; IDs spelled back exactly | in final run |
| A8 | Spoken-answer quality | `evaluate_tool_calls.py --use-llm` response accuracy | **not measured yet** | measure; ≥ baseline | watchdog "speak the result" (Lohit's pack) only if silent answers show up | TODO: measure on baseline + final |
| A9 | Latency | `analyze_tool_latency.py`: first response, tool-call, task completion | first reply median **3.92 s** (baseline); dev: A2 4.16 s, C 4.24 s | first reply ≤ 4.5 s; report tool-call latency | Jev fast release (0.4 s) on clearly finished turns | TODO: run latency analysis |
| A10 | No empty/failed conversations | results with status ≠ completed or no response | 0 in baseline after billing fix | 0 | retry on Gemini connection drop | watch in final run |

## G. The guide's three capabilities ("What you build": stay responsive / work async / recover cleanly)

| # | Capability | Objective | Now (evidence) | Target | Plan | Status |
|---|---|---|---|---|---|---|
| G1 | **Stay responsive**: acknowledge instantly ("meaningful spoken feedback within a few hundred milliseconds, no dead air, no false done") | cut time to first speech | first reply median **3.9 s** (baseline), 4.2 s dev | ≈ 1 s, with passes unchanged | on end of user turn, a short neutral acknowledgement ("Sure, one moment") while the gate/tools work; never result-like words; test on the dev set only; check that speaking on demand via Gemini is actually faster | TODO (test after final run) |
| G2 | **Work async**: tools + perception | tools never block the conversation; slow tools narrated | Gemini 3.8 NON_BLOCKING tools; gate holds without pausing speech; extension narrates slow tools (offline tests) | shown live in the extension demo | run `ext_agent.py` live | TODO (D1) |
| G3 | **Recover cleanly**: corrections + rollback | drop stale intent, never double-execute, **undo** when possible | gate supersede/duplicate block; extension idempotency + handoff; **rollback built**: `ToolRunner.rollback_and_run` compensates (`cancel_charging_booking`) then re-books, `on_rollback` callback for the talker, compensation-failure → handoff (35/35 offline tests incl. rollback + failed-compensation cases) | extension shows a compensating action (cancel old booking, book new) on a change of mind after execution | wired into `ext_agent.py` (write-only) + demo beat added to `DESIGN.md`/`VIDEO_SCRIPT.md`; live run pending with D1 | done offline; live demo TODO |

## B. Reproducibility (gates the whole 60%)

| # | Objective | Now | Target | Status |
|---|---|---|---|---|
| B1 | `reproduce.sh` runs end to end on a clean machine | drafted, never run | passes on the AWS g5 box (Amazon Linux) | TODO |
| B2 | Default path = plain `GOOGLE_API_KEY` (organizers: "for Gemini we will not need the key") | our runs use Vertex ADC | one smoke test with an API key | TODO (needs a working key with billing) |
| B3 | Pinned versions | FDB commit pinned; `env-freeze.txt` predates `typesafe-sdk` | re-freeze incl. typesafe-sdk 0.7.2 | TODO |
| B4 | Works without optional keys | Jev falls back to rules (unit-tested) | live smoke test with no `TYPESAFE_API_KEY` | TODO |
| B5 | Run logs + exact config for every reported number | all runs pushed with `run.txt` settings | keep | ongoing |

## C. Evidence quality (credibility with the jury)

| # | Objective | Now | Target | Status |
|---|---|---|---|---|
| C1 | Score with the organizers' judge (GPT-4o) | Gemini 2.5 Pro stand-in only | re-score baseline + final with GPT-4o (no rerun needed) | blocked: needs Azure/OpenAI key |
| C2 | Ablation on the benchmark: same model, stock vs our pipeline | baseline done; final running | table with both, same judge | in progress |
| C3 | Component evidence (dev set, never the benchmark) | A2 vs C tie on pass; decision eval: combined catches most pauses | reported honestly | done; README update pending |
| C4 | Calibration: reproduce the paper's number (stock + Gemini 3.1 ≈ 0.54) | not run | optional if time | optional |
| C5 | Variance: second run of the final config | not run | optional if time | optional |

## D. Extension (20%)

| # | Objective | Now | Target | Status |
|---|---|---|---|---|
| D1 | In-car recovery agent runs live end to end | core + rollback (35 offline tests); wired into `ext_agent.py`, never run live | live session works (slow tool, retry, change of mind, handoff, rollback) | TODO after the final run (LiveKit busy) |
| D2 | Recorded on video, unedited take | script ready (`VIDEO_SCRIPT.md`) | 2-min segment | TODO |

## E. Docs, architecture, video (20%)

| # | Objective | Now | Target | Status |
|---|---|---|---|---|
| E1 | README: architecture diagram, why, results, reproduce, limitations, declared APIs | drafted; final numbers TBD | final numbers filled | after final run |
| E2 | Slide deck ≤ 8 slides | outline done | deck built | TODO |
| E3 | Demo video 3–5 min | script done | recorded | TODO |
| E4 | AI-usage declaration form | notes in `AI_USAGE.md` | form submitted by the user | TODO (user) |

## F. Security hygiene

- Rotate the AWS key pair (`hahaha.pem`) before the next use of the box.
- Keys pasted into chats (Lohit's session; the revoked LiveKit key): recreate after the hackathon; revoke the Tavily key now if unused.
- Delete `~/theme5/Full-Duplex-Bench/v3/.env.localnano.save` and the stray `.env.localnano` if present (may hold keys).
