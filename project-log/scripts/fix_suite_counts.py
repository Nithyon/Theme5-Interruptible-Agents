"""The SLURP shard holds 51 distinct light-control sentences under our rule, not 60: correct the
counts in the suite's texts and add the how-to to extension/README.md."""
import io, sys
R = sys.argv[1]
def rw(p, pairs):
    s = io.open(R + "/" + p, encoding="utf-8").read()
    for a, b in pairs:
        if a not in s: print("NOT FOUND", p, a[:50])
        s = s.replace(a, b)
    io.open(R + "/" + p, "w", encoding="utf-8", newline="\n").write(s)
rw("extension/fallback_suite.py", [
    ("120 real user requests from the SLURP test set:", "111 real user requests from the SLURP test set:"),
    ("60 light-control (expect set_lights, right on/off)", "51 light-control (expect set_lights, right on/off)"),
    ("3 runs of both sets take about 40 minutes; --runs 1 takes about 14.", "3 runs of both sets take about 38 minutes; --runs 1 takes about 13."),
    ("slurp = 120 real requests from the SLURP test set (60 light control, 60 that none of",
     "slurp = 111 real requests from the SLURP test set (51 light control, 60 that none of"),
])
rw("extension/make_fallback_slurp.py", [
    ("Build extension/fallback_eval_slurp.jsonl: 120 REAL user requests", "Build extension/fallback_eval_slurp.jsonl: 111 REAL user requests"),
    ("  - 60 light-control requests -> expect", "  - 51 light-control requests (all the distinct ones in the shard) -> expect"),
    ("# quotas sum to 60; the shard holds only 2 distinct \"light on\" sentences and 12 \"brighter\" ones",
     "# the shard holds 25 distinct \"off\", 2 \"on\", 12 \"dim\" and 12 \"brighter\" sentences: 51 in all"),
])
p = R + "/extension/README.md"
s = io.open(p, encoding="utf-8").read()
if "## Fallback test suite" not in s:
    s = s.rstrip("\n") + """

## Fallback test suite (`fallback_suite.py`)

One command, two small text sets, several runs, and a record of the machine:

```bash
python extension/fallback_suite.py --model gemma4:26b-a4b-it-qat --runs 3 --timeout 30
```

| Set | File | What it checks |
|---|---|---|
| own | `fallback_eval.jsonl` (40) | Commands we wrote for the car and home tools, 6 with a self-correction |
| slurp | `fallback_eval_slurp.jsonl` (111) | Real user requests from the SLURP test set (Bastianelli et al., EMNLP 2020, text CC BY 4.0): 51 light-control requests (right tool, right on/off) and 60 requests none of our tools can serve (the model must not act) |

- Needs a running Ollama with the model pulled (`ollama pull <model>`). Nothing else to download: both sets are in the repo (18 KB).
- Output folder `project-log/runs/<date>_fallback_suite_<model>/`: `machine.json` (CPU, RAM, Ollama version, tokens per second), one result file per set and run with every command and the model's answer, `summary.md` with a table.
- Time: about 5 s per command on a CPU-only laptop, so about 13 minutes per run of both sets. `--runs 1` for a single pass, `--sets slurp` for one set, `--limit 10` for a quick check.
- The mapping from SLURP intent to our tool is ours (`make_fallback_slurp.py`); room and brightness are not scored because most requests name no room. Typed text, no audio.
"""
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("done")
