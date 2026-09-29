"""Duration and trailing-silence length of input WAVs (header + amplitude only, no content)."""
import glob, sys, wave, audioop, statistics
def info(p):
    w = wave.open(p); n = w.getnframes(); sr = w.getframerate(); sw = w.getsampwidth()
    data = w.readframes(n); step = int(sr * 0.05) * sw * w.getnchannels()
    last_voice = 0
    for i in range(0, len(data), step):
        if audioop.rms(data[i:i+step], sw) > 300: last_voice = i
    dur = n / sr; tail = dur - last_voice / (sw * w.getnchannels()) / sr
    return dur, tail
for pat in sys.argv[1:]:
    files = sorted(glob.glob(pat))[:40]
    d = [info(p) for p in files]
    print(pat.split('/')[-3] if 'audio' in pat else 'benchmark', f"n={len(d)} | duration median {statistics.median(x[0] for x in d):.1f}s | silence after last speech median {statistics.median(x[1] for x in d):.1f}s, min {min(x[1] for x in d):.1f}s")
