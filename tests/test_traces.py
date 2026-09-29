"""Trace-level tests for interruption and safety behavior (no ground truth used).

Each case replays a small scenario through the real harness and asserts on the
trace. Run:  py -3.12 tests/test_traces.py [--time-scale 4] [-k name]
"""

from __future__ import annotations
import argparse
import asyncio
import json
import os
import re
import sys
import time
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)

from contextlib import contextmanager  # noqa: E402

from harness.runner import EvaluationHarness  # noqa: E402
from harness.scorer import _eval_checkpoint, _score_recovery  # noqa: E402
from agent.agent import ParticipantAgent  # noqa: E402
import agent.llm as llm_mod  # noqa: E402


class FakeLLM:
    """Stands in for Gemini: answers after a delay given in scenario (virtual) ms.
    `audio` may be a dict or a list of dicts returned for successive audio turns;
    a call that outlives its budget returns None, as the real layer does."""
    available = True
    audio_available = True

    def __init__(self, delay_ms, interpret=None, audio=None):
        self.delay_ms = delay_ms
        self._interpret = interpret
        self._audio = audio if isinstance(audio, list) else [audio]
        self.audio_calls = 0
        self.budgets = []

    async def _wait(self, budget_s):
        self.budgets.append(budget_s)
        delay = self.delay_ms / 1000.0 / SCALE_NOW[0]
        await asyncio.sleep(min(delay, budget_s))
        return delay <= budget_s

    async def interpret(self, utterance, tools, state, history, budget_s=6.0):
        if not await self._wait(budget_s):
            return None
        return self._interpret(utterance) if self._interpret else None

    async def understand_audio(self, clips, context, budget_s=6.0):
        out = self._audio[min(self.audio_calls, len(self._audio) - 1)]
        self.audio_calls += 1
        if not await self._wait(budget_s):
            return None
        return out

    async def describe_frame(self, image, mime, budget_s=6.0):
        return None


@contextmanager
def fake_llm(fake):
    original = llm_mod.init

    async def init():
        return fake
    llm_mod.init = init
    try:
        yield
    finally:
        llm_mod.init = original

SCALE = 4.0
SCALE_NOW = [SCALE]   # time scale of the run in progress, read by FakeLLM


def speech(text, t, eot=True):
    return {"timestamp_ms": t, "event_type": "user_speech_chunk",
            "payload": {"text": text, "end_of_turn": eot}}


def interrupt(text, t):
    return {"timestamp_ms": t, "event_type": "interruption", "payload": {"text": text}}


def run(events, overrides=None, manifest=None, sid="t", scale=None):
    sc = {"scenario_id": sid, "events": events}
    if overrides:
        sc["tool_overrides"] = overrides
    if manifest:
        sc["tool_manifest"] = manifest
    SCALE_NOW[0] = scale or SCALE
    return asyncio.run(EvaluationHarness(sc, ParticipantAgent, time_scale=SCALE_NOW[0],
                                         verbose=False).run())


def acts(tr, kind=None):
    return [e for e in tr if e["kind"] == "action" and (kind is None or e["action"] == kind)]


def calls(tr, api=None):
    return [e for e in acts(tr, "tool_call") if api is None or e["api_name"] == api]


def spoken(tr):
    return [e for e in acts(tr) if e["action"] in ("filler_speech", "clarification_request", "final_response")]


def event_t(tr, etype, nth=0):
    return [e["t_ms"] for e in tr if e["kind"] == "event" and e["event_type"] == etype][nth]


def hygiene(tr):
    bad = [e for e in tr if e["kind"] in ("protocol_error", "agent_crash")]
    assert not bad, f"protocol/crash: {bad}"
    fillers = [e["payload"]["text"].strip().lower() for e in acts(tr, "filler_speech")]
    assert len(fillers) <= 4, f"{len(fillers)} fillers"
    assert len(fillers) == len(set(fillers)), f"repeated filler: {fillers}"
    for e in acts(tr, "final_response"):
        assert isinstance(e.get("state_snapshot"), dict), "final without snapshot"
    ids = [e["call_id"] for e in calls(tr)]
    assert len(ids) == len(set(ids)), "call_id reused"
    abandoned = [e for e in tr if e["kind"] == "tool_abandoned"]
    assert not abandoned, f"abandoned calls: {abandoned}"


