# Questions we expect, answered

Format: each entry is a short decision record (Context, Decision, Consequence: the ADR form by Michael Nygard) written answer-first (BLUF: bottom line up front). Every number comes from `SCORES.md` or a cited source. Names: Commit Harness = `fdb_agent/gate.py`; Reflex = its rule-based decider; Reasoner = TypeSafe Jev; Listener = Smart Turn.

## 1. Why Gemini Live as the voice model?
**Answer:** it was the strongest real-time voice model we could use that also calls tools, and the organizers prefer Gemini/Gemma.
- Context: the benchmark needs speech in, speech out and tool calls in one model.
- Evidence: FDB-v3 paper: Gemini Live fastest to complete (about 4.25 s vs 10.12 s for a cascaded pipeline). Our stock-agent run with Gemini 3.8 Live: 62/100 judged.
- Consequence: we depend on a hosted model; nothing of ours runs on a GPU.

## 2. Why a harness around the model instead of training a model?
**Answer:** the failure we targeted is about *when* to act, not *what* to say, so we tried a small layer instead of training. The measurement says it rarely matters on this benchmark (see the last bullet).
- Context: the paper names self-correction as the most consistent failure; the model calls a tool at the first pause, before "no, sorry, New York".
- Decision: hold each proposed call until the turn settles, replace it on a correction, withdraw it on "never mind", never run it twice.
- Our agent's scores on the target slices (29 September): self-corrections 0.529 vs 0.471 stock; 3-request turns 0.375 vs 0.312; housing 0.346 vs 0.192. These are differences of one to four recordings.
- What the decision log shows: of 148 proposed calls in that run, 146 executed unchanged; the harness replaced one and blocked one duplicate (2 of 100 recordings). Gemini Live proposes a call only after it judges the turn finished, so there is rarely anything left to replace. The gains therefore do not come from replacing calls; our prompt rules also differ from the stock agent and were not tested separately.
- Consequence: slower first reply (median 6.4 s vs 4.0 s), and overall 61 vs 62: we did not beat the stock agent overall.

## 3. Why did the overall score not improve?
**Answer:** gains and losses cancelled out, and 10 failures are of a kind no hold can fix.
- Losses: shopping 0.586 vs 0.759, pauses 0.50 vs 0.611.
- The 10 cases: the user changed their mind 1.4 to 10.7 s after the first call had already run. Those need undo, which is what the extension's rollback does.
- Three of the pipeline's 100 recordings were silent (the agent never heard the user: empty transcript, no call), against none in the stock run. They are counted as failures. Cause not established; machine load is the leading explanation (see README, Honest limitations).
- A second full run with today's changes is in progress; its result will be reported as it comes out.

## 4. Why TypeSafe Jev (the Reasoner)?
**Answer:** to judge meaning ("is the user finished?", "correction or second request?") where keyword patterns are unsure, with a typed answer and probabilities.
- Decision: 0.8 s timeout; on any failure the Reflex layer decides alone.
- Evidence (our practice set, mid-sentence pauses): Reflex 15, Reasoner 16, combined 17 of 25, largely the same items. A small gain, reported as small.
- Consequence: one extra network call per user turn.

## 5. Why Gemma for the offline fallback, and why FunctionGemma?
**Answer:** it is the open, on-device model family from the same vendor as our main model, the organizers prefer it, and FunctionGemma is the variant built for choosing tools.
- Context: if the cloud is unreachable, a car or appliance should still handle simple commands.
- Decision: FunctionGemma (300 MB) through Ollama, CPU only. Risky actions (booking, cancelling, starting an appliance) are never executed offline; they come back as "needs confirmation".
- Evidence: Google reports FunctionGemma at 58% before and 85% after fine-tuning on its Mobile Actions task. **Our own result is poor:** measured twice on our 40 test commands (CPU, while the benchmark was running): 11/40 and 13/40 fully correct (27.5% and 32.5%), 0 of 18 in-car commands correct in both runs, 15 to 18 of 40 with no answer. Not usable as built. We did not fine-tune. Part of the loss is our wiring (replies lost between the model and our module), part is the model (wrong values), and the measurement ran under load, so it should be repeated on a quiet machine.
- Consequence: it is a fallback for the extension only. It is not in the benchmark pipeline and not needed to reproduce our score.

## 6. Why Smart Turn (the Listener), and is it in the score?
**Answer:** words alone miss a silent thinking pause; Smart Turn hears it. It is built but not in the benchmark configuration.
- Evidence: open source (BSD-2), 8 MB, runs on CPU; its authors report 94.31% on English test data. We have not validated it on real voices ourselves.
- Consequence: documented as "built, not validated".

## 7. Why Gemini 2.5 Pro as the judge, not GPT-4o?
**Answer:** we had no GPT-4o access; we used Gemini 2.5 Pro with the benchmark's own judge prompts, unchanged.
- Both agents were scored by the same judge, so the comparison between them is like for like.
- The judge returned a usable verdict for every item (119/119 for our run, 121/121 for the stock run).
- We do not claim it is a better judge. A GPT-4o re-score may differ by a few items.

## 8. Did you tune on the benchmark?
**Answer:** no. We wrote 62 practice scenarios of our own and tuned on those. We read only pass/fail and failure kinds from benchmark runs, never the expected answers.

## 9. Is the extension a Bixby or SmartThings integration?
**Answer:** no. It is a recovery layer shown on two mock scenarios: in-car (35 offline tests) and a Bixby-style home assistant (28 offline tests). The device tools are mocks.

## 10. Can we reproduce it?
**Answer:** one command, `./reproduce.sh`, with pinned package versions and a pinned benchmark commit. It has been run on our development machine only. A clean-folder test found and fixed one install error; the fix has not been re-tested yet.

## 11. What is not done?
Plugins (MCP): a local mock plugin runs through the recovery layer in 19 offline checks; not attached to the live voice agent, no real plugin wired (future scope; real plugins exist for each benchmark domain, see `PLAN_PLUGINS_MCP.md`). Escalation to a stronger model on hard turns: designed, not built. Local fallback: measured at 27.5% and 32.5% fully correct in two runs, not usable yet. Listener: not validated.
