"""Offline tests for local_fallback.LocalFallback: fake HTTP responder, no inference, no network.
Run (plain python, no pytest needed):
  wsl -d Ubuntu -- ~/theme5/fdb-env/bin/python /mnt/d/Theme5-Interruptible-Agents/extension/test_local_fallback.py
"""
import ast
import json
import os
import sys
import time

import local_fallback as lf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from local_fallback import CAR_TOOLS, HOME_TOOLS, LocalFallback


def _tool_resp(name, args):
    return {"message": {"role": "assistant", "content": "",
                        "tool_calls": [{"function": {"name": name, "arguments": args}}]}}


def _patch(_mp, fn):
    lf._post = fn


def test_valid_call_parsed(monkeypatch):
    seen = {}

    def fake(url, payload, timeout):
        seen.update(url=url, payload=payload)
        return _tool_resp("set_ac_temperature", {"room": "bedroom", "celsius": "23"})
    _patch(monkeypatch, fake)
    out = LocalFallback().decide("set the bedroom AC to 23", HOME_TOOLS)
    assert out == {"tool": "set_ac_temperature", "args": {"room": "bedroom", "celsius": 23}}
    assert seen["url"].endswith("/api/chat")
    assert seen["payload"]["options"] == {"temperature": 0.0, "num_thread": 4, "num_predict": 64}
    assert len(seen["payload"]["tools"]) == len(HOME_TOOLS)
    assert lf.is_executable(out)


def test_no_tool(monkeypatch):
    _patch(monkeypatch, lambda u, p, t: {"message": {"content": "Hello there!"}})
    assert LocalFallback().decide("good morning", CAR_TOOLS) == {"tool": None}


def test_json_mode_valid(monkeypatch):
    body = json.dumps({"tool": "check_traffic", "args": {}})
    _patch(monkeypatch, lambda u, p, t: {"message": {"content": body}})
    assert LocalFallback(mode="json").decide("traffic?", CAR_TOOLS) == {"tool": "check_traffic", "args": {}}


def test_malformed_json_returns_none(monkeypatch):
    _patch(monkeypatch, lambda u, p, t: {"message": {"content": "{not json"}})
    assert LocalFallback(mode="json").decide("x", CAR_TOOLS) is None
    _patch(monkeypatch, lambda u, p, t: {"message": {"tool_calls": [
        {"function": {"name": "set_lights", "arguments": "{bad"}}]}})
    assert LocalFallback().decide("x", HOME_TOOLS) is None


def test_http_error_returns_none(monkeypatch):
    def boom(u, p, t):
        raise ConnectionError("refused")
    _patch(monkeypatch, boom)
    assert LocalFallback().decide("x", CAR_TOOLS) is None


def test_timeout_returns_none_quickly(monkeypatch):
    def slow(u, p, t):
        time.sleep(1.0)
        return _tool_resp("check_traffic", {})
    _patch(monkeypatch, slow)
    t0 = time.time()
    assert LocalFallback(timeout=0.1).decide("traffic", CAR_TOOLS) is None
    assert time.time() - t0 < 0.8

    def raising(u, p, t):
        raise TimeoutError("read timed out")
    _patch(monkeypatch, raising)
    assert LocalFallback().decide("traffic", CAR_TOOLS) is None


RISKY_CASES = [
    ("book_charging_slot", {"station_id": "CHG-001", "time_slot": "18:00"}, CAR_TOOLS),
    ("call_roadside_assistance", {"issue": "flat tire"}, CAR_TOOLS),
    ("start_washer", {"cycle": "eco"}, HOME_TOOLS),
    ("call_service_center", {"issue": "leak"}, HOME_TOOLS),
]


def test_risky_needs_confirmation(monkeypatch):
    for name, args, tools in RISKY_CASES:
        _patch(monkeypatch, lambda u, p, t: _tool_resp(name, args))
        out = LocalFallback().decide("do it", tools)
        assert out["tool"] == name and out["args"] == args
        assert out["needs_confirmation"] is True
        assert not lf.is_executable(out)


def test_cancel_tools_are_risky_even_if_offered(monkeypatch):
    tools = CAR_TOOLS + [lf._tool("cancel_charging_booking", "cancel",
                                  {"booking_ref": {"type": "string"}}, ["booking_ref"])]
    _patch(monkeypatch, lambda u, p, t: _tool_resp("cancel_charging_booking", {"booking_ref": "BOOK-0001"}))
    out = LocalFallback().decide("cancel", tools)
    assert out["needs_confirmation"] is True


def test_unknown_tool_returns_none(monkeypatch):
    _patch(monkeypatch, lambda u, p, t: _tool_resp("launch_missiles", {"target": "x"}))
    assert LocalFallback().decide("x", CAR_TOOLS) is None
    # a real tool from the OTHER pack is unknown here too
    _patch(monkeypatch, lambda u, p, t: _tool_resp("set_lights", {"room": "a", "state": "on"}))
    assert LocalFallback().decide("x", CAR_TOOLS) is None


def test_missing_required_arg_returns_none(monkeypatch):
    _patch(monkeypatch, lambda u, p, t: _tool_resp("set_ac_temperature", {"room": "bedroom"}))
    assert LocalFallback().decide("x", HOME_TOOLS) is None


def test_schemas_mirror_ext_agent(_mp=None):
    src = open(os.path.join(os.path.dirname(__file__), "ext_agent.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    real = {}
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)
                and n.name in ("InCarAssistant", "HomeAssistant")]:
        for fn in cls.body:
            if isinstance(fn, ast.AsyncFunctionDef):
                real[fn.name] = [a.arg for a in fn.args.args if a.arg != "self"]
    ours = {t["name"]: list(t["parameters"]["properties"]) for t in CAR_TOOLS + HOME_TOOLS}
    assert ours == real


if __name__ == "__main__":
    orig = lf._post
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            lf._post = orig
            try:
                fn(None)
                print("PASS", name)
            except Exception as e:  # noqa: BLE001
                failed += 1
                print("FAIL", name, repr(e))
    print("ALL PASS" if not failed else f"{failed} FAILED")
    sys.exit(1 if failed else 0)