def responded_within(tr, t_event, ms=800):
    first = next((e["t_ms"] for e in spoken(tr) if e["t_ms"] >= t_event), None)
    assert first is not None and first - t_event <= ms, f"no speech within {ms}ms of {t_event} (got {first})"


def last_snapshot(tr):
    snaps = [e["state_snapshot"] for e in acts(tr) if isinstance(e.get("state_snapshot"), dict)]
    return snaps[-1] if snaps else None


# ---------------------------------------------------------------------------
def test_double_correction():
    tr = run([speech("Please find flights to ", 100, False), speech("Boston for Friday.", 700),
              interrupt("Wait, make it New York.", 1500), interrupt("Actually, make it Chicago instead.", 2300)])
    hygiene(tr)
    t2 = event_t(tr, "interruption", 1)
    for c in calls(tr, "flight_search"):
        if c["args"]["destination"] in ("Boston", "New York"):
            assert c["t_ms"] < t2, "stale destination re-issued"
    last = calls(tr, "flight_search")[-1]
    assert last["args"]["destination"] == "Chicago"
    assert last_snapshot(tr)["slots"]["destination"] == "Chicago"
    cancelled = {e["call_id"] for e in tr if e["kind"] in ("tool_cancelled", "cancel_noop")}
    for c in calls(tr, "flight_search")[:-1]:
        assert c["call_id"] in cancelled or any(
            e["kind"] == "tool_completed" and e["call_id"] == c["call_id"] and e["t_ms"] <= t2 for e in tr)
    responded_within(tr, t2)


def test_retraction():
    tr = run([speech("Can you find flights to Denver for Monday?", 100), interrupt("Actually, never mind.", 1200)])
    hygiene(tr)
    t = event_t(tr, "interruption")
    assert not [c for c in calls(tr) if c["t_ms"] > t], "new work after retraction"
    assert any(e["kind"] == "tool_cancelled" for e in tr)
    responded_within(tr, t)
    finals_after = [e for e in acts(tr, "final_response") if e["t_ms"] >= t]
    assert finals_after and "denver" not in finals_after[-1]["payload"]["text"].lower()


def test_intent_change():
    tr = run([speech("Find me flights to Miami.", 100),
              interrupt("Forget the flight, my TV is blinking red.", 1200)])
    hygiene(tr)
    t = event_t(tr, "interruption")
    assert any(e["kind"] == "tool_cancelled" for e in tr)
    assert not [c for c in calls(tr, "flight_search") if c["t_ms"] > t]
    assert [c for c in calls(tr, "lookup_manual") if c["t_ms"] >= t], "no switch to the manual"
    responded_within(tr, t)


def test_result_races_interruption():
    # the search completes 1 ms before the interruption lands
    tr = run([speech("Find flights to Austin.", 100), interrupt("Actually, make it Seattle.", 1700)],
             overrides={"flight_search": [{"call_index": 0, "delay_ms": 1599}]})
    hygiene(tr)
    t = event_t(tr, "interruption")
    for e in acts(tr, "final_response"):
        assert "austin" not in e["payload"]["text"].lower() or e["t_ms"] < t, "final grounded in stale result"
    assert last_snapshot(tr)["slots"]["destination"] == "Seattle"


def test_booking_cancel_loses_race():
    tr = run([speech("Find a flight to Denver and book the 8 AM one for Alice.", 100),
              interrupt("Wait, make it for Bob.", 2600)],
             overrides={"flight_search": [{"call_index": 0, "delay_ms": 1500}],
                        "book_flight": [{"call_index": 0, "delay_ms": 800}]})
    hygiene(tr)
    books = calls(tr, "book_flight")
    keys = [json.dumps(c["args"], sort_keys=True) for c in books]
    assert len(keys) == len(set(keys)), "duplicate booking args"
    t = event_t(tr, "interruption")
    responded_within(tr, t)


