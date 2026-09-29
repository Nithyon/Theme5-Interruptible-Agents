"""Pad dev-set input.wav files with trailing silence so the benchmark's recording window
(= input duration) leaves the agent as much time after the user stops as the real FDB-v3
recordings do (~40-59 s files, agent answers ~15-25 s in). Idempotent: skips padded files."""
import glob, sys, wave
PAD_S = float(sys.argv[1]) if len(sys.argv) > 1 else 20.0
n = 0
for p in sorted(glob.glob("/mnt/d/Theme5-Interruptible-Agents/devset/audio/*/input.wav")):
    w = wave.open(p); params = w.getparams(); frames = w.readframes(w.getnframes()); w.close()
    dur = params.nframes / params.framerate
    if dur > 20:                      # already padded
        continue
    pad = b"\x00" * int(PAD_S * params.framerate) * params.sampwidth * params.nchannels
    o = wave.open(p, "wb"); o.setparams(params); o.writeframes(frames + pad); o.close(); n += 1
print(f"padded {n} files with {PAD_S:.0f}s of trailing silence")
