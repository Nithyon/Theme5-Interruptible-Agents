# Improvement plan: baseline/benchmark scores, Jev, extension

Written 2026-09-29, ~18:15 UTC. **Deadline is 30 Sep 18:00 IST freeze, 22:30 form** — under 24 hours from now, and the gate run started at 11:56 UTC today is *still running* (no `score.txt` yet). That fact shapes everything below more than any feature idea does: there is realistically room for **one more full 100-recording run**, maybe two if the current one finishes soon. Everything here is split into **Tier 1 (fits before freeze)** and **Tier 2 (only if the deadline actually moves to 4 Oct)** — don't spend Tier-1 hours on Tier-2 ideas.

One framing note for "improve baseline scores": the baseline (50/100 exact-match, 62/100 Gemini-2.5-Pro-judge — see below) is the **before** number; it doesn't change. What we're actually improving is *our agent's* number against it. This plan is about that gap.

## What's already better than it looked an hour ago

`project-log/SCORES.md` now has a second baseline row: **the same 100-recording run, re-scored with a Gemini 2.5 Pro judge (Vertex) = 62/100**, up from 50/100 exact-match. Two things follow from this:

1. **The judge-key problem is already solved.** Drop any plan to wire in Azure/OpenAI/Opus-as-judge — it's done, via Vertex, no new key needed. (Superseding my own earlier suggestions in this conversation.)
2. **The 12-point lift (50→62) tells us something diagnostic:** a real chunk of the "wrong-args" failures were formatting differences the judge forgives (dates, casing, phrasing) — not reasoning failures. The *remaining* gap after judging is the part that's actually about content: stale pre-correction values, mishearing, or a genuinely wrong call. That's exactly what the commit gate targets, and it's a stronger case for the gate's value than the raw 50/100 number alone.

## Tier 1 — do before the 30 Sep freeze

**1. Prompt patch for the worst domain (housing, 0.115) — cheapest lever available.**
`WORKLOG.md` already diagnosed this without touching ground truth: the 5 housing no-call failures were the model **asking a follow-up question** (city/bedrooms/address) instead of acting — even though the stock prompt already says "do not ask clarifying questions." The fix is a prompt strengthening, not an architecture change: something like *"if a parameter wasn't stated, use the most reasonable value from context and call the tool anyway — never ask, never wait."* This is a same-day, low-risk, high-expected-value change. **Action: draft the exact prompt diff for `gate_agent.py`'s instructions (or wherever the system prompt lives) as a proposal for the lead session to apply** — not something I should apply myself since it's `fdb_agent/` code and outside my current task scope.

**2. Read the gate run's result, then branch — don't guess now.**
The gate run (`runs/2026-09-29_full_gate_gemini38/`) isn't finished. Two branches once it is:
- **If the gate's self-correction/pause numbers beat the baseline:** freeze it, spend any remaining run budget on a second pass for mean + variance (per `BUILD_PLAN_FDB_V3.md`'s own "report both runs and the mean" rule) rather than chasing new features.
- **If it doesn't clearly beat baseline:** check `gate_stats.log`'s supersede/duplicate counts and the still-open NON_BLOCKING item (`STATUS.md`: *"Gemini 3.8 tools are NON_BLOCKING by default, so the model may confirm an action while the gate still holds it"*) before touching anything else — that's the most likely reason a gate run would underperform, and it's a known, named risk, not a mystery to re-diagnose.
- Neither branch requires opening any `*_pass_rate_report.json` or other file containing `expected_args` — that's ground truth by another name (the scoring script writes expected values into its own report), so failure analysis should come from the lead session's own summary of the run, not from a Sonnet session reading the report directly.

**3. Extension: run it once, record it, stop.**
`extension/ext_agent.py` is a written-but-never-run draft. The 20% extension score is earned by a working 60–90s demo clip showing retry → supersede → handoff, not by adding more mock tools or scenarios. "Improve the extension" today means: **get someone to actually run `ext_agent.py` once, capture the demo per `extension/DESIGN.md`'s script, and stop** — polishing further has a low return this close to the deadline.

**4. Submission hygiene (cheap, easy to forget under time pressure).**
- Push the `runs/` folders — organizers explicitly check run logs, not just numbers (`project-log/meetings/2026-09-29_organizer_briefing_notes.md`, fact 2).
- Run the fresh-clone test of `reproduce.sh` at least once before the freeze — the PDF calls this the one thing to "never cut."
- Fill the AI-usage declaration form (still an open checkbox in `STATUS.md`).
- Remove the stale `TYPESAFE_API_KEY` checkbox from `STATUS.md`'s blocked-on-user list — the Deadline section 14 lines above it already says "Jev cut," so that checkbox reads like an open item when it isn't one anymore.

## Tier 2 — only if the deadline actually moves to 4 Oct

**Jev, with the exact prerequisite chain (each link costs real time):**
1. User obtains a `TYPESAFE_API_KEY` (nobody else can do this step).
2. Declare it to the organizers as a new non-Gemini dependency — the briefing said they *"might reach out... for reproduction steps"* for anything outside Gemini/Gemma, so this isn't free reproducibility the way the current agent is.
3. Kokoro installed in the separate `~/theme5/tts-env`, `devset/make_audio.py` actually run to produce audio.
4. A dev-set A/B run (`devset/run_dev.sh` + `score_dev.py`, built in S11) comparing Jev-augmented gate vs. the rules-only gate — this is the literal condition `DECISIONS.md` set for keeping Jev at all: *"keep only if it beats the rules-only gate on our dev set."*
5. Only then, a full 100-recording run with Jev wired in.

That's four sequential steps before Jev could even be *measured*, let alone shipped — not realistic inside the remaining Tier-1 hours.

**Where Jev actually plugs in, if this becomes live** (already identified, kept here so Tier 2 starts from a spec, not from scratch):
- `fdb_agent/gate.py`'s `required_quiet()` / `ends_hesitantly()` — replace the fixed word-list + timer with Jev's *"is the user done, or still correcting?"* call, so the gate commits faster on genuinely finished turns and holds longer on ones that only look finished.
- The supersede loop in `CommitGate.run()` — replace the mechanical "same tool name, newer speech epoch → supersede" rule with Jev's *correction / addition / retraction / new_request / backchannel* classification, which is what correctly separates a real correction from two genuine same-tool requests in one turn (exactly the case `devset/scenarios.jsonl`'s `s04`/`s13`/`s24`/`s33` test).

**Extension, if there's more time:** wire `recovery.ToolRunner`'s idempotency/supersede ideas more tightly to the actual gate (shared vocabulary between the two recovery layers), add 1-2 more mock tools, build the camera-frame lookup the organizers said is a Round-2 idea. None of this is Tier 1.

## Summary table

| Item | Tier | Owner | Cost |
|---|---|---|---|
| Housing follow-up-question prompt fix | 1 | Draft by Sonnet, apply by lead (touches `fdb_agent/`) | Small |
| Read gate run result, branch | 1 | Lead session | Free (already running) |
| Run + record extension demo once | 1 | Whoever has LiveKit access | Small |
| Push runs/, fresh-clone test, AI form, clean up stale checkbox | 1 | Lead/Docs owner | Small |
| Jev (full chain) | 2 | User (key) → Lead (wiring + A/B) | Large, sequential |
| Extension polish / camera lookup | 2 | Extension owner | Medium |
