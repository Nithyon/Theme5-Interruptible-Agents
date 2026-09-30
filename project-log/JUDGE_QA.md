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
- Consequence: a slower reply (submitted run: median 5.3 s against 3.9 s for the stock agent). On 29 September we were one behind the stock agent (61 vs 62); with the submitted settings we are ahead (67 vs 62), and the log says that gain is not from replacing calls.

## 3. Why was the 29 September score below the stock agent, and what changed?
**Answer:** on 29 September the gains were cancelled by identifier formatting in shopping, three silent recordings and extra waiting. The submitted settings add an identifier rule, handling for withdrawals and listening sounds, and faster release, and score 67 judged and 55 strict against 62 and 50.
- 29 September losses: shopping 0.586 vs 0.759, pauses 0.50 vs 0.611. Three of that run's 100 recordings were silent (the agent never heard the user), against none in the stock run; machine load is the leading explanation.
- Ten failures were changes of mind 1.4 to 10.7 s after the first call had already run. No hold can fix those; they need undo, which the extension's rollback does.
- Submitted run against the stock agent (judged): shopping 24/29 vs 22/29, finance 22/25 vs 22/25, housing 7/26 vs 5/26, travel 14/20 vs 13/20; two requests per turn 13/18 vs 11/18, three requests 7/16 vs 5/16; self-corrections 7/17 vs 8/17 (one worse). No silent recordings.
- We changed four things at once and did not test them separately, so we do not claim which one produced the gain.

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
- Update, later on 30 September (teammate's laptop, idle, same 40 commands, one run each): FunctionGemma 24/40 right tool and 15/40 fully correct. Gemma 4 26B first returned nothing on 38 of 40 because its thinking mode used up the reply limit; with thinking off it scored 40/40 right tool, 38/40 fully correct, 6/6 self-corrections, median 5.4 s. Qwen3 30B: 38/40 and 36/40. The 40 commands are our own, typed, not a published set. Gemma 4 26B is a large model for a PC or car computer, not a phone.
- Fallback suite on Aryan's laptop (Core Ultra 7 258V, 32 GB, no discrete GPU, one run): our 40 commands 34/36 fully correct and 4/4 correctly left alone; 111 real SLURP requests 45/51 light requests right, and it acted on 0 of 60 requests no tool fits. About 6 s per command. The 3 GB Gemma 4 e4b ties on our own commands but gets only 18 of 51 real SLURP light requests right (it declines most), so the fallback needs the large model for now.
- Consequence: it is a fallback for the extension only. It is not in the benchmark pipeline and not needed to reproduce our score.

## 6. Why Smart Turn (the Listener), and is it in the score?
**Answer:** words alone miss a silent thinking pause; Smart Turn hears it. We built and tested it, and it is switched off in the submitted configuration.
- Its authors report 94.31% on English test data; it is open source (BSD-2), 8 MB, and runs on CPU.
- Our checks: on older real recordings it recognised pauses 74 to 84% of the time but true ends of turn only 17 to 36% (balanced accuracy 0.50 to 0.57). In a live run it said "not finished" five times after the user had finished.
- A full run with it on scored 64 judged and 50 strict. That run is handicapped by a defect of ours: the model is loaded at the start of every recording, which stalls the agent for about 7 s, so it is not a fair test of Smart Turn.
- Consequence: off in the submitted run. Next: load it once, give it one vote of three instead of a veto, and test again.

## 7. Why Gemini 2.5 Pro as the judge, not GPT-4o?
**Answer:** we had no GPT-4o access; we used Gemini 2.5 Pro with the benchmark's own judge prompts, unchanged.
- Both agents were scored by the same judge, so the comparison between them is like for like.
- The judge returned a usable verdict for every item (131/131 for the submitted run, 121/121 for the stock run).
- We do not claim it is a better judge. A GPT-4o re-score may differ by a few items.

## 8. Did you tune on the benchmark?
**Answer:** we never read the benchmark's expected answers, and we tuned thresholds on 62 practice scenarios of our own. Two things did use benchmark runs, and we disclose them.
- We looked at pass/fail results, failure kinds and our own agent's outputs from benchmark runs. The identifier formatting rule came from that.
- On 30 September we ran two configurations on the benchmark (Smart Turn off and on) and submit the better one. Both runs' logs are in the repository.

## 9. Is the extension a Bixby or SmartThings integration?
**Answer:** no. It is a recovery layer shown on two mock scenarios: in-car (35 offline tests) and a Bixby-style home assistant (28 offline tests). The device tools are mocks. Both were run end to end on recorded request clips through LiveKit on 30 September; the in-car EV assistant is the headline scenario (`runs/2026-09-30_ext_car_e2e/`).
- Real speech: those two runs use a synthetic request voice. We also played 11 real recordings from the SLURP test set (Bastianelli et al., EMNLP 2020; light-control requests, headset microphone, fixed selection rule) to the home assistant, with the lights tool failing on its first attempt: 10 of 11 ended in a lights action, all 8 injected failures were recovered by a retry, one colour request was declined (no such tool). The first attempt of this run exposed a defect: a repeated request was answered from memory although the lights had been changed in between. We fixed it and re-ran; both runs are kept (`runs/2026-09-30_ext_home_slurp_fail1/` and `_attempt1`). Limits: 11 recordings, one run, the room is not scored because most requests name none, the tools are mocks.

## 10. Can we reproduce it?
**Answer:** one command, `./reproduce.sh`, with pinned package versions and a pinned benchmark commit. It has been run on our development machine only. A clean-folder test found and fixed one install error; the fix has not been re-tested yet.

## 11. What is not done?
Plugins (MCP): a local mock plugin runs through the recovery layer in 19 offline checks; not attached to the live voice agent, no real plugin wired (future scope; real plugins exist for each benchmark domain, see `PLAN_PLUGINS_MCP.md`). Escalation to a stronger model on hard turns: designed, not built. Local fallback: usable only with a large model (Gemma 4 26B, 38 of 40 fully correct); the small FunctionGemma is not (15 of 40); not wired into the voice agent. Listener (Smart Turn): tested, not reliable as wired, off in the submitted run.
