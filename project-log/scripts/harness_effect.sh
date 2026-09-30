#!/usr/bin/env bash
# Read-only: how often did the Commit Harness actually change which calls ran? (decision logs only)
python3 - <<'PY'
import json, os
R = "/mnt/d/Theme5-Interruptible-Agents/project-log/runs"
logs = {"29 Sep pipeline (100 rec.)": f"{R}/2026-09-29_full_gate_gemini38_final/gate_events.log",
        "today, Smart Turn OFF (so far)": "/tmp/runb/gate_events.log",
        "today, Smart Turn ON (so far)": "/tmp/gate_events.log"}
for name, p in logs.items():
    if not os.path.exists(p): print(name, ": no log at", p); continue
    rooms = [json.loads(l) for l in open(p) if l.strip()]
    c = {}
    changed_rooms = 0; holds = []
    for r in rooms:
        ks = [e["kind"] for e in r["events"]]
        for k in ks: c[k] = c.get(k, 0) + 1
        if any(k in ("superseded", "cancelled", "duplicate") for k in ks): changed_rooms += 1
        holds += [e.get("held_s", 0) for e in r["events"] if e["kind"] == "execute"]
    rep = sum(1 for r in rooms for e in r["events"] if e["kind"] == "same_tool_again" and e.get("replace"))
    keep = sum(1 for r in rooms for e in r["events"] if e["kind"] == "same_tool_again" and not e.get("replace"))
    holds.sort()
    print(f"{name}: rooms {len(rooms)} | proposed {c.get('proposed',0)} | executed {c.get('execute',0)} | replaced (superseded) {c.get('superseded',0)} | withdrawn {c.get('cancelled',0)} | duplicates blocked {c.get('duplicate',0)} | same tool again: replace {rep}, keep both {keep} | rooms where the harness changed what ran: {changed_rooms} | median hold {holds[len(holds)//2] if holds else None}s")
PY
