"""Add the Gemma 4 size-versus-accuracy comparison (Aryan's laptop) to the documents."""
import io, os, sys

R = sys.argv[1] if len(sys.argv) > 1 else "."
def rd(p): return io.open(os.path.join(R, p), encoding="utf-8").read()
def wr(p, s): io.open(os.path.join(R, p), "w", encoding="utf-8", newline="\n").write(s)
def add(p, text):
    s = rd(p)
    if text.strip().splitlines()[0] in s: print("already", p); return
    wr(p, s.rstrip("\n") + "\n\n" + text.strip("\n") + "\n"); print("appended", p)
def sub(p, a, b):
    s = rd(p)
    if a not in s: print("NOT FOUND", p, a[:60]); return
    wr(p, s.replace(a, b, 1)); print("ok", p)

SECTION = """### Model size against accuracy (same laptop, same settings)

| Model | Loaded size | Runs | Our 40: right tool and values | SLURP lights: right | SLURP "no tool fits": left alone | Self-corrections | Median time |
|---|---|---|---|---|---|---|---|
| Gemma 4 26B (`gemma4:26b-a4b-it-qat`) | 15.9 GB | 1 | 34/36 | 45/51 | 60/60 | 6/6 | 5.6 to 6.0 s |
| Gemma 4 e4b (`gemma4:e4b-it-qat`) | 3.1 GB | 3 | 34/36 | 18/51 | 60/60 | 6/6 | 1.7 to 2.1 s |

- On our own 40 commands the two models tie; the small one is about three times faster.
- On the real SLURP requests the small one fails: 31 of its 33 misses are requests it declined, including plain ones
  such as "turn the lights off". Our hand-written set hid this difference; only the real requests showed it.
- A likely cause, not tested: our lights tool requires a room, most SLURP requests name none, and the small model
  declines instead of choosing one. Making the room optional is the obvious next experiment.
- The small model gave identical answers in all 3 runs. Neither model ever acted when no tool fitted.
- Recounted from the per-run result files (`project-log/scripts/suite_check.py`); folders
  `project-log/runs/2026-09-30_fallback_suite_gemma4_26b-a4b-it-qat/` and `..._gemma4_e4b-it-qat/`.
"""
for p in ("extension/README.md", "project-log/SCORES.md", "README_FULL.md"):
    add(p, SECTION)
sub("project-log/JUDGE_QA.md", "About 6 s per command.\n",
    "About 6 s per command. The 3 GB Gemma 4 e4b ties on our own commands but gets only 18 of 51 real SLURP light "
    "requests right (it declines most), so the fallback needs the large model for now.\n")
