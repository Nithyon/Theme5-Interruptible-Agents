#!/usr/bin/env bash
# Read-only: how much is the Reasoner (Jev) called, how fast is it, and how often does it shorten a hold?
python3 - <<'PY'
import json, os, statistics as st
for name, d in (("today, Smart Turn OFF (so far)", "/tmp/runb"), ("29 Sep pipeline", "/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-29_full_gate_gemini38_final")):
    sp, ep = os.path.join(d, "gate_stats.log"), os.path.join(d, "gate_events.log")
    if not (os.path.exists(sp) and os.path.exists(ep)): print(name, ": logs missing"); continue
    rows = [json.loads(l) for l in open(sp) if l.strip()]
    j = [r["jev"] for r in rows if r.get("jev")]
    calls = sum(x["calls"] for x in j); ok = sum(x["ok"] for x in j); to = sum(x["timeouts"] for x in j); er = sum(x["errors"] for x in j); ms = sum(x["ms_total"] for x in j)
    rooms = [json.loads(l) for l in open(ep) if l.strip()]
    holds = [e["held_s"] for r in rooms for e in r["events"] if e["kind"] == "execute"]
    fast = sum(h < 0.6 for h in holds); norm = sum(0.6 <= h < 1.5 for h in holds); slow = sum(h >= 1.5 for h in holds)
    print(f"{name}: recordings {len(rows)} | Jev calls {calls} ({calls/max(1,len(rows)):.1f} per recording) | answered {ok}, timed out {to}, errors {er} | average answer time {ms/max(1,ok):.0f} ms")
    print(f"   executed actions {len(holds)}: released fast (about 0.4 s, Jev confident the user was done) {fast} | normal wait (about 0.9 s) {norm} | long wait (1.5 s or more) {slow} | mean wait {st.mean(holds):.2f} s")
PY
