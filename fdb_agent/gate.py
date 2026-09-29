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
import inspect
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
# With Jev: release fast when it's confident the user is done, hold longer when it thinks
# the user is still going (a thinking pause before a correction).
JEV_FAST_S = 0.4
JEV_HOLD_S = 2.5
JEV_DONE_P = 0.8
JEV_CONT_P = 0.6

# Trailing words that usually mean the user hasn't finished (a filler, or the start of
# a self-correction), so a pause after them is a thinking pause, not the end of the turn.
_HESITANT_TAILS = ("um", "uh", "er", "erm", "hmm", "wait", "no", "actually", "sorry",
                   "i mean", "or", "and", "but", "like", "so", "make that", "scratch that")


def ends_hesitantly(text: str) -> bool:
    words = "".join(c if c.isalnum() or c in " '" else " " for c in text.lower()).split()
    tail = " ".join(words[-2:])
    return bool(words) and (words[-1] in _HESITANT_TAILS or tail in _HESITANT_TAILS)


# Words in what the user said *after* a call was proposed that decide whether a newer call
# to the same tool replaces the held one (a correction) or joins it (a second request).
_CORRECTION_CUES = ("no", "not", "sorry", "actually", "wait", "i mean", "instead", "rather",
                    "make that", "make it", "change", "scratch that", "correction", "oops",
                    "my mistake", "wrong", "cancel")
_ADDITION_CUES = ("and", "also", "another", "too", "as well", "plus", "both", "second")


def _words(text: str) -> List[str]:
    return "".join(c if c.isalnum() or c in " '" else " " for c in text.lower()).split()


def _has_cue(text: str, cues) -> bool:
    w = _words(text)
    joined = " " + " ".join(w) + " "
    return any((" " + c + " ") in joined for c in cues)


