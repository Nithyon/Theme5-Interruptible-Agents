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
- [Datasets](#datasets)
- [Setup and reproduce](#setup-and-reproduce)
- [Troubleshooting](#troubleshooting)
- [Things you can run without keys](#things-you-can-run-without-keys)
- [Extension: in-car EV assistant](#extension-in-car-ev-assistant)
  - [Reproduce the extension](#reproduce-the-extension)
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

## Datasets

Everything we ran, what it is, and what we used it for. Only the first one is the scored benchmark. We never tuned on it.

| Dataset | What it is | What we used | Used for | Evidence |
|---|---|---|---|---|
| **Full-Duplex-Bench v3** ([arXiv 2604.04847](https://arxiv.org/abs/2604.04847), [GitHub](https://github.com/DanielLin94144/Full-Duplex-Bench)) | The scored benchmark: real people asking for actions out loud, with fillers, pauses, hesitations, self-corrections and false starts, across travel, finance, housing and e-commerce (12 tools) | All 100 recordings, with the benchmark's expected tool calls | Every benchmark score in this README (stock agent and ours) | `project-log/runs/2026-09-30_full_gate_gemini38_v2b/` and the other `*_full_*` runs |
| **Our practice set** (`devset/`) | Requests we wrote for the same 12 tools, spoken by a synthetic voice ([Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)) and padded with 20 s of silence to match the benchmark's recording length | 62 scenarios: 50 of ours plus 12 pause scenarios from a teammate | Tuning the harness (runs A to E) and scoring its decisions one by one | `project-log/runs/2026-09-29_dev_*`, `2026-09-29_decision_eval.json` |
| **Full-Duplex-Bench v1**, CANDOR subsets ([arXiv 2503.04721](https://arxiv.org/abs/2503.04721)) | Clips of real conversation, labelled at pauses and at turn ends | 216 pause-handling clips and 119 turn-taking clips (fetched with `project-log/scripts/fdbv1_fetch.sh`) | Testing Smart Turn on its own | `project-log/runs/2026-09-30_smart_turn_fdbv1/` |
| **SLURP**, test split (Bastianelli et al., EMNLP 2020; audio CC BY-NC 4.0) | Real people giving home-assistant commands | 11 light-control recordings, picked by a fixed rule | The home assistant on real speech, with the lights tool failing on its first try | `project-log/runs/2026-09-30_ext_home_slurp_fail1/` |
| | | The same 11 recordings with a silence of 1.6 to 3.1 s inserted inside each request | The home assistant when the speaker stops mid-sentence: 8 of 11 ended with the asked lights action, but 6 of 11 also had a wrong action (this agent has no Commit Harness) | `project-log/runs/2026-09-30_ext_home_slurp_pauses_fail0/` |
| | | 111 requests as typed text: 51 light requests and 60 that none of our tools can serve | The local fallback suite | `extension/fallback_eval_slurp.jsonl` |
| **Our extension clips** (`extension/e2e/`) | In-car and home requests we wrote, spoken by the same synthetic voice | One recorded conversation per pack | The extension agent end to end | `project-log/runs/2026-09-30_ext_car_e2e/`, `2026-09-30_ext_home_e2e/` |
| **Our fallback command sets** (`extension/`) | Typed commands we wrote | 40 car and home commands (`fallback_eval.jsonl`) and 37 interruptions (`fallback_eval_interrupt.jsonl`) | The local fallback suite | [`project-log/FALLBACK_TEST_SUMMARY.md`](project-log/FALLBACK_TEST_SUMMARY.md) |

The benchmark recordings are downloaded by `./reproduce.sh`. The SLURP and Full-Duplex-Bench v1 audio are not stored in
this repository: `extension/e2e/make_clip_slurp.py`, `make_clip_slurp_pauses.py` and `fdbv1_fetch.sh` rebuild them from the originals.

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
./reproduce_extension.sh      # offline tests of the extension: recovery layer, MCP plugin, local fallback (~1 min)
```

The harness tests need the benchmark's tool definitions, so run them from the benchmark folder after setup:

```bash
source ~/theme5/fdb-env/bin/activate
cd ~/theme5/Full-Duplex-Bench/v3
python <path-to-this-repo>/fdb_agent/test_gate.py
```

## Extension: in-car EV assistant

A use case beyond the benchmark, not part of its score: what the agent does when tools are slow or fail.
It has its own agent (`extension/ext_agent.py`) and a recovery layer (`extension/recovery.py`): a time limit per
attempt, a quiet retry, no repeat of an identical request, undo (cancel the old action, then do the new one), and a
hand-off to a human after repeated failures. The same layer runs two tool packs: an in-car EV assistant and a
Bixby-style home assistant. All tools are mocks: there is no real car, SmartThings or Bixby integration.

### What we ran

**In-car, end to end on recorded audio.** A corrected reroute runs once, a failing charger lookup is retried quietly,
a repeated booking is not made twice, changing the time cancels the first booking before making the new one, and two
failed roadside requests end in a hand-off to a human. Mock tools, synthetic request voice, one run.
Evidence: `project-log/runs/2026-09-30_ext_car_e2e/` (conversation audio, recovery log).

**Home assistant, on real speech.** 11 recordings from the SLURP test set (light-control requests, headset
microphone, picked by a fixed rule, not by ear) were played to the home assistant with the lights tool made to fail
on its first attempt. 10 of 11 requests ended in a lights action and all 8 injected failures were recovered by a
retry. One request asked for a light colour and was declined (no such tool); one asked for a time and was switched
off at once, with the agent saying it cannot schedule. One run.
Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/`.

**Local fallback: Gemma 4 offline, on typed commands.** If the cloud model is unreachable, a local model on
[Ollama](https://ollama.com) could choose the action instead. We tested two sizes on three sets of typed commands:
40 of our own, 111 real SLURP requests (51 light requests and 60 that none of our tools can serve), and
37 interruptions (corrections, changed actions, "never mind", hesitations). Measured on a laptop with an Intel Core
Ultra 7 258V, 32 GB RAM and no discrete GPU:

| | Gemma 4 26B (15.9 GB) | Gemma 4 e4b (3.1 GB) |
|---|---|---|
| Runs | 1 per set | 3 per set, same answers each time |
| Our commands: right tool and values | 34/36 | 34/36 |
| Our commands: correctly did nothing | 4/4 | 4/4 |
| SLURP light requests right | **45/51** | **18/51** (declined 31) |
| SLURP requests no tool can serve: correctly did nothing | 60/60 | 60/60 |
| Interruptions: right tool and values | 28/29 | 29/29 |
| Interruptions: cancelled, correctly did nothing | **8/8** | **6/8** |
| Median time per command | about 6 s | about 2 s |

The 26B is the one to use: e4b is three times faster, but it declined most real light requests and carried out two
cancelled actions ("Turn off the living room lights, wait, no, leave them as they are" turned them off). The 26B needs
about 16 GB of memory, so it suits a PC or a car computer, not a phone. These are typed sentences, not speech, and
the fallback is not yet connected to the voice agent. Every miss is listed in
[`project-log/FALLBACK_TEST_SUMMARY.md`](project-log/FALLBACK_TEST_SUMMARY.md).

### Reproduce the extension

`./reproduce_extension.sh` checks the extension on its own. It is separate from `./reproduce.sh` and is not part of
the benchmark score. Each mode checks what it needs before it starts and stops with a clear message if something is missing.

| Command | Needs | What it does | Time |
|---|---|---|---|
| `./reproduce_extension.sh` (same as `tests`) | Python and [`uv`](https://docs.astral.sh/uv/); no keys, no GPU | Offline tests of the recovery layer for both packs (timeouts, retries, duplicate blocking, cancel and undo, hand-off), the MCP plugin and the local fallback | about 1 min |
| `./reproduce_extension.sh fallback` | Ollama running and the model pulled: `ollama pull gemma4:26b-a4b-it-qat` (about 16 GB); no keys | The local fallback suite on all three command sets | about 20 min per run on a 32 GB laptop (188 commands, about 6 s each) |
| `./reproduce_extension.sh e2e car` | The setup and keys of `./reproduce.sh` (run `SETUP_ONLY=1 ./reproduce.sh` first) | Starts the extension agent, streams a recorded request clip into a LiveKit room with the benchmark's own runner, saves the agent's spoken reply and its recovery log | about 2 min |
| `./reproduce_extension.sh e2e home`, `e2e slurp`, `e2e slurp_pauses` | Same as above | The home assistant on our own clip, on real SLURP recordings (the lights tool fails on its first try, to show the retry), or on SLURP recordings with pauses inside the request | about 2 min each |
| `./reproduce_extension.sh all` | – | `tests`, then `fallback` if Ollama is running, then `e2e car` if the benchmark setup exists; skipped parts say why | – |

`./reproduce_extension.sh --help` prints the same summary. Extra arguments after `fallback` go to
`extension/fallback_suite.py`:

```bash
./reproduce_extension.sh fallback --limit 5                               # first 5 commands of each set, a quick check
./reproduce_extension.sh fallback --sets interrupt                        # only the interruption commands
FALLBACK_MODEL=gemma4:e4b-it-qat FALLBACK_RUNS=3 ./reproduce_extension.sh fallback   # the small model, 3 runs
```

Settings (all optional):

| Variable | Default | Effect |
|---|---|---|
| `FALLBACK_MODEL` | `gemma4:26b-a4b-it-qat` | Model for the fallback suite |
| `FALLBACK_RUNS` | `1` | How many times each command set is run |
| `OLLAMA_URL` | `http://127.0.0.1:11434` | Ollama server address |
| `EXT_ENV_DIR` | `~/theme5/ext-env` | Where the small test environment is created |
| `FDB_DIR`, `ENV_DIR` | same as `./reproduce.sh` | Where the benchmark and its Python environment live (used by `e2e`) |

Where results go:

| Mode | Folder | Contents |
|---|---|---|
| `fallback` | `project-log/runs/<date>_fallback_suite_<model>/` | `summary.md` (the results table), one file per set and run with every command, the expected answer and the model's answer, and `machine.json` (CPU, RAM, model size, tokens per second) |
| `e2e` | `project-log/runs/<date>_repro_ext_<pack>/` | `agent_reply.wav` (what the agent said), `ext_recovery_events.log` (every retry, duplicate, undo and hand-off), `result.json` (transcript of the reply), `agent.log`, `inference.log`, `run.txt` |

Good to know:

- Keys are never asked for or printed. `e2e` only checks that the variable names exist in the benchmark's
  `.env.local`, the same way `./reproduce.sh` does.
- It never downloads a model by itself; it prints the `ollama pull` command instead.
- `fallback` refuses to overwrite an existing results folder; move it aside to run again on the same day.
  `e2e` writes into the same day's folder again and replaces its files.
- It does not touch the benchmark's logs (`/tmp/agent_tool_calls.log` and the harness logs). Still, don't run `e2e`
  while a benchmark run is using the same LiveKit project.
- `e2e` uses Gemini Live, so it needs the same keys as the benchmark.

### Talk to it yourself

The extension agent uses the same `.env.local`. Start it and connect from the
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
| `reproduce_extension.sh` | Optional: tests, local fallback suite and end-to-end runs of the extension |
| `fdb_agent/` | The benchmark agent (`gate_agent.py`), the harness (`gate.py`), the stock agent (`baseline_agent.py`) and tests |
| `extension/` | Extension agent, recovery layer, in-car and home tool packs, local fallback, their tests |
| `docs/figures/` | The overview figure and the script that draws it |
| `project-log/ARCHITECTURE.md` | One-page architecture of both agents |
| `project-log/runs/` | Logs, decision logs, per-recording results and score reports for every run |
| `project-log/SCORES.md` | Every score and where it came from |
| `project-log/FALLBACK_TEST_SUMMARY.md` | Local fallback results and every miss |
| `README_FULL.md` | Full write-up: design, all results, limitations, related work |
| `project-log/AI_USAGE.md` | AI assistants wrote most of the code and documents; the team made the decisions |
