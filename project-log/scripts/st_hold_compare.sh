#!/usr/bin/env bash
# Read-only: hold lengths and corrections caught, run v2 (no Smart Turn) vs run v3st so far (Smart Turn on).
python3 - <<'PY'
import json, os, statistics as st
def load(p): return [json.loads(l) for l in open(p)] if os.path.exists(p) else []
def summ(name, rooms):
    holds = [e["held_s"] for r in rooms for e in r["events"] if e["kind"] == "execute"]
    sup = sum(e["kind"] == "superseded" for r in rooms for e in r["events"])
    wd = sum(e["kind"] == "cancelled" for r in rooms for e in r["events"])
    fast = sum(h < 0.6 for h in holds); mid = sum(0.6 <= h < 1.5 for h in holds); slow = sum(h >= 1.5 for h in holds)
    print(f"{name}: rooms {len(rooms)} | executed {len(holds)} | median hold {st.median(holds):.2f}s mean {st.mean(holds):.2f}s | holds <0.6s: {fast}, 0.6-1.5s: {mid}, >=1.5s: {slow} | superseded {sup}, withdrawn {wd}")
v2 = load("/mnt/d/Theme5-Interruptible-Agents/project-log/runs/2026-09-30_full_gate_gemini38_v2/gate_events.log")
v3 = load("/tmp/gate_events.log")
first = lambda r: next((e["name"] + json.dumps(e["args"], sort_keys=True) for e in r["events"] if e["kind"] == "proposed"), None)
summ("v2 all 34 (no Smart Turn)", v2)
summ(f"v2 first {len(v3)} rooms", v2[:len(v3)])
summ(f"v3st first {len(v3)} rooms (Smart Turn on)", v3)
same = sum(first(a) == first(b) for a, b in zip(v2, v3))
print(f"first proposed call identical in v2 and v3st, room by room: {same}/{len(v3)} (a rough check that these are the same recordings in the same order)")
for a, b in zip(v2, v3):
    ha = [e["held_s"] for e in a["events"] if e["kind"] == "execute"]; hb = [e["held_s"] for e in b["events"] if e["kind"] == "execute"]
    pb = [e.get("p_complete") for e in b["events"] if e["kind"] == "smart_turn"]
    print("  ", (first(b) or "")[:38].ljust(38), "v2 hold", ha, "| v3st hold", hb, "p_complete", pb)
PY
