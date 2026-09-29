"""Generate the instant-acknowledgement clip (run once, in ~/theme5/tts-env).
Writes fdb_agent/assets/ack.wav: 24 kHz mono 16-bit, neutral words only."""
from pathlib import Path
import numpy as np, soundfile as sf
from kokoro import KPipeline

TEXT = "Sure, one moment."
out = Path(__file__).resolve().parent / "assets" / "ack.wav"
out.parent.mkdir(exist_ok=True)
pipe = KPipeline(lang_code="a")
audio = np.concatenate([np.asarray(a) for _, _, a in pipe(TEXT, voice="af_heart")])
sf.write(out, audio, 24000, subtype="PCM_16")
print("wrote", out, f"{len(audio)/24000:.2f}s")
