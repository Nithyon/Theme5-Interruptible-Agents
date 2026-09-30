"""Record the pause test (real SLURP speech with inserted mid-request silences) in the documents."""
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

SECTION = """## Pause test: real speech with silences inside the request (30 September, 23:15 IST)

The same 11 real SLURP recordings, each with one silence of 1.6 to 3.1 s (irregular, fixed seed) inserted at its
longest gap between words, e.g. "turn off the ... 2.8 s ... porch light". The speech is real; the pauses are ours.
Played to the extension's home assistant through LiveKit, tools not failing (`EXT_LIGHTS_FAIL_FIRST=0`).
This agent has the recovery layer but not the Commit Harness. One run; the first attempt failed to connect to
Gemini Live and is kept as `..._attempt1_no_connection`.

| | Same recordings without pauses (earlier run) | With pauses |
|---|---|---|
| Requests that ended with the asked lights action | 10 of 11 | 8 of 11 |
| Requests with a wrong or unrequested action | 0 of 11 | **6 of 11** |
| Requests fully right, with nothing wrong done | 10 of 11 | 5 of 11 |

Wrong actions with pauses: "turn the lights off" turned them on; "light colour for study room" set the study AC to
22 (without pauses it said it cannot change colour); "and the darkness has fallen" set the bedroom AC; "please turn
lights off" also changed the dining-room AC; "light up the lights in the kitchen" first switched on the bedroom,
then the kitchen; after "turn my lights down" it also rang the phone, which nobody asked for.

- By our clock no action came before the request had ended, but the clock is lined up from the agent's session
  start, so it can be off by a second or two; we do not claim that the agent acted during the pause.
- What the run does show: silences inside a request make the plain voice agent mishear and act wrongly, six times in
  eleven. The benchmark agent puts the Commit Harness in front of the tools for this reason; the extension agent does
  not have it yet, and this run supports combining the two.
- Limits: 11 recordings, one run, inserted pauses, the no-pause comparison ran with the lights tool failing on its
  first attempt (that does not cause wrong actions, but the conditions are not identical).
- Evidence: `project-log/runs/2026-09-30_ext_home_slurp_pauses_fail0/` (recovery log, per-request score, agent audio);
  clip builder `extension/e2e/make_clip_slurp_pauses.py`.
"""
for p in ("project-log/SCORES.md", "README_FULL.md", "extension/README.md"):
    add(p, SECTION)
sub("project-log/JUDGE_QA.md", "Limits: 11 recordings, one run, the room is not scored because most requests name none, the tools are mocks.",
    "Limits: 11 recordings, one run, the room is not scored because most requests name none, the tools are mocks.\n"
    "- Pauses: with a 1.6 to 3.1 s silence inserted inside each of those real requests, the extension agent (recovery "
    "layer, no Commit Harness) did something wrong or unrequested in 6 of 11, for example turning the lights on after "
    "\"turn the lights off\"; without pauses, 0 of 11. One run. It is the case for putting the harness in front of the "
    "recovery layer.")
