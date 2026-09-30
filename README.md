# Commit Harness: an interruptible voice agent (Theme 05, Full-Duplex-Bench v3)

A voice agent that acts only on what the user finally meant, and recovers when a tool is slow or fails.
Gemini 3.8 Live does the talking; a small layer in front of the tools decides when an action may run.

## Result (100 real recordings)

| Agent | Judged pass | Strict pass | Typical reply delay |
|---|---|---|---|
| Stock agent (Gemini 3.8 Live, no harness) | 62 | 50 | 3.9 s |
| **Ours, submitted configuration** | **67** | **55** | 5.3 s |

- Judge: Gemini 2.5 Pro with the benchmark's own judge prompts, as a stand-in for GPT-4o. One run each.
- On 30 September we ran two configurations and submit the better one; both runs' logs are in the repo.
- No silent recordings in the submitted run. Run folder: `project-log/runs/2026-09-30_full_gate_gemini38_v2b/`.

## How it works

1. **Propose.** The voice model proposes a tool call.
2. **Settle.** The harness (`fdb_agent/gate.py`) holds it until the user's turn is over. Two deciders:
   word patterns ("um", "no, sorry") and a small classifier (TypeSafe Jev) that falls back to the patterns.
3. **Commit.** The call runs once. A correction replaces a held call, "never mind" withdraws it, a repeat is not re-run.

## What we found (and report)

- The harness changed what ran in only 2 of 100 recordings: the model proposes a call only after it thinks
  the user has finished. The gain over the stock agent comes from our prompt rules and an identifier
  formatting rule, which we did not test separately.
- We are one recording worse than the stock agent on self-corrections (7 of 17 against 8) and slower to reply.
- Ten failures were changes of mind after the action had already run. Only undo can fix those.

## Extension: in-car EV assistant

A recovery layer (`extension/recovery.py`) for slow and failing tools, run end to end on recorded audio:
a corrected reroute runs once, a failing charger lookup is retried quietly, a repeated booking is not made
twice, changing the time cancels the first booking before making the new one, and two failed roadside
requests end in a hand-off to a human. Mock tools, synthetic request voice, one run.

On real speech: 11 recordings from the SLURP test set (light-control requests, headset microphone, picked by a fixed rule, not by ear) were played to the home assistant with the lights tool made to fail on its first attempt. 10 of 11 requests ended in a lights action and all 8 injected failures were recovered by a retry. One request asked for a light colour and was declined (no such tool); one asked for a time and was switched off at once, with the agent saying it cannot schedule. One run. Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/`.
Evidence: `project-log/runs/2026-09-30_ext_car_e2e/` (conversation audio, recovery log).

## Reproduce

On Linux (or WSL on Windows), with `git` installed:

```bash
git clone https://github.com/Nithyon/Theme5-Interruptible-Agents.git
cd Theme5-Interruptible-Agents
./reproduce.sh
```

What happens:

1. **Setup (about 10 minutes).** Installs `uv`, fetches the benchmark at a pinned commit, builds the Python
   environment from `project-log/runs/env-freeze.txt`, downloads the 100 recordings (736 MB).
2. **Keys.** The script asks for any missing key in the terminal and saves it to `.env.local` in the
   benchmark folder. Secrets are not shown as you type and are never printed or logged; no keys are in this repo.
   - Required: `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` (a LiveKit Cloud project), `GOOGLE_API_KEY` (Gemini).
   - Optional, Enter to skip: `TYPESAFE_API_KEY` (without it the word patterns decide alone),
     `OPENAI_API_KEY` (GPT-4o judge; without it scoring is exact-match only).
3. **Run and score (about 2 hours).** Starts our agent with the submitted settings, plays the 100 recordings,
   scores them. Results land in `project-log/runs/<date>_repro_gate_gemini38_v2/` (`score.txt`, logs).

Useful variants:

```bash
SETUP_ONLY=1 ./reproduce.sh                              # setup and key check only, no run
./reproduce.sh fdb_agent/baseline_agent.py gemini3_8    # the stock agent, for comparison
```

Run one agent at a time per LiveKit project. No GPU is needed by our code. The install steps (tools,
benchmark, Python environment) were checked in a clean folder on our machine; the script has not been run end
to end on a second machine.

Other things to run (no keys needed):

```bash
python extension/test_recovery.py && python extension/test_recovery_home.py   # recovery layer, 35 + 28 checks
python fdb_agent/test_gate.py                                                  # the harness
python extension/fallback_suite.py --model gemma4:26b-a4b-it-qat --runs 1      # local fallback; needs Ollama
```

## Where things are

| Path | What |
|---|---|
| `fdb_agent/` | The benchmark agent, the harness and its tests |
| `extension/` | Recovery layer, in-car and home scenarios, their tests |
| `project-log/runs/` | Logs, decision logs, per-recording results and score reports for every run |
| `project-log/SCORES.md` | Every score and where it came from |
| `README_FULL.md` | Full write-up: design, all results, limitations, related work |
| `project-log/AI_USAGE.md` | AI assistants wrote most of the code and documents; the team made the decisions |
