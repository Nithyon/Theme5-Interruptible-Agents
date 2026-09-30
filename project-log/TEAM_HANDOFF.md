# Team handoff (submission day, 30 Sep 2026)

Deadline: **23:59 IST, 30 Sep 2026.** Aim to submit the form by **22:30 IST**.

Names used in this document vs. the code: Commit Harness = `fdb_agent/gate.py` (`CommitGate`, settings `GATE_*`); Reflex = the rule-based decider in `gate.py`; Reasoner = `fdb_agent/jev.py` (TypeSafe Jev); Listener = `fdb_agent/smart_turn.py` (Smart Turn v3.2).

**The organizers' briefing checklist (every point, with status and owner) is at the end of this file: "Everything the organizers said (briefing, 2026-09-29) — point by point".** The results table may be updated tonight, check `SCORES.md`.

## Who edits what
| Person | Edits | Output |
|---|---|---|
| README polisher | `README.md` (root) only | final README on GitHub |
| Deck maker | `project-log/SLIDES_OUTLINE.md` -> slides | deck, max 8 slides |
| Video | `project-log/VIDEO_SCRIPT.md` | 3-5 min video |
| Form filler | `project-log/AI_USAGE.md` as source | AI-usage declaration form |

Do not edit `SCORES.md`, `fdb_agent/` or run folders. If a number looks wrong, tell the lead instead of changing it.

## Where every number comes from
- `project-log/SCORES.md` is the source of truth (overall, per-slice, latency, failure counts).
- Raw evidence: `project-log/runs/2026-09-29_full_gemini3_8/` (baseline), `runs/2026-09-29_full_gate_gemini38_final/` (final pipeline; `score.txt` strict, `score_geminijudge.txt` judged), `runs/2026-09-29_decision_eval.json` (Reflex vs Reasoner decisions), `runs/2026-09-29_dev_*` (62-item practice set).
- Headline numbers: judged 61/100 (pipeline) vs 62/100 (baseline); strict 46 vs 50; first reply median 6.4 s vs 4.00 s.
- Paper numbers (arXiv 2604.04847) are verified in `RESEARCH_NOTE_FDB_AUTHORS.md`.
- If a number is not in SCORES.md, WORKLOG.md or a run folder, do not use it.

