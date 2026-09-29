""""Stay responsive" layer (participant guide: "meaningful spoken feedback within a few
hundred milliseconds, no dead air, no false 'done!' claims").

R1 instant acknowledgement (GATE_ACK=1): when the commit gate decides the user has really
   finished (Jev says complete and the rules see no hesitation), play a short pre-recorded
   neutral clip ("Sure, one moment.") at once, unless the agent is already speaking. It is
   pre-recorded because asking the realtime model to speak takes as long as its own reply.
   It never contains result words ("done", "booked"), so it can't be a false completion.
R2 must-speak watchdog (GATE_WATCHDOG=1): if a tool result came back and the agent hasn't
   started speaking within WATCHDOG_S, ask the model to state the result now.

Both are off by default. Decisions are written to the gate's event log.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import wave
from pathlib import Path

log = logging.getLogger("responsive")

ACK_TEXT = "Sure, one moment."
ACK_PATH = Path(__file__).resolve().parent / "assets" / "ack.wav"
WATCHDOG_S = float(os.getenv("GATE_WATCHDOG_S", "2.5"))


def _load_frames(path: Path, frame_ms: int = 20):
    from livekit import rtc
    with wave.open(str(path)) as w:
        sr, ch, data = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
    step = int(sr * frame_ms / 1000) * 2 * ch
    frames = []
    for i in range(0, len(data), step):
        chunk = data[i:i + step]
        if len(chunk) < step:
            chunk += b"\x00" * (step - len(chunk))
        frames.append(rtc.AudioFrame(data=chunk, sample_rate=sr, num_channels=ch,
                                     samples_per_channel=len(chunk) // (2 * ch)))
    return frames


class Responsiveness:
    def __init__(self, session, gate, ack: bool, watchdog: bool):
        self.session, self.gate = session, gate
        self.agent_speaking = False
        self.last_agent_speech = 0.0
        self.acked = 0
        self._frames = _load_frames(ACK_PATH) if ack and ACK_PATH.exists() else None
        if ack and self._frames is None:
            log.warning("GATE_ACK=1 but %s is missing; acknowledgements disabled", ACK_PATH)
        if self._frames is not None:
            gate.on_turn_done = self.acknowledge
        if watchdog:
            gate.on_tool_done = self.tool_done

    def on_agent_state(self, state: str) -> None:
        self.agent_speaking = state == "speaking"
        if self.agent_speaking:
            self.last_agent_speech = time.monotonic()

    def acknowledge(self) -> None:
        if self.agent_speaking:
            self.gate._event("ack_skipped", reason="agent already speaking")
            return

        async def frames():
            for f in self._frames:
                yield f

        self.acked += 1
        self.gate._event("ack", text=ACK_TEXT)
        self.session.say(ACK_TEXT, audio=frames(), allow_interruptions=True, add_to_chat_ctx=False)

    def tool_done(self, name: str) -> None:
        t0 = time.monotonic()

        async def watch():
            await asyncio.sleep(WATCHDOG_S)
            if self.agent_speaking or self.last_agent_speech > t0:
                return
            self.gate._event("watchdog", tool=name)
            self.session.generate_reply(
                instructions="Tell the user the result of the tool you just used now, key facts first, in one short sentence.")

        asyncio.get_running_loop().create_task(watch())
