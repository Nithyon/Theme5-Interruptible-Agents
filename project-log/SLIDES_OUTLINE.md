# Slide outline (max 8 slides)

Draft for the Theme 05 submission deck. Every number is either sourced or marked TBD — nothing here is invented ahead of the frozen results.

## 1. Problem
- Full-Duplex-Bench v3: 100 real disfluent recordings, 12 tools, 4 domains, strict Pass@1 scoring
- Strict scoring fails on **any** extra/wrong/early tool call — verified in the benchmark's own `evaluate_pass_rate.py` (multiset match + precision check)
- The organizers' own framing: interruption is a state-consistency problem, not just a speech-recognition one
- **Figure:** none — text slide

## 2. Why agents fail
- Published paper numbers (arXiv 2604.04847): GPT-Realtime 0.600 Pass@1, but only 58.8% on self-correction scenarios specifically
- Self-correction is named as one of the most consistent failure modes across *every* system tested — GPT-Realtime, Gemini Live 2.5/3.1, cascaded, Grok, Ultravox
- Root cause: a call fired on the pre-correction value ("Boston... no, New York") still counts as executed and still fails the scenario even after the right call follows
- **Figure/table:** the paper's Pass@1 table from `README.md`'s "Why this design" section

## 3. Architecture
- LiveKit room → Gemini 3.8 Live (realtime) → **commit gate (+ Jev)** → 12 stock tools → tool log
- The gate sits between the model's proposed call and the real tool execution — same tool functions, same log format as the stock agent, nothing changed downstream
- Talker (spoken response) and reasoner (tool-calling) share one realtime model here, not split into separate stages
- Jev (TypeSafe) is an optional typed classifier layered on the gate — a rules-only fallback fires whenever it times out or has no answer, so it can only help, never block
- **Figure:** the mermaid diagram from `README.md`'s Architecture section

## 4. The commit gate (+ Jev)
- Hold until the user is quiet for 0.9 s — or 1.8 s if their last words are a filler/hesitation/correction cue (um, wait, actually, no, I mean...) — or, when Jev is available, a typed "is this turn actually finished?" judgment instead of the fixed timer
- Supersede: a newer call to the same tool, after the user speaks again, replaces the held one — the stale one is dropped, never executed, never logged; Jev additionally classifies *what kind* of follow-up it is (correction / addition / retraction / new request / backchannel)
- Dedupe: canonicalized-argument check blocks executing an identical call twice
- Draft-call hold + dangling-word trigger: catches Gemini's mid-sentence placeholder calls (empty/default args) and utterances that trail off on an incomplete word
- **`GATE_COMBINE=either` — rules and Jev vote together, not Jev alone:** hold if *either* says the user is still going; fast 0.4s release only when Jev says complete **and** the rules see no hesitation. Decision-level eval (`devset/eval_decisions.py`): turn-state accuracy rules 0.796 vs Jev 0.714 vs combined 0.735 (Jev alone is *not* more accurate); but mid-sentence pause catch is rules 0.60, Jev 0.64, **combined 0.68** — the two catch different mistakes, so requiring agreement on early release beats either alone. Correction-vs-addition: 0.963 for both, a tie.
- 8 s hard cap so a long pause can't stall the conversation
- Timing constants tuned on our own 62-item synthetic dev set (`devset/scenarios.jsonl` + Lohit's 12 pause scenarios), not on FDB-v3 itself — never on the graded test items
- **Figure:** none, or a small before/after timeline sketch (held → superseded vs. held → executed)

## 5. Results
- Baseline (stock agent, `gemini-3.8-live`, no gate, all 100): **50/100 (0.50) exact-match**, perceived latency median 3.92 s
- Failure breakdown: self-correction 0.471, pause 0.389, false start 0.667 (by disfluency); travel 0.15, housing 0.115 lowest domains
- **Dev-set tuning (README.md, "How we tuned"):** rules-only gate (A2) 41/62, 5/30 stale calls, 4.16s — Jev+extras (C) 41/62, 4/30 stale calls, 4.24s. Roughly a tie on pass rate, a modest reduction in stale calls; remaining failures are pauses *after* a complete-sounding sentence, which no turn judge can foresee
- **Full 100-recording benchmark, `GATE_COMBINE=either` (rules + Jev as one decider) + draft hold + dangling trigger + prompt v2: TBD — run in progress** (`gate_gemini38_final`, started ~15:23 UTC 2026-09-29; an earlier config-C-only run was stopped at 10/100 once the combined decider was adopted), frozen number and log link added before submission
- `--use-llm` judge column: **TBD**, pending an OpenAI/Azure key
- **Figure:** the Results table from `README.md`, with the gate row filled in once frozen

## 6. Extension (placeholder)
- Organizer briefing: FDB-v3 has no video input in Round 1; they explicitly asked for tool-failure and variable-latency recovery to be shown
- Planned: audio-only "slow/failing tool recovery" scenario — same coordinator (talker/reasoner/gate), a second adapter feeding it slow/failing mock calls
- Shows: retried read-only call, a state-changing call never blindly retried, clean handoff when recovery isn't possible
- **Marked explicitly as not yet built** — this slide is the plan, not a result
- **Figure:** none yet — replace with a demo clip once built

## 7. Limitations
- One baseline run so far; gate run and a second full run still pending
- Exact-match only until a judge key is wired in
- Cloud-dependent reasoner, no local fallback in the current build
- Tuned only on our own 62-scenario synthetic dev set (50 ours + Lohit's 12 pause scenarios), never on the real 100 test recordings
- Extension is a plan, not working code, as of this slide
- **Figure:** none — bullet list, matches `README.md`'s Honest Limitations section verbatim

## 8. Next steps
- Finish the gate run, freeze both exact-match and (if ready) judge-scored numbers
- Second full run for mean + variance
- Build the tool-recovery extension
- Fresh-clone test of `reproduce.sh` before the 30 Sep 11:59 PM IST deadline
- **Figure:** none — closing bullet slide
