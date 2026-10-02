# AI disclosure

Team Reign (SRM Institute of Science and Technology) · Theme 05, Interruptible Real-Time Agents · updated 1 October 2026

Members: Pokala Sai Nithin, Aryan Garg, Lohitashwa and V Preetha.

## In short

AI coding assistants wrote almost all of the code, tests, scripts and documents in this repository and ran most of
the experiments. The team chose the approach, made every decision about what to build, run and submit, supplied the
accounts and keys, reviewed the results, and is responsible for every claim. We did not use AI to read, tune on or
generate the benchmark's expected answers.

## Who did what

| Person | Decisions and work | AI used |
|---|---|---|
| Pokala Sai Nithin (team lead) | Chose the approach and priorities: the Commit Harness, the recovery layer, the in-car EV use case, the SLURP and pause tests; decided which runs to make and which configuration to submit; created the accounts and typed every key; approved or stopped every action | Claude Code (Claude Opus, with Claude Sonnet sub-agents), plus Gemini CLI / Antigravity for small tasks |
| Lohitashwa | The upgrade pack for the harness (dangling-word rule, merged prompt rules, 12 pause practice scenarios); `reproduce_extension.sh`; the README setup guide and overview figure; the presentation files; an independent re-run of `reproduce.sh` on his laptop | An AI assistant for the upgrade pack (tool not recorded); Claude Code for the later work |
| Aryan Garg | The offline Gemma fallback: found why Gemma 4 returned no tool call (its thinking mode used up the reply limit) and fixed it; measured Gemma 4 26B and e4b on his laptop on our commands, real SLURP requests and the interruption set; audited the test summary against the raw result files | Claude Code |
| V Preetha | Documentation and media: the presentation slides, the submission documents, and the editing of the demo video | Not recorded |

## AI tools used to build the submission

| Tool | What it did |
|---|---|
| **Claude Code, lead session (Claude Opus)** | Design and implementation of the benchmark agent and the Commit Harness (`fdb_agent/`), the recovery layer and in-car / home agents (`extension/`), the test suites, `reproduce.sh`, the benchmark, SLURP and pause runs, the scoring and judge scripts, and most documents, including this one |
| **Claude Sonnet sub-agents** (started by the lead session) | Delegated parts: documentation drafts, the home tool pack, the plugin (MCP) test path, the local-fallback module, research notes |
| **Claude Code, teammates' sessions** | Aryan's fallback fix, measurements and audit; Lohit's `reproduce_extension.sh`, README sections and reproduction run |
| **Claude (artifacts)** | Drafted the slide deck and the architecture page as web pages; the team reviewed them and exported the deck |
| **Gemini CLI / Antigravity** | Small scoped tasks: downloading and checking the benchmark audio, checking model ids, a first research note later verified against the papers |

## AI models inside the product and its evaluation

| Model | Role |
|---|---|
| **Gemini 3.8 Live** (Google) | The voice model in every agent: listens, speaks, proposes tool calls |
| **TypeSafe Jev** | Optional classifier inside the harness: is the user finished, is a repeat a correction; falls back to rules on any failure |
| **Gemini 2.5 Pro** (Google) | Our judge for every "judged" score, using the benchmark's own judge prompts unchanged, **as a stand-in for the benchmark's GPT-4o judge**; we had no OpenAI access and used no OpenAI model anywhere |
| **NVIDIA Parakeet-TDT-0.6B-v2** | Speech recognition inside the benchmark's own scoring pipeline (the benchmark's model, not ours) |
| **Smart Turn v3.2** (Pipecat) | Optional end-of-turn model; tested, switched off in the submitted run |
| **Gemma 4 26B and e4b, FunctionGemma** (Google, via Ollama); **Qwen3 30B** (comparison only) | Offline fallback candidates, tested on typed commands; not part of the benchmark agent |
| **Kokoro-82M** | Text-to-speech for our own practice and demo audio only, never mixed with benchmark recordings |

## Data

- **Full-Duplex-Bench v3**: the scored benchmark. We looked only at pass/fail results and our own agent's outputs,
  never used its expected answers to change the agent, and ran two configurations on 30 September and submitted the
  better one (both runs' logs are in the repository).
- **SLURP** (Bastianelli et al., EMNLP 2020): real users' home-assistant requests, used to test the extension and the
  fallback. Recordings were picked by a fixed rule, not by hand. The pauses in the pause test were inserted by us.
- **Our own requests** (practice set, fallback commands, interruption set): written by us with AI help and labelled
  as ours wherever they are used.

## How AI output was checked

Code was checked by automated tests and by benchmark and practice runs. Every published number was recounted from the
raw result files, and a teammate audited the fallback results independently. AI mistakes that were caught and
corrected are recorded in `project-log/WORKLOG.md`, for example a miscounted test total, a wrong claim that a side
measurement had not disturbed a benchmark run, and an early over-optimistic reading of Smart Turn. Humans reviewed
results and decisions, not every line of code.

More detail: `project-log/AI_USAGE.md` (the earlier, longer version of this file).
