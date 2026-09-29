"""TypeSafe Jev as the commit gate's decision layer (optional; rules are the fallback).

Two typed questions, each answered with a label plus probabilities:
  * turn state: has the user finished their request, or paused mid-thought / about to
    correct themselves? Decides how long the gate holds a proposed tool call.
  * follow-up: when the same tool is proposed again after more user speech, is that a
    correction (replace the held call), an addition (keep both) or unrelated?

Jev never sees audio and never builds tool arguments; the voice model does that. Every
call has a hard timeout, and any error or timeout returns None so the gate falls back to
its rule-based behaviour. Enabled when TYPESAFE_API_KEY is set and GATE_JEV != "0".
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Dict, Optional

log = logging.getLogger("jev")

TIMEOUT_S = float(os.getenv("JEV_TIMEOUT_S", "0.8"))

TURN_Q = {
    "complete": "The user has finished their request; nothing more is coming.",
    "continuing": "The user paused mid-thought, is hesitating, or is about to add or "
                  "correct something (e.g. trailing 'um', 'and', 'to…', 'no wait').",
}
FOLLOWUP_Q = {
    "correction": "The later request replaces the earlier one: the user changed their "
                  "mind or fixed a detail (e.g. 'Boston… no, New York').",
    "addition": "The user wants both: a second, separate request of the same kind "
                "(e.g. 'track order A1 and also B2').",
    "retraction": "The user withdrew the earlier request (e.g. 'don't book it, just "
                  "search…'); the earlier call must not run.",
    "unrelated": "Neither: the later call is not about the earlier one.",
}


class JevJudge:
    def __init__(self, client=None):
        from typesafe_sdk import AsyncTypeSafeClient, Choice
        self._Choice = Choice
        self._client = client or AsyncTypeSafeClient()
        self.stats = {"calls": 0, "ok": 0, "timeouts": 0, "errors": 0, "ms_total": 0}

    async def _ask(self, state: Dict[str, Any], name: str, instructions: str,
                   criteria: Dict[str, str]) -> Optional[Dict[str, float]]:
        self.stats["calls"] += 1
        t0 = time.monotonic()
        try:
            resp = await asyncio.wait_for(
                self._client.system_one(
                    state=state,
                    questions={name: self._Choice(instructions=instructions, criteria=criteria)},
                    timeout=TIMEOUT_S),
                timeout=TIMEOUT_S + 0.1)
            ans = resp.choices[name]
            self.stats["ok"] += 1
            self.stats["ms_total"] += int((time.monotonic() - t0) * 1000)
            return dict(ans.probabilities or {ans.choice: 1.0})
        except asyncio.TimeoutError:
            self.stats["timeouts"] += 1
        except Exception as e:                      # network, auth, rate limit…
            self.stats["errors"] += 1
            log.warning("jev %s failed: %s", name, type(e).__name__)
        return None

    async def turn_state(self, transcript: str) -> Optional[Dict[str, float]]:
        return await self._ask(
            {"user_said_so_far": transcript},
            "turn_state",
            "A voice assistant must decide whether to act now. Judge only from what the "
            "user has said so far in this turn.",
            TURN_Q)

    async def followup(self, earlier_call: Dict[str, Any], later_call: Dict[str, Any],
                       said_between: str) -> Optional[Dict[str, float]]:
        return await self._ask(
            {"earlier_call": earlier_call, "later_call": later_call,
             "user_said_between_the_calls": said_between},
            "followup",
            "The voice assistant proposed the same tool twice. How does the later call "
            "relate to the earlier one?",
            FOLLOWUP_Q)


def make_judge() -> Optional[JevJudge]:
    if os.getenv("GATE_JEV", "1") == "0" or not os.getenv("TYPESAFE_API_KEY"):
        return None
    try:
        return JevJudge()
    except Exception as e:
        log.warning("Jev disabled: %s", e)
        return None