def test_book_timeout_not_retried():
    tr = run([speech("Find a flight to Denver and book the 8 AM one for Alice.", 100)],
             overrides={"book_flight": [{"call_index": 0, "error": "timeout", "delay_ms": 900}]})
    hygiene(tr)
    assert len(calls(tr, "book_flight")) == 1, "state-modifying call retried automatically"
    assert acts(tr, "clarification_request"), "should ask before retrying"
    for e in spoken(tr):
        assert not re.search(r"\bbooked\b|\breserved\b", e["payload"]["text"].lower())


def test_duplicate_booking_reused():
    tr = run([speech("Find a flight to Denver and book the 8 AM one for Alice.", 100)],
             overrides={"book_flight": [{"call_index": 0, "error": "duplicate_booking",
                                         "detail": "already booked", "delay_ms": 500}]})
    hygiene(tr)
    assert len(calls(tr, "book_flight")) == 1


def test_slow_tool_after_end():
    # Real time: with one early event the agent cannot infer a faster local time scale,
    # and its tail watchdog runs on the (official) 1x clock.
    tr = run([speech("Find flights to Boston.", 100)],
             overrides={"flight_search": [{"call_index": 0, "delay_ms": 7000}]}, scale=1.0)
    hygiene(tr)
    finals = acts(tr, "final_response")
    assert finals, "no final before the tail ended"


def test_missing_audio_and_frame():
    tr = run([{"timestamp_ms": 100, "event_type": "video_frame",
               "payload": {"frame_id": "f1", "image_ref": "frames/does_not_exist.png"}},
              {"timestamp_ms": 300, "event_type": "user_audio_chunk",
               "payload": {"audio_ref": "audio/missing.mp3", "duration_ms": 900, "end_of_turn": True}}])
    hygiene(tr)
    responded_within(tr, 300)


NESTED = {"schedule_repair": {
    "kind": "state_modifying", "delay_range_ms": [700, 1200],
    "description": "Schedule a technician visit for a broken appliance.",
    "args": {"appliance": {"type": "object", "required": True, "properties": {
                 "model": {"type": "string", "required": True},
                 "issue": {"type": "string", "required": True}}},
             "urgency": {"type": "string", "required": True, "enum": ["low", "normal", "urgent"]},
             "visit_date": {"type": "string", "required": False}},
    "default_result": {"repair_id": "RP-5521", "window": "9-11am"}}}


def test_unseen_nested_tool():
    tr = run([speech("Please schedule a repair for my WF45 washer, it shows a drum error. "
                     "It's urgent, tomorrow if possible.", 100)], manifest=NESTED)
    hygiene(tr)
    cs = calls(tr, "schedule_repair")
    assert len(cs) == 1, f"calls: {calls(tr)}"
    a = cs[0]["args"]
    assert a["appliance"]["model"] == "WF45" and a["urgency"] == "urgent", a
    assert any("RP-5521" in e["payload"]["text"] for e in acts(tr, "final_response"))
    tr_err = [e for e in tr if e["kind"] == "tool_completed" and e["status"] != "success"]
    assert not tr_err, tr_err


def test_unseen_tool_missing_enum_asks():
    tr = run([speech("Please schedule a repair for my WF45 washer, the drum is making noise.", 100)],
             manifest=NESTED)
    hygiene(tr)
    assert not calls(tr, "schedule_repair"), "guessed a required enum on a state-modifying call"
    assert acts(tr, "clarification_request")


