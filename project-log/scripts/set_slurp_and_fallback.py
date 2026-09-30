"""Bring the documents in line with two late results of 2026-09-30: the extension on real SLURP
recordings, and the local fallback re-measured by a teammate on a second machine."""
import io, os, sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."

def rd(p): return io.open(os.path.join(ROOT, p), encoding="utf-8").read()
def wr(p, s): io.open(os.path.join(ROOT, p), "w", encoding="utf-8", newline="\n").write(s)
def sub(p, old, new):
    s = rd(p)
    if old not in s:
        print("NOT FOUND in", p, ":", old[:60]); return
    wr(p, s.replace(old, new, 1)); print("ok", p)
def add(p, text):
    s = rd(p)
    if text.strip().splitlines()[0] in s:
        print("already in", p); return
    wr(p, s.rstrip("\n") + "\n\n" + text.strip("\n") + "\n"); print("appended", p)

SLURP_SHORT = ("On real speech: 11 recordings from the SLURP test set (light-control requests, headset microphone, "
               "picked by a fixed rule, not by ear) were played to the home assistant with the lights tool made to fail "
               "on its first attempt. 10 of 11 requests ended in a lights action and all 8 injected failures were recovered "
               "by a retry. One request asked for a light colour and was declined (no such tool); one asked for a time and "
               "was switched off at once, with the agent saying it cannot schedule. One run. "
               "Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/`.")
FB_SHORT = ("FunctionGemma (300 MB) is fully correct on 15 of 40 of our typed commands on an idle machine; "
            "Gemma 4 26B is fully correct on 38 of 40 (right tool 40 of 40) at about 5.4 s per command, once its thinking "
            "mode is switched off. It is a large model for a PC or car computer, not a phone. Our own 40 commands, one run "
            "each, on a teammate's laptop; not attached to the voice agent")

sub("README.md", "requests end in a hand-off to a human. Mock tools, synthetic request voice, one run.",
    "requests end in a hand-off to a human. Mock tools, synthetic request voice, one run.\n\n" + SLURP_SHORT)

sub("project-log/ARCHITECTURE.md", "FunctionGemma through Ollama; about 30% correct in our test, not attached to the agent",
    "Gemma through Ollama, not attached to the agent. FunctionGemma (300 MB): 15 of 40 of our commands fully correct. "
    "Gemma 4 26B (large, about 5.4 s per command): 38 of 40")

sub("project-log/PRESENTATION_SCRIPT.md", "the local Gemma fallback is about thirty percent correct, so not usable.",
    "the local fallback works only with a large Gemma model (38 of our 40 typed commands fully correct, about five "
    "seconds each); the small one is not usable, and it is not wired into the voice agent.")
sub("project-log/PRESENTATION_SCRIPT.md", "Limits: mock tools, a synthetic request voice, one run, and no spoken \"still checking\" yet.",
    "We also played 11 real recordings from the SLURP test set, light-control requests, with the lights tool failing on "
    "its first try: 10 of 11 were carried out and all 8 failures were recovered by a retry. That run also exposed a bug "
    "in our no-repeat rule, which we fixed and re-ran. Limits: mock tools, a synthetic voice in the car scenario, "
    "one run each, and no spoken \"still checking\" yet.")

sub("project-log/JUDGE_QA.md", "Local fallback: measured at 27.5% and 32.5% fully correct in two runs, not usable yet.",
    "Local fallback: usable only with a large model (Gemma 4 26B, 38 of 40 fully correct); the small FunctionGemma is "
    "not (15 of 40); not wired into the voice agent.")
sub("project-log/JUDGE_QA.md", "- Consequence: it is a fallback for the extension only.",
    "- Update, later on 30 September (teammate's laptop, idle, same 40 commands, one run each): FunctionGemma 24/40 right "
    "tool and 15/40 fully correct. Gemma 4 26B first returned nothing on 38 of 40 because its thinking mode used up the "
    "reply limit; with thinking off it scored 40/40 right tool, 38/40 fully correct, 6/6 self-corrections, median 5.4 s. "
    "Qwen3 30B: 38/40 and 36/40. The 40 commands are our own, typed, not a published set. Gemma 4 26B is a large model "
    "for a PC or car computer, not a phone.\n- Consequence: it is a fallback for the extension only.")
sub("project-log/JUDGE_QA.md", "the in-car EV assistant is the headline scenario (`runs/2026-09-30_ext_car_e2e/`).",
    "the in-car EV assistant is the headline scenario (`runs/2026-09-30_ext_car_e2e/`).\n"
    "- Real speech: those two runs use a synthetic request voice. We also played 11 real recordings from the SLURP test "
    "set (Bastianelli et al., EMNLP 2020; light-control requests, headset microphone, fixed selection rule) to the home "
    "assistant, with the lights tool failing on its first attempt: 10 of 11 ended in a lights action, all 8 injected "
    "failures were recovered by a retry, one colour request was declined (no such tool). The first attempt of this run "
    "exposed a defect: a repeated request was answered from memory although the lights had been changed in between. "
    "We fixed it and re-ran; both runs are kept (`runs/2026-09-30_ext_home_slurp_fail1/` and `_attempt1`). "
    "Limits: 11 recordings, one run, the room is not scored because most requests name none, the tools are mocks.")

