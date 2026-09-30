"""Diagnostic (not a measurement): for a few commands, show the local model's raw reply and
which check in extension/local_fallback.py rejects it. Usage: fallback_diag.py"""
import json, sys, time
sys.path.insert(0, "/mnt/d/Theme5-Interruptible-Agents/extension")
import requests
from local_fallback import LocalFallback, CAR_TOOLS, HOME_TOOLS, SYSTEM_PROMPT

URL = "http://127.0.0.1:11434/api/chat"
CASES = [("car", "Take me to 45 Oak Street"), ("car", "Check traffic please"),
         ("car", "Book charging station CHG-001 at 18:00"), ("car", "Navigate to the office"),
         ("home", "Set the study AC to 20"), ("home", "Turn on the bedroom lights"),
         ("home", "Find my phone")]


def why(fb, resp, tools):
    msg = (resp or {}).get("message") or {}
    calls = msg.get("tool_calls") or []
    content = (msg.get("content") or "").strip()
    if not calls and not content:
        return "REJECT: empty reply (no tool call, no text)"
    if not calls:
        return "no structured tool call; text reply -> treated as 'no tool'"
    fn = calls[0].get("function") or {}
    name, args = fn.get("name"), fn.get("arguments", {})
    schema = next((t for t in tools if t["name"] == name), None)
    if schema is None:
        return f"REJECT: unknown tool name {name!r}"
    props = schema["parameters"]["properties"]
    missing = [r for r in schema["parameters"].get("required", []) if r not in args]
    extra = [k for k in args if k not in props]
    if missing:
        return f"REJECT: required argument(s) missing {missing}; model used keys {list(args)} (unknown keys {extra})"
    return "accepted"


def ask(text, tools, system=True):
    messages = ([{"role": "system", "content": SYSTEM_PROMPT}] if system else []) + [{"role": "user", "content": text}]
    payload = {"model": "functiongemma", "messages": messages, "stream": False,
               "options": {"temperature": 0.0, "num_thread": 4, "num_predict": 200},
               "tools": [{"type": "function", "function": t} for t in tools]}
    t0 = time.monotonic()
    try:
        r = requests.post(URL, json=payload, timeout=40).json()
    except Exception as e:
        return None, f"{type(e).__name__} after {time.monotonic() - t0:.1f}s"
    return r, f"{time.monotonic() - t0:.2f}s, generated {r.get('eval_count')} tokens, done_reason={r.get('done_reason')}"


fb = LocalFallback()
for system in (True, False):
    print(f"\n===== {'WITH our system prompt (as evaluated)' if system else 'WITHOUT our system prompt'} =====")
    for pack, text in CASES:
        tools = CAR_TOOLS if pack == "car" else HOME_TOOLS
        resp, info = ask(text, tools, system)
        msg = (resp or {}).get("message") or {}
        print(f"\n[{pack}] {text!r}  ({info})")
        print("  tool_calls:", json.dumps(msg.get("tool_calls"))[:260])
        print("  content   :", repr((msg.get("content") or "")[:200]))
        print("  verdict   :", why(fb, resp, tools) if resp else "no response")
