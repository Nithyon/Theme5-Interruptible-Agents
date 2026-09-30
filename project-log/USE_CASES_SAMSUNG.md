# Use cases on Samsung products, and what our numbers support

Written 2026-09-30. Two kinds of numbers, kept apart: **Samsung's own figures** (with source and whether we checked the page) and **our measured results** (from `SCORES.md` and the run folders). We have no Samsung internal data and no integration with Bixby or SmartThings; the device tools in our extension are mocks.

## Samsung context

| Fact | Source | Checked |
|---|---|---|
| SmartThings has "more than 430 million users" (Dec 2025; up from 350 million in Sep 2024) | Cheolgi Kim, EVP Digital Appliances, CES 2026, reported by SamMobile | Yes (SamMobile page) |
| AI appliance models grew from about 300 (2024) to about 1,030 (Mar 2025) | Samsung Newsroom interview, 7 Nov 2025 | Yes |
| Bixby on appliances "enhanced with a large language model", for "conversation-like commands"; Voice ID tells speakers apart | same interview | Yes |
| New Bixby in One UI 8.5 described as a "conversational device agent" | Samsung announcement, 20 Feb 2026 (see `RESEARCH.md`) | Yes (earlier in this project) |
| SmartThings at 460 million users (May 2026) | search summary only | **No** |
| Galaxy AI mobile devices: 400 million (2025) to 800 million (2026) target | press reports of a T M Roh interview | **No** (source page blocked) |
| Vision AI Companion on TVs: upgraded Bixby with two-way dialogue | Samsung US Newsroom | **No** (page timed out) |

Unchecked rows must not go on a slide until someone opens the source.

## Use cases

Each row: what the user says, what goes wrong today in a plain voice model, which part of our system handles it, and the evidence we actually have.

| # | Product | What the user says | Failure without us | Our part | Evidence |
|---|---|---|---|---|---|
| 1 | Bespoke washer / SmartThings | "Start the washer on cotton… actually eco." | Two cycles started, or the wrong one | Recovery layer replaces a call that is still pending; if cotton already started, rollback: cancel, then start eco | Home pack, 28/28 offline tests (recovery layer) |
| 2 | Air conditioner | "Set the living room to 24… no, 22." | AC set to 24, then 22 (two commands, a beep each) | Extension agent: the pending 24 call is replaced (home pack test). Benchmark agent: Commit Harness holds until the turn settles | Home pack offline test; on benchmark-style tools, self-correction 0.529 vs 0.471 stock, and practice-set stale calls 4 of 17 (run E, partial) vs 5 of 17 (run D) |
| 3 | Family Hub fridge / shopping | "Order milk and eggs… and bread." | Second request replaces the first, or duplicates | Addition keeps both; identical call never runs twice | Gate tests (addition, dedupe); benchmark 3-request turns 0.375 vs 0.312 |
| 4 | TV (shared screen) | Someone says "mm-hmm" or "okay" while the assistant talks | Treated as a new command or a correction | Backchannel is not a turn | Offline tests only; not measured on the benchmark |
| 5 | Phone (Bixby) | "Book the 6 pm slot." then "never mind" | The booking goes through anyway | Retraction withdraws a held call and tells the model it did not run | Offline tests (5); only works while the call is still held |
| 6 | Any device, slow cloud service | "How much energy did I use today?" | Silence for several seconds | Progress line while waiting; must-speak watchdog | Offline tests; live run pending |
| 7 | Any device, service down | "Call the service centre, the washer is leaking." | Endless retry or silent failure | Two failures, then human handoff with a reference | Offline tests (car and home packs) |
| 8 | In-car (HARMAN) | "Book the Tesla charger… actually Ionity." | Two bookings | Rollback with compensation; never auto-retry a timed-out booking | Car pack, 35/35 offline tests |

**Which agent each row's evidence comes from.** Rows 3, 4 and 5 are Commit Harness behaviours, tested or measured on the benchmark agent with the benchmark's tools, not on device tools. Rows 1, 6, 7 and 8 are recovery-layer behaviours tested on the mock device tools. No single agent has both layers yet, so no row has been shown end to end on a device scenario with spoken input.

## What our numbers do and do not support

- Supported: on the 100-recording benchmark (Gemini 2.5 Pro as stand-in judge) our pipeline scored 61 and the stock agent 62 overall; ours was better on self-corrections (0.529 vs 0.471), 3-request turns (0.375 vs 0.312) and the housing domain (0.346 vs 0.192), and worse on shopping (0.586 vs 0.759) and pauses (0.50 vs 0.611).
- Supported: the first reply was slower with our pipeline (median 6.4 s vs 4.0 s). The lean setting in the run now in progress is meant to reduce this; no number yet.
- Not supported: any claim that we beat the stock agent overall, any claim about real Samsung devices, and any claim that the local fallback model works (measured 11/40 and 13/40 fully correct, not usable yet).
- Known limit: when the user changes their mind after the action has already run (10 benchmark cases, 1.4 to 10.7 s later), holding cannot help. That is what rollback in the extension is for (rows 1 and 8).

## Why the scale matters (one careful sentence for the deck)
With more than 430 million SmartThings users and about 1,030 AI appliance models, a voice command that acts on a withdrawn or half-finished request is not an edge case; the harness is a small, model-independent layer that any of these assistants could put between "the model proposed an action" and "the device did it".

Sources: https://www.sammobile.com/news/smartthings-now-boasts-430-million-users-across-the-globe/ · https://news.samsung.com/global/interview-why-samsung-①-tripling-the-number-of-ai-appliance-models-to-achieve-zero-housework-evp-jeong-seung-moon-on-samsungs-bespoke-ai-vision
