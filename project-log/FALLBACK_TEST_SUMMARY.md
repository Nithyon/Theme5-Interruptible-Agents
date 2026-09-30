# Local fallback: test summary (Aryan's laptop, 30 September 2026)

**Conclusion.** Run offline, Gemma 4 26B chooses the right action reliably, understands corrections and
cancellations, and never acted when no tool fitted. The 3 GB Gemma 4 e4b is three times faster but refuses most
real light requests and carries out cancelled actions, so it is not safe as the fallback. The fallback is not yet wired
into the voice agent and is not part of the benchmark score.

Every number below was recounted from the per-run result files (`project-log/scripts/suite_check.py`,
`interrupt_check.sh`).

## Who did what

Aryan, working with Claude Code on his laptop: found why Gemma 4 returned no tool call (its thinking mode used up
the whole reply limit) and fixed it (`"think": False` in `extension/local_fallback.py`); re-measured three models;
ran the test suite on three command sets; reviewed every miss. The suite and the SLURP and interruption sets were
built by the lead session.

## Device

Intel Core Ultra 7 258V laptop (8 cores), 32 GB RAM, no discrete or NVIDIA GPU (the integrated Arc graphics shares
system RAM), Linux (CachyOS), Ollama 0.32.14. Measured speed: 16.4 to 16.9 tokens/s for the 26B, 27.5 to 27.8 for
e4b. The laptop was otherwise idle during the runs.

## Command sets (all typed text, no audio)

| Set | Size | Source | What it checks |
|---|---|---|---|
| Our commands | 40 | Written by us | Car and home commands; 4 where no tool fits |
| SLURP | 111 | Real user requests, SLURP test set (Bastianelli et al., EMNLP 2020) | 51 light requests (right tool, right on/off); 60 requests none of our tools can serve |
| Interruptions | 37 | Written by us | Corrections, changed actions, "never mind", hesitations, "no rush", double corrections; 8 where the right answer is to do nothing |

## Results

| | Gemma 4 26B (15.9 GB) | Gemma 4 e4b (3.1 GB) |
|---|---|---|
| Runs | 1 per set | 3 per set, identical answers each time |
| Our commands: right tool and values | 34/36 | 34/36 |
| Our commands: correctly did nothing | 4/4 | 4/4 |
| SLURP light requests right | **45/51** | **18/51** (declined 31) |
| SLURP "no tool fits": correctly did nothing | 60/60 | 60/60 |
| Interruptions: right tool and values | 28/29 (right tool 29/29; the miss is wording) | 29/29 |
| Interruptions: cancelled, correctly did nothing | **8/8** | **6/8** |
| Median time per command | 5.6 to 6.0 s | 1.7 to 2.3 s |

Interruptions by kind, 26B: corrected value 6/6, corrected place 4/4, changed action 4/4, cancellation 6/6,
hesitation 4/5, not a correction 5/5, double correction 3/3, correction then cancel 2/2, cancel then new request 2/2.

## What went wrong

- **e4b carried out 2 cancelled actions, in all 3 runs:** "Turn off the living room lights, wait, no, leave them as
  they are" turned the lights off; "Navigate to the mall, no, the office, oh forget it, stay on this route"
  rerouted to the office. Neither tool needs confirmation in our fallback, so both would really run.
- **e4b declined 31 SLURP light requests.** 5 are the same unservable or vague requests the 26B also declined; the
  other 26 are plain ones the 26B handled, such as "turn the lights off". Likely cause, not tested: our lights
  tool requires a room and most requests name none.
- **26B's misses:** the SLURP set has 6 (a scheduled time and a colour it cannot do, two vague wordings, one screen
  request SLURP labels as lights, and one real error: "no lights in the kitchen" turned the lights on). Our commands
  have 2, and the interruption set 1, all free-text wording ("central station" against the expected "the central
  station"). We report the measured score, not an adjusted one.

## What this shows and does not show

- Only the real SLURP requests told the two models apart; on our own commands they tie.
- It does not show behaviour on speech, pauses or someone talking over the agent: these are typed sentences.
- The 26B ran once per set, so its run-to-run stability is not measured.
- It was tested on a 32 GB laptop; the 26B takes about 16 GB when loaded and about 6 s per command: a car
  computer or PC, not a phone. Smaller machines were not tested.

Result folders: `project-log/runs/2026-09-30_fallback_suite_gemma4_26b-a4b-it-qat/`, `..._interrupt/`,
`2026-09-30_fallback_suite_gemma4_e4b-it-qat/`, `..._interrupt/`, and the earlier 40-command comparison
`2026-09-30_local_fallback_eval_*_laptop*.json`.
