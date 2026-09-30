# Commit Harness: an interruptible voice agent (Theme 05, Full-Duplex-Bench v3)

A voice agent that acts only on what the user finally meant, and recovers when a tool is slow or fails.
Gemini 3.8 Live does the talking; a small layer in front of the tools, the **Commit Harness**, decides when an action may run.

![Commit Harness overview: the user says "Book me a flight, um, to New York, wait, Boston". Gemini proposes search_flights("New York"); the harness holds it, replaces it with search_flights("Boston") when the user corrects themselves, waits 0.9 s of quiet, and runs it once.](docs/figures/commit_harness_overview.svg)

*Layout after Figure 1 of the Full-Duplex-Bench v3 paper ([arXiv 2604.04847](https://arxiv.org/abs/2604.04847)); the middle layer is ours.
To change the figure, edit and run `python docs/figures/make_overview.py`.*

## Contents

- [Result](#result-100-real-recordings)
- [How it works](#how-it-works)
- [Smart Turn (Listener)](#smart-turn-listener)
- [Setup and reproduce](#setup-and-reproduce)
- [Troubleshooting](#troubleshooting)
- [Things you can run without keys](#things-you-can-run-without-keys)
- [Extension: in-car EV assistant](#extension-in-car-ev-assistant)
- [Where things are](#where-things-are)

## Result (100 real recordings)

| Agent | Judged pass | Strict pass | Typical reply delay |
|---|---|---|---|
| Stock agent (Gemini 3.8 Live, no harness) | 62 | 50 | 3.9 s |
| **Ours, submitted configuration** | **67** | **55** | 5.3 s |

- Judge: Gemini 2.5 Pro with the benchmark's own judge prompts, as a stand-in for GPT-4o. One run each.
- On 30 September we ran two configurations and submit the better one; both runs' logs are in the repo.
- No silent recordings in the submitted run. Run folder: `project-log/runs/2026-09-30_full_gate_gemini38_v2b/`.

## How it works

1. **Propose.** The voice model hears the user and proposes a tool call.
2. **Settle.** The harness (`fdb_agent/gate.py`) holds the call until the user's turn is over: 0.9 s of quiet,
   or 1.8 s if the last words were a hesitation ("um", "wait", "actually"), never more than 8 s.
   Two deciders judge whether the user has finished: **Reflex** (word patterns such as "um" or "no, sorry")
   and **Reasoner** (a small TypeSafe Jev classifier, optional; if it is slow or missing, Reflex decides alone).
3. **Commit.** The call runs once. A newer call to the same tool replaces a held one, "never mind" withdraws it,
   and an identical call is never run twice.

The prompt rules (the last value said wins, use values exactly as spoken, never say an action is done before it ran)
and an identifier rule ("B-O-B-1-2" becomes "BOB12") are part of the submitted configuration.
One-page architecture with both agents: [`project-log/ARCHITECTURE.md`](project-log/ARCHITECTURE.md).

## Smart Turn (Listener)

A third decider we built and tested, **off in the submitted configuration**. [Smart Turn v3.2](https://github.com/pipecat-ai/smart-turn)
(Pipecat, BSD-2-Clause, about 8M parameters, runs on CPU) listens to the audio itself (tone and pace, not the words)
and gives the probability that the user has finished. In the harness it sits next to Reflex and Reasoner
(`fdb_agent/smart_turn.py`) and is switched on with `GATE_SMART_TURN=1`.

| Test | Result | Evidence |
|---|---|---|
| Full benchmark run, Smart Turn on (30 September) | 50 strict / 64 judged, against 55 / 67 with it off. Faster replies (3.44 s median against 5.28 s), but one silent recording and about 7 s of stalled audio per recording while the model loads in each room. | `project-log/runs/2026-09-30_full_gate_gemini38_v3st/` |
| On its own, on Full-Duplex-Bench v1 conversation clips | Right on 74–84% of mid-sentence pauses, but recognised only 17–36% of finished turns (balanced accuracy 0.50–0.57, close to chance). About 126 ms per check. | `project-log/runs/2026-09-30_smart_turn_fdbv1/` |

So we submit with it off. To try it: `GATE_SMART_TURN=1 ./reproduce.sh`. Background: `project-log/RESEARCH_SMART_TURN.md`.
Recordings and other files for the runs are in the team's
[Google Drive folder](https://drive.google.com/drive/folders/1wFiVit_etrPbMFMhhFRsLO72S9UnPqnm?usp=sharing).

## Setup and reproduce

One script, `./reproduce.sh`, sets everything up, asks for your keys, runs our agent on the 100 benchmark
recordings and scores the result.

### What you need

| | |
|---|---|
| Operating system | **Linux**, or **Windows with WSL** (Ubuntu). macOS is untested: the script installs system tools with `apt` or `dnf` only. |
| Disk | About **10 GB** free (Python environment 7.8 GB, benchmark 1.1 GB, recordings download 0.7 GB). |
| Network | Outbound internet to LiveKit Cloud and Google Gemini. |
| GPU | Not needed by our code. The benchmark's own speech recogniser uses one if present. |
| Time | About 10 minutes of setup, then about 2 hours for the run (the recordings play in real time). |
| Accounts | A LiveKit Cloud project and a Gemini API key. Details in step 2. |

### Step 1: get a Linux shell (Windows only)

In PowerShell **as administrator**:

```powershell
wsl --install -d Ubuntu
```

Restart when asked, open **Ubuntu** from the Start menu and create a user name and password. Everything below runs
in that Ubuntu window. Cloning into your Linux home folder (`~`) is faster than working under `/mnt/c/...`.

### Step 2: get the keys

| Key | Required | Where to get it |
|---|---|---|
| `LIVEKIT_URL` | yes | [cloud.livekit.io](https://cloud.livekit.io): create a project; the URL looks like `wss://<project>.livekit.cloud`. |
| `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | yes | Same project: **Settings → API keys → Create key**. |
| `GOOGLE_API_KEY` | yes | [Google AI Studio → Get API key](https://aistudio.google.com/apikey). |
| `TYPESAFE_API_KEY` | no | Turns on the Reasoner. Without it the word patterns (Reflex) decide alone. |
| `OPENAI_API_KEY` | no | Turns on the organizers' GPT-4o judge. Without it scoring is exact-match only (the "strict" number). |

Use a LiveKit project that nothing else is using while you run: two agents on one project take each other's rooms and ruin both runs.

### Step 3: clone and set up

```bash
git clone https://github.com/Nithyon/Theme5-Interruptible-Agents.git
cd Theme5-Interruptible-Agents
SETUP_ONLY=1 ./reproduce.sh
```

`SETUP_ONLY=1` does everything except the 2-hour run:

1. Installs `ffmpeg`, `git` and `curl` if missing (asks for your Linux password once, for `sudo apt-get`).
2. Installs [`uv`](https://docs.astral.sh/uv/), clones Full-Duplex-Bench at the pinned commit into
   `~/theme5/Full-Duplex-Bench`, and builds the Python environment in `~/theme5/fdb-env` from
   `project-log/runs/env-freeze.txt`.
3. Downloads and unpacks the 100 recordings (736 MB) and checks all 100 are there.
4. **Asks for the keys.** Paste each one and press Enter. Secrets are not shown as you type. After each one
   it prints `<NAME> saved (<n> characters, value not shown)`, so you can see a paste was not cut off.
   Then it offers the two optional keys (Enter to skip).
5. Checks the required keys are present (by name only) and tells you which mode you will run in:
   `Jev disabled: gate uses rules only` or `rules + Jev combined`, and exact-match or GPT-4o scoring.

The keys are saved to `~/theme5/Full-Duplex-Bench/v3/.env.local` (readable by you only). They are never printed,
logged, or written into this repository.

### Step 4: run and score

```bash
./reproduce.sh
```

It skips the setup already done and does not ask for the keys again. Then it starts our agent with the submitted
settings, plays the 100 recordings to it, stops the agent and scores the results. The run is quiet for about
2 hours (output goes to log files). Keep the terminal open, keep the computer awake, and **keep the machine
otherwise idle**: heavy jobs running at the same time can make the agent miss whole recordings.

To run the stock agent for comparison:

```bash
./reproduce.sh fdb_agent/baseline_agent.py gemini3_8
```

### Step 5: read the result

Results land in `project-log/runs/<date>_repro_gate_gemini38_v2/`:

| File | What |
|---|---|
| `score.txt` | The headline: passed out of 100, pass rate, and breakdowns by difficulty, number of tools, disfluency and domain. |
| `run.txt` | Start and end time and the exact settings used. |
| `agent.log`, `inference.log` | The agent's log and the benchmark runner's log. Look here if something went wrong. |
| `agent_tool_calls.log` | Every tool call that ran (what the benchmark scores). |
| `gate_events.log`, `gate_stats.log` | The harness's decisions: every hold, replace, withdraw. |
| `gate_gemini38_v2_pass_rate_report.json` | The full scoring report. |

Compare with our submitted run: **55 strict** (exact-match) and **67 judged**. Without an OpenAI key you only get
the strict score, so compare against 55. The voice model is not deterministic, so expect a few recordings either
way. Our run's logs are in `project-log/runs/2026-09-30_full_gate_gemini38_v2b/`.

### Options

| Setting | Effect |
|---|---|
| `SETUP_ONLY=1` | Setup and key check only, no run. |
| `NO_PROMPT=1` | Never ask for keys (fails if `.env.local` is missing or incomplete). |
| `FDB_DIR=...`, `ENV_DIR=...` | Install the benchmark and the Python environment somewhere other than `~/theme5`. |
| `GATE_SMART_TURN=1` | Also use the Listener (Smart Turn), which was off in the submitted run. |
| `GATE_RETRACT=0 GATE_ID_NORMALIZE=0 GATE_BACKCHANNEL=0 GATE_LEAN=0` | The 29 September configuration instead of the submitted one. |

The install steps were checked in a clean folder on 30 September, up to the key step; the full 2-hour run has not
yet been repeated from a clean folder.

## Troubleshooting

| Problem | What to do |
|---|---|
| `... is required; run ./reproduce.sh again when you have it` | You pressed Enter on a required key. Run the script again; it asks only for what is missing. |
| `... contains a space, quote, $ or backslash` | Add that key by hand: `nano ~/theme5/Full-Duplex-Bench/v3/.env.local`, one `NAME=value` per line. |
| A key was wrong | Edit `~/theme5/Full-Duplex-Bench/v3/.env.local`, or delete its line and run the script again. (Optional keys are offered only the first time; add them by hand later.) |
| `neither apt-get nor dnf found` | Install `ffmpeg`, `git` and `curl` yourself, then run the script again. |
| `wsl: Failed to translate '...'` | A harmless WSL warning about a Windows `PATH` entry. Ignore it. |
| Some recordings have no agent speech | The machine was busy, or another agent was using the same LiveKit project. Stop other jobs and run again. |
| The run stopped halfway | Run `./reproduce.sh` again; it replays all 100 recordings. |

## Things you can run without keys

```bash
python extension/test_recovery.py && python extension/test_recovery_home.py   # recovery layer, 35 + 28 checks
python extension/fallback_suite.py --model gemma4:26b-a4b-it-qat --runs 1      # local fallback; needs Ollama
```

The harness tests need the benchmark's tool definitions, so run them from the benchmark folder after setup:

```bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
python <path-to-this-repo>/fdb_agent/test_gate.py
```

## Extension: in-car EV assistant

A recovery layer (`extension/recovery.py`) for slow and failing tools, run end to end on recorded audio:
a corrected reroute runs once, a failing charger lookup is retried quietly, a repeated booking is not made
twice, changing the time cancels the first booking before making the new one, and two failed roadside
requests end in a hand-off to a human. Mock tools, synthetic request voice, one run.
Evidence: `project-log/runs/2026-09-30_ext_car_e2e/` (conversation audio, recovery log).

On real speech: 11 recordings from the SLURP test set (light-control requests, headset microphone, picked by a fixed
rule, not by ear) were played to the home assistant with the lights tool made to fail on its first attempt. 10 of 11
requests ended in a lights action and all 8 injected failures were recovered by a retry. One request asked for a light
colour and was declined (no such tool); one asked for a time and was switched off at once, with the agent saying it
cannot schedule. One run. Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/`.

To talk to it yourself (uses the same `.env.local`), start it and connect from the
[LiveKit Agents Playground](https://agents-playground.livekit.io) with the same LiveKit project:

```bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
LK_PROVIDER=ext_gemini38 python <path-to-this-repo>/extension/ext_agent.py dev                  # in-car pack
EXT_PACK=home LK_PROVIDER=ext_gemini38 python <path-to-this-repo>/extension/ext_agent.py dev    # home pack
```

More: [`extension/README.md`](extension/README.md) and [`extension/DESIGN.md`](extension/DESIGN.md).

## Where things are

| Path | What |
|---|---|
| `reproduce.sh` | One-command setup, run and scoring |
| `fdb_agent/` | The benchmark agent (`gate_agent.py`), the harness (`gate.py`), the stock agent (`baseline_agent.py`) and tests |
| `extension/` | Recovery layer, in-car and home scenarios, their tests |
| `docs/figures/` | The overview figure and the script that draws it |
| `project-log/ARCHITECTURE.md` | One-page architecture of both agents |
| `project-log/runs/` | Logs, decision logs, per-recording results and score reports for every run |
| `project-log/SCORES.md` | Every score and where it came from |
| `README_FULL.md` | Full write-up: design, all results, limitations, related work |
| `project-log/AI_USAGE.md` | AI assistants wrote most of the code and documents; the team made the decisions |
