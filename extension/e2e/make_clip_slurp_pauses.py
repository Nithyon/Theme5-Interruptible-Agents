"""Same 11 real SLURP recordings as make_clip_slurp.py, but each one gets a silence of irregular
length (1.5 to 4.0 s, fixed seed) inserted INSIDE the request, at its longest gap between words, so the
speaker seems to stop mid-sentence and then carry on ("turn off the ... <3 s> ... porch light").

The speech is real (SLURP test set, Bastianelli et al., EMNLP 2020, audio CC BY-NC 4.0); the pauses are
inserted by us. The gap is found by frame energy (20 ms frames), not by listening. metadata.json records
where each pause went and how long it is, and when the request really ends, so an action taken before
the end can be counted as premature.

Run in the fdb-env:  python extension/e2e/make_clip_slurp_pauses.py ~/theme5/slurp/test-00000.parquet
"""
import hashlib, io, json, random, sys
from pathlib import Path

import librosa
import numpy as np
import pyarrow.parquet as pq
import soundfile as sf

HERE = Path(__file__).resolve().parent
RATE, LEAD_S, GAP_S, PEAK, FRAME = 48000, 2.0, 11.0, 0.8, 0.02
src = json.load(open(next((HERE / "audio_slurp").glob("slurp01_*/metadata.json")), encoding="utf-8"))
want = {m["file"] for m in src["lines"]}
rows = {}
for b in pq.ParquetFile(sys.argv[1]).iter_batches(batch_size=64):
    for r in b.to_pylist():
        if r["audio"]["path"] in want and r["audio"]["path"] not in rows:
            rows[r["audio"]["path"]] = r
    if len(rows) == len(want):
        break
rng = random.Random(7)


def split_point(w):
    """Middle of the longest quiet run between the first and last speech frames."""
    n = int(RATE * FRAME)
    e = np.array([np.sqrt(np.mean(w[i:i + n] ** 2)) for i in range(0, len(w) - n, n)])
    speech = e > 0.1 * e.max()
    idx = np.flatnonzero(speech)
    lo, hi = idx[0] + 8, idx[-1] - 8  # keep at least 160 ms of speech on both sides
    best, run, start = (0, (lo + hi) // 2), 0, None
    for i in range(lo, hi):
        if not speech[i]:
            start = i if run == 0 else start; run += 1
            if run > best[0]:
                best = (run, start + run // 2)
        else:
            run = 0
    if best[0] < 3:  # no clear gap: take the quietest frame in the middle half
        mid = range(lo + (hi - lo) // 4, hi - (hi - lo) // 4)
        best = (0, min(mid, key=lambda i: e[i]))
    return best[1] * n, best[0] * FRAME


chunks, meta, t = [np.zeros(int(RATE * LEAD_S), dtype=np.float32)], [], LEAD_S
for m in src["lines"]:
    r = rows[m["file"]]
    w, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32", always_2d=False)
    w = w.mean(axis=1) if w.ndim > 1 else w
    w = librosa.resample(w, orig_sr=sr, target_sr=RATE)
    w = w * (PEAK / max(float(np.abs(w).max()), 1e-6))
    cut, gap = split_point(w)
    pause = round(rng.uniform(1.5, 4.0), 2)
    w2 = np.concatenate([w[:cut], np.zeros(int(RATE * pause), dtype=np.float32), w[cut:]])
    dur = len(w2) / RATE
    meta.append({**{k: m[k] for k in ("slurp_id", "file", "transcript", "intent", "slots")},
                 "offset_s": round(t, 2), "pause_at_s": round(t + cut / RATE, 2), "pause_len_s": pause,
                 "natural_gap_s": round(gap, 2), "speech_end_s": round(t + dur, 2), "duration_s": round(dur, 2)})
    chunks += [w2.astype(np.float32), np.zeros(int(RATE * GAP_S), dtype=np.float32)]
    t += dur + GAP_S

out = HERE / "audio_slurp_pauses" / f"slurppause01_{hashlib.sha1(b'slurppause01').hexdigest()[:24]}"
out.mkdir(parents=True, exist_ok=True)
sf.write(str(out / "input.wav"), np.concatenate(chunks), RATE, subtype="PCM_16")
json.dump({"id": "slurppause01", "title": "extension on real speech with inserted mid-request pauses (SLURP)",
           "domain": "home", "expected_tool_calls": [],
           "source": "SLURP test split (Bastianelli et al., EMNLP 2020), audio CC BY-NC 4.0; pauses inserted by us",
           "lines": meta}, open(out / "metadata.json", "w", encoding="utf-8"), indent=2)
print("wrote", out, f"({t:.0f} s)")
for x in meta:
    print(f"  {x['offset_s']:6.1f}s pause {x['pause_len_s']:.2f}s at +{x['pause_at_s'] - x['offset_s']:.2f}s "
          f"(natural gap {x['natural_gap_s']:.2f}s)  {x['transcript']!r}")
