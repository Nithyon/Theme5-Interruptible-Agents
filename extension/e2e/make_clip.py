"""Build one recorded "conversation" for the home assistant so the extension can be run end to
end the same way the benchmark runs an agent: a wav is streamed into a LiveKit room, the
agent answers in the gaps, and its audio is recorded. The voice is synthetic (Kokoro); the
lines are our own. Run in the tts-env:  python extension/e2e/make_clip.py"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "devset"))
from make_audio import fake_speaker_id, resample_and_write, synthesize_scenario  # noqa: E402

VOICE = "af_heart"
LINES = [  # (what the user says, seconds of silence left for the assistant to act and answer)
    ("Set the living room AC to 24, no, 22.", 10),
    ("How much energy have I used today?", 15),
    ("Find my phone.", 13),
    ("Start the washer on cotton.", 10),
    ("Start it again.", 10),
    ("Actually, make it eco.", 12),
    ("The washer is leaking, call the service centre.", 16),
    ("Please try the service centre again.", 18),
]
scenario = {"id": "home01", "utterance": " ".join(f"{t} [pause {p}s]" for t, p in LINES)}

from kokoro import KPipeline  # noqa: E402
wave, rate = synthesize_scenario(scenario, VOICE, KPipeline(lang_code="a"))
out = HERE / "audio" / f"home01_{fake_speaker_id('home01', VOICE)}"
resample_and_write(wave, rate, out / "input.wav")
json.dump({"id": "home01", "title": "extension end-to-end: home assistant, 8 spoken lines", "domain": "home",
           "expected_tool_calls": [], "lines": [t for t, _ in LINES]},
          open(out / "metadata.json", "w", encoding="utf-8"), indent=2)
print("wrote", out, f"({len(wave) / rate:.0f} s)")
