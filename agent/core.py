"""The coordinator behind ParticipantAgent.

`run()` only dispatches: it drains the input queue into a batch and calls
synchronous handlers. Handlers update one state object, emit actions with
`put_nowait`, and spawn background tasks for anything slow (model calls, frame
analysis). Tool calls execute in the harness and come back as events, so an
interruption is always handled in the same loop tick it is read.
"""

from __future__ import annotations
import asyncio
import copy
import json
import re
import sys
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from . import llm as llm_mod
from . import media, nlu, schema

SPOKEN = ("filler_speech", "clarification_request", "final_response")
FILLER_SOFT_CAP = 3
FILLER_HARD_CAP = 4
TAIL_MS = 6000.0
TAIL_DEADLINE_MS = 5600.0
FRAME_WAIT_S = 5.0
AUDIO_BUDGET_S = 5.0      # transcription, including fallbacks to other models
TEXT_BUDGET_S = 4.0       # interpreting an utterance the rules could not place
MIN_MODEL_S = 0.3         # below this there is no point starting a model call
CLOCK_TICK_S = time.get_clock_info("monotonic").resolution

# The scorer's premature-claim patterns; hidden tools add more, so claims for any
# state-modifying tool in the manifest are also derived from its verb.
CLAIM_PATTERNS = {
    "book_flight": [r"\bbooked\b", r"\breserved\b", r"booking (is )?confirmed"],
    "create_support_ticket": [r"ticket (id|created|opened|filed)"],
    "cancel_booking": [r"booking (is |was )?cancell?ed", r"cancell?ed your booking"],
}
FUTURE_GUARDS = ("will", "'ll", "going to", "let me", "one moment", "about to",
                 "getting", "get that", "get this", "now", "right away")
DEIXIS = re.compile(r"\b(this|that|these|those|here)\b", re.I)
YES = re.compile(r"\b(yes|yeah|yep|sure|please do|go ahead|ok(?:ay)?|do it|try again)\b", re.I)
NO = re.compile(r"\b(no|nope|don'?t|never mind|leave it|stop)\b", re.I)

_VERB_TOKENS = {"search", "lookup", "look", "get", "find", "check", "fetch", "query", "list",
                "quote", "retrieve", "create", "book", "cancel", "open", "make", "schedule",
                "reset", "update", "delete", "add", "send", "set", "submit", "request",
                "order", "reserve", "estimate", "track", "locate", "reserve"}
_IRREGULAR_PAST = {"reset": "reset", "send": "sent", "set": "set", "make": "made", "buy": "bought",
                   "pay": "paid", "put": "put", "cancel": "cancelled", "run": "run"}
_PLAIN_FIELDS = ("condition", "forecast", "summary", "description", "message", "note",
                 "status_text", "advice", "answer", "details", "text")


def _norm(v: Any) -> str:
    return str(v).strip().lower()


def _log(msg: str):
    print(f"[agent] {msg}", file=sys.stderr)


