"""Score one SLURP run of the home assistant from its recovery log.

Each recording gets the tool events that fall between its start and the next recording's start
(clock anchored on the agent's session_start line). A request counts as done when a set_lights
call ended in success (or was answered from an identical earlier request) with the state the
SLURP intent asks for: lightoff -> off, lighton -> on, lightdim / lightup -> on (brightness is
printed, not scored). The room is not scored: most SLURP requests name none."""
import json, os, sys

out = sys.argv[1]
meta = json.load(open(os.path.join(out, "metadata.json"), encoding="utf-8"))
lines = meta["lines"]
events = [json.loads(x) for x in open(os.path.join(out, "ext_recovery_events.log")) if x.strip()]
start = next((e["ts"] for e in events if e["kind"] == "session_start"), None)
if start is None:
    sys.exit("no session_start in the recovery log")
SLACK = 1.0  # the agent cannot act before it has heard the request
want = {"iot_hue_lightoff": "off", "iot_hue_lighton": "on", "iot_hue_lightdim": "on", "iot_hue_lightup": "on"}
calls = {}
for e in events:
    if e["kind"] == "session_start":
        continue
    c = calls.setdefault(e["call_id"], {"t": e["ts"] - start, "tool": e["tool"], "kinds": [], "args": {}})
    c["kinds"].append(e["kind"])
    if e["kind"] == "proposed":
        try: c["args"] = json.loads(e["detail"])
        except ValueError: pass
done = retried = dup = 0
rows = []
for i, ln in enumerate(lines):
    lo = ln["offset_s"] + SLACK
    hi = (lines[i + 1]["offset_s"] + SLACK) if i + 1 < len(lines) else 1e9
    mine = [c for c in calls.values() if lo <= c["t"] < hi]
    ok = [c for c in mine if c["tool"] == "set_lights" and ("succeeded" in c["kinds"] or "duplicate" in c["kinds"])
          and str(c["args"].get("state", "")).lower() == want[ln["intent"]]]
    r = any("retry" in c["kinds"] for c in mine)
    d = any("duplicate" in c["kinds"] for c in ok)
    done += bool(ok); retried += r; dup += d
    rows.append({"transcript": ln["transcript"], "intent": ln["intent"], "done": bool(ok), "retried": r,
                 "answered_from_earlier_identical_request": d,
                 "calls": [{"tool": c["tool"], "args": c["args"], "events": c["kinds"], "t": round(c["t"], 1)} for c in mine]})
    print(f"{'OK ' if ok else 'NO '} {ln['intent']:18s} {ln['transcript']!r}")
    for c in mine:
        print(f"      t={c['t']:6.1f}s {c['tool']} {c['args']} -> {' '.join(c['kinds'])}")
summary = {"recordings": len(lines), "done": done, "needed_retry": retried, "answered_from_identical_request": dup,
           "failed_events": sum(e["kind"] == "failed" for e in events), "retry_events": sum(e["kind"] == "retry" for e in events),
           "handoff_events": sum(e["kind"] == "handoff" for e in events)}
print("SUMMARY", json.dumps(summary))
json.dump({"summary": summary, "rows": rows}, open(os.path.join(out, "slurp_score.json"), "w", encoding="utf-8"), indent=2)
r = os.path.join(out, "result.json")
if os.path.exists(r):
    print("agent said:", (json.load(open(r)).get("transcript") or "")[:1500])
