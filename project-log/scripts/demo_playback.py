"""Replay a recorded practice run end to end: the request audio, the agent's recorded reply,
the tool calls that ran and the harness's decision trail. Nothing is run live; every file is
from a real run of our agent on our own practice lines (the request voice is synthetic).
Usage: demo_playback.py <1|2|3>   (DRY=1 prints without playing sound)"""
import glob, json, os, sys, time
import numpy as np, soundfile as sf

ROOT = "/mnt/d/Theme5-Interruptible-Agents"
DRY = os.getenv("DRY", "0") == "1"
CASES = {
    "1": ("s31", ["D"], "A correction: only the corrected order is tracked"),
    "2": ("p11", ["D", "E"], "A withdrawal: 29 Sep agent (run D) vs 30 Sep agent (run E)"),
    "3": ("s06", ["D", "E"], "Three requests with an ID: 29 Sep agent (run D) vs 30 Sep agent (run E)"),
}
LABEL = {"D": "29 Sep settings", "E": "30 Sep settings"}


def segments(path):
    """Voiced stretches of a recording, so long silences between them are skipped."""
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1: a = a[:, 0]
    win = int(0.05 * sr)
    loud = [i for i in range(0, len(a) - win, win) if np.abs(a[i:i + win]).max() > 0.01]
    segs = []
    for i in loud:
        if segs and i - segs[-1][1] <= int(0.8 * sr): segs[-1][1] = i + win
        else: segs.append([i, i + win])
    return [a[max(0, s0 - int(0.1 * sr)): s1 + int(0.2 * sr)] for s0, s1 in segs], sr


def play(path, what):
    segs, sr = segments(path)
    total = sum(len(x) for x in segs) / sr
    print(f"   [playing {what}: {total:.1f} s of speech in {len(segs)} part(s)]", flush=True)
    if DRY: return
    import sounddevice as sd
    for x in segs:
        sd.play(x, sr); sd.wait(); time.sleep(0.4)


def trail(run, room):
    p = f"{ROOT}/project-log/runs/2026-09-{'29' if run != 'E' else '30'}_dev_dev_gate_gemini38_{run}/gate_events.log"
    if not os.path.exists(p): return None
    for line in open(p):
        d = json.loads(line)
        if d.get("room") == room: return d["events"]
    return None


sid, runs, title = CASES[sys.argv[1] if len(sys.argv) > 1 else "1"]
d = glob.glob(f"{ROOT}/devset/audio/{sid}_*")[0]
first = json.load(open(f"{d}/result_dev_gate_gemini38_{runs[0]}.json"))
print("=" * 78); print(title); print("=" * 78)
print("Our own practice line, read by a synthetic voice (not a benchmark recording).")
print(f"\nUSER : {first.get('input_transcript')}")
play(f"{d}/input.wav", "the request")
for run in runs:
    r = json.load(open(f"{d}/result_dev_gate_gemini38_{run}.json"))
    print(f"\n--- {LABEL[run]} ---")
    print(f"AGENT: {r.get('transcript')}")
    play(f"{d}/output_dev_gate_gemini38_{run}.wav", "the agent's recorded reply")
    print("TOOL CALLS THAT RAN:")
    for c in r.get("actual_tool_calls") or []:
        print(f"   {c.get('function')}({json.dumps(c.get('args'))})   at {c.get('timestamp_start')} s")
    if not r.get("actual_tool_calls"): print("   (none)")
    print(f"TIMELINE: user stopped speaking at {r.get('user_speech_end_rel')} s, agent started speaking at {r.get('audio_agent_speech_start')} s")
    ev = trail(run, r.get("room_name"))
    if ev is None:
        print("DECISION LOG: not available for this recording")
    else:
        print("DECISION LOG (the harness, in order):")
        t0 = ev[0]["t"] if ev else 0
        for e in ev:
            if e["kind"] in ("proposed", "same_tool_again", "superseded", "cancelled", "retracted", "duplicate", "execute", "jev_turn"):
                rest = {k: v for k, v in e.items() if k not in ("t", "kind")}
                print(f"   +{e['t'] - t0:5.1f} s  {e['kind']:16} {json.dumps(rest)[:110]}")