def test_additive_date():
    tr = run([speech("Find flights to Boston.", 100), interrupt("And make it Friday.", 1200)])
    hygiene(tr)
    t = event_t(tr, "interruption")
    searches = calls(tr, "flight_search")
    last = searches[-1]
    assert last["args"].get("date") == "Friday" and last["args"]["destination"] == "Boston"
    assert last_snapshot(tr)["slots"].get("date") == "Friday"
    # The date-less search is superseded: it must be cancelled, never completed after
    # the change and never re-sent with its old arguments.
    old = searches[0]
    assert "date" not in old["args"]
    assert any(e["kind"] == "tool_cancelled" and e["call_id"] == old["call_id"] for e in tr)
    assert not [c for c in searches if c["t_ms"] > t and "date" not in c["args"]], "old args re-sent"
    # Scored the way an additive-change scenario can be written: new state plus a
    # completed search carrying both values after the change.
    rec = _score_recovery(tr, {"recovery": {
        "interrupt_at_ms": t,
        "required_state_after_interrupt": {"slots.destination": ["boston"], "slots.date": ["friday"]}}})
    assert rec["fraction"] == 1.0, rec
    cp = _eval_checkpoint(tr, {"id": "search_with_date", "type": "tool_called", "tool": "flight_search",
                               "args_subset": {"destination": ["boston"], "date": ["friday"]},
                               "after_ms": t, "must_complete": True})
    assert cp["passed"], cp


def test_added_slot_keeps_unaffected_search():
    # A detail that the in-flight search does not use must not cancel or re-send it.
    tr = run([speech("Find a flight to Denver and book the 8 AM one.", 100), interrupt("It's for Alice.", 1200)])
    hygiene(tr)
    searches = calls(tr, "flight_search")
    assert len(searches) == 1, searches
    assert not any(e["kind"] == "tool_cancelled" and e["call_id"] == searches[0]["call_id"] for e in tr)
    b = calls(tr, "book_flight")
    assert len(b) == 1 and b[0]["args"].get("passenger_name") == "Alice", b


def _stale_boston_ok(tr, new_city):
    t = event_t(tr, "interruption")
    rec = _score_recovery(tr, {"recovery": {
        "interrupt_at_ms": t,
        "invalidated_calls": [{"tool": "flight_search", "args_subset": {"destination": ["boston"]},
                               "invalid_after_ms": t}],
        "required_state_after_interrupt": {"slots.destination": [new_city.lower()]}}})
    assert rec["fraction"] == 1.0, rec["checks"]
    assert any(c["args"]["destination"] == new_city and c["t_ms"] >= t for c in calls(tr, "flight_search"))
    responded_within(tr, t)


def test_correction_during_slow_model_plan():
    # The model is still interpreting the request when the user changes the city;
    # the Boston plan it returns must never reach the harness.
    fake = FakeLLM(2400, interpret=lambda u: {"action": "new_request", "steps": [
        {"tool": "flight_search", "args": {"destination": "Boston", "date": "Friday"}}]})
    with fake_llm(fake):
        tr = run([speech("I need to get over to Boston on Friday somehow.", 100),
                  interrupt("Wait, actually make it New York.", 800)])
    hygiene(tr)
    assert not [c for c in calls(tr, "flight_search") if c["args"]["destination"] == "Boston"]
    _stale_boston_ok(tr, "New York")


def test_correction_during_slow_model_cancels_sent_call():
    # A search is already running; an unrelated remark sends the model off to think;
    # a correction during that wait must cancel the running search immediately.
    fake = FakeLLM(3200, interpret=lambda u: {"action": "chitchat", "reply": "Sure, happy to help."})
    with fake_llm(fake):
        tr = run([speech("Find flights to Boston.", 100),
                  speech("Hmm, and one other small thing.", 700),
                  interrupt("Actually, make it New York.", 1100)])
    hygiene(tr)
    t = event_t(tr, "interruption")
    boston = [c for c in calls(tr, "flight_search") if c["args"]["destination"] == "Boston"]
    assert len(boston) == 1
    cancel = [e for e in tr if e["kind"] == "tool_cancelled" and e["call_id"] == boston[0]["call_id"]]
    ack = next(e["t_ms"] for e in spoken(tr) if e["t_ms"] >= t)
    model_reply = next(e["t_ms"] for e in acts(tr, "final_response") if "happy to help" in e["payload"]["text"])
    assert cancel and cancel[0]["t_ms"] <= ack + 1, f"cancel after the acknowledgement: {cancel}, ack {ack}"
    assert cancel[0]["t_ms"] < model_reply, "cancel waited on the model"
    _stale_boston_ok(tr, "New York")


