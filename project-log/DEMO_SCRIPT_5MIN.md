# Demo video script (5 minutes)

Written 2026-09-30. Neither demo agent has held a spoken conversation yet, so do one rehearsal take first. Items in [brackets] are filled in on the day. Record the screen with sound (Windows: Win + Alt + R). Say nothing that the screen does not show.

Open before recording: the deck (slides 1, 2, 5, 6, 8) and one Ubuntu terminal.

| Time | On screen | What you do | What you say |
|---|---|---|---|
| 0:00–0:20 | Slide 1 | | "We are [team name]. Theme 5, interruptible real-time agents. People change their mind while they talk. We built a layer that decides when it is safe to act, and a recovery layer for when tools fail. This video shows both running, and then our numbers." |
| 0:20–0:40 | Slide 2 | | "The problem in one sentence: 'Book a flight to Boston, no, sorry, New York.' A voice agent that acts at the first pause books the wrong flight. Our benchmark, Full-Duplex-Bench version 3, plays 100 real recordings like that and counts every action the agent runs." |
| 0:40–0:50 | Terminal | Run `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_gate.sh` | "This is the agent we submit: Gemini Live with our Commit Harness in front of the benchmark's tools. These lines are our own practice lines, not benchmark recordings." |
| 0:50–1:10 | Terminal, agent listening | Speak to the agent | **"Track order BOB12."** (short pause) **"Actually, sorry, it's BOB21."** Wait for its answer. |
| 1:10–1:25 | | Speak | **"Track order A1, and also order B2."** Wait for its answer. |
| 1:25–1:40 | | Speak | **"Add two of product K2 to my cart... never mind, don't add it."** Wait for its answer. |
| 1:40–2:05 | Terminal | Press Ctrl+C, then run `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_show_log.sh` | Read the log aloud, line by line: "Here is every decision: proposed, held, and what actually ran." Then say whichever is true: "The first order was replaced before it ran" or "the model waited for me to finish, so there was nothing to replace". Then: "In our 100-recording run the harness changed what ran in only 2 recordings, for that same reason. We report that." |
| 2:05–2:15 | Terminal | Run `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_car.sh home` | "Second part: our extension. Real tools are slow and fail. This is a Bixby-style home assistant with mock devices and our recovery layer." |
| 2:15–2:30 | Agent listening | Speak | **"Set the living room AC to 24... no, 22."** |
| 2:30–2:50 | | Speak | **"How much energy have I used today?"** (it should say it is still checking, then answer) |
| 2:50–3:05 | | Speak | **"Find my phone."** Then say to camera: "That lookup failed twice and was retried. You only heard the answer." |
| 3:05–3:25 | | Speak | **"Start the washer on cotton."** Then: **"Start it again."** (same job number, no second start) |
| 3:25–3:40 | | Speak | **"Actually, make it eco."** (it should cancel cotton, start eco, and say both) |
| 3:40–3:55 | | Speak | **"The washer is leaking, call the service centre."** (two failed tries, then a hand-off with a reference) |
| 3:55–4:10 | Terminal | Press Ctrl+C, then run `bash /mnt/d/Theme5-Interruptible-Agents/project-log/scripts/demo_show_recovery.sh` | "The recovery log shows the retries, the cancel before the new start, and the hand-off. The devices are mocks. This is not a Bixby or SmartThings integration." |
| 4:10–4:35 | Slide 5 | | "Results on 100 recordings. The stock agent passes 62 with the judge. Our pipeline on the 29th passed 61. With the settings we submit it passes 67 judged and 55 strict, with no silent recordings. Same judge for both, one run each." |
| 4:35–4:50 | Slide 6 | | "What we learned: ten failures were changes of mind after the action had already run, which only undo can fix. Three recordings were silent because of machine load. And the harness rarely needed to step in, so our gain comes from the rules around it." |
| 4:50–5:00 | Slide 8 | | "One command reproduces the run, and every log is in the repository. Next: undo in the main agent, a check of each value before it runs, and real plugins. Thank you." |

## If something goes wrong on camera
- The agent does not answer within about five seconds: repeat the line once. If it still does not, stop, and say "this take failed"; do not edit around it.
- The correction line ends with both orders tracked: that is a late change of mind. Say so: "it acted before I corrected myself, which is exactly the failure that needs undo", and go on.
- The washer change does not cancel the first job: say the exact words "book eco instead of cotton" on the next take.
- A demo cannot be made to work at all: show `project-log/runs/` logs of the same behaviour and the offline tests running (`python extension/test_recovery_home.py`), and say clearly that it is a recorded run and offline tests, not a live take.

## Before recording
1. Both benchmark runs must have finished (no agents may be started while they run).
2. Windows microphone allowed and not muted; speakers on.
3. One rehearsal of each demo; note what the terminal shows while you talk.
4. Fill the three numbers for 4:10.