## Claims you must not make
- Do not claim we beat the baseline overall (61 vs 62 judged, 46 vs 50 strict). Say: gains in housing, self-correction, 3-tool; losses in e-commerce and pause.
- Do not claim any latency improvement or any latency figure that is not in SCORES.md (the pipeline's first reply is slower).
- The judge was **Gemini 2.5 Pro as a stand-in for GPT-4o**, not GPT-4o. Never call the numbers "GPT-4o-judged".
- Do not compare our numbers with the paper's as like-for-like.
- Do not say plugins / MCP connectors or a local Gemma model are implemented: both are designed, not built (README "Scalability and what comes next"). Do not say the Listener (Smart Turn v3.2) is validated.
- Do not call the home scenario a Bixby or SmartThings integration: it is a Bixby-style mock scenario, offline-tested (28 tests), on the same recovery layer.
- The Listener (Smart Turn v3.2) is built behind a switch (`GATE_SMART_TURN=1`) with offline tests only; it is NOT validated on real voices and NOT in the benchmark config. Do not claim it improved any score. Escalation to a thinking model and a local fallback are planned only.
- Retraction, backchannel and identifier-joining handling were added after the final run and are unit-tested only; do not attribute any benchmark result to them. `GATE_LEAN` exists as a switch, is being evaluated on the practice set (run E), and is not in the submitted config.
- Do not attribute the housing gain to the Commit Harness alone (a prompt change was made at the same time, no ablation).
- Do not say we tuned on or looked at the 100 benchmark recordings. Tuning used our own 62-item practice set only.
- Do not claim the extension ran live unless someone has actually run it and recorded it (check WORKLOG). It uses mock tools.
- Do not claim `reproduce.sh` was verified on a clean machine (it was not, as of the last WORKLOG entry).
- Do not cite "human hesitation pauses of 600-900 ms": it is not in the paper.
- Do not say the Listener (Smart Turn v3.2) works on Indian-English accents (not checked).

## Submission checklist
- [ ] GitHub repo link works, README renders, no secrets or `.env` files committed
- [ ] Deck: max 8 slides, numbers match README
- [ ] Video: 3-5 minutes, unedited takes preferred, no untrue "live" claims (see the fallback lines in VIDEO_SCRIPT.md)
- [ ] AI-usage form filled from `AI_USAGE.md` (the form is not that file)
- [ ] Form submitted by **22:30 IST** (hard deadline 23:59 IST, 30 Sep 2026)
- [ ] Final `git push` done and the repo link in the form points to the pushed commit

## Known open items (be honest about them)
- No GPT-4o scoring, no second run for variance, no clean-machine run of `reproduce.sh`.
- Extension live run and video take depend on someone running `extension/ext_agent.py`.
- The extension now has two packs (in-car, 36 offline tests; Bixby-style home, 28 offline tests), chosen by `EXT_PACK=car|home`. README has a "Scalability and what comes next" section with a status label per row; deck and video fold it in. Launch commands for the demos are at the top of `VIDEO_SCRIPT.md` (not yet rehearsed live).


## Everything the organizers said (briefing, 2026-09-29) — point by point

Source of truth: `project-log/meetings/2026-09-29_organizer_briefing_transcript.md` (auto-transcribed, so some words are garbled; those points are marked "unclear in transcript"). Quotes are exact and short so you can search for them. Status is as of 30 Sep 2026: DONE / PARTLY / NOT DONE / N/A. The results table may be updated tonight, so check `project-log/SCORES.md` for final numbers.

### Still open before submitting (most important first)

1. **Clean-machine run of `reproduce.sh`** (points 16, 28, 64): organizers rerun the code and "we do not believe your numbers". It has only been run locally, never on a clean machine. Owner: user (AWS g5 box, OBJECTIVES B1).
2. **Demo video recorded** (points 25, 31, 35): not recorded. Script exists (`VIDEO_SCRIPT.md`). The in-car extension agent (`extension/ext_agent.py`) has not been run live yet, so the extension segment cannot be shown live until someone runs it. Owner: video.
3. **Slide deck built** (points 32, 53): only an outline exists (`SLIDES_OUTLINE.md`). Owner: deck maker. Note the transcript says "one PPT slide" (unclear, see point 31) while our plan says max 8 slides; the user should confirm against the participant guide.
4. **AI-usage declaration form filled and submitted** (point 82): not done; the README currently says it is filled out, which is untrue until the user does it. Owner: user (source: `AI_USAGE.md`).
5. **Google Drive link for the agent audio logs in the README** (point 30): TODO for the user (zip files from `D:\Theme5-Interruptible-Agents\logs-audio\`). Owner: user, then README polisher adds the link.
6. **Requirements file** (point 17): organizers asked for an updated "requirements file"; the repo has no `requirements.txt`, only `project-log/runs/env-freeze.txt` (used by `reproduce.sh`). Owner: README polisher to name env-freeze.txt as the requirements file (or lead to add one).
7. **Plain `GOOGLE_API_KEY` path never smoke-tested** (points 45, 92): our runs used Vertex; the README's default reproduction path is a plain key (OBJECTIVES B2). Owner: user.
8. **Final full benchmark run with the new config may happen tonight**: if it lands, README, deck and video numbers must be updated from `SCORES.md` (checks in points 33, 50, 65). Owner: lead, then README polisher and deck maker.
9. **Bixby point** (point 66): Bixby-style mock scenario built (home pack), offline-tested; **not a Bixby integration**. Do not claim a Bixby link. Owner: deck maker and video.
10. **Check the organizers' follow-up PDF and emails** (points 26, 40, 87): a PDF and a possible deadline update were promised. Owner: user.
11. **Per-recording result JSON files** are being added under each run folder's `per_recording/` (point 30): make sure they are pushed. Owner: lead.

### Logs included

- All run logs are in `project-log/runs/`: agent log (`agent.log`), inference log (`inference.log`), every tool call (`agent_tool_calls.log`), the Commit Harness decision log (`gate_events.log`, `gate_stats.log`), strict and Gemini-judged score reports (`score.txt`, `score_geminijudge.txt`, the `*_pass_rate_report*.json` files), and the settings used per run (`run.txt`). Practice-set runs are in `runs/2026-09-29_dev_*` and `runs/2026-09-30_dev_*`.
- Per-recording result JSON files are being added under each run folder's `per_recording/`.
- The agent's recorded audio is too big for git. It goes to Drive as zip files from `D:\Theme5-Interruptible-Agents\logs-audio\`. The user uploads them and the README must link the Drive folder.
- **TODO (user): upload the audio zips to Google Drive and give the README polisher the folder link. Drive link: NOT YET CREATED.**
- Why this matters: the organizers said run logs will be compared to quoted numbers (points 30, 65).

### The points, in transcript order

Owner column: "none" means no action needed. "Lead" is the lead Claude session.

| # | Point (plain words) | Exact quote | Status | Owner |
|---|---|---|---|---|
| 1 | The participation toolkit is replaced by a public benchmark, Full-Duplex-Bench v3. | "we are switching it with something which is publicly available" | DONE: README, `SCORES.md`, all runs use FDB-v3. README "History" says the kit is retired. | none |
| 2 | The benchmark judges real-life domains (flight booking, e-commerce) where tool calls are slow and can break the flow. | "flight booking or e-commerce or certain other things that are very relevant to real life" | DONE: slices reported for finance, e-commerce, travel, housing in `SCORES.md`. | none |
| 3 | Public checkpoints or hosted APIs are both fine. | "take the public checkpoints or if you are uh using APIs for uh your solution that is also fine" | DONE: hosted Gemini 3.8 Live, declared in README. | none |
| 4 | Custom checkpoints are accepted if they fit the limit. | "If you are willing to provide your own checkpoints custom checkpoints, we will accept that." | N/A: we use no custom checkpoint. | none |
| 5 | GPU limit number is garbled. Later (points 41, 84) the plain figure is 48 GB. | "16,000 uh A6000 GPU" | unclear in transcript. We rely on the 48 GB figure stated plainly elsewhere. | none |
| 6 | Special requests: contact the organizers. Also a cut-off sentence about "12" and pooling. | "if you have special uh request, please reach out to us" and "post that at 12, means uh we will have to do some pulling around it" | N/A. The second sentence is unclear in transcript. | none |
| 7 | Round 2 may raise the compute estimate. | "we will uh increase this estimate uh for the later rounds" | N/A: Round 2 only. | none |
| 8 | Core goal: stay responsive throughout the conversation. | "you have to stay responsive throughout the conversation" | PARTLY: the pipeline's first reply median is 6.4 s vs 4.00 s for the stock agent (`SCORES.md`). An instant acknowledgement was proposed (OBJECTIVES G1) but is not built. Do not claim a latency win. | none (report honestly) |
| 9 | All tasks must actually get done. | "You have to make sure that all your tasks are done." | PARTLY: judged 61/100, strict 46/100 (baseline 62 and 50). | none |
| 10 | Tasks will fail; you must manage that. | "There will be instances where the tasks will fail. You will have to manage that." | PARTLY: the extension has timeout, retry, idempotency and human handoff (36/36 offline tests in `extension/test_recovery.py`; 28 more for the home pack) but has not been run live. The benchmark agent has no failure recovery layer. | video (live run) |
| 11 | Latency will vary; showing you handle it "will be very good". | "There will be instances where the latency will be variable." | PARTLY: extension narrates slow tools ("still checking") in offline tests only; not shown live. | video |
| 12 | Tool failures: recover cleanly by retry, closing the session, or human in the loop. | "you can retry, you can close the session, you can move it to human in the loop" | PARTLY: retry and human handoff exist in `extension/recovery.py`, offline tests only. | video |
| 13 | You may need a LiveKit account for the evaluation script. | "you might have to create a LiveKit account for it" | DONE: LiveKit Cloud used (README, "Declared models / APIs"). Organizers will need their own LiveKit credentials; README lists the variable names. | none |
| 14 | The data comes from a Google Drive link on the benchmark GitHub. | "they have provided the Google link uh Google Drive link" | DONE: `reproduce.sh` downloads and extracts the data. | none |
| 15 | You submit a score and all your code. | "you will provide us with a score and all your code" | DONE: repo and README. Numbers may be updated tonight, check `SCORES.md`. | README polisher (final numbers) |
| 16 | They rerun and check the score you promised. | "we will, you know, uh check it by our rerunning" | PARTLY: `reproduce.sh` has been run locally only, not on a clean machine. | user |
| 17 | Code must be runnable; README and requirements file updated. | "make sure that your code are runnable and uh the README and the requirements file" | PARTLY: README done. There is no `requirements.txt`; `project-log/runs/env-freeze.txt` is the frozen environment. Clean-machine run not done. | README polisher, lead |
| 18 | They may contact you if they cannot run the code. | "we will still reach out to you if uh if we are not able to" | N/A for us, but make sure the form has a contact we read. | user |
| 19 | Provide good documentation. | "I would recommend that you provide a good documentation around it" | DONE: `README.md`. Needs final polish. | README polisher |
| 20 | A use-case extension is added as a new part. | "we are adding one part for use case extension" | PARTLY: in-car extension (`extension/`) passes 36/36 offline tests (in-car) plus 28 (home pack); `ext_agent.py` never run live; mock tools only. | video, user |
| 21 | Scores are on the v3 variant only. | "we will be evaluating your scores over the v3 variant only" | DONE: only v3 was run. | none |
| 22 | You may look at the older variants (v1, v1.5, v2) for understanding and metrics. | "get some understanding and the other metrics from uh the older variants as well" | N/A: optional; not done. | none |
| 23 | Use cases beyond the benchmark are welcome in the submission. | "if you have certain use cases that, you know, go beyond this benchmark, feel free to include them" | PARTLY: extension exists but is unproven live. | video |
| 24 | Extension can be a use case, user experience, cost saving or latency saving; earns extra brownie points. | "award you extra brownie points for that" | PARTLY: the extension is a use case with recovery and rollback; we claim no cost or latency saving. | deck maker (state exactly what it is) |
| 25 | Docs and demo video must cover what you built, the approach and the architecture. | "what approach you have followed" | PARTLY: README covers approach and architecture; video not recorded; deck not built. | video, deck maker |
| 26 | Organizers said the session was not recorded and promised the PDF with everything. | "we will try to, you know, provide all the things in the PDF as detailed as possible" | N/A for us. The user should check whether the PDF arrived (see point 87). | user |
| 27 | The kit is replaced but the goals remain. | "The the only thing is that uh whatever participation kit that we have given is now replaced" | DONE: README "History". | none |
| 28 | Submit a code repository and a one-command reproduction script. | "code repository, uh one-command reproduction script" | PARTLY: repo and `reproduce.sh` exist; script not verified on a clean machine. | user |
| 29 | One-command is not meant literally, but wrap the commands in one script. | "Do not take one-command as very serious." | DONE: `reproduce.sh` at repo root. | none |
| 30 | Benchmark results AND run logs are required, because numbers can differ from logs. | "if you can provide the run logs also uh in addition to the numbers" | PARTLY: logs are in `project-log/runs/` (see "Logs included"); per-recording JSON files being added; audio zips must go to Drive with a link in README (TODO user). | user, lead |
| 31 | The demo video is still required. | "the demo video still remains intact" | NOT DONE: script only (`VIDEO_SCRIPT.md`). | video |
| 32 | The slide deck was communicated earlier. Later: "one PPT slide". Our plan is max 8 slides. | "The uh slide deck is something that we have already communicated" and "one slide uh one PPT slide, and the demo" | NOT DONE: outline only (`SLIDES_OUTLINE.md`). The "one PPT slide" wording is unclear in transcript (singular vs deck); confirm limits in the participant guide. | deck maker, user |
| 33 | 60% of the score is the benchmark score. | "60% of the uh score, you know, dedicated to the benchmark score" | DONE (informational). Numbers in `SCORES.md`; may be updated tonight. | none |
| 34 | The weights may change if many teams struggle on the benchmark. | "we might uh change the numbers" | N/A: not final; do not rely on it. | none |
| 35 | 20% for extending the "dual-mind" idea (one mind talks, one thinks) to other use cases. | "where one mind is talking and one mind is thinking" | PARTLY: talker plus Commit Harness design is the dual-mind; extension not run live. | video, deck maker |
| 36 | The remaining 20% is documentation and architecture. | "documentation and architecture will fetch you, uh you know, other 20%" | PARTLY: README done; deck, video open. | deck maker, video |
| 37 | Shortlisted teams may get extra use cases or multimodal inputs in round two. | "certain extra multimodal handling inputs so that we can judge you better" | N/A: Round 2. | none |
| 38 | Artificial Analysis is a reference, not a target to beat. | "I would not say that you have to beat these numbers" | DONE: `project-log/INDUSTRY_BENCHMARKS.md`. Not required in README. | none |
| 39 | Point to the FDB-v3 paper (arXiv) and its GitHub repo. Author name and "NTU and NVIDIA" are as transcribed. | "from NTU and NVIDIA" | DONE: README cites arXiv 2604.04847. The author name "Gaoxuan" is unclear in transcript; the affiliation is not confirmed by us. | none |
| 40 | Deadline: the transcript first says 30 September, possibly moving to 4 October; later "30th"; and once "30th of November" (that line is unclear in transcript and contradicts the rest). | "we can move it to 4th of October or something" ; "take 30th as the deadline for now" ; "extended to 30th of November" | DONE: we plan for 30 Sep (23:59 IST is our own working assumption, not in the transcript). "PRISM team will communicate" any change. | user (watch email) |
| 41 | 48 GB VRAM applies if you run your own checkpoint; else out-of-memory may mean no fair run. | "make sure that your model can run with a VRAM of 48GBs" | N/A: hosted model; the harness's own Parakeet ASR ran on a GPU fine. | none |
| 42 | Any model or architecture is allowed if it stays within the limit. | "you feel free to use any of the models, any of the architectures" | DONE. | none |
| 43 | Benchmark conversations are around two to two and a half minutes. | "most of the conversations are around two, two and a half minutes" | N/A. Our README says real inputs run 40 to 59 s. See "Contradictions" below. | README polisher (check) |
| 44 | Gemini and Gemma are still preferred (close integration, easy to reproduce), but other models are not restricted. | "we still stand with that uh statement" ; "there are no restriction" | DONE: Gemini 3.8 Live. | none |
| 45 | For Gemini and Gemma the organizers need no key; for another lab they may ask for reproduction steps. Ambiguous whether this covers our Vertex path. | "for Gemini and Gemma, uh we will not need the key" | PARTLY: README default path is a plain `GOOGLE_API_KEY` but it was never smoke-tested; our runs used Vertex with ADC. Also see point 92 ("We are not providing API keys"). | user |
| 46 | Provide guidelines for how to reproduce. | "you will have to provide us with certain guidelines how to reproduce them" | DONE: README "Reproduce". | none |
| 47 | The benchmark yields metadata and metrics over about 100 test cases; averaging them makes up the 60%. | "they have certain test cases, I guess 100 of them" | DONE: 100 recordings run. | none |
| 48 | It judges correct tool, correct parameters, speed and the response. | "whether you called the correct tool uh with the correct parameters" | PARTLY: strict 46 and judged 61 vs baseline 50 and 62; first reply slower. | none |
| 49 | Two scoring modes: local without an LLM, or the use-LLM flag with your own LLM as judge. | "you can either target locally, which will not involve an LLM" | DONE: both reported. Judge was Gemini 2.5 Pro as a stand-in for GPT-4o. The transcript says "your own LLM", it does not name GPT-4o. | none |
| 50 | Report the numbers and they will be considered. | "you will report the numbers, and we will consider those numbers" | DONE: `SCORES.md`. May be updated tonight. | README polisher |
| 51 | The 20% extension exists so you think beyond the 100 scenarios. | "so that you think beyond the bench as well" | PARTLY (see 20). | video |
| 52 | Documentation score covers quality of docs, architecture, problems addressed, gaps found and how they are overcome. | "what uh problems you have addressed" | DONE in README ("Why this design", "Honest limitations"); deck open. | deck maker |
| 53 | Docs means the same PPT and README. | "same PPT and README file" | PARTLY: README done, PPT NOT DONE. | deck maker |
| 54 | Do not fret about UX of docs; content matters. | "rather on the content" | DONE. | none |
| 55 | Listing the challenges you found is a good thing. | "if you are able to list them out, that is also a good thing to have" | DONE: README "Honest limitations" and failure analysis. | none |
| 56 | Docs should address the questions in this space. | "addresses all the uh questions uh that are there in this space" | PARTLY: README does; deck open. | deck maker |
| 57 | Video inputs: FDB-v3 has no vision input in round one; what we do is enough for round one. | "I don't think full duplex bench has any kind of vision inputs" | N/A: we have no video path; that is fine for round one. | none |
| 58 | A round-two possibility: tool calls, audio and video. Not a hard constraint. | "But it is not a hard constraint." | N/A. | none |
| 59 | Originality: you cannot claim a big lab's model as your own project. | "you cannot say that I am using GPT Realtime" | DONE: README states the baseline is the stock agent on Gemini 3.8 Live and separates what we added. | none |
| 60 | Replicating numbers from big labs on your environment is itself an achievement. | "you are able to reproduce numbers on your environment" | N/A: optional; the paper-calibration run was not done (OBJECTIVES C4). | none |
| 61 | They can detect copied work; contact you if in doubt. | "we do have techniques to, you know, understand whether it was taken from somewhere else" | DONE: sources and lineage are cited; teammate's upgrade pack is credited in `AI_USAGE.md`. | none |
| 62 | Some leniency because the requirements changed. Do not worry about the paper's numbers; pitch in your own. | "you can expect a little leniency on this team as well" ; "You should pitch in your numbers" | N/A. | none |
| 63 | Later they may make the process more transparent and publish scores. | "we'll try to make uh the process more transparent later on" | N/A. | none |
| 64 | They rerun the code and do not trust numbers; environment must be reproducible. | "we do not believe your numbers" | PARTLY: same as point 16; clean-machine run outstanding. | user |
| 65 | They will check the run logs you provide and rerun on the same benchmark. | "we will check the logs, whatever run logs you provide" | PARTLY: logs pushed; make sure README and deck numbers match the logs after tonight's possible final run. | lead, README polisher |
| 66 | Bixby is already integrated at Samsung and is not fully duplex; a Bixby-related use case would be wonderful. | "a use case which relates to Bixby, that is, you know, wonderful for us" | PARTLY: Bixby-style mock home scenario built (`EXT_PACK=home`, 28 offline tests); not a Bixby integration, not run live. | deck maker, video |
| 67 | The subjective part (use-case extension) is called a percentage; "40%" is inconsistent with 20%. | "come out with flying colors in these this 40%" | unclear in transcript. Every other statement says 60/20/20. Do not use 40%. | none |
| 68 | The benchmark backing comes first; use cases are the cherry on the cake. A bad integration does not help. | "you are backed by a solid system" | PARTLY: extension is offline-tested only. | video |
| 69 | A good demo needs the real full-duplex challenges. The sentence is cut off. | "you should also have—because these are real challenges" | unclear in transcript. | video |
| 70 | An average benchmark score with good use cases still gives a fair chance. | "it gives you a fair chance" | N/A: relevant to us (61 vs 62 judged); no action. | none |
| 71 | Questions about voice-to-voice vs cascaded; tool-call complexity hurts in live models. | "when the complexity of these tool calls will increase" | N/A: supports our Commit Harness framing; no claim needed. | none |
| 72 | No restriction on the approach: text model, voice-to-voice or rule-based. One sentence is garbled. | "You can use a text-based model. You can use a voice-to-voice model." and "Uh I not to use any kind of uh static rule-based system" | DONE: voice-to-voice (Gemini Live) plus a Commit Harness with a rule-based Reflex layer. The rule-based sentence is unclear in transcript; a later sentence says rule-based is allowed. | none |
| 73 | Two objectives: keep the conversation fluent and get the task done, even if it is delayed, neglected or cancelled. | "even if your task is delaying, or it is being neglected, or it is being canceled" | PARTLY: Commit Harness retraction and the extension's rollback exist, unit-tested and offline only; not scored on the benchmark. | none |
| 74 | Text responses are acceptable if voice is hard; state your assumptions. Do not quit; low scores still get a fair look. | "state those assumptions" | DONE: assumptions are stated (identifier canonicalization, judge stand-in). We output speech. | none |
| 75 | Input is a wave file; output is a wave or text file. | "accepting a wave file and it is giving out a wave file or a text file" | N/A. | none |
| 76 | Align performance with the benchmark; voice-to-voice tool calling can be a bottleneck. | "that becomes a bottleneck when you are, you know, scoring against these kind of benchmarks" | DONE: Commit Harness design addresses this. | none |
| 77 | Theme 5 is unchanged; only the evaluation changed. | "Theme 5 has not changed." | DONE. | none |
| 78 | The benchmark has 100 scenarios (flight booking, e-commerce, passports). "Passports" is as transcribed. | "100 scenarios relating to flight booking, e-commerce" | N/A. Our slices are finance, e-commerce, travel, housing per `SCORES.md`; "passports" is unclear in transcript. | none |
| 79 | Goal: do highly logical tasks while keeping the conversation fluent. | "maintaining the uh spirit of the conversation" | DONE (informational). | none |
| 80 | Extensions can go downstream or horizontally. | "downstream or horizontally as well" | N/A. | none |
| 81 | Deliverables: GitHub repo, one PPT slide (as transcribed), and the demo. | "a GitHub repo, one slide uh one PPT slide, and the demo" | PARTLY: repo done; deck and demo open. See point 32. | deck maker, video |
| 82 | No restriction on which AI you use, but fill in the circulated AI-usage declaration each time you use AI. | "whenever you are using an AI, please make sure that you are filling it out" | NOT DONE: form not yet filled; `AI_USAGE.md` is the source but is not the form. | user |
| 83 | Use of Gemini or Claude cloud services is fine; must give reproduction guidelines. | "cloud services that Gemini or Claude provide. That is also fine." | DONE. | none |
| 84 | First said a 48 GB GPU would be given; later corrected that no GPU, tools or API keys are provided and that they rerun in a 48 GB environment. | "we will be giving you a 1 48GB GPU" vs "we are not providing GPU" | DONE: we assume no GPU or keys from organizers. The transcript contradicts itself; the later statement is the clear one. Do not write that organizers supply a GPU. | none |
| 85 | Beware anyone posing as Samsung who asks for money. | "posing as a Samsung member" | N/A: warning only. | user |
| 86 | Contact email for questions is as transcribed. | "prism@campaign.com" | unclear in transcript (likely misheard). Use the address from the official guide, not this one. | user |
| 87 | An updated document with links will be circulated; further updates come via PRISM contacts. | "you will get it by your PRISM PC" | N/A. User: watch for the PDF and for a deadline update. | user |
| 88 | Attendees with a transcript (Otter) were asked to share it with the PRISM team. | "please share it with PRISM team as well" | N/A for us. | none |
| 89 | Questions can be raised in the chat or by mail; whatever silly they are. | "however silly you find it to be" | N/A. | none |
| 90 | The session was not recorded. | "we don't have the permission to record uh this thing" | N/A: our transcript and notes are the only record. | none |
| 91 | Someone asked whether replicating the paper's numbers is a hard requirement; answered "it's not about the benchmark" and that trust in the evaluation depends on documentation and provenance. | "it's not about the benchmark" | unclear in transcript (the sentence continues into the earlier own-kit history). We treat the benchmark as 60% per point 33. | none |
| 92 | The organizers will not supply API keys: everything is yours. This sits oddly with "we will not need the key" (point 45). | "We are not providing API keys or the GPUs; it will be all yours." | PARTLY: README lists required keys by name; ask the organizers if unsure how they will run Gemini. | user |
| 93 | A garbled fragment near the start of the paper description. | "Uh 4 5 it is." | unclear in transcript. | none |

Total: 93 points listed (unclear-in-transcript items are included, marked as such).

### Contradictions between the transcript and our README (for the README polisher)

1. **AI-usage form**: README says the form "is filled out accordingly"; the user has not yet filled it (point 82, `OBJECTIVES.md` E4). Change the README wording to say it will be submitted, or fix after the user submits.
2. **Judge**: README ("Judge caveat") and `OBJECTIVES.md` say "The organizers score with a GPT-4o judge". The transcript only says you can "put your own LLM and make LLM as a judge" and never names GPT-4o. Say "the benchmark's use-LLM judge", and keep "Gemini 2.5 Pro as a stand-in for GPT-4o" as our own description.
3. **Disqualification**: README ("How we tuned") and `AI_USAGE.md` mention a "disqualifying" or "disqualification" rule for tuning on the 100 recordings. The transcript contains no such rule. Keep our no-tuning discipline, but do not attribute it to the briefing.
4. **Conversation length**: organizer said "around two, two and a half minutes"; README says real inputs run 40 to 59 s. Do not repeat either as fact without checking the data lengths from the run logs.
5. **GPU**: README says "The organizers' 48 GB GPU". Organizers said they are not providing a GPU and will rerun in a 48 GB environment (point 84). Reword to "the 48 GB environment the organizers rerun in".
6. **Gemini key**: README's Reproduce section says the organizers' notes say "for Gemini we will not need the key". The transcript supports "we will not need the key" for Gemini and Gemma, but also "We are not providing API keys". Not a clean contradiction, but the README should not present it as confirmed for our setup.
7. **Deadline**: `TEAM_HANDOFF.md` says 23:59 IST on 30 Sep; the transcript says only "30th" (plus a 4 October possibility and an unclear "30th of November"). The time of day is our assumption.
8. **Slides**: `TEAM_HANDOFF.md` says max 8 slides; the transcript says "one PPT slide" (unclear). The 3 to 5 minute video length is also not in the transcript.
