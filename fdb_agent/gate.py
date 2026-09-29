"""Commit gate: tool calls run only once the user's turn has settled.

A realtime model often calls a tool at the first pause, before the user finishes a
self-correction ("Boston… no, New York"). FDB-v3 counts every executed call, so that
early call fails the scenario even if the right call follows. The gate holds each
proposed call until the user has been quiet for a short window, drops a held call
when a newer call to the same tool arrives after further user speech (a correction),
and never executes an identical call twice.

Every call the gate lets through is executed and logged by the benchmark's own tool
code; held or superseded calls are never executed, so nothing is hidden.
"""
from __future__ import annotations

import asyncio
import functools
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

log = logging.getLogger("commit_gate")

QUIET_S = 0.9        # user silence needed before a held call may run
HESITANT_QUIET_S = 1.8   # silence needed when the user's last words signal more is coming
MAX_HOLD_S = 8.0     # never hold a call longer than this
POLL_S = 0.05

# Trailing words that usually mean the user hasn't finished (a filler, or the start of
# a self-correction), so a pause after them is a thinking pause, not the end of the turn.
_HESITANT_TAILS = ("um", "uh", "er", "erm", "hmm", "wait", "no", "actually", "sorry",
                   "i mean", "or", "and", "but", "like", "so", "make that", "scratch that")


def ends_hesitantly(text: str) -> bool:
    words = "".join(c if c.isalnum() or c in " '" else " " for c in text.lower()).split()
    tail = " ".join(words[-2:])
    return bool(words) and (words[-1] in _HESITANT_TAILS or tail in _HESITANT_TAILS)


def _canon(args: Dict[str, Any]) -> str:
    def norm(v):
        return v.strip().lower() if isinstance(v, str) else v
    return json.dumps({k: norm(v) for k, v in sorted(args.items()) if v is not None},
                      sort_keys=True, default=str)


@dataclass
class Proposal:
    seq: int
    name: str
    args: Dict[str, Any]
    created: float
    speech_epoch: int
    superseded: bool = False


@dataclass
class CommitGate:
    quiet_s: float = QUIET_S
    hesitant_quiet_s: float = HESITANT_QUIET_S
    max_hold_s: float = MAX_HOLD_S
    last_user_text: str = ""
    user_speaking: bool = False
    last_user_activity: float = field(default_factory=time.monotonic)
    speech_epoch: int = 0                 # increments each time the user starts speaking
    held: List[Proposal] = field(default_factory=list)
    executed: Dict[str, Any] = field(default_factory=dict)
    seq: int = 0
    stats: Dict[str, int] = field(default_factory=lambda: {"proposed": 0, "executed": 0,
                                                            "superseded": 0, "duplicate": 0})

    # ---- signals from the session -------------------------------------------------
    def on_user_state(self, state: str) -> None:
        now = time.monotonic()
        if state == "speaking" and not self.user_speaking:
            self.speech_epoch += 1
        self.user_speaking = state == "speaking"
        self.last_user_activity = now

    def on_user_transcript(self, text: str = "") -> None:
        self.last_user_activity = time.monotonic()
        if text.strip():
            self.last_user_text = text

    def required_quiet(self) -> float:
        return self.hesitant_quiet_s if ends_hesitantly(self.last_user_text) else self.quiet_s

    # ---- gating ---------------------------------------------------------------------
    async def run(self, name: str, args: Dict[str, Any],
                  execute: Callable[[], Awaitable[Any]]) -> Any:
        self.seq += 1
        self.stats["proposed"] += 1
        p = Proposal(self.seq, name, dict(args), time.monotonic(), self.speech_epoch)
        # A newer proposal for the same tool, made after the user spoke again,
        # replaces an older held one: that is a correction, not a second request.
        for old in self.held:
            if old.name == name and not old.superseded and old.speech_epoch < p.speech_epoch:
                old.superseded = True
        self.held.append(p)
        try:
            while True:
                if p.superseded:
                    self.stats["superseded"] += 1
                    log.info("superseded %s %s", name, args)
                    return json.dumps({"status": "superseded",
                                       "note": "The user corrected this request; the updated "
                                               "request is being handled instead."})
                now = time.monotonic()
                settled = (not self.user_speaking) and now - self.last_user_activity >= self.required_quiet()
                if settled or now - p.created >= self.max_hold_s:
                    break
                await asyncio.sleep(POLL_S)
        finally:
            if p in self.held:
                self.held.remove(p)
        key = name + "|" + _canon(args)
        if key in self.executed:
            self.stats["duplicate"] += 1
            log.info("duplicate %s %s: returning earlier result", name, args)
            return self.executed[key]
        result = await execute()
        self.executed[key] = result
        self.stats["executed"] += 1
        return result


def gate_tools(tools: list, gate: CommitGate, function_tool_cls) -> list:
    """Wrap bound LiveKit FunctionTools so each call goes through the gate.
    The wrapper keeps the original signature and docstring, so the tool schema the
    model sees is unchanged."""
    gated = []
    for t in tools:
        name = t.info.name

        async def wrapper(*a, __t=t, __name=name, **kw):
            return await gate.run(__name, kw, lambda: __t(*a, **kw))

        functools.update_wrapper(wrapper, t)
        wrapper.__signature__ = getattr(t, "__signature__", None) or wrapper.__signature__
        gated.append(function_tool_cls(wrapper, t.info))
    return gated
