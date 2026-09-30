"""Make one audio file of an extension end-to-end run: the recorded request clip and the
assistant's recorded reply are on the same time base, so adding them gives the whole
conversation as it happened. Also zips the submitted benchmark run's agent audio for Drive.
Usage (fdb-env): python ext_conversation.py"""
import glob
import os
import zipfile

import numpy as np
import soundfile as sf

ROOT = "/mnt/d/Theme5-Interruptible-Agents"
RUNS = f"{ROOT}/project-log/runs"


def load(path, rate):
    a, sr = sf.read(path, dtype="float32")
    if a.ndim > 1:
        a = a[:, 0]
    if sr != rate:
        n = int(len(a) * rate / sr)
        a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    return a


for pack, clipdir in (("car", "audio_car"), ("home", "audio")):
    run = f"{RUNS}/2026-09-30_ext_{pack}_e2e"
    clips = glob.glob(f"{ROOT}/extension/e2e/{clipdir}/*/input.wav")
    reply = f"{run}/agent_reply.wav"
    if not clips or not os.path.exists(reply):
        print(pack, ": missing files, skipped")
        continue
    rate = 24000
    user, agent = load(clips[0], rate), load(reply, rate)
    n = max(len(user), len(agent))
    mix = np.zeros(n, dtype=np.float32)
    mix[:len(user)] += user
    mix[:len(agent)] += agent
    peak = float(np.abs(mix).max()) or 1.0
    sf.write(f"{run}/conversation.wav", mix / max(1.0, peak), rate, subtype="PCM_16")
    print(f"{pack}: conversation.wav written, {n / rate:.0f} s (request clip {len(user) / rate:.0f} s, reply track {len(agent) / rate:.0f} s)")

D = os.path.expanduser("~/theme5/Full-Duplex-Bench/v3/fdb_v3_data_released")
A = f"{ROOT}/logs-audio"
os.makedirs(A, exist_ok=True)
for prov in ("gate_gemini38_v2b",):
    files = sorted(glob.glob(f"{D}/*/output_{prov}.wav"))
    out = f"{A}/agent_audio_{prov}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as z:
        for f in files:
            z.write(f, os.path.relpath(f, D))
    print(prov, len(files), "audio files zipped,", round(os.path.getsize(out) / 1e6), "MB")
