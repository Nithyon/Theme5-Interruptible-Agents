"""Turn devset/scenarios.jsonl into audio + the folder layout the FDB-v3 benchmark runner
expects, so we can reuse run_tool_benchmark_all_released.py on our own synthetic dev set
instead of the real 100 test recordings.

WRITE-ONLY DRAFT in this session: does not install Kokoro, does not synthesize anything, and
does not touch the fdb-env used by the benchmark. Install commands are in devset/README.md
(a separate ~/theme5/tts-env venv). Run this yourself once that's set up:

    source ~/theme5/tts-env/bin/activate
    python /mnt/d/Theme5-Interruptible-Agents/devset/make_audio.py --voices af_heart,am_adam

Output layout, matching run_tool_benchmark_all_released.py's discover_inputs_released()
(folder name must match r"^(.+)_([0-9a-f]{24})$" — everything up to the last 24-hex-char
group is the example_id):

    devset/audio/<scenario_id>_<24-hex-fake-speaker-id>/
        input.wav        # mono, 48kHz, 16-bit PCM — matches the benchmark's own input.wav
                          # format (channels=1, framerate=48000), verified by reading only
                          # the WAV header of one real benchmark file, never its content
        metadata.json     # {"id", "title", "domain", "expected_tool_calls": [...]} —
                          # per-folder metadata the runner merges in on top of (or instead
                          # of) benchmark_data_v2.json, so no FDB-v3 data file is needed

Audio construction, per scenario:
  1. Split the utterance on its disfluency markers: "[pause Ns]" becomes N seconds of real
     silence (not a TTS-generated pause); "um"/"uh"/"actually"/"no wait"/etc. are synthesized
     as their own short clips in the same voice, same as the rest of the sentence, so the
     realtime model sees/hears an actual filled pause, not just silence.
  2. Each text segment between markers is synthesized separately with Kokoro, then all
     segments (speech and real silence) are concatenated in order.
  3. The result is resampled to 48kHz mono 16-bit PCM (Kokoro's native output is 24kHz
     float32) and padded with ~1.5s of trailing silence, mirroring the benchmark's own
     "appended silence" convention (see BUILD_PLAN_FDB_V3.md's read of livekit_inference.py).
  4. Each scenario is rendered once per voice in --voices, so the same disfluency shows up in
     more than one speaker's prosody — same spirit as the real benchmark's 12 speakers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import List, Tuple

HERE = Path(__file__).resolve().parent
SCENARIOS_PATH = HERE / "scenarios.jsonl"
AUDIO_ROOT = HERE / "audio"

TARGET_RATE = 48000     # verified against one real benchmark input.wav header (mono, 48kHz)
TARGET_CHANNELS = 1
TRAILING_SILENCE_S = 1.5

_PAUSE_RE = re.compile(r"\[pause\s+([\d.]+)s\]", re.IGNORECASE)


def load_scenarios() -> List[dict]:
    scenarios = []
    with open(SCENARIOS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                scenarios.append(json.loads(line))
    return scenarios


def split_segments(utterance: str) -> List[Tuple[str, object]]:
    """Split an utterance into an ordered list of ("speech", text) and ("pause", seconds)
    segments, so the caller can synthesize speech and splice real silence separately."""
    segments: List[Tuple[str, object]] = []
    pos = 0
    for m in _PAUSE_RE.finditer(utterance):
        text = utterance[pos:m.start()].strip(" .,-")
        if text:
            segments.append(("speech", text))
        segments.append(("pause", float(m.group(1))))
        pos = m.end()
    tail = utterance[pos:].strip(" .,-")
    if tail:
        segments.append(("speech", tail))
    return segments


def fake_speaker_id(scenario_id: str, voice: str) -> str:
    """A deterministic 24-hex-char id (matching the released layout's folder-name regex),
    derived from the scenario id + voice so re-running this script is idempotent."""
    return hashlib.sha1(f"{scenario_id}:{voice}".encode()).hexdigest()[:24]


def synthesize_scenario(scenario: dict, voice: str, kokoro_pipeline) -> "object":
    """Render one scenario with one voice to a single mono float32 waveform at Kokoro's
    native rate, splicing real silence for [pause Ns] markers. Returns (waveform, sample_rate).
    Only called once Kokoro is actually installed and importable — see devset/README.md.
    """
    import numpy as np  # local import: only needed once this actually runs

    segments = split_segments(scenario["utterance"])
    chunks = []
    native_rate = None
    for kind, value in segments:
        if kind == "pause":
            sr = native_rate or 24000  # Kokoro's native rate; corrected once we know it
            chunks.append(np.zeros(int(sr * value), dtype=np.float32))
        else:
            # Kokoro's pipeline yields (graphemes, phonemes, audio) tuples per call.
            for _, _, audio in kokoro_pipeline(value, voice=voice):
                if native_rate is None:
                    native_rate = getattr(kokoro_pipeline, "sample_rate", 24000)
                chunks.append(np.asarray(audio, dtype=np.float32))
    if native_rate is None:
        native_rate = 24000
    # Re-render any pause chunks that were created before we knew the real native rate.
    fixed = []
    for (kind, value), chunk in zip(segments, chunks):
        if kind == "pause" and len(chunk) != int(native_rate * value):
            chunk = np.zeros(int(native_rate * value), dtype=np.float32)
        fixed.append(chunk)
    waveform = np.concatenate(fixed) if fixed else np.zeros(1, dtype=np.float32)
    waveform = np.concatenate([waveform, np.zeros(int(native_rate * TRAILING_SILENCE_S), dtype=np.float32)])
    return waveform, native_rate


def resample_and_write(waveform, src_rate: int, out_path: Path) -> None:
    """Resample to TARGET_RATE and write 16-bit PCM mono, matching the benchmark's own
    input.wav format (verified: mono, 48000 Hz — never inspected beyond the header)."""
    import numpy as np
    import soundfile as sf

    if src_rate != TARGET_RATE:
        import librosa  # only needed for resampling; installed alongside Kokoro
        waveform = librosa.resample(waveform, orig_sr=src_rate, target_sr=TARGET_RATE)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), waveform, TARGET_RATE, subtype="PCM_16")


def write_metadata(scenario: dict, out_dir: Path) -> None:
    """Per-folder metadata.json in the schema run_tool_benchmark.py's process_single()
    actually reads: item["title"] (required), item.get("domain", ...), and
    evaluate_pass_rate.py's scenario["expected_tool_calls"] = [{"function", "args"}, ...]
    (note: our own scenarios.jsonl calls this field "name" — translated to "function" here
    to match the harness's own key, verified by reading evaluate_pass_rate.py directly)."""
    expected_tool_calls = [{"function": c["name"], "args": c["args"]}
                            for c in scenario["expected_calls"]]
    meta = {
        "id": scenario["id"],
        "title": f"devset {scenario['id']}: {scenario['domain']} / level {scenario['level']}",
        "domain": scenario["domain"],
        "expected_tool_calls": expected_tool_calls,
        "must_not_call": scenario.get("must_not_call"),
        "disfluency": scenario.get("disfluency", []),
    }
    with open(out_dir / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--voices", default="af_heart,am_adam",
                    help="Comma-separated Kokoro voice ids to render each scenario with")
    ap.add_argument("--only", default=None,
                    help="Comma-separated scenario ids to render (default: all 50)")
    args = ap.parse_args()

    try:
        from kokoro import KPipeline  # noqa: F401
    except ImportError:
        sys.exit(
            "Kokoro isn't installed here. This script is meant to run inside the separate "
            "~/theme5/tts-env venv described in devset/README.md, not the benchmark's "
            "fdb-env. Install it there first, then re-run this script from that venv."
        )

    scenarios = load_scenarios()
    if args.only:
        wanted = set(args.only.split(","))
        scenarios = [s for s in scenarios if s["id"] in wanted]

    voices = [v.strip() for v in args.voices.split(",") if v.strip()]
    pipeline = KPipeline(lang_code="a")  # American English; see devset/README.md for options

    for scenario in scenarios:
        for voice in voices:
            speaker_id = fake_speaker_id(scenario["id"], voice)
            out_dir = AUDIO_ROOT / f"{scenario['id']}_{speaker_id}"
            waveform, native_rate = synthesize_scenario(scenario, voice, pipeline)
            resample_and_write(waveform, native_rate, out_dir / "input.wav")
            write_metadata(scenario, out_dir)
            print(f"wrote {out_dir}/input.wav ({voice})")


if __name__ == "__main__":
    main()
