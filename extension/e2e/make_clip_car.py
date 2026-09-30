"""Recorded "conversation" for the in-car EV assistant (the headline extension scenario), built
the same way as make_clip.py: our own lines, synthetic voice, gaps left for the assistant.
Run in the tts-env:  python extension/e2e/make_clip_car.py"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "devset"))
from make_audio import fake_speaker_id, resample_and_write, synthesize_scenario  # noqa: E402

VOICE = "am_adam"
LINES = [  # (what the driver says, seconds of silence left for the assistant)
    ("Reroute to the mall, no, sorry, the airport.", 10),            # correction: one reroute
    ("Check the traffic on my route.", 17),                          # slow tool: progress line
    ("Find me a charging station near downtown, CCS connector.", 15),  # flaky tool: quiet retries
    ("Book that station for 6 pm.", 12),                             # state change
    ("Book it again.", 10),                                          # same booking, no duplicate
    ("Actually, make it 7 pm instead.", 14),                         # undo: cancel 6 pm, then book 7 pm
    ("Call roadside assistance, I have a flat tire.", 19),           # service down: failure
    ("Please try roadside assistance again.", 26),                   # second failure: hand-off
]
scenario = {"id": "car01", "utterance": " ".join(f"{t} [pause {p}s]" for t, p in LINES)}

from kokoro import KPipeline  # noqa: E402
wave, rate = synthesize_scenario(scenario, VOICE, KPipeline(lang_code="a"))
out = HERE / "audio_car" / f"car01_{fake_speaker_id('car01', VOICE)}"
resample_and_write(wave, rate, out / "input.wav")
json.dump({"id": "car01", "title": "extension end-to-end: in-car EV assistant, 8 spoken lines", "domain": "car",
           "expected_tool_calls": [], "lines": [t for t, _ in LINES]},
          open(out / "metadata.json", "w", encoding="utf-8"), indent=2)
print("wrote", out, f"({len(wave) / rate:.0f} s)")
