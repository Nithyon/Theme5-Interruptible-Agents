# Presentation script (8 slides, about 4 minutes of talking)

Deck: https://claude.ai/artifact/23ov3X1v58BEcUFnk44Psu (private until shared from its Share menu; it can be downloaded as PowerPoint or PDF). The same narration is in each slide's speaker notes. Numbers are from `SCORES.md`; items in [brackets] must be filled before presenting.

## The story in five sentences
1. People change their mind while they talk; voice agents act on the first thing they hear.
2. We put a small layer, the Commit Harness, between the voice model and its tools: propose, settle, commit.
3. On 100 real recordings our agent did better on some slices and worse on others, and the decision log shows the harness itself changed what ran in only 2 of 100 recordings; we show all of it.
4. The failures told us what is missing: undo for late changes of mind, which our extension builds as a recovery layer.
5. Everything is logged and reproducible with one command, and we say what is not done.

## What to say, slide by slide

**1. Cover (20 s).** Hello. We are [team name]. Our theme is interruptible real-time agents. People change their mind while they talk: "Boston... no, sorry, New York". Most voice agents act on the first thing they hear. We built a small layer called the Commit Harness that makes the agent wait until the request has settled, then act once: propose, settle, commit. We also built a recovery layer for slow and failing tools. We will show what worked, what did not, and the evidence for both.

**2. The problem (30 s).** "Book a flight to Boston... no, sorry, New York." A voice model hears the pause after Boston and acts. Then it hears the correction and acts again: two bookings, one wrong. The benchmark we are graded on, Full-Duplex-Bench v3, uses 100 real human recordings full of pauses, fillers and corrections, and it counts every action the agent actually ran. One early action fails the whole recording. The best published system passes 60 percent, and the paper names self-correction as one of the most consistent failures.

**3. One model talks, a harness decides (35 s).** Our design has two minds. Gemini Live is the talker: it listens and speaks, and when it wants to do something it proposes an action. The Commit Harness is the thinker: it holds that action until your turn has really settled, and only then lets it run, once. Inside it there are three deciders, cheapest first. Reflex looks at words like "um" or "no, sorry" and costs nothing. The Reasoner, TypeSafe Jev, judges the meaning, and if it is slow the Reflex decides alone. The Listener, Smart Turn, hears the tone of voice; we built it and measured it, and it is not reliable enough yet.

**4. What the harness does (30 s).** Four things. Hold: wait for a short quiet, a little longer if you sounded hesitant. Replace: if you correct yourself, the first action is dropped before it runs. Withdraw: if you say never mind, the action is cancelled and the model is told it did not happen. Once: the same request never runs twice, but a second, different request is kept. Every decision is logged, so anyone re-running our code can see each action proposed, held, replaced or executed.

**5. Results (40 s).** The stock agent, Gemini 3.8 Live with no harness, passes 62 of 100 with the judge and 50 under strict matching. Our pipeline on 29 September passed 61, one behind. With the settings we submit it passes 67 judged and 55 strict, five ahead, and no recording went silent. The gain is in shopping, in turns with two or three requests, and a little in housing and travel. We are one recording worse on self-corrections, level on finance, and still slower to reply: 5.3 seconds against 3.9. Same judge for every agent, Gemini 2.5 Pro standing in for GPT-4o, one run each. On the 30th we ran two settings on the benchmark and submit the better one; both logs are in the repository.

**6. What the failures taught us (35 s).** In ten recordings the user changed their mind seconds after the action had already run. No waiting rule fixes that; the answer is undo. In three of our hundred recordings the agent heard nothing at all; we traced it to load on the machine and wrote a check that finds such recordings. Most important: we counted how often the harness changed what ran. In the 29 September run it replaced one action and blocked one duplicate, two recordings out of a hundred, because the voice model proposes an action only after it believes you have finished. The hold costs about nine tenths of a second each time. So our gains cannot come from replacing actions; what else differs is our prompt rules and the ID rule, which we have not tested separately.

**7. Extension (40 s).** The benchmark's tools answer instantly and never fail. Real tools do not. Our extension is a recovery layer, and the headline scenario is an in-car assistant for an electric car. We ran it end to end on audio: a recorded clip of a driver's requests is played to the agent through LiveKit, the same way the benchmark plays its recordings, and we saved what the agent said and the recovery log. The driver corrects the destination, and one reroute runs. The charger lookup fails twice and is retried quietly. A repeated booking is not made twice. Changing the time cancels the first booking before making the new one. When roadside assistance is unreachable on two requests, the agent hands off to a human with a reference number, and it does not claim a transfer before that. The same layer also runs a home assistant scenario. Limits: mock tools, a synthetic request voice, one run, and no spoken "still checking" yet.

**8. Reproduce and next (30 s).** One command, pinned versions, Gemini only. Every run's logs are in the repository, down to each recording. Not done: the harness and the recovery layer are in two separate agents; no GPT-4o judge; the script has not run on a clean machine; the local Gemma fallback is about thirty percent correct, so not usable. Next: undo in the main agent, real plugins (they exist for every domain in the benchmark), and a stronger model only on the hard turns. Thank you.

## Video running order (decided 2026-09-30: slides with voiceover, no live demo)
1. Slides 1 to 8 in order, reading the narration above (about 4 minutes).
2. Optional, about 40 seconds between slides 7 and 8, to show something running: the recovery tests (`python extension/test_recovery_home.py`, `python extension/test_recovery.py`) and one decision log from a real benchmark recording (`project-log/runs/<run>/gate_events.log`). Say plainly that these are automated tests and saved logs, not a live conversation.
3. `DEMO_SCRIPT_5MIN.md` holds the live-demo version in case it is wanted later.

## To fill before presenting
- Slide 1: team name and members.
- Slide 6 footer and slide 3 Listener status if the Smart Turn run is the one submitted.
