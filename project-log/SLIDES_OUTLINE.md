# Slide outline (max 8 slides)

Deck outline for the Theme 05 submission. Every number below is from `project-log/SCORES.md` or the run folders under `project-log/runs/`, and matches `README.md`. Do not add numbers that are not in those files. Read `TEAM_HANDOFF.md` ("claims you must not make") before writing slide text.

> **Names used in this document vs. the code.** Commit Harness = `fdb_agent/gate.py` (`CommitGate`), settings `GATE_*`. Reflex = the rule-based decider in `gate.py`. Reasoner = `fdb_agent/jev.py` (TypeSafe Jev). Listener = `fdb_agent/smart_turn.py` (Smart Turn v3.2). Flow: **Propose -> Settle -> Commit**.

## 1. Problem
- Full-Duplex-Bench v3: 100 real, disfluent recordings, 12 tools, 4 domains, strict Pass@1
- Strict scoring fails on any extra, wrong or early tool call (multiset match + precision check in the benchmark's `evaluate_pass_rate.py`)
- A call fired on the pre-correction value ("Boston... no, New York") still counts as executed, even if the right call follows
- **Speaker notes:** Interruption here is a state-consistency problem: the agent must not commit an action on a value the user is still changing. Say we never tuned on the 100 benchmark recordings (disqualifying); we built our own 62-item practice set.
- **Figure:** none, text slide

## 2. Why agents fail
- Paper (arXiv 2604.04847) Pass@1: GPT-Realtime 0.600, Gemini Live 3.1 0.540, Gemini Live 2.5 0.490, cascaded 0.450, Grok 0.430, Ultravox 0.410
- Self-correction is named as one of the most consistent failure modes across every system tested (GPT-Realtime passes 58.8% of self-correction scenarios)
- Our stock baseline (`gemini-3.8-live`, no Commit Harness): 50/100 strict, 62/100 judged
- **Speaker notes:** The paper's numbers used a GPT-4o judge; ours use a Gemini 2.5 Pro stand-in, so the comparison is indicative only. Do not present our number as beating or matching a paper row.
- **Figure:** the paper's Pass@1 table from `README.md` "Why this design"

## 3. Architecture (diagram described in words)
- Draw left to right: **user audio** -> **Gemini Live (fast mind: talks)** -> **Propose: tool call** -> **Commit Harness (slow mind: Settle, then Commit)** -> **benchmark tool code** -> **result spoken**
- Inside the Commit Harness, a ladder cheapest first: **Reflex** (instant, free, pattern-based: quiet 0.9 s / 1.8 s on hesitation, dangling words, draft-call hold) -> **Reasoner (TypeSafe Jev)** (typed turn-state and follow-up classifier, Reflex-only fallback on timeout) -> then **Listener (Smart Turn v3.2)**, acoustic end-of-turn (built behind a switch, not validated, not in the benchmark config) and a dashed box marked **planned**: **escalation to a thinking model**
- Arrow from the Commit Harness back to the model for "held / superseded, never executed"; only released calls reach the 12 stock tools and the log
- Related work, one line each: talker/supervisor split (OpenAI chat-supervisor, LiveKit supervisor blog, LTS-VoiceAgent); cheapest-first deciders (Hybrid LLM, ICLR 2024); change-of-mind taxonomy addition / revision / retraction (Zou et al. 2026)
- **Speaker notes:** The fast model (Gemini Live, the talker) keeps talking; the Commit Harness (the thinker that decides before acting) decides when a proposed action is safe to run. Emphasize nothing is hidden: held or superseded calls are simply never executed, and every executed call is logged by the benchmark's own tool code. The dashed box is a plan, not built; the Listener (Smart Turn v3.2) is built but not validated.
- **Figure:** the mermaid diagram in `README.md`, redrawn with the ladder and the dashed planned box

## 4. The Commit Harness
- Propose -> Settle -> Commit: the voice model proposes a call; the harness holds it until the user is quiet (0.9 s; 1.8 s after a filler or correction cue); cap any hold at 8 s
- Supersede: a newer call to the same tool after more user speech replaces the held one; the stale one never runs
- Dedupe: an identical call is never executed twice
- Draft-call hold and dangling-word trigger for placeholder calls and trailing-off sentences
- Added after the final benchmark run, unit-tested, not yet scored: retraction ("never mind"), backchannels ("okay", "mm-hmm" are not a new turn), conservative identifier joining ("B-O-B-1-2" -> "BOB12", a stated assumption)
- Practice-set evidence (62 items, not the benchmark): Reflex-only 41/62, Reasoner config 41/62, stale calls 5/30 vs 4/30. Mid-sentence pause catch: Reflex 15/25, Reasoner 16/25, combined 17/25
- **Speaker notes:** Be plain that the Reasoner roughly ties Reflex; combining them catches slightly more mid-sentence pauses. A pause after a sentence that already sounds finished ("Track order QM77 [pause] wait, no, QM78") is not caught by any turn judge, which leads into slide 6.
- **Figure:** optional timeline sketch: held -> superseded vs held -> executed

## 5. Results (honest)
- Judged (Gemini 2.5 Pro stand-in for GPT-4o): pipeline **61/100** vs baseline **62/100**; strict: 46 vs 50. We do not beat the baseline overall.
- Gains: housing 0.346 vs 0.192, self-correction 0.529 vs 0.471, 3-tool 0.375 vs 0.312
- Losses: e-commerce 0.586 vs 0.759, pause 0.50 vs 0.611. Unchanged: travel 0.65, finance 0.88
- First reply median 6.4 s for the pipeline; baseline 4.00 s. No latency improvement claimed.
- **Speaker notes:** Lead with the honest headline. The two-point overall gap is within what we cannot distinguish from noise (single run each). The prompt change and the Commit Harness are not separated on the full benchmark, so do not attribute the housing gain to the Commit Harness alone.
- **Figure:** the results and slice tables from `README.md`

## 6. Failure analysis: late changes
- Of 14 same-tool repeats in the pipeline run: 4 legitimate parallel pairs kept (all passed), **10 late changes** (user resumed 1.4-10.7 s after the first call), **all 10 failed**
- No hold window fixes these: a hold long enough would stall every normal turn, and nobody can foresee a correction not yet spoken
- Conclusion: the remedy is undo / rollback after execution, not a longer hold -> the extension
- **Speaker notes:** This is the honest limit of a hold-based design and the bridge to the extension. The rollback exists in the extension, not in the benchmark agent.
- **Figure:** simple timeline: call at t=0, correction at t=+1.4 ... +10.7 s, call already executed

## 7. Extension: recovery layer, two scenario packs
- Audio-only assistant with mock tools, aligned with the organizers' request to show recovery from slow or failing tools. **Two packs on one agent and one recovery layer** (`EXT_PACK=car|home`): in-car (reroute, traffic, EV charging, roadside) and a Bixby-style home pack (mock SmartThings-like AC, lights, washer, energy check, find phone, service centre). Mock scenario only, **not a Bixby or SmartThings integration**
- **Timeout** per attempt; **retry** with backoff for plain failures; a state-changing call that times out is never blindly retried
- **Idempotency**: same tool + arguments returns the cached result, no double booking / double washer start
- **Rollback**: change of mind after a booking (or washer start) succeeded -> cancel the old one first, then start the new one; if the cancel fails, hand off to a human
- **Read-back / progress**: "still checking..." while a tool is slow, a spoken summary of what was cancelled and started, a handoff reference after repeated failures
- **Scales by...** (status labels, keep them on the slide): new tools/plugins (MCP-style) pass through the same Commit Harness and recovery layer, *Built and tested offline* (a local mock plugin, 19 checks; not attached to the live agent, no real plugin wired); new scenarios by swapping tool packs, *Built and tested offline*; Reflex -> Reasoner -> stronger model ladder, Reflex + Reasoner *Built and benchmarked*, escalation *Designed, not built*; Listener (Smart Turn v3.2) acoustic end-of-turn, *Built, not validated*; graceful degradation (Reasoner down -> Reflex, tool down -> retry then human), *Built and tested offline*; on-device Gemma fallback, *Built, not validated* (FunctionGemma installed, module and offline tests; accuracy not measured)
- 35 (car) + 28 (home) offline tests pass; the live LiveKit run is [confirm status with the team before presenting: not run live per the last WORKLOG entry]
- **Speaker notes:** Tools are deterministic mocks. The home pack shows the recovery layer is scenario-independent (no change to `recovery.py`), not that we integrated with Bixby. Do not say a real plugin (Drive, calendar) is connected or that the plugin path runs in the live agent; do not quote any accuracy for the local Gemma fallback (not measured); do not say the Listener (Smart Turn v3.2) is validated. If the live take is not recorded, say so and show the design and tests instead.
- **Figure:** diagram from `extension/DESIGN.md`, or the demo clip once recorded

## 8. Reproducibility and next steps
- `reproduce.sh` reproduces a run from one command; versions pinned in `project-log/runs/env-freeze.txt`; every reported run has its logs in `project-log/runs/`
- Default path is a plain `GOOGLE_API_KEY` (our own runs used Vertex; the key path is not yet smoke-tested); the Reasoner (TypeSafe Jev) and the judge are optional and fall back cleanly (Reflex-only, exact-match)
- Not yet done: a clean-machine end-to-end run of `reproduce.sh`, a second run for variance, scoring with the GPT-4o judge, practice-set scoring of retraction/backchannel/identifier handling and the `GATE_LEAN` switch
- Built but not validated: the Listener (Smart Turn v3.2, acoustic end-of-turn; `GATE_SMART_TURN=1`, not in the benchmark config). Tested offline only: plugin path (local mock plugin). Built, accuracy not measured: on-device Gemma fallback. Planned, not built: escalation to a thinking model
- **Speaker notes:** Reproducibility gates the benchmark score, so say exactly what was verified. Do not state that planned items exist.
- **Figure:** none, closing bullet slide
