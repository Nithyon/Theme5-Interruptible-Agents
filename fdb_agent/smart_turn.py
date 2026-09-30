"""Smart Turn v3.2 (pipecat-ai, BSD-2) as the gate's optional acoustic decider.

The rules read the user's words and Jev reads their meaning; neither hears the voice. Smart
Turn listens to the last 8 s of the user's audio and returns the probability that the turn
is complete, from tone and pace ("Book a flight to Chicago…" said with a level, unfinished
pitch). It runs locally on CPU (8 MB ONNX, about 10–60 ms), so it adds no API cost.

Off by default (GATE_SMART_TURN=1 enables). It can only lengthen a hold up to the rules'
hesitant window; any error returns None and the gate behaves as if it were absent.
Not yet validated on real voices — see project-log/RESEARCH_SMART_TURN.md.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Optional

import numpy as np

log = logging.getLogger("smart_turn")

SR = 16000
WINDOW_S = 8
REPO = "pipecat-ai/smart-turn-v3"
FILENAME = os.getenv("SMART_TURN_FILE", "smart-turn-v3.2-cpu.onnx")
DONE_P = float(os.getenv("SMART_TURN_DONE_P", "0.5"))      # the model's own default threshold


def last_window(audio: np.ndarray) -> np.ndarray:
    """Last 8 s of audio, zero-padded at the start when shorter (as in the reference code)."""
    n = WINDOW_S * SR
    audio = audio[-n:]
    if len(audio) < n:
        audio = np.concatenate([np.zeros(n - len(audio), dtype=np.float32), audio])
    return audio.astype(np.float32)


class SmartTurn:
    def __init__(self, path: Optional[str] = None):
        import onnxruntime as ort
        from transformers import WhisperFeatureExtractor
        if path is None:
            from huggingface_hub import hf_hub_download
            path = hf_hub_download(REPO, FILENAME)
        so = ort.SessionOptions()
        so.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        so.inter_op_num_threads = 1
        so.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(path, sess_options=so)
        self._fx = WhisperFeatureExtractor(chunk_length=WINDOW_S)
        self.stats = {"calls": 0, "errors": 0, "ms_total": 0}

    def predict(self, audio: np.ndarray) -> float:
        """Probability that the speaker has finished their turn. audio: float32 mono 16 kHz."""
        feats = self._fx(last_window(audio), sampling_rate=SR, return_tensors="np",
                         padding="max_length", max_length=WINDOW_S * SR, truncation=True,
                         do_normalize=True).input_features.astype(np.float32)
        return float(self._session.run(None, {"input_features": feats})[0].reshape(-1)[0])


class AudioTap:
    """Rolling buffer of the user's most recent audio (16 kHz mono float32)."""

    def __init__(self):
        self._chunks: list = []
        self._n = 0

    def push_int16(self, pcm: np.ndarray) -> None:
        self._chunks.append(pcm.astype(np.float32) / 32768.0)
        self._n += len(pcm)
        while self._n - len(self._chunks[0]) >= WINDOW_S * SR:
            self._n -= len(self._chunks.pop(0))

    def snapshot(self) -> np.ndarray:
        return np.concatenate(self._chunks) if self._chunks else np.zeros(0, dtype=np.float32)


class AcousticJudge:
    """What the gate talks to: `await complete_probability()` -> float, or None on any failure."""

    def __init__(self, model: SmartTurn, tap: AudioTap):
        self.model, self.tap = model, tap

    @property
    def stats(self):
        return self.model.stats

    async def complete_probability(self) -> Optional[float]:
        audio = self.tap.snapshot()
        if len(audio) < SR // 2:                       # under half a second: nothing to judge
            return None
        self.model.stats["calls"] += 1
        t0 = time.monotonic()
        try:
            p = await asyncio.get_running_loop().run_in_executor(None, self.model.predict, audio)
            self.model.stats["ms_total"] += int((time.monotonic() - t0) * 1000)
            return p
        except Exception as e:
            self.model.stats["errors"] += 1
            log.warning("smart turn failed: %s", type(e).__name__)
            return None


def make_acoustic_judge() -> Optional[AcousticJudge]:
    if os.getenv("GATE_SMART_TURN", "0") != "1":
        return None
    try:
        return AcousticJudge(SmartTurn(os.getenv("SMART_TURN_PATH") or None), AudioTap())
    except Exception as e:
        log.warning("Smart Turn disabled: %s", e)
        return None


def feed_from_room(room, tap: AudioTap) -> None:
    """Copy the user's microphone track into the tap. Gemini still receives the audio
    through the session as before; this is a second, read-only listener."""
    from livekit import rtc

    async def pump(track):
        stream = rtc.AudioStream(track, sample_rate=SR, num_channels=1)
        try:
            async for ev in stream:
                tap.push_int16(np.frombuffer(ev.frame.data, dtype=np.int16))
        finally:
            await stream.aclose()

    tasks = []

    def on_track(track, *_):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            tasks.append(asyncio.create_task(pump(track)))

    room.on("track_subscribed", on_track)
    for p in room.remote_participants.values():
        for pub in p.track_publications.values():
            if pub.track is not None:
                on_track(pub.track)