def audio_event(ref, t, eot=True):
    return {"timestamp_ms": t, "event_type": "user_audio_chunk",
            "payload": {"audio_ref": ref, "duration_ms": 1200, "end_of_turn": eot}}


def heard(intended, entities=(), verbatim=None, cross=None):
    ents = []
    for e in entities:
        full = {"type": "place", "confidence": 0.95, "alternatives": []}
        full.update(e)
        ents.append(full)
    return {"intended": intended, "verbatim": verbatim or intended, "entities": ents, "cross": cross}


def test_audio_low_confidence_asks_then_acts():
    fake = FakeLLM(1200, audio=[
        heard("I want to fly to Dallas.", [{"text": "Dallas", "confidence": 0.55, "alternatives": ["Denver"]}]),
        heard("Denver.", [{"text": "Denver"}])])
    with fake_llm(fake):
        tr = run([audio_event("audio/pub_05_turn1.mp3", 100), audio_event("audio/pub_05_turn2.mp3", 4200)])
    hygiene(tr)
    t2 = event_t(tr, "user_audio_chunk", 1)
    clar = [e for e in acts(tr, "clarification_request") if e["t_ms"] < t2]
    assert clar and "dallas" in clar[0]["payload"]["text"].lower() and "denver" in clar[0]["payload"]["text"].lower(), clar
    assert not [c for c in calls(tr) if c["t_ms"] < t2], "searched before the user confirmed"
    s = calls(tr, "flight_search")
    assert len(s) == 1 and s[0]["args"]["destination"] == "Denver", s
    responded_within(tr, 100)
    responded_within(tr, t2)


def test_audio_models_disagree_asks():
    fake = FakeLLM(1200, audio=heard("Book a flight to Dallas.", [{"text": "Dallas"}],
                                     cross=heard("Book a flight to Denver.", [{"text": "Denver"}])))
    with fake_llm(fake):
        tr = run([audio_event("audio/pub_05_turn1.mp3", 100), speech("Thanks.", 5000)])
    hygiene(tr)
    clar = acts(tr, "clarification_request")
    assert clar and "dallas" in clar[0]["payload"]["text"].lower() and "denver" in clar[0]["payload"]["text"].lower()
    assert not calls(tr, "flight_search")


def test_audio_self_repair_is_not_ambiguity():
    verb_a = "I want to fly to Denver, uh, no, sorry, Miami."
    fake = FakeLLM(1200, audio=heard("I want to fly to Miami.", [{"text": "Miami"}], verbatim=verb_a,
                                     cross=heard("I want to fly to Denver.", [{"text": "Denver"}], verbatim=verb_a)))
    with fake_llm(fake):
        tr = run([audio_event("audio/pub_06_turn1_part1.mp3", 100, eot=False),
                  audio_event("audio/pub_06_turn1_part2.mp3", 1400)])
    hygiene(tr)
    assert not acts(tr, "clarification_request")
    s = calls(tr, "flight_search")
    assert [c["args"]["destination"] for c in s] == ["Miami"], s


def test_audio_model_time_bounded_after_end():
    # the model never answers in time; the turn is the last event, so the tail is the limit
    # Real time, like test_slow_tool_after_end: one early event cannot reveal a faster local scale.
    fake = FakeLLM(20000, audio=heard("Find me flights to Denver.", [{"text": "Denver"}]))
    with fake_llm(fake):
        tr = run([audio_event("audio/pub_05_turn1.mp3", 100)], scale=1.0)
    hygiene(tr)
    end = event_t(tr, "scenario_end")
    clar = [e for e in acts(tr, "clarification_request") if e["t_ms"] > end]
    assert clar, "no fallback question"
    assert clar[0]["t_ms"] - end < 3200, f"fallback too late: {clar[0]['t_ms'] - end} ms after end"
    assert fake.budgets and fake.budgets[0] < 3.2 / SCALE_NOW[0] + 0.5, fake.budgets