LONG = """## Update, late 30 September: real speech for the extension, and the fallback re-measured

**Extension on real recordings (SLURP).** SLURP (Bastianelli et al., EMNLP 2020) is a published set of real people giving
home-assistant commands; its audio licence is CC BY-NC 4.0. We took one shard of its test split and selected by a fixed
rule, without listening: light-control intents, headset recordings, one per sentence, in file order (5 off, 2 on, 2 dim,
2 up = 11 recordings). They were joined with 11 s of silence between them and played to the home assistant through LiveKit,
the way the benchmark plays its recordings. The lights tool was set to fail on the first attempt of each new request
(`EXT_LIGHTS_FAIL_FIRST=1`).

| | Attempt 1 | After the fix |
|---|---|---|
| Requests that ended in a lights action with the asked state | 9 of 11 | 10 of 11 |
| Injected first-attempt failures, recovered by a retry | 4 of 4 | 8 of 8 |
| Requests answered from an earlier identical request | 5 | 0 |
| Hand-offs | 0 | 0 |

- Attempt 1 exposed a defect in the no-repeat rule: "lights on", then "dim", then "turn up the brightness" produced the same
  call as the first request and was answered from memory, so the lights stayed dimmed while the agent said they were up.
  Fix in `extension/recovery.py`: a repeat is answered from memory only while it still matches the latest completed action
  of that kind. Offline tests still pass (35 and 28).
- Not done in either run: "light colour for study room" (we have no colour tool; the agent said so). "Turn off bedroom light
  at nine thirty pm" was declined in attempt 1 and, in the second run, switched off at once with the agent saying it cannot
  schedule; we count that as a lights action, not as a correct handling of the time.
- Limits: 11 recordings, one run after the fix, the room is not scored (most requests name none and the agent picks one),
  brightness is logged but not scored, mock tools. The SLURP audio is not stored in the repository;
  `extension/e2e/make_clip_slurp.py` rebuilds the clip from the dataset.
- Evidence: `project-log/runs/2026-09-30_ext_home_slurp_fail1/` and `..._attempt1/` (recovery log, per-request score,
  agent audio). Run script: `project-log/scripts/ext_e2e_slurp.sh`.

**Local fallback re-measured (teammate's laptop, idle; our own 40 typed commands; one run each).**

| Model | Right tool | Fully correct | Self-corrections | No answer | Median time |
|---|---|---|---|---|---|
| FunctionGemma (300 MB) | 24/40 | 15/40 | 1/6 | 11 | 0.8 s |
| Qwen3 30B | 38/40 | 36/40 | 6/6 | 2 | 2.2 s |
| Gemma 4 26B, thinking on (before the fix) | 2/40 | 2/40 | 0/6 | 38 | 10.2 s |
| Gemma 4 26B, thinking off | 40/40 | 38/40 | 6/6 | 0 | 5.4 s |

Gemma 4 spent its whole reply limit on hidden thinking and returned no tool call; `"think": False` in the request fixes it.
The earlier statement "about 30% correct, not usable" holds for FunctionGemma only. Gemma 4 26B is a large model, suited to
a PC or a car computer, not a phone. The fallback is still not attached to the voice agent and is not part of the benchmark
score. Result files: `project-log/runs/2026-09-30_local_fallback_eval_*_laptop*.json`.
"""
for p in ("project-log/SCORES.md", "README_FULL.md", "extension/README.md", "project-log/SLIDES_OUTLINE.md"):
    add(p, LONG)

add("project-log/WORKLOG.md", """## 2026-09-30, about 21:45 to 22:05 IST: SLURP run for the extension, fallback branch merged
- Merged the teammate's branch `extension-fallback-gemma4` (commit 9ebb0d5) after checking its four result files.
- Downloaded one shard of the SLURP test split (355 MB, Hugging Face mirror `marcel-gohsen/slurp`) to `~/theme5/slurp/`, outside the repo.
- Added `EXT_LIGHTS_FAIL_FIRST` to the home tools and a `session_start` line to the recovery log (for lining events up with the clip).
- Run 1 on 11 real recordings: 9 of 11, and it showed the no-repeat rule skipping a request whose earlier copy had been overridden. Fixed in `recovery.py`, tests pass, run 2: 10 of 11, 8 of 8 failures recovered. Both runs kept.
""")
