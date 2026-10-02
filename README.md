# Commit Harness: an interruptible voice agent (Theme 05, Full-Duplex-Bench v3)

This is a voice agent that acts only on what the user finally meant. It also recovers when a tool is slow or fails.
Gemini 3.8 Live listens and speaks. A small layer in front of the tools, the Commit Harness, decides when an action can run.

![Commit Harness overview: the user says "Book me a flight, um, to New York, wait, Boston". Gemini proposes search_flights("New York"). The harness holds it, replaces it with search_flights("Boston") when the user corrects themselves, waits for 0.9 s of quiet, and runs it once.](docs/figures/commit_harness_overview.svg)

*The layout follows Figure 1 of the Full-Duplex-Bench v3 paper ([arXiv 2604.04847](https://arxiv.org/abs/2604.04847)). The middle layer is ours.
To change the figure, edit and run `python docs/figures/make_overview.py`.*

Demo video: [watch on YouTube](https://youtu.be/zBp5oEh5yhY)

Presentation: [view the slides online](https://nithyon.github.io/commit-harness/slides.html) (no download) ·
[slides as PDF](presentation/TEAM%20REIGN%20-%20SAMSUNG%20PRISM%20HACKATHON.pdf) (opens in the browser) ·
[PowerPoint file](presentation/TEAM%20REIGN%20-%20SAMSUNG%20PRISM%20HACKATHON.pptx) (download)

Website: [nithyon.github.io/commit-harness](https://nithyon.github.io/commit-harness/)

Team Reign, SRM Institute of Science and Technology: Pokala Sai Nithin, Aryan Garg, Lohitashwa and V Preetha.
Theme 05, Interruptible Agents, Samsung PRISM.

## Contents

- [Words used in this README](#words-used-in-this-readme)
- [Result](#result-100-real-recordings)
- [How it works](#how-it-works)
- [Smart Turn (Listener)](#smart-turn-listener)
- [Datasets](#datasets)
- [Setup and reproduce](#setup-and-reproduce)
- [Troubleshooting](#troubleshooting)
- [Things you can run without keys](#things-you-can-run-without-keys)
- [Extension: in-car EV assistant](#extension-in-car-ev-assistant)
  - [Reproduce the extension](#reproduce-the-extension)
- [Where things are](#where-things-are)

## Words used in this README

| Word | Meaning |
|---|---|
| Tool call | An action that the agent asks a program to do, for example `track_order("BOB12")`. |
| Full-Duplex-Bench v3 | The benchmark that scores this theme. It plays 100 recordings of real people who ask for actions out loud, and it counts every tool call that the agent runs. |
| Strict score | The number of recordings in which every tool call was exactly right. |
| Judged score | The number of recordings that a language model (the judge) accepts as right in meaning. For example, the judge accepts "BOB 12" for "BOB12". |
| Stock agent | The benchmark's own agent with Gemini 3.8 Live and no changes from us. We compare our agent with it. |
| LiveKit | The service that carries the audio between a recording and the agent in real time. |
| Commit Harness | Our layer between the voice model and the tools. It holds, replaces, cancels and runs tool calls. |
| Reflex, Reasoner, Listener | The three parts that decide if the user finished speaking: word patterns, a small classifier (TypeSafe Jev), and a sound-based model (Smart Turn). |
| Recovery layer | Our second layer, for the extension. It handles slow and failing tools. |
| Mock tool | A tool that gives made-up answers. No real car, shop or bank is involved. |
| SLURP | A public dataset of real people's spoken requests to a home assistant (Bastianelli et al., EMNLP 2020). |
| Ollama | A program that runs language models on your own computer, without the internet. |
| Gemma 4 | An open language model from Google. We use it as the offline fallback. |
| Offline fallback | A local model that chooses the action when the cloud model cannot be reached. |
| MCP | Model Context Protocol, a standard way to connect a model to outside tools ("plugins"). |

## Result (100 real recordings)

| Agent | Judged pass | Strict pass | Typical reply delay |
|---|---|---|---|
| Stock agent (Gemini 3.8 Live, no harness) | 62 | 50 | 3.9 s |
| Ours, submitted configuration | **67** | **55** | 5.3 s |

- The judge is Gemini 2.5 Pro, not GPT-4o. We did not use OpenAI anywhere. The benchmark's scorer expects a
  GPT-4o judge. We had no GPT-4o access, so `project-log/scripts/judge_vertex.py` sends the benchmark's own judge
  prompts, unchanged, to Gemini 2.5 Pro on Google Cloud (Vertex AI). The stock agent and our agent had the same judge.
  `./reproduce.sh` does not run this script. It uses GPT-4o if you give it an `OPENAI_API_KEY`. Without that key,
  it gives only the strict score (see [Step 5](#step-5-read-the-result)). Each agent ran once.
- On 30 September we ran two configurations and submitted the better one. The logs of both runs are in this repository.
- The submitted run had no silent recordings (recordings that the agent did not hear).
  Run folder: `project-log/runs/2026-09-30_full_gate_gemini38_v2b/`.

## How it works

1. Propose. The voice model hears the user and proposes a tool call.
2. Settle. The harness (`fdb_agent/gate.py`) holds the call until the user's turn ends. A turn ends after 0.9 s
   of quiet, or after 1.8 s if the last words were a hesitation ("um", "wait", "actually"). The wait is never more
   than 8 s. Two parts decide if the user finished. Reflex reads word patterns such as "um" or "no, sorry".
   Reasoner is a small classifier, TypeSafe Jev, and it is optional. If Reasoner is slow or missing, Reflex decides alone.
3. Commit. The call runs once. A newer call to the same tool replaces a held call. "Never mind" withdraws the
   held call. An identical call never runs twice.

Two more parts are in the submitted configuration:

- Prompt rules: the last value that the user says wins, values are used exactly as spoken, and the agent never says
  that an action is done before it ran.
- An identifier rule: "B-O-B-1-2" becomes "BOB12" before the tool runs.

The one-page architecture of both agents is in [`project-log/ARCHITECTURE.md`](project-log/ARCHITECTURE.md).

## Smart Turn (Listener)

Smart Turn is a third decider that we built and tested. It is off in the submitted configuration.
[Smart Turn v3.2](https://github.com/pipecat-ai/smart-turn) (Pipecat, BSD-2-Clause license, about 8M parameters,
runs on a CPU) listens to the audio itself, the tone and the pace, not the words. It gives the probability that the
user finished. In the harness it works next to Reflex and Reasoner (`fdb_agent/smart_turn.py`).
`GATE_SMART_TURN=1` switches it on.

| Test | Result | Evidence |
|---|---|---|
| Full benchmark run with Smart Turn on (30 September) | 50 strict and 64 judged, against 55 and 67 with it off. The replies were faster (3.44 s median against 5.28 s). But one recording was silent, and the audio stalled for about 7 s in each recording while the model loaded. | `project-log/runs/2026-09-30_full_gate_gemini38_v3st/` |
| Smart Turn alone, on Full-Duplex-Bench v1 conversation clips | It was right on 74 to 84% of the pauses in the middle of a sentence. But it recognized only 17 to 36% of the finished turns (balanced accuracy 0.50 to 0.57, close to chance). Each check took about 126 ms. | `project-log/runs/2026-09-30_smart_turn_fdbv1/` |

For these reasons we submitted with Smart Turn off. To try it, run `GATE_SMART_TURN=1 ./reproduce.sh`.
Background: `project-log/RESEARCH_SMART_TURN.md`.
Recordings and other files for the runs are in the team's
[Google Drive folder](https://drive.google.com/drive/folders/1wFiVit_etrPbMFMhhFRsLO72S9UnPqnm?usp=sharing).

## Datasets

This table lists every dataset that we used, what it is, and what we used it for. Only the first one is the scored
benchmark. We never tuned our agent on it.

| Dataset | What it is | What we used | Used for | Evidence |
|---|---|---|---|---|
| Full-Duplex-Bench v3 ([arXiv 2604.04847](https://arxiv.org/abs/2604.04847), [GitHub](https://github.com/DanielLin94144/Full-Duplex-Bench)) | The scored benchmark. Real people ask for actions out loud, with fillers, pauses, hesitations, self-corrections and false starts. Four areas: travel, finance, housing and e-commerce, with 12 tools. | All 100 recordings, with the benchmark's expected tool calls | Every benchmark score in this README, for the stock agent and for ours | `project-log/runs/2026-09-30_full_gate_gemini38_v2b/` and the other `*_full_*` runs |
| Our practice set (`devset/`) | Requests that we wrote for the same 12 tools. A synthetic voice ([Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M), a text-to-speech model) speaks them. Each has 20 s of silence added, to match the length of the benchmark recordings. | 62 scenarios: 50 of ours and 12 pause scenarios from a teammate | Tuning the harness (runs A to E) and scoring each of its decisions | `project-log/runs/2026-09-29_dev_*`, `2026-09-29_decision_eval.json` |
| Full-Duplex-Bench v1, CANDOR subsets ([arXiv 2503.04721](https://arxiv.org/abs/2503.04721)) | Clips of real conversation, with labels at the pauses and at the ends of turns | 216 pause clips and 119 turn-taking clips (`project-log/scripts/fdbv1_fetch.sh` downloads them) | Testing Smart Turn alone | `project-log/runs/2026-09-30_smart_turn_fdbv1/` |
| SLURP, test split (Bastianelli et al., EMNLP 2020, audio license CC BY-NC 4.0) | Real people who give spoken commands to a home assistant | 11 recordings of light requests, chosen by a fixed rule | The home assistant on real speech, with the lights tool failing on its first try | `project-log/runs/2026-09-30_ext_home_slurp_fail1/` |
| | | The same 11 recordings, with a silence of 1.6 to 3.1 s added inside each request | The home assistant when the speaker stops in the middle of a sentence. 8 of 11 ended with the right lights action, but 6 of 11 also had a wrong action. This agent has no Commit Harness. | `project-log/runs/2026-09-30_ext_home_slurp_pauses_fail0/` |
| | | 111 requests as typed text: 51 light requests and 60 requests that none of our tools can do | The test suite for the offline fallback | `extension/fallback_eval_slurp.jsonl` |
| Our extension clips (`extension/e2e/`) | In-car and home requests that we wrote, spoken by the same synthetic voice | One recorded conversation for each tool pack | The extension agent, from start to end | `project-log/runs/2026-09-30_ext_car_e2e/`, `2026-09-30_ext_home_e2e/` |
| Our fallback command sets (`extension/`) | Typed commands that we wrote | 40 car and home commands (`fallback_eval.jsonl`) and 37 interruptions (`fallback_eval_interrupt.jsonl`) | The test suite for the offline fallback | [`project-log/FALLBACK_TEST_SUMMARY.md`](project-log/FALLBACK_TEST_SUMMARY.md) |

`./reproduce.sh` downloads the benchmark recordings. The SLURP audio and the Full-Duplex-Bench v1 audio are not in this
repository. `extension/e2e/make_clip_slurp.py`, `make_clip_slurp_pauses.py` and `fdbv1_fetch.sh` build them again from the originals.

## Setup and reproduce

One script, `./reproduce.sh`, does all of the setup, asks for your keys, runs our agent on the 100 benchmark
recordings and scores the result.

### What you need

| | |
|---|---|
| Operating system | Linux, or Windows with WSL (Windows Subsystem for Linux, with Ubuntu). We did not test macOS. The script installs system tools only with `apt` or `dnf`. |
| Disk | About 10 GB free: Python environment 7.8 GB, benchmark 1.1 GB, recordings 0.7 GB. |
| Network | Internet access to LiveKit Cloud and Google Gemini. |
| GPU | Our code does not need one. The benchmark's own speech recognizer uses one if it is present. |
| Time | About 10 minutes of setup, then about 2 hours for the run. The recordings play in real time. |
| Accounts | A LiveKit Cloud project and a Gemini API key. Step 2 tells you how to get them. |

### Step 1: get a Linux shell (Windows only)

Open PowerShell as administrator and run:

```powershell
wsl --install -d Ubuntu
```

Restart the computer when Windows asks. Open Ubuntu from the Start menu, and make a user name and a password.
Run all of the steps below in that Ubuntu window. Clone into your Linux home folder (`~`). It is faster than `/mnt/c/...`.

### Step 2: get the keys

| Key | Required | Where to get it |
|---|---|---|
| `LIVEKIT_URL` | yes | [cloud.livekit.io](https://cloud.livekit.io): make a project. The URL looks like `wss://<project>.livekit.cloud`. |
| `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | yes | In the same project: Settings → API keys → Create key. |
| `GOOGLE_API_KEY` | yes | [Google AI Studio → Get API key](https://aistudio.google.com/apikey). |
| `TYPESAFE_API_KEY` | no | Switches on the Reasoner. Without it, the word patterns (Reflex) decide alone. |
| `OPENAI_API_KEY` | no | Switches on the benchmark's GPT-4o judge. Our own judged numbers used Gemini 2.5 Pro (see the Result section). Without this key, you get only the strict score. |

Use a LiveKit project that nothing else uses during your run. Two agents on one project take each other's rooms,
and both runs fail.

### Step 3: clone and set up

```bash
git clone https://github.com/Nithyon/Theme5-Interruptible-Agents.git
cd Theme5-Interruptible-Agents
SETUP_ONLY=1 ./reproduce.sh
```

`SETUP_ONLY=1` does everything except the 2-hour run:

1. It installs `ffmpeg`, `git` and `curl` if they are missing. It asks for your Linux password one time, for `sudo apt-get`.
2. It installs [`uv`](https://docs.astral.sh/uv/) (a Python package installer). It clones Full-Duplex-Bench at a fixed
   commit into `~/theme5/Full-Duplex-Bench`, and builds the Python environment in `~/theme5/fdb-env` from
   `project-log/runs/env-freeze.txt`.
3. It downloads and unpacks the 100 recordings (736 MB) and makes sure that all 100 are there.
4. It asks for the keys. Paste each key and press Enter. The screen does not show the secrets as you type. After each
   key, it prints `<NAME> saved (<n> characters, value not shown)`, so you can see that the paste is complete.
   Then it offers the two optional keys. Press Enter to skip one.
5. It makes sure that the required keys are present (it reads their names only). It tells you which mode you will
   run in: `Jev disabled: gate uses rules only` or `rules + Jev combined`, and exact-match or GPT-4o scoring.

The script saves the keys to `~/theme5/Full-Duplex-Bench/v3/.env.local`, and only your user can read that file.
The script never prints the keys, never writes them to a log, and never puts them in this repository.

### Step 4: run and score

```bash
./reproduce.sh
```

The script skips the setup that it already did and does not ask for the keys again. It starts our agent with the
submitted configuration, plays the 100 recordings to it, stops the agent and scores the results. The terminal stays
quiet for about 2 hours, because the output goes to log files. Keep the terminal open and keep the computer awake.
Do not run other heavy jobs at the same time. They can make the agent miss whole recordings.

To run the stock agent for comparison:

```bash
./reproduce.sh fdb_agent/baseline_agent.py gemini3_8
```

### Step 5: read the result

The results go to `project-log/runs/<date>_repro_gate_gemini38_v2/`:

| File | What it contains |
|---|---|
| `score.txt` | The main result: passed recordings out of 100, the pass rate, and results by difficulty, number of tools, type of disfluency (filler, pause, correction) and area. |
| `run.txt` | The start and end time and the exact configuration. |
| `agent.log`, `inference.log` | The agent's log and the benchmark runner's log. Read these if something went wrong. |
| `agent_tool_calls.log` | Every tool call that ran. The benchmark scores these. |
| `gate_events.log`, `gate_stats.log` | The harness's decisions: every hold, replace and withdraw. |
| `gate_gemini38_v2_pass_rate_report.json` | The full scoring report. |

Compare your result with our submitted run: 55 strict (exact match) and 67 judged. Without an OpenAI key you get only
the strict score, so compare it with 55. The voice model does not answer the same way every time, so expect a
difference of a few recordings. The logs of our run are in `project-log/runs/2026-09-30_full_gate_gemini38_v2b/`.

### Options

| Setting | Effect |
|---|---|
| `SETUP_ONLY=1` | Setup and key check only, no run. |
| `NO_PROMPT=1` | Never ask for keys. The script stops if `.env.local` is missing or incomplete. |
| `FDB_DIR=...`, `ENV_DIR=...` | Install the benchmark and the Python environment in a folder other than `~/theme5`. |
| `GATE_SMART_TURN=1` | Also use the Listener (Smart Turn). It was off in the submitted run. |
| `GATE_RETRACT=0 GATE_ID_NORMALIZE=0 GATE_BACKCHANNEL=0 GATE_LEAN=0` | Use the 29 September configuration instead of the submitted one. |

On 30 September we tested the install steps in a clean folder, up to the key step. We did not yet repeat the full
2-hour run from a clean folder.

## Troubleshooting

| Problem | What to do |
|---|---|
| `... is required; run ./reproduce.sh again when you have it` | You pressed Enter on a required key. Run the script again. It asks only for the keys that are missing. |
| `... contains a space, quote, $ or backslash` | Add that key by hand: `nano ~/theme5/Full-Duplex-Bench/v3/.env.local`, one `NAME=value` on each line. |
| A key was wrong | Edit `~/theme5/Full-Duplex-Bench/v3/.env.local`, or delete the line of that key and run the script again. The script offers the optional keys only the first time. Add them by hand later. |
| `neither apt-get nor dnf found` | Install `ffmpeg`, `git` and `curl` yourself, then run the script again. |
| `wsl: Failed to translate '...'` | WSL shows this warning about a Windows `PATH` entry. It does no harm. Ignore it. |
| Some recordings have no agent speech | The computer was busy, or another agent used the same LiveKit project. Stop other jobs and run again. |
| The run stopped halfway | Run `./reproduce.sh` again. It plays all 100 recordings again. |

## Things you can run without keys

```bash
./reproduce_extension.sh      # offline tests of the extension: recovery layer, MCP plugin, offline fallback (about 1 min)
```

The harness tests need the benchmark's tool definitions. Run them from the benchmark folder after the setup:

```bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
python <path-to-this-repo>/fdb_agent/test_gate.py
```

## Extension: in-car EV assistant

The extension is a use case outside the benchmark, and it is not part of the benchmark score. It shows what the agent
does when tools are slow or fail. It has its own agent (`extension/ext_agent.py`) and a recovery layer
(`extension/recovery.py`). The recovery layer does five things:

1. It sets a time limit for each attempt.
2. It tries a failed call again, without telling the user.
3. It never repeats an identical request.
4. It undoes an old action before it does a changed one (it cancels the old booking, then makes the new one).
5. It passes the request to a human after repeated failures.

The same layer runs two tool packs: an in-car assistant for an electric car (EV), and a home assistant in the style
of Samsung Bixby. All tools are mock tools. There is no real car, SmartThings or Bixby connection.

### What we ran

In the car, from start to end on recorded audio. We corrected the destination, and one reroute ran.
A failing charger search worked on the third try, and the agent did not mention the failures. A repeated booking was
made once. A changed time cancelled the first booking before the new booking was made. Two failed calls to roadside
help ended in a hand-off to a human. Mock tools, synthetic voice, one run.
Evidence: `project-log/runs/2026-09-30_ext_car_e2e/` (conversation audio and recovery log).

The home assistant, on real speech. We played 11 recordings from the SLURP test set to the home assistant. They are
light requests, recorded with a headset microphone, and a fixed rule chose them (we did not choose by ear). We made
the lights tool fail on its first try. The agent carried out 10 of 11 requests and recovered from all 8 failures.
One request asked for a light color. The agent said that it has no tool for color. One request asked for a time.
The agent switched the light off at once and said that it cannot schedule. One run.
Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/`.

The home assistant, with pauses inside the request. We used the same 11 SLURP recordings and added a silence of
1.6 to 3.1 s in the middle of each sentence ("turn off the ... porch light"). Fully right requests dropped from 10 of
11 to 5 of 11, and 6 requests had a wrong or extra action. For example, "turn the lights off" turned them on. This
agent has no Commit Harness. That is why our next step is to put both layers in one agent. Real speech, pauses
added by us, one run.
Evidence: `project-log/runs/2026-09-30_ext_home_slurp_pauses_fail0/`.

The offline fallback: Gemma 4 on typed commands. If the cloud model cannot be reached, a local model on
[Ollama](https://ollama.com) can choose the action. We tested two sizes of Gemma 4 on three sets of typed commands:

- 40 commands of our own.
- 111 real SLURP requests: 51 light requests and 60 requests that none of our tools can do.
- 37 interruptions that we wrote: corrections, changed actions, "never mind" and hesitations.

The test computer was a laptop with an Intel Core Ultra 7 258V, 32 GB of memory and no separate graphics card.

| | Gemma 4 26B (15.9 GB) | Gemma 4 e4b (3.1 GB) |
|---|---|---|
| Runs | 1 for each set | 3 for each set, the same answers each time |
| Our commands: right tool and values | 34/36 | 34/36 |
| Our commands: correctly did nothing | 4/4 | 4/4 |
| SLURP light requests right | **45/51** | **18/51** (declined 31) |
| SLURP requests with no fitting tool: correctly did nothing | 60/60 | 60/60 |
| Interruptions: right tool and values | 28/29 | 29/29 |
| Interruptions that cancel: correctly did nothing | **8/8** | **6/8** |
| Median time for each command | about 6 s | about 2 s |

We use the 26B model. The e4b model is three times faster, but it declined most real light requests and it carried
out two cancelled actions. For example, after "Turn off the living room lights, wait, no, leave them as they are",
it turned them off. The 26B model needs about 16 GB of memory, so it fits a PC or a car computer, not a phone. These
tests use typed sentences, not speech, and the fallback is not yet connected to the voice agent. Every miss is in
[`project-log/FALLBACK_TEST_SUMMARY.md`](project-log/FALLBACK_TEST_SUMMARY.md).

### Reproduce the extension

`./reproduce_extension.sh` tests the extension alone. It is separate from `./reproduce.sh`, and it is not part of
the benchmark score. Each mode makes sure that it has what it needs before it starts. If something is missing, it
stops and says what is missing.

| Command | Needs | What it does | Time |
|---|---|---|---|
| `./reproduce_extension.sh` (same as `tests`) | Python and [`uv`](https://docs.astral.sh/uv/). No keys, no GPU. | Runs the offline tests of the recovery layer for both packs (time limits, retries, duplicate blocking, cancel and undo, hand-off), the MCP plugin and the offline fallback | about 1 min |
| `./reproduce_extension.sh fallback` | Ollama running and the model downloaded: `ollama pull gemma4:26b-a4b-it-qat` (about 16 GB). No keys. | Runs the offline fallback suite on all three command sets | about 20 min for each run on a 32 GB laptop (188 commands, about 6 s each) |
| `./reproduce_extension.sh e2e car` | The setup and keys of `./reproduce.sh`. Run `SETUP_ONLY=1 ./reproduce.sh` first. | Starts the extension agent, plays a recorded request clip into a LiveKit room with the benchmark's own runner, and saves the agent's spoken reply and its recovery log | about 2 min |
| `./reproduce_extension.sh e2e home`, `e2e slurp`, `e2e slurp_pauses` | Same as above | Runs the home assistant on our own clip, on the real SLURP recordings (the lights tool fails on its first try), or on the SLURP recordings with pauses inside the request | about 2 min each |
| `./reproduce_extension.sh all` | – | Runs `tests`, then `fallback` if Ollama is running, then `e2e car` if the benchmark setup exists. It says why it skips a part. | – |

`./reproduce_extension.sh --help` prints the same summary. The script passes extra arguments after `fallback` to
`extension/fallback_suite.py`:

```bash
./reproduce_extension.sh fallback --limit 5                               # the first 5 commands of each set, a quick test
./reproduce_extension.sh fallback --sets interrupt                        # only the interruption commands
FALLBACK_MODEL=gemma4:e4b-it-qat FALLBACK_RUNS=3 ./reproduce_extension.sh fallback   # the small model, 3 runs
```

Settings (all optional):

| Variable | Default | Effect |
|---|---|---|
| `FALLBACK_MODEL` | `gemma4:26b-a4b-it-qat` | The model for the fallback suite |
| `FALLBACK_RUNS` | `1` | How many times each command set runs |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | The address of the Ollama server |
| `EXT_ENV_DIR` | `~/theme5/ext-env` | Where the small test environment is made |
| `FDB_DIR`, `ENV_DIR` | same as `./reproduce.sh` | Where the benchmark and its Python environment are (used by `e2e`) |

Where the results go:

| Mode | Folder | Contents |
|---|---|---|
| `fallback` | `project-log/runs/<date>_fallback_suite_<model>/` | `summary.md` (the results table), one file for each set and run with every command, the expected answer and the model's answer, and `machine.json` (CPU, memory, model size, tokens per second) |
| `e2e` | `project-log/runs/<date>_repro_ext_<pack>/` | `agent_reply.wav` (what the agent said), `ext_recovery_events.log` (every retry, duplicate, undo and hand-off), `result.json` (the text of the reply), `agent.log`, `inference.log`, `run.txt` |

More facts about the script:

- It never asks for keys and never prints them. `e2e` only makes sure that the key names exist in the benchmark's
  `.env.local`, the same way that `./reproduce.sh` does.
- It never downloads a model. It prints the `ollama pull` command instead.
- `fallback` does not write over an existing results folder. Move the old folder to run again on the same day.
  `e2e` writes into the same folder of the day again and replaces its files.
- It does not change the benchmark's logs (`/tmp/agent_tool_calls.log` and the harness logs). But do not run `e2e`
  while a benchmark run uses the same LiveKit project.
- `e2e` uses Gemini Live, so it needs the same keys as the benchmark.

### Talk to it yourself

The extension agent uses the same `.env.local`. Start it, then connect from the
[LiveKit Agents Playground](https://agents-playground.livekit.io) (a LiveKit web page with a microphone) with the same LiveKit project:

```bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
LK_PROVIDER=ext_gemini38 python <path-to-this-repo>/extension/ext_agent.py dev                  # in-car pack
EXT_PACK=home LK_PROVIDER=ext_gemini38 python <path-to-this-repo>/extension/ext_agent.py dev    # home pack
```

More: [`extension/README.md`](extension/README.md) and [`extension/DESIGN.md`](extension/DESIGN.md).

## Where things are

| Path | What it contains |
|---|---|
| `reproduce.sh` | Setup, run and scoring in one command |
| `reproduce_extension.sh` | Optional: tests, the offline fallback suite and the recorded runs of the extension |
| `fdb_agent/` | The benchmark agent (`gate_agent.py`), the harness (`gate.py`), the stock agent (`baseline_agent.py`) and tests |
| `extension/` | The extension agent, the recovery layer, the in-car and home tool packs, the offline fallback and their tests |
| `presentation/` | The slides as PDF and PowerPoint, and the demo video link (`DEMO_VIDEO.md`) |
| `docs/figures/` | The overview figure and the script that draws it |
| `project-log/ARCHITECTURE.md` | A one-page architecture of both agents |
| `project-log/runs/` | Logs, decision logs, results for each recording and score reports for every run |
| `project-log/SCORES.md` | Every score and where it came from |
| `project-log/FALLBACK_TEST_SUMMARY.md` | The offline fallback results and every miss |
| `README_FULL.md` | The full write-up: design, all results, limits, related work |
| `AI_DISCLOSURE.md` | Which AI tools did what. AI assistants wrote most of the code and documents. The team made the decisions. |
