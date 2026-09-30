"""Offline fallback tool selector backed by a small local Ollama model (default: functiongemma).

NOT part of the benchmark pipeline. Given a user utterance and a list of tool schemas it asks the
local model which tool to call and returns:

    {"tool": name, "args": {...}}                              -> safe tool, caller may execute
    {"tool": name, "args": {...}, "needs_confirmation": True}  -> RISKY tool, never auto-executed
    {"tool": None}                                             -> model chose no tool
    None                                                       -> any error / timeout / bad output

The schemas below mirror the real tools in ext_agent.py (InCarAssistant / HomeAssistant) exactly.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as _FutTimeout
from typing import Any, Dict, List, Optional

try:  # requests is present in the project env; only stdlib is needed otherwise
    import requests
except Exception:  # pragma: no cover
    requests = None

OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "functiongemma"


def _tool(name: str, description: str, props: Dict[str, dict], required: List[str]) -> dict:
    return {"name": name, "description": description,
            "parameters": {"type": "object", "properties": props, "required": required}}


_S = "string"
CAR_TOOLS: List[dict] = [
    _tool("reroute_navigation", "Change the car's active navigation destination.",
          {"destination": {"type": _S, "description": "Where to navigate to, e.g. 'the airport' or '123 Main St'"}},
          ["destination"]),
    _tool("check_traffic", "Check traffic conditions on the current route. Can take a few seconds.",
          {"route_id": {"type": _S, "description": "Which route to check, defaults to the current route"}},
          []),
    _tool("find_charging_station", "Find a nearby EV charging station. May need a couple of tries.",
          {"near": {"type": _S, "description": "Area to search near, e.g. 'downtown'"},
           "connector_type": {"type": _S, "description": "Connector type, e.g. 'CCS' or 'NACS'"}},
          ["near", "connector_type"]),
    _tool("book_charging_slot", "Book a specific EV charging station time slot.",
          {"station_id": {"type": _S, "description": "The station id from a prior search, e.g. 'CHG-001'"},
           "time_slot": {"type": _S, "description": "Requested time, e.g. '18:00'"}},
          ["station_id", "time_slot"]),
    _tool("call_roadside_assistance", "Call roadside assistance for a car problem.",
          {"issue": {"type": _S, "description": "What's wrong, e.g. 'flat tire' or 'won't start'"}},
          ["issue"]),
]

HOME_TOOLS: List[dict] = [
    _tool("set_ac_temperature", "Set the air conditioner target temperature in a room.",
          {"room": {"type": _S, "description": "Which room, e.g. 'living room'"},
           "celsius": {"type": "number", "description": "Target temperature in degrees Celsius"}},
          ["room", "celsius"]),
    _tool("set_lights", "Turn the lights in a room on or off and set brightness.",
          {"room": {"type": _S, "description": "Which room, e.g. 'bedroom'"},
           "state": {"type": _S, "description": "'on' or 'off'"},
           "brightness": {"type": "integer", "description": "Brightness percent 0-100"}},
          ["room", "state"]),
    _tool("start_washer", "Start the washer with a cycle, optionally delayed.",
          {"cycle": {"type": _S, "description": "Washer cycle, e.g. 'cotton' or 'eco'"},
           "delay_minutes": {"type": "integer", "description": "Minutes to wait before starting, default 0"}},
          ["cycle"]),
    _tool("check_energy_usage", "Check home energy usage for a period. Can take a few seconds.",
          {"period": {"type": _S, "description": "'today', 'this week' or 'this month'"}},
          []),
    _tool("find_phone", "Ring the user's phone to find it. May need a couple of tries.", {}, []),
    _tool("call_service_center", "Call the appliance service centre about a problem.",
          {"issue": {"type": _S, "description": "What's wrong, e.g. 'washer leaking'"}},
          ["issue"]),
]

TOOL_SETS = {"car": CAR_TOOLS, "home": HOME_TOOLS}

# State-changing tools: the offline fallback must never hand these back as directly executable.
RISKY = frozenset({"book_charging_slot", "cancel_charging_booking", "start_washer",
                   "cancel_washer", "call_roadside_assistance", "call_service_center"})

SYSTEM_PROMPT = (
    "You are an offline device-control assistant. Pick at most ONE tool for the user's request. "
    "If the user corrects themselves mid-sentence (e.g. 'to 24, no, 22'), use the final corrected value. "
    "If the request is small talk or not a device command, do not call any tool."
)


def _post(url: str, payload: dict, timeout: float) -> dict:
    """HTTP POST returning parsed JSON. Isolated so tests can monkeypatch it."""
    if requests is None:
        raise RuntimeError("requests not available")
    r = requests.post(url, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()


def _coerce(value: Any, ptype: str) -> Any:
    if ptype in ("number", "integer") and isinstance(value, str):
        try:
            f = float(value.strip())
        except ValueError:
            return value
        return int(f) if ptype == "integer" and f == int(f) else f
    if ptype == "integer" and isinstance(value, float) and value == int(value):
        return int(value)
    return value


class LocalFallback:
    def __init__(self, model: str = DEFAULT_MODEL, base_url: str = OLLAMA_URL,
                 timeout: float = 8.0, num_thread: int = 4, temperature: float = 0.0,
                 mode: str = "tools", risky=RISKY, max_tokens: int = 64):
        # max_tokens: one tool call is ~20 tokens. Without a cap the model keeps emitting further
        # calls and chat turns until the timeout (seen in the first evaluation), so bound it.
        self.max_tokens = max_tokens
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.num_thread = num_thread
        self.temperature = temperature
        self.mode = mode  # "tools" (native tool calling) or "json" (strict JSON prompt)
        self.risky = frozenset(risky)
        self._pool = ThreadPoolExecutor(max_workers=1)

    # ------------------------------------------------------------------ public
    def decide(self, text: str, tools: List[dict]) -> Optional[dict]:
        """Return a decision dict (see module docstring) or None on any error."""
        try:
            payload = self._payload(text, tools)
            fut = self._pool.submit(_post, self.base_url + "/api/chat", payload, self.timeout)
            try:
                resp = fut.result(timeout=self.timeout)
            except _FutTimeout:
                fut.cancel()
                return None
            return self._parse(resp, tools)
        except Exception:
            return None

    # ----------------------------------------------------------------- internals
    def _payload(self, text: str, tools: List[dict]) -> dict:
        options = {"temperature": self.temperature, "num_thread": self.num_thread,
                   "num_predict": self.max_tokens}
        # think=False: thinking models (e.g. gemma4) otherwise spend the whole num_predict budget
        # on hidden reasoning and return no tool call at all (seen 2026-09-30: 38/40 empty).
        if self.mode == "tools":
            messages = [{"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": text}]
            return {"model": self.model, "messages": messages, "stream": False, "options": options,
                    "think": False, "tools": [{"type": "function", "function": t} for t in tools]}
        listing = json.dumps(tools, separators=(",", ":"))
        sys_msg = (SYSTEM_PROMPT + " Available tools (JSON schemas): " + listing +
                   ' Reply with ONLY one JSON object: {"tool": "<name>", "args": {...}} '
                   'or {"tool": null} if no tool applies.')
        return {"model": self.model, "stream": False, "format": "json", "options": options, "think": False,
                "messages": [{"role": "system", "content": sys_msg},
                             {"role": "user", "content": text}]}

    def _parse(self, resp: dict, tools: List[dict]) -> Optional[dict]:
        msg = (resp or {}).get("message") or {}
        name, args = None, {}
        calls = msg.get("tool_calls") or []
        if calls:
            fn = (calls[0] or {}).get("function") or {}
            name, args = fn.get("name"), fn.get("arguments", {})
        else:
            content = (msg.get("content") or "").strip()
            obj = self._json_from_text(content)
            if obj is None:
                if self.mode == "tools" and content:
                    return {"tool": None}   # plain chat reply, no tool
                return None                 # malformed / empty
            if not isinstance(obj, dict):
                return None
            name, args = obj.get("tool"), obj.get("args", obj.get("arguments", {}))
        if name is None:
            return {"tool": None}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                return None
        if not isinstance(name, str) or not isinstance(args, dict):
            return None
        schema = next((t for t in tools if t["name"] == name), None)
        if schema is None:
            return None                     # unknown / hallucinated tool
        props = schema["parameters"].get("properties", {})
        clean = {k: _coerce(v, props[k].get("type", "string")) for k, v in args.items() if k in props}
        if any(r not in clean for r in schema["parameters"].get("required", [])):
            return None                     # required argument missing
        out = {"tool": name, "args": clean}
        if name in self.risky:
            out["needs_confirmation"] = True
        return out

    @staticmethod
    def _json_from_text(text: str):
        if not text:
            return None
        try:
            return json.loads(text)
        except ValueError:
            pass
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except ValueError:
                return None
        return None


def is_executable(decision: Optional[dict]) -> bool:
    """True only for a non-risky, concrete tool call that needs no confirmation."""
    return bool(decision and decision.get("tool") and not decision.get("needs_confirmation"))
