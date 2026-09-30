"""Build one "conversation" for the home assistant out of REAL recordings from the SLURP test
set (Bastianelli et al., EMNLP 2020; audio licence CC BY-NC 4.0), so the extension can be run
on human speech the same way the benchmark plays its recordings.

Selection rule (fixed, no listening, no hand-picking): from one shard of the SLURP test split,
light-control intents only, close-talk (headset) recordings only, one recording per distinct
sentence, in file order, until each intent's quota is full. The recordings are not edited apart
from resampling to 48 kHz and scaling to a common peak; silence is left between them for the
assistant to act and answer.

Run in the fdb-env:  python extension/e2e/make_clip_slurp.py ~/theme5/slurp/test-00000.parquet
"""
import hashlib, io, json, sys
from pathlib import Path

import librosa
import numpy as np
import pyarrow.parquet as pq
import soundfile as sf

HERE = Path(__file__).resolve().parent
QUOTA = {"iot_hue_lightoff": 5, "iot_hue_lighton": 3, "iot_hue_lightdim": 2, "iot_hue_lightup": 2}
RATE, LEAD_S, GAP_S, PEAK = 48000, 2.0, 11.0, 0.8

table = pq.ParquetFile(sys.argv[1])
picked, seen, left = [], set(), dict(QUOTA)
for batch in table.iter_batches(batch_size=64):
    for row in batch.to_pylist():
        intent, path = row["intent"], (row["audio"]["path"] or "")
        if left.get(intent, 0) <= 0 or "headset" not in path or row["id"] in seen:
            continue
        seen.add(row["id"]); left[intent] -= 1; picked.append(row)
    if not any(left.values()):
        break
order = list(QUOTA)  # interleave intents so the same kind of request does not come in a block
picked.sort(key=lambda r: order.index(r["intent"]))
by = {k: [r for r in picked if r["intent"] == k] for k in order}
lines = []
while any(by.values()):
    for k in order:
        if by[k]:
            lines.append(by[k].pop(0))

chunks, meta, t = [np.zeros(int(RATE * LEAD_S), dtype=np.float32)], [], LEAD_S
for r in lines:
    wave, sr = sf.read(io.BytesIO(r["audio"]["bytes"]), dtype="float32", always_2d=False)
    if wave.ndim > 1:
        wave = wave.mean(axis=1)
    wave = librosa.resample(wave, orig_sr=sr, target_sr=RATE)
    wave = wave * (PEAK / max(float(np.abs(wave).max()), 1e-6))
    dur = len(wave) / RATE
    meta.append({"slurp_id": r["id"], "file": r["audio"]["path"], "transcript": r["transcript"],
                 "intent": r["intent"], "slots": list(r.get("slots:") or []),
                 "offset_s": round(t, 2), "duration_s": round(dur, 2)})
    chunks += [wave.astype(np.float32), np.zeros(int(RATE * GAP_S), dtype=np.float32)]
    t += dur + GAP_S

sid = hashlib.sha1(b"slurp01").hexdigest()[:24]
out = HERE / "audio_slurp" / f"slurp01_{sid}"
out.mkdir(parents=True, exist_ok=True)
sf.write(str(out / "input.wav"), np.concatenate(chunks), RATE, subtype="PCM_16")
json.dump({"id": "slurp01", "title": f"extension on real speech: {len(meta)} SLURP test recordings, light control",
           "domain": "home", "expected_tool_calls": [],
           "source": "SLURP test split (Bastianelli et al., EMNLP 2020), audio CC BY-NC 4.0",
           "selection": "headset recordings, one per sentence, file order, quotas " + json.dumps(QUOTA),
           "lines": meta}, open(out / "metadata.json", "w", encoding="utf-8"), indent=2)
print("wrote", out, f"({t:.0f} s, {len(meta)} recordings)")
for m in meta:
    print(f"  {m['offset_s']:6.1f}s  {m['intent']:18s} {m['transcript']!r}  [{m['file']}]")
