"""Optional Gemini layer (async). Every call runs against a deadline and returns
None on failure, so the agent always has its rule-based path to fall back on.

Enabled when a key is present in SECRET_GEMINI_API_KEY, GEMINI_API_KEY or
GOOGLE_API_KEY and `google-genai` is installed. At setup (off the clock) the
available Flash models are probed, including with a short audio clip, and only
models that answer are used, best first. A call that fails with a transient
error (503, 429, timeout) moves on to the next healthy model while time remains.

THEME5_GEMINI_MODEL pins one model; THEME5_AUDIO_CROSSCHECK=0 turns off the
second, independent audio transcription used as ambiguity evidence.
"""

from __future__ import annotations
import asyncio
import json
import os
import re
import struct
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

_KEY_VARS = ("SECRET_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")
PREFERRED_MODELS = ("gemini-3.8-flash", "gemini-3.5-flash", "gemini-3.5-flash-lite",
                    "gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash")
_EXCLUDE = ("live", "tts", "image", "embedding", "transcribe", "audio-dialog", "native-audio",
            "thinking-exp", "computer-use", "robotics")
MAX_PROBES = 6

_CLIENT: Any = None
_TYPES: Any = None
_MODELS: List[str] = []          # answer text + JSON, best first
_AUDIO_MODELS: List[str] = []    # also accept audio input, best first
_NO_THINKING_CONFIG: set = set()
_INIT_DONE = False
_AUTH_FAILED = False

_AUTH_ERRORS = ("api key not valid", "api_key_invalid", "permission_denied", "unauthenticated",
                "api key expired", "api_key_expired")
_TRANSIENT = ("503", "unavailable", "overloaded", "429", "resource_exhausted", "rate limit",
              "500", "internal", "504", "deadline", "temporarily", "try again")
_NOT_FOUND = ("404", "not_found", "not found", "is not supported", "unsupported model")


def _log(msg: str):
    print(f"[agent.llm] {msg}", file=sys.stderr)


def _api_key() -> Optional[str]:
    for var in _KEY_VARS:
        val = os.environ.get(var, "").strip()
        if val:
            return val
    return None