def classify_followup(text: str) -> str:
    """'correction' | 'addition' | 'none' for user speech that arrived between two calls."""
    if not _words(text):
        return "none"
    if _has_cue(text, _CORRECTION_CUES):
        return "correction"
    if _has_cue(text, _ADDITION_CUES):
        return "addition"
    return "unclear"


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
    transcript_idx: int = 0               # how many user transcript events existed at proposal
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
    unclear_supersedes: bool = True       # a same-tool re-call after more speech with no cue
    judge: Any = None                     # optional JevJudge; None = rules only
    jev_turn: Optional[Dict[str, float]] = None   # Jev's view of the latest transcript
    jev_turn_idx: int = -1                # which transcript event jev_turn refers to
    transcript: List[tuple] = field(default_factory=list)   # (monotonic time, text) per event
    events: List[dict] = field(default_factory=list)        # decision log for analysis
    stats: Dict[str, int] = field(default_factory=lambda: {"proposed": 0, "executed": 0,
                                                            "superseded": 0, "duplicate": 0,
                                                            "kept_both": 0, "transcripts": 0,
                                                            "user_state": 0})

    def _event(self, kind: str, **kw) -> None:
        self.events.append({"t": round(time.monotonic(), 3), "kind": kind, **kw})

    # ---- signals from the session -------------------------------------------------
    def on_user_state(self, state: str) -> None:
        now = time.monotonic()
        if state == "speaking" and not self.user_speaking:
            self.speech_epoch += 1
        self.user_speaking = state == "speaking"
        self.last_user_activity = now
        self.stats["user_state"] += 1
        self._event("user_state", state=state)

    def on_user_transcript(self, text: str = "", final: Optional[bool] = None) -> None:
        # With a realtime model (no local VAD) the user's live transcript is the only
        # reliable "the user is still talking" signal, so it drives the quiet timer.
        now = time.monotonic()
        self.last_user_activity = now
        if text.strip():
            self.last_user_text = text
            self.transcript.append((now, text))
            self.stats["transcripts"] += 1
            self._event("transcript", text=text[-120:], final=final)
            if self.judge is not None:
                idx = len(self.transcript) - 1
                context = " ".join(t for _, t in self.transcript[-3:])
                try:
                    asyncio.get_running_loop().create_task(self._ask_turn(idx, context))
                except RuntimeError:
                    pass                          # no loop (sync caller): rules only

    async def _ask_turn(self, idx: int, context: str) -> None:
        probs = await self.judge.turn_state(context)
        if probs is not None and idx == len(self.transcript) - 1:
            self.jev_turn, self.jev_turn_idx = probs, idx
            self._event("jev_turn", idx=idx, probs={k: round(v, 3) for k, v in probs.items()})

    def _speech_since(self, idx: int) -> str:
        return " ".join(t for _, t in self.transcript[idx:])

    def required_quiet(self) -> float:
        rule = self.hesitant_quiet_s if ends_hesitantly(self.last_user_text) else self.quiet_s
        if self.jev_turn is not None and self.jev_turn_idx == len(self.transcript) - 1:
            if self.jev_turn.get("continuing", 0.0) >= JEV_CONT_P:
                return max(rule, JEV_HOLD_S)
            if self.jev_turn.get("complete", 0.0) >= JEV_DONE_P:
                return JEV_FAST_S
        return rule

    # ---- gating ---------------------------------------------------------------------
    async def run(self, name: str, args: Dict[str, Any],
                  execute: Callable[[], Awaitable[Any]]) -> Any:
        self.seq += 1
        self.stats["proposed"] += 1
        p = Proposal(self.seq, name, dict(args), time.monotonic(), self.speech_epoch,
                     len(self.transcript))
        self._event("proposed", seq=p.seq, name=name, args=args)
        # A newer proposal for the same tool replaces an older held one when the user said
        # more in between and it sounds like a correction ("no, sorry, New York"); it joins
        # it when it sounds like a second request ("and also order B2").
        for old in self.held:
            if old.name != name or old.superseded:
                continue
            said = self._speech_since(old.transcript_idx)
            kind = classify_followup(said)
            if old.speech_epoch < p.speech_epoch and kind == "none":
                kind = "correction"           # a VAD/interrupt said the user spoke again
            source = "rules"
            if self.judge is not None and kind != "none":
                probs = await self.judge.followup({"tool": old.name, "args": old.args},
                                                  {"tool": name, "args": args}, said)
                if probs:
                    kind, source = max(probs, key=probs.get), "jev"
            replace = kind == "correction" or (kind == "unclear" and self.unclear_supersedes)
            self._event("same_tool_again", old=old.seq, new=p.seq, said=said[-120:],
                        followup=kind, source=source, replace=replace)
            if replace:
                old.superseded = True
            else:
                self.stats["kept_both"] += 1
        self.held.append(p)
        try:
            while True:
                if p.superseded:
                    self.stats["superseded"] += 1
                    self._event("superseded", seq=p.seq)
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
            self._event("duplicate", seq=p.seq)
            log.info("duplicate %s %s: returning earlier result", name, args)
            return self.executed[key]
        self._event("execute", seq=p.seq, held_s=round(time.monotonic() - p.created, 3),
                    quiet=self.required_quiet())
        result = await execute()
        self.executed[key] = result
        self.stats["executed"] += 1
        return result


def _is_plain(v: Any) -> bool:
    """True for JSON-like tool arguments; False for injected objects (e.g. RunContext)."""
    return v is None or isinstance(v, (str, int, float, bool, list, dict))


def gate_tools(tools: list, gate: CommitGate, function_tool_cls) -> list:
    """Wrap bound LiveKit FunctionTools so each call goes through the gate.
    The wrapper keeps the original signature and docstring, so the tool schema the
    model sees is unchanged."""
    gated = []
    for t in tools:
        name = t.info.name
        sig = getattr(t, "__signature__", None) or inspect.signature(t)

        async def wrapper(*a, __t=t, __name=name, __sig=sig, **kw):
            # LiveKit may pass tool arguments positionally, so bind them to parameter
            # names; otherwise every call to a tool would look identical to the gate.
            bound = __sig.bind_partial(*a, **kw).arguments
            args = {k: v for k, v in bound.items() if _is_plain(v)}
            return await gate.run(__name, args, lambda: __t(*a, **kw))

        functools.update_wrapper(wrapper, t)
        wrapper.__signature__ = sig
        gated.append(function_tool_cls(wrapper, t.info))
    return gated