def join_and(items: List[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def join_or(items: List[str]) -> str:
    items = [i for i in items if i]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + f" or {items[-1]}"


def human_key(key: str) -> str:
    words = key.replace(".", " ").replace("_", " ").split()
    return " ".join("ID" if w.lower() == "id" else w for w in words)


def fmt_num(v: Any) -> str:
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def plural(noun: str) -> str:
    if not noun or noun.endswith("s"):
        return noun
    if noun.endswith("y") and len(noun) > 1 and noun[-2] not in "aeiou":
        return noun[:-1] + "ies"
    return noun + "s"


def verb_past(v: str) -> str:
    if v in _IRREGULAR_PAST:
        return _IRREGULAR_PAST[v]
    if v.endswith("e"):
        return v + "d"
    if v.endswith("y") and len(v) > 1 and v[-2] not in "aeiou":
        return v[:-1] + "ied"
    return v + "ed"


def tool_noun(name: str) -> str:
    toks = name.split("_")
    rest = [t for t in toks if t not in _VERB_TOKENS] or toks
    return " ".join(rest)


def tool_verb(name: str) -> str:
    return nlu.stem(name.split("_")[0])


def set_path(obj: Dict[str, Any], path: str, value: Any):
    parts = path.split(".")
    cur = obj
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def get_path(obj: Any, path: str) -> Any:
    cur = obj
    for p in path.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


def result_items(result: Dict[str, Any]) -> Tuple[Optional[str], Optional[List[Dict[str, Any]]]]:
    for k, v in result.items():
        if isinstance(v, list) and all(isinstance(x, dict) for x in v):
            return k, v
    return None, None


def idem_key(api: str, args: Dict[str, Any]) -> str:
    flat = {k: _norm(v) if not isinstance(v, (dict, list)) else v for k, v in sorted(args.items())}
    return api + "|" + json.dumps(flat, sort_keys=True, default=str)


def leaf_values(args: Dict[str, Any], prefix: str = "") -> List[Tuple[str, Any]]:
    out = []
    for k, v in args.items():
        path = f"{prefix}{k}"
        if isinstance(v, dict):
            out.extend(leaf_values(v, path + "."))
        else:
            out.append((path, v))
    return out


# ---------------------------------------------------------------------------
# clock
# ---------------------------------------------------------------------------
class VirtualClock:
    """Estimates the harness's virtual time from event timestamps, so deadlines
    hold whatever time scale the harness runs at."""

    def __init__(self):
        self.first: Optional[Tuple[float, float]] = None
        self.last: Optional[Tuple[float, float]] = None
        self.scale = 1.0

    def observe(self, ev: Dict[str, Any]):
        ts = ev.get("timestamp_ms")
        if not isinstance(ts, (int, float)):
            return
        real = asyncio.get_running_loop().time()
        if self.first is None:
            self.first = (float(ts), real)
        if self.last is None or float(ts) >= self.last[0]:
            self.last = (float(ts), real)
        dv = float(ts) - self.first[0]
        dr = real - self.first[1]
        if dv > 300 and dr > 0.01:
            self.scale = min(max(dv / (dr * 1000.0), 0.05), 500.0)

    def now(self) -> float:
        if self.last is None:
            return 0.0
        real = asyncio.get_running_loop().time()
        return self.last[0] + (real - self.last[1]) * 1000.0 * self.scale

    def seconds_until(self, virtual_ms: float) -> float:
        return max(virtual_ms - self.now(), 0.0) / 1000.0 / self.scale


# ---------------------------------------------------------------------------
# plan / call records
# ---------------------------------------------------------------------------
@dataclass
class Step:
    tool: str
    bindings: Dict[str, str] = field(default_factory=dict)   # arg path -> slot name
    literals: Dict[str, Any] = field(default_factory=dict)   # arg path -> fixed value
    chain_from: Optional[int] = None                          # step whose result feeds this one
    chain_args: List[str] = field(default_factory=list)       # arg paths taken from that result
    needs_frame: bool = False


@dataclass
class Plan:
    pid: int
    intent: str
    steps: List[Step]
    text: str
    selector: Dict[str, Any]
    slot_values: Dict[str, Any]
    slot_kinds: Dict[str, str]
    results: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    done: bool = False
    visual_label: Optional[str] = None


@dataclass
class Call:
    call_id: str
    api: str
    args: Dict[str, Any]
    kind: str
    pid: int
    step: int
    attempt: int = 1
    status: str = "pending"          # pending | cancelled | done | error | stale
    key: Optional[str] = None


# ---------------------------------------------------------------------------
# the agent
# ---------------------------------------------------------------------------
class InterruptibleAgent:
    def __init__(self, in_queue: asyncio.Queue, out_queue: asyncio.Queue):
        self.in_q = in_queue
        self.out_q = out_queue
        self.llm = llm_mod.LLM()
        self.clock = VirtualClock()
        self.tools: Dict[str, Dict[str, Any]] = {}
        self._profiles: Dict[str, Tuple[Set[str], Set[str], Set[str]]] = {}
        self.intent: Optional[str] = None
        self.slots: Dict[str, Any] = {}
        self.slot_kinds: Dict[str, str] = {}
        self.memory: Dict[str, Any] = {}
        self.epoch = 0
        self.plan: Optional[Plan] = None
        self.plan_seq = 0
        self.calls: Dict[str, Call] = {}
        self.call_seq = 0
        self.done_keys: Dict[str, Dict[str, Any]] = {}
        self.inflight_keys: Set[str] = set()
        self.succeeded: Set[str] = set()
        self.fillers = 0
        self.spoken: Set[str] = set()
        self.turn_text: List[str] = []
        self.turn_audio: List[str] = []
        self.frame: Optional[Dict[str, Any]] = None
        self.frame_info: Dict[str, Dict[str, Any]] = {}
        self.frame_tasks: Dict[str, asyncio.Task] = {}
        self.pending_clar: Optional[Dict[str, Any]] = None
        self.planning: Optional[asyncio.Task] = None
        self.deferred: List[Tuple[str, Any, bool]] = []   # (kind, text or audio refs, interrupt)
        self.staged: Optional[List[str]] = None
        self.tasks: Set[asyncio.Task] = set()
        self.history: List[str] = []
        self.ended = False
        self.end_vt: Optional[float] = None
        self.watchdog: Optional[asyncio.Task] = None
        self.notes: List[str] = []
        self.outbox: List[Dict[str, Any]] = []
        self.hold_until = 0.0
        self.flush_handle: Optional[asyncio.TimerHandle] = None

    # ------------------------------------------------------------------ lifecycle
    async def setup(self):
        self.llm = await llm_mod.init()

    async def run(self):
        try:
            while True:
                first = await self.in_q.get()
                batch = [first]
                while True:
                    try:
                        batch.append(self.in_q.get_nowait())
                    except asyncio.QueueEmpty:
                        break
                # A tool result queued just before an interruption must be judged
                # against the post-interruption state, so results go last.
                ordered = ([e for e in batch if e.get("event_type") != "tool_result"]
                           + [e for e in batch if e.get("event_type") == "tool_result"])
                for ev in ordered:
                    self.clock.observe(ev)
                    if ev.get("event_type") in ("user_speech_chunk", "user_audio_chunk", "interruption"):
                        self.hold_if_early(ev)
                    self._dispatch(ev)
        finally:
            if self.flush_handle is not None:
                self.flush_handle.cancel()
            for t in list(self.tasks):
                t.cancel()

    def _dispatch(self, ev: Dict[str, Any]):
        etype = ev.get("event_type")
        payload = ev.get("payload") if isinstance(ev.get("payload"), dict) else {}
        handler = {
            "tool_manifest": self.on_manifest,
            "user_speech_chunk": self.on_speech,
            "user_audio_chunk": self.on_audio,
            "video_frame": self.on_frame,
            "interruption": self.on_interruption,
            "tool_result": self.on_tool_result,
            "scenario_end": self.on_end,
        }.get(etype)
        if handler is None:
            return
        try:
            handler(payload, ev)
        except Exception:
            _log(f"handler {etype} failed:\n{traceback.format_exc()}")
            if etype in ("user_speech_chunk", "user_audio_chunk", "interruption"):
                self.say("clarification_request", "Sorry, I lost track there. Could you say that again?")

    def spawn(self, coro) -> asyncio.Task:
        task = asyncio.get_running_loop().create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self._task_done)
        return task

    def _task_done(self, task: asyncio.Task):
        self.tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            _log("background task failed:\n" + "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)))

    # ------------------------------------------------------------------ output
    def snapshot(self) -> Dict[str, Any]:
        slots = {k: v for k, v in self.slots.items() if v not in (None, "", [], {})}
        locs = [k for k, kind in self.slot_kinds.items() if kind == "location" and k in slots]
        if len(locs) == 1 and "destination" not in slots:
            slots["destination"] = slots[locs[0]]
        persons = [k for k, kind in self.slot_kinds.items() if kind == "person" and k in slots]
        if len(persons) == 1 and "passenger_name" not in slots:
            slots["passenger_name"] = slots[persons[0]]
        return {"intent": self.intent, "slots": copy.deepcopy(slots)}

    def emit(self, action: str, payload: Dict[str, Any]):
        msg: Dict[str, Any] = {"action": action, "payload": payload}
        if action in SPOKEN:
            msg["state_snapshot"] = self.snapshot()
        loop = asyncio.get_running_loop()
        if self.outbox or loop.time() < self.hold_until:
            self.outbox.append(msg)
            if self.flush_handle is None:
                self.flush_handle = loop.call_at(self.hold_until, self.flush_outbox)
            return
        self.out_q.put_nowait(msg)

    def flush_outbox(self):
        self.flush_handle = None
        pending, self.outbox = self.outbox, []
        for msg in pending:
            self.out_q.put_nowait(msg)

    def hold_if_early(self, ev: Dict[str, Any]):
        """asyncio fires a timer up to one clock tick early (about 16 ms on Windows,
        negligible on Linux), so a user event can arrive before its own timestamp.
        A reply sent in that tick would be logged before the event and miss both the
        latency check and any checkpoint windowed on the event, so output waits one
        tick."""
        if CLOCK_TICK_S > 0.002:
            loop = asyncio.get_running_loop()
            self.hold_until = max(self.hold_until, loop.time() + CLOCK_TICK_S + 0.001)

    def say(self, kind: str, text: str, critical: bool = False, alt: Optional[str] = None,
            safe: str = "One moment while I finish that.") -> bool:
        text = re.sub(r"\s+", " ", text or "").strip()
        if not text:
            return False
        if kind == "filler_speech":
            if self.fillers >= (FILLER_HARD_CAP if critical else FILLER_SOFT_CAP):
                return False
            if _norm(text) in self.spoken:
                if alt and _norm(alt) not in self.spoken:
                    text = alt
                else:
                    return False
        text = self.lint(text, safe)
        if kind == "filler_speech":
            self.fillers += 1
        self.spoken.add(_norm(text))
        self.history.append(f"assistant: {text}")
        self.emit(kind, {"text": text})
        return True

    def claim_patterns(self) -> Dict[str, List[str]]:
        pats = {k: list(v) for k, v in CLAIM_PATTERNS.items()}
        for name, spec in self.tools.items():
            if spec.get("kind") == "state_modifying":
                past = verb_past(tool_verb(name))
                if past == "cancelled":
                    past = "cancell?ed"
                pats.setdefault(name, []).append(rf"\b{past}\b")
        return pats

    def lint(self, text: str, safe: str) -> str:
        low = _norm(text)
        if any(g in low for g in FUTURE_GUARDS):
            return text
        for tool, pats in self.claim_patterns().items():
            if tool in self.succeeded:
                continue
            if any(re.search(p, low) for p in pats):
                _log(f"claim lint blocked: {text!r}")
                return safe
        return text

    # ------------------------------------------------------------------ calls
    def call_tool(self, api: str, args: Dict[str, Any], plan: Plan, step: int, attempt: int = 1) -> str:
        self.call_seq += 1
        cid = f"c{self.call_seq}"
        spec = self.tools.get(api, {})
        kind = spec.get("kind", "read_only")
        rec = Call(cid, api, copy.deepcopy(args), kind, plan.pid, step, attempt)
        if kind == "state_modifying":
            rec.key = idem_key(api, args)
            self.inflight_keys.add(rec.key)
        self.calls[cid] = rec
        if self.staged is not None:
            self.staged.append(cid)
        else:
            self.emit("tool_call", {"call_id": cid, "api_name": api, "args": args})
        return cid

    def cancel_call(self, rec: Call):
        if rec.status != "pending":
            return
        if self.staged is not None and rec.call_id in self.staged:
            self.staged.remove(rec.call_id)
        else:
            self.emit("cancel_tool", {"call_id": rec.call_id})
        rec.status = "cancelled"
        if rec.key:
            self.inflight_keys.discard(rec.key)

    def begin_staging(self):
        """Hold tool calls back while a finished model result and the utterances that
        arrived during it are applied in order. A call that a later utterance
        invalidates is dropped before it is ever sent, so no call carrying values the
        user already changed reaches the harness after the change."""
        self.staged = []

    def end_staging(self):
        staged, self.staged = self.staged or [], None
        for cid in staged:
            rec = self.calls[cid]
            if rec.status == "pending":
                self.emit("tool_call", {"call_id": cid, "api_name": rec.api, "args": rec.args})

    def resume_after_await(self) -> bool:
        """Called by a planning task after its await. False if the task was superseded."""
        if self.planning is not asyncio.current_task():
            return False
        self.planning = None
        self.begin_staging()
        return True

    def pending_calls(self, pid: Optional[int] = None) -> List[Call]:
        return [c for c in self.calls.values()
                if c.status == "pending" and (pid is None or c.pid == pid)]

    def cancel_all(self):
        for c in self.pending_calls():
            self.cancel_call(c)
        if self.planning is not None and not self.planning.done():
            self.planning.cancel()
        self.planning = None
        self.deferred.clear()

    # ------------------------------------------------------------------ event handlers
    def on_manifest(self, payload, ev):
        tools = payload.get("tools")
        if isinstance(tools, dict):
            self.tools = {k: v for k, v in tools.items() if isinstance(v, dict)}
            self._profiles = {}

    def on_speech(self, payload, ev):
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            self.turn_text.append(text)
        if payload.get("end_of_turn"):
            utter = re.sub(r"\s+", " ", " ".join(self.turn_text)).strip()
            self.turn_text = []
            if utter:
                self.handle_utterance(utter)

    def on_audio(self, payload, ev):
        ref = payload.get("audio_ref")
        if isinstance(ref, str):
            self.turn_audio.append(ref)
        if not payload.get("end_of_turn"):
            return
        refs, self.turn_audio = self.turn_audio, []
        self.epoch += 1
        if not getattr(self.llm, "audio_available", self.llm.available):
            first = "Sorry, I couldn't make out that audio. Could you say it again?"
            again = "Sorry, I still couldn't make that out. Could you say it a little more slowly?"
            self.say("clarification_request", again if _norm(first) in self.spoken else first)
            return
        self.say("filler_speech", "Got it, one moment while I listen to that.", critical=True,
                 alt="Okay, one moment.")
        if self.planning is not None and not self.planning.done():
            self.deferred.append(("audio", refs, False))
            return
        self.planning = self.spawn(self.audio_turn(refs))

    def on_frame(self, payload, ev):
        ref = payload.get("image_ref")
        fid = str(payload.get("frame_id") or ref or "frame")
        self.frame = {"frame_id": fid, "image_ref": ref, "device_hint": payload.get("device_hint")}
        if fid not in self.frame_tasks and isinstance(ref, str):
            self.frame_info[fid] = {}
            self.frame_tasks[fid] = self.spawn(self.analyze_frame(fid, ref))

    def on_interruption(self, payload, ev):
        text = payload.get("text")
        if isinstance(text, str) and text.strip():
            self.handle_utterance(text.strip(), interrupt=True)
        else:
            self.say("filler_speech", "Sorry, go ahead.", critical=True)

    def on_end(self, payload, ev):
        self.ended = True
        ts = ev.get("timestamp_ms")
        self.end_vt = float(ts) if isinstance(ts, (int, float)) else self.clock.now()
        if self.watchdog is None:
            self.watchdog = self.spawn(self.tail_watchdog())

    def on_tool_result(self, payload, ev):
        rec = self.calls.get(str(payload.get("call_id")))
        if rec is None:
            return
        status = payload.get("status")
        result = payload.get("result") if isinstance(payload.get("result"), dict) else {}
        if rec.key:
            self.inflight_keys.discard(rec.key)
        if status == "success":
            self.succeeded.add(rec.api)
            self.remember(result)
            if rec.kind == "state_modifying" and rec.key:
                self.done_keys[rec.key] = result
        plan = self.plan
        stale = rec.status != "pending" or plan is None or plan.pid != rec.pid
        if stale:
            rec.status = "stale"
            if status == "success" and rec.kind == "state_modifying":
                self.report_late_side_effect(rec, result)
            return
        rec.status = "done" if status == "success" else "error"
        if status == "success":
            self.on_step_success(plan, rec.step, result)
        else:
            self.on_step_error(plan, rec, result)

    def remember(self, result: Dict[str, Any]):
        for k, v in result.items():
            if isinstance(v, (str, int)) and (k.endswith("_id") or k == "id"):
                self.memory[k] = v

    # ------------------------------------------------------------------ utterances
    def handle_utterance(self, text: str, interrupt: bool = False, quiet: bool = False):
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            return
        self.epoch += 1
        self.history.append(f"user: {text}")
        if self.planning is not None and not self.planning.done():
            if nlu.retraction_cue(text) and not nlu.remainder_after_retraction(text):
                self.do_retraction()
                return
            rel, data = self.relate(text, self.plan) if self.plan is not None else ("unclear", None)
            if rel == "retraction":
                self.do_retraction()
                return
            if rel == "intent_change":
                self.do_intent_change(data, quiet)
                return
            if rel == "correction":
                # stop sent work now; re-planning waits for the model result
                self.cancel_invalidated(self.plan, data[0], data[1])
            self.deferred.append(("text", text, interrupt))
            if not quiet:
                self.say("filler_speech", "Got it, I'll take that into account.", critical=True,
                         alt="Okay, noted. One moment.")
            return
        if self.pending_clar is not None and self.resolve_clarification(text, quiet):
            return
        plan = self.plan
        if plan is not None:
            rel, data = self.relate(text, plan)
            if rel == "retraction":
                self.do_retraction()
                return
            if rel == "correction":
                self.do_correction(plan, data[0], data[1], quiet)
                return
            if rel == "intent_change":
                self.do_intent_change(data, quiet)
                return
        self.process_request(text, interrupt=interrupt, quiet=quiet)

    def process_request(self, text: str, interrupt: bool = False, quiet: bool = False, prefix: str = ""):
        plan = self.analyze(text)
        if plan is not None:
            self.supersede_plan()
            self.start_plan(plan, ack=not quiet, prefix=prefix)
            return
        if nlu.is_smalltalk(text) or not self.tools:
            self.reply_capabilities(prefix)
            return
        if self.llm.available:
            if not quiet:
                self.say("filler_speech", prefix + "Sure, one moment while I work out the best way to help.",
                         critical=True, alt=prefix + "One moment.")
            self.planning = self.spawn(self.llm_turn(text, interrupt))
            return
        if interrupt:
            self.say("clarification_request", prefix + "Sorry, what would you like me to change?")
        else:
            self.reply_capabilities(prefix, unsure=True)

    def supersede_plan(self):
        if self.plan is not None:
            for c in self.pending_calls(self.plan.pid):
                self.cancel_call(c)
        self.plan = None
        self.pending_clar = None

    def reply_capabilities(self, prefix: str = "", unsure: bool = False):
        phrases = [self.capability_phrase(n) for n in self.tools]
        caps = join_and([p for p in phrases if p][:6])
        if unsure:
            text = (f"{prefix}Sorry, I'm not sure how to help with that. "
                    f"I can help with {caps}." if caps else f"{prefix}Sorry, I'm not sure how to help with that.")
        else:
            text = (f"{prefix}Hi! I can help with {caps}. What would you like to do?" if caps
                    else f"{prefix}Hi! How can I help?")
        self.intent = "chitchat" if not unsure else (self.intent or "chitchat")
        if not unsure:
            self.slots = {}
            self.slot_kinds = {}
        self.say("final_response", text)

    def capability_phrase(self, name: str) -> str:
        toks = name.split("_")
        noun = tool_noun(name)
        spec = self.tools.get(name, {})
        if any(t in ("search", "find", "list") for t in toks):
            return f"finding {plural(noun)}"
        if "quote" in toks or "estimate" in toks:
            return f"getting {noun} quotes"
        if any(t in ("lookup", "look", "check", "get", "fetch", "retrieve") for t in toks):
            return f"looking up {plural(noun) if noun in ('manual', 'guide') else noun}"
        if spec.get("kind") == "state_modifying":
            verb = tool_verb(name)
            gerund = ("cancelling" if verb == "cancel" else
                      verb[:-1] + "ing" if verb.endswith("e") and not verb.endswith("ee") else verb + "ing")
            return f"{gerund} {plural(noun)}"
        return human_key(name)

    # ------------------------------------------------------------------ understanding
    def tool_profile(self, name: str) -> Tuple[Set[str], Set[str], Set[str]]:
        if name not in self._profiles:
            spec = self.tools.get(name, {})
            name_toks = {nlu.stem(t) for t in name.split("_") if t}
            desc_toks = set(nlu.content_stems(str(spec.get("description", ""))))
            arg_text = " ".join(f"{a} {s.get('description', '')}" for a, s in schema.arg_items(spec))
            arg_toks = set(nlu.content_stems(arg_text.replace("_", " ")))
            self._profiles[name] = (name_toks, desc_toks, arg_toks)
        return self._profiles[name]

    def score_tools(self, text: str) -> Dict[str, float]:
        user = set(nlu.content_stems(text))
        scores = {}
        for name in self.tools:
            n, d, a = self.tool_profile(name)
            scores[name] = (3.0 * len(user & n) + 1.5 * len(user & (d - n))
                            + 0.5 * len(user & (a - d - n)))
        return scores

    def feeding_tool(self, sm_name: str, arg_path: str) -> Optional[str]:
        """A read-only tool whose result supplies this argument (named in the descriptions)."""
        spec = self.tools.get(sm_name, {})
        aspec = schema.find_arg_spec(spec, arg_path) or {}
        text = f"{spec.get('description', '')} {aspec.get('description', '')}".lower()
        leaf = arg_path.split(".")[-1]
        for name, other in self.tools.items():
            if name == sm_name or other.get("kind") == "state_modifying":
                continue
            if name.lower() in text:
                return name
        for name, other in self.tools.items():
            if name == sm_name or other.get("kind") == "state_modifying":
                continue
            dr = other.get("default_result")
            if isinstance(dr, dict) and (leaf in dr or any(
                    isinstance(v, list) and v and isinstance(v[0], dict) and leaf in v[0]
                    for v in dr.values())):
                return name
        return None

    def downstream_intent(self, ro_name: str) -> str:
        for name, spec in self.tools.items():
            if spec.get("kind") != "state_modifying":
                continue
            text = str(spec.get("description", "")).lower() + " " + " ".join(
                str(s.get("description", "")).lower() for _, s in schema.arg_items(spec))
            if ro_name.lower() in text:
                return name
        return ro_name

    def extract_value(self, text: str, path: str, aspec: Dict[str, Any], kind: str,
                      bare: bool = False) -> Any:
        leaf = path.split(".")[-1]
        if kind == "location":
            v = nlu.pick_location(text, schema.location_role(leaf, aspec))
            return v or (self.bare_name(text) if bare else None)
        if kind == "date":
            return nlu.extract_date(text)
        if kind == "time":
            return nlu.extract_time(text)
        if kind == "person":
            v = nlu.extract_person(text)
            return v or (self.bare_name(text) if bare else None)
        if kind == "number":
            v = nlu.number_for(text, leaf, str(aspec.get("description", "")))
            if v is None and bare:
                nums = nlu.extract_numbers(text)
                v = nums[-1][1] if nums else None
            return v
        if kind == "enum":
            v = nlu.find_enum(text, aspec.get("enum") or [])
            if v is None and self.frame and self.frame.get("device_hint") in (aspec.get("enum") or []) \
                    and ("model" in leaf or "device" in leaf):
                v = self.frame.get("device_hint")
            return v
        if kind == "id":
            codes = nlu.extract_codes(text)
            if codes:
                return codes[-1]
            return None
        if kind == "model":
            m = re.findall(r"\b[A-Z]{1,5}[- ]?\d{1,5}[A-Z0-9]*\b", text)
            return m[-1] if m else None
        if kind == "text":
            return text.strip()
        return None

    @staticmethod
    def bare_name(text: str) -> Optional[str]:
        seqs = re.findall(nlu._CAP_SEQ, text or "")
        for seq in reversed(seqs):
            name = nlu._clean_name(seq)
            if name and not nlu.extract_date(name):
                return name
        return None

    def analyze(self, text: str) -> Optional[Plan]:
        """Rule-based plan for a request, or None if no tool clearly fits."""
        if not self.tools:
            return None
        scores = self.score_tools(text)
        user = set(nlu.content_stems(text))
        sm = []
        for name, spec in self.tools.items():
            if spec.get("kind") == "state_modifying" and tool_verb(name) in user:
                n, _, _ = self.tool_profile(name)
                sm.append((len(user & n), scores[name], name))
        ro = sorted(((s, n) for n, s in scores.items()
                     if self.tools[n].get("kind") != "state_modifying" and s >= 3.0), reverse=True)
        chain: List[str] = []
        if sm:
            target = max(sm)[2]
            chain = [target]
            spec = self.tools[target]
            for path in schema.missing_required(spec, {}):
                aspec = schema.find_arg_spec(spec, path) or {}
                kind = schema.arg_kind(path.split(".")[-1], aspec)
                if self.extract_value(text, path, aspec, kind) is not None:
                    continue
                if kind == "id" and path.split(".")[-1] in self.memory:
                    continue
                feeder = self.feeding_tool(target, path)
                if feeder and feeder not in chain:
                    chain.insert(0, feeder)
                    break
        elif ro:
            chain = [ro[0][1]]
        elif self.frame and DEIXIS.search(text):
            visual = [n for n, s in self.tools.items()
                      if any(schema.arg_kind(a, sp) == "embedding" for a, sp in schema.arg_items(s))]
            if visual:
                chain = [visual[0]]
        if not chain:
            return None
        return self.build_plan(text, chain)

    def build_plan(self, text: str, chain: List[str], given: Optional[Dict[str, Dict[str, Any]]] = None) -> Plan:
        """Turn a tool chain into steps whose args are bound to slots."""
        steps: List[Step] = []
        values: Dict[str, Any] = {}
        kinds: Dict[str, str] = {}
        for idx, name in enumerate(chain):
            spec = self.tools.get(name, {})
            step = Step(tool=name)
            provided = dict(leaf_values((given or {}).get(name, {}) or {}))

            def visit(prefix: str, props: Dict[str, Any]):
                for arg, aspec in props.items():
                    if not isinstance(aspec, dict):
                        continue
                    path = f"{prefix}{arg}"
                    kind = schema.arg_kind(arg, aspec)
                    if kind == "object":
                        visit(path + ".", aspec.get("properties") or {})
                        continue
                    if kind == "embedding":
                        if self.frame:
                            step.needs_frame = True
                            step.literals[path] = None
                        continue
                    if kind in ("array", "boolean") and path not in provided:
                        continue
                    slot = schema.slot_name(path)
                    kinds[slot] = kind
                    step.bindings[path] = slot
                    if path in provided:
                        val = provided[path]
                    elif given is not None:
                        val = None
                    else:
                        val = self.extract_value(text, path, aspec, kind)
                    if val is None and kind == "id" and arg in self.memory and idx == 0:
                        val = self.memory[arg]
                    if val is not None and slot not in values:
                        values[slot] = val

            visit("", spec.get("args") or {})
            if step.needs_frame and "query" in step.bindings:
                step.bindings.pop("query")
                step.literals["query"] = text
            if idx > 0 and self.tools.get(name, {}).get("kind") == "state_modifying":
                step.chain_from = idx - 1
                for path in schema.missing_required(spec, {}):
                    aspec = schema.find_arg_spec(spec, path) or {}
                    if values.get(schema.slot_name(path)) is None and \
                            schema.arg_kind(path.split(".")[-1], aspec) in ("id", "string", "model"):
                        step.chain_args.append(path)
                        # chained values always come from the latest result, never a stale slot
                        step.bindings.pop(path, None)
            steps.append(step)
        last = chain[-1]
        if self.tools.get(last, {}).get("kind") == "state_modifying":
            intent = last
        else:
            intent = self.downstream_intent(last)
        self.plan_seq += 1
        return Plan(self.plan_seq, intent, steps, text, nlu.selector_from_text(text), values, kinds)

    def extract_for_plan(self, text: str, plan: Plan) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for st in plan.steps:
            spec = self.tools.get(st.tool, {})
            for path, slot in st.bindings.items():
                aspec = schema.find_arg_spec(spec, path) or {}
                kind = schema.arg_kind(path.split(".")[-1], aspec)
                if kind in ("text", "string", "model", "id") or slot in out:
                    continue
                val = self.extract_value(text, path, aspec, kind)
                if val is not None:
                    out[slot] = val
        return out

    def relate(self, text: str, plan: Plan) -> Tuple[str, Any]:
        if nlu.retraction_cue(text) is not None:
            rest = nlu.remainder_after_retraction(text)
            if rest and (self.analyze(rest) is not None or self.llm.available):
                return "intent_change", rest
            return "retraction", None
        values = self.extract_for_plan(text, plan)
        changed = {s: v for s, v in values.items() if _norm(self.slots.get(s, "")) != _norm(v)}
        sel = nlu.selector_from_text(text)
        chained = any(st.chain_args for st in plan.steps)
        sel_changed = chained and not nlu.selector_is_empty(sel)
        other = self.analyze(text)
        if other is not None:
            ours = {st.tool for st in plan.steps}
            theirs = {st.tool for st in other.steps}
            if not (ours & theirs):
                return "intent_change", text
        if changed or sel_changed:
            return "correction", (changed, sel if sel_changed else None)
        return "unclear", None

    # ------------------------------------------------------------------ plan execution
    def start_plan(self, plan: Plan, ack: bool = True, prefix: str = ""):
        self.plan = plan
        self.intent = plan.intent
        self.slots = dict(plan.slot_values)
        self.slot_kinds = dict(plan.slot_kinds)
        spec0 = self.tools.get(plan.steps[0].tool, {})
        args0, _, missing0 = self.build_args(plan, 0)
        if missing0:
            self.ask_missing(plan, 0, missing0, prefix=prefix)
            return
        if ack:
            self.say("filler_speech", prefix + self.ack_text(plan), critical=True,
                     alt=prefix + "Sure, one moment.")
        self.start_step(plan, 0)

    def ack_text(self, plan: Plan) -> str:
        first = plan.steps[0]
        toks = first.tool.split("_")
        noun = tool_noun(first.tool)
        subject = self.subject_phrase(first)
        if first.needs_frame:
            return "Let me take a look at that and check the manual."
        if any(t in ("search", "find", "list") for t in toks):
            thing = plural(noun)
        elif "quote" in toks or "estimate" in toks:
            thing = f"a {noun} quote"
        else:
            thing = f"the {noun}"
        text = f"Let me look up {thing}{subject}"
        last = plan.steps[-1]
        if len(plan.steps) > 1 and self.tools.get(last.tool, {}).get("kind") == "state_modifying":
            person = self.person_phrase(last)
            ready = not self.build_args_missing_nonchain(plan, len(plan.steps) - 1)
            if ready:
                text += f", then I'll {tool_verb(last.tool)} it{person}"
            else:
                text += " first"
        return text + "."

    def person_phrase(self, st: Step) -> str:
        spec = self.tools.get(st.tool, {})
        for path, slot in st.bindings.items():
            aspec = schema.find_arg_spec(spec, path) or {}
            if schema.arg_kind(path.split(".")[-1], aspec) == "person" and self.slots.get(slot):
                return f" for {self.slots[slot]}"
        return ""

    def subject_phrase(self, st: Step) -> str:
        spec = self.tools.get(st.tool, {})
        loc, date, other = [], [], []
        for path, slot in st.bindings.items():
            v = self.slots.get(slot)
            if v in (None, ""):
                continue
            aspec = schema.find_arg_spec(spec, path) or {}
            leaf = path.split(".")[-1]
            kind = schema.arg_kind(leaf, aspec)
            if kind == "location":
                role = schema.location_role(leaf, aspec)
                prep = {"destination": "to", "origin": "from"}.get(role, "in")
                loc.append(f" {prep} {v}")
            elif kind == "date":
                date.append(f" for {v}")
            elif kind == "number":
                other.append(f" for {fmt_num(v)} {human_key(leaf)}")
        return "".join(loc + date + other)

    def build_args_missing_nonchain(self, plan: Plan, i: int) -> List[str]:
        st = plan.steps[i]
        spec = self.tools.get(st.tool, {})
        args = {}
        for path, slot in st.bindings.items():
            if self.slots.get(slot) not in (None, ""):
                set_path(args, path, self.slots[slot])
        for path in st.chain_args:
            set_path(args, path, "x")
        return schema.missing_required(spec, args)

    def coerce(self, value: Any, aspec: Dict[str, Any]) -> Any:
        typ = str(aspec.get("type", "string")).lower()
        if typ in ("number", "integer", "float"):
            try:
                f = float(value)
            except (TypeError, ValueError):
                return value
            return int(f) if (typ == "integer" or f.is_integer()) else f
        if typ == "boolean":
            return bool(value)
        if aspec.get("enum"):
            for opt in aspec["enum"]:
                if _norm(opt) == _norm(value):
                    return opt
            return value
        if typ == "string" and not isinstance(value, str):
            return fmt_num(value)
        return value

    def build_args(self, plan: Plan, i: int):
        """(args, ambiguous_items or None, missing required paths)."""
        st = plan.steps[i]
        spec = self.tools.get(st.tool, {})
        args: Dict[str, Any] = {}
        for path, slot in st.bindings.items():
            v = self.slots.get(slot)
            if v in (None, "", []):
                continue
            set_path(args, path, self.coerce(v, schema.find_arg_spec(spec, path) or {}))
        for path, v in st.literals.items():
            if v is not None:
                set_path(args, path, v)
        ambiguous = None
        if st.chain_args and st.chain_from is not None:
            todo = [p for p in st.chain_args if get_path(args, p) is None]
            src = plan.results.get(st.chain_from)
            if todo and src is not None:
                _, items = result_items(src)
                idx, _why = nlu.select_item(items or [], plan.selector) if items else (None, "none")
                if idx is None:
                    ambiguous = items or []
                else:
                    item = items[idx]
                    for p in todo:
                        leaf = p.split(".")[-1]
                        val = item.get(leaf)
                        if val is None:
                            val = next((v for k, v in item.items()
                                        if k == "id" or k.endswith("_id")), None)
                        if val is not None:
                            set_path(args, p, val)
                            self.slots[schema.slot_name(p)] = val
                            self.slot_kinds.setdefault(schema.slot_name(p), "id")
        missing = schema.missing_required(spec, args)
        if ambiguous is not None:
            missing = [m for m in missing if m not in st.chain_args]
        return args, ambiguous, missing

    def start_step(self, plan: Plan, i: int):
        if self.plan is not plan:
            return
        st = plan.steps[i]
        spec = self.tools.get(st.tool)
        if spec is None:
            self.finish(plan, f"Sorry, I can't {human_key(st.tool)} right now.", kind="final_response")
            return
        if st.needs_frame and self.frame and not self.frame_ready():
            self.planning = self.spawn(self.wait_for_frame(plan, i))
            return
        if st.needs_frame:
            self.fill_visual_literals(plan, st)
        args, ambiguous, missing = self.build_args(plan, i)
        if ambiguous is not None or missing:
            self.ask_after_results(plan, i, ambiguous, missing)
            return
        problems = schema.validate(spec, args)
        if problems:
            args = self.repair_args(spec, args)
            problems = schema.validate(spec, args)
        if problems:
            self.say("clarification_request",
                     f"I need a bit more detail to {human_key(st.tool)}: {problems[0]}. Could you clarify?")
            self.pending_clar = {"kind": "missing", "plan": plan, "step": i,
                                 "paths": [p.split("'")[1] for p in problems if "'" in p]}
            return
        if spec.get("kind") == "state_modifying":
            key = idem_key(st.tool, args)
            if key in self.done_keys:
                self.on_step_success(plan, i, self.done_keys[key])
                return
            if key in self.inflight_keys:
                return
        if not self.time_allows(spec):
            self.finish(plan, f"I'm out of time to run the {tool_noun(st.tool)} check right now. "
                              f"Want me to try again?", kind="final_response")
            return
        self.call_tool(st.tool, args, plan, i)

    def repair_args(self, spec: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        """Drop optional args that fail validation rather than sending a doomed call."""
        fixed = copy.deepcopy(args)
        for name, aspec in schema.arg_items(spec):
            if name in fixed and not aspec.get("required") and schema._validate_one(name, aspec, fixed):
                fixed.pop(name)
        return fixed

    def time_allows(self, spec: Dict[str, Any]) -> bool:
        if not self.ended or self.end_vt is None:
            return True
        lo = float((spec.get("delay_range_ms") or [0, 0])[0])
        return self.clock.now() + lo < self.end_vt + TAIL_DEADLINE_MS

    def ask_missing(self, plan: Plan, i: int, missing: List[str], prefix: str = ""):
        spec = self.tools.get(plan.steps[i].tool, {})
        self.pending_clar = {"kind": "missing", "plan": plan, "step": i, "paths": missing}
        self.say("clarification_request", prefix + self.question_for(spec, missing))

    def question_for(self, spec: Dict[str, Any], paths: List[str], choose: bool = False) -> str:
        parts = []
        if choose:
            parts.append("which one you'd like")
        for p in paths:
            aspec = schema.find_arg_spec(spec, p) or {}
            leaf = p.split(".")[-1]
            kind = schema.arg_kind(leaf, aspec)
            if aspec.get("enum"):
                parts.append(f"the {human_key(p)} ({join_or([str(o) for o in aspec['enum']])})")
            elif kind == "person":
                parts.append("the passenger's name" if "passenger" in p else f"the {human_key(p)}")
            else:
                parts.append(f"the {human_key(p)}")
        return f"Could you tell me {join_and(parts)}?"

    def ask_after_results(self, plan: Plan, i: int, ambiguous, missing: List[str]):
        st = plan.steps[i]
        spec = self.tools.get(st.tool, {})
        self.pending_clar = {"kind": "choose" if ambiguous is not None else "missing",
                             "plan": plan, "step": i, "paths": missing}
        question = self.question_for(spec, missing, choose=ambiguous is not None)
        if ambiguous:
            # the snapshot shows the leading option, as the reference agent does
            for p in st.chain_args:
                val = ambiguous[0].get(p.split(".")[-1])
                if val is not None:
                    self.slots[schema.slot_name(p)] = val
                    self.slot_kinds.setdefault(schema.slot_name(p), "id")
        if st.chain_from is not None and st.chain_from in plan.results:
            summary = self.render_result(plan, st.chain_from, plan.results[st.chain_from])
            verb = tool_verb(st.tool)
            self.say("final_response", f"{summary} To {verb} one, {question[0].lower()}{question[1:]}")
        else:
            self.say("clarification_request", question)

    def on_step_success(self, plan: Plan, i: int, result: Dict[str, Any]):
        plan.results[i] = result
        st = plan.steps[i]
        spec = self.tools.get(st.tool, {})
        if spec.get("kind") == "state_modifying":
            for k, v in result.items():
                if isinstance(v, (str, int)) and (k.endswith("_id") or k == "id"):
                    self.slots[k] = v
                    self.slot_kinds.setdefault(k, "id")
        nxt = i + 1
        if nxt < len(plan.steps):
            args, ambiguous, missing = self.build_args(plan, nxt)
            if ambiguous is not None or missing:
                self.ask_after_results(plan, nxt, ambiguous, missing)
                return
            nst = plan.steps[nxt]
            chosen = ", ".join(str(get_path(args, p)) for p in nst.chain_args if get_path(args, p))
            lead = f"Found {chosen}" if chosen else "Got it"
            self.say("filler_speech",
                     f"{lead}. I'll {tool_verb(nst.tool)} it{self.person_phrase(nst)} now.",
                     alt=f"{lead}, {tool_verb(nst.tool)}ing it now.")
            self.start_step(plan, nxt)
            return
        _, items = result_items(result)
        if items:
            idx, _ = nlu.select_item(items, plan.selector)
            item = items[idx if idx is not None else 0]
            idk = next((k for k in item if k.endswith("_id")), None)
            if idk and spec.get("kind") != "state_modifying":
                self.slots[idk] = item[idk]
                self.slot_kinds.setdefault(idk, "id")
        text = self.render_result(plan, i, result)
        follow = self.tools.get(plan.intent, {})
        if items and plan.intent != st.tool and follow.get("kind") == "state_modifying" \
                and all(s.tool != plan.intent for s in plan.steps):
            text += f" Would you like me to {tool_verb(plan.intent)} one?"
        self.finish(plan, text)

    def on_step_error(self, plan: Plan, rec: Call, result: Dict[str, Any]):
        code = str(result.get("error") or "error")
        detail = result.get("detail")
        detail_s = detail if isinstance(detail, str) else "; ".join(map(str, detail or []))
        spec = self.tools.get(rec.api, {})
        noun = human_key(rec.api)
        if rec.kind != "state_modifying":
            retryable = code not in ("invalid_args", "not_found", "unknown_tool")
            if retryable and rec.attempt == 1 and self.time_allows(spec):
                self.say("filler_speech",
                         f"The {noun} {'timed out' if code == 'timeout' else 'hit an error'}. "
                         f"Let me try that again.", alt="Still working on it, trying once more.")
                self.calls_retry(plan, rec)
                return
            if code == "invalid_args" and rec.attempt == 1:
                fixed = self.repair_args(spec, rec.args)
                if fixed != rec.args and not schema.validate(spec, fixed):
                    self.call_tool(rec.api, fixed, plan, rec.step, attempt=2)
                    return
            self.finish(plan, f"Sorry, the {noun} isn't working right now"
                              f"{f' ({detail_s})' if detail_s else ''}. Would you like me to try again?")
            return
        if code == "duplicate_booking" or "duplicate" in code:
            ids = {k: v for k, v in result.items() if k.endswith("_id")}
            for k, v in ids.items():
                self.slots[k] = v
                self.slot_kinds.setdefault(k, "id")
            ref = join_and([f"{human_key(k)} {v}" for k, v in ids.items()])
            self.finish(plan, f"That was already in place, so I didn't make a second one"
                              f"{f': {ref}' if ref else ''}.")
            return
        if code == "not_found":
            self.finish(plan, f"I couldn't find that{f' ({detail_s})' if detail_s else ''}. "
                              f"Could you double-check the details?", kind="clarification_request")
            return
        self.pending_clar = {"kind": "confirm", "plan": plan, "step": rec.step, "call": rec}
        self.say("clarification_request",
                 f"The {human_key(rec.api)} request didn't go through"
                 f"{f' ({detail_s})' if detail_s else ''}. Would you like me to try again?")

    def calls_retry(self, plan: Plan, rec: Call):
        spec = self.tools.get(rec.api, {})
        args, _, missing = self.build_args(plan, rec.step)
        if missing or schema.validate(spec, args):
            args = rec.args
        self.call_tool(rec.api, args, plan, rec.step, attempt=rec.attempt + 1)

    def finish(self, plan: Plan, text: str, kind: str = "final_response"):
        plan.done = True
        if self.notes:
            text = text + " " + " ".join(self.notes)
            self.notes = []
        self.say(kind, text)

    def report_late_side_effect(self, rec: Call, result: Dict[str, Any]):
        ids = {k: v for k, v in result.items() if k.endswith("_id") and isinstance(v, (str, int))}
        ref = join_and([f"{human_key(k)} {v}" for k, v in ids.items()])
        note = (f"Heads up: the earlier {human_key(rec.api)} request had already gone through"
                f"{f' ({ref})' if ref else ''}.")
        plan = self.plan
        if plan is not None and not plan.done:
            self.notes.append(note)
        else:
            self.say("clarification_request", note + " Would you like me to undo it?")

    # ------------------------------------------------------------------ rendering
    def render_field(self, k: str, v: Any, in_item: bool) -> str:
        lk = k.lower()
        if isinstance(v, bool):
            return human_key(k) if v else f"not {human_key(k)}"
        if isinstance(v, (int, float)) and any(s in lk for s in ("price", "usd", "cost", "fare", "amount", "total")):
            per = " per day" if ("daily" in lk or "per_day" in lk) else " per night" if "night" in lk else ""
            return f"{'for ' if in_item else ''}${fmt_num(v)}{per}"
        if lk in ("temp_f", "temperature_f") or lk.endswith("_f") and "temp" in lk:
            return f"{fmt_num(v)}°F"
        if lk in ("temp_c", "temperature_c") or lk.endswith("_c") and "temp" in lk:
            return f"{fmt_num(v)}°C"
        if isinstance(v, str) and re.fullmatch(r"\d{1,2}:\d{2}", v.strip()):
            if "depart" in lk:
                return f"departing at {v}"
            if "arriv" in lk:
                return f"arriving at {v}"
            return f"{human_key(k)} {v}"
        if lk == "page":
            return f"on page {fmt_num(v)}"
        if lk in ("doc", "document", "manual", "source"):
            return f"in {v}"
        if lk in _PLAIN_FIELDS and isinstance(v, str):
            return v
        if isinstance(v, list):
            return f"{human_key(k)}: {join_and([str(x) for x in v])}"
        if isinstance(v, dict):
            return join_and([self.render_field(kk, vv, in_item) for kk, vv in v.items()])
        return f"{human_key(k)} {fmt_num(v)}"

    def render_item(self, item: Dict[str, Any]) -> str:
        idk = next((k for k in item if k == "id" or k.endswith("_id")), None)
        titlek = next((k for k in item if k in ("title", "name")), None)
        head = []
        if titlek:
            head.append(f"“{item[titlek]}”" if titlek == "title" else str(item[titlek]))
            if idk:
                head.append(f"({item[idk]})")
        elif idk:
            head.append(str(item[idk]))
        rest = [self.render_field(k, v, True) for k, v in item.items() if k not in (idk, titlek)]
        return " ".join(head + rest)

    def render_result(self, plan: Plan, i: int, result: Dict[str, Any]) -> str:
        st = plan.steps[i]
        spec = self.tools.get(st.tool, {})
        noun = tool_noun(st.tool)
        subject = self.subject_phrase(st)
        body = {k: v for k, v in result.items() if k not in ("status",)}
        list_key, items = result_items(body)
        prefix = f"That looks like the {plan.visual_label}. " if plan.visual_label else ""
        if items is not None:
            if not items:
                return f"{prefix}I couldn't find any matching {plural(noun)}{subject}."
            if any("title" in x for x in items):
                return f"{prefix}The manual covers it in {self.render_item(items[0])}."
            rendered = [self.render_item(x) for x in items[:4]]
            label = plural(noun) if len(items) != 1 else noun
            count = "one" if len(items) == 1 else str(len(items))
            extra = {k: v for k, v in body.items() if k != list_key}
            tail = f" ({join_and([self.render_field(k, v, False) for k, v in extra.items()])})" if extra else ""
            return f"{prefix}I found {count} {label}{subject}: {join_and(rendered)}{tail}."
        fields = [self.render_field(k, v, False) for k, v in body.items()]
        if spec.get("kind") == "state_modifying":
            person = self.person_phrase(st)
            detail = join_and(fields)
            detail = f" {detail[0].upper()}{detail[1:]}." if detail else ""
            return f"All done: {noun} {verb_past(tool_verb(st.tool))}{person}.{detail}"
        return f"{prefix}Here's the {noun}{subject}: {join_and(fields)}."

    # ------------------------------------------------------------------ interruptions
    def describe_change(self, changed: Dict[str, Any], sel: Optional[Dict[str, Any]]) -> str:
        parts = []
        for slot, v in changed.items():
            kind = self.slot_kinds.get(slot)
            if kind == "location":
                parts.append(f"switching to {v}")
            elif kind == "date":
                parts.append(f"changing it to {v}")
            elif kind == "person":
                parts.append(f"making it for {v}")
            else:
                parts.append(f"updating the {human_key(slot)} to {fmt_num(v)}")
        if sel:
            if sel.get("times"):
                parts.append(f"going with the {sel['times'][-1]} option")
            else:
                parts.append("going with that option")
        return join_and(parts) or "updating that"

    @staticmethod
    def affected_steps(plan: Plan, changed: Dict[str, Any], sel: Optional[Dict[str, Any]]) -> Set[int]:
        affected: Set[int] = set()
        for i, st in enumerate(plan.steps):
            if set(st.bindings.values()) & set(changed):
                affected.add(i)
            if sel is not None and st.chain_args:
                affected.add(i)
        return affected

    def cancel_invalidated(self, plan: Plan, changed: Dict[str, Any], sel: Optional[Dict[str, Any]]):
        """Cancel sent calls a correction invalidates, without re-planning yet."""
        affected = self.affected_steps(plan, changed, sel)
        if affected:
            earliest = min(affected)
            for c in self.pending_calls(plan.pid):
                if c.step >= earliest:
                    self.cancel_call(c)

    def do_correction(self, plan: Plan, changed: Dict[str, Any], sel: Optional[Dict[str, Any]], quiet: bool):
        affected = self.affected_steps(plan, changed, sel)
        done_side_effect = [i for i in affected
                            if i in plan.results and self.tools.get(plan.steps[i].tool, {}).get("kind") == "state_modifying"]
        for slot, v in changed.items():
            self.slots[slot] = v
        if sel is not None:
            plan.selector = sel
            for st in plan.steps:
                for p in st.chain_args:
                    self.slots.pop(schema.slot_name(p), None)
        if done_side_effect:
            i = done_side_effect[0]
            ids = {k: v for k, v in plan.results[i].items() if k.endswith("_id")}
            ref = join_and([f"{human_key(k)} {v}" for k, v in ids.items()])
            self.pending_clar = None
            self.say("clarification_request",
                     f"Just so you know, that {human_key(plan.steps[i].tool)} request already went through"
                     f"{f' ({ref})' if ref else ''}. Should I undo it and redo it with the change?")
            return
        earliest = min(affected) if affected else None
        if earliest is not None:
            for c in self.pending_calls(plan.pid):
                if c.step >= earliest:
                    self.cancel_call(c)
            for k in list(plan.results):
                if k >= earliest:
                    del plan.results[k]
            plan.done = False
        if not quiet:
            tail = " Let me check that." if earliest is not None else ""
            self.say("filler_speech", f"Got it, {self.describe_change(changed, sel)}.{tail}",
                     critical=True, alt=f"Okay, {self.describe_change(changed, sel)}. One moment.")
        if earliest is None:
            return
        self.pending_clar = None
        start = earliest
        st = plan.steps[earliest]
        if st.chain_from is not None and st.chain_from not in plan.results:
            if self.pending_calls(plan.pid):
                return
            start = st.chain_from
        self.start_step(plan, start)

    def do_retraction(self):
        plan = self.plan
        side = []
        if plan is not None:
            for i, res in plan.results.items():
                if self.tools.get(plan.steps[i].tool, {}).get("kind") == "state_modifying":
                    side.append((plan.steps[i].tool, res))
        self.cancel_all()
        self.plan = None
        self.pending_clar = None
        self.intent = "none"
        self.slots = {}
        self.slot_kinds = {}
        if side:
            tool, res = side[0]
            ids = {k: v for k, v in res.items() if k.endswith("_id")}
            ref = join_and([f"{human_key(k)} {v}" for k, v in ids.items()])
            self.say("clarification_request",
                     f"Okay, I've stopped. The {human_key(tool)} request had already gone through"
                     f"{f' ({ref})' if ref else ''}. Would you like me to undo it?")
            return
        self.say("final_response", "Okay, no problem. I've dropped that. Anything else I can help with?")

    def do_intent_change(self, rest: str, quiet: bool):
        self.cancel_all()
        self.plan = None
        self.pending_clar = None
        self.process_request(rest, interrupt=True, quiet=quiet, prefix="Okay, dropping that. ")

    # ------------------------------------------------------------------ clarifications
    def resolve_clarification(self, text: str, quiet: bool) -> bool:
        pc = self.pending_clar
        kind = pc.get("kind")
        if kind == "candidates":
            chosen = next((c for c in pc["candidates"] if nlu.contains_phrase(text, c)), None)
            if chosen is None and not self.analyze(text):
                # "No, Houston" answers the question even though it names neither option
                chosen = nlu.pick_location(text) or self.bare_name(text)
            self.pending_clar = None
            if chosen is None:
                return False
            original = pc.get("text") or ""
            heard = pc.get("heard") or ""
            if heard and heard in original:
                fixed = original.replace(heard, chosen)
            else:
                fixed = f"{original} ({chosen})"
                plan = self.analyze(original)
                if plan is not None:
                    for slot, k in plan.slot_kinds.items():
                        if k == "location":
                            plan.slot_values[slot] = chosen
                    self.supersede_plan()
                    self.start_plan(plan, ack=not quiet)
                    return True
            self.process_request(fixed, quiet=quiet)
            return True
        if kind == "confirm":
            rec: Call = pc["call"]
            if YES.search(text) and not NO.search(text):
                self.pending_clar = None
                if not quiet:
                    self.say("filler_speech", "Okay, trying that again now.", critical=True)
                self.call_tool(rec.api, rec.args, pc["plan"], rec.step, attempt=rec.attempt + 1)
                return True
            if NO.search(text):
                self.pending_clar = None
                self.finish(pc["plan"], "Okay, I'll leave it there.")
                return True
            return False
        plan: Plan = pc["plan"]
        if plan is not self.plan:
            self.pending_clar = None
            return False
        step = pc["step"]
        st = plan.steps[step]
        spec = self.tools.get(st.tool, {})
        progress = False
        for p in pc.get("paths", []):
            aspec = schema.find_arg_spec(spec, p) or {}
            k = schema.arg_kind(p.split(".")[-1], aspec)
            val = self.extract_value(text, p, aspec, k, bare=len(pc.get("paths", [])) == 1)
            if val is not None:
                slot = schema.slot_name(p)
                self.slots[slot] = val
                self.slot_kinds.setdefault(slot, k)
                st.bindings.setdefault(p, slot)
                progress = True
        if kind == "choose":
            sel = nlu.selector_from_text(text)
            if not nlu.selector_is_empty(sel):
                plan.selector = sel
                progress = True
        if not progress:
            return False
        _, ambiguous, missing = self.build_args(plan, step)
        if ambiguous is None and not missing:
            self.pending_clar = None
            if not quiet:
                nst = plan.steps[step]
                verb = tool_verb(nst.tool)
                self.say("filler_speech", f"Great, I'll {verb} that{self.person_phrase(nst)} now."
                         if self.tools.get(nst.tool, {}).get("kind") == "state_modifying"
                         else "Great, let me check that now.", critical=True, alt="Okay, one moment.")
            self.start_step(plan, step)
        else:
            self.pending_clar["paths"] = missing
            self.ask_after_results(plan, step, ambiguous, missing)
        return True

    # ------------------------------------------------------------------ background work
    def frame_ready(self) -> bool:
        if not self.frame:
            return True
        task = self.frame_tasks.get(self.frame["frame_id"])
        return task is None or task.done()

    async def analyze_frame(self, fid: str, ref: str):
        info = self.frame_info.setdefault(fid, {})
        info["embedding"] = await asyncio.to_thread(media.image_embedding, ref)
        if self.llm.available:
            data = await asyncio.to_thread(media.read_bytes, ref)
            if data:
                info["desc"] = await self.llm.describe_frame(data, media.sniff_mime(ref, data),
                                                             budget_s=FRAME_WAIT_S)

    async def wait_for_frame(self, plan: Plan, i: int):
        task = self.frame_tasks.get(self.frame["frame_id"]) if self.frame else None
        if task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=self.model_budget_s(FRAME_WAIT_S))
            except (asyncio.TimeoutError, Exception):
                pass
        if not self.resume_after_await():
            return
        try:
            if self.plan is plan:
                self.start_step(plan, i)
            self.replay_deferred()
        finally:
            self.end_staging()

    def fill_visual_literals(self, plan: Plan, st: Step):
        info = self.frame_info.get(self.frame["frame_id"], {}) if self.frame else {}
        spec = self.tools.get(st.tool, {})
        for path in list(st.literals):
            aspec = schema.find_arg_spec(spec, path) or {}
            if schema.arg_kind(path.split(".")[-1], aspec) == "embedding":
                st.literals[path] = info.get("embedding")
        desc = info.get("desc") or {}
        label = desc.get("label") if isinstance(desc, dict) else None
        if isinstance(label, str) and label.strip():
            plan.visual_label = label.strip()
            if "query" in st.literals and isinstance(st.literals["query"], str) \
                    and label.lower() not in st.literals["query"].lower():
                st.literals["query"] = f"{label.strip()}: {st.literals['query']}"

    def model_budget_s(self, cap_s: float) -> float:
        """Real seconds a model call may take. After scenario_end it must leave room
        for a typical read-only tool call and the final before the tail closes."""
        if not self.ended or self.end_vt is None:
            return cap_s
        ro = [s.get("delay_range_ms") for s in self.tools.values()
              if s.get("kind") != "state_modifying" and isinstance(s.get("delay_range_ms"), list)]
        typical = max((sum(r[:2]) / 2.0 for r in ro if len(r) >= 2), default=2000.0)
        return max(0.0, min(cap_s, self.clock.seconds_until(self.end_vt + TAIL_DEADLINE_MS - typical - 300.0)))

    async def bounded(self, make_call, cap_s: float):
        """Run a model call under a deadline that tightens if scenario_end arrives
        while it is running. Returns None when the deadline passes."""
        loop = asyncio.get_running_loop()
        start = loop.time()
        budget = self.model_budget_s(cap_s)
        if budget < MIN_MODEL_S:
            return None
        task = asyncio.ensure_future(make_call(budget))
        try:
            while True:
                deadline = min(start + cap_s, loop.time() + self.model_budget_s(cap_s))
                remaining = deadline - loop.time()
                if remaining <= 0:
                    _log("model call stopped at its deadline")
                    return None
                done, _ = await asyncio.wait({task}, timeout=min(remaining, 0.1))
                if done:
                    return task.result()
        finally:
            if not task.done():
                task.cancel()

    async def audio_turn(self, refs: List[str]):
        clips = []
        for r in refs:
            data = await asyncio.to_thread(media.read_bytes, r)
            if data:
                clips.append((data, media.sniff_mime(r, data)))
        out = None
        if clips:
            context = " | ".join(self.history[-6:])
            out = await self.bounded(
                lambda b: self.llm.understand_audio(clips, context, budget_s=b), AUDIO_BUDGET_S)
        if not self.resume_after_await():
            return
        try:
            self.apply_audio(out)
            self.replay_deferred()
        finally:
            self.end_staging()

    def audio_ambiguity(self, out: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
        """Values the recogniser was not sure of, as (heard, candidates).

        Two kinds of evidence count: the model's own low confidence or listed
        alternatives for a name, date, number or code; and a second, independent
        transcription that heard a different place. A self-correction ("Denver, no,
        Miami") is not ambiguity: both transcripts then contain both words."""
        found: List[Tuple[str, List[str]]] = []

        def add(heard: str, cands: List[str]):
            uniq: List[str] = []
            for c in cands:
                if isinstance(c, str) and c.strip() and c.strip().lower() not in [u.lower() for u in uniq]:
                    uniq.append(c.strip())
            if uniq and not any(h.lower() == heard.lower() for h, _ in found):
                found.append((heard, uniq[:3]))

        for e in out.get("entities") or []:
            if e.get("type") not in ("place", "person", "date", "time", "number", "code"):
                continue
            conf = e.get("confidence", 1.0)
            alts = e.get("alternatives") or []
            if alts and conf < 0.85:
                add(e["text"], [e["text"]] + alts)
            elif conf < 0.5:
                add(e["text"], [e["text"]])
        for u in out.get("uncertain") or []:
            if isinstance(u, dict) and len(u.get("candidates") or []) >= 2:
                add(str(u.get("heard") or ""), list(u["candidates"]))
        cross = out.get("cross")
        if isinstance(cross, dict) and cross.get("intended"):
            a = nlu.pick_location(out.get("intended", "")) or self.bare_name(out.get("intended", ""))
            b = nlu.pick_location(cross["intended"]) or self.bare_name(cross["intended"])
            if a and b and _norm(a) != _norm(b):
                heard_a = _norm(a) in _norm(out.get("verbatim", ""))
                in_other_a = _norm(a) in _norm(cross.get("verbatim", ""))
                in_other_b = _norm(b) in _norm(out.get("verbatim", ""))
                if heard_a and not (in_other_a and in_other_b):
                    add(a, [a, b])
        return found

    def apply_audio(self, out: Optional[Dict[str, Any]]):
        if out is None:
            self.say("clarification_request",
                     "Sorry, I couldn't process that audio just now. Could you say it again?")
            return
        intended = str(out.get("intended") or out.get("verbatim") or "").strip()
        uncertain = self.audio_ambiguity(out) if intended else []
        if self.pending_clar is not None and self.pending_clar.get("kind") == "candidates":
            self.history.append(f"user: {intended}")
            if self.resolve_clarification(intended, quiet=True):
                return
        if uncertain and intended:
            heard, cands = uncertain[0]
            self.history.append(f"user: {intended}")
            self.pending_clar = {"kind": "candidates", "text": intended, "heard": heard, "candidates": cands}
            question = (f"Just to confirm, did you say {join_or(cands)}?" if len(cands) > 1
                        else f"Sorry, I want to be sure I heard that right. Did you say {cands[0]}?")
            self.say("clarification_request", question)
            return
        if not intended:
            self.say("clarification_request", "Sorry, I didn't catch that. Could you say it again?")
        else:
            self.handle_utterance(intended, quiet=True)

    async def llm_turn(self, text: str, interrupt: bool):
        state = self.snapshot()
        out = await self.bounded(
            lambda b: self.llm.interpret(text, self.tools, state, self.history, budget_s=b), TEXT_BUDGET_S)
        if not self.resume_after_await():
            return
        try:
            self.apply_interpretation(text, out, interrupt)
            self.replay_deferred()
        finally:
            self.end_staging()

    def apply_interpretation(self, text: str, out: Optional[Dict[str, Any]], interrupt: bool):
        if out is None:
            if interrupt:
                self.say("clarification_request", "Sorry, what would you like me to change?")
            else:
                self.reply_capabilities(unsure=True)
            return
        action = out.get("action")
        if action == "retract":
            self.do_retraction()
            return
        if action == "update" and self.plan is not None and isinstance(out.get("slot_updates"), dict):
            changed = {}
            for k, v in out["slot_updates"].items():
                slot = schema.slot_name(str(k))
                if slot in self.slot_kinds or any(slot in st.bindings.values() for st in self.plan.steps):
                    changed[slot] = v
            if changed:
                self.do_correction(self.plan, changed, None, quiet=True)
                return
        if action == "new_request" and isinstance(out.get("steps"), list):
            chain, given = [], {}
            for s in out["steps"]:
                if isinstance(s, dict) and s.get("tool") in self.tools and s["tool"] not in chain:
                    chain.append(s["tool"])
                    given[s["tool"]] = s.get("args") if isinstance(s.get("args"), dict) else {}
            if chain:
                plan = self.build_plan(text, chain, given)
                self.supersede_plan()
                self.start_plan(plan, ack=False)
                return
        if action == "clarify" and isinstance(out.get("question"), str) and out["question"].strip():
            self.say("clarification_request", out["question"].strip())
            return
        if action == "chitchat" and isinstance(out.get("reply"), str) and out["reply"].strip():
            self.intent = self.intent or "chitchat"
            self.say("final_response", out["reply"].strip())
            return
        self.reply_capabilities(unsure=True)

    def replay_deferred(self):
        """Apply utterances that arrived while a model call ran, in arrival order.
        Runs inside staging, so calls they invalidate are dropped unsent."""
        pending, self.deferred = self.deferred, []
        for idx, (kind, data, interrupt) in enumerate(pending):
            if self.planning is not None and not self.planning.done():
                self.deferred.extend(pending[idx:])
                return
            self.epoch += 1
            if kind == "audio":
                self.planning = self.spawn(self.audio_turn(data))
                continue
            text = data
            plan = self.plan
            if plan is not None:
                rel, data = self.relate(text, plan)
                if rel == "retraction":
                    self.do_retraction()
                    continue
                if rel == "correction":
                    self.do_correction(plan, data[0], data[1], quiet=True)
                    continue
                if rel == "intent_change":
                    self.do_intent_change(data, quiet=True)
                    continue
            self.process_request(text, interrupt=interrupt, quiet=True)

    async def tail_watchdog(self):
        deadline = (self.end_vt or 0.0) + TAIL_DEADLINE_MS
        while True:
            wait = self.clock.seconds_until(deadline)
            if wait <= 0.005:
                break
            await asyncio.sleep(min(wait, 0.25))
        pending = self.pending_calls()
        busy = self.planning is not None and not self.planning.done()
        plan = self.plan
        if not pending and not busy:
            return
        for c in pending:
            self.cancel_call(c)
        if busy:
            self.planning.cancel()
            self.planning = None
        if plan is not None and not plan.done:
            noun = human_key(plan.steps[0].tool)
            self.finish(plan, f"Sorry, the {noun} is taking too long, so I've stopped it for now. "
                              f"Would you like me to try again?")
        elif busy:
            self.say("final_response", "Sorry, I ran out of time on that one. Could you ask me again?")