def _silent_wav(ms: int = 400, rate: int = 16000) -> bytes:
    data = b"\x00\x00" * (rate * ms // 1000)
    fmt = struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    return b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + fmt + b"data" + \
        struct.pack("<I", len(data)) + data


def _classify(err: Exception) -> str:
    low = f"{type(err).__name__} {err}".lower()
    if any(s in low for s in _AUTH_ERRORS):
        return "auth"
    if any(s in low for s in _NOT_FOUND):
        return "not_found"
    if any(s in low for s in _TRANSIENT):
        return "transient"
    return "error"


class LLM:
    """Thin async wrapper; `available` is False when no key, SDK or healthy model exists."""

    def __init__(self):
        self.available = _CLIENT is not None and bool(_MODELS)
        self.audio_available = _CLIENT is not None and bool(_AUDIO_MODELS)

    # ------------------------------------------------------------------ calls
    async def _call(self, model: str, parts: List[Any], timeout: float) -> Tuple[Optional[Dict[str, Any]], str]:
        """One attempt. Returns (parsed JSON or None, outcome)."""
        global _AUTH_FAILED
        cfg: Dict[str, Any] = {"response_mime_type": "application/json", "temperature": 0.0}
        try:
            # plain JSON calls; no functions are offered to the model
            cfg["automatic_function_calling"] = _TYPES.AutomaticFunctionCallingConfig(disable=True)
        except Exception:
            pass
        if model not in _NO_THINKING_CONFIG:
            try:
                cfg["thinking_config"] = _TYPES.ThinkingConfig(thinking_budget=0)
            except Exception:
                _NO_THINKING_CONFIG.add(model)
        try:
            resp = await asyncio.wait_for(
                _CLIENT.aio.models.generate_content(
                    model=model, contents=parts, config=_TYPES.GenerateContentConfig(**cfg)),
                timeout=max(timeout, 0.05))
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            return None, "timeout"
        except Exception as e:
            kind = _classify(e)
            if kind == "auth":
                _AUTH_FAILED = True
                _log(f"Gemini rejected the API key ({type(e).__name__}: {str(e)[:120]})")
                return None, kind
            if "think" in str(e).lower() and model not in _NO_THINKING_CONFIG:
                _NO_THINKING_CONFIG.add(model)
                return await self._call(model, parts, timeout)
            _log(f"{model}: {kind}: {str(e)[:160]}")
            return None, kind
        out = _parse_json(getattr(resp, "text", None))
        return out, ("ok" if out is not None else "bad_output")

    async def _generate(self, parts: List[Any], budget_s: float, models: Optional[List[str]] = None,
                        check=None) -> Optional[Dict[str, Any]]:
        """Try models in order until one returns valid output or the budget runs out."""
        if _CLIENT is None:
            return None
        loop = asyncio.get_running_loop()
        deadline = loop.time() + max(budget_s, 0.0)
        for model in list(models if models is not None else _MODELS):
            remaining = deadline - loop.time()
            if remaining < 0.3 or _AUTH_FAILED:
                break
            out, outcome = await self._call(model, parts, remaining)
            if outcome == "ok" and (check is None or check(out)):
                _promote(model)
                return out
            if outcome == "not_found":
                _drop(model)
            if outcome == "timeout":
                _log(f"{model}: no answer within {remaining:.1f}s")
        return None

    def _part(self, data: bytes, mime: str) -> Any:
        return _TYPES.Part.from_bytes(data=data, mime_type=mime)

    # ------------------------------------------------------------------ tasks
    async def understand_audio(self, clips: Sequence[Tuple[bytes, str]], context: str,
                               budget_s: float = 6.0) -> Optional[Dict[str, Any]]:
        """Transcribe one user turn. Returns {"intended", "verbatim", "entities",
        "cross": second model's result or None}."""
        if not self.audio_available:
            return None
        prompt = (
            "You are the speech-recognition stage of a voice assistant. The audio clips are "
            "consecutive parts of ONE user turn. Return JSON with keys:\n"
            '  "verbatim": the exact words heard, including hesitations and self-corrections;\n'
            '  "intended": the request the user means after applying their own '
            "self-corrections (when they name one thing and then correct it, keep only the "
            "correction);\n"
            '  "entities": for every place, person, date, time, number or code in "intended", '
            '{"type": one of place|person|date|time|number|code, "text": the value as heard, '
            '"confidence": 0.0-1.0 acoustic confidence, "alternatives": other real names or '
            "words the same sounds could plausibly be}.\n"
            "Be calibrated. If a word is mumbled, clipped, rushed or partly masked, give "
            "confidence below 0.7 and list the real alternatives it could be. For clearly "
            "spoken words use high confidence and an empty list. Keep proper nouns "
            "capitalised. Never add content that is not in the audio.\n"
            f"Conversation so far (may be empty): {context}")
        parts = [self._part(d, m) for d, m in clips] + [prompt]

        def valid(out):
            return isinstance(out, dict) and isinstance(out.get("intended") or out.get("verbatim"), str)

        order = list(_AUDIO_MODELS)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + budget_s
        crosscheck = os.environ.get("THEME5_AUDIO_CROSSCHECK", "1") != "0" and len(order) > 1
        second_task = None
        if crosscheck:
            primary_order = [order[0]] + order[2:]
            second_task = asyncio.ensure_future(self._generate(parts, budget_s, [order[1]], valid))
        else:
            primary_order = order
        try:
            primary = await self._generate(parts, budget_s, primary_order, valid)
            second = None
            if second_task is not None:
                wait = min(max(deadline - loop.time(), 0.0), 1.5 if primary is not None else budget_s)
                try:
                    second = await asyncio.wait_for(asyncio.shield(second_task), timeout=wait)
                except asyncio.TimeoutError:
                    second = None
        finally:
            if second_task is not None and not second_task.done():
                second_task.cancel()
        if primary is None:
            primary, second = second, None
        if primary is None:
            return None
        result = _normalize_audio(primary)
        result["cross"] = _normalize_audio(second) if second is not None else None
        return result

    async def describe_frame(self, image: bytes, mime: str, budget_s: float = 6.0) -> Optional[Dict[str, Any]]:
        prompt = (
            "This is a frame from a user's camera, sent to a device-support assistant. "
            "Return JSON with keys:\n"
            '  "object": the device or item shown;\n'
            '  "focus": the specific component at the centre or most prominent '
            "(a named port, button, light, label or part);\n"
            '  "label": a short search phrase naming that component by its standard name;\n'
            '  "visible_text": any readable text, or "".')
        return await self._generate([self._part(image, mime), prompt], budget_s, list(_AUDIO_MODELS or _MODELS),
                                    lambda o: isinstance(o, dict) and isinstance(o.get("label"), str))

    async def interpret(self, utterance: str, tools: Dict[str, Any], state: Dict[str, Any],
                        history: List[str], budget_s: float = 6.0) -> Optional[Dict[str, Any]]:
        tool_view = {name: {k: spec.get(k) for k in ("kind", "description", "args")}
                     for name, spec in tools.items()}
        prompt = (
            "You are the language-understanding stage of a voice assistant that acts only "
            "through these tools (JSON schemas):\n"
            f"{json.dumps(tool_view)}\n\n"
            f"Current request state: {json.dumps(state, default=str)}\n"
            f"Recent conversation: {json.dumps(history[-8:])}\n"
            f"New user utterance: {json.dumps(utterance)}\n\n"
            "Return JSON with keys:\n"
            '  "action": one of "new_request", "update", "retract", "chitchat", "clarify";\n'
            '  "steps": for new_request, ordered tool calls [{"tool": name, "args": {...}}] '
            "using only listed tools; fill only values the user actually gave, in the user's "
            "words; omit args you do not know and args that come from an earlier step's result;\n"
            '  "slot_updates": for update, {arg_name: new_value} for the details the user changed;\n'
            '  "reply": for chitchat, one or two short, friendly sentences;\n'
            '  "question": for clarify, one short question.\n'
            "Never invent facts or results.")
        return await self._generate([prompt], budget_s, None, lambda o: isinstance(o, dict) and o.get("action") in (
            "new_request", "update", "retract", "chitchat", "clarify"))


def _normalize_audio(out: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not isinstance(out, dict):
        return None
    ents = []
    for e in out.get("entities") or []:
        if not isinstance(e, dict) or not isinstance(e.get("text"), str) or not e["text"].strip():
            continue
        try:
            conf = float(e.get("confidence", 1.0))
        except (TypeError, ValueError):
            conf = 1.0
        alts = []
        for a in e.get("alternatives") or []:
            if isinstance(a, str) and a.strip() and a.strip().lower() != e["text"].strip().lower() \
                    and a.strip().lower() not in [x.lower() for x in alts]:
                alts.append(a.strip())
        ents.append({"type": str(e.get("type") or "other").lower(), "text": e["text"].strip(),
                     "confidence": conf, "alternatives": alts})
    return {"intended": str(out.get("intended") or out.get("verbatim") or "").strip(),
            "verbatim": str(out.get("verbatim") or out.get("intended") or "").strip(),
            "entities": ents}


def _parse_json(text: Optional[str]) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        val = json.loads(t)
    except ValueError:
        m = re.search(r"\{.*\}", t, re.S)
        if not m:
            return None
        try:
            val = json.loads(m.group(0))
        except ValueError:
            return None
    return val if isinstance(val, dict) else None


def _promote(model: str):
    """A model that just answered goes first for later calls."""
    for lst in (_MODELS, _AUDIO_MODELS):
        if model in lst and lst[0] != model:
            lst.remove(model)
            lst.insert(0, model)


def _drop(model: str):
    for lst in (_MODELS, _AUDIO_MODELS):
        if model in lst:
            lst.remove(model)


async def _discover() -> List[str]:
    names: List[str] = []
    try:
        pager = await _CLIENT.aio.models.list()
        async for m in pager:
            name = str(getattr(m, "name", "")).split("/")[-1]
            actions = getattr(m, "supported_actions", None) or []
            if name and (not actions or "generateContent" in actions):
                names.append(name)
    except Exception as e:
        _log(f"model listing failed ({type(e).__name__}); using the preferred list")
        return list(PREFERRED_MODELS)
    flash = [n for n in names if "gemini" in n and "flash" in n and not any(x in n for x in _EXCLUDE)]
    ordered = [p for p in PREFERRED_MODELS if p in flash]
    ordered += sorted(n for n in flash if n not in ordered and "preview" not in n and "exp" not in n)
    ordered += sorted(n for n in flash if n not in ordered)
    return ordered[:MAX_PROBES] or list(PREFERRED_MODELS)


async def _probe(model: str) -> Tuple[str, Optional[float], bool]:
    """(model, text latency or None, accepts audio)."""
    llm = LLM()
    t0 = time.monotonic()
    out, outcome = await llm._call(model, ['Return {"ok": true} as JSON.'], 15.0)
    if outcome != "ok":
        return model, None, False
    latency = time.monotonic() - t0
    out, outcome = await llm._call(model, [llm._part(_silent_wav(), "audio/wav"),
                                           'Return {"ok": true} as JSON.'], 15.0)
    return model, latency, outcome == "ok"


async def init() -> LLM:
    """Create the shared client and pick healthy models once per process (from setup())."""
    global _CLIENT, _TYPES, _INIT_DONE
    if _INIT_DONE:
        return LLM()
    _INIT_DONE = True
    key = _api_key()
    if not key:
        return LLM()
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        _log("google-genai not installed; running rule-only")
        return LLM()
    try:
        _CLIENT = genai.Client(api_key=key)
        _TYPES = types
    except Exception as e:
        _log(f"client init failed: {e}")
        _CLIENT = None
        return LLM()
    pinned = os.environ.get("THEME5_GEMINI_MODEL", "").strip()
    candidates = [pinned] if pinned else await _discover()
    results = await asyncio.gather(*(_probe(m) for m in candidates))
    if _AUTH_FAILED:
        _log("check the key in SECRET_GEMINI_API_KEY / GEMINI_API_KEY / GOOGLE_API_KEY "
             "(the first one set is used); running rule-only")
        _CLIENT = None
        return LLM()
    healthy = [(m, lat, audio) for m, lat, audio in results if lat is not None]
    rank = {m: i for i, m in enumerate(candidates)}
    healthy.sort(key=lambda r: rank[r[0]])
    _MODELS[:] = [m for m, _, _ in healthy]
    _AUDIO_MODELS[:] = [m for m, _, audio in healthy if audio]
    if not _MODELS:
        _log(f"no Gemini model answered (tried {', '.join(candidates)}); running rule-only")
        _CLIENT = None
        return LLM()
    lat = ", ".join(f"{m} {l:.1f}s{'' if a else ' (no audio)'}" for m, l, a in healthy)
    _log(f"using {_MODELS[0]}; healthy: {lat}")
    return LLM()
