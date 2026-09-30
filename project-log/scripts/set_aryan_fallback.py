"""Record Aryan's local-fallback work and the laptop it was measured on in the documents."""
import io, os, sys

R = sys.argv[1] if len(sys.argv) > 1 else "."
def rd(p): return io.open(os.path.join(R, p), encoding="utf-8").read()
def wr(p, s): io.open(os.path.join(R, p), "w", encoding="utf-8", newline="\n").write(s)
def sub(p, a, b):
    s = rd(p)
    if a not in s: print("NOT FOUND", p, a[:60]); return
    wr(p, s.replace(a, b, 1)); print("ok", p)
def add(p, text):
    s = rd(p)
    if text.strip().splitlines()[0] in s: print("already", p); return
    wr(p, s.rstrip("\n") + "\n\n" + text.strip("\n") + "\n"); print("appended", p)

sub("project-log/AI_USAGE.md",
    "| Aryan | TODO for the team: state Aryan's contribution here before submitting. |",
    "| Aryan | The local fallback, working with an AI coding assistant (Claude Code) on his own laptop: found why Gemma 4 "
    "returned no tool call (its thinking mode used up the whole reply limit) and fixed it; re-measured three local models; "
    "ran the fallback test suite (our 40 commands and 111 real SLURP requests) on his laptop and reviewed the misses, "
    "including which ones are scoring artefacts. |")
sub("project-log/AI_USAGE.md",
    "| **Gemini CLI / Antigravity (\"junior assistant\")** |",
    "| **Claude Code (Aryan's session, 2026-09-30)** | The `\"think\": False` fix in `extension/local_fallback.py`, the "
    "local-model re-measurement and its write-up in `extension/README.md`, and the fallback-suite run and miss analysis "
    "on Aryan's laptop. |\n| **Gemini CLI / Antigravity (\"junior assistant\")** |")

SECTION = """## Local fallback on Aryan's laptop (30 September, 22:07 to 22:30 IST)

Measured by Aryan with `extension/fallback_suite.py`, one run, typed text.

**Device.** Intel Core Ultra 7 258V laptop (8 cores), 32 GB RAM, no discrete or NVIDIA GPU (the integrated Arc
graphics shares system RAM; Ollama placed 8.3 GB of the model there). Linux (CachyOS), Ollama 0.32.14. Model
`gemma4:26b-a4b-it-qat` (25.2B parameters, Q4_0, 15.9 GB loaded). 16.4 tokens per second as measured by the suite.
Details: `project-log/runs/2026-09-30_fallback_suite_gemma4_26b-a4b-it-qat/machine.json` and `machine_note.txt`.

| Set | Right tool | Right tool and values | Stayed out when no tool fits | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|---|
| Our 40 commands | 36/36 | 34/36 | 4/4 | 6/6 | 0 | 5.6 s |
| 111 real SLURP requests | 46/51 | 45/51 (right on/off) | 60/60 | n/a | 0 | 6.0 s |

- It never acted on a request none of our tools can serve (60 of 60), which matters most for a fallback that runs
  without the cloud.
- The 8 misses: 2 requests asking for something the tool cannot do (a scheduled time, a colour), 2 vague wordings
  ("and the darkness has fallen"), 2 in our own set where the model's free text ("the car won't start") did not
  exactly match our expected text ("won't start"), 1 request about a screen that SLURP labels as lights, and 1 real
  error: "no lights in the kitchen" turned the lights on. The exact-text and mislabelled cases are arguably scoring
  artefacts; we report the measured score, not an adjusted one.
- One run only: three runs would not have finished before the deadline, so stability across runs is not measured.
- It is not wired into the voice agent and is not part of the benchmark score.
- A third set, `fallback_eval_interrupt.jsonl` (37 commands we wrote: corrected values, "never mind", hesitations,
  "no rush"), was added after this run and has not been run with Gemma 4. The small FunctionGemma on our desktop scores
  13 of 29 on its action commands and stays out on 0 of 8 cancellations
  (`project-log/runs/2026-09-30_fallback_suite_functiongemma/`).
"""
for p in ("extension/README.md", "project-log/SCORES.md", "README_FULL.md"):
    add(p, SECTION)

sub("project-log/JUDGE_QA.md", "- Consequence: it is a fallback for the extension only.",
    "- Fallback suite on Aryan's laptop (Core Ultra 7 258V, 32 GB, no discrete GPU, one run): our 40 commands 34/36 "
    "fully correct and 4/4 correctly left alone; 111 real SLURP requests 45/51 light requests right, and it acted on 0 of "
    "60 requests no tool fits. About 6 s per command.\n- Consequence: it is a fallback for the extension only.")
sub("project-log/ARCHITECTURE.md", "Gemma 4 26B (large, about 5.4 s per command): 38 of 40",
    "Gemma 4 26B (large, about 5.4 s per command): 38 of 40; on 111 real SLURP requests 45 of 51 light requests right "
    "and 0 of 60 wrongly acted on (Aryan's laptop, one run)")
