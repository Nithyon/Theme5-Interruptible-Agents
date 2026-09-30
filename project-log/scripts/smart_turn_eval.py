"""Offline check of Smart Turn v3.2 on real human speech: the CANDOR subsets of
Full-Duplex-Bench v1.0 (Lin et al., arXiv 2503.04721; data from the authors' Drive).

  candor_pause_handling (216 clips): annotated mid-turn pauses  -> correct = "not finished"
  candor_turn_taking    (119 clips): annotated turn ends        -> correct = "finished"

At each annotated point the model gets the audio up to the start of the silence plus TAIL_S
of that silence (as a VAD would hand it over), last 8 s. Threshold = the model's default 0.5;
nothing is tuned. Not FDB-v3 data.
Usage: python smart_turn_eval.py <fdb_v1_data dir> <out.json>
"""
import json, os, sys, time
import numpy as np
import soundfile as sf

sys.path.insert(0, "/mnt/d/Theme5-Interruptible-Agents/fdb_agent")
from smart_turn import SmartTurn, SR

TAIL_S = float(os.getenv("TAIL_S", "0.2"))
root, out = sys.argv[1], sys.argv[2]
m = SmartTurn()


def load(path):
    a, sr = sf.read(path, dtype="float32", always_2d=True)
    a = a.mean(axis=1)
    if sr != SR:
        import librosa
        a = librosa.resample(a, orig_sr=sr, target_sr=SR)
    return a


def run(task, fname, want_complete):
    rows, ms = [], []
    d = os.path.join(root, task)
    for clip in sorted(os.listdir(d), key=lambda x: int(x) if x.isdigit() else 0):
        jp, wp = os.path.join(d, clip, fname), os.path.join(d, clip, "input.wav")
        if not (os.path.exists(jp) and os.path.exists(wp)):
            continue
        a = load(wp)
        for ev in json.load(open(jp)):
            t0, t1 = ev["timestamp"]
            end = min(t0 + TAIL_S, t1) if (t1 > t0 and os.getenv("CAP", "1") == "1") else t0 + TAIL_S
            seg = a[: int(end * SR)]
            if len(seg) < SR // 2:
                continue
            s = time.perf_counter()
            p = m.predict(seg)
            ms.append((time.perf_counter() - s) * 1000)
            rows.append({"clip": clip, "t": round(t0, 2), "gap_s": round(t1 - t0, 2), "p_complete": round(p, 4),
                         "correct": (p > 0.5) == want_complete})
    return rows, ms


res = {}
allms = []
for task, fname, want in (("candor_pause_handling", "pause.json", False),
                          ("candor_turn_taking", "turn_taking.json", True)):
    rows, ms = run(task, fname, want)
    allms += ms
    n, ok = len(rows), sum(r["correct"] for r in rows)
    res[task] = {"points": n, "clips": len({r["clip"] for r in rows}), "correct": ok,
                 "accuracy": round(ok / n, 4) if n else None,
                 "mean_p_complete": round(float(np.mean([r["p_complete"] for r in rows])), 4) if n else None,
                 "rows": rows}
    print(f"{task}: {ok}/{n} correct = {ok / max(n, 1):.3f}  (clips {res[task]['clips']}, mean p_complete {res[task]['mean_p_complete']})")
tot = sum(v["points"] for v in res.values()); okt = sum(v["correct"] for v in res.values())
bal = float(np.mean([v["accuracy"] for v in res.values()]))
res["summary"] = {"tail_s": TAIL_S, "threshold": 0.5, "points": tot, "accuracy": round(okt / tot, 4),
                  "balanced_accuracy": round(bal, 4),
                  "latency_ms_median": round(float(np.median(allms)), 1),
                  "latency_ms_p95": round(float(np.percentile(allms, 95)), 1)}
print(json.dumps(res["summary"]))
json.dump(res, open(out, "w"), indent=1)