def test_llm_falls_back_on_503_within_budget():
    class Unavailable(Exception):
        pass

    class Models:
        def __init__(self, behaviour):
            self.behaviour = behaviour
            self.tried = []

        async def generate_content(self, model, contents, config):
            self.tried.append(model)
            b = self.behaviour[model]
            if b == "503":
                raise Unavailable("503 UNAVAILABLE. The model is overloaded.")
            await asyncio.sleep(b)
            return type("R", (), {"text": '{"intended": "fly to Denver", "verbatim": "fly to Denver"}'})()

    class Types:
        AutomaticFunctionCallingConfig = ThinkingConfig = GenerateContentConfig = staticmethod(lambda **kw: kw)

        class Part:
            @staticmethod
            def from_bytes(data, mime_type):
                return (mime_type, len(data))

    saved = (llm_mod._CLIENT, llm_mod._TYPES, list(llm_mod._MODELS), list(llm_mod._AUDIO_MODELS))
    try:
        models = Models({"m-a": "503", "m-b": 0.05, "m-slow": 5.0})
        llm_mod._CLIENT = type("C", (), {"aio": type("A", (), {"models": models})()})()
        llm_mod._TYPES = Types
        llm_mod._MODELS[:] = llm_mod._AUDIO_MODELS[:] = ["m-a", "m-b"]
        os.environ["THEME5_AUDIO_CROSSCHECK"] = "0"
        out = asyncio.run(llm_mod.LLM().understand_audio([(b"x", "audio/mp3")], "", budget_s=2.0))
        assert out and out["intended"] == "fly to Denver" and models.tried == ["m-a", "m-b"], (out, models.tried)
        assert llm_mod._AUDIO_MODELS[0] == "m-b", "healthy model should be tried first next time"
        models.tried.clear()
        llm_mod._MODELS[:] = llm_mod._AUDIO_MODELS[:] = ["m-a", "m-slow"]
        t0 = time.monotonic()
        out = asyncio.run(llm_mod.LLM().understand_audio([(b"x", "audio/mp3")], "", budget_s=1.0))
        took = time.monotonic() - t0
        assert out is None and took < 1.5, (out, took)
    finally:
        os.environ.pop("THEME5_AUDIO_CROSSCHECK", None)
        llm_mod._CLIENT, llm_mod._TYPES = saved[0], saved[1]
        llm_mod._MODELS[:], llm_mod._AUDIO_MODELS[:] = saved[2], saved[3]


def test_correction_during_slow_audio():
    fake = FakeLLM(2400, audio={"verbatim": "Find me flights to Boston.",
                               "intended": "Find me flights to Boston.", "uncertain": []})
    with fake_llm(fake):
        tr = run([{"timestamp_ms": 100, "event_type": "user_audio_chunk",
                   "payload": {"audio_ref": "audio/pub_05_turn1.mp3", "duration_ms": 1400,
                               "end_of_turn": True}},
                  interrupt("Actually, make it Miami.", 800)])
    hygiene(tr)
    assert not [c for c in calls(tr, "flight_search") if c["args"]["destination"] == "Boston"]
    _stale_boston_ok(tr, "Miami")


def test_distractor_speech():
    tr = run([speech("Thanks, that's all.", 100)])
    hygiene(tr)
    assert not calls(tr)
    responded_within(tr, 100)


def test_choose_after_results():
    tr = run([speech("I'd like to book a flight to Denver.", 100),
              speech("The 2 PM one, for Carol Smith.", 4500)])
    hygiene(tr)
    b = calls(tr, "book_flight")
    assert len(b) == 1, b
    flights = next(e["result"]["flights"] for e in tr
                   if e["kind"] == "tool_completed" and e["api_name"] == "flight_search")
    two_pm = next(f["flight_id"] for f in flights if f["depart"] == "14:00")
    assert b[0]["args"].get("flight_id") == two_pm, b
    assert b[0]["args"].get("passenger_name") == "Carol Smith", b


def main():
    global SCALE
    ap = argparse.ArgumentParser()
    ap.add_argument("--time-scale", type=float, default=4.0)
    ap.add_argument("-k", default="")
    args = ap.parse_args()
    SCALE = args.time_scale
    tests = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and args.k in n]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {name}: {e}")
            if not isinstance(e, AssertionError):
                traceback.print_exc()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
