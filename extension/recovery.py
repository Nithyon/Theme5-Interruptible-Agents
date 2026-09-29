"""Recovery layer for the extension's "slow / failing tool recovery" use case.

Pure Python, no LiveKit imports — this is the coordinator-side piece that plugs into a
LiveKit agent later (see extension/DESIGN.md). It gives any tool call:

- a timeout, so a slow backend never hangs the conversation;
- retry with exponential backoff on a plain failure;
- an idempotency cache, so a state-changing call that already succeeded is never re-run
  (same pattern as fdb_agent/gate.py's dedupe-by-canonical-args, reused here deliberately);
- cancel/supersede, so a call still pending is dropped cleanly when the user interrupts or
  changes their mind, without touching a call that already finished;
- rollback, so a state-changing call the user corrects *after* it already succeeded (not just
  while pending) runs a compensating action first, then the new call — never the new call
  without a successful compensation, and never the same compensation twice;
- progress callbacks, so the talker can say "still checking..." without claiming the tool
  is done;
- a graceful handoff to a human after too many consecutive failures on the same request;
- an event log of everything that happened, whether it ran, retried, was cancelled, or
  handed off.

A state-changing call that times out is treated as ambiguous (did it happen or not?) and is
never auto-retried — it goes straight to the failure/handoff path instead, the same way a
real dispatch system would rather ask a human than risk double-booking.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional


def _canon(args: Dict[str, Any]) -> str:
    def norm(v):
        return v.strip().lower() if isinstance(v, str) else v
    return json.dumps({k: norm(v) for k, v in sorted(args.items()) if v is not None},
                       sort_keys=True, default=str)


class ToolFailure(Exception):
    """Raised by a tool to signal a plain (non-ambiguous) failure that happened before any
    state change took effect — safe to retry."""


@dataclass
class Event:
    seq: int
    kind: str  # proposed|started|progress|retry|succeeded|failed|cancelled|superseded|handoff|duplicate|rollback
    call_id: str
    tool: str
    detail: str = ""
    ts: float = field(default_factory=time.monotonic)

    def to_json(self) -> str:
        return json.dumps({"seq": self.seq, "kind": self.kind, "call_id": self.call_id,
                            "tool": self.tool, "detail": self.detail, "ts": round(self.ts, 3)})


@dataclass
class EventLog:
    events: List[Event] = field(default_factory=list)
    _seq: int = 0

    def emit(self, kind: str, call_id: str, tool: str, detail: str = "") -> Event:
        self._seq += 1
        e = Event(self._seq, kind, call_id, tool, detail)
        self.events.append(e)
        return e

    def lines(self) -> List[str]:
        return [e.to_json() for e in self.events]

    def kinds_for(self, call_id: str) -> List[str]:
        return [e.kind for e in self.events if e.call_id == call_id]


@dataclass
class PendingCall:
    call_id: str
    tool: str
    task: "asyncio.Task[Any]"
    superseded: bool = False


@dataclass
class CompletedCall:
    """The last state-changing call that actually succeeded in a given slot — what a later
    rollback would need to compensate for. `compensated` flips once, so the same success is
    never compensated twice even if the driver corrects themselves more than once in a row."""
    tool: str
    args_key: str
    result: Dict[str, Any]
    compensated: bool = False


@dataclass
class ToolRunner:
    """Runs tool calls with timeout, retry/backoff, idempotency, cancel/supersede, progress
    callbacks, and a graceful handoff after repeated failures on the same logical request."""
    timeout_s: float = 6.0
    max_retries: int = 2                 # additional attempts after the first
    backoff_base_s: float = 0.5
    backoff_cap_s: float = 4.0
    progress_after_s: float = 1.5        # first "still checking..." after this long
    handoff_after_failures: int = 3      # consecutive failed run() calls on one slot
    on_progress: Optional[Callable[[str, str], None]] = None       # (tool, call_id)
    on_handoff: Optional[Callable[[str, str, str], None]] = None   # (tool, call_id, ref)
    on_rollback: Optional[Callable[[str, str, str, Dict[str, Any]], None]] = None
    # (old_tool, compensate_tool, new_tool, new_result)
    log: EventLog = field(default_factory=EventLog)
    executed: Dict[str, Any] = field(default_factory=dict)        # idempotency key -> result
    failures: Dict[str, int] = field(default_factory=dict)        # slot -> consecutive fails
    pending: Dict[str, PendingCall] = field(default_factory=dict)  # slot -> in-flight call
    completed: Dict[str, CompletedCall] = field(default_factory=dict)  # slot -> last succeeded
    _seq: int = 0
    _handoff_seq: int = 0

    def _next_call_id(self) -> str:
        self._seq += 1
        return f"c{self._seq}"

    def _handoff_ref(self) -> str:
        self._handoff_seq += 1
        return f"HANDOFF-{self._handoff_seq:04d}"

    def supersede(self, slot: str) -> None:
        """Cancel/mark-stale whatever is pending in this slot: the user interrupted or
        changed their mind mid-wait. A call that already finished executing is untouched —
        only a call still in flight or waiting on backoff is affected."""
        p = self.pending.get(slot)
        if p is None or p.superseded:
            return
        p.superseded = True
        if not p.task.done():
            p.task.cancel()
        self.log.emit("superseded", p.call_id, p.tool, f"slot={slot}")

    async def run(self, tool: str, args: Dict[str, Any], execute: Callable[[], Awaitable[Any]],
                  *, slot: Optional[str] = None, state_changing: bool = False) -> Dict[str, Any]:
        """Execute one tool call under timeout/retry/idempotency.

        `slot` groups calls that represent the same logical request (e.g. one
        destination-change request) so a newer call in the same slot supersedes whatever
        was still pending there.
        """
        slot = slot or tool
        call_id = self._next_call_id()
        key = tool + "|" + _canon(args)
        self.log.emit("proposed", call_id, tool, _canon(args))

        if key in self.executed:
            self.log.emit("duplicate", call_id, tool, "returning cached result, not re-executed")
            return self.executed[key]

        self.supersede(slot)  # a newer call in this slot replaces whatever was pending

        async def attempt() -> Dict[str, Any]:
            attempts = 0
            last_err: Optional[BaseException] = None
            while True:
                attempts += 1
                self.log.emit("started", call_id, tool, f"attempt {attempts}")
                progress_task = None
                if self.on_progress is not None:
                    progress_task = asyncio.create_task(self._progress_loop(tool, call_id))
                ambiguous = False
                try:
                    result = await asyncio.wait_for(execute(), timeout=self.timeout_s)
                    self.executed[key] = result
                    self.failures[slot] = 0
                    if state_changing:
                        self.completed[slot] = CompletedCall(tool=tool, args_key=key, result=result)
                    self.log.emit("succeeded", call_id, tool, f"attempt {attempts}")
                    return result
                except asyncio.CancelledError:
                    self.log.emit("cancelled", call_id, tool, f"attempt {attempts}")
                    raise
                except asyncio.TimeoutError as e:
                    last_err = e
                    ambiguous = state_changing  # did the state change land before the timeout?
                    self.log.emit("failed", call_id, tool, f"attempt {attempts}: timed out")
                except ToolFailure as e:
                    last_err = e
                    self.log.emit("failed", call_id, tool, f"attempt {attempts}: {e}")
                finally:
                    if progress_task:
                        progress_task.cancel()

                if ambiguous or attempts > self.max_retries:
                    break
                delay = min(self.backoff_cap_s, self.backoff_base_s * (2 ** (attempts - 1)))
                self.log.emit("retry", call_id, tool, f"backing off {delay:.2f}s")
                await asyncio.sleep(delay)

            self.failures[slot] = self.failures.get(slot, 0) + 1
            if self.failures[slot] >= self.handoff_after_failures:
                ref = self._handoff_ref()
                self.log.emit("handoff", call_id, tool,
                              f"ref={ref} after {self.failures[slot]} consecutive failures")
                if self.on_handoff:
                    self.on_handoff(tool, call_id, ref)
                return {"status": "handoff", "reference": ref}
            return {"status": "failed", "error": str(last_err)}

        task = asyncio.create_task(attempt())
        self.pending[slot] = PendingCall(call_id, tool, task)
        try:
            result = await task
        except asyncio.CancelledError:
            result = {"status": "cancelled"}
        finally:
            cur = self.pending.get(slot)
            if cur is not None and cur.call_id == call_id:
                del self.pending[slot]
        return result

    async def rollback_and_run(self, tool: str, args: Dict[str, Any], execute: Callable[[], Awaitable[Any]],
                               *, slot: str, compensate_tool: str, compensate_args: Dict[str, Any],
                               compensate_execute: Callable[[], Awaitable[Any]]) -> Dict[str, Any]:
        """For a state-changing correction that arrives *after* the previous call in this slot
        already succeeded (e.g. the charger is already booked, and the driver says "actually,
        the Ionity one instead") — run the compensating action first (e.g. cancel the old
        booking), then the new call, and tell `on_rollback` so the talker can narrate both.

        Rules, enforced here rather than left to the caller:
        - never compensates a call that didn't succeed (nothing recorded in `completed[slot]`,
          or the "new" request is identical to what's already booked — that's just idempotency,
          handled by `run()`'s own cache, not a rollback);
        - never runs the same compensation twice (`CompletedCall.compensated` flips once);
        - if the compensation itself fails, goes to human handoff immediately and never
          attempts the new call — so the driver is never left with both bookings active with
          nobody having told them, nor silently down a booking with no explanation.
        """
        key = tool + "|" + _canon(args)
        prior = self.completed.get(slot)
        if prior is None or prior.compensated or prior.args_key == key:
            # nothing to compensate: either there was no prior success, we already compensated
            # it, or this "correction" is actually identical to what's already booked (run()'s
            # own idempotency cache will just return the cached result).
            return await self.run(tool, args, execute, slot=slot, state_changing=True)

        comp_result = await self.run(compensate_tool, compensate_args, compensate_execute,
                                     slot=f"{slot}:compensate", state_changing=True)
        if comp_result.get("status") != "success":
            if comp_result.get("status") == "handoff":
                return comp_result  # already handed off after repeated compensation failures
            ref = self._handoff_ref()
            cid = self._next_call_id()
            self.log.emit("handoff", cid, compensate_tool,
                          f"ref={ref} compensation failed for slot={slot}: rollback aborted, "
                          f"new call not attempted, prior booking left in place")
            if self.on_handoff:
                self.on_handoff(compensate_tool, cid, ref)
            return {"status": "handoff", "reference": ref, "reason": "compensation_failed"}

        prior.compensated = True
        new_result = await self.run(tool, args, execute, slot=slot, state_changing=True)
        if new_result.get("status") == "success":
            rb_id = self._next_call_id()
            self.log.emit("rollback", rb_id, tool,
                          f"compensated {prior.tool} (key={prior.args_key}) via {compensate_tool}, "
                          f"then executed {tool}")
            if self.on_rollback:
                self.on_rollback(prior.tool, compensate_tool, tool, new_result)
        return new_result

    async def _progress_loop(self, tool: str, call_id: str) -> None:
        try:
            await asyncio.sleep(self.progress_after_s)
            while True:
                if self.on_progress:
                    self.on_progress(tool, call_id)
                await asyncio.sleep(self.progress_after_s)
        except asyncio.CancelledError:
            return
